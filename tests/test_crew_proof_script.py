#!/usr/bin/env python3
"""Proof scripts belong to the verifier: the writer guard on `.crew/`, the verifier's one write, and the
coordinator's `revise_script` delegation to the verifier. The guard runs against the installed role profile names
(crew-worker, crew-content, crew-verifier, crew-coordinator) when they exist on this machine, else against a scratch
home that carries the same `crew: role:` config line."""
import importlib.util
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
import crew_safety  # noqa: E402

PROFILES = Path(os.path.expanduser("~/.hermes/profiles"))
SCRIPT = "/srv/site/.crew/verify.py"


def load_plugin(home):
    """The plugin module with HERMES_HOME=home (it reads HOME and the role at import time)."""
    with mock.patch.dict(os.environ, {"HERMES_HOME": str(home)}):
        spec = importlib.util.spec_from_file_location("crew_plugin_proof_script_test", str(REPO / "__init__.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod


class GuardCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="crew-script-guard-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self._env = dict(os.environ)
        for k in ("HERMES_KANBAN_TASK", "CREW_COORDINATOR_TURN"):
            os.environ.pop(k, None)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self._env)))

    def plugin_for(self, role):
        installed = PROFILES / ("crew-" + role)
        if (installed / "config.yaml").exists():
            return load_plugin(installed), "installed crew-%s" % role
        home = Path(self.tmp) / role
        home.mkdir()
        (home / "config.yaml").write_text("crew:\n  role: %s\n" % role)
        return load_plugin(home), "scratch %s" % role

    def call(self, role, tool, args):
        plug, _where = self.plugin_for(role)
        os.environ["HERMES_KANBAN_TASK"] = "t_none"     # a spawned card run
        with mock.patch.object(plug, "_card_budget", lambda card: None), \
                mock.patch.object(plug, "_verdict_fails", lambda card: 0):
            return plug.crew_tool_guard(tool_name=tool, args=args, session_id="s", turn_id="t")


class WriterGuardTests(GuardCase):
    WRITES = (
        ("write_file", {"path": SCRIPT, "content": "x"}),
        ("write_file", {"path": ".crew/verify.py", "content": "x"}),
        ("patch", {"path": SCRIPT, "old_string": "a", "new_string": "b"}),
        ("patch", {"mode": "patch", "patch": "*** Begin Patch\n*** Update File: /srv/site/.crew/verify.py\n@@\n-a\n+b\n*** End Patch"}),
        ("terminal", {"command": "echo 'import sys' > /srv/site/.crew/verify.py"}),
        ("terminal", {"command": "cd /srv/site && cp /tmp/v.py .crew/verify.py"}),
        ("terminal", {"command": "sed -i 's/a/b/' /srv/site/.crew/verify.py"}),
    )

    def test_a_writer_cannot_write_patch_or_terminal_write_under_crew_dir(self):
        for role in ("worker", "content"):
            for tool, args in self.WRITES:
                with self.subTest(role=role, tool=tool, args=args):
                    res = self.call(role, tool, args)
                    self.assertEqual("block", (res or {}).get("action"))
                    self.assertIn("proof files belong to the verifier", res["message"])

    def test_a_writer_can_read_crew_dir_and_write_elsewhere(self):
        for role in ("worker", "content"):
            for tool, args in (("read_file", {"path": SCRIPT}),
                               ("terminal", {"command": "cat /srv/site/.crew/verify.py"}),
                               ("terminal", {"command": "python3 /srv/site/.crew/verify.py 2>&1 | tail -5"}),
                               ("write_file", {"path": "/srv/site/index.html", "content": "x"}),
                               ("terminal", {"command": "echo hi > /srv/site/index.html"})):
                with self.subTest(role=role, tool=tool, args=args):
                    self.assertIsNone(self.call(role, tool, args))

    def test_the_verifier_writes_only_under_crew_dir_and_the_coordinator_turn_is_unchanged(self):
        self.assertIsNone(self.call("verifier", "write_file", {"path": SCRIPT, "content": "x"}))
        self.assertIsNone(self.call("verifier", "patch", {"path": SCRIPT, "old_string": "a", "new_string": "b"}))
        for tool, args in (("write_file", {"path": "/srv/site/index.html", "content": "x"}),
                           ("patch", {"mode": "patch", "patch": "*** Update File: /srv/site/.crew/v.py\n"
                                                                  "*** Update File: /srv/site/index.html\n"}),
                           ("terminal", {"command": "echo x > /srv/site/.crew/verify.py"}),
                           ("write_file", {"path": "", "content": "x"})):
            with self.subTest(tool=tool, args=args):
                self.assertEqual("block", (self.call("verifier", tool, args) or {}).get("action"))
        os.environ["CREW_COORDINATOR_TURN"] = "1"
        self.assertEqual("block", self.call("coordinator", "write_file", {"path": SCRIPT, "content": "x"})["action"])


class CoerceVerifyTests(unittest.TestCase):
    def contract(self, proof, verify=""):
        return {"role": "worker", "goal": "g", "artifact": "a", "lands": "/srv/site", "audience": "me",
                "done_when": "d", "proof_cmd": proof, "verify": verify, "budget": 500000, "coordinator": "p/s"}

    def test_script_proof_is_independent_whatever_was_asked_and_command_only_stays_proof(self):
        for verify in ("", "proof", "independent"):
            self.assertEqual("independent", crew_card.default_verify(self.contract("python3 %s" % SCRIPT, verify)))
        for cmd in ("test -f /srv/site/index.html && grep -q Hello /srv/site/index.html", "curl -sf http://127.0.0.1/"):
            self.assertEqual("proof", crew_card.default_verify(self.contract(cmd)))
            self.assertEqual("proof", crew_card.default_verify(self.contract(cmd, "proof")))
        self.assertEqual("independent", crew_card.default_verify(self.contract("")))
        self.assertEqual("closeout", crew_card.default_verify(self.contract("python3 %s" % SCRIPT, "closeout")))

    def test_the_card_reads_independent_even_with_a_proof_line_and_the_verifier_closes_it(self):
        body = crew_card.render_body(self.contract("python3 %s" % SCRIPT, "proof"))
        self.assertIn("Verify: independent", body)
        legacy = body.replace("Verify: independent", "Verify: proof")
        self.assertEqual("independent", crew_card.verify_mode(legacy))
        self.assertIn(crew_card.profile_prefix() + "verifier", crew_card.closer_profiles(legacy))
        self.assertNotIn(crew_card.profile_prefix() + "worker", crew_card.closer_profiles(legacy))
        self.assertEqual("independent", crew_card.verify_mode("Role: worker\nVerify: proof\nproof command: python3 .crew/v.py\n"))


class ReviseScriptTests(unittest.TestCase):
    """revise_script with delegate: the verifier, never the writer."""

    def setUp(self):
        import crew_coordinator as cc
        self.cc = cc
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-revise-")
        self.db = os.path.join(self.home, "kanban.db")
        os.environ.update(HERMES_HOME=self.home, HERMES_KANBAN_DB=self.db)
        conn = sqlite3.connect(self.db)
        conn.executescript(
            "create table tasks (id text primary key, title text, status text, assignee text, body text);"
            "create table task_events (id integer primary key autoincrement, task_id text, run_id integer,"
            " kind text, payload text, created_at integer);")
        conn.commit()
        conn.close()
        self.script = os.path.join(self.home, "site", ".crew", "verify.py")
        os.makedirs(os.path.dirname(self.script))
        self.write("import sys; sys.exit(0)\n")
        self.cmd = "python3 %s" % self.script
        self.body = ("Role: worker\nCoordinator: c\nVerify: independent\nGOAL: g\nproof command: %s\n" % self.cmd)
        conn = sqlite3.connect(self.db)
        conn.execute("insert into tasks values ('t_r', 't', 'blocked', 'crew-worker', ?)", (self.body,))
        conn.commit()
        conn.close()
        crew_card.record_origin("t_r", env={"origin": "", "session": "s"}, proof_cmd=self.cmd)
        self.cli = []

        def fake_kanban(args, timeout=120):
            self.cli.append(list(args))
            return mock.Mock(returncode=0, stdout="ok", stderr="")
        self.card = {"id": "t_r", "title": "t", "status": "blocked", "body": self.body}
        self.ctx = cc.Ctx(self.db, None, dry=False, say=lambda *_: None)
        for p in (mock.patch.object(crew_card, "_kanban", fake_kanban),
                  mock.patch.object(crew_card, "repin_for_review", lambda cid: {"action": "unchanged"}),
                  mock.patch.object(crew_card, "retry_card",
                                    lambda *a, **k: {"ok": True, "budget": 1, "unblock": {"rc": 0, "status": "ready"}}),
                  mock.patch.object(crew_card, "lift_into_review",
                                    lambda cid, reviewer, summary: self.cli.append(["request-review", cid, "--reviewer",
                                                                                    reviewer]) or (True, reviewer)),
                  mock.patch.object(cc, "kanban", lambda *a, **k: (0, "ok"))):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self._env)))
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)

    def write(self, text):
        with open(self.script, "w") as fh:
            fh.write(text)

    def hashes_events(self):
        conn = sqlite3.connect(self.db)
        rows = [json.loads(r[0]) for r in conn.execute(
            "select payload from task_events where task_id = 't_r' and kind = 'proof_script_hash' order by id")]
        conn.close()
        return rows

    def test_delegate_authorizes_the_verifier_and_requests_its_review_not_a_writer_run(self):
        crew_safety.run_proof(self.cmd, None, 20, "safe", card="t_r")          # first run binds the script
        self.write("import sys; sys.exit(0)  # edited\n")
        dec = {"decision": "revise_script", "why": "must not import websockets", "delegate": True}
        ok, out = self.cc.apply_decision(self.ctx, self.card, [], dec)
        self.assertTrue(ok, out)
        self.assertIn("sent to the verifier", out)
        reviews = [c for c in self.cli if c[0] == "request-review"]
        self.assertEqual(1, len(reviews))
        self.assertEqual(["--reviewer", crew_card.role_profile("verifier")], reviews[0][2:4])
        self.assertEqual("must not import websockets", crew_card.pending_script_authorization("t_r"))
        # the writer is not the one authorized: the authorization is consumed by the verifier's run, by=verifier
        crew_card._append_card_event("t_r", "crew_decision", dict(dec, applied=True))
        decision = crew_card.decision_id("t_r", "revise_script")
        self.write("import sys; sys.exit(0)  # rewritten by the verifier\n")
        self.assertEqual(0, crew_safety.run_proof(self.cmd, None, 20, "safe", card="t_r").rc)
        last = self.hashes_events()[-1]
        self.assertEqual(("verifier", "must not import websockets", decision),
                         (last["by"], last["why"], last["authorized_by"]))
        self.assertEqual(["must not import websockets"], crew_card.script_revisions("t_r"))

    def test_the_card_names_the_verifier_in_its_proof_script_line_and_no_writer_path_is_left(self):
        dec = {"decision": "revise_script", "why": "stdlib only", "delegate": True}
        with mock.patch.object(self.cc.crew_card, "retry_card") as retry:
            retry.return_value = {"ok": True, "budget": 1, "unblock": {"rc": 0, "status": "ready"}}
            self.cc.apply_decision(self.ctx, self.card, [], dec)
        self.assertIn("Proof script: verifier to revise - stdlib only", retry.call_args.kwargs["body"])
        self.assertFalse(retry.call_args.kwargs["unblock"])        # send_to_verifier lifts it, in the same step as the review
        self.assertNotIn("may revise", retry.call_args.kwargs["body"])
        self.assertNotIn("writer", self.cc.PROMPT.split("revise_script")[1].split("ask_owner")[0])

    def test_a_card_that_cannot_reach_the_verifier_is_refused_for_the_owner_question(self):
        with mock.patch.object(crew_card, "send_to_verifier", return_value={"ok": False, "why": "not in ready"}):
            ok, out = self.cc.apply_decision(self.ctx, self.card, [], {"decision": "revise_script", "why": "x",
                                                                       "delegate": True})
        self.assertFalse(ok)
        self.assertIn("not in ready", out)

    def test_an_accepted_script_without_delegate_still_records_the_coordinator_and_asks_nobody(self):
        self.write("import sys; sys.exit(0)  # edited\n")
        ok, out = self.cc.apply_decision(self.ctx, self.card, [], {"decision": "revise_script", "why": "fine"})
        self.assertTrue(ok, out)
        self.assertEqual([], [c for c in self.cli if c[0] == "request-review"])
        self.assertEqual("coordinator", self.hashes_events()[-1]["by"])


if __name__ == "__main__":
    unittest.main()


class OneScriptPerCardTests(unittest.TestCase):
    """Two cards in one folder must not share a proof script (2026-10-03)."""

    def test_a_script_another_open_card_uses_is_a_contract_gap(self):
        with mock.patch.object(crew_card, "kanban_db", return_value=None):
            self.assertEqual("", crew_card.proof_script_taken("python3 /x/site/.crew/a/verify.py"))
        with mock.patch.object(crew_card, "proof_script_taken", return_value="t_old"):
            gaps = crew_card.contract_gaps({"proof_cmd": "python3 /x/site/.crew/verify.py"})
        self.assertTrue(any("t_old" in g for g in gaps))

    def test_only_crew_scripts_count(self):
        self.assertEqual(["/x/site/.crew/20261003-1-a/verify.py"],
                         crew_card.crew_script_paths("python3 /x/site/.crew/20261003-1-a/verify.py && python3 /x/tool.py"))
