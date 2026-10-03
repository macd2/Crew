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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hermes_fake import FakeConfig  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("crew_install", str(REPO / "install.py"))
CI = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CI)


def approve(home, event, command):
    """What Hermes records when the owner confirms a hook; the installer has no writer for it."""
    path = os.path.join(home, CI.ALLOWLIST_NAME)
    data = json.load(open(path)) if os.path.exists(path) else {"approvals": []}
    data["approvals"].append({"event": event, "command": command, "approved_at": CI._iso(time.time()),
                              "script_mtime_at_approval": CI._mtime_iso(command)})
    with open(path, "w") as fh:
        json.dump(data, fh)
    os.chmod(path, 0o600)


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
        approve(self.home, "pre_tool_call", self.hook)
        self.assertEqual([], CI.permission_problems(self.home))

    def test_another_pair_approved_is_not_this_one(self):
        approve(self.home, "post_tool_call", self.hook)
        problems = CI.permission_problems(self.home)
        self.assertTrue(any("declared but not approved" in p for p in problems), problems)

    def test_a_script_that_changed_after_approval_is_a_finding(self):
        approve(self.home, "pre_tool_call", self.hook)
        later = time.time() + 3600      # the script was edited after it was approved
        os.utime(self.hook, (later, later))
        problems = CI.permission_problems(self.home)
        self.assertTrue(any("approval drift" in p for p in problems), problems)

    def test_a_helper_with_no_hooks_is_never_a_finding(self):
        other = os.path.join(self.tmp, "plain")
        write_config(other, "model:\n  provider: anthropic\n")
        self.assertEqual([], CI.permission_problems(other))

    def test_a_home_without_the_exec_bit_is_a_finding(self):
        approve(self.home, "pre_tool_call", self.hook)
        os.chmod(self.hook, 0o644)
        problems = CI.permission_problems(self.home)
        self.assertTrue(any("not executable" in p for p in problems), problems)

    def test_a_record_that_is_not_0600_is_a_finding(self):
        approve(self.home, "pre_tool_call", self.hook)
        os.chmod(os.path.join(self.home, CI.ALLOWLIST_NAME), 0o644)
        problems = CI.permission_problems(self.home)
        self.assertTrue(any("mode 644" in p for p in problems), problems)

    def test_a_record_the_runtime_cannot_parse_is_a_finding(self):
        with open(os.path.join(self.home, CI.ALLOWLIST_NAME), "w") as fh:
            fh.write("{not json")
        problems = CI.permission_problems(self.home)
        self.assertTrue(any("no approvals list" in p or "unreadable" in p for p in problems), problems)


class NoApprovalWriterTests(unittest.TestCase):
    """Consent is Hermes's: the installer reads the allowlist, reports what is missing, and never writes it."""

    def test_the_installer_has_no_approval_writer_and_sets_no_accept_hooks_env(self):
        self.assertFalse(hasattr(CI, "_approve"))
        self.assertNotIn("HERMES_ACCEPT_HOOKS", (REPO / "install.py").read_text())

    def test_the_step_reports_with_the_hermes_command_and_writes_nothing(self):
        tmp = tempfile.mkdtemp(prefix="crew-perm-unit-")
        home = os.path.join(tmp, "home")
        hook = os.path.join(home, "gate.py")
        os.makedirs(home)
        Path(hook).write_text("#!/bin/sh\n")
        os.chmod(hook, 0o755)
        write_config(home, "hooks:\n  pre_tool_call:\n    - command: %s\n" % hook)
        saved = CI._role_plans
        CI._role_plans = lambda prefix: []
        self.addCleanup(setattr, CI, "_role_plans", saved)
        for apply in (False, True):
            status, detail = CI.step_permissions(home, "owner", "crew-", apply)
            self.assertEqual("FAILED", status)
            self.assertIn("hermes -p owner chat", detail)
            self.assertIn("hermes -p owner hooks doctor", detail)
            self.assertFalse(os.path.exists(os.path.join(home, CI.ALLOWLIST_NAME)))


class SettingsProblemTests(unittest.TestCase):
    """settings_problems: the role's own settings.conf against the profile's config, read through `hermes config get`."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-perm-unit-")
        self.tpl = os.path.join(self.tmp, "tpl")
        os.makedirs(self.tpl)
        with open(os.path.join(self.tpl, "settings.conf"), "w") as fh:
            fh.write("crew.role = worker\n"
                     "fallback_providers = []\n"
                     "# a comment line is ignored\n"
                     "platforms.slack.enabled = false\n")
        self.cfg = FakeConfig()
        self.addCleanup(setattr, CI, "h", CI.h)
        CI.h = self.cfg

    def good(self, **over):
        keys = {"crew.role": "worker", "fallback_providers": "[]", "platforms.slack.enabled": "false"}
        keys.update(over)
        self.cfg.store["p"] = keys

    def test_a_matching_profile_is_clean(self):
        self.good()
        self.assertEqual([], CI.settings_problems("p", "worker", self.tpl))

    def test_a_wrong_role_is_a_finding(self):
        self.good(**{"crew.role": "content"})
        problems = CI.settings_problems("p", "worker", self.tpl)
        self.assertTrue(any("crew.role" in p for p in problems), problems)

    def test_slack_left_on_is_a_finding(self):
        self.good(**{"platforms.slack.enabled": "true"})
        problems = CI.settings_problems("p", "worker", self.tpl)
        self.assertTrue(any("platforms.slack.enabled" in p for p in problems), problems)

    def test_an_unset_profile_is_a_finding_for_every_key(self):
        self.assertEqual(3, len(CI.settings_problems("p", "worker", self.tpl)))

    def test_no_template_settings_is_clean(self):
        self.assertEqual([], CI.settings_problems("p", "worker", os.path.join(self.tmp, "none")))


class PrefixSettingsTests(unittest.TestCase):
    """A `{prefix}` in a settings.conf value is the installer's --profile-prefix, in both the writer and the reader."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-perm-unit-")
        self.tpl = os.path.join(self.tmp, "tpl")
        os.makedirs(self.tpl)
        with open(os.path.join(self.tpl, "settings.conf"), "w") as fh:
            fh.write("kanban.auto_decompose = false\nkanban.orchestrator_profile = {prefix}coordinator\n")
        self.saved = CI.PROFILE_PREFIX
        self.addCleanup(setattr, CI, "PROFILE_PREFIX", self.saved)
        self.cfg = FakeConfig()
        self.addCleanup(setattr, CI, "h", CI.h)
        CI.h = self.cfg

    def test_the_prefix_is_expanded_when_applied_and_when_checked(self):
        CI.PROFILE_PREFIX = "kc-"
        self.cfg.seed("p", kanban__orchestrator_profile="owner-chat", kanban__auto_decompose="true")
        changed = CI._apply_settings("p", os.path.join(self.tpl, "settings.conf"))
        self.assertEqual(["kanban.auto_decompose", "kanban.orchestrator_profile"], changed)
        self.assertIn(("p", "config", "set", "kanban.orchestrator_profile", "kc-coordinator"), self.cfg.calls)
        self.assertEqual("kc-coordinator", CI._cfg("p", "kanban.orchestrator_profile"))
        self.assertEqual("false", CI._cfg("p", "kanban.auto_decompose"))
        self.assertEqual([], CI.settings_problems("p", "worker", self.tpl))
        self.assertEqual([], CI._apply_settings("p", os.path.join(self.tpl, "settings.conf")), "second apply: no writes")

    def test_a_home_on_another_prefix_is_a_finding(self):
        CI.PROFILE_PREFIX = "crew-"
        self.cfg.seed("p", kanban__orchestrator_profile="kc-coordinator", kanban__auto_decompose="false")
        problems = CI.settings_problems("p", "worker", self.tpl)
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
        cfg, saved = FakeConfig(), CI.h
        CI.h = cfg
        self.addCleanup(setattr, CI, "h", saved)
        dotted = "platforms.telegram.extra.command_menu.priority"
        cfg.seed("p", **{dotted + "_mode": "prepend", dotted: "[crew,crew-status,crew-run,crew-verify]"})
        status, detail = CI.step_menu_priority("p", False, True)
        self.assertEqual("CHANGED", status, detail)
        self.assertEqual(["crew", "crew-status", "crew-graph", "crew-stop", "crew-unstuck", "crew-safety", "crew-diagnose"], CI.CREW_MENU_ORDER)
        self.assertFalse([c for c in cfg.calls if c[1:3] == ("config", "set")], "--check writes nothing")
        self.assertEqual("CHANGED", CI.step_menu_priority("p", True, True)[0])
        self.assertEqual("OK", CI.step_menu_priority("p", False, True)[0])

    def test_without_the_flag_the_menu_is_not_touched(self):
        cfg, saved = FakeConfig(), CI.h
        CI.h = cfg
        self.addCleanup(setattr, CI, "h", saved)
        self.assertEqual("SKIP", CI.step_menu_priority("p", True, False)[0])
        self.assertEqual([], cfg.calls)


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
            self.assertEqual("CHANGED", CI.step_chat_kanban("p", False, True)[0])
            self.assertFalse([c for c in calls if c[:2] == ("tools", "enable")])      # --check changes nothing
            self.assertEqual("CHANGED", CI.step_chat_kanban("p", True, True)[0])
            self.assertEqual(sorted(CI.CHAT_KANBAN_PLATFORMS),
                             sorted(c[-1] for c in calls if c[:2] == ("tools", "enable")))
            calls.clear()
            self.assertEqual("OK", CI.step_chat_kanban("p", True, True)[0])
            self.assertFalse([c for c in calls if c[:2] == ("tools", "enable")])
        finally:
            CI.h = orig

    def test_without_the_flag_nothing_is_read_or_enabled(self):
        orig = CI.h
        try:
            CI.h, calls = self.fake_h({p: False for p in CI.CHAT_KANBAN_PLATFORMS})
            self.assertEqual("SKIP", CI.step_chat_kanban("p", True, False)[0])
            self.assertEqual([], calls)
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
            self.assertEqual("FAILED", CI.step_chat_kanban("p", True, True)[0])
        finally:
            CI.h = orig


class OptInStepsTests(unittest.TestCase):
    """Nothing beyond crew's own files is written without its flag; the nightly cron's delivery is local by default."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-optin-unit-")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.home, "scripts"))
        self.cfg = FakeConfig()
        self.saved = (CI.h, CI._cron_id)
        self.addCleanup(lambda: setattr(CI, "h", self.saved[0]) or setattr(CI, "_cron_id", self.saved[1]))
        CI.h = self.cfg
        self.registered = {}
        CI._cron_id = lambda profile, name: self.registered.get(name)

    def test_the_nightly_cron_needs_its_flag_and_delivers_locally_by_default(self):
        status, detail = CI.step_proofs_cron("p", self.home, True, False)
        self.assertEqual("SKIP", status, detail)
        self.assertEqual([], self.cfg.calls)
        self.assertEqual("local", CI.CRON_PROOFS_DELIVER)
        status, detail = CI.step_proofs_cron("p", self.home, True, False, nightly=True)
        self.assertEqual("CHANGED", status, detail)
        create = [c for c in self.cfg.calls if c[1:3] == ("cron", "create")][0]
        self.assertEqual("local", create[create.index("--deliver") + 1])
        self.assertEqual("crew_proofs.sh", create[create.index("--script") + 1])
        shim = Path(self.home, "scripts", "crew_proofs.sh")
        self.assertEqual(CI.PROOFS_SHIM_TEXT, shim.read_text())
        self.assertTrue(os.access(shim, os.X_OK))
        self.assertIn("plugins/crew/scripts/crew_proofs.py", shim.read_text())

    def test_proofs_deliver_overrides_the_target_and_no_cron_wins(self):
        CI.step_proofs_cron("p", self.home, True, False, nightly=True, deliver="telegram")
        create = [c for c in self.cfg.calls if c[1:3] == ("cron", "create")][0]
        self.assertEqual("telegram", create[create.index("--deliver") + 1])
        self.cfg.calls.clear()
        self.assertEqual("SKIP", CI.step_proofs_cron("p", self.home, True, True, nightly=True)[0])
        self.assertEqual([], self.cfg.calls)

    def test_a_cron_registered_earlier_stays_and_its_old_script_becomes_the_shim(self):
        self.registered["Crew proofs (nightly)"] = "abc12345"
        old = Path(self.home, "scripts", "crew_proofs.sh")
        old.write_text("#!/bin/sh\nexec python3 \"$(dirname \"$0\")/crew_proofs.py\" --quiet \"$@\"\n")
        status, _detail = CI.step_proofs_cron("p", self.home, True, False)
        self.assertEqual("OK", status)
        status, detail = CI.step_scripts(self.home, True)
        self.assertEqual("CHANGED", status, detail)
        self.assertEqual(CI.PROOFS_SHIM_TEXT, old.read_text())


class StaleScriptsTests(unittest.TestCase):
    """step_scripts removes only the crew copies an earlier install put in <profile>/scripts, and lists each one."""

    def test_only_crew_files_go_the_owners_own_scripts_stay_and_every_removal_is_printed(self):
        import contextlib
        import io
        home = tempfile.mkdtemp(prefix="crew-stale-unit-")
        scripts = os.path.join(home, "scripts")
        for rel in ("crew_card.py", "crew_dashboard/crew.css", "crew_follow.py", "worker_route.py", "owner_hook.sh"):
            os.makedirs(os.path.dirname(os.path.join(scripts, rel)), exist_ok=True)
            Path(scripts, rel).write_text("x")
        status, detail = CI.step_scripts(home, False)
        self.assertEqual("CHANGED", status)
        self.assertTrue(os.path.exists(os.path.join(scripts, "crew_card.py")), "--check removes nothing")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            CI.step_scripts(home, True)
        for rel in ("crew_card.py", "crew_dashboard/crew.css", "crew_follow.py"):
            self.assertFalse(os.path.exists(os.path.join(scripts, rel)), rel)
            self.assertIn(os.path.join(scripts, rel), buf.getvalue())
        self.assertTrue(os.path.exists(os.path.join(scripts, "worker_route.py")))
        self.assertTrue(os.path.exists(os.path.join(scripts, "owner_hook.sh")))
        self.assertEqual("OK", CI.step_scripts(home, True)[0])


class PluginCarriesScriptsTests(unittest.TestCase):
    def test_the_plugin_copy_includes_every_script(self):
        for rel in CI.SCRIPT_FILES:
            self.assertIn("scripts/" + rel, CI.PLUGIN_FILES)

    def test_step_plugin_copies_scripts_and_is_idempotent(self):
        home = tempfile.mkdtemp(prefix="crew-plugin-unit-")
        self.assertEqual("CHANGED", CI.step_plugin(home, True)[0])
        self.assertTrue(os.path.isfile(os.path.join(home, "plugins", "crew", "scripts", "crew_card.py")))
        self.assertTrue(os.path.isfile(os.path.join(home, "plugins", "crew", "scripts", "crew_dashboard", "crew.css")))
        self.assertEqual("OK", CI.step_plugin(home, False)[0])


class ResolverTests(unittest.TestCase):
    """__init__._script_path looks in the plugin's own tree and crew.source_dir, never in $HERMES_HOME/scripts."""

    def test_a_script_only_in_hermes_home_scripts_is_not_found(self):
        home = tempfile.mkdtemp(prefix="crew-resolve-unit-")
        os.makedirs(os.path.join(home, "scripts"))
        Path(home, "scripts", "crew_nowhere.py").write_text("x")
        spec = importlib.util.spec_from_file_location("crew_plugin_resolve", str(REPO / "__init__.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.HOME = home
        mod._config_get = lambda key: None
        self.assertIsNone(mod._script_path("crew_nowhere.py"))
        self.assertEqual(str(REPO / "scripts" / "crew_card.py"), mod._script_path("crew_card.py"))
        self.assertEqual(str(REPO / "scripts" / "crew_graph.py"), mod._graph_script())

    def test_crew_source_dir_is_the_fallback(self):
        src = tempfile.mkdtemp(prefix="crew-resolve-src-")
        os.makedirs(os.path.join(src, "scripts"))
        Path(src, "scripts", "crew_only_here.py").write_text("x")
        spec = importlib.util.spec_from_file_location("crew_plugin_resolve2", str(REPO / "__init__.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod._config_get = lambda key: src if key == "crew.source_dir" else None
        self.assertEqual(os.path.join(src, "scripts", "crew_only_here.py"), mod._script_path("crew_only_here.py"))

    def test_loading_the_coordinator_leaves_sys_path_and_bare_module_names_alone(self):
        spec = importlib.util.spec_from_file_location("crew_plugin_resolve3", str(REPO / "__init__.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        path_before = list(sys.path)
        had = {n for n in ("crew_card", "crew_handoff", "crew_heal") if n in sys.modules}
        tool = mod._coordinator_tool()
        self.assertEqual(path_before, sys.path)
        self.assertEqual(had, {n for n in ("crew_card", "crew_handoff", "crew_heal") if n in sys.modules})
        self.assertTrue(callable(tool.lock_live) and callable(tool.has_work))
        self.assertEqual(str(REPO / "scripts" / "crew_coordinator.py"), tool.__file__)


if __name__ == "__main__":
    unittest.main()
