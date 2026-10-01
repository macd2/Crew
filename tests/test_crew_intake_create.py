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


if __name__ == "__main__":
    unittest.main()
