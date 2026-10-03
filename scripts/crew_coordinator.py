#!/usr/bin/env python3
"""The crew coordinator loop: one pass over what happened on the board since the last pass.

A crew card is owned by the coordinator from the moment it is opened until it is verified done or one
concrete question needs the owner. This pass is the owner's hands: it reads the `task_events` newer than
its cursor, and for every crew card that needs something it

  1. skips a card that is archived, stopped by the owner, or already waiting on the owner's answer,
  2. applies the mechanical remedy first (crew_heal.heal_card: held workspace, dead model, stale block),
  3. otherwise asks the coordinator profile ONE bounded question with the whole record in front of it,
     and applies the answer itself. The answer is one JSON line from a fixed vocabulary:

       close    {why}                                   only with a PASS verdict line; else treated as verify
       verify   {}                                      run the card's proof now; PASS closes, FAIL asks again once
       retry    {fix, model?, provider?, budget?, constraints?}   the fix is written into the card, then it runs again
       rescope  {goal?, done_when?, proof_cmd?}         the contract lines are rewritten, then retry
       split    {children: [contract, ...]}             independent cards; the card's own proof closes them
       revise_script {why, delegate?}                   the proof SCRIPT changed since it first ran: accept it as it is
                                                        (recorded with `why`, then verified) or, with delegate, the
                                                        verifier rewrites it (never the writer). Never the proof command.
       ask_owner {question}                             one sentence, answerable in one line
       abandon  {why}                                   archive; only when the owner's own words say so

The loop, not the model, enforces the rules: no decision on an archived or stopped card; at most
MAX_COORDINATOR_RETRIES retry/rescope/split decisions per card (the next one becomes ask_owner carrying the
failure signatures); a retry without a fix is refused and asked again once; a budget above twice the role
default is cut back. Every decision is recorded as a `crew_decision` event carrying the id of the event that
triggered it, so a pass that crashes half way repeats its batch without deciding anything twice.

  python3 crew_coordinator.py --once [--board SLUG] [--dry-run] [--card ID] [--since EVENT_ID] [--json]

CREW_COORDINATOR_DECIDER=<command> replaces the model call with `<command> <facts file>` (tests and proofs);
its stdout is read exactly like the model's answer.

Exit: 0 when the pass completes, 2 when the board cannot be read, 3 when another pass holds the lock.
"""
import argparse
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
import tempfile
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_card  # noqa: E402
import crew_handoff  # noqa: E402
import crew_heal  # noqa: E402
import crew_notify  # noqa: E402
import crew_safety  # noqa: E402

# The events that can make a crew card need something. Everything else on the board (heartbeats, comments,
# claims, the coordinator's own unblock and decision rows) is noise to this pass: it advances the cursor and
# never triggers work, which is also what keeps the loop from reacting to its own writes.
EVENT_KINDS = ("blocked", "block_loop_detected", "gave_up", "crashed", "timed_out", "protocol_violation",
               "stale", "reclaimed", "respawn_guarded", "completed")
# Of those, the ones that put a card where only a decision moves it (status blocked / triage).
STOP_EVENT_KINDS = crew_notify.STOP_EVENT_KINDS
# What the model may answer. `owner_close` and `audit` are also crew_decision kinds but only the loop writes them
# (audit_completion).
DECISIONS = ("close", "verify", "retry", "rescope", "split", "revise_script", "ask_owner", "abandon")
FIX_DECISIONS = crew_card.FIX_DECISIONS
MAX_COORDINATOR_RETRIES = 2
MAX_AUDIT_FOLLOWUPS = 2           # follow-up cards chained after failed audits before the owner is asked
FACTS_CHAR_CAP = 48000            # ~12k tokens at 4 chars a token
LOG_TAIL_BYTES = 6000
LOG_TAIL_LINES = 40
MODEL_TIMEOUT_S = 420
LOCK_STALE_S = 1800
ABANDON_WORDS = re.compile(r"\b(scrap(ped)?|cancel(l?ed)?|abandon(ed)?|drop (it|this)|stop(ped)? work)\b", re.I)


# ------------------------------------------------------------------------------------ board and state


def board_db(board=None):
    """The board's kanban.db: an env pin (tests, workers), else the default board, else the board's dir."""
    pinned = os.environ.get("HERMES_KANBAN_DB") or ""
    if pinned:
        return pinned
    base = crew_card.base_home()
    if board and board != "default":
        return os.path.join(base, "kanban", "boards", board, "kanban.db")
    return os.path.join(base, "kanban.db")


def state_path(name, board=None):
    """$HERMES_HOME/crew/<name>[-board].<ext>: one cursor and one lock per board."""
    stem, _, ext = name.partition(".")
    suffix = "-%s" % board if board and board != "default" else ""
    return os.path.join(crew_card.base_home(), "crew", "%s%s.%s" % (stem, suffix, ext))


def load_cursor(board=None):
    try:
        with open(state_path("coordinator-cursor.json", board)) as fh:
            return int(json.load(fh)["last_event_id"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save_cursor(last_id, board=None):
    path = state_path("coordinator-cursor.json", board)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({"last_event_id": int(last_id)}, fh)
    os.replace(tmp, path)


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def lock_live(board=None):
    """True while another pass holds the lock: its pid is alive and the lock is not older than LOCK_STALE_S."""
    path = state_path("coordinator.lock", board)
    try:
        with open(path) as fh:
            pid = int((fh.read() or "0").strip() or 0)
        age = time.time() - os.path.getmtime(path)
    except (OSError, ValueError):
        return False
    return bool(pid) and age < LOCK_STALE_S and _pid_alive(pid)


def take_lock(board=None):
    path = state_path("coordinator.lock", board)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if lock_live(board):
                return False
            try:
                os.unlink(path)
            except OSError:
                pass
            continue
        with os.fdopen(fd, "w") as fh:
            fh.write(str(os.getpid()))
        return True
    return False


def drop_lock(board=None):
    try:
        os.unlink(state_path("coordinator.lock", board))
    except OSError:
        pass


class Ctx:
    """What one pass carries: the board, the switches, and the model call (replaceable for tests)."""

    def __init__(self, db, board=None, dry=False, probe=False, decider=None, say=print):
        self.db, self.board, self.dry, self.probe, self.say = db, board, dry, probe, say
        self.decider = decider or default_decider


# ------------------------------------------------------------------------------------ reading the board


def q(ctx, sql, args=()):
    conn = sqlite3.connect("file:%s?mode=ro" % ctx.db, uri=True, timeout=10)
    try:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(sql, args).fetchall()]
    finally:
        conn.close()


def payload_of(row):
    try:
        data = json.loads(row.get("payload") or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def get_card(ctx, card_id):
    rows = q(ctx, "select * from tasks where id = ?", (card_id,))
    return rows[0] if rows else None


def card_events(ctx, card_id, kinds):
    marks = ",".join("?" * len(kinds))
    return q(ctx, "select id, kind, payload, created_at from task_events where task_id = ? and kind in (%s) "
                  "order by id" % marks, (card_id,) + tuple(kinds))


def decisions_of(ctx, card_id):
    out = []
    for row in card_events(ctx, card_id, ("crew_decision",)):
        data = payload_of(row)
        data["_id"] = row["id"]
        out.append(data)
    return out


def awaiting_owner(ctx, card_id, decisions):
    """The last decision asked the owner and nothing has moved the card since (no unblock, no new run, no exit
    from triage: the kernel's `specified` event is what /crew-unstuck and a coordinator rewrite leave)."""
    asked = [d for d in decisions if d.get("decision") == "ask_owner"]
    if not asked:
        return False
    since = asked[-1]["_id"]
    moved = q(ctx, "select 1 from task_events where task_id = ? and id > ? and kind in "
                   "('unblocked', 'specified', 'claimed', 'spawned', 'completed', 'promoted_manual') limit 1",
              (card_id, since))
    return not moved


def stopped_after(ctx, card_id, event_id):
    return bool(q(ctx, "select 1 from task_events where task_id = ? and kind = 'stopped' and id > ? limit 1",
                  (card_id, event_id)))


def fix_count(decisions):
    """Retry/rescope/split decisions since the owner was last asked: an answer resets the count."""
    n = 0
    for d in decisions:
        if d.get("decision") == "ask_owner":
            n = 0
        elif d.get("decision") in FIX_DECISIONS:
            n += 1
    return n


# ------------------------------------------------------------------------------------ the facts file


def worker_log_tail(card_id):
    try:
        done = subprocess.run([crew_card.hermes_bin(), "kanban", "log", card_id, "--tail", str(LOG_TAIL_BYTES)],
                              capture_output=True, text=True, timeout=60)
    except Exception:  # noqa: BLE001 - a missing log is an empty section, never a failed pass
        return ""
    lines = (done.stdout or "").strip().splitlines() if done.returncode == 0 else []
    return "\n".join(lines[-LOG_TAIL_LINES:])


def build_facts(ctx, card, decisions, extra=""):
    """The whole record as markdown, assembled with no model. The log is cut first when the cap bites."""
    cid, body = card["id"], card.get("body") or ""
    used, budget = crew_card.spent_tokens(cid), crew_card.field(body, "Budget") or "?"
    sections = []
    contract = ["card: %s  status: %s  block kind: %s  assignee: %s" % (
        cid, card["status"], card.get("block_kind") or "-", card.get("assignee") or "-"),
        "title: %s" % (card.get("title") or "")]
    for key in ("Role", "Budget", "GOAL", "Artifact", "Lands at", "For", "Constraints", "Done when",
                "proof command"):
        val = crew_card.field(body, key)
        if val:
            contract.append("%s: %s" % (key, val))
    inputs = crew_card.contract_inputs(body)
    if inputs:        # the owner's material: a result is judged against it as well as against Done when
        contract.append("Inputs:\n" + inputs)
    sections.append("## Contract\n" + "\n".join(contract))
    runs = q(ctx, "select id, profile, status, outcome, started_at, ended_at, summary, error from task_runs "
                  "where task_id = ? order by id desc limit 8", (cid,))
    rows = ["run | profile | outcome | seconds | summary / error"]
    for r in runs:
        secs = int((r["ended_at"] or r["started_at"] or 0) - (r["started_at"] or 0))
        rows.append("%s | %s | %s | %s | %s" % (r["id"], r["profile"], r["outcome"] or r["status"], secs,
                                                " ".join(str(r["summary"] or r["error"] or "").split())[:300]))
    sections.append("## Runs (newest first)\n" + "\n".join(rows))
    verdicts = crew_card.all_verdicts(cid)[-5:]
    sections.append("## Verdict lines (newest last)\n" + ("\n".join(
        "%s rc=%s by %s: %s | %s" % (v.get("verdict"), v.get("rc"), crew_card.verdict_by(v) or "?",
                                     (v.get("command") or "")[:120],
                                     " ".join(str(v.get("output_head") or "").split())[:300])
        for v in verdicts) or "(none)"))
    vb = crew_card.verifier_block(cid)
    if vb:
        sections.append("## Verifier's findings (the verifier blocked this card, run %s)\n%s\n"
                        "A passing proof does not answer these: the fix goes to the writer as a retry "
                        "(fix = these findings, concretely), or rescope, or ask_owner. Not verify, not close." % (
                            vb["run"], vb["reason"] or "(no reason recorded; read the verifier's comment on the card)"))
    sections.append("## Ledger\nused %s of %s" % (used, budget))
    sections.append("## Earlier coordinator decisions on this card\n" + ("\n".join(
        "- %s %s" % (d.get("decision"), json.dumps({k: v for k, v in d.items()
                                                      if k not in ("_id", "decision", "for_event")})[:300])
        for d in decisions) or "(none)"))
    route = card_events(ctx, cid, ("route", "reroute", "quota_wall"))[-6:]
    sections.append("## Route trail\n" + ("\n".join("- %s %s" % (r["kind"], json.dumps(payload_of(r))[:420])
                                                   for r in route) or "(none)"))
    try:
        crew_handoff.KANBAN_DB = ctx.db
        hand = crew_handoff.handoff_text(cid)
    except Exception:  # noqa: BLE001
        hand = ""
    sections.append("## Hand-off (previous work)\n" + (hand or "(first run)"))
    if extra:
        sections.append("## New since your last answer\n" + extra)
    log = worker_log_tail(cid)
    text = PROMPT + "\n\n" + "\n\n".join(sections)
    room = FACTS_CHAR_CAP - len(text)
    tail = "\n\n## Last worker log lines\n" + (log[-max(room, 0):] if log else "(no log)")
    return text + tail


PROMPT = """You are the crew coordinator. One card needs a decision from you. Decide from the facts below; you may
read files and run read-only commands to check one of them, but you change nothing on the board: the loop
applies your answer. Be critical: a worker saying it is done or blocked is not evidence.

Answer in a few lines of reasoning, then end with exactly ONE JSON object on the last line:
  {"decision": "close", "why": "..."}                   only when a PASS verdict line exists above
  {"decision": "verify"}                                run the card's proof now
  {"decision": "retry", "fix": "<what is different this time, concrete>", "model": "..", "provider": "..",
   "budget": N, "constraints": ".."}                    fix is required; the rest optional
  {"decision": "rescope", "goal": "..", "done_when": "..", "proof_cmd": ".."}   when the contract itself is wrong
  {"decision": "split", "children": [{"title","goal","role","artifact","lands","audience","done_when","constraints"}]}
                                                        children carry no proof_cmd, assignee or model: the card's own proof closes the tree
  {"decision": "revise_script", "why": "..", "delegate": false}   only when the proof was refused because its script
                                                        changed: accept the script as it is now, or delegate: true so the verifier rewrites it
  {"decision": "ask_owner", "question": "<one sentence the owner can answer in one line>"}
  {"decision": "abandon", "why": "..."}                 only when the owner's own words scrap the work
Ask the owner only when a human decision is needed; never repeat a fix the decisions above already tried.
A card's `Inputs` (paths, URLs, quoted text the owner gave) are part of the contract: judge a result against them as
well as against Done when."""


# ------------------------------------------------------------------------------------ the model call


def default_decider(ctx, facts_path):
    """(stdout, rc): the coordinator profile's one bounded turn, or CREW_COORDINATOR_DECIDER's stand-in."""
    stub = os.environ.get("CREW_COORDINATOR_DECIDER") or ""
    if stub:
        cmd = shlex.split(stub) + [facts_path]
    else:
        cmd = [crew_card.hermes_bin(), "-p", crew_card.role_profile("coordinator"), "chat",
               "--query-file", facts_path, "-Q", "--max-turns", "6", "--run-budget", "300",
               "--reasoning", "medium", "-t", "file,terminal"]
    # Scrubbed like a proof: `hermes -p crew-coordinator` loads its provider keys from its own profile .env
    # (hermes_cli/main.py load_hermes_dotenv under the profile's HERMES_HOME), not from what it inherits.
    env = crew_safety.proof_env({"CREW_COORDINATOR_TURN": "1"})
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=MODEL_TIMEOUT_S, env=env)
    except subprocess.TimeoutExpired:
        return "decider timed out after %ds" % MODEL_TIMEOUT_S, 124
    except OSError as exc:
        return "decider could not start: %s" % exc, 127
    return (done.stdout or "") + (done.stderr or ""), done.returncode


def parse_decision(text):
    """The last JSON object in the text that carries a `decision`, or None. Never a regex over prose."""
    dec = json.JSONDecoder()
    found = None
    for m in re.finditer(r"\{", text or ""):
        try:
            obj, _end = dec.raw_decode(text[m.start():])
        except ValueError:
            continue
        if isinstance(obj, dict) and "decision" in obj:
            found = obj
    return found


def check_decision(dec):
    """Why this answer is refused, or ''. The fixed vocabulary and the fields each verb needs."""
    kind = str(dec.get("decision") or "")
    if kind not in DECISIONS:
        return "unknown decision %r; use one of %s" % (kind, ", ".join(DECISIONS))
    text = lambda k: str(dec.get(k) or "").strip()  # noqa: E731
    if kind == "retry" and not text("fix"):
        return "a retry needs a non-empty `fix`: what is different this time"
    if kind == "rescope" and not any(text(k) for k in ("goal", "done_when", "proof_cmd")):
        return "a rescope needs at least one of goal, done_when, proof_cmd"
    if kind == "split" and not (isinstance(dec.get("children"), list) and dec["children"]):
        return "a split needs a non-empty `children` list"
    if kind == "ask_owner" and not text("question"):
        return "ask_owner needs a `question`"
    if kind in ("close", "abandon", "revise_script") and not text("why"):
        return "%s needs a `why`" % kind
    return ""


def ask_model(ctx, card, decisions, extra=""):
    """(decision, problem): up to two answers, the second told why the first was refused."""
    facts, problem = build_facts(ctx, card, decisions, extra), ""
    for _attempt in range(2):
        fd, path = tempfile.mkstemp(prefix="crew-coordinator-", suffix=".md")
        with os.fdopen(fd, "w") as fh:
            fh.write(facts + (("\n\n## Refused\nYour previous answer was refused: %s. Answer again."
                               % problem) if problem else ""))
        try:
            out, rc = ctx.decider(ctx, path)
        finally:
            os.unlink(path)
        dec = parse_decision(out)
        if dec is None:
            problem = ("the model call failed (rc=%s): %s" % (rc, " ".join((out or "").split())[-200:])
                       if rc else "no JSON decision on the last line")
            continue
        problem = check_decision(dec)
        if not problem:
            return dec, ""
    return None, problem


# ------------------------------------------------------------------------------------ applying a decision


def sh(*args, timeout=180):
    done = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=timeout,
                          env=crew_safety.proof_env())
    return done.returncode, ((done.stdout or "") + (done.stderr or "")).strip()


def kanban(*args, timeout=180):
    return sh(crew_card.hermes_bin(), "kanban", *args, timeout=timeout)


def set_body(card_id, body):
    return kanban("edit", card_id, "--body", body)


def coordinator_fix_body(body, n, dec):
    """The card body with this decision's fix written in. Numbered, so a repeated pass cannot add it twice."""
    if re.search(r"(?m)^Coordinator fix %d:" % n, body or ""):
        return body
    add = "\nCoordinator fix %d: %s\n" % (n, " ".join(str(dec.get("fix") or "").split()))
    if str(dec.get("constraints") or "").strip():
        add += "Coordinator constraints %d: %s\n" % (n, " ".join(str(dec["constraints"]).split()))
    return (body or "").rstrip() + "\n" + add


def clamp_budget(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    ceiling = crew_card.roles_defaults().get("default_budget_tokens")
    ceiling = (ceiling if isinstance(ceiling, int) else crew_card.DEFAULT_BUDGET) * 2
    return max(0, min(value, ceiling)) or None


def apply_retry(ctx, card, dec, decisions, with_contract=False, lift=True):
    """`lift=False`: a stopped card is written (fix, budget, ledger) but stays stopped: the caller moves it on in one
    step of its own (revise_script delegate: crew_card.send_to_verifier lifts and requests review together)."""
    cid, body = card["id"], card.get("body") or ""
    n = fix_count(decisions) + 1
    if with_contract:
        # the proof command is not a contract line the loop may rewrite: see ask_proof_change
        for key, label in (("goal", "GOAL"), ("done_when", "Done when")):
            if str(dec.get(key) or "").strip():
                body = crew_card.rewrite_line(body, label, dec[key])
    body = coordinator_fix_body(body, n, dec) if str(dec.get("fix") or "").strip() else body
    notes = []
    stopped = card["status"] in ("blocked", "triage")
    if body != (card.get("body") or "") and not stopped:
        rc, out = set_body(cid, body)
        if rc != 0:
            return False, "could not write the fix into the card: %s" % out[-160:]
        notes.append("fix %d written" % n)
    if dec.get("model") and dec.get("provider"):
        crew_card.apply_route(cid, {"model": dec["model"], "provider": dec["provider"],
                                    "task_class": "coordinator", "why": "coordinator decision"})
        notes.append("pinned %s/%s" % (dec["provider"], dec["model"]))
    if card["status"] in ("blocked", "triage"):
        # one write of the rewritten card: a triaged card leaves triage through the kernel's own exit
        # (`specify_triage_task` with the new approach), a blocked one is edited and then unblocked
        res = crew_card.retry_card(cid, budget=clamp_budget(dec.get("budget")), profile=None, body=body, unblock=lift)
        if not res.get("ok") or (res.get("unblock") or {}).get("rc") not in (0, None):
            return False, "retry did not lift the card: %s" % json.dumps(res.get("unblock") or res)[:160]
        if body != (card.get("body") or ""):
            notes.append("fix %d written" % n)
        if lift:
            back = crew_card.hand_to_writer(cid)         # not back to the verifier with nothing changed
            if back["reopened"] or back["assigned"]:
                notes.append("handed back to the writer %s" % (back["assigned"] or ""))
        notes.append("ceiling %s, card %s" % (res["budget"], (res.get("unblock") or {}).get("status") or card["status"]))
    else:
        crew_card.release_hold(cid)
        notes.append("hold released")
    return True, "; ".join(notes)


SPLIT_CHILD_KEYS = ("title", "goal", "role", "artifact", "lands", "audience", "done_when", "constraints")


def split_child(ch, origin, coordinator, inputs=""):
    """A child card from the model's JSON: only the contract's own text fields are taken. The assignee and skills
    are the role's profile (open_card derives them from `role`), the model, provider and runtime are the
    defaults, the budget is clamped, and there is no proof command: the split card's owner-confirmed proof
    closes the tree (run_plan closeout_proof). Anything else the model wrote - an assignee, a model pin, a
    proof_cmd, a parent - is dropped. Every child starts from the split card's own `Inputs` (the owner's material)."""
    out = {k: ch[k] for k in SPLIT_CHILD_KEYS if isinstance(ch.get(k), str)}
    if inputs:
        out["inputs"] = inputs
    budget = clamp_budget(ch.get("budget"))
    if budget:
        out["budget"] = budget
    out["origin"], out["coordinator"] = origin, coordinator
    return out


def apply_split(ctx, card, dec):
    body = card.get("body") or ""
    proof = crew_card.close_proof_command(card["id"])
    if not proof:
        return False, "the card has no owner-confirmed proof command to close the split tree with"
    origin = crew_card.field(body, "Origin") or ""
    coordinator = crew_card.field(body, "Coordinator")
    inputs = crew_card.contract_inputs(body)
    children = [split_child(ch, origin, coordinator, inputs) for ch in dec["children"] if isinstance(ch, dict)]
    spec = {"title": card.get("title"), "goal": crew_card.field(body, "GOAL") or card.get("title"),
            "children": children}
    res = crew_card.run_plan(spec, closeout_proof=proof)
    ids = [c.get("id") for c in res["children"]]
    kanban("comment", card["id"], "Split by the coordinator into %s (close-out %s)." % (
        ", ".join(ids), res["closeout"].get("id")))
    kanban("archive", card["id"])
    return True, "children %s, close-out %s, original archived" % (", ".join(ids), res["closeout"].get("id"))


def answer_line(card_id, flag):
    return 'python3 "%s" proof-answer --card %s %s' % (os.path.join(HERE, "crew_card.py"), card_id, flag)


def proof_blocked_ask(card_id, cmd, reason):
    """The ask_owner decision for a proof Hermes's safety floor refused. The owner answers `brave` (this card)
    or sets /crew-safety brave for good; `proof_ask` is what `crew_card.py proof-answer` closes."""
    reason = " ".join(str(reason).split())
    return {"decision": "ask_owner", "proof_ask": {"kind": "blocked", "command": cmd, "reason": reason},
            "question": "Proof blocked by Hermes safety: `%s` (%s). Reply `brave` to run it for this card, or "
                        "`/crew-safety brave` to stop being asked." % (cmd[:90], reason[:70]),
            "detail": "Proof command: %s\nHermes: %s\nReply `brave` to run it for this card, or `/crew-safety brave` "
                      "to stop being asked.\nRecord the answer: %s" % (cmd, reason, answer_line(card_id, "--brave"))}


def proof_change_ask(card_id, old, new):
    """The ask_owner decision for a coordinator rescope that names a different proof command. Models propose,
    the owner confirms: nothing runs until `proof-answer` writes the new snapshot."""
    return {"decision": "ask_owner", "proof_ask": {"kind": "rescope", "proposed": new},
            "question": "The coordinator proposes a new proof command: `%s` (now: `%s`). Reply yes to accept it."
                        % (new[:100], (old or "none")[:70]),
            "detail": "Proposed proof command: %s\nCurrent: %s\nAccept: %s (add --brave to also skip Hermes's "
                      "dangerous-command check for this card)" % (new, old or "(none)", answer_line(card_id, "--yes"))}


def blocked_ask_for(card, out=""):
    """proof_blocked_ask for the card's snapshot command, the reason being Hermes's (re-asked, so the words are
    the detector's own, not a slice of the verdict output)."""
    cmd = crew_card.close_proof_command(card["id"])
    _ok, reason = crew_safety.check_proof(cmd, crew_safety.proof_mode(card["id"], cmd))
    reason = reason or crew_safety.script_change(card["id"], cmd)
    return proof_blocked_ask(card["id"], cmd, reason or (out.strip().splitlines() or ["blocked"])[-1])


def apply_ask_owner(ctx, card, question, detail=""):
    cid = card["id"]
    text = "Needs you: %s" % " ".join(question.split())[:300]
    if card["status"] == "ready" or (card["status"] == "blocked" and not card.get("block_kind")):
        # a held ready card is stopped for the owner; an untyped breaker block is typed in place
        kanban("block", cid, "--kind", "needs_input", text)
    rc, out = kanban("comment", cid, text + ("\n\n" + detail if detail else ""))
    return rc == 0, text if rc == 0 else "comment failed: %s" % out[-160:]


def apply_close(ctx, card, why):
    rc, out = kanban("complete", card["id"], "--summary", "coordinator close: %s" % why[:300])
    return rc == 0, ("closed: %s" % why[:120]) if rc == 0 else "complete failed: %s" % out[-160:]


def apply_abandon(ctx, card, dec):
    brief = " ".join(str(payload_of(r).get("text") or "") for r in card_events(ctx, card["id"], ("brief",)))
    stopped = card_events(ctx, card["id"], ("stopped",))
    if not (stopped or ABANDON_WORDS.search(brief)):
        return None
    kanban("comment", card["id"], "Abandoned by the coordinator: %s" % str(dec["why"])[:300])
    rc, out = kanban("archive", card["id"])
    return rc == 0, ("archived: %s" % str(dec["why"])[:120]) if rc == 0 else "archive failed: %s" % out[-160:]


def signature_question(ctx, card):
    """The owner's question when the loop's own retry cap is reached: what failed, how often, what it asks."""
    chain = crew_heal.repeat_chain(card["id"], need=MAX_COORDINATOR_RETRIES) or []
    sigs = sorted({"%s/%s" % crew_heal.failure_signature(r) for r in chain if crew_heal.failure_signature(r)})
    err = " ".join(str(card.get("last_failure_error") or "").split())[:160]
    return ("This card was retried %d times by the coordinator and is blocked again%s%s. "
            "Retry once more, change the contract, or drop it?"
            % (MAX_COORDINATOR_RETRIES, (" (same failure: %s)" % ", ".join(sigs)) if sigs else "",
               (": %s" % err) if err else ""))


def run_verdict(card_id, for_event=None):
    args = ["--for-event", str(for_event)] if for_event is not None else []
    rc, out = sh(sys.executable, os.path.join(HERE, "crew_card.py"), "verdict", "--card", card_id,
                 "--by", crew_card.role_profile("coordinator"), "--no-hand-back", *args, timeout=600)
    return rc, out


def pass_line(card_id):
    """The crew close rule (crew_card.close_check) for this card: the same one the kanban_complete guard applies."""
    row = crew_card.card_row(card_id)
    return bool(row) and crew_card.close_check(card_id, row[4], crew_card.claimed_at(card_id))[0]


def record_decision(ctx, card, trigger, dec, result, ok):
    payload = {k: v for k, v in dec.items() if k != "decision"}
    payload.update({"decision": dec["decision"], "for_event": trigger["id"], "applied": bool(ok),
                    "result": str(result)[:300], "by": "crew_coordinator"})
    crew_card._append_card_event(card["id"], "crew_decision", payload)


# ------------------------------------------------------------------------------------ one card


def resolve(ctx, card, decisions, trigger):
    """(decision, source, pending): what to do with this card. `pending` means the model could not answer."""
    if fix_count(decisions) >= MAX_COORDINATOR_RETRIES:
        return {"decision": "ask_owner", "question": signature_question(ctx, card)}, "cap", False
    dec, problem = ask_model(ctx, card, decisions)
    if dec is None:
        errors = [d for d in decisions if d.get("decision") == "error" and d.get("for_event") == trigger["id"]]
        if len(errors) >= 1:               # the second failed answer for the same event goes to the owner
            return {"decision": "ask_owner", "question": "The coordinator could not decide (%s). What should "
                                                         "happen to this card?" % problem[:160]}, "error", False
        return {"decision": "error", "problem": problem}, "error", True
    vb = crew_card.verifier_block(card["id"])
    if vb and dec["decision"] in ("verify", "close"):
        # the verifier blocked this card on its own judgement: a passing proof must not override it
        why = " ".join(vb["reason"].split())[:700] or "see the verifier's comment on the card"
        dec, problem = ask_model(ctx, card, decisions, "The verifier blocked this card on its own judgement, so "
                                 "verify/close is refused (the proof passing does not answer it): %s\nAnswer retry "
                                 "(fix = what the verifier found), rescope or ask_owner." % why)
        if dec is None or dec["decision"] in ("verify", "close"):
            return {"decision": "ask_owner", "question": "The verifier blocked this card: %s. Fix it with the "
                                                         "writer, rescope, or drop the card?" % why[:300]}, "verifier", False
        return dec, "model", False
    if dec["decision"] == "verify" or (dec["decision"] == "close" and not pass_line(card["id"])):
        if ctx.dry:                        # running the proof writes a verdict line: a dry pass only reports
            return dec, "model", False
        rc, out = run_verdict(card["id"])
        if rc == crew_card.PROOF_BLOCKED and crew_safety.is_script_block(script_reason(card)):
            return resolve_script(ctx, card, decisions, script_reason(card))
        if rc == crew_card.PROOF_BLOCKED:
            return blocked_ask_for(card, out), "verify", False
        if rc == 0:
            return {"decision": "close", "why": "verdict PASS: proof exits 0 now"}, "verify", False
        again, problem = ask_model(ctx, card, decisions, "The proof was run for you and FAILED (rc=%s):\n%s"
                                   % (rc, out[-1200:]))
        if again is None or again["decision"] in ("verify", "close"):
            first = next((ln for ln in out.splitlines() if ln.strip()), "proof failed")
            return {"decision": "ask_owner", "question": "The proof fails (%s). Fix it, change it, or drop the "
                                                         "card?" % first[:160]}, "verify", False
        dec = again
    return dec, "model", False


def script_reason(card):
    """Why the card's proof script may not run ('' when it may): crew_safety.script_change, read-only."""
    return crew_safety.script_change(card["id"], crew_card.close_proof_command(card["id"]))


def accept_script(card, why):
    """The coordinator accepts the proof script as it is now: its hash is recorded with the reason."""
    return crew_card.record_script_hashes(card["id"], crew_safety.script_hashes(crew_card.close_proof_command(card["id"])),
                                          by="coordinator", why=" ".join(str(why).split())[:300])


def resolve_script(ctx, card, decisions, reason):
    """(decision, source, pending) for a proof refused because its script changed since it first ran. The owner
    is not asked: the coordinator decides again with that fact (revise_script, retry on a restored script, ...).
    An accepted script is verified right away; no usable answer is the generic owner question of `resolve`."""
    again, problem = ask_model(ctx, card, decisions, "The proof was refused: %s. The writer may not change the proof "
                                                     "script on its own. Accept it (revise_script, with why), have the "
                                                     "verifier rewrite it (revise_script, delegate), or retry." % reason)
    if again is None or again["decision"] in ("verify", "close"):
        return {"decision": "ask_owner", "question": "The proof script changed and the coordinator could not decide "
                                                     "what to do (%s). What should happen to this card?"
                                                     % (problem or reason)[:160]}, "verify", False
    if again["decision"] == "revise_script" and not again.get("delegate"):
        accept_script(card, again["why"])
        rc, out = run_verdict(card["id"])
        if rc == 0:
            return {"decision": "close", "why": "script revised by the coordinator (%s); verdict PASS"
                                                % " ".join(str(again["why"]).split())[:120]}, "verify", False
        first = next((ln for ln in out.splitlines() if ln.strip()), "proof failed")
        return {"decision": "ask_owner", "question": "The proof fails (%s). Fix it, change it, or drop the "
                                                     "card?" % first[:160]}, "verify", False
    return again, "model", False


def apply_revise_script(ctx, card, dec, decisions):
    """revise_script with delegate: the VERIFIER rewrites the script, never a writer. The authorization is an event
    written here from the decision, the card says so in a `Proof script:` body line, and the card goes to the
    verifier's review step (crew_card.send_to_verifier); the verifier's next run records the new hash with this
    reason. Without delegate the script is accepted as it is now and the card runs again as a retry."""
    why = " ".join(str(dec.get("why") or "").split())[:300]
    if not dec.get("delegate"):
        accept_script(card, why)
        dec = dict(dec, fix="the proof script was accepted as it is now: %s. Run the proof again." % why)
        return apply_retry(ctx, card, dec, decisions)
    crew_card.authorize_script_revision(card["id"], why)
    body = crew_card.rewrite_line(card.get("body") or "", "Proof script", "verifier to revise - %s" % why)
    if body != (card.get("body") or "") and card["status"] not in ("blocked", "triage"):
        rc, out = set_body(card["id"], body)
        if rc != 0:
            return False, "could not write the Proof script line into the card: %s" % out[-160:]
    ok, note = apply_retry(ctx, dict(card, body=body), dict(dec, fix=""), decisions, lift=False)   # send_to_verifier lifts it
    if not ok:
        return ok, note
    res = crew_card.send_to_verifier(card["id"], "proof script revision: %s" % why)
    if not res.get("ok"):
        return False, "the card could not go to the verifier: %s" % res.get("why")
    return True, "%s; sent to the verifier (%s)" % (note, res.get("why"))


def apply_decision(ctx, card, decisions, dec):
    kind = dec["decision"]
    if kind == "revise_script":
        return apply_revise_script(ctx, card, dec, decisions)
    if kind == "retry":
        return apply_retry(ctx, card, dec, decisions)
    if kind == "rescope":
        new = str(dec.get("proof_cmd") or "").strip()
        old = crew_card.close_proof_command(card["id"])
        if not new or new == old:
            return apply_retry(ctx, card, dec, decisions, with_contract=True)
        # A different proof command is the owner's to confirm. Goal and done-when apply now; the card stays
        # stopped until the answer writes the new snapshot (crew_card.py proof-answer), which also lifts it.
        body = card.get("body") or ""
        for key, label in (("goal", "GOAL"), ("done_when", "Done when")):
            if str(dec.get(key) or "").strip():
                body = crew_card.rewrite_line(body, label, dec[key])
        if body != (card.get("body") or ""):
            set_body(card["id"], body)
        dec.update(proof_change_ask(card["id"], old, new))     # recorded as the ask it became
        return apply_ask_owner(ctx, card, dec["question"], dec["detail"])
    if kind == "split":
        return apply_split(ctx, card, dec)
    if kind == "ask_owner":
        return apply_ask_owner(ctx, card, str(dec["question"]), str(dec.get("detail") or ""))
    if kind == "close":
        return apply_close(ctx, card, str(dec.get("why") or ""))
    if kind == "abandon":
        done = apply_abandon(ctx, card, dec)
        if done is None:                   # nobody scrapped it: a model's hunch is not the owner's word
            dec["decision"] = "ask_owner"
            dec["question"] = "Abandon this card? %s" % " ".join(str(dec["why"]).split())[:200]
            return apply_ask_owner(ctx, card, dec["question"])
        return done
    return False, "unknown decision"


def audit_followup_number(body):
    """How many failed audits this card descends from: its `Audit follow-up N of <card>` constraint, else 0."""
    m = re.search(r"Audit follow-up (\d+) of t_", crew_card.field(body, "Constraints") or "")
    return int(m.group(1)) if m else 0


def open_audit_followup(card, rc, out, blocked=False):
    """One new card with the done card's contract, the done card as its parent and the audit output under
    Constraints, so the work is retried on a card the board can run: a done card has no re-run verb."""
    body = card.get("body") or ""
    c = crew_card.parse_contract(body)
    n = audit_followup_number(body) + 1
    head = " ".join((out or "").split())[-240:]
    what = "could not run (blocked by Hermes safety)" if rc == crew_card.PROOF_BLOCKED else "failed again"
    note = ("Audit follow-up %d of %s: after the card was completed its proof command %s (rc=%s): %s"
            % (n, card["id"], what, rc, head))
    c["constraints"] = " | ".join(x for x in (c.get("constraints") or "", note) if x)
    c["title"] = "audit follow-up: %s" % (card.get("title") or c.get("goal") or card["id"])
    c["coordinator"] = crew_card.field(body, "Coordinator") or ""
    c["budget"] = c.get("budget") or crew_card.default_budget(c["role"])
    c["proof_cmd"] = crew_card.close_proof_command(card["id"])       # the snapshot, never the body line
    c["proof_mode"] = crew_card.proof_snapshot_mode(card["id"])      # and the owner's choice, carried over
    c["verify"] = crew_card.default_verify(c)
    res = crew_card.open_card(c, parents=[card["id"]], initial_status="blocked" if blocked else None)
    if res.get("id"):       # the follow-up fixes the work, not the proof: it starts with the script hashes bound
        crew_card.carry_script_hashes(card["id"], res["id"])
    return res


def audit_proof(ctx, card, event):
    """The coordinator's own run of a completed card's proof command, once per `completed` event.

    The writer's PASS proves the work at the time it finished; this run, by nobody who wrote it, proves it still
    holds. A FAIL comments the output on the done card and opens one follow-up card under it (a chain of
    MAX_AUDIT_FOLLOWUPS at most, then the owner is asked). Plan machinery (the coordinator's own cards) is not audited.
    Every outcome is an `audit` crew_decision carrying the event id, which is what makes the audit run once."""
    body = card.get("body") or ""
    if (crew_card.field(body, "Role") or "").strip().lower() not in crew_card.WRITER_ROLES:
        return {"detail": "completed: no proof to audit"}
    cmd = crew_card.close_proof_command(card["id"])
    if not cmd:
        return {"detail": "completed: no proof command to re-run"}
    if ctx.dry:
        return {"action": "would audit", "detail": cmd[:160]}
    lines = crew_card.verdict_lines(card["id"], crew_card.claimed_at(card["id"], event["id"]))
    closing = [v for v in lines if (v.get("command") or "") == cmd]
    mine = {crew_card.profile_prefix() + "coordinator", crew_card.role_profile("coordinator")}
    if closing and crew_card.verdict_by(closing[-1]) in mine:
        dec = {"decision": "audit", "outcome": "pass", "why": "closed on the coordinator's own PASS run"}
        record_decision(ctx, card, event, dec, dec["why"], True)
        return {"action": "audit pass", "detail": dec["why"]}
    rc, out = run_verdict(card["id"], for_event=event["id"])
    first = next((ln for ln in out.splitlines() if ln.strip()), "")
    if rc == crew_card.PROOF_BLOCKED and crew_safety.is_script_block(script_reason(card)):
        rc = 1          # the script was edited after the card finished: a failed audit, the follow-up redoes it
    if rc == crew_card.PROOF_BLOCKED:
        # Not a failure: the safety floor refused the proof. The question rides on a blocked follow-up (a done
        # card can not be blocked, and crew_notify alerts on blocked ones), exactly as at the follow-up cap.
        why = blocked_ask_for(card, out)["proof_ask"]
        res = open_audit_followup(card, rc, out, blocked=True)
        ask = proof_blocked_ask(res["id"], why["command"], why["reason"])      # answered on the follow-up card
        held = crew_card.card_row(res.get("id")) or ("", "", "", "", "")
        ok, result = apply_ask_owner(ctx, {"id": res["id"], "status": held[2], "block_kind": ""},
                                     ask["question"], ask["detail"])
        record_decision(ctx, {"id": res["id"]}, event, ask, result, ok)
        dec = {"decision": "audit", "outcome": "blocked", "followup": res.get("id"), "why": ask["question"]}
        record_decision(ctx, card, event, dec, "owner asked on %s" % res.get("id"), ok)
        return {"action": "audit blocked: ask_owner", "detail": "asked on %s: %s" % (res.get("id"), ask["question"][:120])}
    if rc == 0:
        dec = {"decision": "audit", "outcome": "pass", "why": "the proof command passes again after completion"}
        record_decision(ctx, card, event, dec, dec["why"], True)
        return {"action": "audit pass", "detail": dec["why"]}
    kanban("comment", card["id"], "audit failed: the proof command exits %s after the card was completed.\n\n%s"
           % (rc, out[-1200:]))
    try:
        if audit_followup_number(body) >= MAX_AUDIT_FOLLOWUPS:
            # A done card can not be blocked and crew_notify alerts on blocked ones: the question rides on a follow-up
            # card opened already blocked, so it reaches the owner through the same ask_owner alert as any other.
            question = ("This card was re-done %d times and its proof still fails after completion (%s). Fix it, "
                        "change the proof, or drop it?" % (MAX_AUDIT_FOLLOWUPS, " ".join(first.split())[:160]))
            res = open_audit_followup(card, rc, out, blocked=True)
            held = crew_card.card_row(res.get("id")) or ("", "", "", "", "")
            ask = {"decision": "ask_owner", "question": question, "why": "audit failed at the follow-up cap"}
            ok, result = apply_ask_owner(ctx, {"id": res["id"], "status": held[2], "block_kind": ""}, question)
            record_decision(ctx, {"id": res["id"]}, event, ask, result, ok)
            dec = {"decision": "audit", "outcome": "fail", "followup": res.get("id"), "capped": True,
                   "why": question}
            record_decision(ctx, card, event, dec, "owner asked on %s" % res.get("id"), ok)
            return {"action": "audit fail: ask_owner", "detail": "asked on %s: %s" % (res.get("id"), question[:120])}
        res = open_audit_followup(card, rc, out)
        dec = {"decision": "audit", "outcome": "fail", "followup": res.get("id"),
               "why": "the proof command exits %s after completion" % rc}
        record_decision(ctx, card, event, dec, "follow-up %s" % res.get("id"), True)
        return {"action": "audit fail: follow-up", "detail": "follow-up card %s" % res.get("id")}
    except Exception as exc:  # noqa: BLE001 - an audit that cannot open its follow-up is recorded, not retried
        why = "the proof fails after completion (%s) and the follow-up card could not be opened: %s" % (
            " ".join(first.split())[:120], exc)
        dec = {"decision": "audit", "outcome": "fail", "followup": None, "why": why[:300]}
        record_decision(ctx, card, event, dec, why[:300], False)
        return {"action": "audit fail: no follow-up", "detail": why[:160]}


def audit_completion(ctx, card, event):
    """A crew card reached `done`. The kanban_complete guard lets through only a card that passes the close rule
    (crew_card.close_check), so a completion that does not is the owner's override from the CLI
    (`hermes kanban complete --force`, which no tool guard sees) and is recorded as an `owner_close` decision.
    The loop never reopens or re-decides such a card: the owner's word stands. A completion that does pass is
    audited once by re-running the proof (audit_proof)."""
    if card["status"] != "done" or not crew_card.needs_pass(card.get("body")):
        return {"detail": "completed: no proof to audit"}
    if any(d.get("decision") in ("owner_close", "audit") and d.get("for_event") == event["id"]
           for d in decisions_of(ctx, card["id"])):
        return {"detail": "completion already audited"}
    ok, why = crew_card.close_check(card["id"], card.get("body"), crew_card.claimed_at(card["id"], event["id"]))
    if ok:
        return audit_proof(ctx, card, event)
    dec = {"decision": "owner_close", "why": "closed without a PASS line, by the owner's override: %s" % why}
    if ctx.dry:
        return {"action": "would owner_close", "detail": why[:160]}
    record_decision(ctx, card, event, dec, why, True)
    return {"action": "owner_close", "detail": why[:160]}


def handle_card(ctx, card_id, events):
    """One card's answer for this pass: {card, action, detail, pending}."""
    out = {"card": card_id, "action": "skip", "detail": "", "pending": False}
    card = get_card(ctx, card_id)
    if not card:
        out["detail"] = "no such card"
        return out
    if not crew_card.is_crew_body(card.get("body")):
        out["detail"] = "not a crew card"
        return out
    if crew_card.probe_card(card.get("created_by")) and not ctx.probe:
        out["detail"] = "probe fixture"
        return out
    completions = [e for e in events if e["kind"] == "completed"]
    events = [e for e in events if e["kind"] != "completed"]    # a completion is audited, it never asks for a decision
    if completions:
        out.update(audit_completion(ctx, card, completions[-1]))
        if not events:
            return out
    if card["status"] in ("archived", "done"):
        out["detail"] = card["status"]
        return out
    if crew_card.parked_by_owner(ctx.db, card_id):
        out["detail"] = "stopped by the owner (/crew-stop): no decision until /crew-unstuck"
        return out
    newest = events[-1]
    if stopped_after(ctx, card_id, newest["id"]):
        out["detail"] = "stopped by the owner"
        return out
    decisions = decisions_of(ctx, card_id)
    if awaiting_owner(ctx, card_id, decisions):
        out["detail"] = "waiting for the owner's answer"
        return out
    heal = crew_heal.heal_card(card, ctx.dry)
    if heal and heal.get("blocked") and not crew_safety.is_script_block(heal["blocked"]):
        # the stale-block proof was refused by the safety floor: ask, don't decide (a changed script is decided)
        heal = dict(heal, proof_ask=proof_blocked_ask(card_id, heal["command"], heal["blocked"]))
    if heal and heal.get("fixed"):
        out.update(action="heal:%s" % heal["class"], detail=heal["action"])
        return out
    stopped_state = card["status"] in ("blocked", "triage")
    held_ready = card["status"] == "ready" and bool(heal)        # a remedy ran and could not fix it
    if not (stopped_state or held_ready):
        out["detail"] = "%s: nothing to decide" % card["status"]
        return out
    triggers = [e for e in events if e["kind"] in STOP_EVENT_KINDS] or events
    trigger = triggers[-1]
    if any(d.get("for_event") == trigger["id"] and d.get("decision") != "error" for d in decisions):
        out["detail"] = "already decided for event %s" % trigger["id"]
        return out
    if heal and heal.get("proof_ask"):
        dec, source, pending = heal["proof_ask"], "heal", False
    else:
        dec, source, pending = resolve(ctx, card, decisions, trigger)
    if dec["decision"] == "error":
        out.update(action="error", detail=dec["problem"], pending=True)
        if not ctx.dry:
            record_decision(ctx, card, trigger, dec, dec["problem"], False)
        return out
    if ctx.dry:
        out.update(action="would %s" % dec["decision"], detail=json.dumps(dec)[:240])
        return out
    try:
        ok, result = apply_decision(ctx, card, decisions, dec)
    except Exception as exc:  # noqa: BLE001 - a decision that cannot be applied goes to the owner, not a loop
        ok, result = False, "%s: %s" % (type(exc).__name__, exc)
    record_decision(ctx, card, trigger, dec, result, ok)
    if not ok and dec["decision"] != "ask_owner":
        ask = {"decision": "ask_owner", "question": "The coordinator's %s could not be applied (%s). What "
                                                    "should happen to this card?" % (dec["decision"], result[:160])}
        ok, result = apply_ask_owner(ctx, card, ask["question"])
        record_decision(ctx, card, trigger, ask, result, ok)
        dec = ask
    out.update(action=dec["decision"] if ok else "%s failed" % dec["decision"], detail=result, pending=not ok)
    return out


# ------------------------------------------------------------------------------------ one pass


def has_work(board=None):
    """True when a pass would do something: no cursor yet (it initialises one) or a crew event newer than the
    cursor. The same predicate run_pass reads, so False is exactly a pass that exits with 0 events. Any error
    answers True: a broken check must cost one extra pass, never a missed card."""
    try:
        db = board_db(board)
        if not os.path.exists(db):
            return False
        cursor = load_cursor(board)
        if cursor is None or crew_notify.has_pending(crew_notify.state_file(board)):
            return True               # a send that failed last pass waits for its retry (crew_notify)
        marks = ",".join("?" * len(EVENT_KINDS))
        rows = q(types.SimpleNamespace(db=db), "select 1 from task_events where id > ? and kind in (%s) limit 1"
                 % marks, (cursor,) + EVENT_KINDS)
        return bool(rows)
    except Exception:  # noqa: BLE001
        return True


def notify_baseline(db, board=None):
    """When the owner's first notify run counts history from: the time of the event this loop's cursor sits on.
    What the coordinator had not yet handled when notify was installed is new to the owner too; everything
    before it is old. None (now) when there is no cursor yet."""
    try:
        cursor = load_cursor(board)
        rows = q(types.SimpleNamespace(db=db), "select created_at from task_events where id = ?", (cursor,)) \
            if cursor is not None else []
        return rows[0]["created_at"] if rows else None
    except Exception:  # noqa: BLE001
        return None


def run_pass(ctx, only_card=None, since=None):
    """Read the events since the cursor, handle each card once on its newest event, then move the cursor."""
    report = {"board": ctx.db, "cursor_from": None, "cursor_to": None, "events": 0, "cards": []}
    rows = q(ctx, "select coalesce(max(id), 0) as m from task_events")
    top = rows[0]["m"]
    cursor = since if since is not None else load_cursor(ctx.board)
    if cursor is None:
        if not ctx.dry:
            save_cursor(top, ctx.board)
        report.update(cursor_to=top, note="cursor initialised at the newest event; history is not replayed")
        return report
    report["cursor_from"] = cursor
    marks = ",".join("?" * len(EVENT_KINDS))
    events = q(ctx, "select id, task_id, kind, payload, created_at from task_events where id > ? and id <= ? "
                    "and kind in (%s) order by id" % marks, (cursor, top) + EVENT_KINDS)
    if only_card:
        events = [e for e in events if e["task_id"] == only_card]
    report["events"] = len(events)
    by_card = {}
    for ev in events:
        by_card.setdefault(ev["task_id"], []).append(ev)
    pending = False
    for card_id, evs in by_card.items():
        try:
            res = handle_card(ctx, card_id, evs)
        except Exception as exc:  # noqa: BLE001 - one bad card must not stop the batch
            res = {"card": card_id, "action": "error", "detail": "%s: %s" % (type(exc).__name__, exc),
                   "pending": True}
        report["cards"].append(res)
        pending = pending or res["pending"]
        if res["action"] != "skip":
            ctx.say("%-12s %-22s %s" % (res["card"], res["action"], res["detail"][:160]))
    # The cursor moves only when every card in the batch was handled; a pending one repeats next pass.
    if not ctx.dry and not pending and not only_card and since is None:
        save_cursor(top, ctx.board)
        report["cursor_to"] = top
    return report


def main():
    crew_card.reexec_under_hermes_python(os.path.abspath(__file__))     # leaving triage needs hermes_cli
    ap = argparse.ArgumentParser(description="the crew coordinator loop: one pass")
    ap.add_argument("--once", action="store_true", help="one pass and exit (the only mode)")
    ap.add_argument("--board", default=None, help="board slug (the dispatch tick names it)")
    ap.add_argument("--dry-run", action="store_true", help="decide, but change and record nothing")
    ap.add_argument("--card", default=None, help="only this card id")
    ap.add_argument("--since", type=int, default=None,
                    help="read events after this id instead of the cursor (a backfill; the cursor is not moved)")
    ap.add_argument("--probe", action="store_true", help="also handle probe fixture cards (proofs pass this)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    db = board_db(a.board)
    if not os.path.exists(db):
        print("no board: %s" % db)
        return 2
    os.environ["HERMES_KANBAN_DB"] = db
    if a.board and a.board != "default":
        os.environ["HERMES_KANBAN_BOARD"] = a.board
    crew_heal.KANBAN_DB = db
    crew_handoff.KANBAN_DB = db
    if not a.dry_run and not take_lock(a.board):
        print("another coordinator pass holds the lock")
        return 3
    try:
        say = (lambda *_: None) if a.json else print
        baseline = notify_baseline(db, a.board)
        report = run_pass(Ctx(db, a.board, a.dry_run, a.probe, say=say), only_card=a.card, since=a.since)
        if not a.dry_run:     # the owner's return path rides on the pass: done, a new question, an abandon
            try:
                report["notified"] = [list(n) for n in crew_notify.run(db, crew_notify.state_file(a.board), say=say,
                                                                baseline=baseline)]
            except Exception as exc:  # noqa: BLE001 - a failed message never fails the pass
                say("crew notify error: %s: %s" % (type(exc).__name__, str(exc)[:160]))
    finally:
        if not a.dry_run:
            drop_lock(a.board)
    if a.json:
        print(json.dumps(report, indent=1, default=str))
    else:
        print("coordinator pass%s: %d event(s), %d card(s)%s" % (
            " (dry run)" if a.dry_run else "", report["events"], len(report["cards"]),
            ("; " + report["note"]) if report.get("note") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
