#!/usr/bin/env python3
"""Unit tests for the pure logic in scripts/crew_diagnose.py.

human_age, block_event and cards_from_rows touch no board: cards_from_rows takes the row tuples the
reader reads, so the reason's fallback chain and the wait are pinned here directly. The budget read
inside it goes through crew_card.ledger_spent(), so HERMES_HOME points at a throwaway directory and
nothing can drift into the live profile. main() is exercised against a board of its own through
HERMES_KANBAN_DB.
"""
import contextlib
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
os.environ.setdefault("HERMES_BIN", "/bin/false")   # a unit test never starts the real `hermes` (scratch HERMES_HOME bootstraps a runtime and rewrites the live launcher)

import crew_diagnose  # noqa: E402

FIELDS = ("id", "title", "state", "assignee", "kind", "created_at", "result", "failure", "failures",
          "summary", "error", "runs", "payload", "blocked_at", "decision")


def row(**kw):
    """One row as board_rows() returns it, defaulted so a test names only what it means."""
    base = {"id": "t_x", "title": "a card", "state": "blocked", "assignee": "crew-worker",
            "kind": "needs_input", "created_at": 1000, "result": None, "failure": None,
            "failures": 0, "summary": None, "error": None, "runs": 1, "payload": None,
            "blocked_at": 1000, "decision": None}
    base.update(kw)
    return tuple(base[f] for f in FIELDS)


class DiagnoseTestCase(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-diagnose-test-")
        os.environ["HERMES_HOME"] = self.home

    def tearDown(self):
        for key in [k for k in os.environ if k not in self._env]:
            del os.environ[key]
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)


class HumanAgeTests(DiagnoseTestCase):
    def test_no_timestamp_is_empty(self):
        self.assertEqual("", crew_diagnose.human_age(0))
        self.assertEqual("", crew_diagnose.human_age(None))
        self.assertEqual("", crew_diagnose.human_age(-5))

    def test_minutes_hours_and_days(self):
        self.assertEqual("45m", crew_diagnose.human_age(45 * 60))
        self.assertEqual("6h", crew_diagnose.human_age(6 * 3600))
        self.assertEqual("3d 4h", crew_diagnose.human_age(3 * 86400 + 4 * 3600))


class BlockEventTests(DiagnoseTestCase):
    def test_it_reads_the_reason_and_kind_written_at_block_time(self):
        payload = json.dumps({"reason": "waiting on the token", "kind": "needs_input"})
        self.assertEqual(("waiting on the token", "needs_input"), crew_diagnose.block_event(payload))

    def test_a_payload_that_is_not_json_gives_nothing(self):
        self.assertEqual(("", ""), crew_diagnose.block_event("not json at all"))
        self.assertEqual(("", ""), crew_diagnose.block_event(None))
        self.assertEqual(("", ""), crew_diagnose.block_event("[1, 2]"))


class CardsFromRowsTests(DiagnoseTestCase):
    def test_the_last_run_summary_is_the_reason(self):
        cards = crew_diagnose.cards_from_rows([row(summary="the proof failed on the publish step")], now=1000)
        self.assertEqual("the proof failed on the publish step", cards[0]["reason"])

    def test_the_run_error_is_the_reason_when_there_is_no_summary(self):
        cards = crew_diagnose.cards_from_rows([row(error="pid 12 exited rate-limited")], now=1000)
        self.assertEqual("pid 12 exited rate-limited", cards[0]["reason"])

    def test_the_block_event_reason_carries_when_the_run_recorded_none(self):
        payload = json.dumps({"reason": "waiting on the owner's decision", "kind": "needs_input"})
        cards = crew_diagnose.cards_from_rows([row(kind=None, payload=payload)], now=1000)
        self.assertEqual("waiting on the owner's decision", cards[0]["reason"])
        self.assertEqual("needs_input", cards[0]["kind"])

    def test_no_reason_anywhere_says_so_rather_than_inventing_one(self):
        cards = crew_diagnose.cards_from_rows([row()], now=1000)
        self.assertEqual("no reason recorded on the board", cards[0]["reason"])

    def test_the_wait_is_read_from_the_block_event(self):
        cards = crew_diagnose.cards_from_rows([row(created_at=0, blocked_at=1000)], now=1000 + 5 * 3600)
        self.assertEqual("5h", cards[0]["wait"])

    def test_without_a_block_event_the_wait_falls_back_to_creation(self):
        cards = crew_diagnose.cards_from_rows([row(created_at=1000, blocked_at=None)], now=1000 + 90)
        self.assertEqual("1m", cards[0]["wait"])

    def test_a_long_reason_is_cut_and_marked(self):
        cards = crew_diagnose.cards_from_rows([row(summary="x" * 900)], now=1000)
        self.assertEqual(crew_diagnose.REASON_CHARS + 4, len(cards[0]["reason"]))
        self.assertTrue(cards[0]["reason"].endswith(" ..."))

    def test_the_failure_count_and_the_run_count_are_reported(self):
        cards = crew_diagnose.cards_from_rows([row(failures=2, runs=7)], now=1000)
        self.assertEqual(2, cards[0]["failures"])
        self.assertEqual(7, cards[0]["runs"])


class MainTests(DiagnoseTestCase):
    """main() against a board of its own: the live board is never read or written here."""

    def board(self):
        path = os.path.join(self.home, "kanban.db")
        conn = sqlite3.connect(path)
        conn.executescript("""
            create table tasks (id text, title text, status text, assignee text, block_kind text,
                                created_at integer, result text, last_failure_error text,
                                consecutive_failures integer);
            create table task_runs (id integer, task_id text, summary text, error text);
            create table task_events (id integer, task_id text, kind text, payload text,
                                      created_at integer);
        """)
        conn.execute("insert into tasks values ('t_seed01', 'publish the branch', 'blocked',"
                     " 'crew-worker', 'needs_input', 1000, null, null, 0)")
        conn.execute("insert into task_runs values (1, 't_seed01', 'the publish token is missing', null)")
        conn.commit()
        conn.close()
        os.environ["HERMES_KANBAN_DB"] = path
        return path

    def run_main(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = crew_diagnose.main(argv)
        return code, out.getvalue()

    def test_it_lists_the_card_with_its_id_and_reason(self):
        self.board()
        code, text = self.run_main([])
        self.assertEqual(0, code)
        self.assertIn("t_seed01", text)
        self.assertIn("the publish token is missing", text)
        self.assertTrue(text.startswith("diagnose: 1 card(s) in state blocked"))

    def test_json_is_the_same_result_as_data(self):
        self.board()
        code, text = self.run_main(["--json"])
        self.assertEqual(0, code)
        data = json.loads(text)
        self.assertEqual(1, data["count"])
        self.assertEqual("t_seed01", data["cards"][0]["id"])

    def test_one_card_can_be_asked_for_by_id(self):
        self.board()
        code, text = self.run_main(["--card", "t_seed01"])
        self.assertEqual(0, code)
        self.assertIn("card t_seed01", text)

    def test_an_unknown_state_is_refused_with_the_list(self):
        self.board()
        code, text = self.run_main(["--state", "nope"])
        self.assertEqual(1, code)
        self.assertIn("unknown state", text)
        self.assertIn("blocked", text)

    def test_a_missing_board_is_reported_as_such(self):
        os.environ["HERMES_KANBAN_DB"] = os.path.join(self.home, "nothing-here.db")
        os.environ.pop("KANBAN_DB", None)
        code, text = self.run_main([])
        self.assertEqual(2, code)
        self.assertIn("no board to read", text)


class DecisionTextTests(DiagnoseTestCase):
    """The coordinator's last decision, as one line under the card."""

    def test_the_decision_and_its_detail_read_as_one_line(self):
        self.assertEqual("retry: use tmp", crew_diagnose.decision_text(json.dumps({"decision": "retry", "fix": "use  tmp"})))
        self.assertEqual("ask_owner: Which branch?", crew_diagnose.decision_text(
            json.dumps({"decision": "ask_owner", "question": "Which branch?"})))
        self.assertEqual("verify", crew_diagnose.decision_text(json.dumps({"decision": "verify"})))

    def test_no_decision_is_empty(self):
        for payload in (None, "", "{}", "not json", json.dumps(["x"])):
            self.assertEqual("", crew_diagnose.decision_text(payload))

    def test_a_card_carries_it_and_the_render_shows_it(self):
        cards = crew_diagnose.cards_from_rows([row(decision=json.dumps({"decision": "retry", "fix": "x"}))])
        self.assertEqual("retry: x", cards[0]["decision"])
        self.assertIn("coordinator: retry: x", crew_diagnose.render(cards, "blocked", None))
        self.assertNotIn("coordinator:", crew_diagnose.render(crew_diagnose.cards_from_rows([row()]), "blocked", None))


if __name__ == "__main__":
    unittest.main()
