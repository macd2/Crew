#!/usr/bin/env python3
"""Unit tests for the capability floor in a crew card's routing and after a quota wall.

The router side (the floor menu itself) is tested in the router plugin's own suite and on a
copy of the live state by its proof_agent_floor.py. Here: what the crew does with the router's answer.

  * a pick that clears the floor is pinned and its route event carries `floor` and `menu_size`;
  * the router answering "parent" (nothing clears the floor) is not a pick: no pin is written;
  * a wall with a floor model live re-pins the card; with the router answering "parent" the pin is cleared
    through the kernel's own `set-model <id>` and the role profile's own model runs; with no pin to clear the
    first wall is counted and the second blocks the card as `transient` (the coordinator's kind), not
    `needs_input` (the owner's);
  * the router is asked with the card's ROLE class (worker -> code), never the old hard-coded "short".

No hermes CLI, no live board, no router: the CLI call and the router answer are injected, the board is a
throwaway sqlite file.
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
os.environ.setdefault("HERMES_BIN", "/bin/false")   # a unit test never starts the real `hermes` (scratch HERMES_HOME bootstraps a runtime and rewrites the live launcher)

import crew_card  # noqa: E402
import crew_heal  # noqa: E402

CARD = "t_floor_unit"
FLOOR = {"min_context": 64000, "tools": "verified", "menu_size": 2}
PICK_ANSWER = {"label": "gemini:gemini-3.6-flash", "provider": "gemini", "model": "gemini-3.6-flash",
               "decider": "jev", "task_class": "code", "why": "Jev gate picked gemini-3.6-flash",
               "floor": FLOOR, "menu_size": 2}
PARENT_ANSWER = {"label": "parent", "provider": None, "model": None, "decider": "floor", "menu_size": 0,
                 "floor": dict(FLOOR, menu_size=0),
                 "why": "no live free model clears the agent floor: the card runs on the role profile's own model"}


class FloorCase(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-floor-test-")
        self.db = os.path.join(self.home, "kanban.db")
        os.environ["HERMES_HOME"] = self.home
        os.environ["HERMES_KANBAN_DB"] = self.db
        os.environ.pop("KANBAN_DB", None)
        conn = sqlite3.connect(self.db)
        conn.executescript(
            "create table tasks (id text primary key, title text, status text, assignee text, body text,"
            " model_override text, provider_override text, last_failure_error text, block_kind text);"
            "create table task_events (id integer primary key autoincrement, task_id text, run_id text,"
            " kind text, payload text, created_at integer);")
        conn.commit()
        conn.close()
        self.cli = []
        self.answers = []
        self.asked = []

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)

    def seed(self, model="gemini-flash-lite-latest", provider="gemini", role="worker"):
        conn = sqlite3.connect(self.db)
        conn.execute("insert or replace into tasks (id, title, status, assignee, body, model_override,"
                     " provider_override, last_failure_error) values (?,?,?,?,?,?,?,?)",
                     (CARD, "publish branch", "running", "crew-worker", "Role: %s\nGOAL: x\n" % role,
                      model, provider, "HTTP 429 quota"))
        conn.commit()
        conn.close()

    def cli_stub(self, args, timeout=120):
        """The kernel verbs the crew calls: `set-model <id>` clears BOTH columns, `set-model <id> <model>
        [--provider P]` pins them, as the kernel's set_model_override does."""
        self.cli.append(list(args))
        if args[0] == "set-model":
            model = args[2] if len(args) > 2 else None
            provider = args[args.index("--provider") + 1] if "--provider" in args else None
            conn = sqlite3.connect(self.db)
            conn.execute("update tasks set model_override = ?, provider_override = ? where id = ?",
                         (model, provider, args[1]))
            conn.commit()
            conn.close()
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    def answer_stub(self, task_class="code", label="", profile=None):
        self.asked.append((task_class, label, profile))
        return self.answers.pop(0) if self.answers else None

    def wall(self, **kw):
        with mock.patch.object(crew_card, "_kanban", self.cli_stub), \
                mock.patch.object(crew_card, "route_answer", self.answer_stub):
            return crew_card.reroute_after_wall(CARD, model="gemini-flash-lite-latest", provider="gemini", **kw)

    def row(self):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute("select model_override, provider_override, last_failure_error from tasks "
                                "where id = ?", (CARD,)).fetchone()
        finally:
            conn.close()

    def events(self, kind):
        conn = sqlite3.connect(self.db)
        try:
            return [json.loads(p) for (p,) in conn.execute(
                "select payload from task_events where task_id = ? and kind = ? order by id", (CARD, kind))]
        finally:
            conn.close()


class PickTests(FloorCase):
    def test_a_floor_pick_is_pinned_and_the_route_event_carries_the_floor(self):
        pick = crew_card.pick_from_answer(PICK_ANSWER, "code", "publish branch")
        self.assertEqual(("gemini", "gemini-3.6-flash"), (pick["provider"], pick["model"]))
        self.seed(model=None, provider=None)
        with mock.patch.object(crew_card, "_kanban", self.cli_stub):
            self.assertTrue(crew_card.apply_route(CARD, pick))
        self.assertEqual([["set-model", CARD, "gemini-3.6-flash", "--provider", "gemini"]], self.cli,
                         "the pin is the kernel's own set-model, not a column write")
        self.assertEqual(("gemini-3.6-flash", "gemini"), self.row()[:2])
        ev = self.events("route")[0]
        self.assertEqual(FLOOR, ev["floor"])
        self.assertEqual(2, ev["menu_size"])

    def test_the_router_answering_parent_is_not_a_pick(self):
        self.assertIsNone(crew_card.pick_from_answer(PARENT_ANSWER, "code", "publish branch"))
        self.assertIsNone(crew_card.pick_from_answer(None))
        self.assertIsNone(crew_card.pick_from_answer({"label": None, "why": "no plugin"}))

    def test_the_router_is_told_the_role_class_not_short(self):
        self.assertEqual("code", crew_card.role_task_class("worker"))
        self.assertEqual("write", crew_card.role_task_class("content"))
        self.assertEqual("code", crew_card.role_task_class(None))
        self.seed(role="content")
        self.answers = [PICK_ANSWER]
        self.wall()
        self.assertEqual("write", self.asked[0][0])


class WallTests(FloorCase):
    def test_a_floor_model_live_re_pins_the_card_and_the_event_says_why(self):
        self.seed()
        self.answers = [PICK_ANSWER]
        got = self.wall()
        self.assertEqual("rerouted", got["action"])
        self.assertEqual(("gemini-3.6-flash", "gemini"), self.row()[:2])
        self.assertIsNone(self.row()[2], "the hold for the dead model is lifted")
        ev = self.events("reroute")[0]
        self.assertEqual((FLOOR, 2), (ev["floor"], ev["menu_size"]))
        self.assertEqual("gemini-3.6-flash", ev["to_model"])

    def test_nothing_on_the_floor_clears_the_pin_so_the_profile_model_runs(self):
        self.seed()
        self.answers = [PARENT_ANSWER]
        got = self.wall()
        self.assertEqual("unpinned", got["action"])
        self.assertEqual([["set-model", CARD]], self.cli, "the kernel's own verb, no model argument")
        self.assertEqual((None, None, None), self.row(), "model and provider cleared together, hold lifted")
        ev = self.events("reroute")[0]
        self.assertEqual((None, None, 0), (ev["to_model"], ev["to_provider"], ev["menu_size"]))
        self.assertEqual("gemini-flash-lite-latest", ev["from_model"])

    def test_a_card_is_never_re_pinned_to_a_model_below_the_floor(self):
        """The anchor: t_d93e0c7b was re-pinned to ling-3.0-flash-sante after a wall. The pick comes only
        from the floor menu, so a below-floor id can not be the answer; "parent" clears the pin instead."""
        self.seed()
        self.answers = [PARENT_ANSWER]
        self.wall()
        self.assertNotIn("ling", " ".join(str(v) for v in self.row() if v))

    def test_no_pin_to_clear_the_first_wall_is_counted_and_the_second_blocks_as_transient(self):
        self.seed(model=None, provider=None)
        self.answers = [PARENT_ANSWER, PARENT_ANSWER]
        first = self.wall()
        self.assertEqual("counted", first["action"])
        self.assertEqual([], self.cli)
        second = self.wall()
        self.assertEqual("blocked", second["action"])
        self.assertEqual([["block", CARD, "--kind", "transient", second["why"][:400]]], self.cli)
        self.assertIn("quota wall", second["why"])

    def test_no_router_keeps_the_old_behaviour_the_pin_is_left_alone(self):
        self.seed()
        self.answers = [None]
        self.assertEqual("counted", self.wall()["action"])
        self.assertEqual(("gemini-flash-lite-latest", "gemini"), self.row()[:2])
        self.assertEqual([], self.cli)

    def test_a_set_model_failure_is_reported_not_swallowed(self):
        self.seed()
        self.answers = [PARENT_ANSWER]
        with mock.patch.object(crew_card, "_kanban",
                               lambda args, timeout=120: SimpleNamespace(returncode=2, stdout="", stderr="boom")), \
                mock.patch.object(crew_card, "route_answer", self.answer_stub):
            got = crew_card.reroute_after_wall(CARD, model="gemini-flash-lite-latest", provider="gemini")
        self.assertEqual("error", got["action"])
        self.assertEqual(("gemini-flash-lite-latest", "gemini"), self.row()[:2], "the pin is untouched")


class HealTests(FloorCase):
    def test_heal_reports_each_wall_outcome(self):
        card = {"id": CARD}
        for out, fixed, text in (
                ({"action": "rerouted", "to": {"provider": "gemini", "model": "gemini-3.6-flash"}}, True,
                 "re-pinned on gemini/gemini-3.6-flash"),
                ({"action": "unpinned"}, True, "pin cleared"),
                ({"action": "counted"}, False, "no live pick fits (counted)")):
            with mock.patch.object(crew_card, "reroute_after_wall", lambda cid, _o=out: _o), \
                    mock.patch.object(crew_heal, "event", lambda *a, **k: None):
                got = crew_heal.heal_dead_model(card, False)
            self.assertEqual(fixed, got["fixed"], out)
            self.assertIn(text, got["action"], out)


if __name__ == "__main__":
    unittest.main()
