"""install.py --lineup: the writer roles of the crew come from a lineup's overlay (crew_lineup.build), the role
profiles follow it, crew.lineup and <crew folder>/lineup.json record it, a second run and --check are quiet, and going
back to the shipped crew removes the lineup profiles crew created unless the board still holds open cards for them.

Every `hermes` call is a fake (hermes_fake.FakeConfig for config, a directory for `profile create/delete`); HOME and
HERMES_HOME point at a scratch tree, so nothing reaches a live home."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import module_env  # noqa: E402
module_env.pin(globals(), HERMES_BIN="/bin/false")
from hermes_fake import FakeConfig, Proc  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("crew_install_lineup", str(REPO / "install.py"))
CI = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CI)

DUO = {
    "name": "duo",
    "description": "two writers",
    "roles": [
        {"name": "auditor", "purpose": "Finds vulnerabilities, never fixes them.", "task_class": "review",
         "soul": "You are the auditor of this crew."},
        {"name": "fixer", "purpose": "Fixes what the auditor found.", "model": "claude-sonnet-5-5"},
    ],
}


class _InstallBox(unittest.TestCase):
    """A scratch Hermes home, the fake hermes and a 2-role lineup `duo`; no tests of its own."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-lineup-install-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.board = os.path.join(self.tmp, "kanban.db")
        # Every home the installer can resolve points into the scratch tree: HOME/USERPROFILE (~), and LOCALAPPDATA,
        # which is where native Windows keeps the Hermes home (crew_card.default_home) - role profiles live there.
        env = mock.patch.dict(os.environ, {"HOME": self.tmp, "USERPROFILE": self.tmp, "LOCALAPPDATA": self.tmp,
                                           "HERMES_KANBAN_DB": self.board, "KANBAN_DB": self.board,
                                           "CREW_TEMPLATE_OVERRIDES": os.path.join(self.tmp, "overrides")})
        env.start()
        self.addCleanup(env.stop)
        self.base = CI.crew_card.default_home()
        os.environ["HERMES_HOME"] = self.base
        self.profiles = os.path.join(self.base, "profiles")
        os.makedirs(os.path.join(self.profiles, "chat"))
        self.crew = os.path.join(self.base, "crew")
        conn = sqlite3.connect(self.board)
        conn.execute("create table tasks (id text primary key, title text, assignee text, status text)")
        conn.commit()
        conn.close()
        self.cfg = FakeConfig()
        self.deleted = []
        saved = {k: getattr(CI, k) for k in ("h", "OWNER_RECORD", "PROFILE_PREFIX")}
        self.addCleanup(lambda: [setattr(CI, k, v) for k, v in saved.items()])
        self.addCleanup(CI._use_roles, None)
        CI.OWNER_RECORD = os.path.join(self.crew, "owner.json")
        CI.h = self.fake_h
        self.write_lineup(DUO)

    def fake_h(self, profile, *args):
        if args[:1] == ("config",):
            return self.cfg(profile, *args)
        r = Proc()
        if args[:2] == ("profile", "create"):
            home = os.path.join(self.profiles, args[2])
            os.makedirs(os.path.join(home, "skills"), exist_ok=True)
            return r
        if args[:2] == ("profile", "delete"):
            assert args[3] == "--yes", args
            self.deleted.append(args[2])
            shutil.rmtree(os.path.join(self.profiles, args[2]))
            return r
        if args[:2] == ("plugins", "list"):
            r.stdout = "enabled  1.0  user  crew\n"
            return r
        r.returncode = 1
        return r

    def write_lineup(self, data, name="duo"):
        path = os.path.join(self.crew, "lineups", name + ".json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Path(path).write_text(json.dumps(data), encoding="utf-8")

    def run_installer(self, *extra):
        argv = ["install.py", "--profile", "chat", "--no-service", "--no-cron"] + list(extra)
        out = io.StringIO()
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(out):
            rc = CI.main()
        return rc, out.getvalue()

    def state(self):
        with open(os.path.join(self.crew, "lineup.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def home(self, name):
        return os.path.join(self.profiles, name)

    def add_card(self, assignee, status):
        conn = sqlite3.connect(self.board)
        conn.execute("insert into tasks values (?,?,?,?)", ("t_%s_%s" % (assignee, status), "x", assignee, status))
        conn.commit()
        conn.close()


class LineupInstallTests(_InstallBox):
    def test_a_lineup_install_creates_its_roles_and_converges(self):
        rc, out = self.run_installer("--lineup", "duo")
        self.assertEqual(0, rc, out)
        self.assertEqual(["coordinator", "auditor", "fixer", "verifier"], CI.ROLE_ORDER)
        for role in ("coordinator", "auditor", "fixer", "verifier"):
            self.assertTrue(os.path.isdir(self.home("crew-" + role)), role)
        self.assertFalse(os.path.exists(self.home("crew-worker")))
        auditor = self.home("crew-auditor")
        self.assertIn("You are the auditor of this crew.", Path(auditor, "SOUL.md").read_text(encoding="utf-8"))
        skill = Path(auditor, "skills", "crew", "crew-role-auditor", "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: crew-role-auditor", skill)
        self.assertFalse(os.path.exists(os.path.join(auditor, "skills", "crew", "crew-role-worker")))
        self.assertTrue(os.path.isfile(os.path.join(auditor, "plugins", "crew", "skills", "crew-role-fixer",
                                                    "SKILL.md")))
        self.assertEqual("auditor", self.cfg.store["crew-auditor"]["crew.role"])
        self.assertEqual("claude-sonnet-5-5", self.cfg.store["crew-fixer"]["model.default"])
        roles = json.loads(Path(auditor, "roles", "crew", "roles.json").read_text(encoding="utf-8"))
        self.assertEqual(["coordinator", "auditor", "fixer", "verifier"], [r["name"] for r in roles["roles"]])
        self.assertTrue(os.path.isfile(os.path.join(auditor, "roles", "crew", "briefs", "fixer.md")))
        self.assertEqual("duo", self.cfg.store["chat"]["crew.lineup"])
        st = self.state()
        self.assertEqual(("duo", "ready", ["auditor", "fixer"]), (st["active"], st["status"], st["roles"]))
        # the recorded lineup is the one a plain re-run keeps, and nothing is left to change
        rc, out = self.run_installer("--check")
        self.assertEqual(0, rc, out)
        self.assertIn("nothing to change", out)
        rc, out = self.run_installer()
        self.assertEqual(0, rc, out)
        self.assertNotIn("CHANGED profiles", out)
        self.assertEqual("duo", CI.LINEUP)

    def test_back_to_default_removes_idle_lineup_profiles_and_keeps_one_with_open_cards(self):
        self.assertEqual(0, self.run_installer("--lineup", "duo")[0])
        Path(self.home("crew-fixer"), "own.txt").write_text("x", encoding="utf-8")
        self.add_card("crew-auditor", "running")
        self.add_card("crew-fixer", "done")
        self.add_card("crew-fixer", "archived")
        rc, out = self.run_installer("--lineup", "default", "--check")
        self.assertEqual(1, rc)
        self.assertIn("remove crew-fixer", out)
        self.assertTrue(os.path.isdir(self.home("crew-fixer")), "--check deletes nothing")
        rc, out = self.run_installer("--lineup", "default")
        self.assertEqual(0, rc, out)
        self.assertEqual(["crew-fixer"], self.deleted)
        self.assertFalse(os.path.exists(self.home("crew-fixer")))
        self.assertTrue(os.path.isdir(self.home("crew-auditor")))
        self.assertIn("kept crew-auditor: 1 open card", out)
        for role in ("worker", "content"):
            self.assertTrue(os.path.isdir(self.home("crew-" + role)), role)
        self.assertFalse(os.path.exists(os.path.join(self.home("chat"), "skills", "crew", "crew-role-fixer")))
        self.assertEqual("default", self.cfg.store["chat"]["crew.lineup"])
        self.assertEqual(("default", "ready"), (self.state()["active"], self.state()["status"]))
        rc, out = self.run_installer("--check")
        self.assertEqual(0, rc, out)

    def test_never_deletes_a_profile_crew_did_not_create_or_a_core_role(self):
        self.assertEqual(0, self.run_installer("--lineup", "duo")[0])
        os.makedirs(self.home("crew-mine"))                       # the owner's own, no crew record
        os.remove(os.path.join(self.home("crew-fixer"), CI.SHIPPED_RECORD))
        self.assertEqual(0, self.run_installer("--lineup", "default")[0])
        self.assertEqual(["crew-auditor"], self.deleted)
        self.assertTrue(os.path.isdir(self.home("crew-mine")))
        self.assertTrue(os.path.isdir(self.home("crew-fixer")))
        self.assertTrue(os.path.isdir(self.home("crew-coordinator")))
        self.assertTrue(os.path.isdir(self.home("crew-verifier")))

    def test_an_invalid_lineup_exits_non_zero_and_changes_nothing(self):
        bad = {"name": "bad", "roles": [{"name": "Bad-Role", "purpose": "x"}, {"name": "verifier", "purpose": "y"}]}
        self.write_lineup(bad, "bad")
        rc, out = self.run_installer("--lineup", "bad")
        self.assertEqual(1, rc, out)
        self.assertIn("nothing was changed", out)
        self.assertEqual(["chat"], os.listdir(self.profiles))
        self.assertEqual([], os.listdir(self.home("chat")))
        self.assertEqual({}, self.cfg.store.get("chat", {}))
        st = self.state()
        self.assertEqual(("bad", "failed"), (st["active"], st["status"]))
        self.assertTrue(st["error"])

    def test_an_owner_override_applies_to_a_lineup_role(self):
        over = os.path.join(self.tmp, "overrides", "fixer")
        os.makedirs(over)
        Path(over, "settings.conf").write_text("model.default = my-model\n", encoding="utf-8")
        Path(over, "SOUL.md").write_text("my fixer\n", encoding="utf-8")
        self.assertEqual(0, self.run_installer("--lineup", "duo")[0])
        self.assertEqual("my-model", self.cfg.store["crew-fixer"]["model.default"])
        self.assertEqual("my fixer\n", Path(self.home("crew-fixer"), "SOUL.md").read_text(encoding="utf-8"))
        self.assertEqual(0, self.run_installer("--check")[0])

    def test_the_default_crew_lists_are_the_shipped_ones(self):
        CI._use_roles(None)
        self.assertEqual(["coordinator", "worker", "content", "verifier"], CI.ROLE_ORDER)
        self.assertEqual(["roles.json", "briefs/coordinator.md", "briefs/worker.md", "briefs/content.md",
                          "briefs/verifier.md"], CI.ROLE_FILES)
        self.assertEqual(["plugin.yaml", "__init__.py", "skills/crew-verifier/SKILL.md",
                          "skills/crew-role-worker/SKILL.md", "skills/crew-role-content/SKILL.md",
                          "skills/crew/SKILL.md"], CI.PLUGIN_FILES[:6])
        self.assertEqual(CI._SHIPPED_DESCS, CI.ROLE_DESCS)


class ShippedLineupsStepTests(_InstallBox):
    """step_lineups: the package's crew-home/lineups/ land in <crew>/lineups/ like a downloaded lineup; an owner's
    edit is kept, an unedited copy follows the package, a deleted one comes back."""

    def shipped(self):
        return sorted(p.name for p in (REPO / "crew-home" / "lineups").glob("*.json"))

    def dst(self, name):
        return os.path.join(self.crew, "lineups", name)

    def test_copies_every_shipped_lineup_and_converges(self):
        names = self.shipped()
        self.assertTrue({"security.json", "design.json", "pentest.json"} <= set(names), names)
        self.assertEqual("CHANGED", CI.step_lineups(False)[0])
        self.assertFalse(any(os.path.exists(self.dst(n)) for n in names if n != "duo.json"), "--check writes nothing")
        self.assertEqual("CHANGED", CI.step_lineups(True)[0])
        for n in names:
            self.assertEqual(Path(REPO, "crew-home", "lineups", n).read_bytes(), Path(self.dst(n)).read_bytes(), n)
        self.assertEqual("OK", CI.step_lineups(False)[0])
        # found by name from the crew folder, as a user lineup
        import crew_lineup
        self.assertEqual(crew_lineup.find("pentest"), self.dst("pentest.json"))

    def test_an_owner_edit_is_kept_and_a_deleted_one_comes_back(self):
        CI.step_lineups(True)
        Path(self.dst("design.json")).write_text('{"name": "design", "roles": []}', encoding="utf-8")
        os.remove(self.dst("pentest.json"))
        status, detail = CI.step_lineups(True)
        self.assertEqual("CHANGED", status, detail)
        self.assertIn("kept your edit of design", detail)
        self.assertEqual('{"name": "design", "roles": []}', Path(self.dst("design.json")).read_text(encoding="utf-8"))
        self.assertTrue(os.path.isfile(self.dst("pentest.json")))
        self.assertEqual("OK", CI.step_lineups(False)[0])

    def test_an_unedited_copy_follows_the_package(self):
        CI.step_lineups(True)
        pkg = os.path.join(self.tmp, "pkg")
        shutil.copytree(str(REPO / "crew-home"), os.path.join(pkg, "crew-home"))
        Path(pkg, "crew-home", "lineups", "security.json").write_text('{"name": "security", "roles": [1]}',
                                                                      encoding="utf-8")
        with mock.patch.object(CI, "SRC_DIR", Path(pkg)):
            status, detail = CI.step_lineups(True)
        self.assertEqual("CHANGED", status, detail)
        self.assertIn("update security", detail)
        self.assertIn('"roles": [1]', Path(self.dst("security.json")).read_text(encoding="utf-8"))

    def test_the_installer_runs_the_step(self):
        rc, out = self.run_installer("--lineup", "duo")
        self.assertEqual(0, rc, out)
        self.assertIn("shipped lineups", out)
        for n in self.shipped():
            self.assertTrue(os.path.isfile(self.dst(n)), n)


class UninstallLineupTests(_InstallBox):
    """--uninstall-lineup NAME: the reverse of --lineup NAME. Its role profiles and role skills go entirely, the crew is
    the shipped one again, the build folder goes; the lineup file (the recipe) stays. Refused with open cards."""

    def lineup_file(self):
        return os.path.join(self.crew, "lineups", "duo.json")

    def test_uninstall_the_active_lineup_removes_its_profiles_and_keeps_the_file(self):
        self.assertEqual(0, self.run_installer("--lineup", "duo")[0])
        recipe = Path(self.lineup_file()).read_bytes()
        rc, out = self.run_installer("--uninstall-lineup", "duo", "--check")
        self.assertEqual(1, rc, out)
        self.assertIn("role profiles removed entirely: crew-auditor, crew-fixer", out)
        self.assertTrue(os.path.isdir(self.home("crew-auditor")), "--check removes nothing")
        rc, out = self.run_installer("--uninstall-lineup", "duo")
        self.assertEqual(0, rc, out)
        self.assertIn("lineup duo uninstalled", out)
        self.assertEqual(["crew-auditor", "crew-fixer"], sorted(self.deleted))
        for role in ("auditor", "fixer"):
            self.assertFalse(os.path.exists(self.home("crew-" + role)), role)
            for other in ("chat", "crew-coordinator", "crew-worker"):
                self.assertFalse(os.path.exists(os.path.join(self.home(other), "skills", "crew", "crew-role-" + role)),
                                 (other, role))
        for role in ("coordinator", "worker", "content", "verifier"):
            self.assertTrue(os.path.isdir(self.home("crew-" + role)), role)
        self.assertEqual(recipe, Path(self.lineup_file()).read_bytes(), "the lineup file is the recipe: it stays")
        self.assertFalse(os.path.exists(os.path.join(self.crew, "lineup-build", "duo")))
        self.assertEqual("default", self.cfg.store["chat"]["crew.lineup"])
        self.assertEqual(("default", "ready"), (self.state()["active"], self.state()["status"]))
        self.assertEqual(0, self.run_installer("--check")[0])
        # and it installs again from the same file
        self.assertEqual(0, self.run_installer("--lineup", "duo")[0])
        self.assertTrue(os.path.isdir(self.home("crew-auditor")))

    def test_an_open_card_refuses_the_uninstall_and_changes_nothing(self):
        self.assertEqual(0, self.run_installer("--lineup", "duo")[0])
        self.add_card("crew-fixer", "running")
        rc, out = self.run_installer("--uninstall-lineup", "duo")
        self.assertEqual(1, rc, out)
        self.assertIn("crew-fixer (1 open card)", out)
        self.assertEqual([], self.deleted)
        self.assertTrue(os.path.isdir(self.home("crew-fixer")))
        self.assertEqual("duo", self.cfg.store["chat"]["crew.lineup"])

    def test_uninstall_a_lineup_that_is_not_in_force_removes_its_leftover_profiles(self):
        self.write_lineup({"name": "trio", "roles": [{"name": "scout", "purpose": "Scouts."}]}, name="trio")
        self.assertEqual(0, self.run_installer("--lineup", "duo")[0])
        self.assertEqual(0, self.run_installer("--lineup", "trio")[0])   # duo's profiles go when trio comes in
        self.assertTrue(os.path.isdir(self.home("crew-scout")))
        rc, out = self.run_installer("--uninstall-lineup", "duo")
        self.assertEqual(0, rc, out)
        self.assertTrue(os.path.isdir(self.home("crew-scout")), "the lineup in force is untouched")
        self.assertEqual("trio", self.cfg.store["chat"]["crew.lineup"])
        self.assertTrue(os.path.isfile(self.lineup_file()))

    def test_default_and_unknown_lineups_are_refused(self):
        for name in ("default", "nosuch"):
            rc, out = self.run_installer("--uninstall-lineup", name)
            self.assertEqual(1, rc, out)
            self.assertIn("not uninstalled", out)
        rc, out = self.run_installer("--lineup", "duo", "--uninstall-lineup", "duo")
        self.assertEqual(1, rc, out)


if __name__ == "__main__":
    unittest.main()
