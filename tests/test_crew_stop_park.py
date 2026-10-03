#!/usr/bin/env python3
"""/crew-stop parks, it does not destroy (owner decision 2026-10-03), on a board made by the kernel's own code.

The owner ran /crew-stop on a card mid-verification and it was archived, uncontinuable. Now: the worker is killed and
its session closed, the card is held (blocked, or scheduled when parent-gated) with the owner-stop reason, the
coordinator / heal / notify leave it alone, and /crew-unstuck resumes it. --archive is the explicit drop.
"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

_TMP = tempfile.mkdtemp(prefix="crew-stop-park-")
os.environ["HERMES_HOME"] = os.path.join(_TMP, "home")
os.environ["HERMES_BIN"] = "/bin/false"
os.environ["KANBAN_DB"] = os.path.join(_TMP, "x.db")

import crew_card  # noqa: E402
import crew_coordinator as cc  # noqa: E402
import crew_heal  # noqa: E402
import crew_notify as N  # noqa: E402
import crew_stop  # noqa: E402
import crew_watch  # noqa: E402
import kernel_board as K  # noqa: E402

SESSION = "park_session_1"


def never(*_a, **_k):
    raise AssertionError("the coordinator must not decide on an owner-stopped card")


class ParkTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(dir=_TMP)
        self.kb, self.conn, self.db = K.open_board(self.dir)
        self.addCleanup(self.conn.close)
        self.cli = K.kernel_cli(self.db)
        self.procs = []
        self.addCleanup(lambda: [self.reap(p) for p in self.procs])
        for p in (mock.patch.object(crew_card.subprocess, "run", self.cli),
                  mock.patch.object(crew_card, "profile_exists", return_value=True),
                  mock.patch.object(crew_stop, "KANBAN_DB", self.db),
                  mock.patch.object(crew_stop, "TERM_WAIT_S", 0.2),
                  mock.patch.object(crew_heal, "KANBAN_DB", self.db),
                  mock.patch.object(crew_card, "close_proof_command", return_value="true"),
                  mock.patch.dict(os.environ, {"CREW_STOP_HERMES_ROOT": os.path.join(self.dir, "hermes")})):
            p.start()
            self.addCleanup(p.stop)

    def reap(self, proc):
        try:
            os.killpg(os.getpgid(proc.pid), 9)
        except Exception:  # noqa: BLE001
            pass
        proc.wait()

    def status(self, cid):
        return self.kb.get_task(self.conn, cid).status

    def running_card_with_worker(self):
        """A running card whose run row carries the pid of a stand-in worker (its command line names the card) and
        whose session row is open in a real SessionDB."""
        cid = K.add_card(self.conn, "ready")
        self.assertIsNotNone(self.kb.claim_task(self.conn, cid, claimer="w"))
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)", "work kanban task " + cid],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        self.procs.append(proc)
        time.sleep(0.3)
        self.conn.execute("update task_runs set worker_pid = ? where task_id = ?", (proc.pid, cid))
        import json
        self.conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values (?,?,?,?,?)",
                          (cid, None, "session", json.dumps({"session": SESSION, "profile": "crew-worker"}),
                           int(time.time())))
        self.conn.commit()
        sys.path.append(os.path.expanduser("~/.hermes/hermes-agent"))
        from hermes_state import SessionDB
        prof = os.path.join(self.dir, "hermes", "profiles", "crew-worker")
        os.makedirs(prof, exist_ok=True)
        sdb = SessionDB(db_path=Path(os.path.join(prof, "state.db")))
        sdb.create_session(SESSION, "cli")
        sdb.close()
        self.session_db = os.path.join(prof, "state.db")
        return cid, proc

    def stop(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = crew_stop.main(list(argv))
        return rc, out.getvalue()

    def reason_of(self, cid, kind):
        import json
        row = self.conn.execute("select payload from task_events where task_id = ? and kind = ? order by id desc",
                                (cid, kind)).fetchone()
        return json.loads(row[0])["reason"]

    def coordinator_pass(self, cid):
        ctx = cc.Ctx(self.db, None, dry=False, decider=never, say=lambda *_: None)
        ev = [dict(r) for r in self.conn.execute(
            "select id, task_id, kind, payload, created_at from task_events where task_id = ? "
            "and kind in ('blocked','scheduled')", (cid,))]
        return cc.handle_card(ctx, cid, ev)

    # -------------------------------------------------------------------------------- park
    def test_park_kills_the_worker_closes_the_session_and_blocks_with_the_owner_reason(self):
        cid, proc = self.running_card_with_worker()
        rc, out = self.stop(cid)
        self.assertEqual(0, rc, out)
        self.assertFalse(crew_stop.alive(proc.pid))
        self.assertEqual("blocked", self.status(cid))
        self.assertEqual("stopped by owner (/crew-stop) - continue with /crew-unstuck %s" % cid,
                         self.reason_of(cid, "blocked"))
        self.assertTrue(crew_card.parked_by_owner(self.db, cid))
        self.assertNotIn("archived", K.events(self.conn, cid))
        from hermes_state import SessionDB
        sdb = SessionDB(db_path=Path(self.session_db))
        self.assertIsNotNone(sdb.get_session(SESSION)["ended_at"])
        sdb.close()

    def test_coordinator_heal_and_notify_leave_a_parked_card_alone_across_passes(self):
        cid = K.add_card(self.conn, "ready")
        self.assertEqual(0, self.stop(cid)[0])
        before = K.events(self.conn, cid)
        for _ in range(3):
            got = self.coordinator_pass(cid)
            self.assertIn("stopped by the owner", got["detail"])
            self.assertIsNone(crew_heal.heal_card({"id": cid, "status": "blocked", "body": K.BODY}, False))
        c2 = self.conn_ro()
        self.assertEqual([], N.card_reports(c2, self.db, c2.execute("select * from tasks where id = ?",
                                                                    (cid,)).fetchone(), 0, time.time() + 10 ** 6))
        self.assertEqual("blocked", self.status(cid))
        self.assertEqual(before, K.events(self.conn, cid))        # no decision, no unblock, no heal event

    def test_unstuck_resumes_a_parked_card_and_the_coordinator_is_free_of_it(self):
        cid = K.add_card(self.conn, "ready")
        self.stop(cid)
        ok, text = crew_card.unstuck_card(cid)
        self.assertTrue(ok, text)
        self.assertEqual("ready", self.status(cid))
        self.assertEqual(0, crew_card.parked_by_owner(self.db, cid))
        self.assertEqual("unblocked", K.events(self.conn, cid)[-1])

    def test_a_parent_gated_card_is_parked_scheduled_and_unstuck_puts_it_back_gated(self):
        parent = K.add_card(self.conn, "ready")
        cid = K.add_card(self.conn, "ready", parents=(parent,))
        self.assertEqual("todo", self.status(cid))
        self.assertEqual(0, self.stop(cid)[0])
        self.assertEqual("scheduled", self.status(cid))
        self.kb.recompute_ready(self.conn)
        self.kb.recompute_ready(self.conn)
        self.assertEqual("scheduled", self.status(cid))            # the dispatcher's own pass does not promote it
        self.assertIn("stopped by the owner", self.coordinator_pass(cid)["detail"])
        ok, text = crew_card.unstuck_card(cid)
        self.assertTrue(ok, text)
        self.assertEqual("todo", self.status(cid))                 # parent still open: re-gated, not ready

    def test_an_already_blocked_card_is_parked_and_a_same_kind_block_does_not_loop_to_triage(self):
        cid = K.add_card(self.conn, "blocked")                     # block_kind needs_input
        self.assertEqual(0, self.stop(cid)[0])
        self.assertEqual("scheduled", self.status(cid))
        cid2 = K.add_card(self.conn, "blocked")
        self.kb.unblock_task(self.conn, cid2)                      # ready again, last kind needs_input survives
        self.assertEqual(0, self.stop(cid2)[0])
        self.assertEqual("blocked", self.status(cid2))             # not triage: the kind moved on
        self.assertEqual("capability", self.kb.get_task(self.conn, cid2).block_kind)

    def test_a_second_stop_of_a_parked_card_changes_nothing(self):
        cid = K.add_card(self.conn, "ready")
        self.stop(cid)
        before = K.events(self.conn, cid)
        rc, out = self.stop(cid)
        self.assertEqual(0, rc, out)
        self.assertEqual(before, K.events(self.conn, cid))

    def test_a_triage_card_cannot_be_parked_and_says_so(self):
        cid = K.add_card(self.conn, "triage")
        rc, out = self.stop(cid)
        self.assertEqual(1, rc)
        self.assertIn("NOT DOWN", out)
        self.assertEqual("triage", self.status(cid))

    # -------------------------------------------------------------------------------- archive / bare
    def test_archive_flag_archives_and_kills(self):
        cid, proc = self.running_card_with_worker()
        rc, out = self.stop(cid, "--archive")
        self.assertEqual(0, rc, out)
        self.assertEqual("archived", self.status(cid))
        self.assertFalse(crew_stop.alive(proc.pid))

    def test_archive_without_a_card_is_refused(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            crew_stop.main(["--archive"])
        self.assertEqual(2, ctx.exception.code)

    def test_bare_stop_parks_every_open_crew_card_and_nothing_else(self):
        a = K.add_card(self.conn, "ready")
        b = K.add_card(self.conn, "blocked")
        other = K.add_card(self.conn, "ready", body="just a card, no crew lines")
        done = K.add_card(self.conn, "ready")
        self.kb.claim_task(self.conn, done, claimer="w")
        self.kb.complete_task(self.conn, done, result="r")
        rc, out = self.stop()
        self.assertEqual(0, rc, out)
        self.assertEqual(("blocked", "scheduled"), (self.status(a), self.status(b)))
        self.assertEqual(("ready", "done"), (self.status(other), self.status(done)))
        for cid in (a, b, other, done):
            self.assertNotEqual("archived", self.status(cid))

    # -------------------------------------------------------------------------------- the watcher
    def test_the_watcher_reports_a_parked_card_once_and_the_notifier_never(self):
        cid = K.add_card(self.conn, "ready")
        self.stop(cid)
        state = os.path.join(self.dir, "notify-state.json")
        got = crew_watch.check(self.db, cid, state, time.time())
        self.assertIsNotNone(got)
        text, marks = got
        self.assertEqual("crew watch: card %s stopped by you - /crew-unstuck %s to continue." % (cid, cid), text)
        self.assertEqual(1, len(marks))
        self.assertTrue(marks[0][1].startswith("parked:"))
        self.assertEqual(text, crew_watch.watch(self.db, cid, state, poll=0, lifetime=5))
        self.assertEqual([], N.candidates(self.conn_ro(), self.db, 0, time.time() + 10 ** 6))

    def conn_ro(self):
        import sqlite3
        c = sqlite3.connect(self.db)
        c.row_factory = sqlite3.Row
        self.addCleanup(c.close)
        return c


if __name__ == "__main__":
    unittest.main()
