#!/usr/bin/env python3
"""Tests for the lessons file: the command, the skill_manage guard, per-role injection, parity."""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
os.environ.setdefault("HERMES_BIN", "/bin/false")

import crew_lessons  # noqa: E402
import crew_parity_check  # noqa: E402

REAL = ("A structural proof passing (11/11) says nothing about whether citations are real: resolve every "
        "DOI/PMID before passing.")


class LessonsCase(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-lessons-test-")
        os.environ["HERMES_HOME"] = self.home
        os.environ.pop("HERMES_KANBAN_TASK", None)
        self.cfg("worker")

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)

    def cfg(self, role):
        with open(os.path.join(self.home, "config.yaml"), "w") as fh:
            fh.write("crew:\n  role: %s\n" % role)

    def plugin(self):
        spec = importlib.util.spec_from_file_location("crew_plugin_lessons_test", str(REPO / "__init__.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


class CommandTests(LessonsCase):
    def test_cli_writes_and_dedupes(self):
        import crew_card
        self.assertEqual(crew_card.main.__module__, "crew_card")
        argv = ["crew_card.py", "lesson", "--role", "content,verifier", "--text", REAL]
        old = sys.argv
        try:
            sys.argv = argv
            self.assertEqual(crew_card.main(), 0)
            self.assertEqual(crew_card.main(), 0)   # same lesson again
        finally:
            sys.argv = old
        text = open(os.path.join(self.home, "crew", "lessons.md")).read()
        self.assertEqual(text.count(REAL), 1)
        self.assertRegex(text, r"- \d{4}-\d{2}-\d{2} \[content,verifier\] A structural proof")

    def test_profile_home_writes_to_base_crew_dir(self):
        prof = os.path.join(self.home, "profiles", "p1")
        os.makedirs(prof)
        os.environ["HERMES_HOME"] = prof
        crew_lessons.add("worker", "x")
        self.assertTrue(os.path.exists(os.path.join(self.home, "crew", "lessons.md")))

    def test_cap_entries_and_bytes(self):
        for i in range(60):
            crew_lessons.add("worker", "lesson number %d" % i)
        es = crew_lessons.entries()
        self.assertEqual(len(es), crew_lessons.MAX_ENTRIES)
        self.assertEqual(es[-1][2], "lesson number 59")
        self.assertEqual(es[0][2], "lesson number 10")
        for i in range(40):
            crew_lessons.add("all", ("long %d " % i) * 50)
        self.assertLessEqual(os.path.getsize(crew_lessons.path()), crew_lessons.MAX_BYTES)
        self.assertEqual(crew_lessons.entries()[-1][2][:7], "long 39")

    def test_bad_input_refused(self):
        with self.assertRaises(ValueError):
            crew_lessons.add("plumber", "x")
        with self.assertRaises(ValueError):
            crew_lessons.add("worker", " ")
        with self.assertRaises(ValueError):
            crew_lessons.add("worker", "x" * 500)


class GuardTests(LessonsCase):
    def test_refuses_crew_skills_every_shape_every_profile(self):
        for role in ("", "worker", "coordinator"):
            self.cfg(role) if role else os.remove(os.path.join(self.home, "config.yaml"))
            plug = self.plugin()
            for name in ("crew", "crew-diagnose", "crew-role-worker", "crew-role-content", "crew-verifier"):
                for args in ({"operations": [{"action": "patch", "name": name, "old_string": "a", "new_string": "b"}]},
                             {"operations": [{"action": "patch", "name": "crew/" + name, "content": "x"}]},
                             {"action": "edit", "name": name, "content": "x"},
                             {"name": name, "operations": [{"action": "patch", "old_string": "a", "new_string": "b"}]}):
                    v = plug.crew_tool_guard(tool_name="skill_manage", args=args, session_id="S", turn_id="T")
                    self.assertEqual((v or {}).get("action"), "block", (role, name, args))
                    self.assertIn("crew_card.py", v["message"])
                    self.assertIn("lesson --role", v["message"])

    def test_allows_other_skills(self):
        plug = self.plugin()
        for args in ({"operations": [{"action": "patch", "name": "my-skill", "old_string": "a", "new_string": "b"}]},
                     {"action": "edit", "name": "crew-notes", "content": "x"},
                     {"operations": [{"action": "create", "name": "crew-new-thing", "content": "x"}]}):
            self.assertIsNone(plug.crew_tool_guard(tool_name="skill_manage", args=args, session_id="S", turn_id="T"))

    def test_skill_list_is_the_installer_list(self):
        import install
        self.assertEqual(self.plugin()._crew_skill_names(), set(install.skill_names()))


class InjectionTests(LessonsCase):
    def setUp(self):
        super().setUp()
        crew_lessons.add("content,verifier", REAL)
        crew_lessons.add("worker", "worker only lesson")
        crew_lessons.add("all", "everyone lesson")

    def turn(self, role, sid="S1"):
        self.cfg(role)
        os.environ["HERMES_KANBAN_TASK"] = "t_nonexistent"
        plug = self.plugin()
        plug._handoff_text = lambda card: ""
        return (plug.crew_handoff_hook(user_message="go", session_id=sid) or {}).get("context", "")

    def test_role_gets_only_its_lessons(self):
        ctx = self.turn("content")
        self.assertIn("<crew-lessons>", ctx)
        self.assertIn("structural proof", ctx)
        self.assertIn("everyone lesson", ctx)
        self.assertNotIn("worker only", ctx)
        ctx = self.turn("worker", "S2")
        self.assertIn("worker only", ctx)
        self.assertNotIn("structural proof", ctx)
        ctx = self.turn("verifier", "S3")
        self.assertIn("structural proof", ctx)
        self.assertNotIn("worker only", ctx)

    def test_handoff_and_lessons_both_present_and_once_per_session(self):
        self.cfg("worker")
        os.environ["HERMES_KANBAN_TASK"] = "t_x"
        plug = self.plugin()
        plug._handoff_text = lambda card: "PREVIOUS RUN WORK"
        ctx = plug.crew_handoff_hook(user_message="go", session_id="S9")["context"]
        self.assertIn("PREVIOUS RUN WORK", ctx)
        self.assertIn("worker only lesson", ctx)
        self.assertIsNone(plug.crew_handoff_hook(user_message="go", session_id="S9"))

    def test_no_lessons_no_block(self):
        os.remove(crew_lessons.path())
        self.assertEqual(self.turn("worker"), "")

    def test_intake_gets_only_all(self):
        plug = self.plugin()
        plug._card_tool = lambda: type("T", (), {
            "default_budget": staticmethod(lambda r: 1),
            "crew_safety": type("S", (), {"permanent_mode": staticmethod(lambda: "safe")})})
        facts = plug._intake_facts()
        self.assertIn("<crew-facts>", facts)
        self.assertIn("everyone lesson", facts)
        self.assertNotIn("worker only", facts)
        self.assertNotIn("structural proof", facts)


class ParityTests(LessonsCase):
    def test_lessons_file_not_a_shipped_file(self):
        crew_lessons.add("all", "x")
        shipped = [dst for _src, dst in crew_parity_check.shipped_files(str(REPO))]
        self.assertFalse(any("lessons.md" in d for d in shipped))
        self.assertTrue(any(d.endswith("scripts/crew_lessons.py") for d in shipped))


if __name__ == "__main__":
    unittest.main()
