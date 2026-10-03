#!/usr/bin/env python3
"""A verifier's block on an independent card is not a proof's to lift (t_3f619c1d, 2026-10-03).

The sequence, replayed on a board made by the kernel's own code: the verifier blocks an independent card on a
quality judgement (fabricated citations); the proof script, structural only, passes. The heal pass must leave the
card blocked, and the coordinator's decision path gets the verifier's reason and sends the fix to the WRITER.
A block that was not the verifier's (stale proof) still heals.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

_TMP = tempfile.mkdtemp(prefix="crew-verifier-block-")
os.environ["HERMES_HOME"] = os.path.join(_TMP, "home")
os.environ["HERMES_BIN"] = "/bin/false"
os.environ["KANBAN_DB"] = os.path.join(_TMP, "x.db")

import crew_card  # noqa: E402
import crew_coordinator as cc  # noqa: E402
import crew_heal  # noqa: E402
import kernel_board as K  # noqa: E402

BODY = ("Role: content\nCoordinator: owner/s\nBudget: 200000 tokens\nVerify: independent\n\nGOAL: g\nDone when: d\n\n"
        "proof command: true\n")
REASON = "Citations are mismatched: PMC7143747 is a stored-product-insects paper, not Topol."


class VerifierBlockTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(dir=_TMP)
        self.kb, self.conn, self.db = K.open_board(self.dir)
        self.addCleanup(self.conn.close)
        self.cli = K.kernel_cli(self.db)
        for p in (mock.patch.object(crew_card.subprocess, "run", self.cli),
                  mock.patch.object(crew_card, "profile_exists", return_value=True),
                  mock.patch.object(crew_card, "close_proof_command", return_value="true"),
                  mock.patch.object(crew_heal, "KANBAN_DB", self.db),
                  mock.patch.object(cc, "kanban", side_effect=self.kanban),
                  mock.patch.object(crew_heal.crew_safety, "run_proof",
                                    return_value=SimpleNamespace(rc=0, out="11/11 PASS", blocked="")),
                  mock.patch.object(crew_heal.crew_safety, "proof_mode", return_value="plain")):
            p.start()
            self.addCleanup(p.stop)

    def kanban(self, *args):
        self.asked = getattr(self, "asked", []) + [args]
        return 0, "ok"

    def blocked_card(self, by_verifier=True, body=BODY):
        """The real sequence: writer run -> review_requested -> verifier run -> blocked (needs_input)."""
        kb, conn = self.kb, self.conn
        cid = K.add_card(conn, "ready", body=body, assignee="crew-content")
        if by_verifier:
            self.assertIsNotNone(kb.claim_task(conn, cid, claimer="w"))
            self.assertTrue(kb.request_review(conn, cid, summary="done", reviewer="crew-verifier"))
            self.assertIsNotNone(kb.claim_review_task(conn, cid, claimer="v"))
        else:
            self.assertIsNotNone(kb.claim_task(conn, cid, claimer="w"))
        self.assertTrue(kb.block_task(conn, cid, reason=REASON, kind="needs_input"))
        return cid

    def test_the_verifiers_block_is_recognised_with_its_reason(self):
        cid = self.blocked_card()
        got = crew_card.verifier_block(cid)
        self.assertEqual(REASON, got["reason"])

    def test_a_writers_block_is_not_the_verifiers(self):
        self.assertIsNone(crew_card.verifier_block(self.blocked_card(by_verifier=False)))

    def test_heal_leaves_a_verifier_blocked_card_blocked_although_the_proof_passes(self):
        cid = self.blocked_card()
        card = {"id": cid, "status": "blocked", "body": BODY}
        self.assertIsNone(crew_heal.heal_card(card, False))
        crew_heal.crew_safety.run_proof.assert_not_called()
        self.assertEqual("blocked", self.kb.get_task(self.conn, cid).status)
        self.assertNotIn("unblocked", K.events(self.conn, cid))
        self.assertNotIn("self_heal", K.events(self.conn, cid))

    def test_a_stale_block_that_is_not_the_verifiers_still_heals(self):
        cid = self.blocked_card(by_verifier=False)
        got = crew_heal.heal_card({"id": cid, "status": "blocked", "body": BODY}, False)
        self.assertEqual(("stale_verify", True), (got["class"], got["fixed"]))
        self.assertEqual("ready", self.kb.get_task(self.conn, cid).status)

    def test_a_proof_card_blocked_by_its_verifier_run_still_heals(self):
        body = BODY.replace("Verify: independent", "Verify: proof")
        cid = self.blocked_card(body=body)
        got = crew_heal.heal_card({"id": cid, "status": "blocked", "body": body}, False)
        self.assertTrue(got["fixed"])

    def pass_for(self, decider):
        cid = self.blocked_card()
        ctx = cc.Ctx(self.db, None, dry=False, decider=decider, say=lambda *_: None)
        card = cc.get_card(ctx, cid)
        ev = [dict(r) for r in self.conn.execute(
            "select id, task_id, kind, payload, created_at from task_events where task_id = ? and kind = 'blocked'",
            (cid,))]
        return cid, cc.handle_card(ctx, cid, ev), card

    def test_the_coordinator_gets_the_verifiers_reason_and_the_fix_goes_to_the_writer(self):
        seen = []

        def decider(ctx, path):
            seen.append(open(path).read())
            return '{"decision": "retry", "fix": "replace every citation with a real, checked source"}', 0

        cid, out, _ = self.pass_for(decider)
        self.assertIn(REASON, seen[0])
        self.assertIn("Verifier's findings", seen[0])
        self.assertEqual("retry", out["action"], out)
        task = self.kb.get_task(self.conn, cid)
        self.assertEqual(("ready", "crew-content"), (task.status, task.assignee))
        self.assertIn("Coordinator fix 1: replace every citation", task.body)

    def test_a_verify_answer_cannot_close_or_lift_the_card_and_the_owner_is_asked(self):
        with mock.patch.object(cc, "run_verdict", side_effect=AssertionError("the proof was run")):
            cid, out, _ = self.pass_for(lambda ctx, path: ('{"decision": "verify"}', 0))
        self.assertEqual("ask_owner", out["action"], out)
        self.assertIn(REASON[:40], self.asked[-1][2])
        self.assertEqual("blocked", self.kb.get_task(self.conn, cid).status)


if __name__ == "__main__":
    unittest.main()
