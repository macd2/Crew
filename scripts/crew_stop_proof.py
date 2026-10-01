#!/usr/bin/env python3
"""Proof for crew_stop.py - the stop pass, and that a stopped card stays down.

Checks (each one prints PASS/FAIL with the evidence it measured):

  1. the guard: a pid that is not this card's own worker is refused, and the process survives
  2. a real stop: the card's live worker process dies, its open session row is closed, the card is
     archived and the card carries a `stopped` audit event
  3. stays down: after the kernel's own recompute_ready (the dispatcher's promotion pass) the card is
     still archived and no run row was added
  4. the id form touches that card only: a second card with a live worker is left ready and alive
     until it is named
  5. the family is reported, not followed: an open card linked to the stopped one is named in the
     output and left alone

Run:  python3 crew_stop_proof.py
Exit: 0 when every check passes, 1 otherwise.

The fixtures are probe cards on the live board (created_by='probe', the same marker every crew proof
writes, which the board's lanes and the scheduled passes skip) and are archived in a finally block.
The worker processes are stand-ins: a python that sleeps with `work kanban task <card>` in its own
command line, which is exactly what the guard reads.
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_proof_board  # noqa: E402
KANBAN_DB = crew_proof_board.proof_db()
STOP = os.path.join(HERE, "crew_stop.py")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The pass under test is imported, not copied: `alive`, `came_back` and the stopping rules have ONE
# owner, and a proof that re-typed them would agree with itself while the pass was broken.
CS = _load(STOP, "crew_stop_under_test")
SUFFIX = str(os.getpid())
CARD_A = "t_stop_proof_a" + SUFFIX[-4:]      # the card that is stopped
CARD_B = "t_stop_proof_b" + SUFFIX[-4:]      # the card the id form must not touch
CARD_C = "t_stop_proof_c" + SUFFIX[-4:]      # the card whose run points at a foreign pid
SESSION = "prooftmp_" + SUFFIX
FAILS = []
CHECKS = 0


def check(name, ok, detail=""):
    global CHECKS
    CHECKS += 1
    print("%-66s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + str(detail)[:100]) if detail else ""))
    if not ok:
        FAILS.append(name)
    return ok


def db():
    return sqlite3.connect(KANBAN_DB, timeout=10)


def wk(card, status, run_status=None, pid=None):
    """Seed one probe card, with its run row carrying a worker pid when one is given.

    A fixture is seeded 'running' (never 'ready'/'todo'): the dispatcher recomputes readiness on
    every tick, and a card it can claim would spawn a REAL worker on the live board mid-proof.
    """
    conn = db()
    now = int(time.time())
    try:
        conn.execute("insert into tasks (id, title, body, status, assignee, created_by, created_at, "
                     "workspace_kind, claim_lock, claim_expires) values (?,?,?,?,?,?,?,'scratch',?,?)",
                     (card, "PROBE crew_stop " + card, "proof fixture", status, "crew-worker", "probe",
                      now, "proof", now + 900))
        if run_status:
            conn.execute("insert into task_runs (task_id, profile, status, started_at, worker_pid, "
                         "last_heartbeat_at, claim_lock, claim_expires) values (?,?,?,?,?,?,?,?)",
                         (card, "crew-worker", run_status, now, pid, now, "proof", now + 900))
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values "
                     "(?,?,?,?,?)", (card, None, "session",
                                     json.dumps({"session": SESSION, "profile": "crew-worker"}), now))
        conn.commit()
    finally:
        conn.close()


def spawn_worker(card, foreign=False):
    """A stand-in worker: sleeps with the card's own `work kanban task` line in its command line."""
    arg = ("not a worker at all" if foreign else ("work kanban task " + card))
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)", arg],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)


def kill(proc):
    try:
        os.killpg(os.getpgid(proc.pid), 9)
    except Exception:  # noqa: BLE001
        pass


def alive(pid):
    """The pass's own liveness rule (imported, never re-typed): zombies count as gone."""
    return CS.alive(pid)


def hermes_bin():
    return os.environ.get("HERMES_BIN") or shutil.which("hermes") or os.path.expanduser("~/.local/bin/hermes")


def promotion_pass():
    """The dispatcher's own promotion pass, through the shipped CLI.

    `hermes kanban list` runs kb.recompute_ready before it answers (hermes_cli/kanban.py), which is
    the same pass that would promote and claim a stopped card again. Its output is the lane listing
    the last check reads, so one call answers both questions.
    """
    return subprocess.run([hermes_bin(), "kanban", "list", "--status", "ready"],
                          capture_output=True, text=True, timeout=180,
                          env=dict(os.environ, KANBAN_DB=KANBAN_DB))


def card_row(card):
    conn = db()
    try:
        return conn.execute("select status from tasks where id = ?", (card,)).fetchone()
    finally:
        conn.close()


def runs_of(card):
    conn = db()
    try:
        return conn.execute("select id, status from task_runs where task_id = ?", (card,)).fetchall()
    finally:
        conn.close()


def events_of(card, kind):
    conn = db()
    try:
        return conn.execute("select payload from task_events where task_id = ? and kind = ?",
                            (card, kind)).fetchall()
    finally:
        conn.close()


def link(parent, child):
    conn = db()
    try:
        conn.execute("insert into task_links (parent_id, child_id) values (?,?)", (parent, child))
        conn.commit()
    finally:
        conn.close()


def run_stop(args, home):
    env = dict(os.environ, KANBAN_DB=KANBAN_DB, HERMES_HOME=home)
    return subprocess.run([sys.executable, STOP] + args, capture_output=True, text=True,
                          timeout=120, env=env)


def drop():
    conn = db()
    try:
        ids = (CARD_A, CARD_B, CARD_C)
        for card in ids:
            # settle the run rows this fixture invented as well: a probe left 'running' makes the card
            # page show a killed worker as live (the T14 failure mode /crew-stop exists to prevent)
            conn.execute("update task_runs set status = 'stopped', claim_lock = null "
                         "where task_id = ? and status = 'running'", (card,))
            conn.execute("update tasks set status = 'archived', claim_lock = null where id = ?", (card,))
        conn.execute("delete from task_links where parent_id in (?,?,?) or child_id in (?,?,?)",
                     ids + ids)
        conn.commit()
    finally:
        conn.close()


def main():
    procs = []
    tmp = tempfile.mkdtemp(prefix="crew_stop_proof_")
    home = os.path.join(tmp, "hermes")
    prof = os.path.join(home, "profiles", "crew-worker")
    os.makedirs(prof, exist_ok=True)
    sdb = sqlite3.connect(os.path.join(prof, "state.db"))
    sdb.execute("create table sessions (id text primary key, started_at real, ended_at real, title text)")
    sdb.execute("insert into sessions (id, started_at, ended_at, title) values (?,?,?,?)",
                (SESSION, time.time(), None, "proof session"))
    sdb.commit()
    sdb.close()

    try:
        # fixtures: A (stopped by id), B (must not be touched by A's stop), C (foreign pid)
        worker_a = spawn_worker(CARD_A); procs.append(worker_a)
        worker_b = spawn_worker(CARD_B); procs.append(worker_b)
        foreign = spawn_worker(CARD_C, foreign=True); procs.append(foreign)
        time.sleep(0.4)
        wk(CARD_A, "running", run_status="running", pid=worker_a.pid)
        wk(CARD_B, "running", run_status="running", pid=worker_b.pid)
        wk(CARD_C, "running", run_status="running", pid=foreign.pid)
        link(CARD_A, CARD_B)                       # B is linked to A, and stays open

        # 1 + 4 + 5: the id form stops A only
        r = run_stop([CARD_A], home)
        out = r.stdout + r.stderr
        check("the pass runs and exits 0 on a card it stopped", r.returncode == 0,
              "rc=%d %s" % (r.returncode, out.strip().splitlines()[:1]))
        check("A's worker process is dead", not alive(worker_a.pid), "pid %d" % worker_a.pid)
        check("A is archived", (card_row(CARD_A) or [""])[0] == "archived", card_row(CARD_A))
        check("A carries a `stopped` audit event", bool(events_of(CARD_A, "stopped")))
        check("B was not touched by the id form",
              bool(alive(worker_b.pid)) and (card_row(CARD_B) or [""])[0] != "archived",
              "status=%s alive=%s" % (card_row(CARD_B), alive(worker_b.pid)))
        check("the open linked card is named in the output", CARD_B in out, out.strip().splitlines()[-1:])
        check("A's open session row was closed",
              sqlite3.connect(os.path.join(prof, "state.db")).execute(
                  "select ended_at from sessions where id = ?", (SESSION,)).fetchone()[0] is not None)

        # 3: two real promotion passes (the dispatcher's own recompute_ready) do not bring it back
        left = ((card_row(CARD_A) or ["?"])[0], len(runs_of(CARD_A)))
        promotion_pass()
        time.sleep(1.0)
        second = promotion_pass()
        now = ((card_row(CARD_A) or ["?"])[0], len(runs_of(CARD_A)))
        check("still archived and unchanged after two promotion passes",
              now[0] == "archived" and not CS.came_back(left, now), "%s -> %s" % (left, now))
        check("the stopped card is not in the ready lane",
              CARD_A not in (second.stdout + second.stderr),
              [l.strip() for l in (second.stdout + second.stderr).splitlines() if CARD_A in l][:1])

        # 1 (guard): C's run points at a process that is not its worker
        r = run_stop([CARD_C], home)
        check("a foreign pid is refused and survives", alive(foreign.pid) and "refused" in (r.stdout + r.stderr),
              [l for l in (r.stdout + r.stderr).splitlines() if "refused" in l][:1])
        check("the refused card is still archived (the stop still settles it)",
              (card_row(CARD_C) or [""])[0] == "archived", card_row(CARD_C))

        # 4: B goes down when it is named
        r = run_stop([CARD_B], home)
        check("B stops when its own id is given",
              (card_row(CARD_B) or [""])[0] == "archived" and not alive(worker_b.pid), r.returncode)

        # 6: an unknown id is its own exit code, not a silent success
        r = run_stop(["t_nope_" + SUFFIX], home)
        check("an unknown card id is refused as such", r.returncode == 3, "rc=%d" % r.returncode)
    finally:
        for p in procs:
            kill(p)
        drop()
        try:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass

    print("\n%s: %d check(s), %d failed" % (os.path.basename(__file__), CHECKS, len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
