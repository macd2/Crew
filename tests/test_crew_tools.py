#!/usr/bin/env python3
"""Tests for scripts/crew_tools.py: the crew functions as Hermes tools, and the CLI paths they share.

Every handler returns a JSON string and never raises. A board is made by Hermes's own code (tests/kernel_board.py);
the proof commands that run are real `true` / `false` subprocesses (our code, not Hermes's), so the verdict file is
the one the CLI would write. Only the hermes CLI (`_kanban`) is stubbed, because HERMES_BIN is /bin/false here.

Run:  python3 -m pytest tests/test_crew_tools.py -q
"""
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
os.environ.setdefault("HERMES_BIN", "/bin/false")   # a unit test never starts the real `hermes`
sys.path.insert(0, str(REPO / "tests"))
from unittest import mock  # noqa: E402

import crew_card  # noqa: E402
import crew_tools  # noqa: E402
import kernel_board as K  # noqa: E402

HANDLERS = crew_tools.HANDLERS
CHILD = {"title": "a", "goal": "g", "role": "worker", "artifact": "a.md", "lands": "/x", "audience": "me",
         "done_when": "d", "budget": 150000, "proof_cmd": "true"}


def call(name, args=None, **kw):
    """The handler's JSON string, parsed (a handler that returns anything but a str fails here)."""
    raw = HANDLERS[name](args if args is not None else {}, **kw)
    assert isinstance(raw, str), (name, raw)
    return json.loads(raw)


class ToolTestCase(unittest.TestCase):
    """A fresh HERMES_HOME per test, the environment restored afterwards, the scratch home removed."""

    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-tools-test-")
        os.environ["HERMES_HOME"] = self.home
        os.environ.pop("CREW_PROFILE_PREFIX", None)
        os.environ.pop("HERMES_KANBAN_DB", None)
        os.environ.pop("KANBAN_DB", None)
        self.addCleanup(self.restore)

    def restore(self):
        for key in [k for k in os.environ if k not in self._env]:
            del os.environ[key]
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)

    def board_card(self, proof):
        """A card on a kernel board whose opening snapshot names `proof`."""
        kb, conn, _db = K.open_board(self.home)
        self.addCleanup(conn.close)
        cid = K.add_card(conn, "running", body=K.BODY.replace("proof command: true", "proof command: " + proof))
        crew_card.record_origin(cid, env={"origin": "", "session": "s"}, proof_cmd=proof)
        return cid

    def verdict_lines(self, cid):
        with open(crew_card.verdict_path(cid), encoding="utf-8") as fh:
            return [json.loads(x) for x in fh if x.strip()]


class HandlerShapeTests(ToolTestCase):
    def test_every_handler_returns_an_error_string_on_empty_and_non_dict_arguments(self):
        for name in HANDLERS:
            for bad in ({}, "x", None, 7, ["a"]):
                got = call(name, bad)
                self.assertIsInstance(got, dict, (name, bad))
        self.assertIn("error", call("crew_verdict", {}))
        self.assertIn("error", call("crew_plan", "x"))

    def test_a_handler_that_raises_comes_back_as_type_and_message(self):
        with mock.patch.object(crew_card, "run_verdict", side_effect=RuntimeError("boom")):
            self.assertEqual({"error": "RuntimeError: boom"}, call("crew_verdict", {"card": "t_x"}))

    def test_a_handler_takes_the_extra_kwargs_hermes_passes(self):
        self.assertIsInstance(HANDLERS["crew_lesson"]({}, task_id="t", extra=1), str)


class VerdictTests(ToolTestCase):
    def test_a_missing_card_is_an_error(self):
        self.board_card("true")
        self.assertEqual({"error": "no such card t_nope"}, call("crew_verdict", {"card": "t_nope"}))

    def test_anchor_a_true_proof_gives_pass_and_one_pass_line_by_the_calling_profile(self):
        """Anchor: a card opened with proof `true` -> verdict PASS, and the verdict file holds exactly one line,
        verdict PASS, `by` = crew_card.current_profile()."""
        cid = self.board_card("true")
        res = call("crew_verdict", {"card": cid, "timeout": 30})
        self.assertEqual(("PASS", 0, "true"), (res["verdict"], res["rc"], res["proof_command"]))
        lines = self.verdict_lines(cid)
        self.assertEqual(1, len(lines))
        self.assertEqual(("PASS", crew_card.current_profile()), (lines[0]["verdict"], lines[0]["by"]))
        self.assertEqual(crew_card.verdict_path(cid), res["file"])

    def test_verdict_accepts_card_id_as_alias_for_card(self):
        cid = self.board_card("true")
        res = call("crew_verdict", {"card_id": cid, "timeout": 30})
        self.assertEqual(("PASS", 0, "true"), (res["verdict"], res["rc"], res["proof_command"]))

    def test_a_false_proof_fails_then_the_second_fail_is_handed_back(self):
        cid = self.board_card("false")
        stub = mock.Mock(returncode=0, stdout="ok", stderr="")
        with mock.patch.object(crew_card, "_kanban", lambda *a, **k: stub) as _:
            first = call("crew_verdict", {"card": cid, "timeout": 30})
            second = call("crew_verdict", {"card": cid, "timeout": 30})
        self.assertEqual(("FAIL", 1), (first["verdict"], first["fails"]))
        self.assertNotIn("handed_back", first)
        self.assertEqual(("FAIL", 2), (second["verdict"], second["fails"]))
        self.assertIn("returned to its writer", second["handed_back"])
        self.assertEqual(2, len(self.verdict_lines(cid)))

    def test_a_blocked_proof_is_blocked_not_a_fail_and_writes_no_line(self):
        cid = self.board_card("true")
        blocked = crew_tools.crew_safety.Result(126, "flagged", "flagged by test")
        with mock.patch.object(crew_card.crew_safety, "run_proof", lambda *a, **k: blocked):
            res = call("crew_verdict", {"card": cid})
        self.assertEqual(("BLOCKED", "flagged by test"), (res["verdict"], res["blocked"]))
        self.assertFalse(os.path.exists(crew_card.verdict_path(cid)))

    def test_run_verdict_text_starts_with_the_result_word(self):
        cid = self.board_card("true")
        res = crew_card.run_verdict(cid, timeout=30)
        self.assertEqual("verdict: PASS", res["text"].splitlines()[0])
        self.assertEqual(0, res["rc"])
        self.assertEqual("error: no such card t_zz", crew_card.run_verdict("t_zz")["text"])

    def test_the_cli_prints_what_run_verdict_returns_and_keeps_its_exit_code(self):
        cid = self.board_card("true")
        args = types.SimpleNamespace(card=cid, command=None, timeout=30, by=None, no_hand_back=False, for_event=None)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = crew_card.cmd_verdict(args)
        self.assertEqual(0, rc)
        self.assertTrue(buf.getvalue().startswith("verdict: PASS\n"))
        self.assertIn("proof command: true", buf.getvalue())
        other = types.SimpleNamespace(card=cid, command="echo hi", timeout=30, by=None, no_hand_back=False,
                                      for_event=None)
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(4, crew_card.cmd_verdict(other))
        self.assertIn("refused", out.getvalue())


class ProgressTests(ToolTestCase):
    def test_a_unit_is_marked_and_the_second_call_lists_it(self):
        first = call("crew_progress", {"card": "t_p", "unit": "u1", "result": "pass", "evidence": "ok"})
        self.assertEqual(("PASS", "writer", 1, 1), (first["result"], first["by"], first["passed"], first["total"]))
        listing = call("crew_progress", {"card": "t_p"})
        self.assertEqual([("u1", True)], [(u["unit"], u["pass"]) for u in listing["units"]])
        self.assertEqual(1, listing["passed"])

    def test_progress_accepts_card_id_as_alias_for_card(self):
        first = call("crew_progress", {"card_id": "t_p", "unit": "u1", "result": "pass", "evidence": "ok"})
        self.assertEqual(("PASS", "writer", 1, 1), (first["result"], first["by"], first["passed"], first["total"]))
        listing = call("crew_progress", {"card_id": "t_p"})
        self.assertEqual([("u1", True)], [(u["unit"], u["pass"]) for u in listing["units"]])

    def test_by_is_verifier_only_for_the_verifier_profile(self):
        with mock.patch.object(crew_card, "current_profile", lambda: "crew-verifier"):
            got = call("crew_progress", {"card": "t_p", "unit": "u1", "result": "fail"})
        self.assertEqual(("FAIL", "verifier"), (got["result"], got["by"]))
        with mock.patch.object(crew_card, "current_profile", lambda: "crew-worker"):
            self.assertEqual("writer", call("crew_progress", {"card": "t_p", "unit": "u2"})["by"])

    def test_a_bad_result_word_is_refused(self):
        self.assertIn("refused", call("crew_progress", {"card": "t_p", "unit": "u", "result": "maybe"})["error"])


class OtherToolTests(ToolTestCase):
    def test_proof_check_returns_the_check_and_the_mode(self):
        with mock.patch.object(crew_tools.crew_safety, "proof_check", lambda c: "flagged: it deletes things"), \
                mock.patch.object(crew_tools.crew_safety, "permanent_mode", lambda: "brave"):
            self.assertEqual({"check": "flagged", "reason": "it deletes things", "safety_mode": "brave"},
                             call("crew_proof_check", {"command": "rm -rf x"}))
        with mock.patch.object(crew_tools.crew_safety, "proof_check", lambda c: "ok"), \
                mock.patch.object(crew_tools.crew_safety, "permanent_mode", lambda: "safe"):
            self.assertEqual({"check": "ok", "reason": "", "safety_mode": "safe"},
                             call("crew_proof_check", {"command": "true"}))

    def test_a_lesson_is_written_and_the_path_returned(self):
        res = call("crew_lesson", {"role": "worker", "text": "check the path before you write"})
        self.assertEqual("worker", res["lesson"])
        with open(res["file"], encoding="utf-8") as fh:
            self.assertIn("check the path before you write", fh.read())

    def test_a_plan_with_an_incomplete_child_is_refused(self):
        res = call("crew_plan", {"spec": {"title": "t", "goal": "g", "children": [{"title": "a"}]}})
        self.assertTrue(res["error"].startswith("refused:"), res)
        self.assertTrue(call("crew_plan", {"spec": {"title": "t"}})["error"].startswith("refused:"))

    def test_a_dry_run_plan_names_the_parent_and_children(self):
        spec = {"title": "t", "goal": "g",
                "children": [dict(CHILD), dict(CHILD, title="b", artifact="b.md")]}
        res = call("crew_plan", {"spec": spec, "dry_run": True})
        self.assertTrue(res["dry_run"])
        self.assertIn("parent", res)
        self.assertEqual(2, len(res["children"]))

    def test_diagnose_without_a_board_says_so_and_an_unknown_state_names_the_valid_ones(self):
        with mock.patch.object(crew_tools._diag, "kanban_db", lambda: None):
            self.assertIn("no board to read", call("crew_diagnose", {})["error"])
        bad = call("crew_diagnose", {"state": "sleeping"})["error"]
        self.assertIn("unknown state", bad)
        self.assertIn("blocked", bad)

    def test_diagnose_reads_a_blocked_card_off_a_kernel_board(self):
        kb, conn, _db = K.open_board(self.home)
        self.addCleanup(conn.close)
        cid = K.add_card(conn, "blocked")
        res = call("crew_diagnose", {})
        self.assertEqual(1, res["count"])
        self.assertIn(cid, res["text"])

    def test_diagnose_accepts_card_id_as_alias_for_card(self):
        kb, conn, _db = K.open_board(self.home)
        self.addCleanup(conn.close)
        cid = K.add_card(conn, "blocked")
        res = call("crew_diagnose", {"card_id": cid})
        self.assertEqual(1, res["count"])
        self.assertIn(cid, res["text"])


class RegisterTests(ToolTestCase):
    def test_six_tools_in_toolset_crew_each_with_schema_and_callable_handler(self):
        calls = []
        crew_tools.register_tools(types.SimpleNamespace(register_tool=lambda **kw: calls.append(kw)))
        self.assertEqual(6, len(calls))
        self.assertEqual({"crew"}, {c["toolset"] for c in calls})
        for c in calls:
            self.assertTrue(callable(c["handler"]) and callable(c["check_fn"]) and c["check_fn"]())
            for key in ("name", "description", "parameters"):
                self.assertTrue(c["schema"].get(key), (c["name"], key))
            self.assertEqual(c["name"], c["schema"]["name"])
        self.assertEqual("object", next(c for c in calls if c["name"] == "crew_plan")["schema"]["parameters"]
                         ["properties"]["spec"]["type"])

    def test_one_failing_registration_does_not_stop_the_others(self):
        seen = []

        def register_tool(**kw):
            if kw["name"] == "crew_lesson":
                raise RuntimeError("taken")
            seen.append(kw["name"])

        with self.assertLogs(crew_tools.log, level="ERROR"):
            crew_tools.register_tools(types.SimpleNamespace(register_tool=register_tool))
        self.assertEqual(5, len(seen))
        self.assertNotIn("crew_lesson", seen)

    def test_schemas_declare_card_id_alias(self):
        calls = []
        crew_tools.register_tools(types.SimpleNamespace(register_tool=lambda **kw: calls.append(kw)))
        tools_map = {c["name"]: c["schema"] for c in calls}
        for name in ("crew_verdict", "crew_progress", "crew_diagnose"):
            props = tools_map[name]["parameters"]["properties"]
            self.assertIn("card", props, f"{name} must declare 'card'")
            self.assertIn("card_id", props, f"{name} must declare 'card_id'")


if __name__ == "__main__":
    unittest.main()
