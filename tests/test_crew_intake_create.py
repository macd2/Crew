#!/usr/bin/env python3
"""Unit tests for the intake's kanban_create path: the contract parsed back out of a body, the tool guard
(gate, gaps, canonical body) and the post hook (origin, brief, units, route event, subscription drop).

No hermes CLI and no live board: HERMES_HOME and the kanban db are throwaway. The plugin module is loaded
AFTER the environment is set, because it reads HERMES_HOME at import time.
"""
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
os.environ.setdefault("HERMES_BIN", "/bin/false")   # a unit test never starts the real `hermes` (scratch HERMES_HOME bootstraps a runtime and rewrites the live launcher)

import crew_card  # noqa: E402

BODY = """Role: worker
Budget: 500000
Route: none
GOAL: Ship the status page
Artifact: a static page
Lands at: /srv/status/index.html
For: the on-call team
Constraints: no new dependencies
Done when: the page answers 200 with the word OK
proof command: curl -fsS http://127.0.0.1:8081/ | grep -q OK
"""


def load_plugin():
    spec = importlib.util.spec_from_file_location("crew_plugin_intake_test", str(REPO / "__init__.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class IntakeCase(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-intake-test-")
        os.environ["HERMES_HOME"] = self.home
        os.environ["HERMES_KANBAN_DB"] = os.path.join(self.home, "kanban.db")
        os.environ["CREW_ROUTER_PLUGIN"] = os.path.join(self.home, "no-router")   # no pick: route stays off
        for k in ("HERMES_KANBAN_TASK", "HERMES_SESSION_PLATFORM", "HERMES_SESSION_CHAT_ID"):
            os.environ.pop(k, None)
        conn = sqlite3.connect(os.environ["HERMES_KANBAN_DB"])
        conn.executescript(
            "create table tasks (id text primary key, title text, status text, assignee text, body text,"
            " model_override text, provider_override text);"
            "create table task_events (id integer primary key autoincrement, task_id text, run_id text,"
            " kind text, payload text, created_at integer);")
        conn.commit()
        conn.close()
        self.plug = load_plugin()
        self.plug._session_origin = lambda: ""

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)

    def guard(self, body=BODY, session="S1", turn="T1", assignee="crew-worker", title="Status page"):
        return self.plug.crew_tool_guard(
            tool_name="kanban_create",
            args={"title": title, "assignee": assignee, "body": body},
            session_id=session, turn_id=turn)

    def open_intake(self, session="S1", ask="put up a status page"):
        self.plug.crew_intake_preload(user_message="/crew " + ask, session_id=session, turn_id="T1")


class ParseContractTests(unittest.TestCase):
    def test_render_then_parse_round_trips_every_contract_field(self):
        c = crew_card.parse_contract(BODY)
        c.update(title="t", coordinator="p/s", origin="zulip:stream:Kanban|crew", units="a|b", route="auto")
        back = crew_card.parse_contract(crew_card.render_body(crew_card.prepare_contract(c)))
        for key in ("role", "goal", "artifact", "lands", "audience", "constraints", "done_when", "proof_cmd",
                    "origin", "units", "route"):
            self.assertEqual(c[key], back[key], key)
        self.assertEqual(500000, back["budget"])

    def test_route_forms(self):
        self.assertEqual(("auto", "", ""), crew_card.parse_route("auto"))
        self.assertEqual(("", "inclusionai/ling-3.0", "ai-gateway"), crew_card.parse_route("inclusionai/ling-3.0/ai-gateway"))
        self.assertEqual(("", "", ""), crew_card.parse_route("none"))
        self.assertEqual(("", "", ""), crew_card.parse_route("nonsense"))

    def test_none_proof_template_is_not_a_proof(self):
        body = BODY.replace("proof command: curl -fsS http://127.0.0.1:8081/ | grep -q OK",
                            "proof command: (none - the verifier asks for one before accepting)")
        self.assertIn("proof command", crew_card.contract_gaps(crew_card.parse_contract(body)))


class CreateGuardTests(IntakeCase):
    def test_outside_a_crew_turn_a_crew_card_is_refused(self):
        res = self.guard()
        self.assertEqual("block", res["action"])
        self.assertIn("/crew", res["message"])

    def test_inside_a_crew_turn_the_body_is_rebuilt_canonical(self):
        self.open_intake()
        res = self.guard()
        self.assertEqual("modify", res["action"])
        new = res["args"]
        self.assertIn("Coordinator: ", new["body"])
        self.assertIn("Verifier: crew-verifier", new["body"])
        self.assertEqual(3600, new["max_runtime_seconds"])
        self.assertEqual(crew_card.role_profile("worker"), new["assignee"])
        self.assertNotIn("model", new)                      # Route: none pins nothing
        self.assertEqual(500000, crew_card.parse_contract(new["body"])["budget"])

    def test_the_answer_turn_of_a_live_window_may_open_the_card(self):
        self.open_intake()
        self.assertEqual("modify", self.guard(turn="T2")["action"])   # not a /crew turn, window is live

    def test_missing_fields_are_named_and_nothing_is_created(self):
        self.open_intake()
        res = self.guard(body=BODY.replace("For: the on-call team\n", "").replace("Done when: ", "Nope: "))
        self.assertEqual("block", res["action"])
        self.assertIn("For", res["message"])
        self.assertIn("Done when", res["message"])

    def test_the_verify_line_defaults_to_proof_is_kept_when_stated_and_a_bad_value_is_refused(self):
        self.open_intake()
        self.assertEqual("proof", crew_card.verify_mode(self.guard()["args"]["body"]))   # a proof command: the writer proves it
        res = self.guard(body=BODY + "Verify: independent\n")
        self.assertEqual("independent", crew_card.verify_mode(res["args"]["body"]))
        bad = self.guard(body=BODY + "Verify: maybe\n")
        self.assertEqual("block", bad["action"])
        self.assertIn("Verify", bad["message"])

    def test_an_under_floor_budget_is_raised_and_the_origin_is_the_plugins(self):
        self.plug._session_origin = lambda: "zulip:stream:Kanban|crew-intake"
        self.open_intake()
        res = self.guard(body=BODY.replace("500000", "1000").replace("Route: none", "Route: none\nOrigin: made-up:x"))
        c = crew_card.parse_contract(res["args"]["body"])
        self.assertEqual(crew_card.budget_floor(), c["budget"])
        self.assertEqual("zulip:stream:Kanban|crew-intake", c["origin"])

    def test_a_hand_pinned_route_reaches_the_create_args(self):
        self.open_intake()
        res = self.guard(body=BODY.replace("Route: none", "Route: acme/ling-3.0/ai-gateway"))
        self.assertEqual("acme/ling-3.0", res["args"]["model"])
        self.assertEqual("ai-gateway", res["args"]["provider"])

    def test_lines_beyond_the_contract_fields_are_kept(self):
        self.open_intake()
        res = self.guard(body=BODY + "second line of the goal\n")
        self.assertIn("second line of the goal", res["args"]["body"])

    def test_a_card_that_is_not_crew_is_not_gated(self):
        res = self.plug.crew_tool_guard(tool_name="kanban_create", session_id="S9", turn_id="T9",
                                        args={"title": "buy milk", "assignee": "helper", "body": "milk"})
        self.assertIsNone(res)

    def test_a_coordinator_or_worker_process_may_create_children(self):
        os.environ["HERMES_KANBAN_TASK"] = "t_parent"
        self.assertIsNone(self.guard())

    def test_a_guard_error_blocks_instead_of_letting_the_call_through(self):
        self.open_intake()
        self.plug._create_guard = lambda *a, **k: 1 / 0
        self.assertEqual("block", self.guard()["action"])


class FinishCreatedCardTests(IntakeCase):
    def create(self, body, model="", provider=""):
        conn = sqlite3.connect(os.environ["HERMES_KANBAN_DB"])
        conn.execute("insert into tasks (id, title, status, assignee, body, model_override, provider_override)"
                     " values ('t_new1', 'Status page', 'ready', 'crew-worker', ?, ?, ?)", (body, model, provider))
        conn.commit()
        conn.close()
        return json.dumps({"ok": True, "task_id": "t_new1", "status": "ready", "subscribed": False})

    def events(self):
        conn = sqlite3.connect(os.environ["HERMES_KANBAN_DB"])
        rows = conn.execute("select kind, payload from task_events where task_id = 't_new1' order by id").fetchall()
        conn.close()
        return [(k, json.loads(p)) for k, p in rows]

    def test_origin_and_brief_are_recorded_and_the_window_closes(self):
        self.open_intake(ask="put up a status page")
        mod = self.guard()["args"]
        result = self.create(mod["body"])
        self.plug.crew_open_hook(tool_name="kanban_create", args={"title": "Status page"}, result=result,
                                 session_id="S1")
        kinds = [k for k, _ in self.events()]
        self.assertEqual(["origin", "brief"], kinds)
        self.assertEqual("put up a status page", dict(self.events())["brief"]["text"])
        self.assertFalse(self.plug._window_live("S1"))                 # one /crew, one card
        self.assertEqual("block", self.guard(turn="T2")["action"])      # and a second create is refused

    def test_units_and_the_route_event_of_a_pinned_card(self):
        self.open_intake()
        mod = self.guard(body=BODY.replace("Route: none", "Route: acme/ling-3.0/ai-gateway") + "Units: a|b\n")["args"]
        result = self.create(mod["body"], model=mod["model"], provider=mod["provider"])
        self.plug.crew_open_hook(tool_name="kanban_create", args={"title": "Status page"}, result=result,
                                 session_id="S1")
        events = dict(self.events())
        self.assertEqual("acme/ling-3.0", events["route"]["model"])
        progress = os.path.join(self.home, "crew", "progress", "t_new1.json")
        self.assertTrue(os.path.exists(progress))
        self.assertEqual(["a", "b"], [u["unit"] for u in json.load(open(progress))["units"]])

    def test_a_failed_create_changes_nothing(self):
        self.open_intake()
        self.plug.crew_open_hook(tool_name="kanban_create", args={"title": "Status page"},
                                 result=json.dumps({"error": "assignee is required"}), session_id="S1")
        self.assertEqual([], self.events())
        self.assertTrue(self.plug._window_live("S1"))

    def test_a_non_crew_card_is_left_alone(self):
        self.open_intake()
        result = self.create("milk")
        self.plug.crew_open_hook(tool_name="kanban_create", args={"title": "buy milk"}, result=result,
                                 session_id="S1")
        self.assertEqual([], self.events())
        self.assertTrue(self.plug._window_live("S1"))


class ExpandedAskTests(unittest.TestCase):
    def test_a_raw_slash_records_the_ask(self):
        os.environ.setdefault("HERMES_HOME", tempfile.mkdtemp(prefix="crew-intake-test-"))
        plug = load_plugin()
        plug.crew_intake_preload(user_message="/crew make it fast", session_id="SX", turn_id="T")
        self.assertEqual("make it fast", plug._CREW_BRIEFS["SX"])


class IntakeFactsTests(unittest.TestCase):
    """The intake gets crew's own values in the turn, so it never digs through crew's files for them."""

    def setUp(self):
        os.environ.setdefault("HERMES_HOME", tempfile.mkdtemp(prefix="crew-intake-test-"))
        self.plug = load_plugin()

    def test_an_expanded_skill_turn_gets_the_facts(self):
        out = self.plug.crew_intake_preload(
            user_message='[IMPORTANT: The user has invoked the "crew" skill] ask', session_id="SF", turn_id="T")
        facts = (out or {}).get("context", "")
        self.assertIn("<crew-facts>", facts)
        self.assertIn("worker %d" % crew_card.default_budget("worker"), facts)
        self.assertRegex(facts, r"Proof safety mode: (safe|brave)\.")
        self.assertNotIn("<skill", facts)     # the gateway already expanded the skill: facts only

    def test_a_raw_slash_turn_gets_skill_and_facts(self):
        ctx = self.plug.crew_intake_preload(user_message="/crew make it fast", session_id="SG", turn_id="T")["context"]
        self.assertIn('<skill name="crew">', ctx)
        self.assertIn("<crew-facts>", ctx)

    def test_no_card_tool_still_opens_with_the_banner(self):
        """No crew facts readable: the wordmark still goes, the facts block just does not."""
        with unittest.mock.patch.object(self.plug, "_card_tool", return_value=None):
            out = self.plug.crew_intake_preload(
                user_message='[IMPORTANT: The user has invoked the "crew" skill] ask', session_id="SH", turn_id="T")
        ctx = (out or {}).get("context", "")
        self.assertIn("HERMES.CREW", ctx)
        self.assertNotIn("<crew-facts>", ctx)


if __name__ == "__main__":
    unittest.main()


COMPLEX_BODY = """Role: content
Budget: 500000
Route: none
GOAL: Ship a three-page site for the bakery
Artifact: a static site (index, menu, contact)
Lands at: /srv/bakery
For: walk-in customers
Constraints: no JavaScript frameworks
Inputs: /home/owner/bakery/brand.md, https://example.com/menu-draft
> Tone: warm, short sentences.
> Opening hours: Tue-Sat 7-15.
Done when: each of the three pages exists, links to the other two and shows the opening hours
proof command: python3 /srv/bakery/.crew/verify.py
"""


class InputsAndScriptProofTests(IntakeCase):
    """The intake contract for a realistic complex ask, end to end through the plugin guard (no model)."""

    def test_a_complex_ask_renders_independent_with_inputs_and_a_script_proof(self):
        self.open_intake(ask="build the bakery site")
        res = self.guard(body=COMPLEX_BODY, assignee="crew-content")
        self.assertEqual("modify", res["action"])
        body = res["args"]["body"]
        c = crew_card.parse_contract(body)
        self.assertEqual("independent", crew_card.verify_mode(body))      # the intake wrote no Verify line: script proof
        self.assertIn("Verify: independent", body)
        self.assertEqual("python3 /srv/bakery/.crew/verify.py", c["proof_cmd"])
        self.assertEqual("/home/owner/bakery/brand.md, https://example.com/menu-draft\n"
                         "> Tone: warm, short sentences.\n> Opening hours: Tue-Sat 7-15.", c["inputs"])
        self.assertEqual(1, body.count("> Tone: warm"))                   # not repeated as an intake note
        self.assertNotIn("Intake notes", body)
        self.assertEqual(crew_card.role_profile("content"), res["args"]["assignee"])

    def test_a_script_proof_stated_as_proof_is_coerced_and_a_command_only_proof_is_not(self):
        self.open_intake()
        coerced = self.guard(body=COMPLEX_BODY + "Verify: proof\n", assignee="crew-content")["args"]["body"]
        self.assertEqual("independent", crew_card.verify_mode(coerced))
        plain = self.guard(body=BODY + "Verify: proof\n")["args"]["body"]
        self.assertEqual("proof", crew_card.verify_mode(plain))
        self.assertEqual("proof", crew_card.verify_mode(self.guard()["args"]["body"]))

    def test_inputs_round_trip_and_an_empty_field_leaves_no_line(self):
        c = crew_card.parse_contract(BODY)
        self.assertEqual("", c["inputs"])
        self.assertNotIn("Inputs", crew_card.render_body(crew_card.prepare_contract(dict(c, coordinator="p/s"))))
        c = crew_card.parse_contract(COMPLEX_BODY)
        back = crew_card.parse_contract(crew_card.render_body(crew_card.prepare_contract(dict(c, coordinator="p/s"))))
        self.assertEqual(c["inputs"], back["inputs"])
        only_quote = crew_card.parse_contract(BODY + "Inputs:\n> pasted spec line\n")
        self.assertEqual("> pasted spec line", only_quote["inputs"])

    def test_pasted_text_over_the_limit_is_refused_with_the_file_path_advice(self):
        self.open_intake()
        res = self.guard(body=BODY + "Inputs: x\n> " + "y" * 2100 + "\n")
        self.assertEqual("block", res["action"])
        self.assertIn("file path", res["message"])

    def test_inputs_reach_a_coordinator_split_child_and_an_audit_follow_up(self):
        import crew_coordinator as cc
        c = crew_card.parse_contract(COMPLEX_BODY)
        child = cc.split_child({"title": "a", "goal": "g"}, "o", "p/s", crew_card.contract_inputs(COMPLEX_BODY))
        self.assertEqual(c["inputs"], child["inputs"])
        rendered = crew_card.render_body(crew_card.prepare_contract(dict(c, coordinator="p/s")))
        self.assertEqual(c["inputs"], crew_card.parse_contract(rendered)["inputs"])   # open_audit_followup's path


class IntakeWindowTests(IntakeCase):
    def test_an_owner_turn_in_a_live_intake_extends_the_window(self):
        self.open_intake()
        self.plug._CREW_WINDOWS["S1"] = self.plug.time.time() + 5          # nearly expired
        self.plug.crew_intake_preload(user_message="what would the menu page look like?", session_id="S1", turn_id="T2")
        self.assertGreater(self.plug._CREW_WINDOWS["S1"], self.plug.time.time() + self.plug.INTAKE_WINDOW_SECONDS - 60)
        self.assertEqual("modify", self.guard(turn="T3")["action"])

    def test_an_expired_window_is_not_reopened_by_an_ordinary_message(self):
        self.open_intake()
        self.plug._CREW_WINDOWS["S1"] = self.plug.time.time() - 1
        self.plug.crew_intake_preload(user_message="go", session_id="S1", turn_id="T2")
        self.assertEqual("block", self.guard(turn="T3")["action"])

    def test_a_session_with_no_intake_never_gets_a_window_from_chatter(self):
        self.plug.crew_intake_preload(user_message="hello", session_id="S7", turn_id="T1")
        self.assertEqual("block", self.guard(session="S7")["action"])


# The real shape Hermes delivers when the intake's `crew_card.py watch` background process ends
# (state.db, session 20261003_132900_ed8407, 2026-10-03).
WATCH_REPORT = ('[IMPORTANT: Background process proc_376681626e77 completed normally (exit code 0).\n'
                'Command: python3 "$HERMES_HOME/plugins/crew/scripts/crew_card.py" watch --card t_3f619c1d\n'
                'Output:\ncrew watch: card t_3f619c1d was stopped (archived); nothing more to report.\n]')
OTHER_COMPLETION = ('[IMPORTANT: Background process proc_1 completed normally (exit code 0).\n'
                    'Command: python3 build.py --card t_3f619c1d\nOutput:\ndone\n]')


class AnsweringReportTests(IntakeCase):
    def test_report_then_owner_reply_opens_a_card_once_with_skill_injected(self):
        self.assertIsNone(self.plug.crew_intake_preload(user_message=WATCH_REPORT, session_id="S1", turn_id="T1"))
        self.assertEqual("block", self.guard(turn="T1")["action"])          # the report turn itself opens nothing
        out = self.plug.crew_intake_preload(user_message="do it again", session_id="S1", turn_id="T2")
        self.assertIn("t_3f619c1d", out["context"])
        self.assertIn('<skill name="crew">', out["context"])
        self.assertEqual("modify", self.guard(turn="T2")["action"])         # the real guard allows the create
        self.assertIsNone(self.plug.crew_intake_preload(user_message="and more", session_id="S1", turn_id="T3"))   # injected once

    def test_other_session_and_non_watcher_completion_and_expiry_open_nothing(self):
        self.plug.crew_intake_preload(user_message=WATCH_REPORT, session_id="S1", turn_id="T1")
        self.assertIsNone(self.plug.crew_intake_preload(user_message="redo it", session_id="S2", turn_id="T2"))
        self.assertEqual("block", self.guard(session="S2", turn="T2")["action"])
        self.plug.crew_intake_preload(user_message=OTHER_COMPLETION, session_id="S3", turn_id="T1")
        self.assertIsNone(self.plug.crew_intake_preload(user_message="redo it", session_id="S3", turn_id="T2"))
        self.assertEqual("block", self.guard(session="S3", turn="T2")["action"])
        self.plug._REPORT_WINDOWS["S1"] = ("t_3f619c1d", self.plug.time.time() - 1)
        self.assertIsNone(self.plug.crew_intake_preload(user_message="redo it", session_id="S1", turn_id="T3"))
        self.assertEqual("block", self.guard(session="S1", turn="T3")["action"])

    def test_no_session_report_opens_nothing(self):
        self.plug.crew_intake_preload(user_message=WATCH_REPORT, session_id=None, turn_id="T1")
        self.assertEqual({}, self.plug._REPORT_WINDOWS)


class BannerTests(unittest.TestCase):
    """A /crew turn opens with the HERMES.CREW wordmark and the plugin's own version."""

    def setUp(self):
        os.environ.setdefault("HERMES_HOME", tempfile.mkdtemp(prefix="crew-intake-test-"))
        self.plug = load_plugin()

    def test_the_raw_slash_turn_opens_with_the_line(self):
        ctx = self.plug.crew_intake_preload(
            user_message="/crew make it fast", session_id="SB1", turn_id="T")["context"]
        self.assertTrue(ctx.startswith("Open your reply"))
        self.assertIn("HERMES.CREW v", ctx)
        self.assertNotIn("#   #", ctx)          # the ASCII art is gone

    def test_the_expanded_skill_turn_opens_with_the_banner(self):
        out = self.plug.crew_intake_preload(
            user_message='[IMPORTANT: The user has invoked the "crew" skill] ask', session_id="SB2", turn_id="T")
        self.assertIn("HERMES.CREW v", (out or {}).get("context", ""))

    def test_the_version_comes_from_the_manifest(self):
        self.assertRegex(self.plug._crew_banner(), r"^HERMES\.CREW v\d")

    def test_an_ordinary_turn_gets_no_banner(self):
        self.assertIsNone(self.plug.crew_intake_preload(
            user_message="what about the menu?", session_id="SB3", turn_id="T"))
