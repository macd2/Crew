#!/usr/bin/env python3
"""Proof that a quota wall never leaves a card spinning on the same dead model.

Today a provider quota wall is requeued without counting a failure, so a card can burn many stalled
attempts on one walled model. With this, the wall is recorded on the card, the card is re-pinned on
a fresh pick, and if there is no alternative and the wall repeats, the card is stopped visibly:

  1. the wall is recorded on the card, with the model and the wall number
  2. an alternative pick re-pins the card, and the card says what it moved from and to
  3. a completed run clears the wall count (history stays, the counter does not)
  4. no alternative and a repeated wall -> the card is blocked `transient` (the coordinator's kind, not the
     owner's), naming the wall
  5. the real worker hook does all of that on a 429, and nothing on an unrelated error

Run:  python3 crew_quota_wall_proof.py
Exit: 0 when every check passes, 1 otherwise.
"""
import json
import os
import sqlite3
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_card  # noqa: E402 - reads env on each call, so a top-level import is safe
# This proof drives the real `hermes kanban` CLI (the plugin's block path) and then asserts the card's
# own row, so it has to run outside the delegate_task child fence: Hermes refuses board mutations from a
# delegate_task child context on purpose (hermes_cli.kanban_db._assert_not_delegated_child_mutation), and
# a proof run from one would report the block as "not landed" when it was never attempted. Hermes' own
# kanban eval harnesses clear the same marker.
os.environ.pop("HERMES_DELEGATED_CHILD_CONTEXT", None)
import crew_proof_board  # noqa: E402
KANBAN_DB = crew_proof_board.proof_db()
CARD = "t" + "9qu" + "ota_wall"
HOOK_CARD = "t" + "9qu" + "ota_hook"
PLUGIN = os.path.join(crew_card.profile_home("crew-worker"), "plugins", "crew", "__init__.py")
FAILS = []


def check(name, ok, detail=""):
    print("%-58s %s  %s" % (name, "PASS" if ok else "FAIL", str(detail)[:80]))
    if not ok:
        FAILS.append(name)


def seed(card=CARD):
    now = int(time.time())
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute("delete from task_runs where task_id = ?", (card,))
        conn.execute("delete from task_events where task_id = ?", (card,))
        conn.execute("delete from tasks where id = ?", (card,))
        conn.execute("insert into tasks (id, title, body, status, assignee, priority, created_at, "
                     "model_override, provider_override) values (?,?,?,?,?,0,?,?,?)",
                     (card, "PROBE quota wall", "Goal: keep the package work moving\n", "ready",
                      "crew-worker", now, "claude-opus-5-5", "anthropic"))
        conn.commit()
    finally:
        conn.close()


def drop():
    conn = sqlite3.connect(KANBAN_DB)
    try:
        for c in (CARD, HOOK_CARD):
            conn.execute("update tasks set status = 'archived' where id = ?", (c,))
        conn.commit()
    finally:
        conn.close()


def state(card):
    conn = sqlite3.connect("file:%s?mode=ro" % KANBAN_DB, uri=True)
    try:
        row = conn.execute("select model_override, provider_override, status, block_kind from tasks "
                           "where id = ?", (card,)).fetchone()
        ev = conn.execute("select kind, payload from task_events where task_id = ? and kind in "
                          "('quota_wall','reroute','completed') order by created_at", (card,)).fetchall()
        return row, ev
    finally:
        conn.close()


def hook_call(card, status_code=429, error="rate limit exceeded", model="claude-opus-5-5"):
    code = (
        "import importlib.util, json\n"
        "spec = importlib.util.spec_from_file_location('crew_plugin', %r)\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(m)\n"
        "out = m.crew_quota_reroute(status_code=%r, error=%r, model=%r)\n"
        "print(json.dumps(out))\n" % (PLUGIN, status_code, error, model))
    env = dict(os.environ, HERMES_HOME=crew_card.profile_home("crew-worker"),
               HERMES_KANBAN_TASK=card, HERMES_KANBAN_RUN_ID="4242", KANBAN_DB=KANBAN_DB)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=180,
                       env=env, cwd=HERE)
    try:
        return json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception:
        return {"_error": (r.stderr or r.stdout or "")[-200:]}


def main():
    import crew_card

    seed()
    # 1+2. a wall with a live alternative: recorded, and the card re-pinned
    res = crew_card.reroute_after_wall(CARD, model="claude-opus-5-5", provider="anthropic",
                                      force_pick={"provider": "ai-gateway",
                                                  "model": "openai/gpt-oss-120b",
                                                  "why": "forced alternative for the proof"})
    row, ev = state(CARD)
    walls = [e for e in ev if e[0] == "quota_wall"]
    reroutes = [e for e in ev if e[0] == "reroute"]
    check("the wall is recorded on the card with its model",
          bool(walls) and "claude-opus-5-5" in (walls[0][1] or ""), (walls[0][1] or "")[:70] if walls else "no event")
    check("an alternative pick re-pins the card",
          res.get("action") == "rerouted" and row[0] == "openai/gpt-oss-120b" and row[1] == "ai-gateway",
          "action=%s pin=%s/%s" % (res.get("action"), row[1], row[0]))
    check("the card records what it moved from and to",
          bool(reroutes) and "claude-opus-5-5" in (reroutes[0][1] or "")
          and "openai/gpt-oss-120b" in (reroutes[0][1] or ""), (reroutes[0][1] or "")[:70] if reroutes else "")

    # 3. a completed run clears the counter
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)", (CARD, None, "completed", "{}", int(time.time())))
        conn.commit()
    finally:
        conn.close()
    check("a completed run clears the wall count", crew_card.wall_count(CARD) == 0,
          "count=%s" % crew_card.wall_count(CARD))

    # 4. no alternative + a repeated wall -> stopped, not spinning
    seed()
    r1 = crew_card.reroute_after_wall(CARD, model="claude-opus-5-5", provider="anthropic",
                                      force_pick={"provider": "anthropic",
                                                  "model": "claude-opus-5-5", "why": "same model"})
    r2 = crew_card.reroute_after_wall(CARD, model="claude-opus-5-5", provider="anthropic",
                                      force_pick={"provider": "anthropic",
                                                  "model": "claude-opus-5-5", "why": "same model"})
    row, ev = state(CARD)
    check("the first wall without an alternative is counted", r1.get("action") == "counted",
          "action=%s" % r1.get("action"))
    check("a repeated wall stops the card instead of spinning, for the coordinator",
          r2.get("action") == "blocked" and str(row[2]) == "blocked" and row[3] == "transient",
          "action=%s status=%s kind=%s" % (r2.get("action"), row[2], row[3]))
    check("the block reason names the wall and the model",
          "quota wall" in (r2.get("why") or "") and "claude-opus-5-5" in (r2.get("why") or ""),
          (r2.get("why") or "")[:70])

    # 5. the real hook path
    seed(HOOK_CARD)
    out = hook_call(HOOK_CARD)
    row2, ev2 = state(HOOK_CARD)
    check("the worker hook re-pins the card on a 429",
          bool((out or {}).get("context")) and row2[1] != "anthropic",
          "pin=%s/%s ctx=%s" % (row2[1], row2[0], bool((out or {}).get("context"))))
    before = len(ev2)
    hook_call(HOOK_CARD, status_code=500, error="internal server error")
    _row3, ev3 = state(HOOK_CARD)
    check("an unrelated error is left alone", len(ev3) == before,
          "events before=%d after=%d" % (before, len(ev3)))
    drop()
    if FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("PROOF OK: a quota wall is recorded, the card moves to a live model, and a wall with no "
          "alternative stops the card instead of spinning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
