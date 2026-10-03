#!/usr/bin/env python3
"""Unit tests for the proofs board: every proof seeds cards on the crew-proofs board, never the live one.

No hermes CLI and no live board: HERMES_BIN is /bin/false (a scratch HERMES_HOME would make the real launcher
bootstrap a runtime and rewrite itself), HERMES_KANBAN_HOME and every pin point into a throwaway directory.
"""
import contextlib
import io
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
os.environ.setdefault("HERMES_BIN", "/bin/false")

import crew_proof_board as pb  # noqa: E402
import crew_proofs  # noqa: E402

PINS = ("HERMES_KANBAN_DB", "KANBAN_DB", "HERMES_KANBAN_HOME", "HERMES_KANBAN_BOARD", "CREW_GRAPH_BASE",
        "CREW_GRAPH_URL")


class BoardCase(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        for key in PINS:
            os.environ.pop(key, None)
        self.tmp = tempfile.mkdtemp(prefix="crew-proofboard-unit-")
        os.environ["HERMES_KANBAN_HOME"] = self.tmp        # the kernel root: the "live" default board is here
        self.live = os.path.join(self.tmp, "kanban.db")
        sqlite3.connect(self.live).close()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scratch_db(self):
        path = os.path.join(self.tmp, "scratch", "kanban.db")
        os.makedirs(os.path.dirname(path))
        sqlite3.connect(path).close()
        return path

    def refused(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            pb.require_proof_board("x_proof.py")
        return cm.exception.code, err.getvalue()


class GuardTest(BoardCase):
    def test_no_pin_exits_2_before_anything_is_created(self):
        code, msg = self.refused()
        self.assertEqual(code, 2)
        self.assertIn("would use the live board", msg)

    def test_pin_on_the_live_default_board_exits_2_for_either_variable(self):
        for var in ("KANBAN_DB", "HERMES_KANBAN_DB"):
            os.environ.pop("KANBAN_DB", None)
            os.environ.pop("HERMES_KANBAN_DB", None)
            os.environ[var] = self.live
            code, msg = self.refused()
            self.assertEqual(code, 2, var)
            self.assertIn("is the live board", msg)

    def test_one_live_pin_is_enough_even_when_the_other_is_scratch(self):
        os.environ["KANBAN_DB"] = self.scratch_db()
        os.environ["HERMES_KANBAN_DB"] = self.live
        self.assertEqual(self.refused()[0], 2)

    def test_a_path_that_reaches_the_live_file_another_way_is_still_live(self):
        link = os.path.join(self.tmp, "alias.db")
        os.symlink(self.live, link)
        os.environ["KANBAN_DB"] = os.path.join(self.tmp, "scratch", "..", "alias.db")
        os.makedirs(os.path.join(self.tmp, "scratch"))
        self.assertEqual(self.refused()[0], 2)

    def test_a_missing_file_exits_2_instead_of_creating_a_schemaless_one(self):
        os.environ["KANBAN_DB"] = os.path.join(self.tmp, "nope", "kanban.db")
        code, msg = self.refused()
        self.assertEqual(code, 2)
        self.assertIn("does not exist", msg)

    def test_a_scratch_board_passes_and_is_the_file_returned(self):
        db = self.scratch_db()
        os.environ["KANBAN_DB"] = db
        self.assertEqual(pb.require_proof_board("x_proof.py"), db)
        self.assertEqual(pb.proof_db(), db)


class ProofsBoardTest(BoardCase):
    def test_the_proofs_board_lives_under_the_kernel_boards_root_not_at_the_default_file(self):
        self.assertEqual(pb.proofs_db(), os.path.join(self.tmp, "kanban", "boards", "crew-proofs", "kanban.db"))
        self.assertNotEqual(os.path.realpath(pb.proofs_db()), os.path.realpath(pb.default_db()))

    def test_a_profile_home_steps_up_to_the_base_home(self):
        del os.environ["HERMES_KANBAN_HOME"]
        os.environ["HERMES_HOME"] = os.path.join(self.tmp, "profiles", "crew-worker")
        self.assertEqual(pb.default_db(), os.path.join(self.tmp, "kanban.db"))

    def test_the_child_env_pins_every_reader_to_the_proofs_board(self):
        env = pb.proofs_env()
        self.assertEqual(env["HERMES_KANBAN_BOARD"], "crew-proofs")
        self.assertEqual(env["HERMES_KANBAN_DB"], pb.proofs_db())
        self.assertEqual(env["KANBAN_DB"], pb.proofs_db())
        for key in ("HERMES_KANBAN_WORKSPACES_ROOT", "HERMES_KANBAN_ATTACHMENTS_ROOT"):
            self.assertTrue(env[key].startswith(pb.proofs_dir() + os.sep), key)

    def test_the_pinned_proofs_env_passes_the_guard_once_the_board_exists(self):
        os.makedirs(pb.proofs_dir())
        sqlite3.connect(pb.proofs_db()).close()
        os.environ.update(pb.proofs_env())
        self.assertEqual(pb.require_proof_board("x_proof.py"), pb.proofs_db())


class RunnerTest(BoardCase):
    def test_a_normal_proof_is_pinned_and_a_live_service_proof_is_not(self):
        pinned = crew_proofs.child_env("crew_brief_proof.py")
        self.assertEqual(pinned["KANBAN_DB"], pb.proofs_db())
        os.environ["KANBAN_DB"] = "/somewhere/else.db"
        self.assertEqual(crew_proofs.child_env("crew_graph_flow_check.py")["KANBAN_DB"], "/somewhere/else.db")

    def test_a_proof_on_the_live_board_is_never_picked_without_its_hold_being_lifted(self):
        held = set(crew_proofs.LIVE) | set(crew_proofs.NEEDS_ARGS)
        self.assertTrue(crew_proofs.LIVE_BOARD <= held, crew_proofs.LIVE_BOARD - held)

        class Args:
            only, all, card = "", False, ""

        picked, _skipped = crew_proofs.choose(Args)
        self.assertFalse(crew_proofs.LIVE_BOARD & set(picked), crew_proofs.LIVE_BOARD & set(picked))

    def test_a_live_reader_seeds_and_writes_nothing(self):
        writes = re.compile(r"insert into|update tasks|delete from|crew_card\.py[\"']?\s*,?\s*[\"']?open|"
                            r"create_card|open_card|sqlite3\.connect\((?!.*mode=ro)", re.I)
        for name in crew_proofs.LIVE_READERS:
            self.assertIn(name, crew_proofs.candidates())
            self.assertFalse(writes.search((SCRIPTS / name).read_text()), name)
            self.assertNotIn(name, crew_proofs.LIVE)

    def test_no_other_proof_defaults_to_the_live_board_file(self):
        rx = re.compile(r"environ\.get\(\s*[\"']KANBAN_DB[\"']\s*,[^)]*kanban\.db")
        bad = []
        for path in sorted(SCRIPTS.glob("*.py")):
            if path.name in crew_proofs.LIVE_BOARD or not re.search(r"(_proof|_check)\.py$|live_walk", path.name):
                continue
            if rx.search(path.read_text()):
                bad.append(path.name)
        self.assertEqual(bad, [])

    def test_every_proof_that_writes_its_board_asks_the_guard_first(self):
        writes = re.compile(r"sqlite3\.connect\((?:KANBAN_DB|DB)[,)]")
        unguarded = []
        for path in sorted(SCRIPTS.glob("*_proof.py")):
            text = path.read_text()
            if path.name in crew_proofs.LIVE_BOARD or not writes.search(text):
                continue
            if "crew_proof_board" not in text and "init_board" not in text:
                unguarded.append(path.name)
        self.assertEqual(unguarded, [])


if __name__ == "__main__":
    unittest.main()
