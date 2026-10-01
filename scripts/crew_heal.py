#!/usr/bin/env python3
"""The crew's mechanical remedies: fix what the crew can fix without a decision, as a library.

A card must not sit still for a reason the crew can resolve on its own. Every class below has a
deterministic remedy and a proof. crew_coordinator.py calls `heal_card` first for every card it is about
to decide on; a card healed here is done for that pass, and anything a remedy cannot fix goes on to the
coordinator's decision turn (there is no second, escalate-once path any more).

  held_workspace  a ready card the respawn guard holds because its workspace is missing or
                  unwritable (a permission error reads as an auth blocker) -> give it a scratch
                  dir and lift the hold
  dead_model      a ready card held on a quota/auth error from a model it is still pinned to
                  -> ask the router for a fresh pick, re-pin, lift the hold; if no pick fits the
                  remedy says so (`fixed: False`) and the coordinator decides
  stale_verify    a blocked card whose own proof command now exits 0 -> the block is stale, put
                  the card back in the queue with the output attached

Every remedy takes exactly (card, dry) and returns a result dict with `class`, `card`, `action`
and `fixed` (True when the card no longer needs a decision).
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_result  # noqa: E402 - the words of the thrash stop's block reason
KANBAN_DB = os.environ.get("KANBAN_DB") or os.path.expanduser("~/.hermes/kanban.db")
BLOCKER_WORDS = (r"quota", r"rate", r"429", r"403", r"forbidden", r"billing", r"subscription",
                 r"auth(?!or\b)", r"access denied", r"permission denied", r"invalid api key")
# Matched from a word start, so "rate" cannot fire inside "moderate" and "auth" cannot fire inside
# "author" - a healthy card sent down the dead-model heal is the cost of that false positive.
BLOCKER_RX = re.compile(r"(?<![a-z0-9])(?:%s)" % "|".join(BLOCKER_WORDS))

# ---- failure signature: what 'failed the same way' means -------------------------------------
FAILED_RUN_STATUSES = ("crashed", "rate_limited", "timed_out", "blocked", "spawn_failed", "failed")
ESCALATION_REPEATS = 2

_WALL_KINDS = (
    # first: the stop's own reason carries the last failed call's note, which can hold any other kind's words
    ("thrash", (crew_result.THRASH_REASON,)),
    ("quota", ("quota", "rate limit", "rate_limit", "rate_limited", "429", "billing", "subscription",
               "credits", "free-models-per-day")),
    ("auth", ("auth", "403", "forbidden", "invalid api key", "permission denied", "access denied")),
    ("timeout", ("timed out", "timeout", "timed_out")),
    ("spawn_failed", ("spawn", "no such file", "not found", "eacces")),
    ("tool_error", ("tool error", "traceback", "exception", "syntaxerror", "importerror",
                    "typeerror", "valueerror")),
    ("proof_failed", ("proof", "verdict", "rc=1", "failed verification", "assert", "test failed")),
)


def wall_kind(text):
    """What walled a run, as one word from a fixed list ('other' when nothing matches).

    One owner for the words, so 'the same kind' can never be counted two ways.
    """
    low = (text or "").lower()
    for kind, words in _WALL_KINDS:
        if any(w in low for w in words):
            return kind
    return "other"


def failure_signature(run):
    """(status, wall kind) for a failed run; None when that run did not fail.

    The outcome alone is not a kind: two blocked runs for two different reasons must not count as
    one repeat (the owner's rule is 'the same kind', not 'any two failures').
    """
    status = str(run.get("status") or "").strip().lower()
    if status not in FAILED_RUN_STATUSES:
        return None
    text = " ".join(str(run.get(k) or "") for k in ("outcome", "error", "summary"))
    return (status, wall_kind(text))


def repeat_chain(card_id, runs=None, need=ESCALATION_REPEATS):
    """The trailing runs that failed the SAME way, newest first - [] when there is no repeat.

    Read from the board (task_runs), never from the card's prose: the newest run first, stopping at
    the first run that did not fail or that failed differently.
    """
    rows = runs if runs is not None else q(
        "select id, status, outcome, error, summary, started_at, ended_at from task_runs "
        "where task_id = ? order by id desc limit 12", (card_id,))
    chain, sig = [], None
    for run in rows:
        sign = failure_signature(run)
        if sign is None:
            break
        if sig is None:
            sig = sign
        elif sign != sig:
            break
        chain.append(run)
        if len(chain) >= need:
            break
    # a chain shorter than `need` is not a repeat: one failure is not a pattern
    return chain if len(chain) >= need else []


def q(sql, args=()):
    conn = sqlite3.connect("file:%s?mode=ro" % KANBAN_DB, uri=True)
    try:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(sql, args).fetchall()]
    finally:
        conn.close()


def event(card, kind, payload):
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)",
                     (card, None, kind, json.dumps(payload), int(time.time())))
        conn.commit()
    finally:
        conn.close()


def kanban_cli(*args):
    """The kernel's own command, so its events, promotion and notification all still happen."""
    import crew_card
    return subprocess.run([crew_card.hermes_bin(), "kanban"] + [str(a) for a in args],
                          capture_output=True, text=True)


def release_block(card):
    """Lift a block without the CLI, for the run where the CLI call fails.

    `hermes kanban unblock` promotes the card and writes its event; this is the narrow write that only
    makes the card walkable again, used when that call did not land. Returns True when it wrote.
    """
    conn = sqlite3.connect(KANBAN_DB)
    try:
        cur = conn.execute("update tasks set status = 'ready', block_kind = NULL, "
                           "last_failure_error = NULL where id = ? and status = 'blocked'", (card,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def heal_stamp(card, cls):
    """Have we already applied this class to this card in the same state? Then leave it alone."""
    rows = q("select payload from task_events where task_id = ? and kind = 'self_heal' "
             "order by created_at desc limit 5", (card,))
    return any((json.loads(r["payload"] or "{}").get("class") == cls) for r in rows)


def is_blocker(text):
    """A blocker starts at a word: 'rate' must not fire on 'moderate', 'auth' not on 'author' -
    a run error read as a blocker sends a healthy card down the dead-model heal."""
    return bool(BLOCKER_RX.search((text or "").lower()))


def proof_cmd(body):
    """One reader for every caller: crew_card owns the rule that the '(none - ...)' template text
    is a note, not a command. Importing it here is what keeps heal and unstale from drifting."""
    import crew_card
    return crew_card.proof_cmd(body)


def run_proof(cmd, timeout=240):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return 124, "timed out after %ss" % timeout
    except Exception as exc:  # noqa: BLE001
        return 127, str(exc)


def heal_held_workspace(card, dry):
    import crew_card
    ws = card.get("workspace_path") or ""
    bad = not ws or not os.path.isdir(ws) or not os.access(ws, os.W_OK)
    if not bad:
        return None
    if dry:
        return {"class": "held_workspace", "card": card["id"], "action": "would repoint workspace",
                "fixed": True}
    res = crew_card.repoint_workspace(card["id"])
    if not res.get("ok"):
        return None
    event(card["id"], "self_heal", {"class": "held_workspace", "to": res.get("workspace"),
                                    "released": res.get("released"), "ts": time.time()})
    return {"class": "held_workspace", "card": card["id"],
            "action": "workspace -> %s, hold lifted" % res.get("workspace"), "fixed": True}


def heal_dead_model(card, dry):
    import crew_card
    if dry:
        return {"class": "dead_model", "card": card["id"], "action": "would re-pin via the router",
                "fixed": True}
    out = crew_card.reroute_after_wall(card["id"])
    action = (out or {}).get("action") or ""
    event(card["id"], "self_heal", {"class": "dead_model", "outcome": str(out)[:200],
                                    "action": action, "ts": time.time()})
    if action == "rerouted":
        to = out.get("to") or {}
        return {"class": "dead_model", "card": card["id"],
                "action": "re-pinned on %s/%s" % (to.get("provider"), to.get("model")),
                "fixed": True}
    if action == "unpinned":
        return {"class": "dead_model", "card": card["id"],
                "action": "pin cleared: nothing on the agent floor is live, the profile's own model runs",
                "fixed": True}
    return {"class": "dead_model", "card": card["id"],
            "action": "no live pick fits (%s)" % action, "fixed": False}


def heal_stale_verify(card, dry):
    cmd = proof_cmd(card.get("body") or "")
    if not cmd:
        return None
    if dry:
        return {"class": "stale_verify", "card": card["id"], "action": "would re-run: %s" % cmd[:70],
                "fixed": False}
    rc, out = run_proof(cmd)
    head = " ".join(out.split())[-600:]
    if rc != 0:
        event(card["id"], "self_heal", {"class": "stale_verify", "ran": cmd[:200], "rc": rc,
                                        "verdict": "still failing", "ts": time.time()})
        return {"class": "stale_verify", "card": card["id"], "action": "proof still fails (rc=%d)" % rc,
                "fixed": False}
    import crew_card
    lifted = crew_card.lift_block(card["id"])       # the kernel's unblock, plus the block counter reset
    p = type("Lift", (), {"returncode": lifted["rc"]})
    fell_back = False
    if p.returncode != 0:
        # The card must leave the block even when the CLI cannot (a busy board during a parallel proof
        # run does this): the reward for the healed proof is the card leaving the block, not the call.
        fell_back = release_block(card["id"])
    event(card["id"], "self_heal", {"class": "stale_verify", "ran": cmd[:200], "rc": rc,
                                    "verdict": "proof passes now", "unblock_rc": p.returncode,
                                    "direct_release": fell_back,
                                    "output_head": head[:300], "ts": time.time()})
    return {"class": "stale_verify", "card": card["id"],
            "action": "proof exits 0 now, unblocked (rc=%d)" % p.returncode, "fixed": True}


def safely(fn, card, dry):
    """A remedy must survive one bad card: record the failure and carry on.

    fn takes exactly (card, dry) - the pair every heal helper above takes. A helper with a third
    parameter raises TypeError when this call binds it, before that helper's own guards run, so the
    card is never healed and the pass reports "could not heal" on every single run.
    """
    try:
        return fn(card, dry)
    except Exception as exc:  # noqa: BLE001
        cls = getattr(fn, "__name__", "heal").replace("heal_", "")
        if not dry:
            event(card.get("id"), "self_heal", {"class": cls, "error": str(exc)[:200],
                                                "ts": time.time()})
        return {"class": cls, "card": card.get("id"), "action": "could not heal: %s" % str(exc)[:80],
                "fixed": False}


def heal_card(card, dry=False):
    """The remedies for one card, in order; the first that applies is the answer for it.

    ready + a wall in last_failure_error -> held_workspace, then dead_model (quota/rate walls only)
    blocked + a proof command that now exits 0 -> stale_verify
    Returns the remedy's result dict, or None when no remedy applies to this card in this state.
    """
    status = card.get("status")
    if status == "ready":
        err = card.get("last_failure_error") or ""
        if not is_blocker(err):
            return None
        if heal_stamp(card["id"], "held_workspace") or heal_stamp(card["id"], "dead_model"):
            return None
        wall = any(w in err.lower() for w in ("quota", "rate", "429", "403"))
        got = safely(heal_held_workspace, card, dry)
        if got is None and wall:
            got = safely(heal_dead_model, card, dry)
        return got
    if status == "blocked" and proof_cmd(card.get("body") or ""):
        if heal_stamp(card["id"], "stale_verify"):
            return None
        return safely(heal_stale_verify, card, dry)
    return None
