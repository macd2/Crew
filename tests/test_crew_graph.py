"""Unit tests for the card page's own readers - the pieces the right sidebar's steps are built from.

Pure logic only, no board and no browser. The rules pinned here: a card body's `Label: value` lines are
read whatever the label's case; a model pin is labelled once for the whole surface; a card's own fields
come off the CARD node, never off the graph's root (which is the owner brief once one is recorded); a
tool result yields the state, the short reason and the last text its own output produced; and a panel
shows the tail of a run, never without the steps that failed.
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import crew_graph as cg  # noqa: E402
from crew_result import result_row  # noqa: E402


class DecisionLabelTests(unittest.TestCase):
    """The coordinator's decisions as timeline lines (crew_decision events)."""

    def test_each_verb_reads_as_a_plain_line_with_its_detail(self):
        self.assertEqual("coordinator retried it: use tmp", cg.decision_label({"decision": "retry", "fix": "use tmp"}))
        self.assertEqual("coordinator asked the owner: Which branch?",
                         cg.decision_label({"decision": "ask_owner", "question": "Which branch?"}))
        self.assertEqual("coordinator ran the proof", cg.decision_label({"decision": "verify"}))
        self.assertEqual("coordinator could not decide: no JSON",
                         cg.decision_label({"decision": "error", "problem": "no JSON"}))

    def test_a_blocked_audit_is_not_read_as_a_pass(self):
        got = cg.decision_label({"decision": "audit", "outcome": "blocked", "followup": "t_9", "why": "why"})
        self.assertIn("blocked by Hermes safety", got)
        self.assertIn("t_9", got)
        self.assertNotIn("still passes", got)

    def test_an_unknown_verb_is_still_a_line(self):
        self.assertEqual("coordinator decided: new_thing", cg.decision_label({"decision": "new_thing"}))

    def test_a_long_detail_is_cut(self):
        self.assertLessEqual(len(cg.decision_label({"decision": "retry", "fix": "x" * 500})), 100)


class BodyFieldTests(unittest.TestCase):
    """The one reader of a card body's `Label: value` lines, from the card page and the board."""

    def test_a_body_field_is_read_whatever_the_label_case(self):
        # crew_card.py writes `Coordinator:`, but a body that spells it another way must still be
        # read: a case-sensitive reader silently ships an empty value instead of erroring.
        body = "Role: worker\nGoal: x\nCOORDINATOR: owner-chat/s-1\n"
        self.assertEqual("x", cg.body_field(body, "Goal"))
        self.assertEqual("x", cg.body_field(body, "GOAL"))
        self.assertEqual("owner-chat/s-1", cg.body_field(body, "Coordinator"))
        self.assertEqual("worker", cg.body_field(body, "role"))

    def test_only_the_value_is_returned(self):
        body = "Goal: x\nCoordinator: owner-chat/20260929_103439_fc7b7320\nDone when: y\n"
        self.assertEqual("owner-chat/20260929_103439_fc7b7320",
                         cg.body_field(body, "Coordinator"))

    def test_a_card_without_the_line_reads_none(self):
        self.assertIsNone(cg.body_field("Role: worker\nGoal: something\n", "Verifier"))
        self.assertIsNone(cg.body_field("", "Coordinator"))
        self.assertIsNone(cg.body_field(None, "Coordinator"))


class ModelPinTests(unittest.TestCase):
    """The pin's label has one owner, `crew_graph.pin_label`, shared by the card page and the board."""

    def test_the_provider_qualifies_the_model_when_one_is_pinned(self):
        self.assertEqual("gemini/gemini-3-flash-preview",
                         cg.pin_label("gemini-3-flash-preview", "gemini"))

    def test_a_model_without_a_provider_stands_alone(self):
        self.assertEqual("claude-opus-5-5", cg.pin_label("claude-opus-5-5", None))

    def test_an_unpinned_card_reports_nothing(self):
        self.assertEqual("", cg.pin_label(None, "gemini"))
        self.assertEqual("", cg.pin_label("", ""))
        self.assertEqual("", cg.pin_label("   ", "gemini"))


class CardBoxFieldsTests(unittest.TestCase):
    """The first cell's box: the card's own facts, and nothing invented for the ones it lacks."""

    CARD = {"writer_role": "content", "assignee": "crew-content", "block_kind": "",
            "verifier": "crew-verifier", "created_at": 1790697940, "run_count": 2,
            "coordinator": "owner-chat/20260929_174148_86c00e",
            "model_override": "gemini-3-flash-preview", "provider_override": "gemini",
            "spent": 144000, "ceiling": 1500000}

    def test_the_box_carries_the_cards_own_facts(self):
        f = cg.card_box_fields(self.CARD)
        self.assertEqual("content", f["card_role"])
        self.assertEqual("crew-content", f["card_assignee"])
        self.assertEqual("gemini/gemini-3-flash-preview", f["card_model"])
        self.assertEqual("crew-verifier", f["card_verifier"])
        self.assertEqual(1790697940, f["card_created_at"])
        self.assertEqual(2, f["card_run_count"])
        self.assertEqual("owner-chat/20260929_174148_86c00e", f["coordinator"])
        self.assertEqual({"spent": 144000, "ceiling": 1500000}, f["budget"])

    def test_the_roles_coordinator_and_budget_name_the_card_not_a_brief(self):
        # The brief node became the graph's root while the card carries these facts. Handed the brief
        # instead of the card, the box ships a blank coordinator, no role and a zero budget.
        brief = {"assignee": None, "coordinator": None, "spent": None, "ceiling": None}
        f = cg.card_box_fields(self.CARD)
        for key in ("coordinator", "card_role", "card_assignee"):
            self.assertNotEqual(brief.get(key), f[key], key)
        self.assertEqual(144000, f["budget"]["spent"])
        # ...and handed the brief itself those fields are empty rather than invented.
        b = cg.card_box_fields(brief)
        self.assertEqual("", b["coordinator"])
        self.assertIsNone(b["card_role"])
        self.assertEqual({"spent": 0, "ceiling": 0}, b["budget"])

    def test_a_card_with_nothing_recorded_reports_empty_not_a_placeholder(self):
        f = cg.card_box_fields({})
        self.assertEqual("", f["coordinator"])
        self.assertEqual("", f["card_assignee"])
        self.assertEqual("", f["card_model"])
        self.assertEqual("", f["card_block_kind"])
        self.assertEqual("", f["card_verifier"])
        self.assertEqual(0, f["card_run_count"])
        self.assertIsNone(f["card_created_at"])
        self.assertEqual({"spent": 0, "ceiling": 0}, f["budget"])
        self.assertEqual(cg.card_box_fields(None), f)


class ResultOutTests(unittest.TestCase):
    """The last text a step's own output produced: the tail of a run, or the reason it failed."""

    def test_a_terminal_result_gives_its_last_output_line(self):
        raw = json.dumps({"output": "one\ntwo\nrc=0\n", "exit_code": 0, "error": None})
        self.assertEqual(("ok", "", "rc=0"), result_row(raw))

    def test_a_blocked_result_gives_the_reason(self):
        raw = json.dumps({"output": "", "exit_code": -1, "error": "BLOCKED: approval withdrawn"})
        state, note, out = result_row(raw)
        self.assertEqual("err", state)
        self.assertEqual("BLOCKED: approval withdrawn", note)
        self.assertEqual("BLOCKED: approval withdrawn", out)

    def test_a_structured_answer_gives_its_verdict(self):
        raw = json.dumps({"ok": True, "task_id": "t_1", "run_id": 2318})
        self.assertEqual(("ok", "", "ok=true task_id=t_1 run_id=2318"), result_row(raw))

    def test_a_non_json_result_gives_its_text(self):
        self.assertEqual("boom", result_row("boom")[2])

    def test_a_search_result_says_what_it_matched(self):
        """A step whose result is a list of matches must not read as having printed nothing."""
        raw = json.dumps({"total_count": 1, "matches": [
            {"path": "/x/crew_card.py", "line": 551, "content": "CARD_BASE = ..."}]})
        self.assertEqual(("ok", "", "1 matches: /x/crew_card.py:551"), result_row(raw))

    def test_an_empty_result_prints_nothing(self):
        self.assertEqual("", result_row(json.dumps({}))[2])


class TailStepsTests(unittest.TestCase):
    """Which steps a panel shows: the last n, and never without the ones that failed."""

    S = [{"tool": "a", "state": "ok"}, {"tool": "b", "state": "err"}, {"tool": "c", "state": "ok"},
         {"tool": "d", "state": "ok"}, {"tool": "e", "state": "ok"}, {"tool": "f", "state": "ok"},
         {"tool": "g", "state": "ok"}, {"tool": "h", "state": "pending"}]

    def test_the_tail_of_a_clean_run(self):
        clean = [{"tool": t, "state": "ok"} for t in "abcdefgh"]
        self.assertEqual(["f", "g", "h"], [s["tool"] for s in cg.tail_steps(clean, 3)])

    def test_an_old_failure_rides_along(self):
        self.assertEqual(["b", "f", "g", "h"], [s["tool"] for s in cg.tail_steps(self.S, 3)])

    def test_a_short_run_is_left_alone(self):
        self.assertEqual(self.S, cg.tail_steps(self.S, 8))
        self.assertEqual(self.S, cg.tail_steps(self.S, 99))

    def test_nothing_recorded_stays_empty(self):
        self.assertEqual([], cg.tail_steps([], 3))
        self.assertEqual([], cg.tail_steps(None, 3))


class SessionTextTests(unittest.TestCase):
    """The live session view: what the model wrote, and the run -> session mapping that finds it.

    Owner, 2026-09-30: the panel's worker box must show the live session's own text with tool calls
    filtered out, and one box per lane instead of one per run - which only works if a run's session is a
    recorded fact. The worker records it (router plugin, on_session_start), so the reader may not guess.
    """

    def setUp(self):
        import sqlite3
        from tempfile import TemporaryDirectory
        import json as _json
        self._json = _json
        self.tmp = TemporaryDirectory(prefix="crew-text-")
        self.state = os.path.join(self.tmp.name, "state.db")
        db = sqlite3.connect(self.state)
        db.execute("create table messages (id integer primary key autoincrement, session_id text, "
                   "role text, content text, tool_calls text, timestamp real)")
        rows = [
            ("s1", "user", "work kanban task t_x", None),
            ("s1", "assistant", "", '[{"id":"c1","function":{"name":"terminal","arguments":"{}"}}]'),
            ("s1", "tool", '{"output": "lots of tool noise"}', None),
            ("s1", "assistant", "Reading the card, then I will patch the reader.", None),
            ("s1", "assistant", "   ", None),                      # whitespace is not text
            ("s1", "assistant", "Second thought: the guess has to go.", None),
            ("s2", "assistant", "another run's words", None),
        ]
        for sid, role, content, tc in rows:
            db.execute("insert into messages (session_id, role, content, tool_calls, timestamp) "
                       "values (?,?,?,?,?)", (sid, role, content, tc, 100.0))
        db.commit()
        db.close()
        self.board = os.path.join(self.tmp.name, "kanban.db")
        db = sqlite3.connect(self.board)
        db.execute("create table task_events (id integer primary key autoincrement, task_id text, "
                   "run_id integer, kind text, payload text, created_at integer)")
        db.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values "
                   "(?,?,?,?,?)", ("t_x", 7, "session", _json.dumps({"session": "s1"}), 1))
        db.commit()
        db.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_the_models_own_text_comes_back(self):
        lines = cg.load_session_text(self.state, "s1")
        self.assertEqual(["Reading the card, then I will patch the reader.",
                          "Second thought: the guess has to go."], [l["text"] for l in lines])
        self.assertIn("ts", lines[0])

    def test_a_tool_only_message_and_a_result_are_dropped(self):
        texts = [l["text"] for l in cg.load_session_text(self.state, "s1")]
        self.assertNotIn("lots of tool noise", texts)
        self.assertFalse(any(t.strip() == "" for t in texts))

    def test_another_session_stays_separate(self):
        self.assertEqual(["another run's words"],
                         [l["text"] for l in cg.load_session_text(self.state, "s2")])
        self.assertEqual([], cg.load_session_text(self.state, "nope"))
        self.assertEqual([], cg.load_session_text(None, "s1"))

    def test_the_tail_is_capped(self):
        lines = cg.load_session_text(self.state, "s1", max_lines=1)
        self.assertEqual(["Second thought: the guess has to go."], [l["text"] for l in lines])

    def test_the_runs_session_comes_from_the_workers_own_row(self):
        self.assertEqual("s1", cg.exact_session_for_run(self.board, "t_x", 7))

    def test_a_run_without_a_row_is_not_guessed(self):
        self.assertIsNone(cg.exact_session_for_run(self.board, "t_x", 8))
        self.assertIsNone(cg.exact_session_for_run(self.board, "t_other", 7))
        self.assertIsNone(cg.exact_session_for_run(None, "t_x", 7))


class SessionStatusTests(unittest.TestCase):
    """A session's state on the page comes from its own RUN, not from an open ended_at.

    A worker killed outright never writes its session's ended_at, so reading that column alone draws a
    dead session as running for ever: after run 2789 had settled "crashed", the page still showed
    session 20260930_142504_7587cd live (owner, 2026-09-30). The run row is the truth; ended_at is the
    fallback for a session that has no run row at all.
    """

    def test_the_run_row_decides_when_there_is_one(self):
        self.assertEqual("running", cg.session_status(None, "running"))
        for settled in ("done", "blocked", "failed"):
            self.assertEqual("done", cg.session_status(None, settled))

    def test_it_reads_the_pages_own_run_vocabulary(self):
        # run_status() is what builds a run node's state: the two readers must agree, or the page
        # shows a run as crashed and its session as still running.
        self.assertEqual("running", cg.session_status(None, cg.run_status("running", None)))
        for status, outcome in (("crashed", None), ("timed_out", None), ("done", "completed"),
                                ("blocked", "blocked")):
            self.assertEqual("done", cg.session_status(None, cg.run_status(status, outcome)))

    def test_an_open_session_with_no_run_row_is_still_running(self):
        self.assertEqual("running", cg.session_status(None))
        self.assertEqual("done", cg.session_status(1790769127.0))

    def test_a_settled_run_beats_an_open_session_row(self):
        # the exact case the owner saw: ended_at NULL, run already settled
        self.assertEqual("done", cg.session_status(None, "crashed"))


if __name__ == "__main__":
    unittest.main()
