#!/usr/bin/env python3
"""Unit tests for the feed's owner gate (scripts/kanban_zulip_feed.py owner_question).

A blocked crew card is the coordinator's to decide: the feed pings the owner with the coordinator's own
question (an `ask_owner` crew_decision newer than the newest block), stays quiet while the coordinator still
owns the card, and fails open after DECISION_GRACE_S with no decision so a stopped coordinator never hides a block.
"""
import json
import sqlite3
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import kanban_zulip_feed as feed  # noqa: E402


class OwnerQuestionTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("create table task_events (id integer primary key, task_id text, run_id integer, "
                          "kind text, payload text, created_at integer)")
        self.now = 10_000

    def ev(self, kind, payload=None, at=None):
        self.conn.execute("insert into task_events (task_id, kind, payload, created_at) values ('t', ?, ?, ?)",
                          (kind, json.dumps(payload or {}), self.now if at is None else at))

    def ask(self):
        return feed.owner_question(self.conn, "t", self.now)

    def test_a_fresh_block_with_no_decision_is_the_coordinators_for_now(self):
        self.ev("blocked", at=self.now - 30)
        self.assertEqual((False, ""), self.ask())

    def test_the_coordinators_question_is_the_alert(self):
        self.ev("blocked", at=self.now - 30)
        self.ev("crew_decision", {"decision": "ask_owner", "question": "Which branch?"})
        self.assertEqual((True, "Which branch?"), self.ask())

    def test_a_retry_decision_is_no_alert(self):
        self.ev("blocked", at=self.now - 30)
        self.ev("crew_decision", {"decision": "retry", "fix": "x"})
        self.assertEqual((False, ""), self.ask())

    def test_a_block_after_the_question_is_a_new_block_for_the_coordinator(self):
        self.ev("crew_decision", {"decision": "ask_owner", "question": "old?"})
        self.ev("blocked", at=self.now - 30)
        self.assertEqual((False, ""), self.ask())

    def test_no_decision_within_the_grace_window_fails_open(self):
        self.ev("blocked", at=self.now - feed.DECISION_GRACE_S - 1)
        self.assertEqual((True, ""), self.ask())

    def test_a_card_with_no_block_event_at_all_still_alerts(self):
        self.assertEqual((True, ""), self.ask())

    def test_the_question_replaces_the_reason_in_the_alert_text(self):
        self.conn.execute("create table tasks (id text, title text, assignee text, last_failure_error text)")
        self.conn.execute("insert into tasks values ('t', 'a card', 'crew-worker', 'boom')")
        self.ev("blocked", {"reason": "the worker's reason"})
        task = self.conn.execute("select * from tasks").fetchone()
        text = feed._ending_text(self.conn, task, "blocked", question="Which branch?")
        self.assertIn("Why: Which branch?", text)
        self.assertNotIn("worker's reason", text)
        self.assertIn("the worker's reason", feed._ending_text(self.conn, task, "blocked"))


class DecisionRenderTests(unittest.TestCase):
    """A `crew_decision` event reads as its decision and its one line of substance, in the feed and the graph."""

    def test_the_feed_quotes_the_fix_the_question_or_nothing(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row

        def line(payload):
            return feed.render_event(conn, {"kind": "crew_decision", "payload": json.dumps(payload),
                                            "created_at": 1790000000, "task_id": "t"})[1]

        self.assertIn("retry: use tmp", line({"decision": "retry", "fix": "use tmp", "for_event": 3}))
        self.assertIn("ask_owner: Which branch?", line({"decision": "ask_owner", "question": "Which branch?"}))
        self.assertTrue(line({"decision": "verify"}).endswith("- verify"))

    def test_one_reader_orders_fix_question_why_problem(self):
        import crew_card
        self.assertEqual("f", crew_card.decision_detail({"fix": "f", "question": "q", "why": "w"}))
        self.assertEqual("q", crew_card.decision_detail({"question": "q", "why": "w"}))
        self.assertEqual("p", crew_card.decision_detail({"problem": "p"}))
        self.assertEqual("", crew_card.decision_detail({"decision": "verify"}))
        self.assertEqual("", crew_card.decision_detail(None))
        self.assertEqual("x" * 10, crew_card.decision_detail({"fix": "x" * 50}, 10))


if __name__ == "__main__":
    unittest.main()
