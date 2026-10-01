#!/usr/bin/env python3
"""Proof of two-stage verification: `Verify: proof | independent`, the proof snapshot and the coordinator's audit.

Runs on the SCRATCH board and scratch HERMES_HOME of crew_coordinator_proof.py (the real `hermes kanban` verbs
through its wrapper, the plugin's own guards in-process, the loop's own pass as a subprocess). The live board is
never opened and no model is called: the coordinator's decider is a stub that fails the proof if it is asked.

  A  a `Verify: proof` card is opened through crew_card.py: its origin event carries the proof command snapshot
  B  the proof line is rewritten on the card: the verdict tool still runs the snapshot (FAIL), and neither that
     FAIL nor a hand-written PASS for the rewritten command lets kanban_complete through
  C  the real proof passes: the writer closes it; the loop's pass then re-runs it (by=coordinator) once, with no
     verifier session and no model call - two PASS lines (writer, coordinator)
  D  a card whose proof fails after completion: the audit comments on the done card and opens ONE follow-up card
     (parent = the done card, the audit output under Constraints); a second pass opens nothing more
  E  a `Verify: proof` card refuses kanban_request_review
  F  a `Verify: independent` card: the writer's PASS is not enough, the review run's pin is the router's pick or
     cleared (here: no router, so cleared through the kernel's set-model), the verifier's PASS closes it and the
     audit adds the coordinator's line; exactly one review run

Run:  python3 crew_two_stage_proof.py
Exit: 0 when every check passes, 1 otherwise.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_card  # noqa: E402
import crew_coordinator_proof as cp  # noqa: E402
import crew_proof_board  # noqa: E402

CARD = os.path.join(HERE, "crew_card.py")
check = cp.check


def open_card(title, proof, verify):
    """A card the way production opens one (crew_card.py open: create, then origin with the proof snapshot)."""
    r = subprocess.run([sys.executable, CARD, "open", "--title", title, "--goal", title, "--role", "worker",
                        "--artifact", "a file", "--lands", "scratch", "--audience", "the owner",
                        "--done-when", "the file exists", "--proof-cmd", proof, "--budget", "200000",
                        "--verify", verify, "--json"], env=cp.ENV, capture_output=True, text=True, timeout=300)
    m = re.search(r'"id":\s*"(t_[0-9a-f]+)"', r.stdout or "")
    if not m:
        raise RuntimeError("card not opened: %s" % ((r.stdout or "") + (r.stderr or ""))[-300:])
    return m.group(1)


def verdict(cid, by, command=None):
    args = [sys.executable, CARD, "verdict", "--card", cid, "--by", by, "--no-hand-back"]
    if command:
        args += ["--command", command]
    return subprocess.run(args, env=cp.ENV, capture_output=True, text=True, timeout=300)


def lines(cid):
    path = crew_card.verdict_path(cid)
    try:
        return [json.loads(x) for x in open(path)]
    except OSError:
        return []


def load_plugin():
    spec = importlib.util.spec_from_file_location("crew_plugin_two_stage_proof", os.path.join(os.path.dirname(HERE), "__init__.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    cp.setup()
    for name in ("crew-worker", "crew-coordinator", "crew-verifier"):       # role_profile() names a profile only if it exists
        cp.write(os.path.join(cp.HOME, "profiles", name, "config.yaml"), "crew:\n  role: %s\n" % name[5:])
    os.environ.update(cp.ENV)                          # this process is a crew process on the scratch board too
    os.environ["CREW_ROUTER_PLUGIN"] = os.path.join(cp.TMP, "no-router")      # no router: the pick is empty
    cp.ENV["CREW_ROUTER_PLUGIN"] = os.environ["CREW_ROUTER_PLUGIN"]
    check("the scratch board is not the live board",
          os.path.realpath(cp.DB) != os.path.realpath(os.path.expanduser("~/.hermes/kanban.db")), cp.DB)
    plug = load_plugin()
    cp.coordinator()                                   # initialise the cursor: nothing before this is replayed
    worker = crew_card.role_profile("worker")
    coord = crew_card.role_profile("coordinator")

    # ---- A: the snapshot is taken when the card opens
    target = os.path.join(cp.TMP, "artifact-a.txt")
    proof_a = "test -f %s" % target
    a = open_card("two-stage A", proof_a, "proof")
    check("A: the card opened with `Verify: proof`", crew_card.verify_mode(cp.card(a)["body"]) == "proof",
          crew_card.field(cp.card(a)["body"], "Verify"))
    origin = [json.loads(r["payload"]) for r in cp.rows(
        "select payload from task_events where task_id = ? and kind = 'origin'", (a,))]
    check("A: its origin event carries the proof command as opened", origin and origin[0].get("proof_cmd") == proof_a,
          json.dumps(origin)[:100])

    # ---- B: a rewritten proof line changes nothing
    cp.cli("claim", a)
    r = cp.cli("edit", a, "--body", re.sub(r"(?m)^proof command:.*$", "proof command: true", cp.card(a)["body"]))
    check("B: the proof line on the card is rewritten to `true`",
          crew_card.proof_cmd(cp.card(a)["body"]) == "true", "rc=%d" % r.returncode)
    v = verdict(a, worker)
    check("B: the verdict tool still runs the snapshot: FAIL, and says the line differs",
          v.returncode == 1 and "differs from the one the card opened with" in v.stdout and
          lines(a)[-1]["command"] == proof_a and lines(a)[-1]["verdict"] == "FAIL", v.stdout.strip().splitlines()[-1][:80])
    crew_card.record_verdict(a, "true", 0, "hand-written", 0, by=worker)          # a PASS for the rewritten command
    g = plug._close_guard("kanban_complete", {"task_id": a})
    check("B: neither the FAIL nor a hand-written PASS for the rewritten command lets kanban_complete through",
          g and g["action"] == "block" and proof_a in g["message"], (g or {}).get("message", "allowed")[:110])

    # ---- C: the real proof passes, the writer closes, the loop audits
    open(target, "w").write("x")
    v = verdict(a, worker)
    g = plug._close_guard("kanban_complete", {"task_id": a})
    check("C: with the real proof passing the writer's PASS lets kanban_complete through",
          v.returncode == 0 and g is None, "rc=%d guard=%s" % (v.returncode, g))
    cli_done = cp.cli("complete", a, "--summary", "artifact written; proof PASS")
    calls = cp.model_calls()
    rep = cp.coordinator()
    by = [l["by"] for l in lines(a) if l["verdict"] == "PASS" and l["command"] == proof_a]
    check("C: two PASS lines for the proof command, the writer's then the coordinator's",
          by == [worker, coord], str(by))
    ds = cp.decisions(a)
    check("C: one `audit` decision (pass) carries the completed event id, no model call, no owner_close",
          cli_done.returncode == 0 and len(ds) == 1 and ds[0]["decision"] == "audit" and ds[0]["outcome"] == "pass"
          and ds[0]["for_event"] == cp.newest_event(a, "completed") and cp.model_calls() == calls,
          json.dumps(ds)[:110])
    check("C: no verifier session ever ran on it (no review_requested event, no verifier run)",
          not cp.rows("select 1 from task_events where task_id = ? and kind = 'review_requested'", (a,)) and
          not cp.rows("select 1 from task_runs where task_id = ? and profile like '%verifier'", (a,)), "")
    cp.coordinator()
    check("C: a second pass audits nothing again",
          len(cp.decisions(a)) == 1 and len([l for l in lines(a) if l["by"] == coord]) == 1,
          "%d decisions" % len(cp.decisions(a)))

    # ---- D: a proof that fails after completion
    target_d = os.path.join(cp.TMP, "artifact-d.txt")
    proof_d = "test -f %s" % target_d
    d = open_card("two-stage D", proof_d, "proof")
    cp.cli("claim", d)
    open(target_d, "w").write("x")
    verdict(d, worker)
    cp.cli("complete", d, "--summary", "written; proof PASS")
    os.remove(target_d)                                                          # the artifact is gone again
    before = len(cp.rows("select id from tasks"))
    cp.coordinator()
    follow = [r for r in cp.rows("select id, title, body, status from tasks where id != ? and title like 'audit follow-up%'", (d,))]
    parent = cp.rows("select parent_id from task_links where child_id = ?", (follow[0]["id"],)) if follow else []
    ds = cp.decisions(d)
    check("D: one follow-up card is opened, the done card is its parent, the audit output is under Constraints",
          len(follow) == 1 and parent and parent[0]["parent_id"] == d and
          "Audit follow-up 1 of %s" % d in (crew_card.field(follow[0]["body"], "Constraints") or ""),
          "%d new cards; %s" % (len(cp.rows("select id from tasks")) - before, follow[0]["title"] if follow else ""))
    check("D: the follow-up has the same contract and proof snapshot; it is runnable (ready)",
          follow and crew_card.proof_cmd(follow[0]["body"]) == proof_d and follow[0]["status"] == "ready" and
          crew_card.proof_snapshot(follow[0]["id"]) == proof_d, follow[0]["status"] if follow else "")
    check("D: the done card got an `audit failed` comment and one audit decision (fail) naming the follow-up",
          cp.rows("select 1 from task_comments where task_id = ? and body like 'audit failed%'", (d,)) and
          len(ds) == 1 and ds[0]["outcome"] == "fail" and ds[0]["followup"] == follow[0]["id"], json.dumps(ds)[:100])
    cp.coordinator()
    check("D: a second pass opens no second follow-up",
          len(cp.rows("select id from tasks where title like 'audit follow-up%'")) == 1, "")

    # ---- E: a proof card refuses the review
    e = open_card("two-stage E", "true", "proof")
    g = plug._review_guard("kanban_request_review", {"task_id": e})
    check("E: kanban_request_review on a `Verify: proof` card is refused, naming verdict and kanban_complete",
          g and g["action"] == "block" and "verdict --card %s" % e in g["message"] and "kanban_complete" in g["message"],
          (g or {}).get("message", "allowed")[:90])

    # ---- F: independent verification
    target_f = os.path.join(cp.TMP, "artifact-f.txt")
    proof_f = "test -f %s" % target_f
    f = open_card("two-stage F", proof_f, "independent")
    cp.cli("set-model", f, "writer-pick", "--provider", "gemini")
    check("F: the card carries the writer's pin before the review",
          cp.card(f)["model_override"] == "writer-pick", str(cp.card(f)["model_override"]))
    cp.cli("claim", f)
    open(target_f, "w").write("x")
    verdict(f, worker)
    g = plug._close_guard("kanban_complete", {"task_id": f})
    check("F: the writer's own PASS does not close an independent card",
          g and g["action"] == "block" and "not by the verifier" in g["message"], (g or {}).get("message", "allowed")[-90:])
    g = plug._review_guard("kanban_request_review", {"task_id": f})
    check("F: the review goes ahead, and the writer's model pin is cleared for the verifier",
          g is None and cp.card(f)["model_override"] in (None, ""), str(cp.card(f)["model_override"]))
    rr = cp.cli("request-review", f, "--summary", "done; proof PASS", "--reviewer", "crew-verifier")
    reviewing = crew_proof_board.claim_review(cp.DB, f, cp.REAL_HOME)
    verdict(f, "crew-verifier")
    verdict(f, "crew-verifier", command="test -s %s" % target_f)                # the one extra check
    g = plug._close_guard("kanban_complete", {"task_id": f})
    check("F: after the verifier's PASS and its one extra check the close is allowed",
          rr.returncode == 0 and reviewing and g is None, str(g)[:100])
    cp.cli("complete", f, "--summary", "verified")
    cp.coordinator()
    pass_by = [l["by"] for l in lines(f) if l["verdict"] == "PASS" and l["command"] == proof_f]
    runs = cp.rows("select profile from task_runs where task_id = ?", (f,))
    ds = cp.decisions(f)
    check("F: PASS lines writer, verifier, coordinator; exactly one review run; one audit decision",
          pass_by == [worker, "crew-verifier", coord] and len(ds) == 1 and ds[0]["decision"] == "audit" and
          ds[0]["outcome"] == "pass", "%s runs=%s" % (pass_by, [r["profile"] for r in runs]))
    check("F: the review run count is one", len([r for r in runs if "verifier" in (r["profile"] or "")]) <= 1,
          str([r["profile"] for r in runs]))

    if cp.FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(cp.FAILS), ", ".join(cp.FAILS)))
        return 1
    print("PROOF OK: a rewritten proof line can not reach done, the coordinator audits every completed card once "
          "(pass, or a follow-up card under it), a proof card gets no verifier session and an independent one gets one")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        import shutil
        shutil.rmtree(cp.TMP, ignore_errors=True)
