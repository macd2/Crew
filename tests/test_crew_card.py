#!/usr/bin/env python3
"""Unit tests for the pure logic in scripts/crew_card.py.

No board, no network, no subprocess, no hermes CLI. Every test points HERMES_HOME at a throwaway
directory so the config/roles lookups read test fixtures and never the live profile.

Run:  python3 -m unittest discover -s tests -t .      (from the repo root)
      python3 -m pytest tests -q
"""
import json
import os
import shutil
import sqlite3
import sys
import time
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
os.environ.setdefault("HERMES_BIN", "/bin/false")   # a unit test never starts the real `hermes` (scratch HERMES_HOME bootstraps a runtime and rewrites the live launcher)

sys.path.insert(0, str(REPO / "tests"))
from unittest import mock  # noqa: E402

import crew_card  # noqa: E402
import kernel_board as K  # noqa: E402


class CardTestCase(unittest.TestCase):
    """Base: a fresh HERMES_HOME per test, with the process environment restored afterwards."""

    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-card-test-")
        os.environ["HERMES_HOME"] = self.home
        os.environ.pop("CREW_PROFILE_PREFIX", None)

    def tearDown(self):
        for key in [k for k in os.environ if k not in self._env]:
            del os.environ[key]
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)

    def write(self, relpath, text):
        path = os.path.join(self.home, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(text)
        return path


class FieldTests(CardTestCase):
    """field(body, key): the one reader of contract lines."""

    def test_field_returns_the_value_of_a_key_case_insensitively(self):
        body = "Role: worker\nGOAL: ship the thing\nDone when: tests pass\n"
        self.assertEqual("ship the thing", crew_card.field(body, "goal"))
        self.assertEqual("ship the thing", crew_card.field(body, "GOAL"))
        self.assertEqual("tests pass", crew_card.field(body, "done when"))

    def test_field_strips_surrounding_whitespace(self):
        self.assertEqual("ship it", crew_card.field("Goal:    ship it   \n", "goal"))

    def test_field_returns_the_first_occurrence_only(self):
        self.assertEqual("first", crew_card.field("Goal: first\nGoal: second\n", "goal"))

    def test_field_is_none_when_the_key_is_absent(self):
        self.assertIsNone(crew_card.field("Role: worker\n", "goal"))

    def test_field_is_none_when_nothing_follows_the_colon(self):
        # the regex needs at least one character after the colon
        self.assertIsNone(crew_card.field("Goal:\n", "goal"))
        self.assertIsNone(crew_card.field("", "goal"))
        self.assertIsNone(crew_card.field(None, "goal"))

    def test_field_returns_an_empty_string_for_a_whitespace_only_value(self):
        # quirk: "\s*" gives one whitespace char back to the group, so a blank value reads as ""
        # rather than None. Harmless for truthiness checks, but it is not the same as "absent".
        self.assertEqual("", crew_card.field("Goal:   \n", "goal"))
        self.assertEqual("", crew_card.field("Goal: \n", "goal"))

    def test_field_matches_a_key_only_when_a_colon_follows_it(self):
        # "proof" must not read the "proof command:" line, "done" must not read "Done when:"
        body = "proof command: pytest -q\nDone when: green\n"
        self.assertIsNone(crew_card.field(body, "proof"))
        self.assertIsNone(crew_card.field(body, "done"))
        self.assertEqual("pytest -q", crew_card.field(body, "proof command"))

    def test_field_reads_a_key_indented_on_its_own_line(self):
        self.assertEqual("x", crew_card.field("Role: worker\n   Goal: x\n", "goal"))


class ContractGapsTests(unittest.TestCase):
    """contract_gaps(c, allow_no_proof): the contract gate, defended mechanically."""

    COMPLETE = {"role": "worker", "goal": "g", "artifact": "a", "lands": "l",
                "audience": "For MarketingTeam", "done_when": "d", "proof_cmd": "p"}

    def test_a_complete_worker_card_has_no_gaps(self):
        self.assertEqual([], crew_card.contract_gaps(self.COMPLETE))

    def test_a_complete_content_card_has_no_gaps(self):
        self.assertEqual([], crew_card.contract_gaps(dict(self.COMPLETE, role="content")))

    def test_every_missing_field_is_reported_in_contract_order_with_the_role_last(self):
        self.assertEqual(["GOAL", "Artifact", "Lands at", "For", "Done when", "proof command",
                          "role (worker or content)"], crew_card.contract_gaps({}))

    def test_only_the_role_gap_remains_when_the_role_is_the_only_problem(self):
        self.assertEqual(["role (worker or content)"],
                         crew_card.contract_gaps(dict(self.COMPLETE, role="verifier")))

    def test_empty_and_whitespace_values_count_as_missing(self):
        card = dict(self.COMPLETE, goal="   ", artifact="", lands=None, audience="\t")
        self.assertEqual(["GOAL", "Artifact", "Lands at", "For"], crew_card.contract_gaps(card))

    def test_allow_no_proof_skips_only_the_proof_command(self):
        card = dict(self.COMPLETE, proof_cmd="")
        self.assertEqual(["proof command"], crew_card.contract_gaps(card))
        self.assertEqual([], crew_card.contract_gaps(card, allow_no_proof=True))

    def test_allow_no_proof_does_not_excuse_anything_else(self):
        self.assertEqual(["Artifact", "Lands at", "For", "Done when",
                          "role (worker or content)"],
                         crew_card.contract_gaps({"proof_cmd": "p", "goal": "g"}, allow_no_proof=True))

    def test_the_role_gate_accepts_the_forms_open_card_accepts(self):
        # open_card() strips/lowercases the role before it writes the card, so run_plan (which gates
        # the raw child spec) must accept the same forms - otherwise a plan is refused for children
        # open_card would happily open.
        self.assertEqual([], crew_card.contract_gaps(dict(self.COMPLETE, role="Worker")))
        self.assertEqual([], crew_card.contract_gaps(dict(self.COMPLETE, role=" worker ")))
        self.assertEqual([], crew_card.contract_gaps(dict(self.COMPLETE, role="CONTENT")))
        self.assertEqual(["role (worker or content)"],
                         crew_card.contract_gaps(dict(self.COMPLETE, role="verifier")))


class OriginIdTests(unittest.TestCase):
    """origin_id(value): the chat a card came from, kept verbatim or dropped."""

    def test_no_value_is_no_origin(self):
        for value in (None, "", "   "):
            with self.subTest(value=value):
                self.assertEqual("", crew_card.origin_id(value))

    def test_a_missing_platform_or_chat_is_no_origin(self):
        for value in (":chat", "zulip:", "web: ", "plainword", "  :  "):
            with self.subTest(value=value):
                self.assertEqual("", crew_card.origin_id(value))

    def test_a_chat_origin_is_kept_verbatim(self):
        self.assertEqual("zulip:stream:Kanban|crew-alerts",
                         crew_card.origin_id("zulip:stream:Kanban|crew-alerts"))
        self.assertEqual("telegram:-1001234", crew_card.origin_id("telegram:-1001234"))

    def test_surrounding_whitespace_is_stripped(self):
        self.assertEqual("zulip:1|2", crew_card.origin_id("  zulip:1|2  "))


class FmtTokensTests(unittest.TestCase):
    """fmt_tokens(n): the numbers printed in stats."""

    def test_below_a_thousand_is_plain(self):
        self.assertEqual("999", crew_card.fmt_tokens(999))
        self.assertEqual("0", crew_card.fmt_tokens(0))
        self.assertEqual("0", crew_card.fmt_tokens(None))

    def test_thousands_get_a_k_suffix(self):
        self.assertEqual("1k", crew_card.fmt_tokens(1000))
        self.assertEqual("120k", crew_card.fmt_tokens(120000))

    def test_millions_get_an_m_suffix_with_one_decimal(self):
        self.assertEqual("1.0M", crew_card.fmt_tokens(1000000))
        self.assertEqual("1.5M", crew_card.fmt_tokens(1500000))

    def test_just_below_a_million_is_still_reported_in_k(self):
        # boundary quirk: the M branch starts at exactly 1_000_000, so 999_999 prints as "1000k"
        self.assertEqual("1000k", crew_card.fmt_tokens(999999))


class RolesJsonTests(CardTestCase):
    """default_budget(role) / budget_floor(): read from roles/roles.json, never hardcoded."""

    def repo_roles(self):
        with open(REPO / "roles" / "roles.json") as fh:
            return json.load(fh)

    def test_repo_roles_json_supplies_each_role_budget(self):
        data = self.repo_roles()
        for role in data["roles"]:
            if isinstance(role.get("budget_tokens"), int):
                with self.subTest(role=role["name"]):
                    self.assertEqual(role["budget_tokens"], crew_card.default_budget(role["name"]))

    def test_the_unknown_role_falls_back_to_the_default_budget(self):
        expected = self.repo_roles().get("default_budget_tokens")
        self.assertEqual(expected if isinstance(expected, int) else crew_card.DEFAULT_BUDGET,
                         crew_card.default_budget("no-such-role"))

    def test_budget_floor_matches_repo_roles_json(self):
        expected = self.repo_roles().get("budget_floor_tokens")
        self.assertEqual(expected if isinstance(expected, int) else crew_card.BUDGET_FLOOR,
                         crew_card.budget_floor())

    def test_the_profile_home_roles_json_wins_over_the_repo_copy(self):
        self.write("roles/crew/roles.json",
                   json.dumps({"budget_floor_tokens": 777, "default_budget_tokens": 55,
                               "roles": [{"name": "worker", "budget_tokens": 42}]}))
        self.assertEqual(777, crew_card.budget_floor())
        self.assertEqual(42, crew_card.default_budget("worker"))
        self.assertEqual(55, crew_card.default_budget("content"))

    def test_non_integer_values_fall_back_to_the_module_constants(self):
        self.write("roles/crew/roles.json",
                   json.dumps({"budget_floor_tokens": "not-an-int",
                               "roles": [{"name": "worker", "budget_tokens": "x"}]}))
        self.assertEqual(crew_card.BUDGET_FLOOR, crew_card.budget_floor())
        self.assertEqual(crew_card.DEFAULT_BUDGET, crew_card.default_budget("worker"))
        self.assertEqual(crew_card.DEFAULT_BUDGET, crew_card.default_budget("unknown"))

    def test_a_corrupt_roles_json_is_ignored_and_the_repo_copy_still_answers(self):
        self.write("roles/crew/roles.json", "{not json")
        expected_default = self.repo_roles().get("default_budget_tokens")
        self.assertEqual(expected_default if isinstance(expected_default, int) else crew_card.DEFAULT_BUDGET,
                         crew_card.default_budget("no-such-role"))
        self.assertGreater(crew_card.budget_floor(), 0)


class ProfilePrefixTests(CardTestCase):
    """profile_prefix(): env, then this profile's config.yaml, then the built-in default."""

    def test_env_wins(self):
        os.environ["CREW_PROFILE_PREFIX"] = "env-"
        self.assertEqual("env-", crew_card.profile_prefix())

    def test_config_value_is_used_when_env_is_unset(self):
        self.write("config.yaml", 'profile: x\ncrew:\n  profile_prefix: "crew-x-"\n  other: 1\n')
        self.assertEqual("crew-x-", crew_card.profile_prefix())

    def test_the_builtin_default_applies_with_no_config(self):
        self.assertEqual("crew-", crew_card.profile_prefix())
        self.assertEqual(crew_card.DEFAULT_PREFIX, crew_card.profile_prefix())

    def test_a_nested_crew_section_under_another_key_is_not_read(self):
        self.write("config.yaml", 'skills:\n  crew:\n    profile_prefix: nope\n')
        self.assertEqual("crew-", crew_card.profile_prefix())

    def test_an_indented_crew_line_is_not_a_top_level_section(self):
        self.write("config.yaml", "outer:\n  crew:\n    profile_prefix: nope\n")
        self.assertEqual("crew-", crew_card.profile_prefix())


class FixtureAssigneeTests(unittest.TestCase):
    """A fixture card must be unclaimable: the dispatcher claims by profile name."""

    def test_no_profile_answers_to_the_fixture_assignee(self):
        home = Path(os.path.expanduser("~/.hermes/profiles"))
        names = set()
        if home.is_dir():
            names = {p.name for p in home.iterdir() if p.is_dir()}
        self.assertNotIn(crew_card.FIXTURE_ASSIGNEE, names)
        self.assertIsNot(crew_card.FIXTURE_ASSIGNEE, crew_card.PROBE_OWNER)

    def test_the_heal_and_probe_skip_proofs_seed_it(self):
        """The two proofs whose fixtures were picked up and worked by a real agent."""
        import re
        scripts = Path(crew_card.__file__).resolve().parent
        for name in ("crew_heal_proof.py", "crew_probe_skip_proof.py"):
            text = (scripts / name).read_text()
            inserts = re.findall(r"insert into tasks.*?values.*?\n.*?\n", text, re.S)
            self.assertTrue(inserts, name)
            for chunk in inserts:
                self.assertNotIn('"crew-worker",', chunk, name)
                self.assertNotIn("'crew-worker',", chunk, name)


class CrewBodyTests(unittest.TestCase):
    def test_a_coordinator_or_role_line_makes_a_crew_card(self):
        self.assertTrue(crew_card.is_crew_body("Role: worker\nGOAL: g"))
        self.assertTrue(crew_card.is_crew_body("  coordinator: owner-chat/s"))
        self.assertTrue(crew_card.is_crew_body(crew_card.render_body(
            {"role": "worker", "budget": 120000, "goal": "g", "done_when": "d", "proof_cmd": "true"})))

    def test_anything_else_is_not(self):
        for body in ("", None, "just a note", "the Role: is in the middle of a line"):
            self.assertFalse(crew_card.is_crew_body(body))


class LiftAndRetryTests(CardTestCase):
    """lift_block / retry_card / unstuck_card on a board made by Hermes's own code (tests/kernel_board.py): a card
    in triage is a real second same-kind block, and it leaves triage through the kernel's specify_triage_task."""

    def setUp(self):
        super().setUp()
        self.kb, self.conn, self.db = K.open_board(self.home)
        self.addCleanup(self.conn.close)
        self.cli = K.kernel_cli(self.db)
        patch = mock.patch.object(crew_card.subprocess, "run", self.cli)
        patch.start()
        self.addCleanup(patch.stop)

    def task(self, cid):
        return self.kb.get_task(self.conn, cid)

    def test_a_triage_card_leaves_triage_with_the_new_approach_and_the_kernel_keeps_its_block_counter(self):
        cid = K.add_card(self.conn, "triage")
        self.assertEqual(("triage", 2), (self.task(cid).status, self.task(cid).block_recurrences))
        new = K.BODY + "\nCoordinator fix 1: try the other endpoint\n"
        got = crew_card.lift_block(cid, body=new)
        self.assertEqual((0, "ready"), (got["rc"], got["status"]))
        self.assertEqual(new, self.task(cid).body)
        self.assertEqual(2, self.task(cid).block_recurrences, "the counter is the kernel's, not the crew's")
        self.assertEqual(1, K.events(self.conn, cid).count("specified"))
        self.assertEqual([], [c for c in self.cli.calls if "unblock" in c], "no raw unblock on a triage card")

    def test_a_triage_card_with_an_open_parent_waits_in_todo(self):
        parent = K.add_card(self.conn, "ready")
        cid = K.add_card(self.conn, "triage")
        self.kb.link_tasks(self.conn, parent, cid)
        crew_card.lift_block(cid)
        self.assertEqual("todo", self.task(cid).status)

    def test_a_triage_exit_without_a_body_changes_no_field(self):
        cid = K.add_card(self.conn, "triage", body=K.BODY)
        before = self.task(cid)
        ok, text = crew_card.unstuck_card(cid)
        after = self.task(cid)
        self.assertTrue(ok, text)
        self.assertEqual((before.title, before.body, before.assignee), (after.title, after.body, after.assignee))
        self.assertEqual("ready", after.status)

    def test_a_blocked_card_is_unblocked_through_the_kernels_command(self):
        cid = K.add_card(self.conn, "blocked")
        got = crew_card.lift_block(cid)
        self.assertEqual((0, "ready"), (got["rc"], got["status"]))
        self.assertEqual(1, len([c for c in self.cli.calls if "unblock" in c]))

    def test_a_card_already_running_is_left_alone(self):
        cid = K.add_card(self.conn, "ready")
        self.assertEqual("already ready", crew_card.lift_block(cid)["out"])
        self.assertEqual([], self.cli.calls)

    def test_an_unknown_card_is_reported_not_raised(self):
        self.assertEqual(2, crew_card.lift_block("t_none")["rc"])
        self.assertFalse(crew_card.retry_card("t_none")["ok"])

    def test_retry_of_a_triage_card_writes_budget_and_fix_in_the_one_kernel_exit(self):
        cid = K.add_card(self.conn, "triage")
        dry = crew_card.retry_card(cid, budget=300000, dry_run=True)
        self.assertEqual((True, 300000), (dry["ok"], dry["budget"]))
        self.assertEqual("triage", self.task(cid).status)
        res = crew_card.retry_card(cid, budget=300000, body=K.BODY + "Coordinator fix 1: x\n")
        self.assertEqual("ready", self.task(cid).status)
        self.assertIn("Budget: 300000 tokens", self.task(cid).body)
        self.assertIn("Coordinator fix 1: x", self.task(cid).body)
        self.assertEqual(0, res["unblock"]["rc"])
        self.assertEqual([], [c for c in self.cli.calls if "edit" in c], "one write, not an edit then a lift")
        self.assertEqual(1, K.events(self.conn, cid).count("specified"))

    def test_retry_of_a_blocked_card_edits_the_body_then_unblocks(self):
        cid = K.add_card(self.conn, "blocked")
        crew_card.retry_card(cid, budget=300000)
        self.assertIn("Budget: 300000 tokens", self.task(cid).body)
        self.assertEqual("ready", self.task(cid).status)
        self.assertIn("edited", K.events(self.conn, cid))

    def test_the_default_ceiling_is_one_and_six_tenths_of_what_was_spent_with_a_floor(self):
        cid = K.add_card(self.conn, "triage")
        got = crew_card.retry_card(cid, dry_run=True)
        self.assertEqual(crew_card.budget_floor(), got["budget"])       # nothing spent: the floor

    def test_unstuck_refuses_a_card_that_is_not_stuck_or_not_a_crew_card(self):
        ready = K.add_card(self.conn, "ready")
        ok, text = crew_card.unstuck_card(ready)
        self.assertEqual((False, True), (ok, "nothing to unstick" in text))
        plain = K.add_card(self.conn, "triage", body="just a note")
        ok, text = crew_card.unstuck_card(plain)
        self.assertEqual((False, "triage"), (ok, self.task(plain).status))
        self.assertFalse(crew_card.unstuck_card("t_none")[0])

    def test_unstuck_moves_a_blocked_crew_card_and_says_where_it_went(self):
        cid = K.add_card(self.conn, "blocked")
        self.assertEqual((True, "%s: blocked -> ready" % cid), crew_card.unstuck_card(cid))

    def test_release_hold_clears_the_stale_error_through_the_kernel_and_records_it(self):
        cid = K.add_card(self.conn, "ready")
        self.conn.execute("update tasks set last_failure_error = 'HTTP 429 quota', consecutive_failures = 3 "
                          "where id = ?", (cid,))          # seeding the fixture state the kernel's guard reads
        self.conn.commit()
        self.assertTrue(crew_card.release_hold(cid))
        t = self.task(cid)
        self.assertEqual((None, 0), (t.last_failure_error, t.consecutive_failures))
        from hermes_cli import kanban_db_dispatch
        self.assertIsNone(kanban_db_dispatch.check_respawn_guard(self.conn, cid))
        self.assertIn("hold_released", K.events(self.conn, cid))

    def test_status_lists_a_triage_card_with_its_unstuck_command(self):
        cid = K.add_card(self.conn, "triage")
        text = crew_card.status_text()
        self.assertIn(cid, text)
        self.assertIn("Needs you: /crew-unstuck %s" % cid, text)


class SplitPlanTests(CardTestCase):
    """run_plan(closeout_proof=...): a split's children carry no proof of their own and the close-out runs the split
    card's owner-confirmed one. The cards are recorded, not created (create_card / finish_card are replaced)."""

    PROOF = "sh -c 'exit 0'"
    CHILD = {"title": "a", "goal": "g", "role": "worker", "artifact": "a.md", "lands": "/x", "audience": "me",
             "done_when": "d", "budget": 150000}

    def setUp(self):
        super().setUp()
        self.made = []

        def create(title, body, assignee, skills=(), parents=(), **kw):
            cid = "t_%d" % (len(self.made) + 1)
            self.made.append({"id": cid, "title": title, "body": body, "assignee": assignee, "parents": list(parents), **kw})
            return {"id": cid, "assignee": assignee}

        for p in (mock.patch.object(crew_card, "create_card", create),
                  mock.patch.object(crew_card, "finish_card", lambda *a, **k: {}),
                  mock.patch.object(crew_card, "_append_card_event", lambda *a, **k: True),
                  mock.patch.object(crew_card, "_kanban", lambda *a, **k: mock.Mock(returncode=0, stdout="", stderr=""))):
            p.start()
            self.addCleanup(p.stop)

    def test_children_have_no_proof_of_their_own_and_the_closeout_runs_the_split_cards_proof(self):
        res = crew_card.run_plan({"title": "t", "goal": "g", "children": [dict(self.CHILD)]}, closeout_proof=self.PROOF)
        child = next(m for m in self.made if m["id"] == res["children"][0]["id"])
        self.assertIn("Verify: closeout", child["body"])
        self.assertEqual("", crew_card.proof_cmd(child["body"]))
        self.assertIsNone(child.get("model"))
        closeout = self.made[-1]
        self.assertEqual("python3 %s closeout --cards %s && (%s)" % (crew_card.SELF, child["id"], self.PROOF),
                         crew_card.proof_cmd(closeout["body"]))

    def test_a_split_child_closes_without_a_pass_line_and_a_normal_child_still_needs_one(self):
        crew_card.run_plan({"title": "t", "goal": "g", "children": [dict(self.CHILD)]}, closeout_proof=self.PROOF)
        body = self.made[1]["body"]
        self.assertFalse(crew_card.needs_pass(body))
        self.assertTrue(crew_card.close_check("t_2", body)[0])
        crew_card.run_plan({"title": "t", "goal": "g", "children": [dict(self.CHILD, proof_cmd=self.PROOF)]})
        plain = next(m["body"] for m in self.made if "Verify: proof" in m["body"])
        self.assertTrue(crew_card.needs_pass(plain))

    def test_a_spec_cannot_ask_for_a_child_without_a_proof(self):
        with self.assertRaises(ValueError):
            crew_card.run_plan({"title": "t", "goal": "g",
                                "children": [dict(self.CHILD, verify="closeout")]})
        with self.assertRaises(ValueError):                 # no closeout_proof: the proof is still required
            crew_card.run_plan({"title": "t", "goal": "g", "children": [dict(self.CHILD)]})
        self.assertEqual([], self.made)

    def test_the_closeout_check_counts_a_done_split_child_with_no_verdict_but_not_an_open_one(self):
        crew_card.run_plan({"title": "t", "goal": "g", "children": [dict(self.CHILD)]}, closeout_proof=self.PROOF)
        body = self.made[1]["body"]
        for status, want in (("done", 0), ("running", 1)):
            with mock.patch.object(crew_card, "card_row", lambda cid, st=status: (cid, "t", st, "w", body)), \
                    mock.patch.object(crew_card, "all_verdicts", lambda cid: []):
                self.assertEqual(want, crew_card.cmd_closeout(mock.Mock(cards="t_2")), status)


    def test_a_script_proof_closeout_is_independent_and_goes_to_the_verifier_not_a_missing_script_run(self):
        script = "python3 /srv/site/.crew/verify.py"
        crew_card.run_plan({"title": "t", "goal": "g", "children": [dict(self.CHILD)]}, closeout_proof=script)
        closeout = self.made[-1]["body"]
        self.assertEqual("independent", crew_card.verify_mode(closeout))
        self.assertIn(crew_card.role_profile("verifier"), crew_card.closer_profiles(closeout))
        self.assertNotIn(crew_card.profile_prefix() + "worker", crew_card.closer_profiles(closeout))
        self.assertIn("kanban_request_review", closeout)
        self.assertIn('reviewer="%s"' % crew_card.role_profile("verifier"), closeout)
        self.assertNotIn(" verdict --card", closeout)           # the coordinator never runs the verifier's script
        self.assertEqual("python3 %s closeout --cards t_2 && (%s)" % (crew_card.SELF, script), crew_card.proof_cmd(closeout))
        self.assertTrue(crew_card.needs_pass(closeout))

    def test_a_plain_proof_closeout_is_still_run_by_the_coordinator(self):
        crew_card.run_plan({"title": "t", "goal": "g", "children": [dict(self.CHILD)]}, closeout_proof=self.PROOF)
        closeout = self.made[-1]["body"]
        self.assertEqual("", crew_card.verify_mode(closeout))
        self.assertIn(" verdict --card $HERMES_KANBAN_TASK", closeout)
        self.assertNotIn("kanban_request_review", closeout)


class SendToVerifierTests(CardTestCase):
    """send_to_verifier on the kernel's real states: the stopped card is lifted and put in review in one step, so a
    dispatcher claim in between cannot make the review fail."""

    BODY = ("Role: worker\nCoordinator: owner/s\nVerify: independent\nGOAL: g\nDone when: d\n\n"
            "proof command: python3 /x/.crew/verify.py\n")

    def setUp(self):
        super().setUp()
        self.kb, self.conn, self.path = K.open_board(self.home)
        self.addCleanup(self.conn.close)
        self.cid = K.add_card(self.conn, "blocked", body=self.BODY)
        p = mock.patch.object(crew_card, "repin_for_review", lambda cid: {"action": "unchanged"})
        p.start()
        self.addCleanup(p.stop)

    def status(self):
        task = self.kb.get_task(self.conn, self.cid)
        return task.status, task.assignee

    def test_a_blocked_card_goes_to_review_for_the_verifier_in_one_step(self):
        res = crew_card.send_to_verifier(self.cid, "revise")
        self.assertTrue(res["ok"], res)
        self.assertEqual(("review", crew_card.role_profile("verifier")), self.status())

    def test_a_dispatcher_claim_between_the_lift_and_the_review_does_not_fail_it(self):
        real_unblock = self.kb.unblock_task

        def unblock_then_dispatcher_claims(conn, cid):
            ok = real_unblock(conn, cid)
            self.assertIsNotNone(self.kb.claim_task(conn, cid))        # the dispatcher wins the card first
            return ok
        with mock.patch.object(self.kb, "unblock_task", unblock_then_dispatcher_claims):
            res = crew_card.send_to_verifier(self.cid, "revise")
        self.assertTrue(res["ok"], res)
        self.assertEqual(("review", crew_card.role_profile("verifier")), self.status())

    def test_a_card_whose_writer_run_is_already_alive_is_refused_with_the_kernels_reason(self):
        self.kb.unblock_task(self.conn, self.cid)
        self.kb.claim_task(self.conn, self.cid)
        with mock.patch.object(self.kb, "_worker_alive", lambda *a: True):
            self.conn.execute("update tasks set worker_pid = 1, worker_started_at = 1 where id = ?", (self.cid,))
            self.conn.commit()
            res = crew_card.send_to_verifier(self.cid, "revise")
        self.assertFalse(res["ok"])
        self.assertIn("live claim", res["why"])
        self.assertEqual("running", self.status()[0])

    def test_a_writer_proof_card_is_not_sent(self):
        cid = K.add_card(self.conn, "blocked", body=self.BODY.replace("Verify: independent", "Verify: proof")
                         .replace("/x/.crew/verify.py", "/x/check.py"))
        self.assertEqual({"ok": False, "why": "not an independent-verification card"},
                         crew_card.send_to_verifier(cid, "revise"))


class VerdictLineTests(CardTestCase):
    """The verdict log: one writer (record_verdict), one reader (all_verdicts), one close rule (close_check)."""

    PROOF = "sh -c 'exit 0'"
    BODY = "Role: worker\nCoordinator: crew-coordinator\nGOAL: g\nDone when: d\n\nproof command: sh -c 'exit 0'\n"

    def setUp(self):
        super().setUp()
        self.db = os.path.join(self.home, "kanban.db")
        conn = sqlite3.connect(self.db)
        conn.executescript(
            "create table tasks (id text primary key, title text, status text, assignee text, body text);"
            "create table task_events (id integer primary key autoincrement, task_id text, run_id integer,"
            " kind text, payload text, created_at integer);")
        conn.commit()
        conn.close()
        os.environ["HERMES_KANBAN_DB"] = self.db

    def snap(self, cmd=None):
        """The snapshot a card gets when it opens: the only proof command a PASS line can be for."""
        crew_card.record_origin("t_v", env={"origin": "", "session": "s"}, proof_cmd=cmd or self.PROOF)

    def event(self, kind, payload=None, at=None):
        conn = sqlite3.connect(self.db)
        conn.execute("insert into task_events (task_id, kind, payload, created_at) values ('t_v', ?, ?, ?)",
                     (kind, json.dumps(payload or {}), int(at or time.time())))
        conn.commit()
        conn.close()

    def test_a_verdict_line_names_who_ran_it_and_in_which_run(self):
        os.environ["HERMES_KANBAN_RUN_ID"] = "42"
        rec = crew_card.record_verdict("t_v", self.PROOF, 0, "ok", 0.5)
        self.assertEqual("default", rec["by"])
        self.assertEqual(42, rec["run_id"])
        with open(crew_card.verdict_path("t_v")) as fh:
            line = json.loads(fh.read())
        self.assertEqual(("default", 42, "PASS"), (line["by"], line["run_id"], line["verdict"]))
        self.assertNotIn("profile", line)
        self.assertNotIn("role", line)

    def test_the_run_id_is_the_kernels_variable_and_absent_outside_a_worker(self):
        os.environ.pop("HERMES_KANBAN_RUN_ID", None)
        os.environ["HERMES_KANBAN_RUN"] = "7"               # the name the crew used to read: not the kernel's
        self.assertIsNone(crew_card.kanban_run_id())
        os.environ["HERMES_KANBAN_RUN_ID"] = "9"
        self.assertEqual(9, crew_card.kanban_run_id())

    def test_by_can_be_named_for_the_coordinator_loop_and_an_old_line_reads_by_its_profile(self):
        self.assertEqual("crew-coordinator", crew_card.record_verdict("t_v", "x", 1, "", 0, by="crew-coordinator")["by"])
        self.assertEqual("crew-verifier", crew_card.verdict_by({"profile": "crew-verifier", "role": "verifier"}))
        self.assertEqual("", crew_card.verdict_by({"role": "verifier"}))

    def test_the_reader_merges_homes_and_counts_a_shared_line_once(self):
        line = json.dumps({"ts": 5, "command": "c", "rc": 0, "verdict": "PASS", "by": "crew-worker"}) + "\n"
        self.write("crew/verdicts/t_v.jsonl", line)
        self.write("profiles/crew-verifier/crew/verdicts/t_v.jsonl", line +
                   json.dumps({"ts": "9", "command": "c", "rc": "1", "verdict": "FAIL"}) + "\n")
        got = crew_card.all_verdicts("t_v")
        self.assertEqual([5.0, 9.0], [v["ts"] for v in got])
        self.assertEqual(1, got[1]["rc"])

    def close(self, claimed=None):
        return crew_card.close_check("t_v", self.BODY, claimed)

    def put(self, rc, command=None, by="crew-worker", ts=None):
        rec = crew_card.record_verdict("t_v", command or self.PROOF, rc, "", 0, by=by)
        if ts is not None:
            path = crew_card.verdict_path("t_v")
            with open(path) as fh:
                lines = [json.loads(x) for x in fh]
            lines[-1]["ts"] = ts
            with open(path, "w") as fh:
                fh.write("".join(json.dumps(x) + "\n" for x in lines))
        return rec

    def test_no_verdict_line_means_no_close(self):
        self.snap()
        ok, why = self.close()
        self.assertFalse(ok)
        self.assertIn("verdict --card t_v", why)

    def test_a_pass_on_the_proof_command_closes(self):
        self.snap()
        self.put(0)
        self.assertEqual((True, "PASS by crew-worker"), self.close())

    def test_a_fail_a_foreign_command_or_the_chat_profile_does_not(self):
        self.snap()
        self.put(1)
        self.assertFalse(self.close()[0])
        os.remove(crew_card.verdict_path("t_v"))
        self.put(0, command="echo hi")
        self.assertIn("no verdict line for the card's proof command", self.close()[1])
        os.remove(crew_card.verdict_path("t_v"))
        self.put(0, by="owner-chat")
        self.assertIn("not by a crew role profile", self.close()[1])

    def test_a_pass_from_before_the_newest_claim_is_stale(self):
        self.snap()
        self.put(0, ts=1000.0)
        self.assertTrue(self.close(claimed=None)[0])
        self.assertFalse(self.close(claimed=2000)[0])
        self.put(0)                                                 # recorded after the claim
        self.assertTrue(self.close(claimed=2000)[0])

    def test_a_check_that_failed_after_the_pass_holds_the_card_and_the_chip_ends_on_the_same_line(self):
        self.snap()
        self.put(0, ts=1000.0)
        self.put(1, command="test -f nothing", ts=1001.0)
        ok, why = self.close()
        self.assertFalse(ok)
        self.assertIn("a check failed after the PASS line", why)
        self.assertEqual("FAIL", crew_card.verdict_lines("t_v")[-1]["verdict"])
        self.put(0, command="test -f nothing", ts=1002.0)           # the check now passes: newest line is a PASS
        self.assertTrue(self.close()[0])
        self.assertEqual("PASS", crew_card.verdict_lines("t_v")[-1]["verdict"])

    def test_a_card_with_no_proof_command_can_not_be_closed_by_tool_but_a_plan_parent_is_not_work(self):
        body = "Role: worker\nCoordinator: c\nGOAL: g\n\nproof command: (none - the verifier asks for one)\n"
        ok, why = crew_card.close_check("t_v", body)
        self.assertFalse(ok)
        self.assertIn("no owner-confirmed proof command", why)
        parent = "Role: coordinator\nCoordinator: c\n\nGOAL: g\n\nDone when: children done\n"
        self.assertFalse(crew_card.needs_pass(parent))
        self.assertTrue(crew_card.close_check("t_v", parent)[0])
        closeout = parent + "\nproof command: python3 crew_card.py closeout --cards a,b\n"
        self.assertTrue(crew_card.needs_pass(closeout))
        self.assertFalse(crew_card.needs_pass("just a card"))

    # ---- two-stage verification: the Verify line and the proof snapshot taken when the card opens

    def body(self, mode, proof=None):
        return ("Role: worker\nCoordinator: crew-coordinator\nVerify: %s\nGOAL: g\nDone when: d\n\n"
                "proof command: %s\n" % (mode, proof or self.PROOF))

    def test_the_verify_line_parses_defaults_and_refuses_a_bad_value(self):
        self.assertEqual("independent", crew_card.parse_contract(self.body("independent"))["verify"])
        self.assertEqual("", crew_card.parse_contract(self.BODY)["verify"])             # a card from before the line
        c = {"goal": "g", "artifact": "a", "lands": "l", "audience": "o", "done_when": "d", "proof_cmd": "true",
             "role": "worker"}
        self.assertEqual([], crew_card.contract_gaps(c))
        self.assertEqual(["Verify (proof or independent)"], crew_card.contract_gaps(dict(c, verify="maybe")))
        self.assertEqual("proof", crew_card.default_verify(c))                          # a proof command: the writer proves it
        self.assertEqual("independent", crew_card.default_verify(dict(c, proof_cmd="")))  # none: a verifier must judge
        self.assertEqual("independent", crew_card.default_verify(dict(c, verify="independent")))

    def test_render_body_writes_the_verify_line_and_the_finish_that_matches_it(self):
        c = {"role": "worker", "budget": 200000, "goal": "g", "done_when": "d", "proof_cmd": "true",
             "coordinator": "c"}
        proof, indep = crew_card.render_body(c), crew_card.render_body(dict(c, verify="independent"))
        self.assertEqual("proof", crew_card.verify_mode(proof))
        self.assertIn("kanban_request_review is refused", proof)
        self.assertEqual("independent", crew_card.verify_mode(indep))
        self.assertIn('kanban_request_review(summary=..., reviewer="crew-verifier")', indep)
        self.assertEqual("independent", crew_card.parse_contract(indep)["verify"])      # the round trip keeps it

    def test_the_snapshot_is_the_proof_command_the_card_opened_with_not_the_body_line(self):
        self.assertIsNone(crew_card.proof_snapshot("t_v"))
        crew_card.record_origin("t_v", env={"origin": "", "session": "s"}, proof_cmd="sh -c 'exit 0'")
        self.assertEqual("sh -c 'exit 0'", crew_card.proof_snapshot("t_v"))
        self.assertEqual("sh -c 'exit 0'", crew_card.close_proof_command("t_v"))        # the body line is never read
        self.assertEqual("", crew_card.close_proof_command("t_none"))                   # no snapshot: no command

    def test_a_pass_for_an_edited_proof_line_does_not_close_the_card(self):
        crew_card.record_origin("t_v", env={"origin": "", "session": "s"}, proof_cmd="sh -c 'exit 7'")
        edited = self.body("proof", proof="sh -c 'exit 0'")
        self.put(0, command="sh -c 'exit 0'", by="crew-worker")                         # the rewritten command passes
        ok, why = crew_card.close_check("t_v", edited)
        self.assertFalse(ok)
        self.assertIn("no verdict line for the card's proof command `sh -c 'exit 7'`", why)

    def test_a_rescope_decision_never_moves_the_snapshot_only_the_owners_confirmation_does(self):
        self.snap("old")
        self.event("crew_decision", {"decision": "rescope", "proof_cmd": "never", "applied": False})
        self.event("crew_decision", {"decision": "rescope", "proof_cmd": "new", "applied": True})
        self.assertEqual("old", crew_card.proof_snapshot("t_v"))                       # a model's proposal runs nothing
        self.event("proof_confirm", {"proof_cmd": "new", "by": "owner"})
        self.assertEqual("new", crew_card.proof_snapshot("t_v"))
        self.event("proof_confirm", {"proof_cmd": "new", "proof_mode": "brave", "by": "owner"})
        self.assertEqual("brave", crew_card.proof_snapshot_mode("t_v"))

    def test_the_verdict_tool_runs_the_snapshot_not_the_edited_line(self):
        self.snap("test -d /no/such/dir/crew")
        conn = sqlite3.connect(self.db)
        conn.execute("insert into tasks values ('t_v', 't', 'running', 'crew-worker', ?)",
                     (self.body("proof", proof="true"),))
        conn.commit()
        conn.close()
        import argparse
        args = argparse.Namespace(card="t_v", command=None, timeout=20, no_hand_back=True, by="crew-worker",
                                  for_event=None)
        self.assertEqual(1, crew_card.cmd_verdict(args))
        line = crew_card.all_verdicts("t_v")[-1]
        self.assertEqual(("test -d /no/such/dir/crew", 1, "FAIL"), (line["command"], line["rc"], line["verdict"]))

    def test_who_may_close_follows_the_verify_line(self):
        self.snap()
        self.put(0, by="crew-worker")
        self.assertTrue(crew_card.close_check("t_v", self.body("proof"))[0])
        ok, why = crew_card.close_check("t_v", self.body("independent"))
        self.assertFalse(ok)
        self.assertIn("not by the verifier", why)
        self.put(0, by="crew-verifier")
        self.assertTrue(crew_card.close_check("t_v", self.body("independent"))[0])
        os.remove(crew_card.verdict_path("t_v"))
        self.put(0, by="crew-verifier")                                                  # a verifier's PASS on a proof card
        self.assertFalse(crew_card.close_check("t_v", self.body("proof"))[0])
        os.remove(crew_card.verdict_path("t_v"))
        self.put(0, by="crew-coordinator")                                               # the coordinator's run counts in both
        self.assertTrue(crew_card.close_check("t_v", self.body("proof"))[0])
        self.assertTrue(crew_card.close_check("t_v", self.body("independent"))[0])
        self.assertTrue({"crew-content", "crew-worker", "crew-verifier", "crew-coordinator"}
                        <= crew_card.closer_profiles(self.BODY))                         # no line: the old rule

    def test_the_audit_line_carries_the_completed_event_it_audits(self):
        self.assertNotIn("for_event", crew_card.record_verdict("t_v", "x", 0, "", 0, by="crew-coordinator"))
        self.assertEqual(12, crew_card.record_verdict("t_v", "x", 0, "", 0, by="crew-coordinator", for_event=12)["for_event"])

    def test_the_claim_time_is_the_newest_claimed_event_before_a_given_event(self):
        self.event("claimed", at=100)
        self.event("completed", at=150)
        self.event("claimed", at=200)
        self.assertEqual(200, crew_card.claimed_at("t_v"))
        self.assertEqual(100, crew_card.claimed_at("t_v", before_event_id=2))
        self.assertIsNone(crew_card.claimed_at("t_other"))

    def test_the_rework_count_starts_again_after_a_coordinator_fix(self):
        self.put(1, ts=1000.0)
        self.put(1, ts=1001.0)
        self.assertEqual(2, crew_card.rework_fails("t_v"))
        self.event("crew_decision", {"decision": "ask_owner"}, at=1500)    # not a fix: the count stands
        self.assertEqual(2, crew_card.rework_fails("t_v"))
        self.event("crew_decision", {"decision": "retry", "fix": "x"}, at=1500)
        self.assertEqual(0, crew_card.rework_fails("t_v"))
        self.put(1, ts=1600.0)
        self.assertEqual(1, crew_card.rework_fails("t_v"))


class LedgerSpentTests(CardTestCase):
    def test_used_and_budget_are_the_highest_over_every_ledger_including_kept_copies(self):
        self.write("crew/budget/t_x.json", json.dumps({"used": 100, "budget": 500}))
        self.write("crew/budget/t_x.json.spent", json.dumps({"used": 900, "budget": 400}))
        self.write("profiles/crew-worker/crew/budget/t_x.json", json.dumps({"used": 300}))
        self.assertEqual((900, 500), crew_card.ledger_spent("t_x"))

    def test_no_ledger_is_zero_and_a_broken_one_is_skipped(self):
        self.assertEqual((0, 0), crew_card.ledger_spent("t_none"))
        self.write("crew/budget/t_bad.json", "not json")
        self.assertEqual((0, 0), crew_card.ledger_spent("t_bad"))


class StatusTests(CardTestCase):
    """/crew-status: the crew cards in flight with the coordinator's last decision and the open question."""

    CREW_BODY = "Role: worker\nCoordinator: crew-coordinator\nGOAL: g\n"

    def setUp(self):
        super().setUp()
        self.db = os.path.join(self.home, "kanban.db")
        os.environ["HERMES_KANBAN_DB"] = self.db
        self.conn = sqlite3.connect(self.db)
        self.conn.executescript(
            "create table tasks (id text, title text, body text, status text, assignee text, created_at integer);"
            "create table task_events (id integer primary key, task_id text, kind text, payload text);")

    def tearDown(self):
        self.conn.close()
        super().tearDown()

    def card(self, cid, status, created, body=None, title=None):
        self.conn.execute("insert into tasks values (?,?,?,?,?,?)",
                          (cid, title or "title " + cid, self.CREW_BODY if body is None else body, status,
                           "crew-worker", created))

    def decide(self, cid, **payload):
        self.conn.execute("insert into task_events (task_id, kind, payload) values (?, 'crew_decision', ?)",
                          (cid, json.dumps(payload)))

    def test_no_board_no_cards_and_only_finished_cards_all_say_nothing_in_flight(self):
        self.conn.close()
        os.remove(self.db)
        os.environ.pop("HERMES_KANBAN_DB")
        self.assertIsNone(crew_card.status_cards())
        self.assertEqual("no cards in flight", crew_card.status_text())
        self.conn = sqlite3.connect(self.db)
        self.conn.executescript("create table tasks (id text, title text, body text, status text, assignee text, created_at integer);"
                                "create table task_events (id integer primary key, task_id text, kind text, payload text);")
        os.environ["HERMES_KANBAN_DB"] = self.db
        self.card("t_done", "done", 1)
        self.conn.commit()
        self.assertEqual("no cards in flight", crew_card.status_text())

    def test_only_crew_cards_in_flight_newest_first(self):
        self.card("t_old", "running", 1)
        self.card("t_new", "blocked", 3)
        self.card("t_plain", "ready", 2, body="buy milk")
        self.card("t_done", "done", 4)
        self.conn.commit()
        cards, total = crew_card.status_cards()
        self.assertEqual((["t_new", "t_old"], 2), ([c["id"] for c in cards], total))

    def test_the_last_decision_is_shown_and_the_question_only_while_blocked_on_it(self):
        self.card("t_ask", "blocked", 1)
        self.card("t_fixed", "running", 2)
        self.decide("t_ask", decision="retry", fix="old fix")
        self.decide("t_ask", decision="ask_owner", question="Which repo?")
        self.decide("t_fixed", decision="ask_owner", question="stale question")     # the owner answered; card runs again
        self.decide("t_fixed", decision="retry", fix="use the other port")
        self.conn.commit()
        text = crew_card.status_text()
        self.assertIn("Coordinator: ask_owner - Which repo?", text)
        self.assertIn("Needs you: Which repo?", text)
        self.assertIn("Coordinator: retry - use the other port", text)
        self.assertNotIn("stale question", text)

    def test_running_card_with_an_old_ask_owner_decision_is_not_waiting_on_the_owner(self):
        self.card("t_run", "running", 1)
        self.decide("t_run", decision="ask_owner", question="Which repo?")
        self.conn.commit()
        self.assertNotIn("Needs you", crew_card.status_text())

    def test_a_later_block_without_a_new_decision_is_not_the_old_question(self):
        self.card("t_reblock", "blocked", 1)
        self.decide("t_reblock", decision="ask_owner", question="Which repo?")
        self.conn.execute("insert into task_events (task_id, kind, payload) values ('t_reblock', 'blocked', '{}')")
        self.conn.commit()
        text = crew_card.status_text()
        self.assertIn("Coordinator: ask_owner", text)
        self.assertNotIn("Needs you", text)

    def test_more_than_the_limit_says_how_many_are_left(self):
        for i in range(10):
            self.card("t_%02d" % i, "ready", i)
        self.conn.commit()
        text = crew_card.status_text(8)
        self.assertEqual(8, text.count("ID: "))
        self.assertIn("open cards: 10", text)
        self.assertIn("(+2 more)", text)


class DecisionDetailTests(unittest.TestCase):
    """One reader orders a `crew_decision`'s substance: fix, question, why, problem (graph, diagnose, status)."""

    def test_one_reader_orders_fix_question_why_problem(self):
        self.assertEqual("f", crew_card.decision_detail({"fix": "f", "question": "q", "why": "w"}))
        self.assertEqual("q", crew_card.decision_detail({"question": "q", "why": "w"}))
        self.assertEqual("p", crew_card.decision_detail({"problem": "p"}))
        self.assertEqual("", crew_card.decision_detail({"decision": "verify"}))
        self.assertEqual("", crew_card.decision_detail(None))
        self.assertEqual("x" * 10, crew_card.decision_detail({"fix": "x" * 50}, 10))


if __name__ == "__main__":
    unittest.main()


class FirstPassTests(unittest.TestCase):
    """'Passed first try' is about the independent check, never the writer's own run (t_d3c396cd, 2026-10-03)."""

    def lines(self, *pairs):
        return [{"by": by, "verdict": v, "ts": i} for i, (by, v) in enumerate(pairs)]

    def test_a_writer_pass_then_an_audit_fail_is_not_a_first_try_pass(self):
        with mock.patch.object(crew_card, "all_verdicts",
                               lambda cid: self.lines(("crew-worker", "PASS"), ("crew-coordinator", "FAIL"))):
            fp = crew_card.first_pass("t_x")
        self.assertEqual((False, 0, 1), (fp["first_pass"], fp["passes"], fp["fails"]))

    def test_the_first_judge_pass_counts_and_writer_lines_are_ignored(self):
        with mock.patch.object(crew_card, "all_verdicts",
                               lambda cid: self.lines(("crew-worker", "FAIL"), ("crew-verifier", "PASS"))):
            self.assertTrue(crew_card.first_pass("t_x")["first_pass"])

    def test_no_judge_run_yet_is_no_chip(self):
        with mock.patch.object(crew_card, "all_verdicts", lambda cid: self.lines(("crew-worker", "PASS"))):
            self.assertEqual({}, crew_card.first_pass("t_x"))
