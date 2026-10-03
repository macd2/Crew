#!/usr/bin/env python3
"""Unit tests for scripts/crew_notify.py on a real kernel board (tests/kernel_board.py: hermes_cli makes the
schema and moves the cards); only the `hermes send` subprocess is replaced.

The owner hears about a crew card three ways and no other: it ends done, the coordinator asks him a question (or
sat on a stuck card past the grace window), or it was abandoned on his word. Each goes out once per card+event, a
failed send is retried, and everything the coordinator is handling stays silent.
"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

import kernel_board as K  # noqa: E402
import crew_card  # noqa: E402
import crew_notify as N  # noqa: E402

ORIGIN = "zulip:stream:Kanban|crew chat"


class Sender:
    """A `hermes send` stand-in that records (target, text); `fail` makes the next n calls fail."""

    def __init__(self, fail=0):
        self.calls, self.fail = [], fail

    def __call__(self, target, text):
        if self.fail:
            self.fail -= 1
            return False, "rc=1 boom"
        self.calls.append((target, text))
        return True, "rc=0 sent"


class NotifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-notify-unit-")
        self._env = mock.patch.dict(os.environ, {"HERMES_HOME": os.path.join(self.tmp, "home"),
                                                 "CREW_OWNER_PROFILE": "owner", "CREW_CARD_BASE": "http://dash"})
        self._env.start()
        self.addCleanup(self._env.stop)
        self.kb, self.conn, self.db = K.open_board(self.tmp)
        self.addCleanup(self.conn.close)
        self.state = os.path.join(self.tmp, "notify-state.json")
        N.save_state(self.state, {"since": time.time() - 3600, "sent": {}, "tries": {}})
        self.say = []

    def run_notify(self, send, **kw):
        return N.run(self.db, self.state, send=send, say=self.say.append, **kw)

    def card(self, status="ready", origin=ORIGIN, parents=()):
        cid = K.add_card(self.conn, status=status, parents=parents)
        if origin:
            crew_card._append_card_event(cid, "origin", {"origin": origin, "session": "s"}, db=self.db)
        return cid

    def done(self, origin=ORIGIN):
        cid = self.card(origin=origin)
        self.assertTrue(self.kb.complete_task(self.conn, cid, summary="shipped the thing", force=True))
        return cid

    def decide(self, cid, **payload):
        crew_card._append_card_event(cid, "crew_decision", payload, db=self.db)

    def age(self, cid, secs):
        self.conn.execute("update task_events set created_at = created_at - ? where task_id = ?", (secs, cid))
        self.conn.execute("update tasks set completed_at = completed_at - ? where id = ?", (secs, cid))
        self.conn.commit()

    # ---- done
    def test_a_done_card_reports_once_into_its_origin_and_a_restart_resends_nothing(self):
        cid = self.done()
        s = Sender()
        self.run_notify(s)
        self.assertEqual(1, len(s.calls))
        target, text = s.calls[0]
        self.assertEqual(ORIGIN, target)
        self.assertIn("done · %s" % cid, text)
        self.assertIn("shipped the thing", text)
        self.assertIn("Card: http://dash/card/%s" % cid, text)
        self.run_notify(s)                                  # the next tick
        self.run_notify(s)                                  # a restart reads the same state file
        self.assertEqual(1, len(s.calls))

    def test_the_first_run_baselines_old_endings_and_only_new_ones_go_out(self):
        old = self.done()
        self.age(old, 7200)
        os.unlink(self.state)
        s = Sender()
        self.assertEqual([], self.run_notify(s, now=time.time() - 30))   # baseline: records `since`, sends nothing
        self.assertEqual([], self.run_notify(s))
        self.assertEqual([], s.calls)
        new = self.done()
        self.run_notify(s)
        self.assertEqual([new], [c for c in (self.cards_in(s))])

    def cards_in(self, s):
        return [t.split(" · ")[1] for _target, t in s.calls]

    def test_a_done_card_with_no_origin_stays_silent_and_is_not_retried(self):
        self.done(origin="")
        s = Sender()
        self.run_notify(s)
        self.run_notify(s)
        self.assertEqual([], s.calls)
        self.assertTrue(any("no chat to report into" in m for m in self.say))

    def test_a_child_with_no_origin_of_its_own_reports_into_its_parents_chat(self):
        parent = self.card()
        self.assertTrue(self.kb.complete_task(self.conn, parent, summary="parent done", force=True))
        child = self.card(origin="", parents=(parent,))
        self.assertTrue(self.kb.complete_task(self.conn, child, summary="child done", force=True))
        s = Sender()
        self.run_notify(s)
        self.assertEqual([(ORIGIN, parent), (ORIGIN, child)], [(t, x.split(" · ")[1]) for t, x in s.calls])
        self.assertIn("From card: %s" % parent, s.calls[1][1])

    def test_a_card_of_another_coordinator_is_not_ours_to_report(self):
        cid = K.add_card(self.conn, status="ready", body=K.BODY.replace("owner/s", "someone/s"))
        crew_card._append_card_event(cid, "origin", {"origin": ORIGIN}, db=self.db)
        self.kb.complete_task(self.conn, cid, summary="x", force=True)
        s = Sender()
        self.run_notify(s)
        self.assertEqual([], s.calls)

    # ---- needs you
    def test_a_block_the_coordinator_still_owns_is_silent(self):
        cid = self.card(status="blocked")
        s = Sender()
        self.run_notify(s)                                  # fresh block, no decision yet
        self.decide(cid, decision="retry", fix="use tmp")
        self.decide(cid, decision="rescope", goal="g")
        self.decide(cid, decision="verify")
        self.run_notify(s)
        self.assertEqual([], s.calls)

    def test_each_new_owner_question_is_one_message_and_the_same_one_is_never_resent(self):
        cid = self.card(status="blocked")
        self.decide(cid, decision="ask_owner", question="Which branch?")
        s = Sender()
        self.run_notify(s)
        self.run_notify(s)
        self.assertEqual(1, len(s.calls))
        self.assertEqual(ORIGIN, s.calls[0][0])
        self.assertIn("needs you · %s" % cid, s.calls[0][1])
        self.assertIn("Which branch?", s.calls[0][1])
        self.decide(cid, decision="ask_owner", question="And which tag?")      # a new question: a new message
        self.run_notify(s)
        self.run_notify(s)
        self.assertEqual(2, len(s.calls))
        self.assertIn("And which tag?", s.calls[1][1])

    def test_a_block_after_the_question_goes_back_to_the_coordinator(self):
        cid = self.card(status="blocked")
        self.decide(cid, decision="ask_owner", question="old?")
        self.conn.execute("insert into task_events (task_id, kind, payload, created_at) values (?, 'blocked', '{}', ?)",
                          (cid, int(time.time())))
        self.conn.commit()
        s = Sender()
        self.run_notify(s)
        self.assertEqual([], s.calls)

    def test_no_decision_within_the_grace_window_goes_out_with_the_block_reason(self):
        cid = self.card(status="blocked")
        s = Sender()
        conn = N.sqlite3.connect(self.db)
        conn.row_factory = N.sqlite3.Row
        self.assertEqual((False, ""), N.owner_question(conn, cid, time.time())[:2])
        alert, question, key = N.owner_question(conn, cid, time.time() + N.DECISION_GRACE_S + 5)
        conn.close()
        self.assertEqual((True, ""), (alert, question))
        self.assertTrue(key.startswith("block:"))
        self.run_notify(s, now=time.time() + N.DECISION_GRACE_S + 5)
        self.assertEqual(1, len(s.calls))
        self.assertIn("stuck", s.calls[0][1])               # the kernel's block reason

    def test_a_question_on_a_card_with_no_origin_goes_to_the_home_channel_of_the_owners_last_platform(self):
        self.card(origin="telegram:-1001:7")                # the owner's newest chat origin on the board
        cid = self.card(status="blocked", origin="")
        self.decide(cid, decision="ask_owner", question="Which?")
        s = Sender()
        self.run_notify(s)
        self.assertEqual([("telegram", cid)], [(t, x.split(" · ")[1]) for t, x in s.calls])

    def test_a_question_with_no_chat_anywhere_is_logged_and_marked_not_retried_forever(self):
        cid = self.card(status="blocked", origin="")
        self.decide(cid, decision="ask_owner", question="Which?")
        s = Sender()
        self.run_notify(s)
        self.run_notify(s)
        self.assertEqual([], s.calls)
        self.assertFalse(N.has_pending(self.state))
        self.assertEqual(1, sum("no chat to report into" in m for m in self.say))

    # ---- abandoned
    def test_an_abandoned_card_is_one_line(self):
        cid = self.card()
        self.decide(cid, decision="abandon", why="owner said scrap it")
        self.kb.archive_task(self.conn, cid)
        s = Sender()
        self.run_notify(s)
        self.run_notify(s)
        self.assertEqual(1, len(s.calls))
        self.assertEqual(ORIGIN, s.calls[0][0])
        self.assertEqual(1, len(s.calls[0][1].strip().splitlines()) - 1)        # one line plus the card link
        self.assertIn("abandoned · %s" % cid, s.calls[0][1])

    def test_an_archive_that_was_not_an_abandon_decision_is_silent(self):
        cid = self.card()
        self.kb.archive_task(self.conn, cid)
        s = Sender()
        self.run_notify(s)
        self.assertEqual([], s.calls)

    # ---- failure
    def test_a_failed_send_is_not_marked_and_retries_on_the_next_pass(self):
        self.done()
        s = Sender(fail=1)
        self.run_notify(s)
        self.assertEqual([], s.calls)
        self.assertTrue(N.has_pending(self.state))          # the coordinator tick starts a pass for the retry
        self.run_notify(s)
        self.assertEqual(1, len(s.calls))
        self.assertFalse(N.has_pending(self.state))
        self.run_notify(s)
        self.assertEqual(1, len(s.calls))

    def test_a_target_that_never_works_is_given_up_after_max_tries(self):
        self.done()
        s = Sender(fail=10 ** 6)
        for _ in range(N.MAX_TRIES + 2):
            self.run_notify(s)
        self.assertFalse(N.has_pending(self.state))
        self.assertTrue(any("giving up" in m for m in self.say))

    def test_a_dry_run_prints_target_and_text_and_records_nothing(self):
        self.done()
        before = open(self.state).read()
        out = []
        N.run(self.db, self.state, dry_run=True, say=out.append,
              send=lambda *_: self.fail("dry run must not send"))
        self.assertIn("--- %s" % ORIGIN, out[0])
        self.assertEqual(before, open(self.state).read())

    # ---- the sender
    def test_hermes_send_calls_the_public_sender_for_the_owner_profile_with_the_text_on_stdin(self):
        with mock.patch.object(N.subprocess, "run") as run:
            run.return_value = mock.Mock(returncode=0, stdout="sent", stderr="")
            ok, _ = N.hermes_send(ORIGIN, "hello")
        argv = run.call_args[0][0]
        self.assertTrue(ok)
        self.assertEqual(["-p", "owner", "send", "-t", ORIGIN, "--file", "-"], argv[1:])
        self.assertEqual("hello", run.call_args[1]["input"])


if __name__ == "__main__":
    unittest.main()
