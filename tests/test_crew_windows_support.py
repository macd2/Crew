"""The dashboard server names its host with platform.node(), not os.uname() (absent off POSIX), and the
installer honours HERMES_BIN the way scripts/crew_card.py already does."""
import importlib.util
import os
import platform
import sqlite3
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
        with mock.patch.object(self.mod.shutil, "which", return_value=None):
            self.assertEqual(self.mod.hermes_bin(), os.path.expanduser("~/.local/bin/hermes"))

    def test_matches_crew_card(self):
        card = load("crew_card_bin", os.path.join("scripts", "crew_card.py"))
        os.environ["HERMES_BIN"] = "/opt/hermes/bin/hermes"
        self.assertEqual(self.mod.hermes_bin(), card.hermes_bin())


if __name__ == "__main__":
    unittest.main()
