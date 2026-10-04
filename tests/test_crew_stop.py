#!/usr/bin/env python3
"""Unit tests for the pure logic in scripts/crew_stop.py.

crew_stop binds KANBAN_DB at import time, so this module points it at a throwaway path BEFORE the
import - the live board is never opened, and one test asserts the binding is not the live board.
"""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

_TMPDIR = tempfile.mkdtemp(prefix="crew-stop-test-")
SAFE_DB = os.path.join(_TMPDIR, "not-the-live-board.db")
os.environ["KANBAN_DB"] = SAFE_DB

import crew_stop  # noqa: E402

LIVE_BOARD = os.path.join(os.path.expanduser("~"), ".hermes", "kanban.db")


class NoLiveBoardTests(unittest.TestCase):
    def test_the_module_was_imported_against_a_throwaway_db(self):
        self.assertNotEqual(os.path.realpath(LIVE_BOARD), os.path.realpath(crew_stop.KANBAN_DB))
        self.assertFalse(os.path.exists(crew_stop.KANBAN_DB))


class BoardResolutionTests(unittest.TestCase):
    """The board is resolved the way the rest of the crew resolves it: a pinned board, else this HERMES_HOME -
    never a hard-coded ~/.hermes/kanban.db."""

    def bind(self, env):
        done = subprocess.run([sys.executable, "-c", "import crew_stop; print(crew_stop.KANBAN_DB)"],
                              cwd=str(REPO / "scripts"), capture_output=True, text=True, env=env)
        return done.stdout.strip()

    def base_env(self, home):
        env = {k: v for k, v in os.environ.items() if k not in ("KANBAN_DB", "HERMES_KANBAN_DB")}
        env["HERMES_HOME"] = home
        return env

    def test_a_pinned_board_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            pinned = os.path.join(tmp, "pinned.db")
            open(pinned, "w").close()
            env = self.base_env(os.path.join(tmp, "home"))
            env["HERMES_KANBAN_DB"] = pinned
            self.assertEqual(pinned, self.bind(env))

    def test_the_board_under_hermes_home_is_used_not_tilde(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = os.path.join(tmp, "home")
            os.makedirs(home, exist_ok=True)
            open(os.path.join(home, "kanban.db"), "w").close()
            bound = self.bind(self.base_env(home))
            self.assertEqual(os.path.join(home, "kanban.db"), bound)
            self.assertNotEqual(os.path.join(os.path.expanduser("~"), ".hermes", "kanban.db"), bound)


class StopTargetTests(unittest.TestCase):
    """stop_targets: the named card, or every card that is not done/archived."""

    CREW = "Role: writer\nGOAL: x"
    CARDS = [{"id": "t_a", "status": "running", "body": CREW}, {"id": "t_b", "status": "blocked", "body": CREW},
             {"id": "t_c", "status": "done", "body": CREW}, {"id": "t_d", "status": "archived", "body": CREW},
             {"id": "t_e", "status": "triage", "body": CREW}, {"id": "t_f", "status": "review", "body": CREW},
             {"id": "t_x", "status": "running", "body": "someone else's card"},
             {"id": "t_y", "status": "blocked", "body": None}]

    def test_no_argument_stops_every_open_card(self):
        self.assertEqual(["t_a", "t_b", "t_e", "t_f"],
                         [c["id"] for c in crew_stop.stop_targets(self.CARDS)])

    def test_the_all_form_never_takes_a_non_crew_card(self):
        ids = [c["id"] for c in crew_stop.stop_targets(self.CARDS)]
        self.assertNotIn("t_x", ids)
        self.assertNotIn("t_y", ids)

    def test_a_named_card_is_the_only_target(self):
        self.assertEqual(["t_b"], [c["id"] for c in crew_stop.stop_targets(self.CARDS, "t_b")])

    def test_a_named_closed_card_is_still_returned(self):
        # the caller decides what to say about it; silently ignoring the id would read as success
        self.assertEqual(["t_c"], [c["id"] for c in crew_stop.stop_targets(self.CARDS, "t_c")])

    def test_an_unknown_id_is_no_target(self):
        self.assertEqual([], crew_stop.stop_targets(self.CARDS, "t_nope"))

    def test_an_empty_board_is_no_target(self):
        self.assertEqual([], crew_stop.stop_targets([]))


class LiveRunTests(unittest.TestCase):
    """live_runs: only a run marked running whose pid still answers is worth killing."""

    def test_running_with_a_live_pid_is_live(self):
        runs = [{"id": 1, "status": "running", "worker_pid": 11}]
        self.assertEqual([1], [r["id"] for r in crew_stop.live_runs(runs, lambda p: True)])

    def test_a_dead_pid_is_not_live(self):
        runs = [{"id": 1, "status": "running", "worker_pid": 11}]
        self.assertEqual([], crew_stop.live_runs(runs, lambda p: False))

    def test_a_settled_run_is_not_live_even_with_a_live_pid(self):
        runs = [{"id": 1, "status": "blocked", "worker_pid": 11},
                {"id": 2, "status": "timed_out", "worker_pid": 12}]
        self.assertEqual([], crew_stop.live_runs(runs, lambda p: True))

    def test_a_running_row_without_a_pid_is_not_live(self):
        runs = [{"id": 1, "status": "running", "worker_pid": None}]
        self.assertEqual([], crew_stop.live_runs(runs, lambda p: True))


class WorkerGuardTests(unittest.TestCase):
    """is_our_worker: the one thing that makes a pid safe to signal."""

    CARD = "t_85273cf6"

    def test_the_dispatchers_own_worker_line_matches(self):
        cmd = ('/usr/bin/python3 -I -c import os sys.argv[0]=... -p crew-worker --cli --accept-hooks'
               ' chat -q "work kanban task %s"' % self.CARD)
        self.assertTrue(crew_stop.is_our_worker(cmd, self.CARD))

    def test_another_cards_worker_does_not_match(self):
        self.assertFalse(crew_stop.is_our_worker("hermes chat -q \"work kanban task t_other\"", self.CARD))

    def test_the_gateway_and_the_board_server_never_match(self):
        for cmd in ("/usr/bin/python3 -m gateway", "python3 crew_graph_serve.py",
                    "python3 crew_stop.py t_85273cf6", ""):
            self.assertFalse(crew_stop.is_our_worker(cmd, self.CARD))

    def test_a_worker_line_without_the_marker_does_not_match(self):
        self.assertFalse(crew_stop.is_our_worker("hermes chat -q \"%s\"" % self.CARD, self.CARD))


class CameBackTests(unittest.TestCase):
    """came_back: the stays-down comparison the pass and its proof share."""

    def test_an_unchanged_card_did_not_come_back(self):
        self.assertFalse(crew_stop.came_back(("archived", 2, 0), ("archived", 2, 0)))

    def test_a_new_run_row_came_back(self):
        self.assertTrue(crew_stop.came_back(("archived", 2, 0), ("archived", 3, 0)))

    def test_a_status_change_came_back(self):
        self.assertTrue(crew_stop.came_back(("archived", 2, 0), ("ready", 2, 0)))

    def test_a_run_turning_running_came_back(self):
        self.assertTrue(crew_stop.came_back(("archived", 2, 0), ("archived", 2, 1)))


class FamilyTests(unittest.TestCase):
    """family_of: the open cards beside the one that was stopped, named for the report."""

    CARDS = [{"id": "t_a", "status": "archived", "assignee": "crew-worker"},
             {"id": "t_b", "status": "running", "assignee": "crew-worker"},
             {"id": "t_c", "status": "done", "assignee": "crew-verifier"},
             {"id": "t_d", "status": "todo", "assignee": "crew-coordinator"}]

    def test_open_links_are_named_in_both_directions(self):
        links = [{"parent_id": "t_b", "child_id": "t_a", "self": "t_a"},
                 {"parent_id": "t_a", "child_id": "t_d", "self": "t_a"}]
        self.assertEqual(["crew-worker: t_b (running)", "crew-coordinator: t_d (todo)"],
                         crew_stop.family_of(links, self.CARDS))

    def test_closed_links_are_left_out(self):
        links = [{"parent_id": "t_c", "child_id": "t_a", "self": "t_a"}]
        self.assertEqual([], crew_stop.family_of(links, self.CARDS))

    def test_a_repeated_link_is_named_once(self):
        links = [{"parent_id": "t_b", "child_id": "t_a", "self": "t_a"},
                 {"parent_id": "t_b", "child_id": "t_a", "self": "t_a"}]
        self.assertEqual(["crew-worker: t_b (running)"], crew_stop.family_of(links, self.CARDS))


class ReportTests(unittest.TestCase):
    """report_lines: what a stop says about itself."""

    CARD = {"id": "t_x", "status": "running"}

    def test_nothing_running_is_said_plainly(self):
        lines = crew_stop.report_lines(self.CARD, [], [], True, ("archived", 1, 1), [])
        self.assertIn("t_x  running -> archived", lines[0])
        self.assertEqual("  killed: nothing running", lines[1])

    def test_the_killed_runs_are_named_with_their_pids(self):
        lines = crew_stop.report_lines(self.CARD, [{"id": 2789, "worker_pid": 3693927}], [], True,
                                       ("archived", 2, 0), [])
        self.assertIn("run 2789 pid 3693927", lines[1])

    def test_the_open_family_is_reported_and_hinted_at(self):
        lines = crew_stop.report_lines(self.CARD, [], [], True, ("archived", 1, 1),
                                       ["crew-worker: t_other (running)"])
        self.assertTrue(any("still open beside it" in l for l in lines))
        self.assertTrue(any("separate ask" in l for l in lines))


class AliveTests(unittest.TestCase):
    """alive: a killed child nobody has reaped must not read as running."""

    def test_a_live_process_reads_alive(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            self.assertTrue(crew_stop.alive(proc.pid))
        finally:
            proc.kill()
            proc.wait()

    def test_a_zombie_reads_dead(self):
        # the bug this pins: signal 0 answers for a zombie, so the first live stop reported a
        # process it had just killed as STILL ALIVE
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        os.kill(proc.pid, 9)
        time.sleep(0.3)
        try:
            self.assertFalse(crew_stop.alive(proc.pid))
        finally:
            proc.wait()

    def test_a_pid_that_never_existed_reads_dead(self):
        self.assertFalse(crew_stop.alive(99999999))
        self.assertFalse(crew_stop.alive(None))
        self.assertFalse(crew_stop.alive("not a pid"))


if __name__ == "__main__":
    unittest.main()
