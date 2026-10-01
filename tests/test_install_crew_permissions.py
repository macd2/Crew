#!/usr/bin/env python3
"""Unit tests for the installer's shell-hook consent helpers (install.py).

The rule these pin: a hook only fires when its (event, command) pair is in that home's
shell-hooks-allowlist.json, so the pair list must come from the home's own config.yaml and the record
the installer writes must be the record the runtime accepts.
"""
import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("crew_install", str(REPO / "install.py"))
CI = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CI)


def write_config(home, body):
    os.makedirs(home, exist_ok=True)
    with open(os.path.join(home, "config.yaml"), "w") as fh:
        fh.write(body)


class DeclaredHooksTests(unittest.TestCase):
    """_declared_hooks: the pairs the runtime will try to fire, read from config.yaml."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-perm-unit-")

    def test_the_matcher_form_yields_the_pair(self):
        home = os.path.join(self.tmp, "matcher")
        write_config(home, "hooks:\n"
                           "  pre_tool_call:\n"
                           "    - matcher: terminal|execute_code\n"
                           "      command: /tmp/gate.py\n"
                           "      timeout: 10\n")
        self.assertEqual([("pre_tool_call", "/tmp/gate.py")], CI._declared_hooks(home))

    def test_the_inline_form_yields_the_pair(self):
        home = os.path.join(self.tmp, "inline")
        write_config(home, "hooks:\n  pre_llm_call:\n    - command: /tmp/llm.py\n")
        self.assertEqual([("pre_llm_call", "/tmp/llm.py")], CI._declared_hooks(home))

    def test_a_bare_string_item_yields_the_pair(self):
        home = os.path.join(self.tmp, "bare")
        write_config(home, "hooks:\n  pre_tool_call:\n    - /tmp/bare.py\n")
        self.assertEqual([("pre_tool_call", "/tmp/bare.py")], CI._declared_hooks(home))

    def test_output_spill_settings_are_not_hooks(self):
        home = os.path.join(self.tmp, "spill")
        write_config(home, "hooks:\n"
                           "  output_spill:\n"
                           "    max_chars: 19000\n"
                           "hooks_auto_accept: false\n")
        self.assertEqual([], CI._declared_hooks(home))

    def test_every_event_in_the_real_shape_is_read(self):
        home = os.path.join(self.tmp, "real")
        write_config(home, "hooks:\n"
                           "  pre_tool_call:\n"
                           "    - matcher: terminal\n      command: /tmp/a.py\n      timeout: 10\n"
                           "    - matcher: tool_call\n      command: /tmp/b.py\n      timeout: 10\n"
                           "  pre_llm_call:\n"
                           "    - matcher: ''\n      command: /tmp/a.py\n      timeout: 10\n"
                           "  output_spill:\n    max_chars: 19000\n"
                           "security:\n  redact_secrets: true\n")
        self.assertEqual([("pre_tool_call", "/tmp/a.py"), ("pre_tool_call", "/tmp/b.py"),
                          ("pre_llm_call", "/tmp/a.py")], CI._declared_hooks(home))

    def test_a_missing_config_is_not_an_error(self):
        self.assertEqual([], CI._declared_hooks(os.path.join(self.tmp, "nothing")))


class ScriptPathTests(unittest.TestCase):
    """_script_path: the runtime's own rule, so the mtime recorded is the one it compares."""

    def test_the_script_token_wins_over_a_launcher(self):
        self.assertEqual("/opt/gate.py", CI._script_path("/usr/bin/python3 /opt/gate.py --strict"))

    def test_a_bare_path_is_itself(self):
        self.assertEqual("/opt/gate.py", CI._script_path("/opt/gate.py"))

    def test_a_command_without_a_script_falls_back_to_the_first_path_like_token(self):
        self.assertEqual("/usr/local/bin/gate", CI._script_path("/usr/local/bin/gate"))

    def test_an_empty_command_is_empty(self):
        self.assertEqual("", CI._script_path(""))


class PermissionProblemTests(unittest.TestCase):
    """permission_problems: the two directions of the gate."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-perm-unit-")
        self.home = os.path.join(self.tmp, "home")
        self.hook = os.path.join(self.home, "hooks", "gate.py")
        os.makedirs(os.path.dirname(self.hook))
        with open(self.hook, "w") as fh:
            fh.write("#!/usr/bin/env python3\nprint('{}')\n")
        os.chmod(self.hook, 0o755)
        write_config(self.home, "hooks:\n  pre_tool_call:\n"
                                "    - matcher: terminal\n      command: %s\n" % self.hook)

    def test_no_record_is_a_finding(self):
        problems = CI.permission_problems(self.home)
        self.assertTrue(any("no consent record" in p for p in problems), problems)

    def test_approved_and_fresh_is_clean(self):
        CI._approve(self.home, "pre_tool_call", self.hook)
        self.assertEqual([], CI.permission_problems(self.home))

    def test_another_pair_approved_is_not_this_one(self):
        CI._approve(self.home, "post_tool_call", self.hook)
        problems = CI.permission_problems(self.home)
        self.assertTrue(any("declared but not approved" in p for p in problems), problems)

    def test_a_script_that_changed_after_approval_is_a_finding(self):
        CI._approve(self.home, "pre_tool_call", self.hook)
        later = time.time() + 3600      # the script was edited after it was approved
        os.utime(self.hook, (later, later))
        problems = CI.permission_problems(self.home)
        self.assertTrue(any("approval drift" in p for p in problems), problems)

    def test_a_helper_with_no_hooks_is_never_a_finding(self):
        other = os.path.join(self.tmp, "plain")
        write_config(other, "model:\n  provider: anthropic\n")
        self.assertEqual([], CI.permission_problems(other))

    def test_a_home_without_the_exec_bit_is_a_finding(self):
        CI._approve(self.home, "pre_tool_call", self.hook)
        os.chmod(self.hook, 0o644)
        problems = CI.permission_problems(self.home)
        self.assertTrue(any("not executable" in p for p in problems), problems)

    def test_a_record_that_is_not_0600_is_a_finding(self):
        CI._approve(self.home, "pre_tool_call", self.hook)
        os.chmod(os.path.join(self.home, CI.ALLOWLIST_NAME), 0o644)
        problems = CI.permission_problems(self.home)
        self.assertTrue(any("mode 644" in p for p in problems), problems)

    def test_a_record_the_runtime_cannot_parse_is_a_finding(self):
        with open(os.path.join(self.home, CI.ALLOWLIST_NAME), "w") as fh:
            fh.write("{not json")
        problems = CI.permission_problems(self.home)
        self.assertTrue(any("no approvals list" in p or "unreadable" in p for p in problems), problems)


class ApproveTests(unittest.TestCase):
    """_approve: the writer both the gate and the runtime accept."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-perm-unit-")
        self.home = os.path.join(self.tmp, "home")
        self.hook = os.path.join(self.home, "hooks", "gate.py")
        os.makedirs(os.path.dirname(self.hook))
        with open(self.hook, "w") as fh:
            fh.write("#!/usr/bin/env python3\nprint('{}')\n")
        os.chmod(self.hook, 0o755)
        write_config(self.home, "hooks:\n  pre_tool_call:\n      command: %s\n" % self.hook)

    def entry(self):
        with open(os.path.join(self.home, CI.ALLOWLIST_NAME)) as fh:
            return json.load(fh)["approvals"]

    def test_it_records_the_runtime_entry_shape(self):
        self.assertEqual("approved", CI._approve(self.home, "pre_tool_call", self.hook))
        entry = self.entry()[0]
        self.assertEqual({"event", "command", "approved_at", "script_mtime_at_approval"},
                         set(entry))
        self.assertEqual("pre_tool_call", entry["event"])
        self.assertTrue(entry["script_mtime_at_approval"].endswith("Z"))

    def test_it_is_idempotent(self):
        CI._approve(self.home, "pre_tool_call", self.hook)
        before = Path(os.path.join(self.home, CI.ALLOWLIST_NAME)).read_bytes()
        self.assertEqual("", CI._approve(self.home, "pre_tool_call", self.hook))
        self.assertEqual(before, Path(os.path.join(self.home, CI.ALLOWLIST_NAME)).read_bytes())

    def test_it_refreshes_a_drifted_pair_and_drops_no_other(self):
        CI._approve(self.home, "post_tool_call", "/tmp/other.py")
        old = time.time() - 3600
        os.utime(self.hook, (old, old))
        CI._approve(self.home, "pre_tool_call", self.hook)
        os.utime(self.hook, None)
        self.assertEqual("refreshed", CI._approve(self.home, "pre_tool_call", self.hook))
        events = sorted(e["event"] for e in self.entry())
        self.assertEqual(["post_tool_call", "pre_tool_call"], events)

    def test_the_record_is_0600(self):
        CI._approve(self.home, "pre_tool_call", self.hook)
        mode = os.stat(os.path.join(self.home, CI.ALLOWLIST_NAME)).st_mode & 0o777
        self.assertEqual(0o600, mode)

    def test_it_replaces_a_record_the_runtime_cannot_parse(self):
        with open(os.path.join(self.home, CI.ALLOWLIST_NAME), "w") as fh:
            fh.write("{not json")
        self.assertEqual("approved", CI._approve(self.home, "pre_tool_call", self.hook))
        self.assertEqual(1, len(self.entry()))


class SettingsProblemTests(unittest.TestCase):
    """settings_problems: the role's own settings.conf against the home's config.yaml."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-perm-unit-")
        self.home = os.path.join(self.tmp, "home")
        self.tpl = os.path.join(self.tmp, "tpl")
        os.makedirs(self.tpl)
        with open(os.path.join(self.tpl, "settings.conf"), "w") as fh:
            fh.write("crew.role = worker\n"
                     "fallback_providers = []\n"
                     "# a comment line is ignored\n"
                     "platforms.slack.enabled = false\n")

    def test_a_matching_home_is_clean(self):
        write_config(self.home, "crew:\n  role: worker\n"
                                "fallback_providers: []\n"
                                "platforms:\n  slack:\n    enabled: false\n")
        self.assertEqual([], CI.settings_problems(self.home, "worker", self.tpl))

    def test_a_wrong_role_is_a_finding(self):
        write_config(self.home, "crew:\n  role: content\n"
                                "fallback_providers: []\n"
                                "platforms:\n  slack:\n    enabled: false\n")
        problems = CI.settings_problems(self.home, "worker", self.tpl)
        self.assertTrue(any("crew.role" in p for p in problems), problems)

    def test_slack_left_on_is_a_finding(self):
        write_config(self.home, "crew:\n  role: worker\n"
                                "fallback_providers: []\n"
                                "platforms:\n  slack:\n    enabled: true\n")
        problems = CI.settings_problems(self.home, "worker", self.tpl)
        self.assertTrue(any("platforms.slack.enabled" in p for p in problems), problems)

    def test_a_missing_config_is_a_finding_for_every_key(self):
        os.makedirs(self.home, exist_ok=True)
        self.assertEqual(3, len(CI.settings_problems(self.home, "worker", self.tpl)))

    def test_no_template_settings_is_clean(self):
        self.assertEqual([], CI.settings_problems(self.home, "worker", os.path.join(self.tmp, "none")))


class PrefixSettingsTests(unittest.TestCase):
    """A `{prefix}` in a settings.conf value is the installer's --profile-prefix, in all three readers."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-perm-unit-")
        self.home = os.path.join(self.tmp, "home")
        self.tpl = os.path.join(self.tmp, "tpl")
        os.makedirs(self.tpl)
        with open(os.path.join(self.tpl, "settings.conf"), "w") as fh:
            fh.write("kanban.auto_decompose = false\nkanban.orchestrator_profile = {prefix}coordinator\n")
        self.saved = CI.PROFILE_PREFIX
        self.addCleanup(setattr, CI, "PROFILE_PREFIX", self.saved)

    def test_the_prefix_is_expanded_when_applied_and_when_checked(self):
        CI.PROFILE_PREFIX = "kc-"
        write_config(self.home, "kanban:\n  orchestrator_profile: owner-chat\n  auto_decompose: true\n")
        changed = CI._apply_settings(self.home, os.path.join(self.tpl, "settings.conf"))
        self.assertEqual(["kanban.auto_decompose", "kanban.orchestrator_profile"], changed)
        self.assertEqual("kc-coordinator", CI._yaml_read_key(self.home, "kanban.orchestrator_profile"))
        self.assertEqual("false", CI._yaml_read_key(self.home, "kanban.auto_decompose"))
        self.assertEqual([], CI.settings_problems(self.home, "worker", self.tpl))

    def test_a_home_on_another_prefix_is_a_finding(self):
        CI.PROFILE_PREFIX = "crew-"
        write_config(self.home, "kanban:\n  orchestrator_profile: kc-coordinator\n  auto_decompose: false\n")
        problems = CI.settings_problems(self.home, "worker", self.tpl)
        self.assertEqual(1, len(problems), problems)
        self.assertIn("crew-coordinator", problems[0])

    def test_every_role_template_carries_the_loop_keys(self):
        for role in ("coordinator", "worker", "content", "verifier"):
            text = (REPO / "templates" / "profiles" / role / "settings.conf").read_text()
            with self.subTest(role=role):
                self.assertIn("kanban.auto_decompose = false", text)
                self.assertIn("kanban.orchestrator_profile = {prefix}coordinator", text)


class RetireCronsTests(unittest.TestCase):
    """The jobs an earlier install registered (the 5-minute self-heal, the weekly observer) are removed by the
    installer: the coordinator loop replaced the first and the observer role is gone."""

    def run_step(self, registered, apply=True, no_cron=False):
        """(status, detail, calls): the step against a fake cron list; `registered` maps name -> id."""
        calls = []

        class Done:
            returncode = 0
            stdout = ""

        live = dict(registered)

        def fake_h(profile, *args):
            calls.append(args)
            if args[:2] == ("cron", "remove"):
                for name, cid in list(live.items()):
                    if cid == args[2]:
                        del live[name]
            return Done()

        orig_id, orig_h = CI._cron_id, CI.h
        CI._cron_id = lambda profile, name: live.get(name)
        CI.h = fake_h
        try:
            status, detail = CI.step_retire_crons("p", apply, no_cron)
        finally:
            CI._cron_id, CI.h = orig_id, orig_h
        return status, detail, calls

    def test_the_names_are_the_heal_job_and_the_observer(self):
        self.assertEqual(("crew self-heal", "Crew observer (weekly)"), CI.OLD_CRON_NAMES)

    def test_both_old_jobs_are_removed_on_apply(self):
        status, detail, calls = self.run_step({"crew self-heal": "abc12345", "Crew observer (weekly)": "def67890"})
        self.assertEqual("CHANGED", status, detail)
        self.assertEqual([("cron", "remove", "abc12345"), ("cron", "remove", "def67890")], calls)

    def test_only_the_one_that_exists_is_removed(self):
        status, _detail, calls = self.run_step({"Crew observer (weekly)": "def67890", "Crew proofs (nightly)": "ffff0000"})
        self.assertEqual("CHANGED", status)
        self.assertEqual([("cron", "remove", "def67890")], calls)        # the nightly proofs job is never touched

    def test_nothing_registered_is_ok_and_check_removes_nothing(self):
        self.assertEqual("OK", self.run_step({})[0])
        status, _detail, calls = self.run_step({"Crew observer (weekly)": "def67890"}, apply=False)
        self.assertEqual(("CHANGED", []), (status, calls))               # --check only reports

    def test_no_cron_skips(self):
        self.assertEqual("SKIP", self.run_step({"Crew observer (weekly)": "def67890"}, no_cron=True)[0])


class MenuPriorityTests(unittest.TestCase):
    """The Telegram menu list is compared whole, so a menu an earlier install wrote (with the commands that
    are gone) is rewritten instead of reported OK because /crew still comes first."""

    def test_menu_names_reads_a_flow_list(self):
        self.assertEqual(["crew", "crew-status"], CI._menu_names("[crew, crew-status]"))
        self.assertEqual(["crew", "crew-status"], CI._menu_names(' [ "crew" , \'crew-status\' ] '))
        self.assertEqual([], CI._menu_names(""))
        self.assertEqual([], CI._menu_names("crew"))

    def test_the_old_menu_with_the_removed_commands_is_a_change(self):
        with tempfile.TemporaryDirectory() as home:
            with open(os.path.join(home, "config.yaml"), "w") as fh:
                fh.write("platforms:\n  telegram:\n    extra:\n      command_menu:\n        priority_mode: prepend\n"
                         "        priority:\n          - crew\n          - crew-status\n          - crew-run\n"
                         "          - crew-verify\n")
            status, detail = CI.step_menu_priority(home, "p", False)
            self.assertEqual("CHANGED", status, detail)
            self.assertEqual(["crew", "crew-status", "crew-graph", "crew-stop", "crew-diagnose"], CI.CREW_MENU_ORDER)
            with open(os.path.join(home, "config.yaml"), "w") as fh:
                fh.write("platforms:\n  telegram:\n    extra:\n      command_menu:\n        priority_mode: prepend\n"
                         "        priority:\n" + "".join("          - %s\n" % n for n in CI.CREW_MENU_ORDER))
            self.assertEqual("OK", CI.step_menu_priority(home, "p", False)[0])


class ChatKanbanToolsetTests(unittest.TestCase):
    """The intake opens the card with kanban_create, which a chat platform offers only with the kanban toolset on."""

    LIST_OFF = "Built-in toolsets (%s):\n  \u2717 disabled  kanban  Kanban\n"
    LIST_ON = "Built-in toolsets (%s):\n  \u2713 enabled  kanban  Kanban\n"

    def fake_h(self, state):
        calls = []

        class Done:
            returncode = 0

            def __init__(self, stdout=""):
                self.stdout = stdout

        def h(profile, *args):
            calls.append(args)
            if args[:2] == ("tools", "list"):
                return Done((self.LIST_ON if state[args[-1]] else self.LIST_OFF) % args[-1])
            if args[:2] == ("tools", "enable"):
                state[args[-1]] = True
            return Done()

        return h, calls

    def test_off_is_enabled_on_apply_only_and_on_is_left_alone(self):
        orig = CI.h
        try:
            state = {p: False for p in CI.CHAT_KANBAN_PLATFORMS}
            CI.h, calls = self.fake_h(state)
            self.assertEqual("CHANGED", CI.step_chat_kanban("p", False)[0])
            self.assertFalse([c for c in calls if c[:2] == ("tools", "enable")])      # --check changes nothing
            self.assertEqual("CHANGED", CI.step_chat_kanban("p", True)[0])
            self.assertEqual(sorted(CI.CHAT_KANBAN_PLATFORMS),
                             sorted(c[-1] for c in calls if c[:2] == ("tools", "enable")))
            calls.clear()
            self.assertEqual("OK", CI.step_chat_kanban("p", True)[0])
            self.assertFalse([c for c in calls if c[:2] == ("tools", "enable")])
        finally:
            CI.h = orig

    def test_a_toolset_that_stays_off_after_enable_is_a_failure(self):
        orig = CI.h
        try:
            state = {p: False for p in CI.CHAT_KANBAN_PLATFORMS}
            CI.h, _calls = self.fake_h(state)
            base = CI.h

            def stubborn(profile, *args):
                return base(profile, *args) if args[:2] != ("tools", "enable") else base(profile, "tools", "noop", "x")
            CI.h = stubborn
            self.assertEqual("FAILED", CI.step_chat_kanban("p", True)[0])
        finally:
            CI.h = orig


if __name__ == "__main__":
    unittest.main()
