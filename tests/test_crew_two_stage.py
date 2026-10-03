#!/usr/bin/env python3
"""Unit tests for the plugin's side of two-stage verification: `kanban_request_review` follows the card's
`Verify:` line, and the intake's `kanban_create` refuses a bad one. Pure hook logic on a throwaway board; the
router and the hermes CLI are never reached (repin_for_review is replaced, HERMES_BIN is /bin/false).
"""
import importlib.util
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
os.environ.setdefault("HERMES_BIN", "/bin/false")   # a unit test never starts the real `hermes` (scratch HERMES_HOME bootstraps a runtime and rewrites the live launcher)

import crew_card  # noqa: E402

BODY = "Role: worker\nCoordinator: c\n%sBudget: 200000 tokens\nGOAL: g\nArtifact: a\nLands at: l\nFor: o\nDone when: d\nproof command: true\n"


def load_plugin():
    spec = importlib.util.spec_from_file_location("crew_plugin_two_stage_test", str(REPO / "__init__.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ReviewGuardTests(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-two-stage-test-")
        os.environ["HERMES_HOME"] = self.home
        os.environ["HERMES_KANBAN_DB"] = os.path.join(self.home, "kanban.db")
        os.environ["HERMES_KANBAN_TASK"] = "t_w"
        conn = sqlite3.connect(os.environ["HERMES_KANBAN_DB"])
        conn.executescript("create table tasks (id text primary key, title text, status text, assignee text, body text);")
        conn.commit()
        conn.close()
        self.plug = load_plugin()
        p = mock.patch.object(self.plug, "_card_tool", return_value=crew_card)   # the plugin's own copy would dodge the mocks
        p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        for key in [k for k in os.environ if k not in self._env]:
            del os.environ[key]
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)

    def card(self, verify_line):
        conn = sqlite3.connect(os.environ["HERMES_KANBAN_DB"])
        conn.execute("insert or replace into tasks values ('t_w', 't', 'running', 'crew-worker', ?)",
                     (BODY % verify_line,))
        conn.commit()
        conn.close()

    def test_a_proof_card_refuses_the_review_and_names_the_two_steps_that_finish_it(self):
        self.card("Verify: proof\n")
        res = self.plug._review_guard("kanban_request_review", {"summary": "done"})
        self.assertEqual("block", res["action"])
        self.assertIn("verdict --card t_w", res["message"])
        self.assertIn("kanban_complete", res["message"])

    def test_an_independent_card_repins_for_the_verifier_and_goes_on(self):
        self.card("Verify: independent\n")
        with mock.patch.object(crew_card, "repin_for_review", return_value={"action": "pinned"}) as repin:
            self.assertIsNone(self.plug._review_guard("kanban_request_review", {"summary": "done"}))
        repin.assert_called_once_with("t_w")

    def test_the_verifier_never_requests_review_it_would_become_the_implementer(self):
        self.card("Verify: independent\n")
        with mock.patch.object(self.plug, "_crew_role", return_value="verifier"):
            res = self.plug._review_guard("kanban_request_review", {"summary": "verified"})
        self.assertEqual("block", res["action"])
        self.assertIn("kanban_request_changes", res["message"])

    def test_a_repin_that_raises_never_stops_the_review(self):
        self.card("Verify: independent\n")
        with mock.patch.object(crew_card, "repin_for_review", side_effect=RuntimeError("router down")):
            self.assertIsNone(self.plug._review_guard("kanban_request_review", {}))

    def test_a_card_from_before_the_line_and_other_tools_are_left_alone(self):
        self.card("")
        with mock.patch.object(crew_card, "repin_for_review", side_effect=AssertionError("repinned")):
            self.assertIsNone(self.plug._review_guard("kanban_request_review", {}))
        self.card("Verify: proof\n")
        self.assertIsNone(self.plug._review_guard("kanban_complete", {}))

    def test_the_review_guard_runs_inside_the_tool_guard(self):
        self.card("Verify: proof\n")
        res = self.plug.crew_tool_guard(tool_name="kanban_request_review", args={"summary": "x"})
        self.assertEqual("block", res["action"])


class RepinTests(unittest.TestCase):
    """repin_for_review: the review gets the router's `review` pick, or the pin is cleared."""

    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-repin-test-")
        os.environ["HERMES_HOME"] = self.home
        self.db = os.path.join(self.home, "kanban.db")
        os.environ["HERMES_KANBAN_DB"] = self.db
        conn = sqlite3.connect(self.db)
        conn.executescript(
            "create table tasks (id text primary key, title text, status text, assignee text, body text,"
            " model_override text, provider_override text);"
            "create table task_events (id integer primary key autoincrement, task_id text, run_id integer,"
            " kind text, payload text, created_at integer);")
        conn.execute("insert into tasks values ('t_r', 'title', 'running', 'crew-worker', ?, 'writer-model', 'gemini')",
                     (BODY % "Verify: independent\n",))
        conn.execute("insert into tasks values ('t_p', 'title', 'running', 'crew-worker', ?, 'writer-model', 'gemini')",
                     (BODY % "Verify: proof\n",))
        conn.commit()
        conn.close()

    def tearDown(self):
        for key in [k for k in os.environ if k not in self._env]:
            del os.environ[key]
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)

    def pin(self, cid):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute("select model_override, provider_override from tasks where id = ?", (cid,)).fetchone()
        finally:
            conn.close()

    def test_a_review_pick_replaces_the_writers_pin_and_asks_for_the_review_class(self):
        answer = {"label": "gemini:m", "provider": "gemini", "model": "gemini-3-flash-preview", "why": "w",
                  "floor": {"min_context": 64000}, "menu_size": 2}
        calls = []

        def fake_kanban(args, timeout=120):          # `hermes kanban set-model <id> <model> --provider P`
            calls.append(args)
            conn = sqlite3.connect(self.db)
            conn.execute("update tasks set model_override = ?, provider_override = ? where id = ?",
                         (args[2], args[args.index("--provider") + 1], args[1]))
            conn.commit()
            conn.close()
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(crew_card, "route_answer", return_value=answer) as ask, \
                mock.patch.object(crew_card, "_kanban", fake_kanban):
            got = crew_card.repin_for_review("t_r")
        self.assertEqual("pinned", got["action"])
        self.assertEqual([["set-model", "t_r", "gemini-3-flash-preview", "--provider", "gemini"]], calls)
        self.assertEqual("review", ask.call_args.args[0])
        self.assertEqual(("gemini-3-flash-preview", "gemini"), self.pin("t_r"))

    def test_nothing_clearing_the_floor_clears_the_writers_pin_through_the_kernels_set_model(self):
        calls = []

        def fake_kanban(args, timeout=120):
            calls.append(args)
            conn = sqlite3.connect(self.db)
            conn.execute("update tasks set model_override = null, provider_override = null where id = ?", (args[1],))
            conn.commit()
            conn.close()
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(crew_card, "route_answer", return_value={"label": "parent", "floor": {}, "menu_size": 0}), \
                mock.patch.object(crew_card, "_kanban", fake_kanban):
            got = crew_card.repin_for_review("t_r")
        self.assertEqual(("cleared", [["set-model", "t_r"]]), (got["action"], calls))
        self.assertEqual((None, None), self.pin("t_r"))

    def test_a_proof_card_is_never_repinned(self):
        with mock.patch.object(crew_card, "route_answer", side_effect=AssertionError("asked the router")):
            self.assertEqual("unchanged", crew_card.repin_for_review("t_p")["action"])
        self.assertEqual(("writer-model", "gemini"), self.pin("t_p"))


if __name__ == "__main__":
    unittest.main()
