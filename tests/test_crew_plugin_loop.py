#!/usr/bin/env python3
"""Unit tests for the plugin's side of the coordinator loop (__init__.py).

The dispatch-tick hook that starts a pass, the decision turn's read-only guard, and the command table that
no longer carries the passes the loop replaced. The plugin is loaded from the package source with a throwaway
HERMES_HOME; nothing here starts a real process (Popen is replaced) or reads a board.
"""
import importlib.util
import os
import shutil
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
                                          lock_live=lambda board: self.live,
                                          has_work=lambda board: self.work,
                                          crew_safety=types.SimpleNamespace(proof_env=lambda: {"SCRUBBED": "1"}))
        self.live = False
        self.work = True
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
        self.assertEqual({"SCRUBBED": "1"}, kw["env"])                 # the pass never inherits the gateway's env

    def test_a_board_with_no_new_crew_event_starts_no_process(self):
        self.work = False
        P.crew_tick(board="proofs", dry_run=False, outcome="idle")
        self.assertEqual([], self.started)

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

    def test_the_intakes_watcher_command_is_not_blocked_in_the_intake_or_any_role(self):
        cmd = 'python3 "$HERMES_HOME/plugins/crew/scripts/crew_card.py" watch --card t_d3c396cd'
        for role, turn in (("", False), ("coordinator", False), ("coordinator", True), ("verifier", False)):
            with self.subTest(role=role, turn=turn):
                self.assertIsNone(self.guard("terminal", {"command": cmd, "background": True,
                                                          "notify_on_complete": True}, turn=turn, role=role))

    def test_a_writing_command_is_refused(self):
        for cmd in ("echo x > /tmp/f", "hermes kanban complete t_1", "rm -rf x", "git commit -m x"):
            with self.subTest(cmd=cmd):
                self.assertEqual("block", (self.guard("terminal", {"command": cmd}) or {}).get("action"))

    def test_a_raw_board_or_consent_write_is_refused_for_every_role(self):
        for cmd in ("sqlite3 $HERMES_KANBAN_DB \"insert into task_events ...\"",
                    "python3 -c 'import crew_card; crew_card.owner_proof_answer(\"t_x\", True)'",
                    "grep proof_confirm $HERMES_KANBAN_DB"):
            for role in ("worker", "content", "verifier", "coordinator"):
                with self.subTest(cmd=cmd, role=role):
                    self.assertEqual("block",
                                     (self.guard("terminal", {"command": cmd}, turn=False, role=role) or {}).get("action"))

    def test_a_script_that_writes_the_board_is_refused_before_it_exists(self):
        bodies = (
            "import sqlite3; sqlite3.connect(d).execute(\"insert into task_events (task_id, kind) values\")",
            "\"\"\"UPDATE task_events SET payload = '{}'\"\"\"",
            "import crew_card; crew_card.owner_proof_answer(\"t_x\", True)",
        )
        for body in bodies:
            for role in ("worker", "content", "verifier", "coordinator"):
                with self.subTest(body=body, role=role):
                    self.assertEqual("block", (self.guard("write_file", {"path": "/tmp/x.py", "content": body},
                                                           turn=False, role=role) or {}).get("action"))
                    self.assertEqual("block", (self.guard("patch", {"path": "/tmp/x.py", "patch": body},
                                                           turn=False, role=role) or {}).get("action"))

    def test_a_proof_script_that_only_reads_the_board_is_still_allowed(self):
        body = ("import sqlite3\n"
                "rows = sqlite3.connect(db).execute(\"select kind, payload from task_events order by id\")\n"
                "print(len(rows.fetchall()))\n")
        for role in ("worker", "content", "verifier", "coordinator"):
            with self.subTest(role=role):
                self.assertIsNone(self.guard("write_file", {"path": "/tmp/read_board.py", "content": body},
                                             turn=False, role=role))

    def test_a_role_agent_cannot_flip_the_proof_safety_switch(self):
        for role in ("worker", "content", "verifier", "coordinator"):
            with self.subTest(role=role):
                for cmd in ("hermes -p crew-coordinator config set approvals.mode off",
                            "hermes -p crew-worker config set approvals.mode brave",
                            "python3 -c 'import os; print(os.environ.get(\"approvals.mode\"))'"):
                    self.assertEqual("block", (self.guard("terminal", {"command": cmd}, turn=False,
                                                          role=role) or {}).get("action"), cmd)
                self.assertEqual("block", (self.guard("write_file", {
                    "path": os.path.join(tempfile.gettempdir(), "profiles", "crew-coordinator", "config.yaml"),
                    "content": "approvals:\n  mode: off\n"}, turn=False, role=role) or {}).get("action"))

    def test_reading_config_stays_possible(self):
        for role in ("worker", "content", "verifier", "coordinator"):
            with self.subTest(role=role):
                self.assertIsNone(self.guard("terminal", {"command": "hermes -p crew-worker config get crew.role"},
                                             turn=False, role=role))
                self.assertIsNone(self.guard("terminal", {"command": "python3 -m pytest -q tests/"},
                                             turn=False, role=role))

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

    def test_unstuck_takes_exactly_one_card_id_and_answers_with_the_tools_text(self):
        tool = mock.Mock()
        tool.unstuck_card.return_value = (True, "t_1: triage -> ready")
        with mock.patch.object(P, "_card_tool", return_value=tool):
            handler = P._option_handler("unstuck")
            self.assertEqual("Usage: /crew-unstuck <card id>", handler(""))
            self.assertEqual("Usage: /crew-unstuck <card id>", handler("t_1 t_2"))
            tool.unstuck_card.assert_not_called()
            self.assertEqual("t_1: triage -> ready", handler(" t_1 "))
        tool.unstuck_card.assert_called_once_with("t_1")

    def test_the_options_that_stay_are_the_documented_ones(self):
        self.assertEqual(["status", "graph", "stop", "unstuck", "safety", "proof"],
                         [a for _n, a, _h, _d in P.COMMANDS])

    def test_the_platform_menu_is_the_skills_around_the_plugin_commands(self):
        spec = importlib.util.spec_from_file_location("crew_install_menu", str(REPO / "install.py"))
        inst = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(inst)
        self.assertEqual(["crew"] + [n for n, _a, _h, _d in P.COMMANDS] + ["crew-diagnose"], inst.CREW_MENU_ORDER)


class SafetyCommandTests(unittest.TestCase):
    """/crew-safety: no argument shows the mode; brave and safe switch Hermes's approvals.mode on every crew profile
    and safe puts back what each profile had before brave."""

    def setUp(self):
        from hermes_fake import FakeConfig
        self.cfg = FakeConfig()
        self.cfg.seed("crew-coordinator", approvals__mode="smart")
        self.cfg.seed("crew-worker", approvals__mode="manual")
        self.cfg.seed("crew-content", approvals__mode="manual")
        self.home = tempfile.mkdtemp()
        self.tool = mock.Mock()
        self.tool.base_home.return_value = self.home
        self.tool.roles_defaults.return_value = {"roles": [{"name": "coordinator"}, {"name": "worker"},
                                                           {"name": "content"}]}
        self.tool.profile_prefix.return_value = "crew-"
        self.tool.profile_exists.side_effect = lambda n: n != "crew-content"
        self.tool.crew_safety.permanent_mode.return_value = "safe"

        def run(cmd, **kw):
            return self.cfg(cmd[cmd.index("-p") + 1], *cmd[cmd.index("-p") + 2:])
        for p in (mock.patch.object(P, "_card_tool", lambda: self.tool),
                  mock.patch.object(P, "_hermes_bin", lambda: "hermes"),
                  mock.patch.object(P.subprocess, "run", run)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.home, True)

    def mode(self, profile):
        return self.cfg.store[profile]["approvals.mode"]

    def test_no_argument_shows_the_mode_and_changes_nothing(self):
        self.assertIn("crew proof safety: safe", P._cmd_safety(""))
        self.assertEqual([], self.calls)

    def test_no_argument_shows_the_mode_and_changes_nothing(self):
        self.assertIn("crew proof safety: safe", P._cmd_safety(""))
        self.assertEqual([], [c for c in self.cfg.calls if c[1:3] == ("config", "set")])

    def test_brave_sets_off_and_safe_restores_each_profiles_own_value(self):
        text = P._cmd_safety("brave")
        self.assertEqual(("off", "off"), (self.mode("crew-coordinator"), self.mode("crew-worker")))
        self.assertIn("crew-coordinator: smart -> off", text)
        self.assertIn("workers' own terminal commands run unprompted", text)
        text = P._cmd_safety("safe")
        self.assertEqual(("smart", "manual"), (self.mode("crew-coordinator"), self.mode("crew-worker")))
        self.assertIn("crew-coordinator: off -> smart", text)

    def test_brave_twice_keeps_the_original_and_safe_without_state_falls_back_to_manual(self):
        P._cmd_safety("brave")
        P._cmd_safety("brave")                                  # must not overwrite smart with off
        P._cmd_safety("safe")
        self.assertEqual("smart", self.mode("crew-coordinator"))
        self.cfg.seed("crew-worker", approvals__mode="off")     # brave set by hand, nothing kept
        P._cmd_safety("safe")
        self.assertEqual("manual", self.mode("crew-worker"))

    def test_safe_leaves_a_value_that_is_not_off_alone(self):
        P._cmd_safety("safe")
        self.assertEqual("smart", self.mode("crew-coordinator"))
        self.assertEqual([], [c for c in self.cfg.calls if c[1:3] == ("config", "set")])

    def test_a_bad_word_is_a_usage_line(self):
        self.assertEqual("usage: /crew-safety [brave|safe]", P._cmd_safety("yolo"))



if __name__ == "__main__":
    unittest.main()
