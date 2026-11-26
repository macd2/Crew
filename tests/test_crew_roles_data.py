#!/usr/bin/env python3
"""The crew's roles come from the installed roles.json, not from lists in the code: a crew whose writers are
auditor + remediator (a lineup) is checked, closed, routed, taught and guarded by those names, and `worker` is
no longer one of its writers. A throwaway HERMES_HOME carries that roles.json."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))
os.environ.setdefault("HERMES_BIN", "/bin/false")
_HOME = tempfile.mkdtemp(prefix="crew-roles-data-")
import module_env  # noqa: E402

module_env.pin(globals(), HERMES_HOME=_HOME)

import crew_card  # noqa: E402
import crew_graph  # noqa: E402
import crew_lessons  # noqa: E402

ROLES = {"roles": [
    {"name": "coordinator", "kind": "coordinator", "purpose": "plans"},
    {"name": "auditor", "kind": "writer", "task_class": "review", "purpose": "finds holes"},
    {"name": "remediator", "kind": "writer", "task_class": "code", "purpose": "fixes them"},
    {"name": "verifier", "kind": "verifier", "task_class": "review", "purpose": "checks"},
]}


def _write_roles(home):
    d = os.path.join(home, "roles", "crew")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "roles.json"), "w", encoding="utf-8") as fh:
        json.dump(ROLES, fh)


_write_roles(_HOME)


class LineupRolesTests(unittest.TestCase):
    def setUp(self):
        os.environ["HERMES_HOME"] = _HOME

    def test_writer_roles_come_from_roles_json(self):
        self.assertEqual(("auditor", "remediator"), crew_card.writer_roles())
        self.assertEqual(("coordinator", "auditor", "remediator", "verifier"), crew_card.all_roles())
        self.assertEqual("auditor", crew_card.default_writer())

    def _card(self, role):
        return {"goal": "g", "artifact": "a", "lands": "l", "audience": "o", "done_when": "d",
                "proof_cmd": "python3 /tmp/x/.crew/20260101-000000-x/verify.py", "role": role}

    def test_contract_accepts_a_lineup_writer_and_refuses_worker(self):
        self.assertFalse([g for g in crew_card.contract_gaps(self._card("auditor")) if g.startswith("role")])
        gaps = [g for g in crew_card.contract_gaps(self._card("worker")) if g.startswith("role")]
        self.assertEqual(["role (auditor or remediator)"], gaps)

    def test_closer_profiles_follow_the_writers(self):
        pre = crew_card.profile_prefix()
        got = crew_card.closer_profiles("Role: auditor\nVerify: proof\n")
        self.assertIn(pre + "auditor", got)
        self.assertNotIn(pre + "worker", got)
        legacy = crew_card.closer_profiles("Role: auditor\n")
        self.assertTrue({pre + "auditor", pre + "remediator", pre + "verifier"} <= legacy)
        self.assertNotIn(pre + "content", legacy)

    def test_task_class_reads_roles_json(self):
        self.assertEqual("review", crew_card.role_task_class("auditor"))
        self.assertEqual("code", crew_card.role_task_class("remediator"))

    def test_lessons_take_the_crew_roles(self):
        self.assertEqual(["auditor"], crew_lessons._parse_roles("auditor"))
        with self.assertRaises(ValueError):
            crew_lessons._parse_roles("worker")
        self.assertIn("all", crew_lessons.known_roles())

    def test_graph_role_order_and_default_card_role(self):
        self.assertEqual(["coordinator", "auditor", "remediator", "verifier"], crew_graph.role_order())
        self.assertEqual(["coordinator", "auditor", "remediator", "verifier"],
                         [r["name"] for r in crew_graph.load_roles()][:4])
        self.assertEqual("auditor", crew_graph.card_role("", "[]"))
        self.assertEqual("remediator", crew_graph.profile_role("crew-remediator", "x"))
        self.assertEqual(["coordinator", "worker", "content", "verifier"], crew_graph.role_order({}))


class PluginGuardTests(unittest.TestCase):
    """__init__.py's role guards treat a lineup writer as a writer."""

    @classmethod
    def setUpClass(cls):
        os.environ["HERMES_HOME"] = _HOME
        spec = importlib.util.spec_from_file_location("crew_roles_data_plugin", str(REPO / "__init__.py"))
        cls.P = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.P)

    def setUp(self):
        os.environ["HERMES_HOME"] = _HOME
        os.environ.pop("HERMES_KANBAN_TASK", None)
        self._role = self.P._ROLE

    def tearDown(self):
        self.P._ROLE = self._role

    def _guard(self, role):
        self.P._ROLE = role
        return self.P.crew_tool_guard("write_file", {"path": "/tmp/land/.crew/20260101-000000-x/verify.py",
                                                     "content": "print(1)"})

    def test_a_lineup_writer_may_not_write_under_crew(self):
        verdict = self._guard("auditor")
        self.assertEqual("block", (verdict or {}).get("action"))
        self.assertIn(".crew/", verdict["message"])

    def test_a_role_outside_the_lineup_is_not_a_writer(self):
        self.assertIsNone(self._guard("worker"))

    def test_roles_fall_back_to_the_shipped_crew_without_the_card_tool(self):
        orig = self.P._card_tool
        self.P._card_tool = lambda: None
        try:
            self.assertEqual((("worker", "content"), ("coordinator", "worker", "content", "verifier")),
                             self.P._crew_roles_now())
        finally:
            self.P._card_tool = orig

    def test_is_crew_create_knows_the_lineup_writers(self):
        tool = self.P._card_tool()
        pre = tool.profile_prefix()
        self.assertTrue(self.P._is_crew_create({"assignee": pre + "remediator", "body": ""}, tool))
        self.assertFalse(self.P._is_crew_create({"assignee": pre + "worker", "body": ""}, tool))


if __name__ == "__main__":
    unittest.main()
