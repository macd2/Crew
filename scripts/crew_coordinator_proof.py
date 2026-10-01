#!/usr/bin/env python3
"""Proof that the coordinator loop owns a crew card: it decides, applies, records, and stops at its cap.

Runs on a SCRATCH board it creates itself (a kanban.db pinned through HERMES_KANBAN_DB, a scratch
HERMES_HOME for the cursor, ledgers and verdict files, the real `hermes kanban` verbs through a wrapper that
keeps the real profile home) - the live board is never opened. The model call is replaced by a stub that
answers from a queue file, so each decision is exactly the one the proof scripted and the number of model
calls is countable.

  A  first pass: the cursor is initialised at the newest event and nothing is replayed
  B  a blocked crew card gets a `crew_decision` (retry) carrying the triggering event id; the fix is written
     into the card body and the card is back in the queue with the kernel's block counter reset
  C  the same card blocked again lands in `blocked` (not `triage`): the counter reset held
  D  the third failure is NOT sent to the model: the loop's retry cap turns it into ask_owner
  E  an owner stop wins: an archived/stopped card gets no decision and no model call
  F  a model that cannot answer is asked twice and then the owner is asked, never a silent loop
  G  a card the kernel breaker parked untyped is typed needs_input in place by ask_owner
  H  a card in `triage` (a second same-kind block) is lifted by a retry
  I  close: refused without a PASS line (becomes verify, runs the proof), accepted with one
  J  abandon without the owner's own words becomes ask_owner
  K  split opens children under a close-out and archives the original
  M  the mechanical remedy (a block whose proof passes now) is applied before any model call
  L  the lock: a live pass blocks a second one, a dead pid's lock is taken over
  N  the close rule: a card closed from the CLI (`complete --force`) with no PASS line is recorded as an
     owner_close decision, once and with no model call; one closed on a PASS line is left alone
  O  two FAILs on a verifier's review run go back to the writer (request-changes), the owner is not asked
  P  two FAILs on a writer's own run block the card as `transient`, and the coordinator decides
     (the completion audit is scripts/crew_two_stage_proof.py)

Run:  python3 crew_coordinator_proof.py
Exit: 0 when every check passes, 1 otherwise.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_card  # noqa: E402
import crew_proof_board  # noqa: E402

COORD = os.path.join(HERE, "crew_coordinator.py")
FAILS = []
REAL_HOME = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
REAL_HERMES = crew_card.hermes_bin()
TMP = tempfile.mkdtemp(prefix="crew-coordinator-proof-")
SHIM = os.path.join(TMP, "shim")
DB = os.path.join(TMP, "kanban.db")
HOME = os.path.join(TMP, "home")
QUEUE = os.path.join(TMP, "queue.txt")
CALLS = os.path.join(TMP, "calls.log")
WRAP = os.path.join(TMP, "hermes_wrap.sh")
STUB = os.path.join(TMP, "stub_decider.py")
ENV = dict(os.environ, PATH=SHIM + os.pathsep + os.environ.get("PATH", ""), HERMES_HOME=HOME, HERMES_KANBAN_DB=DB, HERMES_BIN=WRAP, CREW_PROFILE_PREFIX="crew-",
           CREW_COORDINATOR_DECIDER="%s %s" % (sys.executable, STUB), STUB_QUEUE=QUEUE, STUB_LOG=CALLS,
           HERMES_KANBAN_WORKSPACES_ROOT=os.path.join(TMP, "ws"),
           HERMES_KANBAN_ATTACHMENTS_ROOT=os.path.join(TMP, "att"))


def check(name, ok, detail=""):
    print("%-70s %s  %s" % (name, "PASS" if ok else "FAIL", str(detail)[:90]))
    if not ok:
        FAILS.append(name)


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    if mode:
        os.chmod(path, mode)


def setup():
    os.makedirs(HOME)
    # the real `hermes kanban` verbs, pinned to the scratch board, under the real profile home (a scratch
    # HERMES_HOME would make the CLI bootstrap a whole runtime)
    write(WRAP, "#!/bin/sh\nexport HERMES_HOME=%s\nexec %s \"$@\"\n" % (REAL_HOME, REAL_HERMES), 0o755)
    # a bare `hermes` anywhere in a subprocess must also reach the wrapper: hermes run under a scratch
    # HERMES_HOME bootstraps a runtime there and rewrites the live launcher (it did, once)
    os.makedirs(SHIM)
    os.symlink(WRAP, os.path.join(SHIM, "hermes"))
    write(STUB, (
        "import os, sys\n"
        "q = os.environ['STUB_QUEUE']\n"
        "lines = open(q).read().splitlines() if os.path.exists(q) else []\n"
        "open(os.environ['STUB_LOG'], 'a').write(os.path.basename(sys.argv[1]) + '\\n')\n"
        "open(os.environ['STUB_LOG'] + '.facts', 'w').write(open(sys.argv[1]).read())\n"
        "if lines:\n"
        "    answer, rest = lines[0], lines[1:]\n"
        "    open(q, 'w').write('\\n'.join(rest))\n"
        "else:\n"
        "    answer = 'QUEUE EMPTY'\n"
        "print('some reasoning first')\n"
        "print(answer)\n"))
    crew_proof_board.init_board(DB, REAL_HOME)


def cli(*args, timeout=180):
    return subprocess.run([WRAP, "kanban"] + [str(a) for a in args], env=ENV, capture_output=True, text=True,
                          timeout=timeout)


def rows(sql, args=()):
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]
    finally:
        conn.close()


def sql(query, args=()):
    conn = sqlite3.connect(DB, timeout=30)
    try:
        conn.execute(query, args)
        conn.commit()
    finally:
        conn.close()


def card(cid):
    return rows("select * from tasks where id = ?", (cid,))[0]


def decisions(cid):
    out = []
    for r in rows("select id, payload from task_events where task_id = ? and kind = 'crew_decision' order by id",
                  (cid,)):
        d = json.loads(r["payload"] or "{}")
        d["_id"] = r["id"]
        out.append(d)
    return out


def newest_event(cid, kind):
    r = rows("select max(id) m from task_events where task_id = ? and kind = ?", (cid, kind))[0]["m"]
    return r


def new_card(title, proof="sh -c 'exit 3'", assignee="crew-worker", extra=None):
    spec = {"role": "worker", "budget": 200000, "goal": title, "artifact": "a file", "lands": "here",
            "audience": "the owner", "done_when": "the file exists", "proof_cmd": proof,
            "coordinator": "proof/scratch"}
    spec.update(extra or {})
    body_file = os.path.join(TMP, "body-%d.md" % time.time_ns())
    write(body_file, crew_card.render_body(spec))
    r = cli("create", title, "--assignee", assignee, "--body-file", body_file, "--json")
    m = re.search(r'"id":\s*"(t_[0-9a-f]+)"', r.stdout or "")
    cid = m.group(1) if m else ""
    if not cid:
        raise RuntimeError("card not created: %s" % ((r.stdout or "") + (r.stderr or ""))[-300:])
    return cid


def stamp_healed(cid):
    """Mark the stale-block remedy as already tried, so a passing proof does not lift the card first."""
    sql("insert into task_events (task_id, run_id, kind, payload, created_at) values (?, null, 'self_heal', ?, ?)",
        (cid, json.dumps({"class": "stale_verify", "verdict": "still failing"}), int(time.time())))


def worker_blocks(cid, reason="needs a decision", kind="needs_input"):
    r = cli("block", cid, "--kind", kind, reason)
    return r.returncode == 0


def queue(*answers):
    write(QUEUE, "\n".join(answers))


def last_facts():
    """The newest facts file the stub was handed (it copies it, the loop deletes its own)."""
    path = CALLS + ".facts"
    return path if os.path.exists(path) else ""


def model_calls():
    try:
        return len(open(CALLS).read().splitlines())
    except OSError:
        return 0


def coordinator(*args, timeout=300):
    r = subprocess.run([sys.executable, COORD, "--once", "--json"] + list(args), env=ENV, capture_output=True,
                       text=True, timeout=timeout)
    raw = r.stdout or ""
    try:
        report = json.JSONDecoder().raw_decode(raw[raw.find("{"):])[0]
    except ValueError:
        report = {"raw": (raw + r.stderr)[-400:], "cards": []}
    report["rc"] = r.returncode
    return report


def acted(report, cid):
    return [c for c in report.get("cards", []) if c["card"] == cid]


def cursor():
    try:
        return json.load(open(os.path.join(HOME, "crew", "coordinator-cursor.json")))["last_event_id"]
    except (OSError, ValueError, KeyError):
        return None


def main():
    setup()
    check("the scratch board exists and is not the live board", os.path.exists(DB) and
          os.path.realpath(DB) != os.path.realpath(os.path.expanduser("~/.hermes/kanban.db")), DB)

    # ---- A: first pass initialises the cursor
    first = cid_a = new_card("proof card A")
    rep = coordinator()
    top = rows("select max(id) m from task_events")[0]["m"]
    check("A: the first pass initialises the cursor at the newest event", cursor() == top and
          rep.get("events", 0) == 0, "cursor=%s newest=%s" % (cursor(), top))
    check("A: nothing was decided and no model was called", not decisions(cid_a) and model_calls() == 0, "")

    # ---- B: a blocked crew card gets a retry decision, applied and recorded
    worker_blocks(cid_a, "the proof fails on line 3")
    blocked_ev = newest_event(cid_a, "blocked")
    queue(json.dumps({"decision": "retry", "fix": "use the tmp dir, not /root", "budget": 250000}))
    rep = coordinator()
    ds = decisions(cid_a)
    check("B: one crew_decision carries the triggering event id",
          len(ds) == 1 and ds[0].get("decision") == "retry" and ds[0].get("for_event") == blocked_ev and
          ds[0].get("applied") is True, json.dumps(ds)[:120])
    body = card(cid_a)["body"]
    check("B: the fix is written into the card body", "Coordinator fix 1: use the tmp dir, not /root" in body,
          body[-120:])
    check("B: the budget line carries the coordinator's ceiling", re.search(r"(?m)^Budget: 250000 tokens", body)
          is not None, "")
    c = card(cid_a)
    check("B: the card is back in the queue with the block counter reset",
          c["status"] in ("ready", "todo") and not c["block_recurrences"] and not c["block_kind"],
          "%s recurrences=%s kind=%s" % (c["status"], c["block_recurrences"], c["block_kind"]))
    check("B: exactly one model call was made and the cursor advanced", model_calls() == 1 and
          cursor() >= blocked_ev, "calls=%d cursor=%s" % (model_calls(), cursor()))
    facts_named = open(CALLS).read().strip().splitlines()[-1]
    check("B: the facts file was handed to the model", facts_named.startswith("crew-coordinator-"), facts_named)

    # ---- repeat pass: nothing new, nothing done
    calls_before = model_calls()
    rep = coordinator()
    check("B2: a pass with no new events changes nothing", not [c for c in rep["cards"] if c["action"] != "skip"]
          and model_calls() == calls_before and len(decisions(cid_a)) == 1, "")

    # ---- C: blocked again lands in blocked, second retry
    worker_blocks(cid_a, "the proof fails on line 9")
    check("C: the same-kind re-block lands in `blocked`, not `triage`", card(cid_a)["status"] == "blocked",
          card(cid_a)["status"])
    queue(json.dumps({"decision": "rescope", "done_when": "the file exists and is non-empty",
                      "fix": "the contract asked for too little"}))
    coordinator()
    body = card(cid_a)["body"]
    check("C: a rescope rewrites the Done when line and numbers its fix 2",
          "Done when: the file exists and is non-empty" in body and "Coordinator fix 2:" in body, body[-160:])

    # ---- D: the third failure never reaches the model
    worker_blocks(cid_a, "still failing the same way")
    calls_before = model_calls()
    queue(json.dumps({"decision": "retry", "fix": "THIS MUST NOT BE ASKED"}))
    coordinator()
    ds = decisions(cid_a)
    check("D: the third failure is an ask_owner decision made without a model call",
          ds[-1].get("decision") == "ask_owner" and model_calls() == calls_before, json.dumps(ds[-1])[:110])
    check("D: the question names the retry count", "retried 2 times" in str(ds[-1].get("question", "")),
          ds[-1].get("question", ""))
    comments = rows("select body from task_comments where task_id = ?", (cid_a,))
    check("D: the owner's question is on the card as a `Needs you:` comment",
          any(c["body"].startswith("Needs you:") for c in comments), str(comments[-1:])[:100])
    check("D: the card stays blocked for the owner", card(cid_a)["status"] == "blocked", card(cid_a)["status"])
    calls_before = model_calls()
    coordinator()
    coordinator("--since", "0")
    check("D: waiting for the owner, a later pass does nothing more", len(decisions(cid_a)) == 3 and
          model_calls() == calls_before, "%d decisions" % len(decisions(cid_a)))

    # ---- E: the owner's stop wins
    cid_e = new_card("proof card E")
    worker_blocks(cid_e, "whatever")
    cli("archive", cid_e)
    sql("insert into task_events (task_id, run_id, kind, payload, created_at) values (?, null, 'stopped', '{}', ?)",
        (cid_e, int(time.time())))
    calls_before = model_calls()
    queue(json.dumps({"decision": "retry", "fix": "MUST NOT RUN"}))
    coordinator()
    check("E: a stopped card gets no decision and no model call", not decisions(cid_e) and
          model_calls() == calls_before, "")

    # ---- F: a model that cannot answer
    cid_f = new_card("proof card F")
    worker_blocks(cid_f, "flaky")
    calls_before = model_calls()
    queue("no json at all", "still nothing")
    rep = coordinator()
    ds = decisions(cid_f)
    check("F: two unusable answers are one recorded error and the cursor is held",
          len(ds) == 1 and ds[0].get("decision") == "error" and model_calls() - calls_before == 2,
          json.dumps(ds)[:100])
    held = cursor()
    queue("garbage", "more garbage")
    coordinator()
    ds = decisions(cid_f)
    check("F: the second failed pass asks the owner instead of looping",
          [d.get("decision") for d in ds] == ["error", "ask_owner"], [d.get("decision") for d in ds])
    coordinator()
    check("F: then the cursor moves on", cursor() >= newest_event(cid_f, "blocked"), cursor())

    # ---- G: an untyped breaker block is typed in place
    cid_g = new_card("proof card G")
    worker_blocks(cid_g, "parked by the breaker")
    sql("update tasks set block_kind = null, block_recurrences = 0 where id = ?", (cid_g,))
    queue(json.dumps({"decision": "ask_owner", "question": "Which branch should this land on?"}))
    coordinator()
    check("G: ask_owner types an untyped block needs_input in place",
          card(cid_g)["status"] == "blocked" and card(cid_g)["block_kind"] == "needs_input",
          "%s/%s" % (card(cid_g)["status"], card(cid_g)["block_kind"]))

    # ---- H: triage is lifted by a retry
    cid_h = new_card("proof card H")
    worker_blocks(cid_h, "first")
    cli("unblock", cid_h)
    worker_blocks(cid_h, "second")          # same kind after an unblock: the kernel routes it to triage
    check("H: the kernel routed the second same-kind block to triage (precondition)",
          card(cid_h)["status"] == "triage", card(cid_h)["status"])
    queue(json.dumps({"decision": "retry", "fix": "different approach"}))
    coordinator()
    check("H: a retry lifts the card out of triage", card(cid_h)["status"] in ("ready", "todo") and
          decisions(cid_h)[-1].get("applied") is True, card(cid_h)["status"])

    # ---- I: close needs a PASS line
    cid_i = new_card("proof card I", proof="sh -c 'exit 0'")
    stamp_healed(cid_i)
    worker_blocks(cid_i, "waiting")
    queue(json.dumps({"decision": "close", "why": "the work looks done"}))
    coordinator()
    ds = decisions(cid_i)
    check("I: close without a PASS line runs the proof, then closes on its PASS",
          ds and ds[-1].get("decision") == "close" and card(cid_i)["status"] == "done",
          "%s %s" % (card(cid_i)["status"], json.dumps(ds[-1:])[:80]))
    cid_i2 = new_card("proof card I2", proof="sh -c 'exit 3'")
    worker_blocks(cid_i2, "waiting")
    queue(json.dumps({"decision": "verify"}), json.dumps({"decision": "verify"}))
    coordinator()
    ds = decisions(cid_i2)
    check("I: a failing proof is not a close: the owner is asked with the failure",
          ds and ds[-1].get("decision") == "ask_owner" and card(cid_i2)["status"] == "blocked",
          json.dumps(ds[-1:])[:110])

    # ---- J: abandon needs the owner's words
    cid_j = new_card("proof card J")
    worker_blocks(cid_j, "hopeless")
    queue(json.dumps({"decision": "abandon", "why": "it looks pointless"}))
    coordinator()
    ds = decisions(cid_j)
    check("J: abandon with no owner word becomes ask_owner and the card is not archived",
          ds and ds[-1].get("decision") == "ask_owner" and card(cid_j)["status"] == "blocked",
          json.dumps(ds[-1:])[:100])

    # ---- K: split
    cid_k = new_card("proof card K")
    worker_blocks(cid_k, "too big")
    child = {"title": "part one", "goal": "part one", "role": "worker", "artifact": "one.txt", "lands": "here",
             "audience": "the owner", "done_when": "one.txt exists", "proof_cmd": "test -f one.txt"}
    child2 = dict(child, title="part two", goal="part two", artifact="two.txt", done_when="two.txt exists",
                  proof_cmd="test -f two.txt")
    queue(json.dumps({"decision": "split", "children": [child, child2]}))
    coordinator()
    ds = decisions(cid_k)
    kids = rows("select id, status, title from tasks where title in ('part one', 'part two')")
    check("K: a split opens the children and archives the original",
          ds and ds[-1].get("decision") == "split" and ds[-1].get("applied") is True and len(kids) == 2 and
          card(cid_k)["status"] == "archived", "%s %d kids" % (card(cid_k)["status"], len(kids)))

    # ---- M: the mechanical remedy comes first
    cid_m = new_card("proof card M", proof="sh -c 'exit 0'")
    worker_blocks(cid_m, "stale block")
    calls_before = model_calls()
    queue(json.dumps({"decision": "retry", "fix": "MUST NOT BE ASKED"}))
    coordinator()
    check("M: a block whose proof passes now is lifted by the remedy, with no model call and no decision",
          card(cid_m)["status"] in ("ready", "todo") and model_calls() == calls_before and not decisions(cid_m)
          and not card(cid_m)["block_recurrences"], "%s recurrences=%s" % (card(cid_m)["status"],
                                                                        card(cid_m)["block_recurrences"]))

    # ---- L: the lock
    lock = os.path.join(HOME, "crew", "coordinator.lock")
    write(lock, str(os.getpid()))
    r = subprocess.run([sys.executable, COORD, "--once"], env=ENV, capture_output=True, text=True, timeout=120)
    check("L: a live pass blocks a second one", r.returncode == 3, "rc=%d" % r.returncode)
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    write(lock, str(dead.pid))
    r = subprocess.run([sys.executable, COORD, "--once"], env=ENV, capture_output=True, text=True, timeout=120)
    check("L: a dead pid's lock is taken over and released", r.returncode == 0 and not os.path.exists(lock),
          "rc=%d" % r.returncode)

    # ---- N: the owner's close is recorded, a proven close is not
    calls_before = model_calls()
    cid_n = new_card("proof card N", proof="sh -c 'exit 3'")
    r = cli("complete", cid_n, "--force", "--summary", "the owner says it is done")
    done_ev = newest_event(cid_n, "completed")
    report = coordinator()
    ds = decisions(cid_n)
    check("N: complete --force with no PASS line is one owner_close decision carrying the completed event id",
          r.returncode == 0 and card(cid_n)["status"] == "done" and len(ds) == 1 and
          ds[0].get("decision") == "owner_close" and ds[0].get("for_event") == done_ev and ds[0].get("applied"),
          "%s %s" % (card(cid_n)["status"], json.dumps(ds)[:110]))
    coordinator()
    check("N: the next pass does not record it again, and no model was asked",
          len(decisions(cid_n)) == 1 and model_calls() == calls_before, "%d decisions" % len(decisions(cid_n)))
    cid_n2 = new_card("proof card N2", proof="sh -c 'exit 0'")
    v = subprocess.run([sys.executable, os.path.join(HERE, "crew_card.py"), "verdict", "--card", cid_n2, "--by",
                        "crew-worker"], env=ENV, capture_output=True, text=True, timeout=200)
    cli("complete", cid_n2, "--summary", "proven")
    coordinator()
    ds2 = decisions(cid_n2)
    check("N: a card closed on its PASS line gets no owner_close, only the audit (pass) of its proof",
          v.returncode == 0 and card(cid_n2)["status"] == "done" and
          [(d["decision"], d.get("outcome")) for d in ds2] == [("audit", "pass")],
          "%s rc=%d %s" % (card(cid_n2)["status"], v.returncode, json.dumps(ds2)[:80]))

    # ---- O: two FAILs in a verifier's review run go back to the writer
    cid_o = new_card("proof card O", proof="sh -c 'exit 3'")
    cli("claim", cid_o)
    cli("request-review", cid_o, "--summary", "done", "--reviewer", "crew-verifier")
    reviewing = crew_proof_board.claim_review(DB, cid_o, REAL_HOME)
    vrc = []
    for _ in range(2):
        r = subprocess.run([sys.executable, os.path.join(HERE, "crew_card.py"), "verdict", "--card", cid_o, "--by",
                            "crew-verifier"], env=ENV, capture_output=True, text=True, timeout=200)
        vrc.append((r.returncode, r.stdout))
    back = rows("select payload from task_events where task_id = ? and kind = 'changes_requested'", (cid_o,))
    check("O: the second FAIL returns the review to its writer through request-changes",
          reviewing and [c for c, _ in vrc] == [1, 3] and len(back) == 1 and card(cid_o)["status"] == "ready"
          and card(cid_o)["assignee"] == "crew-worker" and "request-changes" in vrc[1][1],
          "%s/%s %s" % (card(cid_o)["status"], card(cid_o)["assignee"], vrc[1][1].strip().splitlines()[-1][:80]))
    check("O: the owner is not asked: no block, no `Needs you` comment",
          not rows("select 1 from task_events where task_id = ? and kind in ('blocked', 'commented')", (cid_o,))
          and "crew: 2 failed verifications" in (json.loads(back[0]["payload"]).get("reason") or ""),
          json.loads(back[0]["payload"]).get("reason", "")[:80] if back else "no changes_requested event")

    # ---- P: two FAILs in the writer's own run block the card as transient; the coordinator decides
    cid_p = new_card("proof card P", proof="sh -c 'exit 3'")
    cli("claim", cid_p)
    for _ in range(2):
        r = subprocess.run([sys.executable, os.path.join(HERE, "crew_card.py"), "verdict", "--card", cid_p, "--by",
                            "crew-worker"], env=ENV, capture_output=True, text=True, timeout=200)
    blk = card(cid_p)
    check("P: the second FAIL blocks the card as transient with the failure, not as a question to the owner",
          r.returncode == 3 and blk["status"] == "blocked" and blk["block_kind"] == "transient",
          "%s/%s rc=%d" % (blk["status"], blk["block_kind"], r.returncode))
    stamp_healed(cid_p)
    queue(json.dumps({"decision": "retry", "fix": "address the two failed proofs"}))
    calls_before = model_calls()
    coordinator()
    ds = decisions(cid_p)
    check("P: the next pass hands the coordinator the two FAIL lines and applies its retry",
          ds and ds[-1].get("decision") == "retry" and ds[-1].get("applied") and model_calls() == calls_before + 1
          and card(cid_p)["status"] in ("ready", "todo"), "%s %s" % (card(cid_p)["status"], json.dumps(ds[-1:])[:80]))
    check("P: the coordinator's facts carried both FAIL lines (by the writer profile)",
          len(re.findall(r"FAIL rc=3 by crew-worker", open(last_facts()).read() if last_facts() else "")) == 2,
          last_facts() or "no facts file")

    if FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("PROOF OK: the coordinator loop decides and applies every verb on a scratch board, records each "
          "decision with its triggering event, caps its own retries at two and never loops on a silent model")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        import shutil
        shutil.rmtree(TMP, ignore_errors=True)
