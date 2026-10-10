#!/usr/bin/env python3
"""Unit tests for the one kanban board resolver, scripts/crew_card.py kanban_db().

The rules pinned here: a HERMES_KANBAN_DB / KANBAN_DB pin wins; where hermes_cli is importable its
kanban_db.kanban_db_path() decides, and crew_graph.kanban_db_path() and the plugin's _tasks_db() go through
crew_card rather than carrying their own copy; under a bare interpreter _kanban_db_fallback() mirrors Hermes:
HERMES_KANBAN_BOARD, then kanban/current, each only for a valid slug naming a live (board.json, not archived)
board under HERMES_KANBAN_HOME or the base home, else the default board's <root>/kanban.db.
Runs standalone (python tests/test_crew_kanban_multi_board.py) and in the suite; every variable it touches is
restored, and nothing reads a real board.
"""
import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCRIPTS = os.path.join(REPO, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import crew_card  # noqa: E402
import crew_graph  # noqa: E402

ENV_KEYS = ("HERMES_HOME", "HERMES_KANBAN_HOME", "HERMES_KANBAN_BOARD", "HERMES_KANBAN_DB", "KANBAN_DB")


def make_db(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("create table tasks (id text primary key, title text, status text, assignee text, body text)")
    conn.commit()
    conn.close()
    return path


def make_board(root, slug, archived=False, board_json=True):
    """<root>/kanban/boards/<slug>/ with a kanban.db and, unless board_json is False, its board.json."""
    b_dir = os.path.join(root, "kanban", "boards", slug)
    db = make_db(os.path.join(b_dir, "kanban.db"))
    if board_json:
        with open(os.path.join(b_dir, "board.json"), "w", encoding="utf-8") as fh:
            json.dump({"name": slug, "archived": archived}, fh)
    return db


class ResolverTestCase(unittest.TestCase):
    def setUp(self):
        self.saved = {k: os.environ.get(k) for k in ENV_KEYS}
        self.addCleanup(self.restore_env)
        for k in ENV_KEYS:
            os.environ.pop(k, None)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = os.path.realpath(self.tmp.name)
        os.environ["HERMES_HOME"] = self.home
        self.root_db = make_db(os.path.join(self.home, "kanban.db"))
        self.board_db = make_board(self.home, "test-board")

    def restore_env(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def write_current(self, slug, root=None):
        path = os.path.join(root or self.home, "kanban", "current")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(slug + "\n")

    def bare(self):
        """Resolve as a bare interpreter would: hermes_cli reported not importable."""
        return mock.patch.object(crew_card, "_hermes_kanban_db_path", return_value=None)

    def assertSamePath(self, want, got):
        self.assertIsNotNone(got)
        self.assertEqual(os.path.normcase(os.path.realpath(want)), os.path.normcase(os.path.realpath(got)))


class FallbackResolutionTests(ResolverTestCase):
    def test_current_pointer_names_a_live_board(self):
        self.write_current("test-board")
        with self.bare():
            self.assertSamePath(self.board_db, crew_card.kanban_db())
            self.assertSamePath(self.board_db, crew_graph.kanban_db_path())

    def test_hermes_kanban_board_env_outranks_the_pointer(self):
        other = make_board(self.home, "other")
        self.write_current("other")
        os.environ["HERMES_KANBAN_BOARD"] = "test-board"
        with self.bare():
            self.assertSamePath(self.board_db, crew_card.kanban_db())
        os.environ.pop("HERMES_KANBAN_BOARD")
        with self.bare():
            self.assertSamePath(other, crew_card.kanban_db())

    def test_default_board_resolves_to_the_root_kanban_db(self):
        self.write_current("default")
        with self.bare():
            self.assertSamePath(self.root_db, crew_card.kanban_db())
        os.remove(os.path.join(self.home, "kanban", "current"))
        with self.bare():
            self.assertSamePath(self.root_db, crew_card.kanban_db())

    def test_a_db_pin_wins_over_board_and_pointer(self):
        pinned = make_db(os.path.join(self.home, "pinned.db"))
        self.write_current("test-board")
        os.environ["HERMES_KANBAN_BOARD"] = "test-board"
        os.environ["HERMES_KANBAN_DB"] = pinned
        with mock.patch.object(crew_card, "_hermes_kanban_db_path", side_effect=AssertionError("pin must win")):
            self.assertSamePath(pinned, crew_card.kanban_db())
            self.assertSamePath(pinned, crew_graph.kanban_db_path())
        os.environ.pop("HERMES_KANBAN_DB")
        os.environ["KANBAN_DB"] = pinned
        with self.bare():
            self.assertSamePath(pinned, crew_card.kanban_db())

    def test_a_malformed_slug_never_becomes_a_path(self):
        self.assertEqual("", crew_card._valid_board_slug("../escape"))
        self.assertEqual("", crew_card._valid_board_slug("a/b"))
        self.assertEqual("", crew_card._valid_board_slug("-lead"))
        self.assertEqual("", crew_card._valid_board_slug(""))
        self.assertEqual("test-board", crew_card._valid_board_slug("  Test-Board\n"))
        # a live board one level above the boards dir: `../escape` must not reach it
        escape = os.path.join(self.home, "kanban", "escape")
        make_db(os.path.join(escape, "kanban.db"))
        with open(os.path.join(escape, "board.json"), "w", encoding="utf-8") as fh:
            json.dump({"name": "escape"}, fh)
        self.write_current("../escape")
        with self.bare():
            self.assertSamePath(self.root_db, crew_card.kanban_db())
        os.environ["HERMES_KANBAN_BOARD"] = "../escape"
        with self.bare():
            self.assertSamePath(self.root_db, crew_card.kanban_db())

    def test_an_archived_or_unmarked_board_falls_through_to_default(self):
        make_board(self.home, "gone", archived=True)
        make_board(self.home, "stub", board_json=False)
        boards = os.path.join(self.home, "kanban", "boards")
        self.assertFalse(crew_card._board_holds_live_board(os.path.join(boards, "gone")))
        self.assertFalse(crew_card._board_holds_live_board(os.path.join(boards, "stub")))
        self.assertTrue(crew_card._board_holds_live_board(os.path.join(boards, "test-board")))
        for slug in ("gone", "stub"):
            self.write_current(slug)
            with self.bare():
                self.assertSamePath(self.root_db, crew_card.kanban_db())
        # an archived HERMES_KANBAN_BOARD falls through to the pointer, as Hermes's get_current_board does
        os.environ["HERMES_KANBAN_BOARD"] = "gone"
        self.write_current("test-board")
        with self.bare():
            self.assertSamePath(self.board_db, crew_card.kanban_db())

    def test_hermes_kanban_home_roots_the_boards(self):
        k_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(k_tmp.cleanup)
        k_root = os.path.realpath(k_tmp.name)
        k_root_db = make_db(os.path.join(k_root, "kanban.db"))
        k_board = make_board(k_root, "shared")
        os.environ["HERMES_KANBAN_HOME"] = k_root
        self.assertSamePath(k_root, crew_card.kanban_home())
        with self.bare():
            self.assertSamePath(k_root_db, crew_card.kanban_db())
        self.write_current("shared", root=k_root)
        with self.bare():
            self.assertSamePath(k_board, crew_card.kanban_db())
        # the base home's pointer is not the kanban home's
        os.remove(os.path.join(k_root, "kanban", "current"))
        self.write_current("test-board")
        with self.bare():
            self.assertSamePath(k_root_db, crew_card.kanban_db())


class DelegationTests(ResolverTestCase):
    def test_hermes_resolver_decides_where_importable_and_every_entry_point_uses_it(self):
        fake_kb = types.SimpleNamespace(kanban_db_path=lambda: Path(self.board_db))
        with mock.patch.dict(os.environ, {"HERMES_BIN": os.environ.get("HERMES_BIN") or "/bin/false"}):
            spec = importlib.util.spec_from_file_location("crew_plugin_multi_board_test",
                                                          os.path.join(REPO, "__init__.py"))
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)
        with mock.patch.object(crew_card, "hermes_kb", return_value=(fake_kb, None)), \
                mock.patch.object(plugin, "_card_tool", return_value=crew_card), \
                mock.patch.object(crew_card, "_kanban_db_fallback", side_effect=AssertionError("Hermes decides")):
            self.assertSamePath(self.board_db, crew_card.kanban_db())
            self.assertSamePath(self.board_db, crew_graph.kanban_db_path())
            self.assertSamePath(self.board_db, plugin._tasks_db())
        # no copy of the resolver is left outside crew_card
        for path in (os.path.join(SCRIPTS, "crew_graph.py"), os.path.join(REPO, "__init__.py")):
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            self.assertNotIn('"current"', src, path)
            self.assertNotIn('"boards"', src, path)
        # a missing hermes_cli means the crew-side fallback, never an error
        with mock.patch.object(crew_card, "hermes_kb", side_effect=RuntimeError("no hermes_cli")):
            self.assertIsNone(crew_card._hermes_kanban_db_path())
            self.assertSamePath(self.root_db, crew_card.kanban_db())


if __name__ == "__main__":
    unittest.main()
