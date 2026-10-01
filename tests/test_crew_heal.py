#!/usr/bin/env python3
"""Unit tests for the pure logic in scripts/crew_heal.py.

crew_heal reads KANBAN_DB from the environment at import time, so this module points it at a
throwaway path BEFORE importing it - the live board is never opened, and a test asserts that the
bound value is not the live board.
"""
import os
import sqlite3
import sys
import tempfile
import unittest
import inspect
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

_TMPDIR = tempfile.mkdtemp(prefix="crew-heal-test-")
SAFE_DB = os.path.join(_TMPDIR, "not-the-live-board.db")
os.environ["KANBAN_DB"] = SAFE_DB

import crew_card  # noqa: E402
import crew_heal  # noqa: E402

LIVE_BOARD = os.path.join(os.path.expanduser("~"), ".hermes", "kanban.db")


class NoLiveBoardTests(unittest.TestCase):
    def test_the_module_was_imported_against_a_throwaway_db(self):
        # the invariant is "never the live board", not "exactly this temp path": whichever test
        # module imports it first does the binding, and KANBAN_DB is read at import time.
        self.assertNotEqual(os.path.realpath(LIVE_BOARD), os.path.realpath(crew_heal.KANBAN_DB))
        self.assertFalse(os.path.exists(crew_heal.KANBAN_DB))


class IsBlockerTests(unittest.TestCase):
    """is_blocker(text): a held card is only healable when its error reads as a blocker."""

    def test_every_word_on_the_blocker_list_matches(self):
        for text in ("quota exceeded", "rate limit hit", "HTTP 429", "403 Forbidden",
                     "auth error", "forbidden", "Access denied", "permission denied",
                     "invalid api key", "billing problem", "subscription lapsed"):
            with self.subTest(text=text):
                self.assertTrue(crew_heal.is_blocker(text))

    def test_ordinary_text_is_not_a_blocker(self):
        self.assertFalse(crew_heal.is_blocker("the tests fail on line 3"))
        self.assertFalse(crew_heal.is_blocker("waiting for the owner to choose a name"))

    def test_empty_and_none_are_not_blockers(self):
        self.assertFalse(crew_heal.is_blocker(""))
        self.assertFalse(crew_heal.is_blocker(None))

    def test_matching_is_case_insensitive(self):
        self.assertTrue(crew_heal.is_blocker("Quota Exceeded"))
        self.assertTrue(crew_heal.is_blocker("AUTH"))

    def test_a_substring_inside_a_normal_word_is_not_a_blocker(self):
        # word-start matching: a run error that merely contains these letters is NOT a blocker.
        # Getting this wrong routes a healthy held card to the dead-model heal.
        self.assertFalse(crew_heal.is_blocker("the file is moderate in size"))
        self.assertFalse(crew_heal.is_blocker("the numbers look accurate"))
        self.assertFalse(crew_heal.is_blocker("corporate plan"))
        self.assertFalse(crew_heal.is_blocker("written by the author"))

    def test_real_blockers_still_match(self):
        for text in ("quota exceeded", "rate-limited (quota wall)", "HTTP 429 too many requests",
                     "403 forbidden", "authentication failed", "AUTH", "invalid api key",
                     "permission denied: /home/x", "billing problem"):
            with self.subTest(text=text):
                self.assertTrue(crew_heal.is_blocker(text), text)


class ProofCmdTests(unittest.TestCase):
    """proof_cmd(body): the command the stale-block remedy re-runs."""

    def test_it_reads_the_proof_command_line(self):
        self.assertEqual("pytest -q tests", crew_heal.proof_cmd("Role: worker\nproof command: pytest -q tests\n"))

    def test_it_is_case_insensitive_and_tolerates_extra_spacing(self):
        self.assertEqual("pytest -q", crew_heal.proof_cmd("Proof Command:    pytest -q\n"))

    def test_a_bodiless_or_valueless_line_returns_an_empty_string(self):
        self.assertEqual("", crew_heal.proof_cmd("Role: worker\nDone when: green\n"))
        self.assertEqual("", crew_heal.proof_cmd("proof command:\n"))
        self.assertEqual("", crew_heal.proof_cmd("proof command:   \n"))
        self.assertEqual("", crew_heal.proof_cmd(""))
        self.assertEqual("", crew_heal.proof_cmd(None))

    def test_the_no_proof_placeholder_is_not_a_command(self):
        # render_body() writes "proof command: (none - ...)" for a card opened with no proof. That
        # is a note, not a command: handing it to a shell gives rc=2 and the card is reported as
        # "still failing" instead of being escalated. crew_card owns the rule; both readers use it.
        body = crew_card.render_body({"role": "worker", "budget": 1000000, "goal": "g",
                                      "done_when": "d", "proof_cmd": ""})
        self.assertIn("(none - the verifier asks for one before accepting)", body)
        self.assertEqual("", crew_heal.proof_cmd(body))
        self.assertEqual("", crew_card.proof_cmd(body))

    def test_a_real_command_after_the_placeholder_line_is_still_read(self):
        # only the placeholder text is dropped, never a real command on another line
        body = "proof command: (none - the verifier asks for one before accepting)\nRole: worker\n"
        self.assertEqual("", crew_heal.proof_cmd(body))
        self.assertEqual("sh -c 'exit 0'",
                         crew_heal.proof_cmd("Role: worker\nproof command: sh -c 'exit 0'\n"))

    def test_it_reads_the_first_proof_line_only(self):
        self.assertEqual("first", crew_heal.proof_cmd("proof command: first\nproof command: second\n"))


def heal_with_extra(card, dry, healed):
    """The shape that caused the outage: a heal helper demanding a third argument."""
    return {"card": card.get("id")}


class SafelyBindingTests(unittest.TestCase):
    """safely(fn, card, dry) binds exactly two arguments - the regression that shipped once.

    crew_heal declared escalate_once(card, dry, healed) while its own wrapper called fn(card, dry):
    every card hit a TypeError, was never healed, and the pass reported "could not heal" forever.
    """

    HELPERS = ("heal_held_workspace", "heal_dead_model", "heal_stale_verify")

    def test_every_heal_helper_takes_exactly_card_and_dry(self):
        for name in self.HELPERS:
            with self.subTest(helper=name):
                params = list(inspect.signature(getattr(crew_heal, name)).parameters)
                self.assertEqual(["card", "dry"], params)

    def test_every_helper_named_as_a_safely_callback_is_one_of_them(self):
        for name in self.HELPERS:
            with self.subTest(helper=name):
                self.assertTrue(callable(getattr(crew_heal, name, None)))

    def test_safely_reports_a_helper_that_demands_a_third_argument(self):
        got = crew_heal.safely(heal_with_extra, {"id": "t_1"}, True)
        self.assertEqual("with_extra", got["class"])
        self.assertEqual("t_1", got["card"])
        self.assertEqual("could not heal: heal_with_extra() missing 1 required positional "
                         "argument: 'healed'", got["action"])

    def test_a_helper_that_returns_none_reports_nothing(self):
        def heal_nothing(card, dry):
            return None

        self.assertIsNone(crew_heal.safely(heal_nothing, {"id": "t_1"}, True))


class HealCardRoutingTests(unittest.TestCase):
    """heal_card(card, dry): which remedy a card's state selects, and what `fixed` says about it."""

    def setUp(self):
        self.seen = []

        def remedy(name, fixed=True):
            def fn(card, dry):
                self.seen.append(name)
                return {"class": name, "card": card["id"], "action": name, "fixed": fixed}
            fn.__name__ = "heal_" + name
            return fn

        self.patches = [
            mock.patch.object(crew_heal, "heal_held_workspace", remedy("held_workspace")),
            mock.patch.object(crew_heal, "heal_dead_model", remedy("dead_model", fixed=False)),
            mock.patch.object(crew_heal, "heal_stale_verify", remedy("stale_verify")),
            mock.patch.object(crew_heal, "heal_stamp", lambda card, cls: False),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def card(self, **kw):
        base = {"id": "t_1", "status": "ready", "last_failure_error": "", "body": ""}
        base.update(kw)
        return base

    def test_a_ready_card_with_no_wall_needs_no_remedy(self):
        self.assertIsNone(crew_heal.heal_card(self.card(last_failure_error="the tests fail on line 3"), False))
        self.assertEqual([], self.seen)

    def test_a_held_workspace_wins_before_the_dead_model(self):
        got = crew_heal.heal_card(self.card(last_failure_error="permission denied: /x"), False)
        self.assertEqual("held_workspace", got["class"])
        self.assertTrue(got["fixed"])
        self.assertEqual(["held_workspace"], self.seen)

    def test_a_wall_falls_through_to_the_dead_model_and_stays_unfixed_when_no_pick_fits(self):
        with mock.patch.object(crew_heal, "heal_held_workspace", lambda card, dry: None):
            got = crew_heal.heal_card(self.card(last_failure_error="429 rate limit"), False)
        self.assertEqual(("dead_model", False), (got["class"], got["fixed"]))

    def test_an_auth_error_is_not_a_model_wall(self):
        with mock.patch.object(crew_heal, "heal_held_workspace", lambda card, dry: None):
            self.assertIsNone(crew_heal.heal_card(self.card(last_failure_error="invalid api key"), False))

    def test_a_blocked_card_with_a_proof_command_gets_the_stale_check(self):
        got = crew_heal.heal_card(self.card(status="blocked", body="proof command: true\n"), False)
        self.assertEqual("stale_verify", got["class"])

    def test_a_blocked_card_with_no_proof_command_gets_nothing(self):
        self.assertIsNone(crew_heal.heal_card(self.card(status="blocked", body="Role: worker\n"), False))

    def test_other_states_get_nothing(self):
        for status in ("running", "done", "review", "triage", "todo"):
            with self.subTest(status=status):
                self.assertIsNone(crew_heal.heal_card(
                    self.card(status=status, last_failure_error="429", body="proof command: true\n"), False))


class ReleaseBlockTests(unittest.TestCase):
    """release_block lifts a block even when the kernel CLI cannot (a busy board during a proof run)."""

    def test_a_missing_card_is_not_released_and_a_blocked_one_is(self):
        db = os.path.join(_TMPDIR, "release.db")
        conn = sqlite3.connect(db)
        conn.execute("create table tasks (id text primary key, status text, block_kind text, "
                     "last_failure_error text)")
        conn.execute("insert into tasks values ('t_note', 'blocked', 'needs_input', 'boom')")
        conn.commit()
        conn.close()
        with mock.patch.object(crew_heal, "KANBAN_DB", db):
            self.assertFalse(crew_heal.release_block("t_missing"))
            self.assertTrue(crew_heal.release_block("t_note"))
        conn = sqlite3.connect(db)
        try:
            row = conn.execute("select status, block_kind, last_failure_error from tasks "
                               "where id = 't_note'").fetchone()
        finally:
            conn.close()
        self.assertEqual(("ready", None, None), tuple(row))


if __name__ == "__main__":
    unittest.main()
