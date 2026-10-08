import unittest
import os
import tempfile
import sqlite3
from pathlib import Path


class KanbanMultiBoardResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = self.tmp.name
        self.old_home = os.environ.get("HERMES_HOME")
        os.environ["HERMES_HOME"] = self.home

        # Setup board directory structure
        self.k_home = os.path.join(self.home, "kanban")
        self.board_dir = os.path.join(self.k_home, "boards", "test-board")
        os.makedirs(self.board_dir, exist_ok=True)
        self.test_db = os.path.join(self.board_dir, "kanban.db")
        conn = sqlite3.connect(self.test_db)
        conn.execute("create table tasks (id text primary key, title text, status text, assignee text, body text)")
        conn.execute("insert into tasks values ('t_test1', 'Task 1', 'ready', 'worker', 'Body 1')")
        conn.commit()
        conn.close()

    def tearDown(self):
        if self.old_home is not None:
            os.environ["HERMES_HOME"] = self.old_home
        else:
            os.environ.pop("HERMES_HOME", None)
        os.environ.pop("HERMES_KANBAN_BOARD", None)
        os.environ.pop("HERMES_KANBAN_DB", None)
        self.tmp.cleanup()

    def test_current_board_pointer_resolution(self):
        cur_file = os.path.join(self.k_home, "current")
        with open(cur_file, "w", encoding="utf-8") as f:
            f.write("test-board\n")

        import crew_graph
        resolved = crew_graph.kanban_db_path()
        self.assertEqual(resolved, self.test_db)

    def test_hermes_kanban_board_env_resolution(self):
        os.environ["HERMES_KANBAN_BOARD"] = "test-board"
        import crew_graph
        resolved = crew_graph.kanban_db_path()
        self.assertEqual(resolved, self.test_db)

    def test_default_board_resolves_to_root_kanban_db(self):
        root_db = os.path.join(self.home, "kanban.db")
        Path(root_db).touch()
        cur_file = os.path.join(self.k_home, "current")
        with open(cur_file, "w", encoding="utf-8") as f:
            f.write("default\n")

        import crew_graph
        resolved = crew_graph.kanban_db_path()
        self.assertEqual(resolved, root_db)

    def test_hermes_kanban_db_direct_pin(self):
        pinned_db = os.path.join(self.home, "pinned.db")
        Path(pinned_db).touch()
        os.environ["HERMES_KANBAN_DB"] = pinned_db
        import crew_graph
        resolved = crew_graph.kanban_db_path()
        self.assertEqual(resolved, pinned_db)


if __name__ == "__main__":
    unittest.main()
