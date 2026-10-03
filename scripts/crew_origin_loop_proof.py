#!/usr/bin/env python3
"""Proof that the session which kicked a brief off stays in the loop, even for cards it never opened.

A card the decomposer creates under a crew card has no body of its own, so without inheritance the
chat (or the session) that started the brief never hears that its child is stuck:

  1. a card's own origin record wins over anything inherited
  2. a card with no record of its own takes the origin of the card it came from
  3. that inheritance crosses the decomposer's own from_decompose_of link
  4. a chat-less origin (a CLI session) is still recorded, and the alert names the session
  5. the notifier resolves the same inherited origin, so the alert reaches the origin chat
  6. a stale permission/quota error that holds a card in the ready lane can be lifted

Run:  python3 crew_origin_loop_proof.py
Exit: 0 when every check passes, 1 otherwise.
"""
import importlib.util
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_card  # noqa: E402 - reads env on each call, so a top-level import is safe
import crew_proof_board  # noqa: E402
KANBAN_DB = crew_proof_board.proof_db()
ROOT = "t" + "9or" + "igin_root"
CHILD = "t" + "9or" + "igin_child"
GRAND = "t" + "9or" + "igin_grand"
SOLO = "t" + "9or" + "igin_solo"
HELD = "t" + "9or" + "igin_held"
ORIGIN = "zulip:stream:Kanban|chat that kicked off the brief"
SESSION = "20260928_161919_026dbd"
FAILS = []


def check(name, ok, detail=""):
    print("%-58s %s  %s" % (name, "PASS" if ok else "FAIL", str(detail)[:80]))
    if not ok:
        FAILS.append(name)


def seed():
    now = int(time.time())
    conn = sqlite3.connect(KANBAN_DB)
    try:
        for cid in (ROOT, CHILD, GRAND, SOLO, HELD):
            conn.execute("delete from task_runs where task_id = ?", (cid,))
            conn.execute("delete from task_events where task_id = ?", (cid,))
            conn.execute("delete from task_links where child_id = ? or parent_id = ?", (cid, cid))
            conn.execute("delete from tasks where id = ?", (cid,))
        for cid, title in ((ROOT, "PROBE origin root"), (CHILD, "PROBE origin child"),
                           (GRAND, "PROBE origin grandchild"), (SOLO, "PROBE origin solo"),
                           (HELD, "PROBE origin held")):
            conn.execute("insert into tasks (id, title, body, status, assignee, priority, created_at, "
                         "workspace_kind, workspace_path) values (?,?,?,?,?,0,?,?,?)",
                         (cid, title, "Goal: probe\n", "ready", "crew-worker", now,
                          "scratch", os.path.join(crew_card.base_home(), "kanban", "workspaces", cid)))
        # the chat's card carries the origin; the decomposer's children carry only their lineage
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)",
                     (ROOT, None, "origin",
                      json.dumps({"origin": ORIGIN, "platform": "zulip",
                                  "chat": "stream:Kanban|chat that kicked off the brief",
                                  "session": SESSION, "by": crew_card.owner_profile(), "ts": now}), now))
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)",
                     (CHILD, None, "created", json.dumps({"by": "auto-decomposer",
                                                          "from_decompose_of": ROOT}), now))
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)",
                     (GRAND, None, "created", json.dumps({"by": "auto-decomposer",
                                                          "from_decompose_of": CHILD}), now))
        conn.execute("insert into task_links (parent_id, child_id) values (?,?)", (ROOT, CHILD))
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)",
                     (SOLO, None, "origin",
                      json.dumps({"origin": "", "platform": "cli", "chat": "", "session": SESSION,
                                  "chat_type": "", "by": crew_card.owner_profile(), "ts": now}), now))
        conn.execute("update tasks set last_failure_error = ? where id = ?",
                     ("workspace: [Errno 13] Permission denied: '/home/nobody/Landing Page'", HELD))
        conn.commit()
    finally:
        conn.close()


def drop():
    conn = sqlite3.connect(KANBAN_DB)
    try:
        for cid in (ROOT, CHILD, GRAND, SOLO, HELD):
            conn.execute("update tasks set status = 'archived' where id = ?", (cid,))
        conn.commit()
    finally:
        conn.close()


def main():
    import crew_card

    seed()
    own, src, hops = crew_card.origin_of(ROOT)
    check("a card's own origin record is used", own.get("origin") == ORIGIN and hops == 0,
          "origin=%s hops=%s" % (own.get("origin"), hops))

    found, src, hops = crew_card.origin_of(CHILD)
    check("a card with no record inherits its parent's origin",
          found.get("origin") == ORIGIN and src == ROOT and hops >= 1,
          "origin=%s from=%s hops=%s" % (found.get("origin"), src, hops))

    gfound, gsrc, ghops = crew_card.origin_of(GRAND)
    check("inheritance crosses the decomposer's own link",
          gfound.get("origin") == ORIGIN and bool(gfound.get("inherited")),
          "origin=%s from=%s hops=%s" % (gfound.get("origin"), gsrc, ghops))

    sfound, _ssrc, _sh = crew_card.origin_of(SOLO)
    check("a chat-less session is still recorded as the origin",
          not sfound.get("origin") and sfound.get("session") == SESSION,
          "session=%s origin=%r" % (sfound.get("session"), sfound.get("origin")))

    import crew_notify
    r_origin, r_src = crew_notify.resolved_origin(KANBAN_DB, GRAND)
    check("the notifier resolves the same inherited origin",
          r_origin == ORIGIN, "origin=%s from=%s" % (r_origin, r_src))
    check("a chat-less session has no send target", not crew_notify.send_target(
        crew_notify.resolved_origin(KANBAN_DB, SOLO)[0]))

    conn = sqlite3.connect("file:%s?mode=ro" % KANBAN_DB, uri=True)
    try:
        before = conn.execute("select last_failure_error from tasks where id = ?", (HELD,)).fetchone()[0]
    finally:
        conn.close()
    released = crew_card.release_hold(HELD)
    conn = sqlite3.connect("file:%s?mode=ro" % KANBAN_DB, uri=True)
    try:
        after = conn.execute("select last_failure_error from tasks where id = ?", (HELD,)).fetchone()[0]
    finally:
        conn.close()
    check("a stale hold can be lifted", released and bool(before) and after is None,
          "before=%r after=%r" % ((before or "")[:30], after))

    drop()
    if FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("PROOF OK: the origin of a card - chat or session - is recorded, inherited by the cards "
          "created under it, and used by the notifier, so the loop closes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
