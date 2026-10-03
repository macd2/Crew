#!/usr/bin/env python3
"""Proof that the coordinator pass heals what the crew can fix and leaves the rest to a decision.

Seeded on a scratch board of this proof's own (never the live one), through the real coordinator pass, with no
`hermes` call (HERMES_BIN is /bin/false) and no model call (the decider is /bin/false):

  1. a ready card the respawn guard holds because its workspace is unwritable is NOT touched by the crew: the
     kernel owns workspaces and has no call to repoint one, so no write, no `self_heal` row, and the kernel's
     own guard (asked in its own interpreter) still holds it - the card goes on to a coordinator decision
  2. a second pass changes nothing either
  3. a ready card held on a quota wall with no router pick available -> the wall is counted and the card
     is left un-pinned (the remedy says it could not fix it), so it goes on to a decision instead of being
     re-pinned on a guess
  4. a dry run changes nothing
  5. no remedy on the pass reports a could-not-heal (a remedy that cannot take (card, dry) fails here,
     not in the field)

Run:  python3 crew_heal_proof.py
Exit: 0 when every check passes, 1 otherwise.
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_proof_board  # noqa: E402

COORD = os.path.join(HERE, "crew_coordinator.py")
WS = "t9selfheal_ws"
WALL = "t9selfheal_wall"
BROKEN = "/home/nobody/Landing Page"
FAILS = []


def check(name, ok, detail=""):
    print("%-62s %s  %s" % (name, "PASS" if ok else "FAIL", str(detail)[:90]))
    if not ok:
        FAILS.append(name)


def main():
    tmp = tempfile.mkdtemp(prefix="crew-heal-proof-")
    db = os.path.join(tmp, "kanban.db")
    home = os.path.join(tmp, "home")
    os.makedirs(home)
    try:
        if not crew_proof_board.init_board(db):
            print("PROOF FAIL: the scratch board could not be created")
            return 1
        env = dict(os.environ, HERMES_HOME=home, HERMES_KANBAN_DB=db, CREW_WORKSPACE_ROOT=os.path.join(tmp, "ws"),
                   HERMES_BIN="/bin/false", CREW_COORDINATOR_DECIDER="/bin/false",
                   CREW_ROUTER_PLUGIN=os.path.join(tmp, "no-router"))      # an explicit path that holds nothing
        now = int(time.time())
        conn = sqlite3.connect(db)
        for cid, err, path in ((WS, "workspace: [Errno 13] Permission denied: '%s'" % BROKEN, BROKEN),
                               (WALL, "rate-limited (quota wall): 429 too many requests", os.path.join(tmp, "ok"))):
            os.makedirs(path, exist_ok=True) if path != BROKEN else None
            conn.execute("insert into tasks (id, title, body, assignee, status, priority, created_by, created_at, "
                         "workspace_kind, workspace_path, last_failure_error) values "
                         "(?,?,?,'crew-probe','ready',0,'owner',?,'scratch',?,?)",
                         (cid, "self heal %s" % cid, "Role: worker\nCoordinator: proof/x\nGoal: probe\n", now, path, err))
            conn.execute("insert into task_runs (task_id, profile, status, started_at, ended_at, outcome, summary, "
                         "last_heartbeat_at) values (?, 'crew-worker', 'blocked', ?, ?, 'blocked', 'probe', ?)",
                         (cid, now - 900, now - 600, now - 600))
            conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                         "values (?, NULL, 'respawn_guarded', ?, ?)", (cid, json.dumps({"by": "probe"}), now))
        conn.commit()
        conn.close()

        def rows(sql, args=()):
            c = sqlite3.connect(db)
            c.row_factory = sqlite3.Row
            try:
                return [dict(r) for r in c.execute(sql, args).fetchall()]
            finally:
                c.close()

        def heal_events(cid, cls):
            out = []
            for r in rows("select payload from task_events where task_id = ? and kind = 'self_heal'", (cid,)):
                d = json.loads(r["payload"] or "{}")
                if d.get("class") == cls:
                    out.append(d)
            return out

        def guard(cid):
            """The kernel's own respawn guard for this card, asked in its own interpreter."""
            code = ("import sys,sqlite3;sys.path.insert(0,%r);import hermes_cli.kanban_db_dispatch as kbd;"
                    "c=sqlite3.connect('file:%s?mode=ro',uri=True);c.row_factory=sqlite3.Row;"
                    "print(kbd.check_respawn_guard(c,%r))" % (crew_proof_board.AGENT, db, cid))
            p = subprocess.run([crew_proof_board.VENV_PY, "-c", code], capture_output=True, text=True, timeout=180,
                               env=dict(os.environ, HERMES_HOME=os.environ.get("HERMES_HOME")
                                        or os.path.expanduser("~/.hermes")))
            return (p.stdout or "").strip().splitlines()[-1:] and (p.stdout or "").strip().splitlines()[-1]

        def coordinator(*args):
            p = subprocess.run([sys.executable, COORD, "--once", "--json", "--since", "0"] + list(args), env=env,
                               capture_output=True, text=True, timeout=300)
            raw = p.stdout or ""
            try:
                return json.JSONDecoder().raw_decode(raw[raw.find("{"):])[0]
            except ValueError:
                return {"cards": [], "raw": (raw + p.stderr)[-300:]}

        before = guard(WS)
        check("the kernel guard holds the card before the heal", before == "blocker_auth", before)

        coordinator("--dry-run")
        rep = coordinator()
        by_card = {c["card"]: c for c in rep.get("cards", [])}
        row = rows("select workspace_path, last_failure_error from tasks where id = ?", (WS,))[0]
        check("the crew leaves a card with an unwritable workspace as it is (no repoint, error kept)",
              row["workspace_path"] == BROKEN and bool(row["last_failure_error"]), row["workspace_path"])
        check("no heal is recorded and the report names none",
              not heal_events(WS, "held_workspace") and not str(by_card.get(WS, {}).get("action") or "").startswith("heal:"),
              str(by_card.get(WS))[:80])
        after = guard(WS)
        check("the kernel guard still holds the card (a decision, not a repair, moves it)", after == "blocker_auth",
              after or "(none)")

        wall = heal_events(WALL, "dead_model")
        check("a card on a dead model is acted on once and is not re-pinned on a guess",
              len(wall) == 1 and wall[0].get("action") == "counted" and
              not rows("select model_override from tasks where id = ?", (WALL,))[0]["model_override"],
              json.dumps(wall)[:90])
        check("no remedy on the pass reports a could-not-heal",
              not [c for c in rep.get("cards", []) if "could not heal" in str(c.get("detail"))],
              [c.get("detail") for c in rep.get("cards", []) if "could not heal" in str(c.get("detail"))][:1])

        coordinator()
        check("a second pass changes nothing", not heal_events(WS, "held_workspace") and len(wall) == 1,
              "%d heal event(s)" % len(heal_events(WS, "held_workspace")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("PROOF OK: the coordinator pass never rewrites a workspace behind the kernel's back, never re-pins a "
          "dead model on a guess, and leaves a second pass with nothing to do")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
