#!/usr/bin/env python3
"""Unit tests for the slim role profiles (spec step 7): the installer cuts a role profile's skills dir
down to skills/crew/ + skills_extra, the role toolsets in settings.conf are real kernel toolsets, and
the first-call prompt of a role is measured from state.db against roles.json prompt_budget_tokens.

Every installer call that would run `hermes` is replaced by a fake here: a test never starts the real
launcher (a scratch HERMES_HOME under it once rewrote the live launcher).
"""
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["HERMES_BIN"] = "/bin/false"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hermes_fake import FakeConfig  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("crew_install_slim", str(REPO / "install.py"))
CI = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CI)

KERNEL_TOOLSETS = Path.home() / ".hermes" / "hermes-agent" / "toolsets.py"


class Fake:
    """What CI.h returns: a finished process with no output."""
    returncode = 1
    stdout = ""
    stderr = ""


def put(path, text="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Path(path).write_text(text)


def tree_bytes(root):
    return sum(os.path.getsize(os.path.join(d, f)) for d, _s, fs in os.walk(root) for f in fs
               if os.path.isfile(os.path.join(d, f)))


def cloned_skills(home, extra_bytes=0):
    """What `hermes profile create --clone-from` leaves in skills/: categories, a .git, curator files."""
    root = os.path.join(home, "skills")
    put(os.path.join(root, "crew", "crew-role-worker", "SKILL.md"), "worker skill")
    put(os.path.join(root, "devops", "foo", "SKILL.md"), "foo")
    put(os.path.join(root, "devops", "bar", "SKILL.md"), "bar")
    put(os.path.join(root, "marketing", "x", "SKILL.md"), "x" * 5000)
    put(os.path.join(root, ".git", "objects", "pack"), "g" * (extra_bytes or 5000))
    put(os.path.join(root, ".curator_ledger.jsonl"), "l" * 3000)
    put(os.path.join(root, ".bundled_manifest"), "a:1\n")
    put(os.path.join(root, "README.md"), "readme")
    return root


class SlimSkillsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-slim-unit-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = os.path.join(self.tmp, "profiles", "crew-worker")
        self.source = os.path.join(self.tmp, "src")
        put(os.path.join(self.source, "skills", "devops", "foo", "SKILL.md"), "foo from source")
        self.tpl = os.path.join(self.tmp, "tpl")
        put(os.path.join(self.tpl, "settings.conf"), "crew.role = worker\nskills_extra = [devops/foo]\n")

    def test_the_kept_set_is_crew_the_extras_and_the_marker(self):
        cloned_skills(self.home)
        self.assertEqual(
            [".bundled_manifest", ".curator_ledger.jsonl", ".git", "README.md", "devops", "marketing"],
            CI._skills_excess(self.home, []))
        self.assertEqual(
            [".bundled_manifest", ".curator_ledger.jsonl", ".git", "README.md", "devops/bar", "marketing"],
            CI._skills_excess(self.home, ["devops/foo"]))

    def test_slimming_leaves_crew_and_the_extra_and_nothing_else(self):
        root = cloned_skills(self.home)
        status, detail = CI.step_role_skills(self.home, self.tpl, self.source, True)
        self.assertEqual("CHANGED", status, detail)
        self.assertEqual([".no-bundled-skills", "crew", "devops"], sorted(os.listdir(root)))
        self.assertEqual(["foo"], os.listdir(os.path.join(root, "devops")))
        self.assertTrue(os.path.isfile(os.path.join(root, "crew", "crew-role-worker", "SKILL.md")))
        self.assertLess(tree_bytes(root), 1024 * 1024)

    def test_an_extra_the_role_lacks_is_copied_from_the_installing_profile(self):
        root = cloned_skills(self.home)
        put(os.path.join(self.source, "skills", "devops", "baz", "SKILL.md"), "baz from source")
        both = os.path.join(self.tmp, "tpl2")
        put(os.path.join(both, "settings.conf"), "skills_extra = [devops/foo, devops/baz]\n")
        CI.step_role_skills(self.home, both, self.source, True)
        self.assertEqual(["baz", "foo"], sorted(os.listdir(os.path.join(root, "devops"))))
        self.assertEqual("baz from source", Path(root, "devops", "baz", "SKILL.md").read_text())

    def test_a_second_run_changes_nothing_and_check_mode_writes_nothing(self):
        root = cloned_skills(self.home)
        before = sorted(os.listdir(root))
        status, detail = CI.step_role_skills(self.home, self.tpl, self.source, False)
        self.assertEqual("CHANGED", status)
        self.assertEqual(before, sorted(os.listdir(root)), "--check must not write")
        CI.step_role_skills(self.home, self.tpl, self.source, True)
        status, _detail = CI.step_role_skills(self.home, self.tpl, self.source, True)
        self.assertEqual("OK", status)
        self.assertEqual(([], [], False), CI.role_skills_todo(self.home, self.tpl, self.source))

    def test_a_symlink_entry_is_unlinked_and_its_target_survives(self):
        root = cloned_skills(self.home)
        target = os.path.join(self.tmp, "shared-skills")
        put(os.path.join(target, "keep.txt"), "must survive")
        os.symlink(target, os.path.join(root, "external"))
        CI.step_role_skills(self.home, self.tpl, self.source, True)
        self.assertFalse(os.path.lexists(os.path.join(root, "external")))
        self.assertTrue(os.path.isfile(os.path.join(target, "keep.txt")))

    def test_a_symlinked_skills_dir_is_left_alone(self):
        real = os.path.join(self.tmp, "real-skills")
        put(os.path.join(real, "devops", "foo", "SKILL.md"), "x")
        os.makedirs(self.home)
        os.symlink(real, os.path.join(self.home, "skills"))
        status, _detail = CI.step_role_skills(self.home, self.tpl, self.source, True)
        self.assertEqual("FAILED", status)
        self.assertTrue(os.path.isfile(os.path.join(real, "devops", "foo", "SKILL.md")))

    def test_no_extras_means_crew_only(self):
        root = cloned_skills(self.home)
        bare = os.path.join(self.tmp, "bare")
        put(os.path.join(bare, "settings.conf"), "crew.role = worker\nskills_extra = []\n")
        CI.step_role_skills(self.home, bare, self.source, True)
        self.assertEqual([".no-bundled-skills", "crew"], sorted(os.listdir(root)))


class ShippedListsTests(unittest.TestCase):
    def test_every_file_the_installer_ships_exists_in_the_package(self):
        # A script deleted from the package but left in SCRIPT_FILES makes step_plugin raise on the
        # copy and leaves the profile half installed (crew_repeat_escalation_proof.py did, after step 1).
        # PLUGIN_FILES carries the scripts (plugins/crew/scripts/...), so one list covers both.
        missing = [rel for rel in CI.PLUGIN_FILES if not (REPO / rel).is_file()]
        missing += ["roles/" + rel for rel in CI.ROLE_FILES if not (REPO / "roles" / rel).is_file()]
        self.assertEqual([], missing)

    def test_skill_names_are_the_skill_dirs_of_the_package(self):
        self.assertEqual(sorted(p.parent.name for p in (REPO / "skills").glob("*/SKILL.md")), CI.skill_names())


class SettingsTests(unittest.TestCase):
    def test_installer_directives_are_not_config_keys(self):
        tmp = tempfile.mkdtemp(prefix="crew-slim-unit-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        conf = os.path.join(tmp, "settings.conf")
        put(conf, "# c\ncrew.role = worker\nskills_extra = [a/b, c/d]\nkanban.orchestrator_profile = {prefix}coordinator\n")
        self.assertEqual([("crew.role", "worker"), ("kanban.orchestrator_profile", CI.PROFILE_PREFIX + "coordinator")],
                         CI._conf_entries(conf))
        self.assertEqual(["a/b", "c/d"], CI._conf_list(conf, "skills_extra"))
        self.assertEqual([], CI._conf_list(conf, "nothing_here"))

    def test_every_template_toolset_is_a_kernel_toolset(self):
        if not KERNEL_TOOLSETS.exists():
            self.skipTest("kernel not on this host")
        known = set(re.findall(r'^    "([a-z_]+)": _ts\(', KERNEL_TOOLSETS.read_text(), re.M))
        self.assertIn("file", known)
        seen = 0
        for role in CI.ROLE_ORDER:
            conf = REPO / "templates" / "profiles" / role / "settings.conf"
            for key, val in CI._conf_entries(str(conf)):
                if key != "platform_toolsets.cli":
                    continue
                seen += 1
                for name in [x for x in val.strip("[]").split(",") if x]:
                    self.assertIn(name, known, "%s lists %s, not a kernel toolset" % (role, name))
        self.assertGreaterEqual(seen, 4, "coordinator, worker, content and verifier each list their toolsets")

    def test_the_toolset_list_round_trips_through_hermes_config(self):
        cfg, saved = FakeConfig(), CI.h
        CI.h = cfg
        self.addCleanup(setattr, CI, "h", saved)
        cfg.seed("p", platform_toolsets__cli="[browser,kanban,web]", platform_toolsets__slack="[]",
                 agent__max_turns="150")
        conf = REPO / "templates" / "profiles" / "worker" / "settings.conf"
        changed = CI._apply_settings("p", str(conf))
        self.assertIn("platform_toolsets.cli", changed)
        self.assertEqual("[terminal,file,web,kanban]", CI._cfg("p", "platform_toolsets.cli"))
        self.assertEqual("[]", CI._cfg("p", "platform_toolsets.slack"))
        self.assertEqual([], CI._apply_settings("p", str(conf)), "applying twice must change nothing")
        self.assertEqual([], CI.settings_problems("p", "worker", str(conf.parent)))


class PromptBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-slim-unit-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self._resolve = CI.resolve_profile_home
        CI.resolve_profile_home = lambda name: os.path.join(self.tmp, "profiles", name)
        self.addCleanup(setattr, CI, "resolve_profile_home", self._resolve)

    def db(self, name, rows):
        home = os.path.join(self.tmp, "profiles", name)
        os.makedirs(home, exist_ok=True)
        conn = sqlite3.connect(os.path.join(home, "state.db"))
        conn.execute("create table sessions (id text primary key, source text, started_at real, "
                     "api_call_count int, input_tokens int, cache_read_tokens int, cache_write_tokens int)")
        conn.executemany("insert into sessions values (?,?,?,?,?,?,?)", rows)
        conn.commit()
        conn.close()
        return home

    def test_the_bound_is_the_smallest_per_call_average_over_kanban_sessions(self):
        # anchor: t 205157 of the live crew-worker - 5 calls, input 28656, cache read 110272 (cache write 0):
        # (28656 + 110272) / 5 = 27785.6 -> 27785. The spec's "input + cache_write" alone would give 5731.
        home = self.db("crew-worker", [
            ("a", "kanban", 5.0, 5, 28656, 110272, 0),
            ("b", "kanban", 4.0, 132, 512081, 11241536, 0),       # long run: average 89k, not the smallest
            ("c", "cli", 3.0, 1, 10, 10, 0),                        # not a kanban run
            ("d", "kanban", 2.0, 0, 0, 0, 0)])                      # no call made
        self.assertEqual((27785, 2), CI.prompt_first_call(home))

    def test_exact_when_a_session_made_one_call(self):
        home = self.db("crew-verifier", [("a", "kanban", 2.0, 1, 100, 20000, 400), ("b", "kanban", 1.0, 9, 270000, 0, 0)])
        self.assertEqual((20500, 2), CI.prompt_first_call(home))

    def test_the_newest_ten_sessions_only(self):
        rows = [("old", "kanban", 1.0, 1, 1, 0, 0)]
        rows += [("n%d" % i, "kanban", 10.0 + i, 1, 50000, 0, 0) for i in range(10)]
        home = self.db("crew-content", rows)
        self.assertEqual((50000, 10), CI.prompt_first_call(home))

    def test_no_state_db_or_no_session_is_unmeasured_not_a_failure(self):
        empty = os.path.join(self.tmp, "profiles", "crew-coordinator")
        os.makedirs(empty)
        self.assertEqual((None, 0), CI.prompt_first_call(empty))
        self.db("crew-verifier", [("a", "cli", 1.0, 3, 1, 1, 1)])
        self.assertEqual((None, 0), CI.prompt_first_call(os.path.join(self.tmp, "profiles", "crew-verifier")))

    def test_a_role_over_the_budget_fails_the_step(self):
        self.db("crew-worker", [("a", "kanban", 1.0, 1, 41000, 0, 0)])
        self.db("crew-verifier", [("a", "kanban", 1.0, 1, 12000, 0, 0)])
        self.assertEqual(40000, CI.roles_budget())
        lines, over = CI.prompt_report("crew-")
        self.assertEqual(["crew-worker"], over)
        self.assertTrue(any("crew-worker" in l and "OVER BUDGET" in l for l in lines))
        self.assertTrue(any("crew-verifier" in l and "12000" in l and "skills" in l and "OVER" not in l for l in lines))
        status, detail = CI.step_prompt_budget("crew-", False)
        self.assertEqual("FAILED", status)
        self.assertIn("crew-worker", detail)

    def test_within_budget_is_ok(self):
        self.db("crew-worker", [("a", "kanban", 1.0, 1, 39999, 0, 0)])
        self.assertEqual("OK", CI.step_prompt_budget("crew-", False)[0])


class ProvisionFlowTests(unittest.TestCase):
    """The golden path on a scratch tree: the clone is 47 MB-shaped, the provisioned role is not."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-slim-unit-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.saved = {k: getattr(CI, k) for k in ("resolve_profile_home", "h", "hermes_bin")}
        self.addCleanup(lambda: [setattr(CI, k, v) for k, v in self.saved.items()])
        CI.resolve_profile_home = lambda name: os.path.join(self.tmp, "profiles", name)
        CI.hermes_bin = lambda: "/bin/false"
        self.calls = []
        self.src_home = os.path.join(self.tmp, "profiles", "chat")
        cloned_skills(self.src_home, extra_bytes=4_000_000)
        put(os.path.join(self.src_home, "config.yaml"),
            "model:\n  default: x\nplatform_toolsets:\n  cli:\n  - browser\n  - kanban\nagent:\n  max_turns: 150\n")

        self.cfg = FakeConfig()

        class Created(Fake):
            returncode = 0

        def fake_h(profile, *args):
            self.calls.append(args)
            if args[:2] == ("profile", "create"):        # what --clone-from does: copy the whole tree
                shutil.copytree(self.src_home, CI.resolve_profile_home(args[2]))
                return Created()
            if args[:1] == ("config",):
                return self.cfg(profile, *args)
            return Fake()
        CI.h = fake_h

    def test_a_new_role_profile_ends_slim_with_its_toolsets_and_a_second_pass_is_quiet(self):
        status, detail = CI.step_profiles("chat", "crew-", True)
        self.assertEqual("CHANGED", status, detail)
        for role in ("coordinator", "worker", "content", "verifier"):
            home = CI.resolve_profile_home("crew-" + role)
            skills = os.path.join(home, "skills")
            self.assertLess(tree_bytes(skills), 1024 * 1024, role)
            self.assertEqual([".no-bundled-skills", "crew"], sorted(os.listdir(skills)), role)
            for name in CI.skill_names():
                self.assertTrue(os.path.isfile(os.path.join(skills, "crew", name, "SKILL.md")), (role, name))
        worker = CI.resolve_profile_home("crew-worker")
        self.assertEqual("[terminal,file,web,kanban]", CI._cfg("crew-worker", "platform_toolsets.cli"))
        self.assertGreater(tree_bytes(os.path.join(self.src_home, "skills")), 4_000_000, "the source keeps its skills")
        status, detail = CI.step_profiles("chat", "crew-", False)
        self.assertEqual("OK", status, detail)

    def test_a_fat_existing_role_profile_is_found_by_check_mode_and_cut_by_apply(self):
        CI.step_profiles("chat", "crew-", True)
        fat = os.path.join(CI.resolve_profile_home("crew-verifier"), "skills")
        put(os.path.join(fat, ".git", "pack"), "g" * 3_000_000)
        put(os.path.join(fat, "devops", "x", "SKILL.md"), "x")
        status, detail = CI.step_profiles("chat", "crew-", False)
        self.assertEqual("CHANGED", status)
        self.assertIn("update crew-verifier", detail)
        self.assertTrue(os.path.isdir(os.path.join(fat, ".git")), "--check must not delete")
        CI.step_profiles("chat", "crew-", True)
        self.assertEqual([".no-bundled-skills", "crew"], sorted(os.listdir(fat)))

    def test_parity_passes_on_the_provisioned_tree_and_sees_a_stale_role_skill(self):
        import subprocess
        for step in (CI.step_plugin, CI.step_skills, CI.step_roles):
            step(self.src_home, True)
        CI.step_profiles("chat", "crew-", True)
        cmd = [sys.executable, str(REPO / "scripts" / "crew_parity_check.py"), "--package", str(REPO),
               "--profiles", os.path.join(self.tmp, "profiles")]
        ok = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        self.assertEqual(0, ok.returncode, ok.stdout[-600:])
        self.assertIn("PARITY OK", ok.stdout)
        stale = os.path.join(CI.resolve_profile_home("crew-worker"), "skills", "crew", "crew-verifier", "SKILL.md")
        Path(stale).write_text("drifted")
        bad = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        self.assertEqual(1, bad.returncode)
        self.assertIn("skills/crew-verifier/SKILL.md", bad.stdout)

    def test_a_profile_crew_did_not_create_is_never_pruned(self):
        # an existing crew-verifier with no crew/template-shipped.json: someone else's profile under crew's name
        home = CI.resolve_profile_home("crew-verifier")
        put(os.path.join(home, "skills", "mine", "SKILL.md"), "keep me")
        put(os.path.join(home, "SOUL.md"), "own soul")
        self.assertFalse(CI.crew_owned(home))
        status, detail = CI.step_role_skills(home, os.path.join(str(REPO), "templates", "profiles", "verifier"),
                                             self.src_home, True, CI.crew_owned(home))
        self.assertEqual("SKIP", status, detail)
        self.assertTrue(os.path.isfile(os.path.join(home, "skills", "mine", "SKILL.md")))
        CI.step_profiles("chat", "crew-", True)
        self.assertTrue(os.path.isfile(os.path.join(home, "skills", "mine", "SKILL.md")), "step_profiles keeps it too")

    def test_every_removed_path_is_printed(self):
        import contextlib
        import io
        CI.step_profiles("chat", "crew-", True)
        fat = os.path.join(CI.resolve_profile_home("crew-worker"), "skills")
        put(os.path.join(fat, "devops", "x", "SKILL.md"), "x")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            CI.step_profiles("chat", "crew-", True)
        self.assertIn("removed %s" % os.path.join(fat, "devops"), buf.getvalue())

    def test_the_installing_profile_keeps_its_skills(self):
        before = tree_bytes(os.path.join(self.src_home, "skills"))
        CI.step_profiles("chat", "crew-", True)
        CI.step_skills(self.src_home, True)
        self.assertGreaterEqual(tree_bytes(os.path.join(self.src_home, "skills")), before)
        self.assertTrue(os.path.isdir(os.path.join(self.src_home, "skills", "marketing")))


if __name__ == "__main__":
    unittest.main()
