#!/usr/bin/env python3
"""scripts/crew_watch.py on a real kernel board (tests/kernel_board.py): the in-session watcher exits only when
crew_notify's own decision has something for the card, tells the session, and records it so crew_notify stays silent.
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
import crew_watch as W  # noqa: E402

PROOF = "python3 /x/site/.crew/verify.py"


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-watch-unit-")
        self._env = mock.patch.dict(os.environ, {"HERMES_HOME": os.path.join(self.tmp, "home"),
                                                 "CREW_OWNER_PROFILE": "owner", "CREW_CARD_BASE": "http://dash"})
        self._env.start()
        self.addCleanup(self._env.stop)
        self.kb, self.conn, self.db = K.open_board(self.tmp)
        self.addCleanup(self.conn.close)
        self.state = os.path.join(self.tmp, "notify-state.json")

    def card(self, proof=PROOF, status="ready", parents=()):
        cid = K.add_card(self.conn, status=status, parents=parents, title="landing page",
                         body=K.BODY + "Lands at: /x/site\n")
        crew_card._append_card_event(cid, "origin", {"origin": "", "session": "s", "proof_cmd": proof}, db=self.db)
        return cid

    def finish(self, cid, summary="shipped"):
        self.assertTrue(self.kb.complete_task(self.conn, cid, summary=summary, force=True))
        return self.conn.execute("select max(id) from task_events where task_id=? and kind='completed'",
                                 (cid,)).fetchone()[0]

    def decide(self, cid, **payload):
        crew_card._append_card_event(cid, "crew_decision", payload, db=self.db)

    def check(self, cid, now=None):
        return W.check(self.db, cid, self.state, now or time.time())

    def test_done_waits_for_the_audit_then_reports_with_summary_and_marks_state(self):
        cid = self.card()
        ev = self.finish(cid, "built the page")
        self.assertIsNone(self.check(cid))                       # audited card, audit not written yet
        self.decide(cid, decision="audit", outcome="pass", why="again", for_event=ev)
        text, marks = self.check(cid)
        self.assertIn("done · %s" % cid, text)
        self.assertIn("built the page", text)
        self.assertIn("Lands at: /x/site", text)
        self.assertIn("Proof: passed", text)
        self.assertEqual([(cid, "done:%d" % ev)], marks)
        sent = []
        out = W.watch(self.db, cid, self.state, poll=0, sleep=lambda s: None)
        self.assertIn("done · %s" % cid, out)
        self.assertEqual(["done:%d" % ev], N.sent_keys(self.state, cid))
        # crew_notify sends nothing for what the watcher told (the card has an origin chat here)
        crew_card._append_card_event(cid, "origin", {"origin": "zulip:stream:K|t", "session": "s"}, db=self.db)
        N.run(self.db, self.state, send=lambda t, x: sent.append(x) or (True, "ok"), say=lambda *_: None)
        self.assertEqual([], sent)

    def test_audit_fail_followup_pass_is_one_combined_report(self):
        cid = self.card()
        ev = self.finish(cid, "first try")
        fu = self.card(parents=(cid,))
        self.decide(cid, decision="audit", outcome="fail", followup=fu, why="rc 1", for_event=ev)
        self.assertIsNone(self.check(cid))                       # waiting on the follow-up, not reporting the done
        ev2 = self.finish(fu, "redone, stdlib only")
        self.assertIsNone(self.check(cid))                       # follow-up's own audit not settled yet
        self.decide(fu, decision="audit", outcome="pass", why="ok", for_event=ev2)
        crew_card.record_script_hashes(fu, {"/x/site/.crew/verify.py": "ab"}, by="coordinator", why="needed stdlib")
        text, marks = self.check(cid)
        self.assertIn("done · %s · landing page" % fu, text.split("\n")[0])      # the title is the original card's
        self.assertIn("redone, stdlib only", text)
        self.assertIn("Proof: the audit of %s failed; %s redid it, audit passed" % (cid, fu), text)
        self.assertIn("proof script revised by the coordinator: needed stdlib", text)
        self.assertEqual([(fu, "done:%d" % ev2)], marks)

    def report(self, cid):
        import sqlite3
        conn = sqlite3.connect("file:%s?mode=ro" % self.db, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            return W.done_report(conn, self.db, cid, time.time())
        finally:
            conn.close()

    def test_done_report_is_the_sent_text_minus_header_and_link_and_follows_a_failed_audit(self):
        cid = self.card()
        self.assertEqual("", self.report(cid))                   # not done: no report
        ev = self.finish(cid, "first try")
        fu = self.card(parents=(cid,))
        self.decide(cid, decision="audit", outcome="fail", followup=fu, why="rc 1", for_event=ev)
        ev2 = self.finish(fu, "redone, stdlib only")
        self.decide(fu, decision="audit", outcome="pass", why="again", for_event=ev2)
        sent = self.check(cid)[0]
        report = self.report(cid)
        self.assertIn("redone, stdlib only", report)             # anchor: the follow-up's summary, not the first try's
        self.assertNotIn("first try", report)
        self.assertIn("Lands at: /x/site", report)
        self.assertIn("redid it", report)
        self.assertNotIn("Card: ", report)
        self.assertNotIn("done · ", report)
        for line in report.splitlines():                         # every report line is in the message the owner gets
            self.assertIn(line, sent)

    def test_a_new_owner_question_exits_with_the_question_and_how_to_answer(self):
        cid = self.card(status="blocked")
        self.assertIsNone(self.check(cid, now=time.time()))      # the coordinator still owns it
        self.decide(cid, decision="ask_owner", question="Which palette?")
        text, marks = self.check(cid)
        self.assertIn("needs you · %s" % cid, text)
        self.assertIn("Which palette?", text)
        self.assertIn("/crew-unstuck %s" % cid, text)
        W.watch(self.db, cid, self.state, poll=0, sleep=lambda s: None)
        # the same question is not reported twice; a new one is
        self.assertEqual(1, len(N.sent_keys(self.state, cid)))
        self.decide(cid, decision="ask_owner", question="And the font?")
        self.assertIn("And the font?", self.check(cid)[0])

    def test_a_running_card_is_waited_for_and_the_lifetime_cap_ends_the_wait(self):
        cid = self.card()
        clock = [1000.0]
        text = W.watch(self.db, cid, self.state, poll=15, lifetime=3600,
                       sleep=lambda s: clock.__setitem__(0, clock[0] + s), now=lambda: clock[0])
        self.assertIn("still running", text)
        self.assertIn("/crew-status", text)
        self.assertEqual([], N.sent_keys(self.state, cid))

    def test_a_stopped_card_and_a_missing_card_are_one_line(self):
        cid = self.card()
        self.kb.archive_task(self.conn, cid)
        self.assertIn("was stopped", self.check(cid)[0])
        self.assertIn("not on the board", self.check("t_nope")[0])

    def test_an_abandoned_card_reports_once(self):
        cid = self.card()
        self.decide(cid, decision="abandon", why="owner said scrap it")
        self.kb.archive_task(self.conn, cid)
        text, _ = self.check(cid)
        self.assertIn("abandoned · %s" % cid, text)
        W.watch(self.db, cid, self.state, poll=0, sleep=lambda s: None)
        self.assertIn("already reported", self.check(cid)[0])

    def test_a_done_card_crew_notify_already_sent_is_not_told_again(self):
        cid = self.card(proof="")
        ev = self.finish(cid)
        N.mark_sent(self.state, cid, "done:%d" % ev)
        self.assertIn("already reported", self.check(cid)[0])

    def test_the_verb_is_wired_through_crew_card(self):
        cid = self.card(proof="")
        self.finish(cid, "all done")
        os.environ["HERMES_KANBAN_DB"] = self.db
        import subprocess
        out = subprocess.run([sys.executable, str(REPO / "scripts" / "crew_card.py"), "watch", "--card", cid,
                              "--poll", "1", "--lifetime", "5"], capture_output=True, text=True, timeout=60,
                             env=dict(os.environ))
        self.assertEqual(0, out.returncode, out.stderr)
        self.assertIn("done · %s" % cid, out.stdout)


if __name__ == "__main__":
    unittest.main()
