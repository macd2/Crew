#!/usr/bin/env python3
"""Unit tests for the probe-card rule: the coordinator pass never acts on another run's fixture.

The coordinator pass runs on every dispatch tick against the same board the proofs seed probe cards into,
so it skips a probe card through crew_card's rule unless a proof passes --probe. crew_heal reads KANBAN_DB at
import time, so this module points it at a throwaway path BEFORE importing anything.
"""
import inspect
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

_TMPDIR = tempfile.mkdtemp(prefix="crew-probe-skip-test-")
os.environ["KANBAN_DB"] = os.path.join(_TMPDIR, "not-the-live-board.db")

import crew_card  # noqa: E402
import crew_coordinator  # noqa: E402


class ProbeCardTests(unittest.TestCase):
    def test_it_recognises_the_marker_every_proof_writes(self):
        for marked in ("probe", "PROBE", " Probe "):
            self.assertTrue(crew_card.probe_card(marked), marked)

    def test_a_real_owner_is_not_a_probe(self):
        for other in ("", None, "crew-coordinator", "crew-worker", "the owner",
                      "prober", "probe-card", "probes"):
            self.assertFalse(crew_card.probe_card(other), other)


class FilterProbesTests(unittest.TestCase):
    def setUp(self):
        self.probe = {"id": "t9x_probe", "created_by": "probe"}
        self.real = {"id": "t_2f00", "created_by": "crew-coordinator"}
        self.bare = {"id": "t_2f01"}          # a row whose caller did not select created_by

    def test_a_scheduled_pass_drops_the_probe_and_keeps_the_rest(self):
        self.assertEqual([self.real, self.bare],
                         crew_card.filter_probes([self.probe, self.real, self.bare]))

    def test_a_missing_marker_keeps_the_card(self):
        # dropping a card because the caller forgot a column would silently stop real work
        self.assertIn(self.bare, crew_card.filter_probes([self.bare]))

    def test_the_owning_run_gets_its_cards_back(self):
        self.assertEqual([self.probe, self.real],
                         crew_card.filter_probes([self.probe, self.real], include_probe=True))

    def test_it_preserves_order_and_returns_a_list(self):
        got = crew_card.filter_probes((self.real, self.probe))
        self.assertIsInstance(got, list)
        self.assertEqual([self.real], got)


class CoordinatorUsesTheRuleTests(unittest.TestCase):
    """The rule is only worth having if the pass applies it and offers --probe."""

    def test_the_coordinator_skips_a_probe_card_unless_asked(self):
        self.assertIn("probe_card", inspect.getsource(crew_coordinator.handle_card))
        self.assertIn('"--probe"', inspect.getsource(crew_coordinator.main))


if __name__ == "__main__":
    unittest.main()
