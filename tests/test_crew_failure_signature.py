#!/usr/bin/env python3
"""Unit tests for the failure signature in scripts/crew_heal.py.

"Failed the same way" is one signature - the run status plus what walled it - so two different failures
are never counted as one repeat. crew_coordinator.py reads it to name the repeated failure when its own
retry cap hands a card to the owner.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

# crew_heal binds KANBAN_DB at import time: point it at a throwaway db *before* importing.
_TMP = tempfile.mkdtemp(prefix="crew-heal-unit-")
_DB = os.path.join(_TMP, "kanban.db")
os.environ["KANBAN_DB"] = _DB
os.environ.pop("CREW_PROFILE_PREFIX", None)

import crew_heal  # noqa: E402

# `unittest discover` may have imported crew_heal already (another module bound it to its own path).
crew_heal.KANBAN_DB = _DB


def run(status, error="", summary="", outcome="", rid=1, task="t_x"):
    return {"id": rid, "task_id": task, "status": status, "outcome": outcome or status,
            "error": error, "summary": summary}


class NoLiveBoardTests(unittest.TestCase):
    def test_the_module_reads_a_throwaway_db(self):
        self.assertNotEqual(os.path.join(os.path.expanduser("~"), ".hermes", "kanban.db"),
                            os.path.realpath(crew_heal.KANBAN_DB))


class WallKindTests(unittest.TestCase):
    def test_quota_words(self):
        for text in ("quota exceeded", "rate limit exceeded: free-models-per-day",
                     "HTTP 429", "out of credits", "billing issue"):
            self.assertEqual("quota", crew_heal.wall_kind(text), text)

    def test_rate_does_not_fire_inside_a_word(self):
        self.assertEqual("other", crew_heal.wall_kind("the run was moderately slow"))

    def test_auth_words(self):
        for text in ("HTTP 403 forbidden", "invalid api key", "permission denied"):
            self.assertEqual("auth", crew_heal.wall_kind(text), text)

    def test_the_remaining_kinds(self):
        self.assertEqual("timeout", crew_heal.wall_kind("run timed out after 600s"))
        self.assertEqual("spawn_failed", crew_heal.wall_kind("python3: no such file or directory"))
        self.assertEqual("tool_error", crew_heal.wall_kind("TypeError: bad operand"))
        self.assertEqual("proof_failed", crew_heal.wall_kind("assert 1 == 2 - test failed"))

    def test_nothing_matches(self):
        self.assertEqual("other", crew_heal.wall_kind(""))
        self.assertEqual("other", crew_heal.wall_kind(None))


class FailureSignatureTests(unittest.TestCase):
    def test_a_successful_run_has_no_signature(self):
        self.assertIsNone(crew_heal.failure_signature(run("completed")))
        self.assertIsNone(crew_heal.failure_signature(run("done", outcome="completed")))
        self.assertIsNone(crew_heal.failure_signature(run("running")))

    def test_a_wall_becomes_the_second_half_of_the_signature(self):
        self.assertEqual(("crashed", "quota"),
                         crew_heal.failure_signature(run("crashed", "rate limit exceeded")))
        self.assertEqual(("blocked", "spawn_failed"),
                         crew_heal.failure_signature(run("blocked", "python3: not found")))


class RepeatChainTests(unittest.TestCase):
    def test_two_same_kind_failures_are_a_repeat(self):
        runs = [run("crashed", "rate limit exceeded", rid=9), run("crashed", "rate limit exceeded", rid=8)]
        self.assertEqual([9, 8], [r["id"] for r in crew_heal.repeat_chain("t_x", runs=runs)])

    def test_two_different_failures_are_not(self):
        runs = [run("crashed", "rate limit exceeded", rid=9), run("crashed", "TypeError: boom", rid=8)]
        self.assertEqual([], crew_heal.repeat_chain("t_x", runs=runs))

    def test_a_success_breaks_the_chain(self):
        runs = [run("completed", rid=9), run("crashed", "rate limit exceeded", rid=8),
                run("crashed", "rate limit exceeded", rid=7)]
        self.assertEqual([], crew_heal.repeat_chain("t_x", runs=runs))

    def test_the_chain_is_the_trailing_run_of_failures(self):
        runs = [run("crashed", "rate limit exceeded", rid=9), run("crashed", "rate limit exceeded", rid=8),
                run("timed_out", "run timed out", rid=7)]
        self.assertEqual([9, 8], [r["id"] for r in crew_heal.repeat_chain("t_x", runs=runs)])

    def test_need_three_stops_at_three(self):
        runs = [run("crashed", "429", rid=n) for n in (9, 8, 7, 6)]
        self.assertEqual([9, 8, 7], [r["id"] for r in crew_heal.repeat_chain("t_x", runs=runs, need=3)])

    def test_a_single_failure_is_not_a_repeat(self):
        self.assertEqual([], crew_heal.repeat_chain("t_x", runs=[run("crashed", "429", rid=9)]))

    def test_an_empty_run_list_is_not_a_repeat(self):
        self.assertEqual([], crew_heal.repeat_chain("t_x", runs=[]))


if __name__ == "__main__":
    unittest.main()
