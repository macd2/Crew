#!/usr/bin/env python3
"""Stop crew work: one command that kills it and leaves it down.

  crew_stop.py <card id>          that one card, nothing else
  crew_stop.py                    every card that is not done or archived (the open board)
  [--dry-run] [--json] [--quiet]

WHAT ONE STOP DOES, IN ORDER

  1. kill the process group of every live run of the card (its own worker_pid). A pid that answers
     but is not this card's own worker is never touched - the guard reads the process's command
     line, so the gateway, the board server and the caller are safe by construction.
  2. close the session row each killed worker left open. A killed worker never writes its session's
     ended_at, and every surface that reads a session then draws it as running for ever (the card
     page did, until the row was closed by hand).
  3. archive the card.
  4. re-read the card and say so when it came back - the stop is only a stop if it holds.

WHY ARCHIVE AND NOT BLOCK (measured on the live board, 2026-09-30)

  - a parent-gated `todo` card cannot be blocked at all: kanban_db.block_task only transitions
    running/ready, and answers `cannot block <id>` for anything else.
  - cutting one of its parent links is not a stop either: recompute_ready sees all parents done and
    PROMOTES it to ready (a real `promoted` event), which reads as the card restarting itself.
  - a second same-kind block is rerouted by the kernel to `triage` (BLOCK_RECURRENCE_LIMIT=2) and
    triage is what feeds the decomposer, which spawns NEW children - more work, not less.
  - `archived` holds: recompute_ready reads only todo/blocked, and every dispatch query carries
    `status != 'archived'`.

THE FAMILY IS REPORTED, NEVER SILENTLY FOLLOWED

  A card the decomposer fanned out keeps its work alive in child cards, which the owner reads as the
  card restarting on its own. This pass names the open cards linked to the one it stopped; stopping
  them is a second, explicit ask.

Run:  python3 crew_stop.py [<card id>] [--dry-run] [--json] [--quiet]
Exit: 0 when every card it touched is down; 1 when one came back; 2 no board; 3 unknown card id.
"""
import argparse
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
KANBAN_DB = os.environ.get("KANBAN_DB", os.path.join(os.path.expanduser("~"), ".hermes", "kanban.db"))
# A card in one of these is still somebody's work in progress; done and archived are not.
OPEN_STATUSES = ("triage", "todo", "scheduled", "ready", "running", "blocked", "review")
CLOSED_STATUSES = ("done", "archived")
TERM_WAIT_S = 1.5


def q(sql, args=()):
    conn = sqlite3.connect("file:%s?mode=ro" % KANBAN_DB, uri=True)
    try:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(sql, args).fetchall()]
    finally:
        conn.close()


def write(sql, args=()):
    conn = sqlite3.connect(KANBAN_DB)
    try:
        cur = conn.execute(sql, args)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def event(card, kind, payload):
    """One audit row on the card, the same shape every other crew pass writes."""
    return write("insert into task_events (task_id, run_id, kind, payload, created_at) values (?,?,?,?,?)",
                 (card, None, kind, json.dumps(payload), int(time.time())))


# ------------------------------------------------------------------ decisions (pure)

def stop_targets(cards, card_id=None):
    """The cards this run stops: the named one, or every open card.

    A named card is returned whether or not it is open - the caller decides what to say about a card
    that is already done or archived, and a stop that silently ignored the id would read as success.
    """
    if card_id:
        return [c for c in cards if c.get("id") == card_id]
    return [c for c in cards if (c.get("status") or "") not in CLOSED_STATUSES]


def live_runs(runs, alive):
    """The runs worth killing: still marked running AND their pid still answers.

    A worker that died without writing a settle row leaves `status='running'` behind for ever, so the
    status column alone would send a kill at a pid the kernel has already reused.
    """
    out = []
    for r in runs:
        pid = r.get("worker_pid")
        if (r.get("status") or "") == "running" and pid and alive(pid):
            out.append(r)
    return out


def is_our_worker(cmdline, card_id):
    """True only for a process that is this card's own crew worker.

    The dispatcher spawns workers as `hermes -p <role> ... chat -q "work kanban task <id>"`, so the
    card id is in the command line. Everything else - the gateway, the board server, this process,
    a sibling session - fails the guard and is never signalled.
    """
    cmd = cmdline or ""
    return "work kanban task" in cmd and card_id in cmd


def came_back(before, after):
    """True when a card moved between two reads of its state.

    The pass uses it to compare the state it left the card in with the state a later promotion pass
    leaves it in (that is the stays-down check the proof runs): a stop holds only while the status
    stays `archived` and no run row is added.
    """
    return tuple(before) != tuple(after)


def family_of(links, cards):
    """The open cards linked to this one in either direction, named as `role: id (status)`.

    The decomposer links the card it decomposed to the children it created, so the work of a stopped
    card lives on in cards that are not the card - the reason the owner saw one restart by itself.
    """
    by_id = {c["id"]: c for c in cards}
    open_ids = []
    for l in links:
        for other in (l.get("parent_id"), l.get("child_id")):
            if other and other != l.get("self") and other not in open_ids:
                open_ids.append(other)
    out = []
    for oid in open_ids:
        c = by_id.get(oid)
        if c and (c.get("status") or "") not in CLOSED_STATUSES:
            out.append("%s: %s (%s)" % (c.get("assignee") or "?", oid, c.get("status")))
    return out


def report_lines(card, killed, closed, archived, after, family):
    """The pass's own wording: what it killed, what it closed, what it left open beside it."""
    lines = ["%s  %s -> %s" % (card["id"], card.get("status"), after[0])]
    if killed:
        lines.append("  killed: " + ", ".join("run %s pid %s" % (r["id"], r["worker_pid"]) for r in killed))
    else:
        lines.append("  killed: nothing running")
    if closed:
        lines.append("  session(s) closed: " + ", ".join(closed))
    if family:
        lines.append("  still open beside it: " + "; ".join(family))
        lines.append("  stopping those is a separate ask: crew_stop.py <id>")
    return lines


# ------------------------------------------------------------------ process/board work

def alive(pid):
    """True while the process really runs.

    A zombie counts as gone: a killed child nobody has reaped yet still answers signal 0, and a stop
    that reported "still alive" for a process it had just killed would be wrong (it did, on the first
    live run of this pass).
    """
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    try:
        with open("/proc/%d/stat" % pid) as fh:
            state = fh.read().rsplit(") ", 1)[-1][:1]
        if state == "Z":
            return False
    except OSError:
        pass
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except (PermissionError, ValueError):
        return True


def cmdline_of(pid):
    try:
        with open("/proc/%d/cmdline" % int(pid)) as fh:
            return fh.read().replace("\0", " ")
    except OSError:
        return ""


def kill_run(run, card_id, dry):
    """Kill one run's worker process group. Returns (word, landed) for the report."""
    pid = int(run["worker_pid"])
    cmd = cmdline_of(pid)
    if cmd and not is_our_worker(cmd, card_id):
        return "refused pid %s (not this card's worker)" % pid, False
    if dry:
        return "would kill run %s pid %s" % (run["id"], pid), True
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return "gone run %s pid %s" % (run["id"], pid), False
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            break
        time.sleep(TERM_WAIT_S)
        if not alive(pid):
            break
    if alive(pid):
        # The group was gone but the pid answers: signal the pid itself rather than report a kill
        # that did not land.
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    return "run %s pid %s %s" % (run["id"], pid, "dead" if not alive(pid) else "STILL ALIVE"), not alive(pid)


def sessions_of(card_id):
    """(session id, profile) for every session a worker recorded on this card, newest first."""
    out = []
    for row in q("select payload, run_id from task_events where task_id = ? and kind = 'session' "
                 "order by id desc", (card_id,)):
        try:
            data = json.loads(row["payload"] or "{}")
        except ValueError:
            continue
        sid, prof = data.get("session"), data.get("profile") or ""
        if sid and (sid, prof) not in out:
            out.append((sid, prof))
    return out


def hermes_root():
    home = os.path.abspath(os.environ.get("HERMES_HOME") or os.path.join(os.path.expanduser("~"), ".hermes"))
    if os.path.basename(os.path.dirname(home)) == "profiles":
        return os.path.dirname(os.path.dirname(home))
    return home


def session_db(profile):
    root = hermes_root()
    if profile and profile != "default":
        return os.path.join(root, "profiles", profile, "state.db")
    return os.path.join(root, "state.db")


def close_sessions(card_id, dry):
    """Close every session row this card's workers left open.

    A killed worker never reaches its own exit path, so ended_at stays NULL and each surface that
    asks a session whether it is running answers yes for ever.
    """
    closed, skipped = [], []
    for sid, prof in sessions_of(card_id):
        path = session_db(prof)
        if not os.path.exists(path):
            skipped.append("%s (no %s)" % (sid, os.path.basename(path)))
            continue
        try:
            conn = sqlite3.connect(path, timeout=10)
            row = conn.execute("select ended_at from sessions where id = ?", (sid,)).fetchone()
            if row is None or row[0] is not None:
                conn.close()
                continue
            if dry:
                closed.append("%s (would close)" % sid)
            else:
                conn.execute("update sessions set ended_at = ? where id = ? and ended_at is null",
                             (time.time(), sid))
                conn.commit()
                closed.append(sid)
            conn.close()
        except sqlite3.Error as exc:
            skipped.append("%s (%s)" % (sid, exc))
    return closed, skipped


def snapshot(card_id):
    """(status, run count, running count) - what 'it came back' is measured against."""
    t = q("select status from tasks where id = ?", (card_id,))
    runs = q("select status from task_runs where task_id = ?", (card_id,))
    return ((t[0]["status"] if t else "?"), len(runs), sum(1 for r in runs if r["status"] == "running"))


def archive_card(card_id, dry):
    if dry:
        return 0
    return write("update tasks set status = 'archived' where id = ? and status != 'archived'", (card_id,))


def stop_card(card, dry=False):
    """One card, in the order the docstring promises. Returns (report, ok, json facts)."""
    card_id = card["id"]
    before = snapshot(card_id)
    runs = q("select id, status, worker_pid from task_runs where task_id = ?", (card_id,))
    live = live_runs([dict(r) for r in runs], alive)
    killed, kill_words = [], []
    for r in live:
        word, landed = kill_run(r, card_id, dry)
        kill_words.append(word)
        if landed:
            killed.append(r)
    closed, skipped = close_sessions(card_id, dry)
    archive_card(card_id, dry)
    if not dry:
        event(card_id, "stopped", {"by": "crew_stop", "runs_killed": [r["id"] for r in killed],
                                   "sessions_closed": closed})
    after = snapshot(card_id) if not dry else before
    # a killed worker that still answers (the guard refused it, or the signal did not land) is the
    # one thing a stop may not report as done
    still_live = live_runs([dict(r) for r in q("select id, status, worker_pid from task_runs "
                                              "where task_id = ?", (card_id,))], alive) if not dry else []
    links = q("select parent_id, child_id, ? as self from task_links where parent_id = ? or child_id = ?",
              (card_id, card_id, card_id))
    cards = q("select id, status, assignee from tasks")
    family = family_of([dict(l) for l in links], cards)
    ok = True if dry else (after[0] == "archived" and not still_live)
    facts = {"card": card_id, "before": before, "after": after, "runs_killed": [r["id"] for r in killed],
             "sessions_closed": closed, "sessions_skipped": skipped, "family": family, "still_down": ok,
             "kill_words": kill_words}
    lines = report_lines(card, killed, closed, not dry, after, family)
    lines += ["  " + w for w in kill_words if "dead" not in w and "would kill" not in w]
    if skipped:
        lines.append("  session(s) not closed: " + ", ".join(skipped))
    if not ok:
        lines.append("  NOT DOWN: status=%s still running=%s - the stop did not hold"
                     % (after[0], [r["id"] for r in still_live]))
    return lines, ok, facts


def main(argv=None):
    ap = argparse.ArgumentParser(description="Stop crew work and keep it down.")
    ap.add_argument("card", nargs="?", help="one card id; without it every open card is stopped")
    ap.add_argument("--dry-run", action="store_true", help="report what would be stopped")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--quiet", action="store_true", help="only the failing cards and the count")
    args = ap.parse_args(argv)

    if not os.path.exists(KANBAN_DB):
        print("no board at %s" % KANBAN_DB)
        return 2
    cards = q("select id, status, assignee, title from tasks")
    if args.card:
        targets = stop_targets([dict(c) for c in cards], args.card)
        if not targets:
            print("no such card: %s" % args.card)
            return 3
    else:
        targets = stop_targets([dict(c) for c in cards])
    if not targets:
        # a dry run says so even when there is nothing to do, so the caller can see which mode answered
        print("stop%s: nothing to stop (0 card(s) open)" % (" (dry run)" if args.dry_run else ""))
        return 0

    results, fails = [], []
    mode = "dry run" if args.dry_run else "stop"
    if not args.quiet:
        print("crew stop - %s  %d card(s)%s" % (mode, len(targets), "  (--dry-run)" if args.dry_run else ""))
    for card in targets:
        lines, ok, facts = stop_card(card, args.dry_run)
        results.append(facts)
        if not ok:
            fails.append(card["id"])
        if not args.quiet or not ok:
            print("\n".join(lines))
    killed = sum(len(f["runs_killed"]) for f in results)
    closed = sum(len(f["sessions_closed"]) for f in results)
    print("stop: %d card(s), %d run(s) killed, %d session(s) closed%s"
          % (len(results), killed, closed, "  (%d came back!)" % len(fails) if fails else ""))
    if args.json:
        print(json.dumps({"mode": mode, "cards": results, "came_back": fails}, indent=2))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
