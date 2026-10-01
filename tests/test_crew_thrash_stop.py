#!/usr/bin/env python3
"""Unit tests for the thrash stop: consecutive failed tool calls in a role profile stop the run.

Pure hook logic with injected results, like crew_guard_quadrants.py: the post_tool_call observer counts, the
pre_tool_call guard refuses. No hermes CLI, no live board; HERMES_HOME and the kanban db are throwaway. The
plugin module is loaded AFTER the environment is set, because it reads HERMES_HOME at import time.
"""
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
os.environ.setdefault("HERMES_BIN", "/bin/false")   # a unit test never starts the real `hermes` (scratch HERMES_HOME bootstraps a runtime and rewrites the live launcher)

import crew_card  # noqa: E402
import crew_heal  # noqa: E402
import crew_result  # noqa: E402

CARD = "t_thrash_unit"
FAIL_TERMINAL = json.dumps({"output": "", "exit_code": 2, "error": "No such file or directory: /x"})
OK_TERMINAL = json.dumps({"output": "done", "exit_code": 0, "error": None})


def load_plugin():
    spec = importlib.util.spec_from_file_location("crew_plugin_thrash_test", str(REPO / "__init__.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ThrashCase(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-thrash-test-")
        os.environ["HERMES_HOME"] = self.home
        os.environ["HERMES_KANBAN_DB"] = os.path.join(self.home, "kanban.db")
        os.environ["HERMES_KANBAN_TASK"] = CARD
        with open(os.path.join(self.home, "config.yaml"), "w") as fh:
            fh.write("crew:\n  role: worker\n")
        conn = sqlite3.connect(os.environ["HERMES_KANBAN_DB"])
        conn.executescript(
            "create table tasks (id text primary key, title text, status text, assignee text, body text);"
            "create table task_events (id integer primary key autoincrement, task_id text, run_id text,"
            " kind text, payload text, created_at integer);")
        conn.commit()
        conn.close()
        self.plug = load_plugin()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)

    def call(self, tool, result, args=None):
        """One tool call the way the runtime makes it: the guard first, then (when it let the call through) the
        observer with the result. Returns the guard's verdict."""
        verdict = self.plug.crew_tool_guard(tool_name=tool, args=args or {}, session_id="S", turn_id="T")
        if verdict is None or verdict.get("action") != "block":
            self.plug.crew_thrash_hook(tool_name=tool, args=args or {}, result=result, session_id="S")
        return verdict


class ThrashStopTests(ThrashCase):
    def test_limit_comes_from_roles_json(self):
        self.assertEqual(5, crew_card.max_consecutive_failures())

    def test_the_sixth_call_after_five_failures_is_blocked_with_the_exact_block_call(self):
        for _ in range(5):
            self.assertIsNone(self.call("terminal", FAIL_TERMINAL))
        verdict = self.call("terminal", OK_TERMINAL)
        self.assertEqual("block", verdict["action"])
        msg = verdict["message"]
        self.assertIn("kanban_block(kind='transient'", msg)
        self.assertIn("crew: repeated tool failure: No such file or directory: /x", msg)
        self.assertIn("5 tool calls in a row failed", msg)

    def test_four_failures_then_an_ok_result_start_the_count_again(self):
        for _ in range(4):
            self.call("terminal", FAIL_TERMINAL)
        self.assertIsNone(self.call("terminal", OK_TERMINAL))
        for _ in range(3):
            self.assertIsNone(self.call("terminal", FAIL_TERMINAL))
        self.assertIsNone(self.call("read_file", OK_TERMINAL))

    def test_kanban_tools_are_not_counted(self):
        for _ in range(4):
            self.call("terminal", FAIL_TERMINAL)
        for _ in range(10):
            self.plug.crew_thrash_hook(tool_name="kanban_comment", result=FAIL_TERMINAL)
            self.plug.crew_thrash_hook(tool_name="kanban_complete", result=json.dumps({"error": "refused"}))
        self.assertIsNone(self.call("terminal", OK_TERMINAL))

    def test_the_tools_a_blocked_card_may_still_use_stay_allowed(self):
        for _ in range(6):
            self.call("terminal", FAIL_TERMINAL)
        for tool in ("kanban_block", "kanban_comment", "kanban_show", "kanban_heartbeat"):
            self.assertIsNone(self.call(tool, "{}"), tool)
        # and everything else stays refused: the stop cannot be walked around with another tool
        for tool in ("terminal", "write_file", "search_files", "kanban_complete"):
            self.assertEqual("block", (self.call(tool, OK_TERMINAL) or {}).get("action"), tool)

    def test_a_result_arriving_already_parsed_counts_the_same(self):
        for _ in range(5):
            self.plug.crew_thrash_hook(tool_name="terminal", result={"error": "boom", "exit_code": 1})
        verdict = self.plug.crew_tool_guard(tool_name="terminal", args={}, session_id="S", turn_id="T")
        self.assertEqual("block", verdict["action"])

    def test_nothing_happens_outside_a_kanban_worker(self):
        os.environ.pop("HERMES_KANBAN_TASK")
        for _ in range(8):
            self.assertIsNone(self.call("terminal", FAIL_TERMINAL))

    def test_nothing_happens_in_a_profile_without_a_crew_role(self):
        os.remove(os.path.join(self.home, "config.yaml"))
        plug = load_plugin()
        for _ in range(8):
            plug.crew_thrash_hook(tool_name="terminal", result=FAIL_TERMINAL)
        self.assertIsNone(plug.crew_tool_guard(tool_name="terminal", args={}, session_id="S", turn_id="T"))

    def test_the_budget_stop_and_the_rework_cap_name_their_block_call_too(self):
        self.assertIn("kanban_block(kind='needs_input', reason='Needs you: budget exhausted')",
                      self.plug._stop_message("x.", "needs_input", "Needs you: budget exhausted"))
        self.assertTrue(self.plug._stop_message("x.", "transient", "r").endswith("and end."))


# Where the failed non-kanban calls fall in the real t_d93e0c7b run (202 non-kanban calls, 23 failed, never more
# than 2 in a row), read from the worker's state.db. The streak rule never sees it; the window rule must.
ANCHOR_ERR_AT = [31, 99, 111, 112, 115, 116, 121, 122, 129, 130, 134, 163, 170, 175, 177, 178, 185, 186, 192,
                 195, 198, 201, 202]
ANCHOR_CALLS = 202


class ThrashRateTests(ThrashCase):
    def feed(self, states):
        """Drive the guard+hook pair over a list of 'err'/'ok' results; return the 1-based index of the call
        after which the next call is refused, or None."""
        for i, st in enumerate(states, 1):
            verdict = self.call("terminal", FAIL_TERMINAL if st == "err" else OK_TERMINAL)
            if verdict is not None:
                return i - 1
        verdict = self.plug.crew_tool_guard(tool_name="terminal", args={}, session_id="S", turn_id="T")
        return len(states) if verdict else None

    def test_the_window_limits_come_from_roles_json(self):
        self.assertEqual(8, crew_card.max_window_failures())
        self.assertEqual(25, crew_card.failure_window_calls())

    def test_scattered_failures_stop_the_run_at_the_eighth_in_the_window(self):
        states = ["err", "ok"] * 8          # 8 failures, never two in a row
        self.assertEqual(15, self.feed(states))

    def test_seven_scattered_failures_do_not_stop_it(self):
        self.assertIsNone(self.feed(["err", "ok"] * 7))

    def test_failures_older_than_the_window_are_forgotten(self):
        self.assertIsNone(self.feed(["err", "ok"] * 7 + ["ok"] * 25 + ["err", "ok"] * 7))

    def test_the_stop_message_says_how_many_and_names_the_block_call(self):
        self.feed(["err", "ok"] * 8)
        msg = self.plug.crew_tool_guard(tool_name="terminal", args={}, session_id="S", turn_id="T")["message"]
        self.assertIn("8 of the last 15 tool calls failed", msg)
        self.assertIn("kanban_block(kind='transient'", msg)
        self.assertIn("crew: repeated tool failure:", msg)

    def test_the_real_anchor_run_is_stopped_after_its_130th_call_not_its_202nd(self):
        states = ["err" if i in ANCHOR_ERR_AT else "ok" for i in range(1, ANCHOR_CALLS + 1)]
        self.assertEqual(130, self.feed(states))

    def test_the_heaviest_healthy_real_run_is_not_stopped(self):
        # Same call and failure counts as the heaviest done worker run in 7 days (110 non-kanban calls, 14
        # failed; in the real run no 25 consecutive calls held more than 6 failures). The positions here are
        # spread by hand, so this pins the threshold's margin, not the real run.
        errs = [3, 9, 14, 20, 26, 31, 37, 52, 58, 71, 80, 91, 99, 105]
        states = ["err" if i in errs else "ok" for i in range(1, 111)]
        self.assertIsNone(self.feed(states))


class ThrashConsumerTests(unittest.TestCase):
    """The new block reason must not fall into the heal's catch-all kind."""

    def test_the_reason_is_its_own_wall_kind_whatever_the_last_note_says(self):
        for note in ("permission denied: /etc/x", "429 too many requests", "timed out", "x"):
            text = "blocked crew: %s: %s" % (crew_result.THRASH_REASON, note)
            self.assertEqual("thrash", crew_heal.wall_kind(text), note)

    def test_two_thrash_blocks_with_different_notes_are_one_repeat(self):
        runs = [{"id": 2, "status": "blocked", "outcome": "blocked",
                 "summary": "crew: repeated tool failure: permission denied", "error": None},
                {"id": 1, "status": "blocked", "outcome": "blocked",
                 "summary": "crew: repeated tool failure: No such file", "error": None}]
        self.assertEqual(2, len(crew_heal.repeat_chain("t_x", runs=runs)))

    def test_the_classifier_is_the_one_the_dashboard_uses(self):
        import crew_graph
        self.assertIs(crew_graph.crew_result, crew_result)
        self.assertEqual("err", crew_result.result_state(FAIL_TERMINAL))
        self.assertEqual("ok", crew_result.result_state(OK_TERMINAL))


if __name__ == "__main__":
    unittest.main()
