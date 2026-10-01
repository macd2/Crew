#!/usr/bin/env python3
"""Proof that a card page carries its children where they belong, however they were linked.

The board's card view draws a card's children from task_links, and only when a child has exactly
one parent. Two normal cases fell out of that rule:

  * the gateway's auto-decomposer creates children with no parent link at all and then links them
    as parents of the card it decomposed (so the card waits for them), which leaves the spawned
    card invisible on every page
  * a card created with one parent can gain more parents later the same way, which hides it from
    the card that spawned it

This pins that both are drawn: a card spawned by decomposition appears on the page of the card it
came from, and a card born under this card stays there after extra parents are added. A card with
no relation to this one must not appear.

Seed cards are written straight into kanban.db (no crew_card.py open) and archived afterwards, so
any agent context can run this. HTTP only: the page's own /card/<id>.json is the thing checked.

Run:  python3 crew_child_link_proof.py
Exit: 0 when every check passes, 1 otherwise.
"""
import json
import os
import sqlite3
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_proof_board  # noqa: E402
KANBAN_DB = crew_proof_board.proof_db()
BASE = crew_proof_board.graph_base()
PARENT = "t" + "9b" + "0rn_parent"
SPAWNED = "t" + "9b" + "0rn_spawned"
BORN = "t" + "9b" + "0rn_born"
STRANGER = "t" + "9b" + "0rn_stranger"
OUTSIDER = "t" + "9b" + "0rn_out"
FAILS = []


def check(name, ok, detail=""):
    print("%-58s %s  %s" % (name, "PASS" if ok else "FAIL", str(detail)[:80]))
    if not ok:
        FAILS.append(name)


def card_json(card):
    with urllib.request.urlopen("%s/card/%s.json" % (BASE, card), timeout=20) as fh:
        return json.loads(fh.read().decode())


def card_nodes(graph):
    return [n for n in (graph or {}).get("nodes", []) if n.get("kind") == "card"]


def seed():
    now = int(time.time())
    body = "Goal: probe child links.\nProof command: python3 crew_child_link_proof.py\n"
    conn = sqlite3.connect(KANBAN_DB)
    try:
        for cid in (PARENT, SPAWNED, BORN, STRANGER, OUTSIDER):
            conn.execute("delete from task_runs where task_id = ?", (cid,))
            conn.execute("delete from task_events where task_id = ?", (cid,))
            conn.execute("delete from tasks where id = ?", (cid,))
        for cid, status in ((PARENT, "done"), (SPAWNED, "done"), (BORN, "done"), (STRANGER, "done"),
                            (OUTSIDER, "done")):
            conn.execute("insert into tasks (id, title, body, status, assignee, priority, created_at) "
                         "values (?,?,?,?,?,0,?)",
                         (cid, "PROBE child link %s" % cid[-6:], body, status, "crew-worker", now - 300))
            conn.execute("insert into task_runs (task_id, profile, status, started_at, ended_at, outcome) "
                         "values (?,?,?,?,?,?)",
                         (cid, "crew-worker", "done", now - 240, now - 60, "completed"))
        # the spawned card: created by decomposing PARENT, linked to no parent at all
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values (?,?,?,?,?)",
                     (SPAWNED, None, "created",
                      json.dumps({"by": "auto-decomposer", "from_decompose_of": PARENT}), now - 300))
        # the born card: created with PARENT as its only parent, then given a second parent later
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values (?,?,?,?,?)",
                     (BORN, None, "created", json.dumps({"parents": [PARENT], "assignee": "crew-worker"}),
                      now - 300))
        conn.execute("insert into task_links (parent_id, child_id) values (?,?)", (OUTSIDER, BORN))
        # the stranger: no relation to PARENT
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values (?,?,?,?,?)",
                     (STRANGER, None, "created", json.dumps({"parents": [], "assignee": "crew-worker"}),
                      now - 300))
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values (?,?,?,?,?)",
                     (OUTSIDER, None, "created", json.dumps({"parents": [], "assignee": "crew-worker"}),
                      now - 300))
        conn.commit()
    finally:
        conn.close()


def drop():
    conn = sqlite3.connect(KANBAN_DB)
    try:
        for cid in (PARENT, SPAWNED, BORN, STRANGER, OUTSIDER):
            conn.execute("update tasks set status = 'archived' where id = ?", (cid,))
            conn.execute("delete from task_links where child_id = ? or parent_id = ?", (cid, cid))
        conn.commit()
    finally:
        conn.close()


def newest_decomposed():
    """(origin, child) of the newest card this board says it decomposed, or (None, None)."""
    conn = sqlite3.connect(KANBAN_DB)
    try:
        rows = conn.execute(
            "select task_id, payload from task_events where kind = 'created' "
            "and payload like '%from_decompose_of%' order by created_at desc limit 40").fetchall()
        for tid, payload in rows:
            try:
                rec = json.loads(payload or "{}")
            except (TypeError, ValueError):
                continue
            origin = rec.get("from_decompose_of")
            if not origin:
                continue
            alive = conn.execute("select count(*) from tasks where id = ? and status != 'archived'",
                                 (tid,)).fetchone()[0]
            ok_origin = conn.execute("select count(*) from tasks where id = ? and status != 'archived'",
                                     (origin,)).fetchone()[0]
            if alive and ok_origin:
                return origin, tid
    finally:
        conn.close()
    return None, None


def main():
    seed()
    try:
        try:
            graph = card_json(PARENT)
        except Exception as exc:
            print("PROOF FAIL: the card page is not reachable at %s (%s)" % (BASE, exc))
            return 1
        ids = [n.get("label") for n in card_nodes(graph)]
        check("a card spawned by decomposition is drawn under its origin", SPAWNED in ids,
              "cards on the page: %s" % ids)
        check("a card born here stays after later extra parents", BORN in ids,
              "cards on the page: %s" % ids)
        check("an unrelated card is not drawn", STRANGER not in ids, "cards on the page: %s" % ids)
        edges = ["%s->%s" % (e.get("from"), e.get("to")) for e in (graph or {}).get("edges", [])]
        card_ids = [n.get("id") for n in card_nodes(graph) if n.get("label") == PARENT]
        check("the spawned card hangs off the coordinator card by an edge",
              any(e.get("from") in card_ids and e.get("to") == "card:" + SPAWNED
                  for e in (graph or {}).get("edges", [])),
              "card nodes=%s edges=%s" % (card_ids, edges[:6]))

        origin, child = newest_decomposed()
        if origin and child:
            live = card_json(origin)
            live_ids = [n.get("label") for n in card_nodes(live)]
            check("a real decomposed card is drawn on its origin's page", child in live_ids,
                  "%s on %s: %s" % (child, origin, child in live_ids))
        else:
            check("a real decomposed card exists to check", False, "none found")
    finally:
        drop()
    if FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("PROOF OK: a card page draws the children it spawned and the children it was born with, "
          "and leaves unrelated cards off")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
