"""The dashboard server names its host with platform.node(), not os.uname() (absent off POSIX), the
installer honours HERMES_BIN the way scripts/crew_card.py already does, and the two Windows helpers in
the plugin - _which_hermes (skip a PATH hit this OS cannot run) and crew_safety._home_vars (keep a home
the child can read, without inventing one on POSIX) - pick the right answer on every platform."""
import importlib.util
import os
import platform
import sqlite3
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def no_uname():
    """os as it is on a platform without uname(): any call is the AttributeError the server used to hit."""
    return mock.patch.object(os, "uname", create=True,
                             side_effect=AttributeError("module 'os' has no attribute 'uname'"))


def restore_env(saved):
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


class BoardNodeName(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        db = os.path.join(self.tmp.name, "kanban.db")
        conn = sqlite3.connect(db)
        conn.execute("create table tasks (id text, title text, status text, assignee text, created_at int, "
                     "started_at int, completed_at int, body text, skills text, last_failure_error text)")
        conn.commit()
        conn.close()
        self.addCleanup(restore_env, {k: os.environ.get(k) for k in ("KANBAN_DB", "HERMES_KANBAN_DB")})
        os.environ.pop("HERMES_KANBAN_DB", None)
        os.environ["KANBAN_DB"] = db
        self.mod = load("cgs_node", os.path.join("scripts", "crew_graph_serve.py"))

    def test_board_data_names_the_node_without_uname(self):
        with no_uname(), mock.patch.object(platform, "node", return_value="crew-host"):
            data = self.mod.board_data()
        self.assertNotIn("error", data)
        self.assertEqual(data["node"], "crew-host")

    def test_server_no_longer_calls_uname(self):
        with open(os.path.join(REPO, "scripts", "crew_graph_serve.py"), encoding="utf-8") as fh:
            self.assertNotIn("os.uname", fh.read())


class HermesBin(unittest.TestCase):
    def setUp(self):
        self.mod = load("crew_install_bin", "install.py")
        self.addCleanup(restore_env, {"HERMES_BIN": os.environ.get("HERMES_BIN")})

    def test_hermes_bin_env_wins(self):
        os.environ["HERMES_BIN"] = "/opt/hermes/bin/hermes"
        with mock.patch.object(self.mod.shutil, "which", return_value="/usr/bin/hermes"):
            self.assertEqual(self.mod.hermes_bin(), "/opt/hermes/bin/hermes")

    def test_unset_falls_back_to_path_then_local_bin(self):
        os.environ.pop("HERMES_BIN", None)
        with mock.patch.object(self.mod.shutil, "which", return_value="/usr/bin/hermes"):
            self.assertEqual(self.mod.hermes_bin(), "/usr/bin/hermes")
        with mock.patch.object(self.mod.shutil, "which", return_value=None), \
                mock.patch.object(self.mod.crew_card, "hermes_exe", return_value=""):
            want = (os.path.join(self.mod.crew_card.default_home(), "bin", "hermes.exe") if os.name == "nt"
                    else os.path.expanduser("~/.local/bin/hermes"))
            self.assertEqual(self.mod.hermes_bin(), want)

    def test_hermes_exe_prefers_checkout_launcher_and_ignores_pm_installs(self):
        card = load("crew_card_pm", os.path.join("scripts", "crew_card.py"))
        cand_checkout = os.path.normpath("C:/repo/hermes-agent/.hermes/bin/hermes.exe")
        cand_pm = os.path.normpath("C:/home/installs/abc/environments/xyz/venv/Scripts/hermes.exe")
        with mock.patch.object(card, "hermes_root", return_value="C:/repo/hermes-agent"), \
                mock.patch.object(card, "hermes_python", return_value="C:/home/installs/abc/environments/xyz/venv/Scripts/python.exe"), \
                mock.patch.object(os.path, "isfile", side_effect=lambda p: os.path.normpath(p) in (cand_checkout, cand_pm)):
            # Checkout launcher must win over PM venv
            self.assertEqual(card.hermes_exe(), cand_checkout)

        # When no checkout launcher exists, PM venv must still be ignored
        with mock.patch.object(card, "hermes_root", return_value="C:/repo/hermes-agent"), \
                mock.patch.object(card, "hermes_python", return_value="C:/home/installs/abc/environments/xyz/venv/Scripts/python.exe"), \
                mock.patch.object(card, "default_home", return_value="C:/home"), \
                mock.patch.object(os.path, "isfile", side_effect=lambda p: os.path.normpath(p) == cand_pm):
            self.assertEqual(card.hermes_exe(), "")

    def test_a_cmd_launcher_gives_way_to_a_real_exe_on_windows(self):
        # Hermes Desktop's bin\hermes.cmd cut a multi-line card body to its first line (2026-10-14, Windows 11)
        card = load("crew_card_cmd", os.path.join("scripts", "crew_card.py"))
        os.environ.pop("HERMES_BIN", None)
        with mock.patch.object(card, "IS_WINDOWS", True), \
                mock.patch.object(card.shutil, "which", return_value=r"C:\h\bin\hermes.cmd"), \
                mock.patch.object(card, "hermes_exe", return_value=r"C:\h\venv\Scripts\hermes.exe"):
            self.assertEqual(card.hermes_bin(), r"C:\h\venv\Scripts\hermes.exe")
        with mock.patch.object(card, "IS_WINDOWS", True), \
                mock.patch.object(card.shutil, "which", return_value=r"C:\h\bin\hermes.cmd"), \
                mock.patch.object(card, "hermes_exe", return_value=""):
            self.assertEqual(card.hermes_bin(), r"C:\h\bin\hermes.cmd")      # no exe anywhere: the .cmd still beats nothing
        os.environ["HERMES_BIN"] = r"C:\mine\hermes.cmd"
        with mock.patch.object(card, "IS_WINDOWS", True), \
                mock.patch.object(card, "hermes_exe", return_value=r"C:\h\venv\Scripts\hermes.exe"):
            self.assertEqual(card.hermes_bin(), r"C:\mine\hermes.cmd")        # an explicit HERMES_BIN is obeyed

    def test_matches_crew_card(self):
        card = load("crew_card_bin", os.path.join("scripts", "crew_card.py"))
        os.environ["HERMES_BIN"] = "/opt/hermes/bin/hermes"
        self.assertEqual(self.mod.hermes_bin(), card.hermes_bin())


def touch(d, name, size):
    p = os.path.join(d, name)
    with open(p, "wb") as fh:
        fh.write(b"x" * size)
    return p


class WhichHermes(unittest.TestCase):
    """_which_hermes walks PATH by PATHEXT and returns the first hermes this OS can run, falling back to
    shutil.which. The win32 branch is exercised on any runner by patching sys.platform and os.pathsep."""

    def setUp(self):
        self.mod = load("crew_pkg_which", "__init__.py")

    def _win32(self, path, pathext):
        return (mock.patch.object(sys, "platform", "win32"),
                mock.patch.object(os, "pathsep", ";"),
                mock.patch.dict(os.environ, {"PATH": path, "PATHEXT": pathext}))

    def test_skips_zero_byte_stub_and_walks_pathext(self):
        stub = touch(tempfile.mkdtemp(), "hermes.exe", 0)     # the System32 stub that used to lead PATH
        good = touch(tempfile.mkdtemp(), "hermes.exe", 10)    # the real bin/hermes.exe behind it
        cm = self._win32(";".join([os.path.dirname(stub), os.path.dirname(good)]), ".EXE;.CMD;.BAT")
        with cm[0], cm[1], cm[2]:
            self.assertEqual(self.mod._which_hermes(), good)

    def test_walks_pathext_to_a_runnable_launcher(self):
        d = tempfile.mkdtemp()
        cmd = touch(d, "hermes.cmd", 5)
        touch(d, "hermes", 5)                                 # POSIX script, no runnable ext: ignored on win32
        cm = self._win32(d, ".EXE;.CMD;.BAT")
        with cm[0], cm[1], cm[2]:
            self.assertEqual(self.mod._which_hermes(), cmd)

    def test_falls_back_to_shutil_which(self):
        cm = self._win32(tempfile.mkdtemp(), ".EXE;.BAT")
        with cm[0], cm[1], cm[2], mock.patch.object(self.mod.shutil, "which", return_value="/usr/bin/hermes"):
            self.assertEqual(self.mod._which_hermes(), "/usr/bin/hermes")


class HomeVars(unittest.TestCase):
    """crew_safety._home_vars keeps a home the child's Path.home() reads, but cross-fills USERPROFILE only
    on Windows: on POSIX a copied HOME would hand every proof and coordinator child a bogus username."""

    def setUp(self):
        self.mod = load("crew_safety_home", os.path.join("scripts", "crew_safety.py"))

    def _env(self, platform_name, parent, child):
        with mock.patch.object(sys, "platform", platform_name), \
             mock.patch.dict(os.environ, parent, clear=True):
            return self.mod._home_vars(dict(child))

    def test_win32_home_from_userprofile(self):
        env = self._env("win32", {}, {"USERPROFILE": "C:\\Users\\thana"})
        self.assertEqual(env.get("HOME"), "C:\\Users\\thana")

    def test_win32_userprofile_from_home(self):
        env = self._env("win32", {}, {"HOME": "C:\\Users\\thana"})
        self.assertEqual(env.get("USERPROFILE"), "C:\\Users\\thana")

    def test_win32_pulls_systemroot_from_parent(self):
        env = self._env("win32", {"SYSTEMROOT": "C:\\Windows"}, {})
        self.assertEqual(env.get("SYSTEMROOT"), "C:\\Windows")

    def test_posix_does_not_invent_userprofile(self):
        env = self._env("linux", {}, {"HOME": "/home/crew"})
        self.assertEqual(env.get("HOME"), "/home/crew")
        self.assertNotIn("USERPROFILE", env)


class InstallerGraphUnit(unittest.TestCase):
    """install.py's graph-http step is the one step with no native Windows equivalent (no systemd --user):
    it must SKIP on win32 without --no-service and shell out to nothing, while --no-service still works on
    POSIX."""

    def setUp(self):
        self.mod = load("crew_install_unit", "install.py")

    def test_win32_skips_without_the_flag(self):
        with mock.patch.object(sys, "platform", "win32"), \
             mock.patch.object(self.mod.subprocess, "run",
                               side_effect=AssertionError("systemctl run on Windows")) as run:
            status, msg = self.mod.step_graph_unit(tempfile.mkdtemp(), apply=True, no_service=False)
        self.assertEqual(status, "SKIP")
        self.assertIn("WINDOWS.md", msg)
        run.assert_not_called()

    def test_posix_honours_no_service_flag(self):
        with mock.patch.object(sys, "platform", "linux"), \
             mock.patch.object(self.mod.subprocess, "run",
                               side_effect=AssertionError("systemctl run with --no-service")):
            status, msg = self.mod.step_graph_unit(tempfile.mkdtemp(), apply=True, no_service=True)
        self.assertEqual(status, "SKIP")
        self.assertIn("--no-service", msg)

    def _active_unit(self, calls):
        """An installed, identical, running unit: systemctl answers `active` and every call is recorded."""
        home = tempfile.mkdtemp()
        unit_dir = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, home, True)
        self.addCleanup(shutil.rmtree, str(unit_dir), True)
        with mock.patch.object(sys, "platform", "linux"):     # the unit text depends on the platform
            unit = self.mod.render_graph_unit(home, 8799)
        (unit_dir / self.mod.UNIT_GRAPH_NAME).write_bytes(unit.encode())

        def fake(cmd, **kw):
            calls.append(cmd)
            return mock.Mock(stdout="active\n", returncode=0)
        return home, unit_dir, fake

    def test_an_upgrade_restarts_a_running_daemon_that_loaded_the_old_code(self):
        calls = []
        home, unit_dir, fake = self._active_unit(calls)
        with mock.patch.object(sys, "platform", "linux"), mock.patch.object(self.mod, "UNIT_DIR", unit_dir), \
             mock.patch.object(self.mod.subprocess, "run", fake):
            status, msg = self.mod.step_graph_unit(home, True, False, 8799, code_changed=True)
        self.assertEqual(status, "CHANGED")
        self.assertIn(["systemctl", "--user", "restart", self.mod.UNIT_GRAPH_NAME], calls)

    def test_no_code_change_leaves_a_running_daemon_alone(self):
        calls = []
        home, unit_dir, fake = self._active_unit(calls)
        with mock.patch.object(sys, "platform", "linux"), mock.patch.object(self.mod, "UNIT_DIR", unit_dir), \
             mock.patch.object(self.mod.subprocess, "run", fake):
            status, _ = self.mod.step_graph_unit(home, True, False, 8799, code_changed=False)
        self.assertEqual(status, "OK")
        self.assertFalse([c for c in calls if "restart" in c])

    def test_a_check_run_reports_the_restart_without_doing_it(self):
        calls = []
        home, unit_dir, fake = self._active_unit(calls)
        with mock.patch.object(sys, "platform", "linux"), mock.patch.object(self.mod, "UNIT_DIR", unit_dir), \
             mock.patch.object(self.mod.subprocess, "run", fake):
            status, _ = self.mod.step_graph_unit(home, False, False, 8799, code_changed=True)
        self.assertEqual(status, "CHANGED")
        self.assertFalse([c for c in calls if "restart" in c])


if __name__ == "__main__":
    unittest.main()
