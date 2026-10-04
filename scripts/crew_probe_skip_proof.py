#!/usr/bin/env python3
"""Proof that the coordinator pass leaves another run's probe card alone.

A proof seeds fixture cards with created_by='probe' and deletes them in a finally. The coordinator pass runs
on every dispatch tick, so a pass that acted on a fixture a proof was still asserting on made the proof fail
on its own probe, which reads as a defect in the change that shipped. crew_card owns the marker and the
filter; this proof shows both directions of it, on a scratch board of its own (never the live one):

  1. the dispatcher cannot claim a fixture card (its assignee is no Hermes profile)
  2. two blocked cards, one created_by='probe' and one by a person, both carrying an owner-confirmed proof
     (`proof_confirm` snapshot `true`) that now exits 0, so the stale_verify heal applies to both: a pass
     without --probe heals the person's card (unblocked) and names the probe card as skipped, leaving it blocked
  3. the same pass with --probe heals the probe card, which is how a proof gets its own cards back

Run:  python3 crew_probe_skip_proof.py
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
import crew_card   # noqa: E402  - owns the probe-card marker and the filter
import crew_proof_board   # noqa: E402

AGENT = crew_proof_board.AGENT
VENV_PY = crew_proof_board.VENV_PY
COORD = os.path.join(HERE, "crew_coordinator.py")
PROBE = "t9probeskip"           # created_by='probe': another run's fixture
REAL = "t9probeskip_real"       # a normal card beside it, same error, must still be walked
PROOF_CMD = "true"             # the snapshot both cards were opened with; exits 0, so stale_verify lifts the block
FAILS = []


def check(name, ok, detail=""):
    print("%-62s %s  %s" % (name, "PASS" if ok else "FAIL", str(detail)[:70]))
    if not ok:
        FAILS.append(name)


def profile_exists(name):
    """The host's own predicate, asked in its own interpreter - the call the dispatcher makes."""
    code = ("import sys;sys.path.insert(0,%r);"
            "from hermes_cli.profiles import profile_exists as pe;print(pe(%r))" % (AGENT, name))
    p = subprocess.run([VENV_PY, "-c", code], capture_output=True, text=True, timeout=180)
    return (p.stdout or "").strip() == "True"


def main():
    tmp = tempfile.mkdtemp(prefix="crew-probe-skip-")
    db = os.path.join(tmp, "kanban.db")
    home = os.path.join(tmp, "home")
    os.makedirs(home)
    try:
        if not crew_proof_board.init_board(db):
            print("PROOF FAIL: the scratch board could not be created")
            return 1
        # the heal runs the snapshot proof and lifts the block through the kernel's own unblock (a database
        # write); a `hermes` call, should one be made, fails here instead of reaching a real profile
        env = dict(os.environ, HERMES_HOME=home, HERMES_KANBAN_DB=db, CREW_WORKSPACE_ROOT=os.path.join(tmp, "ws"),
                   HERMES_BIN="/bin/false", CREW_COORDINATOR_DECIDER="/bin/false")
        now = int(time.time())
        conn = sqlite3.connect(db)
        for cid, owner in ((PROBE, "probe"), (REAL, "crew-coordinator")):
            conn.execute("insert into tasks (id, title, body, assignee, status, priority, created_by, created_at, "
                         "workspace_kind) values (?,?,?,?,'blocked',0,?,?,'scratch')",
                         (cid, "probe skip %s" % cid, "Role: worker\nGoal: probe\n", crew_card.FIXTURE_ASSIGNEE,
                          owner, now))
            for kind, payload in (("proof_confirm", {"proof_cmd": PROOF_CMD, "by": "owner"}),
                                  ("blocked", {"reason": "probe"})):
                conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                             "values (?, NULL, ?, ?, ?)", (cid, kind, json.dumps(payload), now))
        conn.commit()
        conn.close()

        def pass_report(*extra):
            p = subprocess.run([sys.executable, COORD, "--once", "--json", "--since", "0"] + list(extra),
                               env=env, capture_output=True, text=True, timeout=300)
            raw = p.stdout or ""
            try:
                return json.JSONDecoder().raw_decode(raw[raw.find("{"):])[0]
            except ValueError:
                return {"cards": [], "raw": (raw + p.stderr)[-300:]}

        def status(cid):
            c = sqlite3.connect(db)
            try:
                return c.execute("select status from tasks where id = ?", (cid,)).fetchone()[0]
            finally:
                c.close()

        check("the dispatcher cannot claim a fixture card", not profile_exists(crew_card.FIXTURE_ASSIGNEE),
              crew_card.FIXTURE_ASSIGNEE)
        check("the marker rule drops a probe and keeps a person's card",
              [c["id"] for c in crew_card.filter_probes([{"id": PROBE, "created_by": "probe"},
                                                        {"id": REAL, "created_by": "crew-coordinator"}])] == [REAL])

        rep = pass_report()
        by_card = {c["card"]: c for c in rep.get("cards", [])}
        check("a scheduled pass heals the person's card", status(REAL) != "blocked", status(REAL))
        check("the probe card stays blocked", status(PROBE) == "blocked", status(PROBE))
        check("the skipped probe card is named in the report",
              by_card.get(PROBE, {}).get("detail") == "probe fixture", str(by_card.get(PROBE))[:70])

        pass_report("--probe")
        check("--probe heals the proof's own probe card", status(PROBE) != "blocked", status(PROBE))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("PROOF OK: the coordinator pass leaves another run's probe card alone while it still walks real "
          "cards - and --probe gives a proof its own cards back")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
