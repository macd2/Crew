#!/usr/bin/env python3
"""Unit tests for the plugin's side of the coordinator loop (__init__.py).

The dispatch-tick hook that starts a pass, the decision turn's read-only guard, and the command table that
no longer carries the passes the loop replaced. The plugin is loaded from the package source with a throwaway
HERMES_HOME; nothing here starts a real process (Popen is replaced) or reads a board.
"""
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
os.environ.setdefault("HERMES_BIN", "/bin/false")   # a unit test never starts the real `hermes` (scratch HERMES_HOME bootstraps a runtime and rewrites the live launcher)
_HOME = tempfile.mkdtemp(prefix="crew-plugin-loop-")
os.environ["HERMES_HOME"] = _HOME
spec = importlib.util.spec_from_file_location("crew_plugin_loop_under_test", str(REPO / "__init__.py"))
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)


class TickTests(unittest.TestCase):
    def setUp(self):
        self.started = []
        self.tool = types.SimpleNamespace(__file__=str(REPO / "scripts" / "crew_coordinator.py"),
                                          lock_live=lambda board: self.live)
        self.live = False
        for p in (mock.patch.object(P, "_coordinator_tool", lambda: self.tool),
                  mock.patch.object(P, "HOME", _HOME),
                  mock.patch.object(P.subprocess, "Popen", lambda args, **kw: self.started.append((args, kw)))):
            p.start()
            self.addCleanup(p.stop)

    def test_an_idle_tick_starts_one_detached_pass_for_its_board(self):
        self.assertIsNone(P.crew_tick(board="proofs", dry_run=False, outcome="idle"))
        (args, kw), = self.started
        self.assertEqual(["--once", "--board", "proofs"], args[2:])
        self.assertTrue(kw["start_new_session"])
        self.assertEqual(P.subprocess.DEVNULL, kw["stdin"])

    def test_the_default_board_passes_no_board_flag(self):
        P.crew_tick(board=None, dry_run=False, outcome="ok")
        self.assertEqual(["--once"], self.started[0][0][2:])

    def test_a_live_pass_a_dry_tick_or_a_lock_skipped_tick_start_nothing(self):
        self.live = True
        P.crew_tick(board=None, dry_run=False, outcome="ok")
        self.live = False
        P.crew_tick(board=None, dry_run=True, outcome="ok")
        P.crew_tick(board=None, dry_run=False, outcome="skipped_locked")
        self.assertEqual([], self.started)

    def test_a_missing_script_or_a_failing_start_never_breaks_the_tick(self):
        with mock.patch.object(P, "_coordinator_tool", lambda: None):
            self.assertIsNone(P.crew_tick(board=None, dry_run=False, outcome="ok"))
        with mock.patch.object(P.subprocess, "Popen", mock.Mock(side_effect=OSError("no fork"))):
            self.assertIsNone(P.crew_tick(board=None, dry_run=False, outcome="ok"))

    def test_the_tick_hook_is_registered_and_the_block_route_hook_is_gone(self):
        hooks = []
        ctx = types.SimpleNamespace(register_command=lambda *a, **k: None, register_skill=lambda *a, **k: None,
                                    register_hook=lambda name, fn: hooks.append((name, fn.__name__)))
        P.register(ctx)
        self.assertIn(("on_kanban_dispatch_tick", "crew_tick"), hooks)
        self.assertFalse([h for h in hooks if "block" in h[1]])
        self.assertFalse(hasattr(P, "crew_block_route"))


class DecisionTurnGuardTests(unittest.TestCase):
    def guard(self, tool, args=None, turn=True, role="coordinator"):
        env = {"CREW_COORDINATOR_TURN": "1"} if turn else {}
        with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(P, "_crew_role", lambda: role):
            if not turn:
                os.environ.pop("CREW_COORDINATOR_TURN", None)
            os.environ.pop("HERMES_KANBAN_TASK", None)
            return P.crew_tool_guard(tool_name=tool, args=args or {}, session_id="s", turn_id="t")

    def test_the_turn_changes_nothing_on_the_board(self):
        for tool in ("write_file", "patch", "delegate_task", "execute_code", "kanban_complete", "kanban_block",
                     "kanban_unblock", "kanban_request_review", "kanban_create"):
            with self.subTest(tool=tool):
                self.assertEqual("block", (self.guard(tool) or {}).get("action"))

    def test_reads_and_read_only_commands_are_allowed(self):
        self.assertIsNone(self.guard("read_file"))
        self.assertIsNone(self.guard("terminal", {"command": "hermes kanban show t_1"}))
        self.assertIsNone(self.guard("terminal", {"command": "git log --oneline | head"}))

    def test_a_writing_command_is_refused(self):
        for cmd in ("echo x > /tmp/f", "hermes kanban complete t_1", "rm -rf x", "git commit -m x"):
            with self.subTest(cmd=cmd):
                self.assertEqual("block", (self.guard("terminal", {"command": cmd}) or {}).get("action"))

    def test_outside_a_decision_turn_or_another_role_nothing_is_guarded(self):
        self.assertIsNone(self.guard("write_file", turn=False))
        self.assertIsNone(self.guard("write_file", role="worker"))


class CommandTableTests(unittest.TestCase):
    def test_the_commands_that_went_are_gone_from_every_table(self):
        gone = ("unstale", "heal", "triage", "unblock", "run", "verify", "roles", "install", "ops")
        self.assertFalse([a for _n, a, _h, _d in P.COMMANDS if a in gone])
        for word in gone:
            self.assertNotIn("/crew-" + word, P.USAGE)
        for name in ("_cmd_background", "_cmd_run", "_cmd_roles", "_cmd_install", "_cmd_crew_ops",
                     "SUBCOMMANDS", "ROLES_PATH"):
            self.assertFalse(hasattr(P, name), name)

    def test_the_options_that_stay_are_the_documented_ones(self):
        self.assertEqual(["status", "graph", "stop"], [a for _n, a, _h, _d in P.COMMANDS])

    def test_the_platform_menu_is_the_skills_around_the_plugin_commands(self):
        spec = importlib.util.spec_from_file_location("crew_install_menu", str(REPO / "install.py"))
        inst = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(inst)
        self.assertEqual(["crew"] + [n for n, _a, _h, _d in P.COMMANDS] + ["crew-diagnose"], inst.CREW_MENU_ORDER)


if __name__ == "__main__":
    unittest.main()
