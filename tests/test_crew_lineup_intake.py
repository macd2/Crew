#!/usr/bin/env python3
"""/crew lineup integration: the `--lineup NAME` flag in a /crew ask (raw slash and skill-expanded turn), the detached
installer launch, the lineup lines of the crew facts, the kanban_create wait for a role still being set up, and the
/crew-lineup command.

No hermes CLI, no installer run: HERMES_HOME is throwaway and subprocess.Popen is mocked.
"""
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
os.environ.setdefault("HERMES_BIN", "/bin/false")   # never start the real `hermes`

BODY = """Role: %s
Budget: 500000
Route: none
GOAL: Audit the login form
Artifact: a report
Lands at: /srv/report.md
For: the owner
Constraints: none stated
Done when: the report exists
proof command: test -s /srv/report.md
"""

LINEUP = {"name": "sec", "description": "Audit things",
          "roles": [{"name": "auditor", "purpose": "Finds vulnerabilities, never fixes them."},
                    {"name": "fixer", "purpose": "Fixes what the auditor found."}]}


def load_plugin():
    spec = importlib.util.spec_from_file_location("crew_plugin_lineup_test", str(REPO / "__init__.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class LineupCase(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-lineup-intake-")
        os.environ["HERMES_HOME"] = self.home
        os.environ["HERMES_KANBAN_DB"] = os.path.join(self.home, "kanban.db")
        os.environ["CREW_ROUTER_PLUGIN"] = os.path.join(self.home, "no-router")
        os.environ["CREW_PKG"] = str(REPO)
        for k in ("HERMES_KANBAN_TASK", "HERMES_SESSION_PLATFORM", "HERMES_SESSION_CHAT_ID", "CREW_PROFILE_PREFIX",
                  "CREW_OWNER_PROFILE"):
            os.environ.pop(k, None)
        conn = sqlite3.connect(os.environ["HERMES_KANBAN_DB"])
        conn.executescript(
            "create table tasks (id text primary key, title text, status text, assignee text, body text,"
            " model_override text, provider_override text);"
            "create table task_events (id integer primary key autoincrement, task_id text, run_id text,"
            " kind text, payload text, created_at integer);")
        conn.commit()
        conn.close()
        self.crew = os.path.join(self.home, "crew")
        os.makedirs(os.path.join(self.crew, "lineups"))
        with open(os.path.join(self.crew, "lineups", "sec.json"), "w", encoding="utf-8") as fh:
            json.dump(LINEUP, fh)
        self.plug = load_plugin()
        self.plug._session_origin = lambda: ""
        self.lu = self.plug._lineup_tool()
        self.popen = mock.patch.object(self.plug.subprocess, "Popen")
        self.Popen = self.popen.start()

    def tearDown(self):
        self.popen.stop()
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)

    def make_profile(self, name):
        d = os.path.join(self.home, "profiles", name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "config.yaml"), "w") as fh:
            fh.write("model: {}\n")

    def install_roles(self, writers):
        """An installed roles.json whose writers are `writers` (what the installer leaves behind)."""
        shipped = json.load(open(REPO / "roles" / "roles.json", encoding="utf-8"))
        core = [r for r in shipped["roles"] if r["name"] in ("coordinator", "verifier")]
        shipped["roles"] = [core[0]] + [{"name": w, "kind": "writer", "purpose": "p " + w, "budget_tokens": 900000}
                                        for w in writers] + core[1:]
        d = os.path.join(self.home, "roles", "crew")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "roles.json"), "w", encoding="utf-8") as fh:
            json.dump(shipped, fh)

    def preload(self, msg, session="S1"):
        return self.plug.crew_intake_preload(user_message=msg, session_id=session, turn_id="T1")

    def argv(self):
        self.assertEqual(1, self.Popen.call_count)
        return self.Popen.call_args[0][0]


class FlagTests(LineupCase):
    def test_split_both_forms_anywhere(self):
        s = self.plug._split_lineup
        self.assertEqual(("sec", "fix the login"), s("--lineup sec fix the login"))
        self.assertEqual(("sec", "fix the login"), s("fix --lineup=sec the login"))
        self.assertEqual(("sec", "fix the login"), s("fix the login --lineup sec"))
        self.assertEqual((None, "fix the--lineup x"), s("fix the--lineup x"))
        self.assertEqual(("", "fix"), s("fix --lineup"))

    def test_raw_slash_strips_the_flag_from_brief_and_ask(self):
        out = self.preload("/crew --lineup sec audit the login form")
        self.assertEqual("audit the login form", self.plug._CREW_BRIEFS["S1"])
        self.assertIn('The owner\'s ask is: "audit the login form"', out["context"])
        self.assertIn("`--lineup sec` option was handled", out["context"])

    def test_skill_expanded_turn_strips_the_flag(self):
        msg = '[IMPORTANT: The user has invoked the "crew" skill ...]\n\nbody'
        with mock.patch.object(self.plug, "_expanded_ask", return_value="audit it --lineup=sec now"):
            out = self.preload(msg)
        self.assertEqual("audit it now", self.plug._CREW_BRIEFS["S1"])
        self.assertIn("`--lineup sec` option was handled", out["context"])
        self.assertIn("being set up in the background", out["context"])
        self.assertEqual("sec", self.argv()[-1])

    def test_unknown_lineup_tells_the_model_to_report_and_carry_on(self):
        out = self.preload("/crew --lineup nosuch do a thing")
        self.assertIn("It failed: lineup nosuch:", out["context"])
        self.assertIn("continue the intake with the current crew", out["context"])
        self.Popen.assert_not_called()
        self.assertEqual({}, self.lu.read_state())

    def test_no_flag_no_lineup_text_and_no_launch(self):
        out = self.preload("/crew do a thing")
        self.assertNotIn("--lineup", out["context"])
        self.Popen.assert_not_called()


class LaunchTests(LineupCase):
    def test_background_launch_argv_log_and_state(self):
        self.preload("/crew --lineup sec audit it")
        argv = self.argv()
        self.assertEqual([sys.executable, os.path.join(str(REPO), "install.py"), "--profile", "default",
                          "--lineup", "sec"], argv)
        kw = self.Popen.call_args[1]
        if os.name != "nt":
            self.assertTrue(kw.get("start_new_session"))
        self.assertEqual(os.path.join(self.crew, "lineup-install.log"), kw["stdout"].name)
        st = self.lu.read_state()
        self.assertEqual(("sec", "building", ["auditor", "fixer"]), (st["active"], st["status"], st["roles"]))

    def test_installing_profile_is_the_owner_profile(self):
        os.environ["CREW_OWNER_PROFILE"] = "me"
        self.preload("/crew --lineup sec audit it")
        self.assertEqual(["--profile", "me"], self.argv()[2:4])

    def test_no_launch_when_already_active_and_ready(self):
        self.lu.write_state(active="sec", status="ready", error="", roles=["auditor", "fixer"])
        out = self.preload("/crew --lineup sec audit it")
        self.Popen.assert_not_called()
        self.assertIn("Nothing to set up", out["context"])

    def test_default_with_no_state_is_already_active(self):
        self.preload("/crew --lineup default audit it")
        self.Popen.assert_not_called()

    def test_relaunch_when_the_last_switch_failed(self):
        self.lu.write_state(active="sec", status="failed", error="boom", roles=["auditor"])
        self.preload("/crew --lineup sec audit it")
        self.assertEqual("sec", self.argv()[-1])

    def test_a_popen_failure_is_an_error_text_not_an_exception(self):
        self.Popen.side_effect = OSError("no exec")
        out = self.preload("/crew --lineup sec audit it")
        self.assertIn("installer could not start", out["context"])


class FactsTests(LineupCase):
    def test_facts_list_the_crew_writer_roles(self):
        facts = self.plug._intake_facts()
        self.assertIn("Writer roles in this crew", facts)
        self.assertIn("worker — Code, config", facts)
        self.assertIn("content — Posts", facts)
        self.assertIn("crew-<role>", facts)

    def test_facts_follow_the_installed_roles_json(self):
        self.install_roles(["scout"])
        facts = self.plug._intake_facts()
        self.assertIn("scout — p scout", facts)
        self.assertIn("scout 900000", facts)
        self.assertNotIn("worker —", facts)

    def test_facts_name_the_lineup_being_set_up(self):
        self.lu.write_state(active="sec", status="building", error="", roles=["auditor", "fixer"])
        facts = self.plug._intake_facts()
        self.assertIn("Lineup sec is being set up now", facts)
        self.assertIn("auditor — Finds vulnerabilities", facts)
        self.assertIn("fixer — Fixes", facts)


class CreateGuardTests(LineupCase):
    def setUp(self):
        super().setUp()
        self.plug.LINEUP_WAIT_SECONDS = 1.0
        self.plug.LINEUP_POLL_SECONDS = 0.05
        self.preload("/crew audit the login form")    # an intake window for S1
        self.lu.write_state(active="sec", status="building", error="", roles=["auditor", "fixer"])

    def create(self, role="auditor"):
        return self.plug.crew_tool_guard(tool_name="kanban_create",
                                         args={"title": "Audit", "assignee": "crew-" + role, "body": BODY % role},
                                         session_id="S1", turn_id="T1")

    def test_waits_until_the_profile_and_role_appear(self):
        def finish():
            time.sleep(0.2)
            self.install_roles(["auditor", "fixer"])
            self.make_profile("crew-auditor")
            self.lu.write_state(status="ready")
        t = threading.Thread(target=finish)
        t.start()
        out = self.create()
        t.join()
        self.assertEqual("modify", out["action"], out)
        self.assertEqual("crew-auditor", out["args"]["assignee"])

    def test_times_out_with_retry_message(self):
        out = self.create()
        self.assertEqual("block", out["action"])
        self.assertIn("crew-auditor is still being set up; call kanban_create again in a minute", out["message"])

    def test_refuses_with_the_error_when_the_install_failed(self):
        def fail():
            time.sleep(0.1)
            self.lu.write_state(status="failed", error="bad model name")
        t = threading.Thread(target=fail)
        t.start()
        out = self.create()
        t.join()
        self.assertEqual("block", out["action"])
        self.assertIn("lineup sec failed to install: bad model name", out["message"])

    def test_a_role_in_neither_crew_nor_lineup_is_refused_naming_the_valid_roles(self):
        start = time.time()
        out = self.create("ghost")
        self.assertLess(time.time() - start, 0.5)
        self.assertEqual("block", out["action"])
        self.assertIn("worker or content", out["message"])

    def test_an_installed_role_does_not_wait(self):
        self.make_profile("crew-worker")
        start = time.time()
        out = self.create("worker")
        self.assertLess(time.time() - start, 0.5)
        self.assertEqual("modify", out["action"], out)


class CommandTests(LineupCase):
    def run_cmd(self, rest):
        return self.plug._option_handler("lineup")(rest)

    def test_registered_in_the_command_table(self):
        self.assertIn(("crew-lineup", "lineup"), [(n, a) for n, a, _h, _d in self.plug.COMMANDS])

    def test_overview(self):
        self.lu.write_state(active="sec", status="failed", error="bad model", roles=["auditor"])
        out = self.run_cmd("")
        self.assertIn("crew lineup: sec (failed)", out)
        self.assertIn("error: bad model", out)
        self.assertIn("writer roles: worker", out)
        self.assertIn("default (shipped): worker, content", out)
        self.assertIn("sec (user) - Audit things: auditor, fixer", out)

    def test_overview_without_state_is_the_default_crew(self):
        self.assertIn("crew lineup: default (ready)", self.run_cmd(""))

    def test_use_launches_in_the_background(self):
        out = self.run_cmd("use sec")
        self.assertIn("being set up in the background", out)
        self.assertEqual("sec", self.argv()[-1])

    def test_default_is_use_default(self):
        self.lu.write_state(active="sec", status="ready", roles=["auditor"])
        self.run_cmd("default")
        self.assertEqual(["--lineup", "default"], self.argv()[-2:])
        self.assertEqual("default", self.lu.read_state()["active"])

    def test_uninstall_shows_what_goes_and_starts_only_with_yes(self):
        out = self.run_cmd("uninstall sec")
        self.assertIn("role profiles removed entirely: crew-auditor, crew-fixer", out)
        self.assertIn("stays", out)
        self.assertIn("/crew-lineup uninstall sec --yes", out)
        self.Popen.assert_not_called()
        out = self.run_cmd("uninstall sec --yes")
        self.assertIn("Uninstalling in the background", out)
        self.assertEqual(["--uninstall-lineup", "sec"], self.argv()[-2:])
        self.assertTrue(os.path.isfile(os.path.join(self.crew, "lineups", "sec.json")), "the lineup file stays")

    def test_uninstall_default_is_refused(self):
        self.assertIn("cannot be uninstalled", self.run_cmd("uninstall default --yes"))
        self.Popen.assert_not_called()

    def test_use_unknown_reports_the_error(self):
        self.assertIn("lineup nosuch:", self.run_cmd("use nosuch"))
        self.Popen.assert_not_called()

    def test_show(self):
        out = self.run_cmd("show sec")
        self.assertIn("== auditor: Finds vulnerabilities", out)

    def test_add_previews_and_saves_nothing(self):
        src = os.path.join(self.home, "elsewhere")
        os.makedirs(src)
        other = dict(LINEUP, name="ops")
        with open(os.path.join(src, "ops.json"), "w", encoding="utf-8") as fh:
            json.dump(other, fh)
        out = self.run_cmd("add " + os.path.join(src, "ops.json"))
        self.assertIn("== auditor", out)
        self.assertIn("Nothing saved yet; run /crew-lineup save ops to keep it.", out)
        self.assertFalse(os.path.exists(os.path.join(self.crew, "lineups", "ops.json")))
        saved = self.run_cmd("save ops")
        self.assertIn("lineup ops saved", saved)
        self.assertIn("Nothing was overwritten", saved)
        self.assertTrue(os.path.exists(os.path.join(self.crew, "lineups", "ops.json")))

    def test_save_without_pending_is_an_error_text(self):
        self.assertIn("crew-lineup save failed", self.run_cmd("save nothing"))

    def test_usage(self):
        self.assertTrue(self.run_cmd("frob").startswith("usage: /crew-lineup"))


if __name__ == "__main__":
    unittest.main()
