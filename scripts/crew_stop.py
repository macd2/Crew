#!/usr/bin/env python3
"""Stop crew work without destroying it: kill the worker, park the card, keep everything.

  crew_stop.py <card id>             PARK that one card: worker killed, session closed, card held for the owner
  crew_stop.py <card id> --archive   the real drop: as above, then the card is archived (explicit, one card)
  crew_stop.py                       PARK every CREW card that is not done or archived (a card without a crew
                                     Coordinator:/Role: line is somebody else's and is never touched). Never archives.
  [--dry-run] [--json] [--quiet]

WHAT ONE STOP DOES, IN ORDER

  1. kill the process group of every live run of the card (its own worker_pid). A pid that answers
     but is not this card's own worker is never touched - the guard reads the process's command
     line, so the gateway, the board server and the caller are safe by construction.
  2. close the session row each killed worker left open, through Hermes' own SessionDB.end_session
     (a killed worker never writes its session's ended_at, and every surface that reads a session then
     draws it as running for ever). No raw write into a profile's state.db: when hermes_state cannot
     be imported the sessions are reported as not closed.
  3. PARK the card with the kernel's own verbs, reason "stopped by owner (/crew-stop) - continue with
     /crew-unstuck <id>" (crew_card.owner_stop_reason): running/ready -> `hermes kanban block --kind <k>`
     (the Needs-you lane); todo/blocked -> `hermes kanban schedule`. With --archive: `hermes kanban archive`.
  4. re-read the card and say so when it did not hold.

WHY THIS PARK HOLDS (read from hermes_cli/kanban_db.py, 2026-10-03)

  - recompute_ready skips a `blocked` card whose newest block event is explicit (_has_sticky_block), and reads only
    todo/blocked, so a `scheduled` card is never promoted; every dispatch query needs ready.
  - block_task only moves running/ready. A parent-gated `todo` or an already-`blocked` card cannot be blocked, which
    is what `schedule_task` (todo/ready/running/blocked -> scheduled, not dispatchable, `unblock` re-gates) is for.
  - the kind: a same-kind re-block routes to `triage` (BLOCK_RECURRENCE_LIMIT) and triage feeds the decomposer,
    so the kind is the first of needs_input/capability/transient that differs from the card's last block kind.
  - the coordinator (handle_card), crew_heal.heal_card and crew_notify (card_reports) recognise the reason
    (crew_card.parked_by_owner) and leave the card alone: no decision, no heal, no "needs you" ping.
  - triage and review cards have no park verb in the kernel: they are reported as NOT down, never as stopped.

CONTINUE: /crew-unstuck <id> (crew_card.unstuck_card -> `hermes kanban unblock`): the card goes back in the queue
and the worker resumes with the card's whole history.

THE FAMILY IS REPORTED, NEVER SILENTLY FOLLOWED

  A card the decomposer fanned out keeps its work alive in child cards. This pass names the open cards linked to
  the one it stopped; stopping them is a second, explicit ask.

Run:  python3 crew_stop.py [<card id>] [--archive] [--dry-run] [--json] [--quiet]
Exit: 0 when every card it touched is down; 1 when one came back or could not be parked; 2 no board / bad
      arguments; 3 unknown card id.
"""
import argparse
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_card  # noqa: E402

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


def is_crew_card(card):
    """A card is crew work only when its body carries the crew Coordinator:/Role: line."""
    return crew_card.is_crew_body(card.get("body"))


# ------------------------------------------------------------------ decisions (pure)

def stop_targets(cards, card_id=None):
    """The cards this run stops: the named one, or every open crew card.

    A named card is returned whether or not it is open - the caller decides what to say about a card
    that is already done or archived, and a stop that silently ignored the id would read as success.
    """
    if card_id:
        return [c for c in cards if c.get("id") == card_id]
    return [c for c in cards if (c.get("status") or "") not in CLOSED_STATUSES and is_crew_card(c)]


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
    return bool(cmd) and "work kanban task" in cmd and card_id in cmd


def came_back(before, after):
    """True when a card moved between two reads of its state.

    The pass uses it to compare the state it left the card in with the state a later promotion pass
    leaves it in (that is the stays-down check the proof runs): a stop holds only while the status
    stays down (parked or archived) and no run row is added.
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
    if not is_our_worker(cmd, card_id):      # an empty / unreadable command line is refused too
        return "refused pid %s (not this card's worker%s)" % (pid, "" if cmd else ": command line unreadable"), False
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
    """Where the profiles live. CREW_STOP_HERMES_ROOT points the session lookup at a scratch tree (the
    proof's), leaving HERMES_HOME real so the `hermes kanban` call still runs."""
    if os.environ.get("CREW_STOP_HERMES_ROOT"):
        return os.path.abspath(os.environ["CREW_STOP_HERMES_ROOT"])
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
    """Close every session row this card's workers left open, through Hermes' SessionDB.end_session.

    A killed worker never reaches its own exit path, so ended_at stays NULL and each surface that
    asks a session whether it is running answers yes for ever.
    """
    closed, skipped = [], []
    src = os.environ.get("HERMES_SRC") or os.path.expanduser("~/.hermes/hermes-agent")
    if os.path.isdir(src) and src not in sys.path:
        sys.path.append(src)
    try:
        from hermes_state import SessionDB
    except ImportError:
        return closed, ["%s (hermes_state not importable here)" % sid for sid, _ in sessions_of(card_id)]
    for sid, prof in sessions_of(card_id):
        path = session_db(prof)
        if not os.path.exists(path):
            skipped.append("%s (no %s)" % (sid, os.path.basename(path)))
            continue
        try:
            sdb = SessionDB(db_path=Path(path))
            try:
                sess = sdb.get_session(sid)
                if not sess or sess.get("ended_at") is not None:
                    continue
                if not dry:
                    sdb.end_session(sid, "crew_stop")
                closed.append(sid if not dry else "%s (would close)" % sid)
            finally:
                sdb.close()
        except Exception as exc:  # noqa: BLE001 - one unreadable store must not stop the stop
            skipped.append("%s (%s)" % (sid, exc))
    return closed, skipped


def snapshot(card_id):
    """(status, run count, running count) - what 'it came back' is measured against."""
    t = q("select status from tasks where id = ?", (card_id,))
    runs = q("select status from task_runs where task_id = ?", (card_id,))
    return ((t[0]["status"] if t else "?"), len(runs), sum(1 for r in runs if r["status"] == "running"))


def archive_card(card_id, dry):
    if dry:
        return 0, ""
    done = subprocess.run([crew_card.hermes_bin(), "kanban", "archive", card_id], capture_output=True, text=True,
                          timeout=120, env=dict(os.environ, HERMES_KANBAN_DB=KANBAN_DB))
    return 1 if done.returncode == 0 else 0, (done.stdout + done.stderr).strip()


PARK_KINDS = ("needs_input", "capability", "transient")


def park_kind(card_id):
    """The block kind for the park: the first that differs from the card's last one, because a same-kind re-block
    is the kernel's loop breaker and routes the card to triage (BLOCK_RECURRENCE_LIMIT)."""
    rows = q("select block_kind from tasks where id = ?", (card_id,))
    last = rows[0]["block_kind"] if rows else None
    return next(k for k in PARK_KINDS if k != last)


def park_card(card_id, dry):
    """Park the card with the kernel's own verb for its state. Returns (status word, output)."""
    status = (q("select status from tasks where id = ?", (card_id,)) or [{"status": "?"}])[0]["status"]
    reason = crew_card.owner_stop_reason(card_id)
    if crew_card.parked_by_owner(KANBAN_DB, card_id):
        return "already parked", ""
    if status in ("running", "ready"):
        argv = ["block", card_id, "--kind", park_kind(card_id), reason]
    elif status in ("todo", "blocked"):
        argv = ["schedule", card_id, reason]
    elif status == "scheduled":
        return "already parked", ""
    else:
        return "cannot park a %s card" % status, ""
    if dry:
        return "would %s" % argv[0], ""
    done = subprocess.run([crew_card.hermes_bin(), "kanban"] + argv, capture_output=True, text=True, timeout=120,
                          env=dict(os.environ, HERMES_KANBAN_DB=KANBAN_DB))
    return argv[0] if done.returncode == 0 else "%s refused" % argv[0], (done.stdout + done.stderr).strip()


def stop_card(card, dry=False, archive=False):
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
    if archive:
        _archived, archive_msg = archive_card(card_id, dry)
        park_word = "archived"
    else:
        park_word, archive_msg = park_card(card_id, dry)
    after = snapshot(card_id) if not dry else before
    # a killed worker that still answers (the guard refused it, or the signal did not land) is the
    # one thing a stop may not report as done
    still_live = live_runs([dict(r) for r in q("select id, status, worker_pid from task_runs "
                                              "where task_id = ?", (card_id,))], alive) if not dry else []
    links = q("select parent_id, child_id, ? as self from task_links where parent_id = ? or child_id = ?",
              (card_id, card_id, card_id))
    cards = q("select id, status, assignee from tasks")
    family = family_of([dict(l) for l in links], cards)
    if dry:
        ok = True
    elif archive:
        ok = after[0] == "archived" and not still_live
    else:
        ok = (after[0] == "scheduled" or (after[0] == "blocked" and bool(crew_card.parked_by_owner(KANBAN_DB, card_id)))) \
            and not still_live
    facts = {"card": card_id, "before": before, "after": after, "runs_killed": [r["id"] for r in killed],
             "sessions_closed": closed, "sessions_skipped": skipped, "family": family, "still_down": ok, "parked": (not archive and ok), "how": park_word,
             "kill_words": kill_words}
    lines = report_lines(card, killed, closed, not dry, after, family)
    if ok and not dry and not archive:
        lines.append("  parked (%s): stays on the board with its history - /crew-unstuck %s to continue" % (park_word, card_id))
    lines += ["  " + w for w in kill_words if "dead" not in w and "would kill" not in w]
    if skipped:
        lines.append("  session(s) not closed: " + ", ".join(skipped))
    if not ok:
        lines.append("  %s said: %s" % ("archive" if archive else park_word, (archive_msg or "(nothing)")[-300:]))
        lines.append("  NOT DOWN: status=%s still running=%s - the stop did not hold"
                     % (after[0], [r["id"] for r in still_live]))
    return lines, ok, facts


def main(argv=None):
    ap = argparse.ArgumentParser(description="Stop crew work: park the card, keep its history.")
    ap.add_argument("card", nargs="?", help="one card id; without it every open crew card is parked")
    ap.add_argument("--archive", action="store_true",
                    help="drop the card for good (archive it) instead of parking it; needs a card id")
    ap.add_argument("--dry-run", action="store_true", help="report what would be stopped")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--quiet", action="store_true", help="only the failing cards and the count")
    args = ap.parse_args(argv)

    if args.archive and not args.card:
        ap.error("--archive drops a card for good: name the card (the all-cards form only parks)")
    if not os.path.exists(KANBAN_DB):
        print("no board at %s" % KANBAN_DB)
        return 2
    cards = q("select id, status, assignee, title, body from tasks")
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
        lines, ok, facts = stop_card(card, args.dry_run, args.archive)
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
