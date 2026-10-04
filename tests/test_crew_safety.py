#!/usr/bin/env python3
"""scripts/crew_safety.py and the places that run a proof through it.

The detector tests use Hermes's real detectors (tools.approval_detection), never a stand-in: what a proof
may do is whatever Hermes says today. Boards are throwaway sqlite files; no live board and no `hermes` CLI.
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
os.environ.setdefault("HERMES_BIN", "/bin/false")

import crew_card  # noqa: E402
import crew_heal  # noqa: E402
import crew_safety  # noqa: E402


class SafetyCase(unittest.TestCase):
    """A fresh HERMES_HOME and board per test; the environment is restored afterwards."""

    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-safety-test-")
        self.db = os.path.join(self.home, "kanban.db")
        os.environ.update(HERMES_HOME=self.home, HERMES_KANBAN_DB=self.db)
        os.environ.pop("CREW_PROFILE_PREFIX", None)
        for k in ("HERMES_KANBAN_TASK", "CREW_COORDINATOR_TURN"):
            os.environ.pop(k, None)
        # tirith resolves its binary under HERMES_HOME/bin and tries to install it into this scratch home
        # (11 s a call); the pattern detectors under test are Hermes's real ones, tirith is not what these test
        crew_safety._hermes()
        patch = mock.patch("tools.tirith_security.check_command_security", return_value={"action": "allow"})
        patch.start()
        self.addCleanup(patch.stop)
        conn = sqlite3.connect(self.db)
        conn.executescript(
            "create table tasks (id text primary key, title text, status text, assignee text, body text);"
            "create table task_events (id integer primary key autoincrement, task_id text, run_id integer,"
            " kind text, payload text, created_at integer);")
        conn.commit()
        conn.close()

    def tearDown(self):
        for key in [k for k in os.environ if k not in self._env]:
            del os.environ[key]
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)

    def card(self, cid="t_s", body="Role: worker\nCoordinator: c\nGOAL: g\nproof command: true\n", status="running"):
        conn = sqlite3.connect(self.db)
        conn.execute("insert into tasks values (?, 't', ?, 'crew-worker', ?)", (cid, status, body))
        conn.commit()
        conn.close()

    def event(self, cid, kind, payload):
        conn = sqlite3.connect(self.db)
        conn.execute("insert into task_events (task_id, kind, payload, created_at) values (?,?,?,1)",
                     (cid, kind, json.dumps(payload)))
        conn.commit()
        conn.close()

    def snap(self, cid, cmd, mode=None):
        crew_card.record_origin(cid, env={"origin": "", "session": "s"}, proof_cmd=cmd, proof_mode=mode)

    def verdict_args(self, cid="t_s", command=None):
        return argparse.Namespace(card=cid, command=command, timeout=20, no_hand_back=True, by="crew-worker",
                                  for_event=None)


class RunnerTests(SafetyCase):
    def test_a_hardline_command_is_blocked_even_in_brave_mode_and_nothing_runs(self):
        res = crew_safety.run_proof("rm -rf /", None, 5, "brave")
        self.assertEqual(crew_safety.BLOCKED_RC, res.rc)
        self.assertIn("hardline", res.blocked)
        self.assertIn("recursive delete of root filesystem", res.blocked)

    def test_a_flagged_rm_is_blocked_in_safe_mode_and_runs_in_brave_mode(self):
        victim = os.path.join(self.home, "victim")
        os.makedirs(victim)
        cmd = "rm -rf %s" % os.path.join(self.home, "victim")
        ok, why = crew_safety.check_proof(cmd, "safe")
        self.assertFalse(ok)
        self.assertIn("flagged by Hermes as dangerous", why)
        res = crew_safety.run_proof(cmd, None, 20, "safe")
        self.assertTrue(res.blocked)
        self.assertTrue(os.path.isdir(victim))                       # anchor: blocked means it was not deleted
        res = crew_safety.run_proof(cmd, None, 20, "brave")
        self.assertEqual(("", 0), (res.blocked, res.rc))
        self.assertFalse(os.path.exists(victim))                     # anchor: brave means it was

    def test_a_plain_proof_runs_and_reports_its_exit_code_and_output(self):
        res = crew_safety.run_proof("echo hi; exit 3", None, 20, "safe")
        self.assertEqual((3, "hi\n", ""), tuple(res))
        self.assertEqual(124, crew_safety.run_proof("sleep 5", None, 1, "safe").rc)

    def test_a_user_deny_rule_blocks_even_in_brave_mode(self):
        with mock.patch("tools.approval_context._get_approval_config", return_value={"deny": ["echo secret*"]}):
            ok, why = crew_safety.check_proof("echo secret-stuff", "brave")
        self.assertFalse(ok)
        self.assertIn("approvals.deny", why)

    def test_hermes_missing_fails_closed_and_the_env_falls_back_to_the_allowlist(self):
        with mock.patch.object(crew_safety, "_hermes", side_effect=ImportError("no hermes")):
            ok, why = crew_safety.check_proof("true", "brave")
            env = crew_safety.proof_env()
        self.assertFalse(ok)
        self.assertIn("could not be loaded", why)
        self.assertIn("PATH", env)

    def test_the_proof_env_drops_provider_keys_and_keeps_what_the_crew_scripts_need(self):
        os.environ.update(ANTHROPIC_API_KEY="sk-ant-x", OPENROUTER_API_KEY="sk-or-x")
        for env in (crew_safety.proof_env(),):
            self.assertNotIn("ANTHROPIC_API_KEY", env)
            self.assertNotIn("OPENROUTER_API_KEY", env)
            self.assertEqual(self.home, env["HERMES_HOME"])
            self.assertEqual(self.db, env["HERMES_KANBAN_DB"])
            self.assertIn("PATH", env)
            self.assertIn("HOME", env)
        with mock.patch.object(crew_safety, "_hermes", side_effect=ImportError):
            fallback = crew_safety.proof_env()
        self.assertNotIn("ANTHROPIC_API_KEY", fallback)
        self.assertEqual(self.db, fallback["HERMES_KANBAN_DB"])
        out = crew_safety.run_proof("env", None, 20, "safe").out                  # what a proof itself sees
        self.assertNotIn("ANTHROPIC_API_KEY", out)
        self.assertNotIn("OPENROUTER_API_KEY", out)
        self.assertIn("HERMES_KANBAN_DB=%s" % self.db, out)


class ModeTests(SafetyCase):
    def profile(self, mode):
        d = os.path.join(self.home, "profiles", "crew-coordinator")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "config.yaml"), "w") as fh:
            fh.write("approvals:\n  mode: %s\n  timeout: 300\ncrew:\n  role: coordinator\n" % mode)

    def test_safe_unless_the_card_snapshot_or_the_coordinator_profile_says_brave(self):
        self.snap("t_s", "true")
        self.assertEqual("safe", crew_safety.proof_mode("t_s"))
        self.profile("manual")
        self.assertEqual("safe", crew_safety.proof_mode("t_s"))
        self.event("t_s", "proof_confirm", {"proof_cmd": "true", "proof_mode": "brave", "by": "owner"})
        self.assertEqual("brave", crew_safety.proof_mode("t_s"))               # the owner's per-card answer

    def test_approvals_mode_off_on_the_coordinator_profile_is_brave_for_every_card(self):
        self.profile("off")
        self.snap("t_s", "true")
        self.assertEqual(("brave", "brave"), (crew_safety.proof_mode("t_s"), crew_safety.permanent_mode()))
        os.remove(os.path.join(self.home, "profiles", "crew-coordinator", "config.yaml"))
        self.profile("smart")
        self.assertEqual("safe", crew_safety.permanent_mode())


class VerdictTests(SafetyCase):
    def test_a_card_with_no_snapshot_fails_with_no_owner_confirmed_proof_command(self):
        self.card(body="Role: worker\nCoordinator: c\nGOAL: g\nproof command: touch %s/ran\n" % self.home)
        self.assertEqual(1, crew_card.cmd_verdict(self.verdict_args()))
        line = crew_card.all_verdicts("t_s")[-1]
        self.assertEqual(("FAIL", 1), (line["verdict"], line["rc"]))
        self.assertIn("no owner-confirmed proof command", line["output_head"])
        self.assertFalse(os.path.exists(os.path.join(self.home, "ran")))      # the body line was not executed

    def test_the_verdict_runs_the_snapshot_never_the_body_line_or_an_applied_rescope(self):
        self.card(body="Role: worker\nCoordinator: c\nGOAL: g\nproof command: touch %s/body\n" % self.home)
        self.snap("t_s", "touch %s/snapshot" % self.home)
        self.event("t_s", "crew_decision", {"decision": "rescope", "applied": True,
                                            "proof_cmd": "touch %s/rescoped" % self.home})
        self.assertEqual(0, crew_card.cmd_verdict(self.verdict_args()))
        self.assertEqual(["snapshot"], sorted(n for n in os.listdir(self.home) if n in ("body", "snapshot", "rescoped")))

    def test_command_is_accepted_only_when_it_equals_the_snapshot(self):
        self.card()
        self.snap("t_s", "true")
        self.assertEqual(4, crew_card.cmd_verdict(self.verdict_args(command="touch %s/other" % self.home)))
        self.assertFalse(os.path.exists(os.path.join(self.home, "other")))
        self.assertEqual([], crew_card.all_verdicts("t_s"))                     # a refusal is not a verdict line
        self.assertEqual(0, crew_card.cmd_verdict(self.verdict_args(command="true")))

    def test_a_blocked_proof_exits_blocked_and_writes_no_verdict_line(self):
        self.card()
        self.snap("t_s", "rm -rf build-output")
        self.assertEqual(crew_card.PROOF_BLOCKED, crew_card.cmd_verdict(self.verdict_args()))
        self.assertEqual([], crew_card.all_verdicts("t_s"))
        self.event("t_s", "proof_confirm", {"proof_cmd": "rm -rf build-output", "proof_mode": "brave",
                                            "by": "owner"})
        self.assertEqual(0, crew_card.cmd_verdict(self.verdict_args()))         # brave for this card: it ran
        self.assertEqual("PASS", crew_card.all_verdicts("t_s")[-1]["verdict"])


class ApprovedFlaggedTests(SafetyCase):
    PY = 'python3 -c "print(1)"'

    def test_proof_check_verb_uses_the_real_detectors(self):
        self.assertTrue(crew_safety.proof_check(self.PY).startswith("flagged: script execution"))
        self.assertEqual("ok", crew_safety.proof_check("test -f x"))
        self.assertTrue(crew_safety.proof_check("rm -rf /").startswith("hardline: "))

    def test_a_flagged_command_is_not_approved_by_the_intake_line_but_runs_brave_via_the_owner(self):
        self.card()
        crew_card.finish_card("t_s", {"proof_cmd": self.PY, "proof_approved": True}, "crew-worker",
                              env={"origin": "", "session": "s"}, pinned=True)
        self.assertEqual("safe", crew_safety.proof_mode("t_s", self.PY))     # the body line is ignored when flagged
        self.assertIn("script execution", crew_safety.run_proof(self.PY, None, 20, "safe").blocked)
        # the owner's /crew-proof brave is what lets a flagged command run, never the intake body line
        self.event("t_s", "proof_confirm", {"proof_cmd": self.PY, "proof_mode": "brave", "by": "owner"})
        self.assertEqual("brave", crew_safety.proof_mode("t_s", self.PY))
        self.assertEqual(0, crew_safety.run_proof(self.PY, None, 20, "brave").rc)

    def test_an_unapproved_card_is_blocked_and_approval_never_passes_the_hardline(self):
        self.card()
        self.snap("t_s", self.PY)
        self.assertEqual("safe", crew_safety.proof_mode("t_s", self.PY))
        self.assertTrue(crew_safety.run_proof(self.PY, None, 20, "safe").blocked)
        self.card("t_h")
        crew_card.finish_card("t_h", {"proof_cmd": "rm -rf /", "proof_approved": True}, "crew-worker",
                              env={"origin": "", "session": "s"}, pinned=True)
        mode = crew_safety.proof_mode("t_h", "rm -rf /")
        self.assertEqual("safe", mode)                                       # approval never passes the hardline
        self.assertIn("hardline", crew_safety.run_proof("rm -rf /", None, 20, mode).blocked)

    def test_the_intake_line_round_trips_and_a_plan_child_cannot_carry_it(self):
        c = {"role": "worker", "budget": 200000, "goal": "g", "done_when": "d", "proof_cmd": self.PY,
             "coordinator": "c", "proof_approved": True}
        body = crew_card.render_body(c)
        self.assertIn("Proof approved: yes", body)
        self.assertTrue(crew_card.parse_contract(body)["proof_approved"])
        self.assertEqual([], crew_card.unparsed_lines("Proof approved: yes\n"))
        self.assertFalse(crew_card.parse_contract(crew_card.render_body(dict(c, proof_approved=False)))["proof_approved"])


class HealTests(SafetyCase):
    def test_heal_runs_the_snapshot_not_the_body_line(self):
        self.card(status="blocked", body="Role: worker\nCoordinator: c\nproof command: touch %s/body\n" % self.home)
        self.snap("t_s", "touch %s/snapshot" % self.home)
        card = {"id": "t_s", "status": "blocked", "body": crew_card.card_row("t_s")[4]}
        with mock.patch.object(crew_card, "lift_block", return_value={"rc": 0, "status": "ready"}), \
                mock.patch.object(crew_heal, "event", lambda *a, **k: None):
            got = crew_heal.heal_stale_verify(card, False)
        self.assertTrue(got["fixed"])
        self.assertEqual(["snapshot"], sorted(n for n in os.listdir(self.home) if n in ("body", "snapshot")))

    def test_heal_does_nothing_for_a_body_line_with_no_snapshot(self):
        card = {"id": "t_s", "status": "blocked", "body": "proof command: true\n"}
        self.assertIsNone(crew_heal.heal_card(card, False))

    def test_a_blocked_proof_is_reported_blocked_not_as_a_failed_proof(self):
        self.card(status="blocked")
        self.snap("t_s", "rm -rf build-output")
        got = crew_heal.heal_stale_verify({"id": "t_s", "status": "blocked", "body": ""}, False)
        self.assertEqual((False, "rm -rf build-output"), (got["fixed"], got["command"]))
        self.assertIn("flagged by Hermes as dangerous", got["blocked"])


class AnswerTests(SafetyCase):
    def ask(self, cid, proof_ask):
        self.event(cid, "crew_decision", {"decision": "ask_owner", "question": "q", "proof_ask": proof_ask})

    def test_the_owners_yes_confirms_the_proposed_proof_and_rewrites_the_body_line(self):
        self.card(status="blocked")
        self.snap("t_s", "true")
        self.ask("t_s", {"kind": "rescope", "proposed": "test -d ."})
        self.assertEqual({"kind": "rescope", "proposed": "test -d ."}, crew_card.pending_proof_ask("t_s"))
        edits = []
        with mock.patch.object(crew_card, "_kanban", lambda a, **k: edits.append(a)), \
                mock.patch.object(crew_card, "lift_block", return_value={"rc": 0, "status": "ready"}):
            out = crew_card.owner_proof_answer("t_s", brave=False)
        self.assertTrue(out.startswith("confirmed proof for t_s"))
        self.assertEqual("test -d .", crew_card.close_proof_command("t_s"))
        self.assertEqual("", crew_card.proof_snapshot_mode("t_s"))
        self.assertIsNone(crew_card.pending_proof_ask("t_s"))
        self.assertIn("proof command: test -d .", edits[0][3])

    def test_brave_on_a_blocked_proof_records_the_mode_and_a_plain_yes_is_not_enough(self):
        self.card(status="blocked")
        self.snap("t_s", "rm -rf build-output")
        self.ask("t_s", {"kind": "blocked", "command": "rm -rf build-output", "reason": "flagged"})
        self.assertIn("/crew-proof t_s brave", crew_card.owner_proof_answer("t_s", brave=False))
        with mock.patch.object(crew_card, "lift_block", return_value={"rc": 0, "status": "ready"}):
            out = crew_card.owner_proof_answer("t_s", brave=True)
        self.assertTrue(out.startswith("confirmed proof for t_s"))
        self.assertEqual("brave", crew_card.proof_snapshot_mode("t_s"))
        self.assertEqual("rm -rf build-output", crew_card.close_proof_command("t_s"))

    def test_an_answer_from_inside_a_card_run_is_refused(self):
        self.card(status="blocked")
        self.snap("t_s", "true")
        self.ask("t_s", {"kind": "rescope", "proposed": "touch pwned"})
        for var in ("HERMES_KANBAN_TASK", "CREW_COORDINATOR_TURN"):
            with mock.patch.dict(os.environ, {var: "1"}):
                self.assertIn("refused", crew_card.owner_proof_answer("t_s", brave=True))
        self.assertEqual("true", crew_card.close_proof_command("t_s"))


class PlanTests(SafetyCase):
    def test_a_plans_closeout_card_is_its_own_snapshot_and_a_child_cannot_choose_brave(self):
        opened = []
        made = iter(["t_parent", "t_close"])
        with mock.patch.object(crew_card, "create_card", lambda *a, **k: {"id": next(made)}), \
                mock.patch.object(crew_card, "_kanban", lambda *a, **k: mock.Mock(returncode=0)), \
                mock.patch.object(crew_card, "open_card",
                                  lambda c, **k: (opened.append(c) or {"id": "t_child"})):
            self.card("t_close")
            res = crew_card.run_plan({"title": "p", "children": [
                {"title": "a", "goal": "g", "artifact": "a", "lands": "l", "audience": "o", "done_when": "d",
                 "proof_cmd": "true", "role": "worker", "proof_mode": "brave"}]})
        self.assertNotIn("proof_mode", opened[0])
        self.assertEqual("t_close", res["closeout"]["id"])
        self.assertEqual("python3 %s closeout --cards t_child" % crew_card.SELF,
                         crew_card.close_proof_command("t_close"))


class ContractTests(SafetyCase):
    def test_the_intake_proof_mode_line_round_trips_into_the_snapshot(self):
        c = {"role": "worker", "budget": 200000, "goal": "g", "done_when": "d", "proof_cmd": "true",
             "coordinator": "c", "proof_mode": "brave"}
        body = crew_card.render_body(c)
        self.assertIn("Proof mode: brave", body)
        parsed = crew_card.parse_contract(body)
        self.assertEqual("brave", parsed["proof_mode"])
        self.assertEqual([], crew_card.unparsed_lines("Proof mode: brave\n"))      # a contract line, not an intake note
        self.assertEqual("", crew_card.parse_contract(crew_card.render_body(dict(c, proof_mode="yolo")))["proof_mode"])
        self.card()
        crew_card.finish_card("t_s", parsed, "crew-worker", env={"origin": "", "session": "s"}, pinned=True)
        self.assertEqual(("true", "brave"), (crew_card.close_proof_command("t_s"), crew_card.proof_snapshot_mode("t_s")))


if __name__ == "__main__":
    unittest.main()


class ScriptHashTests(SafetyCase):
    """The proof script is bound at its first run: the writer cannot rewrite it, the coordinator can."""

    def setUp(self):
        super().setUp()
        self.script = os.path.join(self.home, "site", ".crew", "verify.py")
        os.makedirs(os.path.dirname(self.script))
        self.write("import sys; sys.exit(0)\n")
        self.cmd = "python3 %s" % self.script
        self.card()
        self.snap("t_s", self.cmd)

    def write(self, text):
        with open(self.script, "w") as fh:
            fh.write(text)

    def run_it(self):
        return crew_safety.run_proof(self.cmd, None, 20, "safe", card="t_s")

    def test_first_run_records_and_an_unchanged_script_runs_again(self):
        self.assertEqual({}, crew_card.proof_script_hashes("t_s"))
        self.assertEqual(0, self.run_it().rc)
        self.assertEqual(crew_safety.script_hashes(self.cmd), crew_card.proof_script_hashes("t_s"))
        self.assertEqual([self.script], list(crew_card.proof_script_hashes("t_s")))
        self.assertEqual(0, self.run_it().rc)

    def test_an_edited_script_is_blocked_with_the_reason_and_the_verdict_exits_5(self):
        self.run_it()
        self.write("import sys; sys.exit(0)  # now it always passes\n")
        res = self.run_it()
        self.assertEqual((crew_safety.BLOCKED_RC, "proof script changed since it first ran: %s" % self.script),
                         (res.rc, res.blocked))
        self.assertEqual(crew_card.PROOF_BLOCKED, crew_card.cmd_verdict(self.verdict_args()))

    def test_the_coordinator_accepting_the_script_records_the_hash_with_its_reason(self):
        import crew_coordinator as C
        self.run_it()
        self.write("import sys; sys.exit(0)  # stdlib only\n")
        C.accept_script({"id": "t_s"}, "websockets is missing in the proof runner")
        self.assertEqual(0, self.run_it().rc)
        self.assertEqual(["websockets is missing in the proof runner"], crew_card.script_revisions("t_s"))

    def test_a_delegated_revision_lets_the_writer_change_it_once_and_is_then_used_up(self):
        self.run_it()
        crew_card.authorize_script_revision("t_s", "verify.py must not import websockets")
        self.write("import sys; sys.exit(0)  # rewritten by the writer\n")
        self.assertEqual(0, self.run_it().rc)
        self.assertEqual(["verify.py must not import websockets"], crew_card.script_revisions("t_s"))
        self.assertEqual("", crew_card.pending_script_authorization("t_s"))
        self.write("import sys; sys.exit(0)  # a second rewrite\n")
        self.assertEqual(crew_safety.BLOCKED_RC, self.run_it().rc)

    def test_an_audit_followup_carries_the_hashes_and_a_pending_authorization(self):
        self.run_it()
        crew_card.authorize_script_revision("t_s", "allowed")
        self.card("t_f")
        crew_card.carry_script_hashes("t_s", "t_f")
        self.assertEqual(crew_card.proof_script_hashes("t_s"), crew_card.proof_script_hashes("t_f"))
        self.assertEqual("allowed", crew_card.pending_script_authorization("t_f"))
        plain = "t_g"
        self.card(plain)
        self.snap(plain, self.cmd)
        crew_card.carry_script_hashes("t_s", plain)
        self.write("import sys; sys.exit(0)  # rewritten on the follow-up\n")
        self.assertEqual(0, crew_safety.run_proof(self.cmd, None, 20, "safe", card="t_f").rc)

    def test_a_follow_up_without_authorization_cannot_rewrite_the_script(self):
        self.run_it()
        self.card("t_f")
        crew_card.carry_script_hashes("t_s", "t_f")
        self.write("import sys; sys.exit(0)  # rewritten on the follow-up\n")
        self.assertEqual(crew_safety.BLOCKED_RC, crew_safety.run_proof(self.cmd, None, 20, "safe", card="t_f").rc)

    def test_a_changed_script_is_a_coordinator_decision_not_an_owner_question(self):
        import crew_coordinator as C
        self.run_it()
        self.write("import sys; sys.exit(0)  # edited\n")
        card = {"id": "t_s", "body": "Role: worker\n", "status": "blocked"}
        ctx = mock.Mock(dry=False)
        answers = [{"decision": "revise_script", "why": "the edit fixes a real bug"}]
        with mock.patch.object(C, "ask_model", side_effect=lambda *a, **k: (answers[0], "")), \
                mock.patch.object(C, "run_verdict", return_value=(0, "PASS")):
            dec, source, pending = C.resolve_script(ctx, card, [], crew_safety.SCRIPT_CHANGED + self.script)
        self.assertEqual("close", dec["decision"])
        self.assertEqual(["the edit fixes a real bug"], crew_card.script_revisions("t_s"))
        self.assertEqual(0, self.run_it().rc)
        self.assertEqual("", C.check_decision({"decision": "revise_script", "why": "x", "delegate": True}))
        self.assertIn("why", C.check_decision({"decision": "revise_script"}))
