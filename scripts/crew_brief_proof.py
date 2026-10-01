#!/usr/bin/env python3
"""Proof that the card view opens with the owner's brief, above the coordinator card.

The page must read from the /crew invocation to the close-out, so the owner's own words sit in a
brief card on top of the coordinator root, with the coordinator under it:

  1. a card whose brief was recorded shows a brief node as the root, layer 0, with the coordinator
     on the layer below and an edge brief -> coordinator
  2. the brief text is the owner's own text, and its source is named
  3. an older card with no recorded brief falls back to its own Goal line, and says so
  4. a card with neither shows no brief node at all (nothing is invented)
  5. crew_card.py open --brief is what records it (the row it writes is what the page reads)

Seed cards are written straight into kanban.db and archived afterwards, so any agent context can
run this. HTTP only: the page's own /card/<id>.json is what is checked.

Run:  python3 crew_brief_proof.py
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
WITH_BRIEF = "t" + "9br" + "ief_now"
GOAL_ONLY = "t" + "9br" + "ief_goal"
BARE = "t" + "9br" + "ief_bare"
OWNER_WORDS = "make the card view show the whole story from me invoking crew to done"
FAILS = []


def check(name, ok, detail=""):
    print("%-58s %s  %s" % (name, "PASS" if ok else "FAIL", str(detail)[:84]))
    if not ok:
        FAILS.append(name)


def card_json(card):
    with urllib.request.urlopen("%s/card/%s.json" % (BASE, card), timeout=20) as fh:
        return json.loads(fh.read().decode())


def node_of(graph, kind):
    for n in (graph or {}).get("nodes", []):
        if n.get("kind") == kind:
            return n
    return None


def seed():
    now = int(time.time())
    conn = sqlite3.connect(KANBAN_DB)
    try:
        for cid in (WITH_BRIEF, GOAL_ONLY, BARE):
            conn.execute("delete from task_runs where task_id = ?", (cid,))
            conn.execute("delete from task_events where task_id = ?", (cid,))
            conn.execute("delete from tasks where id = ?", (cid,))
        bodies = {
            WITH_BRIEF: "Goal: %s\n\nArtifact: the served card page\n" % OWNER_WORDS,
            GOAL_ONLY: "Goal: ship the columned top area\n\nArtifact: the served card page\n",
            BARE: "no goal line here at all\n",
        }
        for cid, body in bodies.items():
            conn.execute("insert into tasks (id, title, body, status, assignee, priority, created_at) "
                         "values (?,?,?,?,?,0,?)",
                         (cid, "PROBE brief %s" % cid[-4:], body, "done", "crew-worker", now - 300))
            conn.execute("insert into task_runs (task_id, profile, status, started_at, ended_at, outcome) "
                         "values (?,?,?,?,?,?)",
                         (cid, "crew-worker", "done", now - 240, now - 60, "completed"))
            conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                         "values (?,?,?,?,?)",
                         (cid, None, "created", json.dumps({"parents": [], "assignee": "crew-worker"}),
                          now - 300))
        conn.commit()
    finally:
        conn.close()


def drop():
    conn = sqlite3.connect(KANBAN_DB)
    try:
        for cid in (WITH_BRIEF, GOAL_ONLY, BARE):
            conn.execute("update tasks set status = 'archived' where id = ?", (cid,))
        conn.commit()
    finally:
        conn.close()


def record_via_cli_path(card_id, text):
    """Use crew_card.py's own writer, so this check covers the --brief path, not just the view."""
    import crew_card
    return crew_card.record_brief(card_id, text, source="owner", origin="cli:probe")


def main():
    seed()
    recorded = record_via_cli_path(WITH_BRIEF, OWNER_WORDS)
    check("crew_card.py records the brief it is given", bool(recorded))
    try:
        graph = card_json(WITH_BRIEF)
        brief = node_of(graph, "brief")
        card_node = node_of(graph, "card")
        check("a recorded brief is a node on the page", brief is not None,
              "kinds: %s" % [n.get("kind") for n in graph.get("nodes", [])])
        check("the brief is the root of the page", brief and graph.get("root") == brief.get("id"),
              "root=%s brief=%s" % (graph.get("root"), (brief or {}).get("id")))
        check("the brief sits above the coordinator card",
              brief is not None and card_node is not None and
              int(brief.get("layer") or 0) < int(card_node.get("layer") or 0),
              "brief layer=%s card layer=%s" % ((brief or {}).get("layer"), (card_node or {}).get("layer")))
        check("the brief -> coordinator edge exists",
              any(e.get("from") == (brief or {}).get("id") and e.get("to") == (card_node or {}).get("id")
                  for e in graph.get("edges", [])))
        check("the owner's own words are shown",
              OWNER_WORDS in json.dumps(brief.get("brief") or {}) if brief else False,
              (brief or {}).get("brief", {}).get("text", "")[:60] if brief else "")
        check("the brief names its source", (brief or {}).get("brief", {}).get("source") == "owner",
              (brief or {}).get("brief", {}).get("source"))

        goal_graph = card_json(GOAL_ONLY)
        gb = node_of(goal_graph, "brief")
        check("an older card falls back to its Goal line", gb is not None
              and "columned top area" in json.dumps(gb.get("brief") or {}),
              (gb or {}).get("brief", {}).get("text", "")[:50] if gb else "no brief node")
        check("a fallback brief says it came from the card",
              bool(gb) and (gb.get("brief") or {}).get("source") == "card goal",
              (gb or {}).get("brief", {}).get("source"))

        # the sidebar carries the same brief, in full
        with urllib.request.urlopen("%s/card/%s" % (BASE, WITH_BRIEF), timeout=20) as fh:
            page = fh.read().decode("utf-8", "replace")
        import html as _h
        block = page.split('id="briefsec"', 1)[-1].split("</div>", 3)
        body = block[0] if block else ""
        check("the sidebar carries the brief block", 'id="briefText"' in page and "hidden" not in body[:40],
              body[:60])
        check("the sidebar shows the owner's words in full",
              _h.escape(OWNER_WORDS) in page, OWNER_WORDS[:40])
        check("the sidebar names the brief's source",
              "the owner&#x27;s words" in page or "the owner's words" in page)

        with urllib.request.urlopen("%s/card/%s" % (BASE, GOAL_ONLY), timeout=20) as fh:
            goal_page = fh.read().decode("utf-8", "replace")
        check("the sidebar marks a fallback brief as the GOAL line",
              "GOAL line" in goal_page and "no brief was recorded" in goal_page)

        with urllib.request.urlopen("%s/card/%s" % (BASE, BARE), timeout=20) as fh:
            bare_page = fh.read().decode("utf-8", "replace")
        bare_block = bare_page.split('id="briefsec"', 1)[-1][:40]
        check("a card with no brief hides the sidebar block", "hidden" in bare_block, bare_block[:40])

        bare_graph = card_json(BARE)
        check("a card with no brief and no goal shows no brief node",
              node_of(bare_graph, "brief") is None,
              "kinds: %s" % [n.get("kind") for n in bare_graph.get("nodes", [])])
    except Exception as exc:
        print("PROOF FAIL: could not read the page (%s)" % exc)
        return 1
    finally:
        drop()
    if FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("PROOF OK: the owner's brief is the root of the card page, the coordinator sits under it, "
          "and a card without one says where its line came from")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
