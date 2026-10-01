#!/usr/bin/env python3
"""Proof that a retried card's worker is handed the work already done (nothing is redone).

A card's runs are separate sessions and the model can change between attempts (the router picks per
card), so the work must travel with the card, not with the model:

  1. a card on its first run gets no hand-off (nothing is invented)
  2. a card with prior runs gets every run's outcome and summary
  3. the workspace path and what is actually in it are named
  4. the card's notes are carried over
  5. the block is recorded once per card, not once per turn
  6. the worker hook injects it once per session, and only for a card that ran before

Run:  python3 crew_handoff_proof.py
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
import crew_proof_board  # noqa: E402
KANBAN_DB = crew_proof_board.proof_db()
FRESH = "t" + "9ho" + "ff_fresh"
OLD = "t" + "9ho" + "ff_old"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402 - the owner profile, the base home and the package checkout
WS = os.path.join(crew_card.owner_home(), "cache", "scratch", "handoff_ws_probe")
PLUGIN = os.path.join(crew_card.profile_home("crew-worker"), "plugins", "crew", "__init__.py")
FAILS = []


def check(name, ok, detail=""):
    print("%-58s %s  %s" % (name, "PASS" if ok else "FAIL", str(detail)[:80]))
    if not ok:
        FAILS.append(name)


def seed():
    now = int(time.time())
    os.makedirs(WS, exist_ok=True)
    with open(os.path.join(WS, "already-built.txt"), "w") as fh:
        fh.write("work from the earlier run\n")
    conn = sqlite3.connect(KANBAN_DB)
    try:
        for cid in (FRESH, OLD):
            conn.execute("delete from task_runs where task_id = ?", (cid,))
            conn.execute("delete from task_events where task_id = ?", (cid,))
            conn.execute("delete from task_comments where task_id = ?", (cid,))
            conn.execute("delete from tasks where id = ?", (cid,))
        conn.execute("insert into tasks (id, title, body, status, assignee, priority, created_at, "
                     "workspace_kind, workspace_path) values (?,?,?,?,?,0,?,?,?)",
                     (FRESH, "PROBE handoff fresh", "Goal: nothing done yet\n", "ready",
                      "crew-worker", now, "scratch", WS))
        conn.execute("insert into tasks (id, title, body, status, assignee, priority, created_at, "
                     "workspace_kind, workspace_path) values (?,?,?,?,?,0,?,?,?)",
                     (OLD, "PROBE handoff old", "Goal: continue the package work\n", "ready",
                      "crew-worker", now - 3600, "scratch", WS))
        conn.execute("insert into task_runs (task_id, profile, status, started_at, ended_at, outcome, "
                     "summary) values (?,?,?,?,?,?,?)",
                     (OLD, "crew-worker", "blocked", now - 3000, now - 2900, "blocked",
                      "committed the package scaffolding and pushed it to ops/hermes-crew"))
        conn.execute("insert into task_runs (task_id, profile, status, started_at, ended_at, outcome, "
                     "summary) values (?,?,?,?,?,?,?)",
                     (OLD, "crew-verifier", "done", now - 1000, now - 900, "completed",
                      "ran the ten proof scripts: 9 pass, 1 fails on the missing md5 step"))
        conn.execute("insert into task_comments (task_id, author, body, created_at) values (?,?,?,?)",
                     (OLD, crew_card.owner_profile(), "keep the pinned proof filenames, they are referenced "
                                               "by install.py", now - 800))
        conn.commit()
    finally:
        conn.close()


def drop():
    conn = sqlite3.connect(KANBAN_DB)
    try:
        for cid in (FRESH, OLD):
            conn.execute("update tasks set status = 'archived' where id = ?", (cid,))
        conn.commit()
    finally:
        conn.close()


def run_hook(session_id, card, turns=1):
    """The real hook, in one process (its once-per-session guard lives in the worker's own process)."""
    code = (
        "import importlib.util, json, os\n"
        "spec = importlib.util.spec_from_file_location('crew_plugin', %r)\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(m)\n"
        "out = [m.crew_handoff_hook(user_message='go', session_id=%r) for _ in range(%d)]\n"
        "print(json.dumps(out))\n" % (PLUGIN, session_id, turns))
    env = dict(os.environ, HERMES_HOME=crew_card.profile_home("crew-worker"),
               HERMES_KANBAN_TASK=card, HERMES_KANBAN_RUN_ID="999", KANBAN_DB=KANBAN_DB)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120,
                       env=env, cwd=HERE)
    try:
        out = json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception:
        return [{"_error": (r.stderr or r.stdout or "")[-160:]}]
    return out if isinstance(out, list) else [out]


def main():
    import crew_handoff

    seed()
    fresh = crew_handoff.handoff_text(FRESH)
    check("a card on its first run gets no hand-off", fresh == "", repr(fresh[:40]))

    text = crew_handoff.handoff_text(OLD)
    check("a card with prior runs gets a hand-off", bool(text), text[:60])
    check("every prior run is named with its outcome",
          "committed the package scaffolding" in text and "ran the ten proof scripts" in text
          and "blocked" in text and "done" in text)
    check("the hand-off says not to redo the work",
          "do not redo" in text.lower() and "keep every artifact" in text.lower())
    check("the workspace and its real contents are named",
          WS in text and "already-built.txt" in text, [l for l in text.splitlines() if WS in l][:1])
    check("the card's own notes are carried over", "referenced" in text and "install.py" in text)

    calls = run_hook("sessionA", OLD, turns=2)     # two turns of one worker session
    first = calls[0] if calls else None
    second = calls[1] if len(calls) > 1 else None
    third = run_hook("sessionB", FRESH, turns=1)[0]
    check("the worker hook injects the hand-off", bool((first or {}).get("context")),
          str(first)[:60])
    check("it is injected once per session, not every turn", second is None or second == {},
          str(second)[:40])
    check("a first-run card is not handed anything", third is None or third == {}, str(third)[:40])
    check("the injected block is the same text the builder makes",
          ((first or {}).get("context") or "").strip() == text.strip())

    conn = sqlite3.connect(KANBAN_DB)
    try:
        n = conn.execute("select count(*) from task_events where task_id = ? and kind = 'handoff'",
                         (OLD,)).fetchone()[0]
    finally:
        conn.close()
    check("the hand-off is noted on the card once, for that run", n == 1,
          "%d row(s) for run 999" % n)

    r = subprocess.run([sys.executable, os.path.join(HERE, "crew_handoff.py"), "--card", OLD,
                        "--record"], capture_output=True, text=True, timeout=60)
    conn = sqlite3.connect(KANBAN_DB)
    try:
        n2 = conn.execute("select count(*) from task_events where task_id = ? and kind = 'handoff'",
                          (OLD,)).fetchone()[0]
    finally:
        conn.close()
    subprocess.run([sys.executable, os.path.join(HERE, "crew_handoff.py"), "--card", OLD, "--record"],
                   capture_output=True, text=True, timeout=60)
    conn = sqlite3.connect(KANBAN_DB)
    try:
        n3 = conn.execute("select count(*) from task_events where task_id = ? and kind = 'handoff'",
                          (OLD,)).fetchone()[0]
    finally:
        conn.close()
    check("--record notes it once, and does not repeat itself",
          r.returncode == 0 and n2 == n + 1 and n3 == n2,
          "after first=%d after second=%d (before=%d)" % (n2, n3, n))
    drop()
    if FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("PROOF OK: a retried card hands its worker the previous runs' work - the workspace, the "
          "notes and every run's outcome - once per session")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
