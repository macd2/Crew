#!/usr/bin/env python3
"""The plugin's side of the native crew tools (__init__.py): registration, the guard matrix by tool name, the
intake window the plan tool closes, and the rule that no model-facing text names a crew_card.py command except
`watch`. The plugin is loaded from source with a throwaway HERMES_HOME."""
import importlib.util
import os
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
os.environ.setdefault("HERMES_BIN", "/bin/false")
_HOME = tempfile.mkdtemp(prefix="crew-tools-guard-")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import module_env  # noqa: E402

module_env.pin(globals(), HERMES_HOME=_HOME)
spec = importlib.util.spec_from_file_location("crew_tools_guard_under_test", str(REPO / "__init__.py"))
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

TOOLS = ["crew_verdict", "crew_progress", "crew_proof_check", "crew_lesson", "crew_plan", "crew_diagnose"]


class FakeCtx:
    def __init__(self):
        self.tools = []
        self.hooks = []

    def register_command(self, *a, **k):
        pass

    def register_skill(self, *a, **k):
        pass

    def register_hook(self, name, fn):
        self.hooks.append((name, fn.__name__))

    def register_tool(self, **kw):
        self.tools.append(kw)


class RegisterTests(unittest.TestCase):
    def test_register_adds_the_six_tools_in_toolset_crew(self):
        if not (REPO / "scripts" / "crew_tools.py").exists():
            self.skipTest("scripts/crew_tools.py is not there yet")
        ctx = FakeCtx()
        P.register(ctx)
        self.assertEqual(sorted(TOOLS), sorted(t["name"] for t in ctx.tools))
        self.assertEqual({"crew"}, {t["toolset"] for t in ctx.tools})

    def test_a_failing_tools_script_does_not_stop_register(self):
        ctx = FakeCtx()
        with mock.patch.object(P, "_load_script", side_effect=RuntimeError("boom")):
            P.register(ctx)
        self.assertIn(("pre_tool_call", "crew_tool_guard"), ctx.hooks)

    def test_plugin_yaml_declares_the_six(self):
        text = (REPO / "plugin.yaml").read_text(encoding="utf-8")
        for name in TOOLS:
            self.assertRegex(text, r"(?m)^  - %s$" % name)


class GuardTests(unittest.TestCase):
    def setUp(self):
        P._CREW_TURNS.clear()
        P._CREW_WINDOWS.clear()
        env = mock.patch.dict(os.environ, {}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        for k in ("HERMES_KANBAN_TASK", "CREW_COORDINATOR_TURN"):
            os.environ.pop(k, None)

    def guard(self, tool, args=None, role="", session="S", turn="T"):
        with mock.patch.object(P, "_crew_role", lambda: role):
            return P.crew_tool_guard(tool_name=tool, args=args or {}, session_id=session, turn_id=turn)

    def test_crew_plan_outside_a_crew_turn_is_refused(self):
        res = self.guard("crew_plan", {"spec": {}})
        self.assertEqual("block", res["action"])
        self.assertIn("crew_plan is refused", res["message"])

    def test_crew_plan_inside_a_crew_turn_is_allowed(self):
        P._CREW_TURNS[P._turn_key("S", "T")] = time.time()
        self.assertIsNone(self.guard("crew_plan", {"spec": {}}))

    def test_crew_plan_in_a_live_intake_window_is_allowed(self):
        P._open_window("S")
        self.assertIsNone(self.guard("crew_plan", {"spec": {}}, turn="T2"))

    def test_crew_plan_with_a_kanban_task_is_allowed(self):
        os.environ["HERMES_KANBAN_TASK"] = "t_x"
        with mock.patch.object(P, "_card_budget", lambda c: 0):
            self.assertIsNone(self.guard("crew_plan", {"spec": {}}, role="worker"))

    def test_a_terminal_card_open_is_still_refused_outside_a_crew_turn(self):
        cmd = 'sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" crew_card.py open --title X'
        res = self.guard("terminal", {"command": cmd})
        self.assertEqual("block", res["action"])
        self.assertIn("crew_card.py open is refused", res["message"])

    def test_a_terminal_card_open_with_a_kanban_task_is_allowed(self):
        # The same rule as crew_plan and kanban_create: a role process may open a card.
        os.environ["HERMES_KANBAN_TASK"] = "t_x"
        cmd = 'sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" crew_card.py open --title X'
        with mock.patch.object(P, "_card_budget", lambda c: 0):
            self.assertIsNone(self.guard("terminal", {"command": cmd}, role="worker"))

    def test_verifier_cannot_plan_but_can_verdict(self):
        os.environ["HERMES_KANBAN_TASK"] = "t_x"
        with mock.patch.object(P, "_card_budget", lambda c: 0), mock.patch.object(P, "_verdict_fails", lambda c: 0):
            res = self.guard("crew_plan", {"spec": {}}, role="verifier")
            self.assertEqual("block", res["action"])
            self.assertIn("verifier has no write/send tools", res["message"])
            for tool in ("crew_verdict", "crew_progress", "crew_lesson", "crew_proof_check", "crew_diagnose"):
                with self.subTest(tool=tool):
                    self.assertIsNone(self.guard(tool, {"card": "t_x"}, role="verifier"))

    def test_the_coordinator_turn_cannot_act_through_the_tools(self):
        os.environ["CREW_COORDINATOR_TURN"] = "1"
        for tool in ("crew_verdict", "crew_progress", "crew_lesson", "crew_plan"):
            with self.subTest(tool=tool):
                res = self.guard(tool, {}, role="coordinator")
                self.assertEqual("block", res["action"])
        for tool in ("crew_proof_check", "crew_diagnose"):
            with self.subTest(tool=tool):
                self.assertIsNone(self.guard(tool, {}, role="coordinator"))


class OpenHookTests(unittest.TestCase):
    def setUp(self):
        P._CREW_WINDOWS.clear()

    def test_a_plan_result_without_error_closes_the_window(self):
        P._open_window("S")
        P.crew_open_hook(tool_name="crew_plan", args={}, result='{"parent": "t_1", "children": []}', session_id="S")
        self.assertFalse(P._window_live("S"))

    def test_a_plan_result_with_error_keeps_the_window(self):
        P._open_window("S")
        P.crew_open_hook(tool_name="crew_plan", args={}, result='{"error": "refused: no proof"}', session_id="S")
        self.assertTrue(P._window_live("S"))


class NoShellCommandNamedTests(unittest.TestCase):
    """Model-facing text names the tool, never a crew_card.py command. The one line allowed to is `watch`."""
    ANY = re.compile(r"crew_card\.py\s+(?!watch\b)\S+")
    ALLOWED = {"skills/crew/SKILL.md": 1}   # the one `crew_card.py watch` line

    def test_skills_name_no_crew_card_command_but_watch(self):
        found = {}
        for path in sorted((REPO / "skills").rglob("*.md")):
            rel = path.relative_to(REPO).as_posix()
            text = path.read_text(encoding="utf-8")
            self.assertEqual([], self.ANY.findall(text), rel)
            n = len(re.findall(r"crew_card\.py\s+watch\b", text))
            if n:
                found[rel] = n
        self.assertEqual(self.ALLOWED, found)

    def test_card_bodies_name_the_tool_not_the_script(self):
        """The contract text the plugin writes into a card is model-facing too: the verifier read `python3 <script>
        verdict --card` there on 2026-10-18 and shelled out instead of calling crew_verdict."""
        import crew_card
        for mode in ("proof", "independent"):
            body = crew_card.render_body({"title": "t", "role": "worker", "goal": "g", "artifact": "a", "lands": "l",
                                          "audience": "o", "done_when": "d", "proof_cmd": "true", "verify": mode,
                                          "budget": 200000})
            self.assertIn("crew_verdict(card=<this card id>)", body, mode)
            self.assertNotIn("verdict --card", body, mode)
        body = crew_card.render_body({"title": "t", "role": "worker", "goal": "g", "artifact": "a", "lands": "l",
                                      "audience": "o", "done_when": "d", "proof_cmd": "true", "verify": "proof",
                                      "budget": 200000, "units": "one|two"})
        self.assertIn("crew_progress(card=<card id>", body)
        self.assertNotIn(" progress --card", body)

    def test_plugin_and_lessons_messages_run_no_crew_card_command(self):
        cmd = re.compile(r"crew_card\.py\s+(verdict|progress|lesson|plan|proof-check|safety)\b|crew-run\.sh[^\n]*crew_card")
        for rel in ("__init__.py", "scripts/crew_lessons.py"):
            text = (REPO / rel).read_text(encoding="utf-8")
            self.assertEqual([], [m.group(0) for m in cmd.finditer(text)], rel)


if __name__ == "__main__":
    unittest.main()
