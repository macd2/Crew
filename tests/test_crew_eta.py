"""The card page's ETA: how much longer a running crew worker likely needs, read off the role's own history.

The estimator is pure (no db, no clock) so its rules are pinned directly: which basis it picks, how far it
trusts the run's own pace against the role median, the cap that never calls a live run done, the floor that
never goes negative, and the band that stays ordered. The two gatherers are pinned against throwaway
sqlite files. The guards are pinned so a done run - or a card with no live run - yields no ETA, never a 0.
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import crew_graph as cg  # noqa: E402

DURS = [300, 400, 500, 600, 700, 800, 900, 1000]   # 8 samples; crew_card._pct(0.5) -> vals[4] = 700
STEPS = [12, 14, 16, 18, 20, 22, 24]               # 7 samples; _pct(0.5) -> vals[3] = 18


class EstimateMath(unittest.TestCase):
    def test_no_history_is_not_a_guess(self):
        e = cg.estimate_run_eta(300, 5, [], [])
        self.assertEqual(e["basis"], "none")
        self.assertIsNone(e["remaining_s"])
        self.assertEqual(cg.short_eta(e), "")
        self.assertIn("no baseline", cg.fmt_eta(e))

    def test_duration_only_when_no_step_history(self):
        e = cg.estimate_run_eta(300, None, DURS, [])
        self.assertEqual(e["basis"], "duration")
        self.assertEqual(e["dur_median"], 700)  # _pct(0.5) of 8 samples is the 5th
        self.assertEqual(e["remaining_s"], 400)  # median total 700 - 300 elapsed

    def test_milestone_uses_role_median_steps(self):
        # at half the typical steps, half way: total ~= 2 * elapsed
        e = cg.estimate_run_eta(200, 9, DURS, STEPS)
        self.assertEqual(e["basis"], "milestone")
        self.assertAlmostEqual(e["progress"], 0.5, places=2)
        self.assertGreater(e["remaining_s"], 0)

    def test_early_run_trusts_the_median_not_its_own_pace(self):
        # one step in, pace would scream "hours left"; the blend must stay near the role median
        e = cg.estimate_run_eta(60, 1, DURS, STEPS)
        self.assertEqual(e["basis"], "milestone")
        self.assertLessEqual(e["remaining_s"], max(DURS) - 60)
        self.assertGreaterEqual(e["remaining_s"], 0)

    def test_more_progress_never_raises_the_estimate(self):
        early = cg.estimate_run_eta(300, 4, DURS, STEPS)
        late = cg.estimate_run_eta(300, 16, DURS, STEPS)
        self.assertLessEqual(late["remaining_s"], early["remaining_s"])

    def test_progress_is_capped_below_done(self):
        e = cg.estimate_run_eta(100, 5000, DURS, STEPS)  # far more steps than typical
        self.assertLess(e["progress"], 1.0)
        self.assertLessEqual(e["progress"], cg.ETA_CAP)

    def test_remaining_never_negative(self):
        # a duration-basis run long past its median clamps to zero
        self.assertEqual(cg.estimate_run_eta(100000, None, DURS, [])["remaining_s"], 0)
        # a milestone run past its typical step count still reports a small positive tail, never a negative
        self.assertGreaterEqual(cg.estimate_run_eta(100000, 18, DURS, STEPS)["remaining_s"], 0)

    def test_band_is_ordered(self):
        e = cg.estimate_run_eta(200, 8, DURS, STEPS)
        self.assertLessEqual(e["lo_s"], e["remaining_s"])
        self.assertLessEqual(e["remaining_s"], e["hi_s"])

    def test_steps_velocity_when_only_steps_history(self):
        e = cg.estimate_run_eta(100, 3, [], STEPS)  # no durations, but pace is known
        self.assertEqual(e["basis"], "steps-velocity")
        self.assertGreater(e["remaining_s"], 0)

    def test_high_confidence_needs_many_runs_and_progress(self):
        self.assertEqual(cg.estimate_run_eta(200, 12, DURS, STEPS)["confidence"], "high")
        self.assertEqual(cg.estimate_run_eta(50, 1, DURS[:3], STEPS[:3])["confidence"], "medium")


class Formatters(unittest.TestCase):
    def test_short_eta_is_one_number_saying_remaining(self):
        e = cg.estimate_run_eta(200, 9, DURS, STEPS)
        s = cg.short_eta(e)
        self.assertTrue(s.startswith("~"))
        self.assertTrue(s.endswith("remaining"))
        self.assertNotIn("-", s[1:].split(" ")[0])  # the duration part is one value, not a "a-b" band

    def test_fmt_eta_names_basis_detail(self):
        e = cg.estimate_run_eta(200, 9, DURS, STEPS)
        self.assertIn("remaining", cg.fmt_eta(e))
        self.assertIn("step", cg.fmt_eta(e))
        self.assertIn("n=", cg.fmt_eta(e))

    def test_fmt_dur_str_units(self):
        self.assertEqual(cg.fmt_dur_str(45), "45s")
        self.assertEqual(cg.fmt_dur_str(300), "5m")
        self.assertEqual(cg.fmt_dur_str(3900), "1h05m")
        self.assertEqual(cg.fmt_dur_str(None), "-")


class Gatherers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _board(self):
        path = os.path.join(self.tmp.name, "kanban.db")
        conn = sqlite3.connect(path)
        conn.execute("create table task_runs (profile text, status text, outcome text, "
                     "started_at int, ended_at int)")
        conn.executemany("insert into task_runs values (?,?,?,?,?)", [
            ("worker", "done", "completed", 1000, 1600),      # counts: 600s
            ("worker", "running", "completed", 2000, 2750),   # counts by outcome: 750s
            ("worker", "blocked", "blocked", 3000, 3900),     # not a success -> ignored
            ("worker", "done", "completed", 4000, None),      # no end -> ignored
            ("other", "done", "completed", 5000, 9000),        # other role -> ignored
        ])
        conn.commit()
        conn.close()
        return path

    def _profile_state(self):
        path = os.path.join(self.tmp.name, "state.db")
        conn = sqlite3.connect(path)
        conn.execute("create table sessions (source text, parent_session_id text, "
                     "ended_at real, tool_call_count int)")
        conn.executemany("insert into sessions values (?,?,?,?)", [
            ("kanban", None, 1.0, 15),       # counts
            ("kanban", None, 2.0, 21),       # counts
            ("kanban", "parent-1", 3.0, 40),  # a child -> excluded
            ("kanban", None, None, 99),      # still open -> excluded
            ("chat", None, 4.0, 100),        # not kanban -> excluded
        ])
        conn.commit()
        conn.close()
        return path

    def test_role_durations_counts_successes_only(self):
        self.assertEqual(sorted(cg.role_durations(self._board(), "worker")), [600.0, 750.0])

    def test_role_durations_empty_for_unknown_role(self):
        self.assertEqual(cg.role_durations(self._board(), "ghost"), [])

    def test_role_step_medians_reads_top_level_finished_kanban_sessions(self):
        with mock.patch.object(cg, "state_db_for", return_value=self._profile_state()):
            self.assertEqual(sorted(cg.role_step_medians("worker")), [15, 21])


class Guards(unittest.TestCase):
    def test_no_live_run_is_no_eta(self):
        self.assertIsNone(cg.live_run_eta(None, None, None))

    def test_a_finished_run_is_no_eta(self):
        # run_row: (id, profile, status, outcome, summary, error, started_at, ended_at, heartbeat)
        done = (1, "worker", "done", "completed", "", "", 1000, 1600, 1600)
        self.assertIsNone(cg.live_run_eta(None, ("t", "", "done", "", "", "", None), done))
