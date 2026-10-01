#!/usr/bin/env python3
"""Every card sitting in one board state, with its id and the reason it is there. Read-only.

The reader behind the /crew-diagnose pass: deterministic, no model call, and it changes nothing - no
retry, no unblock, no comment, no assignee change, no dispatch, no file written. The turn that runs
it reads the list and works out how each card would resume; the owner decides what to act on.

Usage:
  crew_diagnose.py                     every blocked card (the default state)
  crew_diagnose.py --state todo        every card in one state: triage|todo|ready|running|blocked|done|archived
  crew_diagnose.py --card t_ab12cd34   one card, whatever state it is in
  crew_diagnose.py --json              the same result as data

Exit: 0 with the list (an empty list is a result, not an error), 1 for an unknown state,
2 when the board cannot be read.
"""
import argparse
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# One reader for the board and one for the token budget: crew_card's, so a card's reason and its
# spend read the same here as they do in the coordinator loop.
import crew_card  # noqa: E402
from crew_card import base_home, kanban_db, ledger_spent as spent  # noqa: E402

STATES = ("triage", "todo", "ready", "running", "blocked", "done", "archived")
REASON_CHARS = 400
# Said once, when the board really carries nothing: a card with no reason is a fact about the board,
# not something to dress up, and the turn reading this must not fill the gap with a guess.
NO_REASON = "no reason recorded on the board"


def board_rows(state, card):
    """The barest rows for the cards in that state, or None when there is no board to read."""
    db = kanban_db()
    if not db:
        return None
    sql = ("select t.id, t.title, t.status, t.assignee, t.block_kind, t.created_at, t.result, "
           "t.last_failure_error, t.consecutive_failures, "
           "(select r.summary from task_runs r where r.task_id=t.id order by r.id desc limit 1), "
           "(select r.error   from task_runs r where r.task_id=t.id order by r.id desc limit 1), "
           "(select count(*)  from task_runs r where r.task_id=t.id), "
           "(select e.payload from task_events e where e.task_id=t.id and e.kind='blocked' "
           " order by e.id desc limit 1), "
           "(select e.created_at from task_events e where e.task_id=t.id and e.kind='blocked' "
           " order by e.id desc limit 1), "
           "(select e.payload from task_events e where e.task_id=t.id and e.kind='crew_decision' "
           " order by e.id desc limit 1) "
           "from tasks t")
    where, params = [], []
    if card:
        where.append("t.id = ?")
        params.append(card)
    if state:
        where.append("t.status = ?")
        params.append(state)
    if where:
        sql += " where " + " and ".join(where)
    sql += " order by t.created_at asc"
    conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    try:
        return conn.execute(sql, tuple(params)).fetchall()
    finally:
        conn.close()


def block_event(payload):
    """(reason, kind) as recorded when the card was blocked, for a run that recorded neither."""
    try:
        data = json.loads(payload or "{}")
    except ValueError:
        return "", ""
    if not isinstance(data, dict):
        return "", ""
    return str(data.get("reason") or "").strip(), str(data.get("kind") or "").strip()


def decision_text(payload):
    """The coordinator's last decision on the card as one short line, '' when it has made none."""
    try:
        data = json.loads(payload or "{}")
    except ValueError:
        return ""
    if not isinstance(data, dict) or not data.get("decision"):
        return ""
    detail = crew_card.decision_detail(data)
    return ("%s: %s" % (data["decision"], detail)) if detail else str(data["decision"])


def human_age(seconds):
    """A wait as it reads on a board: 45m, 6h, 3d 4h. Empty when there is no timestamp."""
    seconds = int(seconds or 0)
    if seconds <= 0:
        return ""
    minutes = seconds // 60
    if minutes < 60:
        return "%dm" % minutes
    hours = minutes // 60
    if hours < 24:
        return "%dh" % hours
    return "%dd %dh" % (hours // 24, hours % 24)


def cards_from_rows(rows, now=None):
    """The rows as cards: id, title, state, kind, how long it has waited and why it is there."""
    now = int(now if now is not None else time.time())
    out = []
    for (cid, title, state, assignee, block_kind, created_at, result, failure,
         failures, summary, error, runs, payload, blocked_at, decision_payload) in rows:
        event_reason, event_kind = block_event(payload)
        reason = (summary or error or event_reason or result or failure or "").strip()
        used, budget = spent(cid)
        out.append({
            "id": cid,
            "title": (title or "").strip(),
            "state": state,
            "assignee": assignee or "",
            "kind": (block_kind or event_kind or "").strip(),
            "created_at": int(created_at or 0),
            "blocked_at": int(blocked_at or 0),
            "wait": human_age(now - int(blocked_at)) if blocked_at else human_age(now - int(created_at or 0)),
            "runs": int(runs or 0),
            "failures": int(failures or 0),
            "spent": used,
            "budget": budget,
            "decision": decision_text(decision_payload),
            "reason": (reason[:REASON_CHARS] + (" ..." if len(reason) > REASON_CHARS else "")) or NO_REASON,
        })
    return out


def render(cards, state, card):
    what = "card %s" % card if card else "state %s" % state
    if not cards:
        return "diagnose: 0 card(s) in %s" % what
    lines = ["diagnose: %d card(s) in %s" % (len(cards), what), ""]
    for c in cards:
        wait = ("   wait: %s" % c["wait"]) if c["wait"] else ""
        lines.append("id: %s   state: %s   assignee: %s   kind: %s%s"
                     % (c["id"], c["state"], c["assignee"] or "-", c["kind"] or "-", wait))
        lines.append("  title: %s" % c["title"])
        lines.append("  reason: %s" % c["reason"])
        lines.append("  runs: %d   failures: %d   tokens: %d/%d"
                     % (c["runs"], c["failures"], c["spent"], c["budget"]))
        if c["decision"]:
            lines.append("  coordinator: %s" % c["decision"])
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cards in one board state, with the reason they are there.")
    ap.add_argument("--state", default="blocked",
                    help="one of %s (default blocked)" % "|".join(STATES))
    ap.add_argument("--card", default=None, help="one card id, whatever state it is in")
    ap.add_argument("--json", action="store_true", help="the same result as data")
    args = ap.parse_args(argv)

    state = (args.state or "blocked").strip().lower()
    if not args.card and state not in STATES:
        print("unknown state %r: %s" % (state, "|".join(STATES)))
        return 1

    rows = board_rows(None if args.card else state, args.card)
    if rows is None:
        print("no board to read: HERMES_KANBAN_DB, KANBAN_DB and %s are all missing"
              % os.path.join(base_home(), "kanban.db"))
        return 2

    cards = cards_from_rows(rows)
    if args.json:
        print(json.dumps({"state": state, "card": args.card, "count": len(cards), "cards": cards},
                         indent=2))
    else:
        print(render(cards, state, args.card))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
