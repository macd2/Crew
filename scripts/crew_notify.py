#!/usr/bin/env python3
"""Crew's own way back to the owner: one message per thing that needs him, through Hermes's public sender.

A crew card is the coordinator's until it is verified done, one concrete question needs the owner, or the owner's
own words abandoned it. Only those three reach the owner, each exactly once, into the chat the card was opened
from (its `Origin: <platform>:<chat>` record):

  done       one report (the card's closing summary, or its result) into the origin chat
  needs you  one message per NEW owner question: the coordinator's `ask_owner` decision, or a crew card stuck in
             blocked/triage that the coordinator has not decided on within DECISION_GRACE_S (it is not
             running: the block goes out as it is). While the coordinator still owns the card - blocks, retries,
             rescopes, heals, verifier runs - nothing is sent.
  abandoned  one line, when the coordinator archived the card on the owner's own word

There is no platform code here. The text goes out as `hermes [-p <owner>] send -t <target> --file -`: Hermes
resolves the target and delivers with the profile's own gateway credentials (no model, no running gateway).
The origin string IS the send target: Hermes records a chat as `<platform>:<chat id>` and the platform's own
target parser reads that same form (Zulip: `zulip:stream:<s>|<topic>`, `zulip:dm:<id>`; checked against its
parser). `send_target` is the one place a platform that needs another spelling would be translated.

A done card is reported once the coordinator's audit of it has settled (audit_outcome): an audit that failed opens a
follow-up card, and that card's ending is the report. The same decision, per card, is `card_reports`; crew_watch (the
in-session watcher: it tells the session that opened the card, before this sender would) calls the same functions
and records what it told in this state file, so nothing goes out twice.

A card with no origin: done and abandoned stay silent (nobody asked in a chat; whoever ran it from the CLI sees
it end). A needs-you message still has to reach him, so it goes to the home channel of the platform of the owner's
newest chat origin on the board (`hermes send -t <platform>`); with no chat origin anywhere it is logged and
marked, never retried forever.

State, one file per board ($HERMES_HOME/crew/notify-state[-board].json): {"since": first run, "sent": {card: [key]},
"tries": {"card|key": n}}. The first run only records `since`: endings before it are never replayed, and nothing
older than NOTIFY_WINDOW_S is sent after an outage either. A key is `done:<completed event id>`,
`ask:<decision event id>` (or `block:<stop event id>` for the no-decision case) or `abandoned:<decision event id>`:
a restart resends nothing, a reopened card that ends again reports again, a new question is a new key. A failed
send is not marked and retries on the next pass (`has_pending` makes the coordinator tick start one); after
MAX_TRIES failures it is marked and logged, so a dead target cannot keep every tick busy.

  python3 crew_notify.py [--db PATH] [--state PATH] [--dry-run]     (dry run prints target + text, sends nothing)
"""
import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_card  # noqa: E402

NOTIFY_WINDOW_S = int(os.environ.get("CREW_NOTIFY_WINDOW", "3600"))      # never replay old endings
# A blocked crew card is the coordinator's to decide (crew_coordinator.py, one pass per tick). No decision within
# this many seconds of the block means it is not deciding, and the owner hears about the block as it stands.
DECISION_GRACE_S = int(os.environ.get("CREW_DECISION_GRACE", "600"))
# A done card's audit decision (crew_coordinator.audit_completion) normally lands in the same pass as the completion;
# none within this many seconds of it means the coordinator is not auditing, and the done is reported as it stands.
AUDIT_GRACE_S = int(os.environ.get("CREW_AUDIT_GRACE", "900"))
STOP_EVENT_KINDS = ("blocked", "block_loop_detected", "gave_up")
MAX_TRIES = 6
SEND_TIMEOUT_S = 90
COORD_RX = re.compile(r"^\s*Coordinator:\s*(\S+)", re.M)
SECRET_RX = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|(?i:(?:api[_-]?key|token|secret|password)\s*[=:]\s*)\S+)")


def short(text, n):
    text = SECRET_RX.sub("[redacted]", " ".join(str(text or "").split()))
    return text if len(text) <= n else text[: n - 1] + "…"


def card_url(tid):
    base = (os.environ.get("CREW_CARD_BASE") or crew_card.dashboard_url()).rstrip("/")
    return "%s/card/%s" % (base, urllib.parse.quote(tid))


def state_file(board=None):
    """$HERMES_HOME/crew/notify-state[-board].json: one state per board, beside the coordinator's cursor."""
    suffix = "-%s" % board if board and board != "default" else ""
    return os.path.join(crew_card.base_home(), "crew", "notify-state%s.json" % suffix)


def load_state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def save_state(path, state):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    os.replace(tmp, path)


def has_pending(path):
    """True when a send failed and waits for its retry: the coordinator tick starts a pass for it."""
    state = load_state(path)
    return bool(state and state.get("tries"))


# ------------------------------------------------------------------------------------ what happened to a card
def owner_question(conn, tid, now):
    """(alert?, question, key) for a blocked/triage crew card: ask the owner when the coordinator's newest decision
    after the newest block is ask_owner (its question), or when the block is older than DECISION_GRACE_S with no
    decision at all; otherwise the coordinator still owns the card and nothing goes out. `key` names the event the
    message answers, so the same question is never sent twice and a new one always is."""
    stop = conn.execute("select id, created_at from task_events where task_id=? and kind in (%s) "
                        "order by id desc limit 1" % ",".join("?" * len(STOP_EVENT_KINDS)),
                        (tid,) + STOP_EVENT_KINDS).fetchone()
    dec = conn.execute("select id, payload from task_events where task_id=? and kind='crew_decision' "
                       "order by id desc limit 1", (tid,)).fetchone()
    if dec and (not stop or dec["id"] > stop["id"]):
        try:
            data = json.loads(dec["payload"] or "{}")
        except ValueError:
            data = {}
        if data.get("decision") == "ask_owner":
            return True, str(data.get("question") or ""), "ask:%d" % dec["id"]
        return False, "", ""
    if stop and now - (stop["created_at"] or 0) > DECISION_GRACE_S:
        return True, "", "block:%d" % stop["id"]
    return (not stop), "", "block:0"


def resolved_origin(db, tid):
    """(origin, source card): the card's own record, else inherited up its chain (a child the coordinator split
    off carries none of its own; crew_card.ancestors walks task_links parents and the decomposer's record)."""
    for cid in [tid] + crew_card.ancestors(db, tid):
        found = crew_card.own_origin(db, cid) or {}
        origin = crew_card.origin_id(found.get("origin"))
        if origin:
            return origin, cid
    return "", tid


def last_origin_platform(conn):
    """The platform of the owner's newest chat origin on the board, '' when no card ever came from a chat."""
    for row in conn.execute("select payload from task_events where kind='origin' order by id desc limit 50"):
        try:
            origin = crew_card.origin_id((json.loads(row["payload"] or "{}") or {}).get("origin"))
        except ValueError:
            continue
        if origin:
            return origin.partition(":")[0].strip().lower()
    return ""


def send_target(origin):
    """The `hermes send -t` target for an origin. Hermes's own platform parsers read the chat id Hermes records
    (`<platform>:<chat id>[:<thread>]`), so it passes through; this is the single place to translate a platform
    whose send syntax differs from its session chat id."""
    return crew_card.origin_id(origin)


def done_summary(conn, task):
    """What a done card delivered: its newest run summary, else its result (the closing summary of the report)."""
    run = conn.execute("select summary from task_runs where task_id=? and summary is not null "
                       "order by id desc limit 1", (task["id"],)).fetchone()
    return short((run["summary"] if run else None) or task["result"] or "", 600)


def _text(conn, task, kind, src, question="", extra=""):
    """The message for one ending. `extra` is lines the caller adds above the card link (crew_watch: what was
    delivered where, the proof outcome, how to answer)."""
    tid, title = task["id"], short(task["title"], 120)
    tail = "\nFrom card: %s (this card was created under it)" % src if src and src != tid else ""
    link = "%s\nCard: %s" % (("\n" + extra.strip("\n")) if extra else "", card_url(tid))
    if kind == "done":
        summary = done_summary(conn, task)
        return "🟢 done · %s · %s\n%s%s%s" % (tid, title, (summary + "\n") if summary else "", tail, link)
    if kind == "abandoned":
        dec = conn.execute("select payload from task_events where task_id=? and kind='crew_decision' "
                           "order by id desc limit 1", (tid,)).fetchone()
        try:
            why = (json.loads(dec["payload"] or "{}") or {}).get("why") if dec else ""
        except ValueError:
            why = ""
        return "⚫ abandoned · %s · %s%s%s" % (tid, title, (": " + short(why, 200)) if why else "", link)
    ev = conn.execute("select payload from task_events where task_id=? and kind in "
                      "('blocked','gave_up','crashed','timed_out') order by id desc limit 1", (tid,)).fetchone()
    try:
        reason = (json.loads(ev["payload"] or "{}") or {}).get("reason") if ev else ""
    except ValueError:
        reason = ""
    reason = short(question or reason or task["last_failure_error"] or "", 300)
    return ("🔴 needs you · %s · %s\n%s%s%s"
            % (tid, title, ("%s\n" % reason) if reason and reason != "initial_status" else "", tail, link))


def _decisions(conn, tid, kinds=("crew_decision",)):
    """The card's crew_decision payloads, newest first, each with its event id as `_id` and time as `_at`."""
    out = []
    for row in conn.execute("select id, payload, created_at from task_events where task_id=? and kind in (%s) "
                            "order by id desc" % ",".join("?" * len(kinds)), (tid,) + tuple(kinds)):
        try:
            data = json.loads(row["payload"] or "{}")
        except ValueError:
            continue
        if isinstance(data, dict):
            out.append(dict(data, _id=row["id"], _at=row["created_at"]))
    return out


def audit_outcome(conn, db, task, completed, now):
    """(state, decision, follow-up card) for a done card's `completed` event (id, created_at):
    settled   the audit passed, or there is none to wait for (no proof to re-run, the owner's own close)
    followup  the audit failed and a follow-up card carries the work on: that card's ending is the report
    wait      an audited card whose audit decision is not written yet (the coordinator is mid-pass)
    Waiting ends AUDIT_GRACE_S after the completion: a coordinator that is not running reports the done as it is."""
    for dec in _decisions(conn, task["id"]):
        if dec.get("decision") in ("audit", "owner_close") and dec.get("for_event") == completed["id"]:
            if dec["decision"] == "audit" and dec.get("outcome") in ("fail", "blocked") and dec.get("followup"):
                return "followup", dec, dec["followup"]
            return "settled", dec, ""
    role = (crew_card.field(task["body"], "Role") or "").strip().lower()
    audited = (crew_card.needs_pass(task["body"]) and role in crew_card.WRITER_ROLES
               and bool(crew_card.close_proof_command(task["id"], db)))
    if audited and now - (completed["created_at"] or 0) <= AUDIT_GRACE_S:
        return "wait", None, ""
    return "settled", None, ""


def card_reports(conn, db, task, cutoff, now):
    """[(key, kind, question)] this one card has for the owner right now, whether or not it was already sent
    (that is the state's business). The single decision both senders use: crew_notify's pass over the board and
    crew_watch's poll of one card. A done card counts once its audit settled and no follow-up took over;
    an abandoned one when the abandon is newer than `cutoff`; a stopped one when the owner owes an answer."""
    tid, status = task["id"], task["status"]
    if status == "done":
        ev = conn.execute("select id, created_at from task_events where task_id=? and kind='completed' "
                          "order by id desc limit 1", (tid,)).fetchone() or {"id": 0, "created_at": 0}
        state, _dec, _follow = audit_outcome(conn, db, task, ev, now)
        return [("done:%d" % ev["id"], "done", "")] if state == "settled" else []
    if status == "archived":
        dec = (_decisions(conn, tid) or [{}])[0]          # the newest decision decides: abandon, or not
        if dec.get("decision") == "abandon" and (dec["_at"] or 0) >= cutoff:
            return [("abandoned:%d" % dec["_id"], "abandoned", "")]
        return []
    if status not in ("blocked", "triage"):
        return []
    if crew_card.parked_by_owner(db, tid):
        return []              # the owner stopped it themselves (/crew-stop): nothing to ask, nothing to report
    alert, question, key = owner_question(conn, tid, now)
    return [(key, "needs", question)] if alert else []     # a card the coordinator still owns: no ping, no mark


def candidates(conn, db, since, now):
    """[(card, key, kind, when, task, src, question)] for every crew card whose ending or question is newer than
    `since` and the notify window. Whether it was already sent is the state's business."""
    cutoff = max(since, now - NOTIFY_WINDOW_S)
    owner = crew_card.owner_profile() + "/"
    rows = conn.execute(
        "select t.*, (select max(created_at) from task_events e where e.task_id=t.id) as last_ev from tasks t "
        "where t.status in ('done','blocked','triage','archived')").fetchall()
    out = []
    for task in rows:
        last = max(task["completed_at"] or 0, task["last_ev"] or 0)
        if last < cutoff:
            continue
        coord = COORD_RX.search(task["body"] or "")
        if not coord or not coord.group(1).startswith(owner):
            continue                              # not this owner's crew card
        for key, kind, question in card_reports(conn, db, task, cutoff, now):
            out.append((task["id"], key, kind, last, task, "", question))
    return out


def sent_keys(state_path, tid):
    return (load_state(state_path) or {}).get("sent", {}).get(tid, [])


def mark_sent(state_path, tid, key, now=None):
    """Record a message as sent from outside `run` (crew_watch told the session itself). Creates the state the way
    a first run would: from now on counts, nothing before is replayed."""
    state = load_state(state_path) or {"since": now or time.time(), "sent": {}, "tries": {}}
    state.setdefault("sent", {}).setdefault(tid, [])
    if key not in state["sent"][tid]:
        state["sent"][tid].append(key)
    save_state(state_path, state)


# ------------------------------------------------------------------------------------ sending
def hermes_send(target, text):
    """(ok, detail): `hermes [-p owner] send -t target --file -`. The caller's env is kept as it is: Hermes loads the
    profile's own .env and secret sources for `-p` itself, so a scrubbed coordinator env still delivers."""
    cmd = [crew_card.hermes_bin()]
    owner = crew_card.owner_profile()
    if owner and owner != "default":
        cmd += ["-p", owner]
    cmd += ["send", "-t", target, "--file", "-"]
    try:
        proc = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=SEND_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, "%s: %s" % (type(exc).__name__, str(exc)[:160])
    tail = ((proc.stderr or "") + (proc.stdout or "")).strip().splitlines()[-1:] or [""]
    return proc.returncode == 0, "rc=%d %s" % (proc.returncode, tail[0][:160])


def run(db, state_path, dry_run=False, send=None, say=print, now=None, baseline=None):
    """One notify pass over the board at `db`; returns the list of (card, key, target, sent?) it acted on.
    `send(target, text) -> (ok, detail)` replaces the real sender (tests). `baseline` is where a first run
    counts history from (default: now)."""
    send = send or hermes_send
    now = now or time.time()
    state = load_state(state_path)
    if state is None:                              # first run: baseline, no replay
        if not dry_run:
            save_state(state_path, {"since": baseline or now, "sent": {}, "tries": {}})
            say("crew notify: first run, endings before %s are not replayed"
                % time.strftime("%H:%M:%S", time.localtime(baseline or now)))
            if not baseline:
                return []
            state = load_state(state_path)
        else:
            state = {"since": now, "sent": {}, "tries": {}}
            say("crew notify (dry run): no state yet - a real first run would baseline at now; showing the last "
                "%d s" % NOTIFY_WINDOW_S)
            state["since"] = now - NOTIFY_WINDOW_S
    sent, tries = state.setdefault("sent", {}), state.setdefault("tries", {})
    conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    done = []
    try:
        for tid, key, kind, _when, task, _src, question in sorted(candidates(conn, db, state["since"], now),
                                                                  key=lambda c: c[3]):
            if key in sent.get(tid, []):
                continue
            origin, src = resolved_origin(db, tid)
            target = send_target(origin)
            if not target and kind == "needs":
                platform = last_origin_platform(conn)
                target = platform or ""
            if not target:
                say("crew notify: %s %s has no chat to report into, skipped" % (tid, kind))
                sent.setdefault(tid, []).append(key)
                continue
            text = _text(conn, task, kind, src, question)
            if dry_run:
                say("--- %s (%s %s)\n%s\n" % (target, kind, tid, text))
                done.append((tid, key, target, False))
                continue
            ok, detail = send(target, text)
            slot = "%s|%s" % (tid, key)
            if ok:
                sent.setdefault(tid, []).append(key)
                tries.pop(slot, None)
            else:
                tries[slot] = tries.get(slot, 0) + 1
                say("crew notify: send of %s %s to %s failed (%d/%d): %s" % (kind, tid, target, tries[slot],
                                                                              MAX_TRIES, detail))
                if tries[slot] >= MAX_TRIES:
                    say("crew notify: giving up on %s %s" % (kind, tid))
                    sent.setdefault(tid, []).append(key)
                    tries.pop(slot, None)
            done.append((tid, key, target, ok))
        live = {r[0] for r in conn.execute("select id from tasks")}
    finally:
        conn.close()
    for tid in [t for t in sent if t not in live]:
        sent.pop(tid, None)
    if not dry_run:
        for tid, keys in ((load_state(state_path) or {}).get("sent") or {}).items():    # what crew_watch marked meanwhile
            have = state["sent"].setdefault(tid, []) if tid in live else []
            have.extend(k for k in keys if k not in have)
        save_state(state_path, state)
    return done


def main():
    ap = argparse.ArgumentParser(description="report crew endings and owner questions back to the owner's chat")
    ap.add_argument("--db", default=None, help="board kanban.db (default: the live board)")
    ap.add_argument("--state", default=None, help="state file (default: $HERMES_HOME/crew/notify-state.json)")
    ap.add_argument("--dry-run", action="store_true", help="print target + text, send and record nothing")
    a = ap.parse_args()
    db = a.db or crew_card.kanban_db()
    if not db or not os.path.exists(db):
        print("no board")
        return 2
    run(db, a.state or state_file(), dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
