#!/usr/bin/env python3
"""The hand-off a retried card's worker gets: the work already done, so nothing is redone.

A card's runs are separate sessions, and a new run may start on a different model (the router's pick
can change between attempts). Without a hand-off the new worker re-explores everything the previous
one already did - the work is in the card's record, not in the model. This builds the compact block
that carries it: previous runs and how they ended, the last session id (so the worker can read the
transcript itself), the card's comments, the workspace path and what is in it, and the artifacts the
card already produced. Nothing is invented: every line comes from kanban.db or the filesystem.

Nothing to hand over (a card on its first run) prints nothing, and the caller injects nothing.
"""
import json
import os
import sqlite3
import sys
import time

KANBAN_DB = os.environ.get("KANBAN_DB", os.path.expanduser("~/.hermes/kanban.db"))
MAX_COMMENTS = 4
MAX_WORKSPACE_ENTRIES = 12


def _db():
    return sqlite3.connect("file:%s?mode=ro" % KANBAN_DB, uri=True)


def _rows(conn, sql, args=()):
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]
    except sqlite3.Error:
        return []


def workspace_state(path):
    """What is actually in the card's workspace right now."""
    if not path or not os.path.isdir(path):
        return "", 0
    names = sorted(os.listdir(path))[:MAX_WORKSPACE_ENTRIES]
    return ", ".join(names), len(os.listdir(path))


def handoff_text(card_id):
    """The hand-off block for a card with prior runs, or "" when there is nothing to hand over."""
    conn = _db()
    try:
        task = _rows(conn, "select id, title, status, workspace_kind, workspace_path, body "
                           "from tasks where id = ?", (card_id,))
        if not task:
            return ""
        task = task[0]
        runs = _rows(conn, "select id, profile, status, outcome, summary, error, started_at, ended_at "
                           "from task_runs where task_id = ? order by id", (card_id,))
        comments = _rows(conn, "select author, body, created_at from task_comments where task_id = ? "
                               "order by created_at desc limit ?", (card_id, MAX_COMMENTS))
        current = os.environ.get("HERMES_KANBAN_RUN_ID")
        done = [r for r in runs if r["id"] != _int_or_none(current)]
    finally:
        conn.close()
    if not done:
        return ""
    lines = ["[crew hand-off] This card has run before. Continue from what is below - do not redo "
             "finished work, and keep every artifact it already produced."]
    for r in done:
        how = (r["summary"] or r["error"] or "").strip().replace("\n", " ")
        dur = ""
        if r["started_at"] and r["ended_at"]:
            dur = " (%.0fs)" % max(0, r["ended_at"] - r["started_at"])
        lines.append("- run %s on %s: %s%s%s" % (r["id"], r["profile"] or "?", r["status"], dur,
                                                 (" - " + how[:240]) if how else ""))
    last = done[-1]
    if last.get("id"):
        lines.append("  its session transcript is reachable by the card id %s (run %s on profile %s)"
                     % (card_id, last["id"], last["profile"] or "?"))
    ws, n = workspace_state(task.get("workspace_path"))
    if task.get("workspace_path"):
        if ws:
            lines.append("workspace %s (%s) already holds %d entr%s: %s"
                         % (task["workspace_path"], task.get("workspace_kind") or "scratch", n,
                            "y" if n == 1 else "ies", ws))
        else:
            lines.append("workspace %s (%s) exists and is empty"
                         % (task["workspace_path"], task.get("workspace_kind") or "scratch"))
    for c in comments:
        body = (c["body"] or "").strip().replace("\n", " ")
        if body:
            lines.append("- note from %s: %s" % (c["author"] or "?", body[:200]))
    return "\n".join(lines)


def _int_or_none(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def record_handoff(card_id, text):
    """Note on the card that this run picked up the previous work (once per run, not per turn)."""
    run = _int_or_none(os.environ.get("HERMES_KANBAN_RUN_ID"))
    conn = sqlite3.connect(KANBAN_DB)
    try:
        dup = _rows(conn, "select 1 from task_events where task_id = ? and kind = 'handoff' "
                          "and json_extract(payload, '$.run') is ? limit 1", (card_id, run))
        if dup:
            return False
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)",
                     (card_id, run, "handoff",
                      json.dumps({"run": run, "chars": len(text or ""),
                                  "profile": os.environ.get("CREW_PROFILE") or "",
                                  "ts": time.time()}), int(time.time())))
        conn.commit()
    finally:
        conn.close()
    return True


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--card", required=True)
    ap.add_argument("--record", action="store_true", help="note the hand-off on the card")
    a = ap.parse_args()
    text = handoff_text(a.card)
    if text and a.record:
        record_handoff(a.card, text)
    sys.stdout.write(text + ("\n" if text else ""))
    return 0 if text else 1


if __name__ == "__main__":
    raise SystemExit(main())
