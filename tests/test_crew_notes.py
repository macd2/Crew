#!/usr/bin/env python3
"""Unit tests for the notification-bell rules in scripts/crew_graph_serve.py.

Only the pure rules are covered - what clearing a row writes down, and when a cleared row comes
back - so nothing here touches the board or the ack file. HERMES_HOME is still pointed at a
throwaway directory, because importing the module pulls in crew_graph, which reads it.
"""
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

import crew_graph_serve as serve  # noqa: E402


class NotesTestCase(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-notes-test-")
        os.environ["HERMES_HOME"] = self.home

    def tearDown(self):
        for key in [k for k in os.environ if k not in self._env]:
            del os.environ[key]
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)

    @staticmethod
    def row(cid="t_1", status="blocked", entered_ts=100):
        return {"id": cid, "status": status, "entered_ts": entered_ts,
                "ack_url": "/ack/%s" % cid}


class AckTokenTests(NotesTestCase):
    """ack_token(status, entered_ts): the value a clear writes for one row."""

    def test_a_done_row_is_cleared_for_good(self):
        # done is terminal: the timestamp is deliberately not part of the token
        self.assertEqual("done", serve.ack_token("done", 1790000000))
        self.assertEqual("done", serve.ack_token("done", None))

    def test_a_waiting_row_is_cleared_only_for_the_state_it_is_in(self):
        self.assertEqual("blocked@1790000000", serve.ack_token("blocked", 1790000000))
        self.assertEqual("triage@100", serve.ack_token("triage", 100))

    def test_a_waiting_row_with_no_state_event_still_gets_a_token(self):
        # no event on record: the row is clearable, and the token says "this state, no timestamp"
        self.assertEqual("blocked@0", serve.ack_token("blocked", None))


class RowClearedTests(NotesTestCase):
    """row_cleared(row, acks): whether the row is already cleared and nothing has moved since."""

    def test_a_row_never_cleared_is_shown(self):
        self.assertFalse(serve.row_cleared(self.row(), {}))

    def test_a_cleared_waiting_row_is_hidden(self):
        acks = {"t_1": serve.ack_token("blocked", 100)}
        self.assertTrue(serve.row_cleared(self.row(entered_ts=100), acks))

    def test_a_cleared_waiting_row_comes_back_when_the_card_moves(self):
        # the card was cleared while blocked at ts=100; it has been blocked again at ts=200
        acks = {"t_1": serve.ack_token("blocked", 100)}
        self.assertFalse(serve.row_cleared(self.row(entered_ts=200), acks))

    def test_a_cleared_done_row_stays_cleared_whatever_the_timestamp(self):
        acks = {"t_1": "done"}
        self.assertTrue(serve.row_cleared(self.row(status="done", entered_ts=100), acks))
        self.assertTrue(serve.row_cleared(self.row(status="done", entered_ts=999), acks))

    def test_a_clear_of_one_state_does_not_hide_the_card_in_another(self):
        # cleared while in triage, now blocked: that is a different state and a new notification
        acks = {"t_1": serve.ack_token("triage", 100)}
        self.assertFalse(serve.row_cleared(self.row(status="blocked", entered_ts=100), acks))

    def test_another_card_s_clear_does_not_hide_this_row(self):
        acks = {"t_2": serve.ack_token("blocked", 100)}
        self.assertFalse(serve.row_cleared(self.row(cid="t_1", entered_ts=100), acks))


class NotesTotalTests(NotesTestCase):
    """notes_total(att): the number the bell shows."""

    def test_it_is_the_list_s_own_total(self):
        self.assertEqual(7, serve.notes_total({"rows": [{}] * 7, "stuck": 2, "done": 5, "total": 7}))

    def test_it_falls_back_to_stuck_plus_done(self):
        self.assertEqual(3, serve.notes_total({"stuck": 1, "done": 2}))

    def test_an_empty_list_reads_zero(self):
        self.assertEqual(0, serve.notes_total({}))
        self.assertEqual(0, serve.notes_total(None))


class ProbeCardTests(NotesTestCase):
    """is_probe_card(title): the scaffolding rule the clear-all walk has to apply too."""

    def test_the_suite_s_own_cards_are_scaffolding(self):
        for title in ("PROBE notify done", "TEST card", "   probe card", "Probe: x"):
            self.assertTrue(serve.is_probe_card(title), title)

    def test_the_match_is_anchored_at_the_start_of_the_title(self):
        # the board's rule is a prefix match, case-insensitive: a card whose title BEGINS with the
        # word counts as scaffolding even in prose ("Probe the market for X" is hidden from the
        # lanes - the rule's own quirk, pinned here rather than quietly changed), while a mid-title
        # mention is a real card
        self.assertTrue(serve.is_probe_card("Probe the market for X"))
        self.assertFalse(serve.is_probe_card("the probe of the market"))
        for title in ("", None, "donatr.ee feasibility"):
            self.assertFalse(serve.is_probe_card(title), repr(title))


class NotifiableCardsTests(NotesTestCase):
    """notifiable_cards(db): what clear-all means by 'every notification'."""

    def board(self, rows):
        path = os.path.join(self.home, "kanban.db")
        conn = sqlite3.connect(path)
        conn.execute("create table tasks (id text, status text, title text)")
        conn.executemany("insert into tasks values (?,?,?)", rows)
        conn.commit()
        conn.close()
        return path

    def test_it_returns_every_stuck_and_every_done_card(self):
        path = self.board([("t_1", "done", "finished"), ("t_2", "blocked", "waiting"),
                           ("t_3", "triage", "triage"), ("t_4", "running", "busy"),
                           ("t_5", "archived", "old")])
        self.assertEqual([("t_1", "done"), ("t_2", "blocked"), ("t_3", "triage")],
                         sorted(serve.notifiable_cards(path)))

    def test_the_scaffolding_is_cleared_out_of_the_walk(self):
        path = self.board([("t_1", "done", "PROBE notify"), ("t_2", "done", "TEST card"),
                           ("t_3", "done", "real work")])
        self.assertEqual([("t_3", "done")], serve.notifiable_cards(path))

    def test_a_board_that_is_not_there_is_an_empty_list(self):
        self.assertEqual([], serve.notifiable_cards(os.path.join(self.home, "nope.db")))


if __name__ == "__main__":
    unittest.main()
