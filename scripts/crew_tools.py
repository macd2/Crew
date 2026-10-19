#!/usr/bin/env python3
"""The crew functions the model used to reach through a shell line, as Hermes tools (toolset `crew`).

A tool call carries typed arguments: nothing for the model to quote, and the guards match a name instead of
regex-ing a command string apart. Each handler calls the function the CLI subcommand calls (crew_card.run_verdict,
record_progress, run_plan, crew_lessons.add, crew_safety.proof_check, crew_diagnose), so there is one
implementation and two entry points.

Hermes wants a plugin tool handler to return a JSON string, success and error alike, and never to raise. Every
handler here therefore answers `json.dumps(obj)`: the structured result, or `{"error": "<message>"}`."""
import json
import logging
import os
import sys

HERE_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if HERE_SCRIPTS not in sys.path:
    sys.path.insert(0, HERE_SCRIPTS)
import crew_card  # noqa: E402 - the card functions the CLI also calls
import crew_diagnose as _diag  # noqa: E402 - the blocked-card reader (the tool of the same name is defined below)
import crew_safety  # noqa: E402 - the proof check and the safety mode

log = logging.getLogger(__name__)
TOOLSET = "crew"
VERIFIER_ROLE = "verifier"


def _out(obj):
    return json.dumps(obj, default=str)


def _guarded(fn):
    """A handler never raises: a refusal (ValueError) and any other failure come back as one error line."""
    def handler(args, **kwargs):
        try:
            if not isinstance(args, dict):
                return _out({"error": "arguments must be an object, got %s" % type(args).__name__})
            return fn(args)
        except ValueError as exc:
            return _out({"error": "refused: %s" % exc})
        except Exception as exc:  # noqa: BLE001 - the model gets a line, not a traceback
            return _out({"error": "%s: %s" % (type(exc).__name__, exc)})
    handler.__name__ = fn.__name__
    handler.__doc__ = fn.__doc__
    return handler


def _need(args, key):
    val = args.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        raise ValueError("%s is required" % key)
    return val


def _card_arg(args):
    val = args.get("card") if args.get("card") is not None else args.get("card_id")
    if val is None or (isinstance(val, str) and not val.strip()):
        raise ValueError("card is required")
    return str(val).strip()


def _is_verifier():
    """The calling profile is the verifier role. Only the prefixed name counts: role_profile() falls back to the
    current profile when the role has none, which would make every caller a verifier."""
    return crew_card.current_profile() == crew_card.profile_prefix() + VERIFIER_ROLE


@_guarded
def crew_verdict(args):
    """The card's owner-confirmed proof, run and recorded under the calling profile. No command argument."""
    card = _card_arg(args)
    kw = {}
    if args.get("timeout") is not None:
        kw["timeout"] = int(args["timeout"])
    res = crew_card.run_verdict(card, by=crew_card.current_profile(), **kw)
    if res.get("error"):
        return _out({"error": res["error"]})
    out = {"verdict": res["verdict"], "rc": res.get("proof_rc"), "fails": res.get("fails"),
           "proof_command": res.get("proof_command"), "output": res.get("output", ""), "file": res.get("file")}
    for key in ("handed_back", "blocked"):
        if res.get(key):
            out[key] = res[key]
    return _out(out)


@_guarded
def crew_progress(args):
    """List a card's units, or mark one pass/fail with evidence. `by` comes from the profile, never an argument."""
    card = _card_arg(args)
    result = args.get("result")
    if result not in (None, "pass", "fail"):
        raise ValueError('result must be "pass" or "fail"')
    res = crew_card.record_progress(card, unit=args.get("unit") or None,
                                    result=None if result is None else result == "pass",
                                    evidence=args.get("evidence"),
                                    by="verifier" if _is_verifier() else "writer")
    return _out({k: res[k] for k in ("card", "unit", "result", "by", "passed", "total", "units")})


@_guarded
def crew_proof_check(args):
    """What Hermes's own danger check says about a proof command, and the safety mode proofs run in."""
    line = crew_safety.proof_check(str(_need(args, "command")))
    check, _sep, reason = line.partition(": ")
    return _out({"check": check, "reason": reason, "safety_mode": crew_safety.permanent_mode()})


@_guarded
def crew_lesson(args):
    """Record one lesson for a role (the file the next turn of that role is shown)."""
    import crew_lessons
    role = str(_need(args, "role"))
    crew_lessons.add(role, str(_need(args, "text")))
    return _out({"lesson": role, "file": crew_lessons.path()})


@_guarded
def crew_plan(args):
    """Split work into a parent card, independent children and a close-out; a gap in the spec is refused."""
    spec = args.get("spec")
    if not isinstance(spec, dict):
        raise ValueError("spec must be the plan object")
    dry = bool(args.get("dry_run"))
    res = crew_card.run_plan(spec, dry_run=dry)
    return _out(dict(res, dry_run=dry))


@_guarded
def crew_diagnose(args):
    """Why each card in one board state is there: reason, wait, runs, failures, spend, coordinator decision."""
    card = str(args.get("card") or args.get("card_id") or "").strip() or None
    state = str(args.get("state") or "blocked").strip().lower()
    if not card and state not in _diag.STATES:
        raise ValueError("unknown state %r: %s" % (state, "|".join(_diag.STATES)))
    rows = _diag.board_rows(None if card else state, card)
    if rows is None:
        return _out({"error": "no board to read: HERMES_KANBAN_DB, KANBAN_DB and %s are all missing"
                              % os.path.join(crew_card.base_home(), "kanban.db")})
    cards = _diag.cards_from_rows(rows)
    return _out({"state": state, "card": card, "count": len(cards), "text": _diag.render(cards, state, card)})


HANDLERS = {"crew_verdict": crew_verdict, "crew_progress": crew_progress, "crew_proof_check": crew_proof_check,
            "crew_lesson": crew_lesson, "crew_plan": crew_plan, "crew_diagnose": crew_diagnose}


def _obj(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required)}


SCHEMAS = {
    "crew_verdict": {
        "name": "crew_verdict",
        "description": "Run the card's owner-confirmed proof command and record the PASS/FAIL line in the verdict "
                       "log; takes no command of its own.",
        "parameters": _obj({"card": {"type": "string", "description": "the card id"},
                            "card_id": {"type": "string", "description": "alias for card"},
                            "timeout": {"type": "integer", "description": "seconds the proof may run (default 300)"}})},
    "crew_progress": {
        "name": "crew_progress",
        "description": "List a card's units of work, or mark one unit pass or fail with evidence; the recording "
                       "role is taken from the calling profile, not from an argument.",
        "parameters": _obj({"card": {"type": "string", "description": "the card id"},
                            "card_id": {"type": "string", "description": "alias for card"},
                            "unit": {"type": "string", "description": "the unit to mark; omit to list"},
                            "result": {"type": "string", "enum": ["pass", "fail"]},
                            "evidence": {"type": "string"}})},
    "crew_proof_check": {
        "name": "crew_proof_check",
        "description": "Ask Hermes's danger check about a proof command before it is proposed (ok, flagged or "
                       "hardline) and report the safety mode proofs run in; it runs nothing.",
        "parameters": _obj({"command": {"type": "string"}}, ["command"])},
    "crew_lesson": {
        "name": "crew_lesson",
        "description": "Record one short lesson for a crew role; an agent may not write lessons for the role `all`.",
        "parameters": _obj({"role": {"type": "string", "description": "worker, content, verifier, coordinator"},
                            "text": {"type": "string", "description": "one or two lines"}}, ["role", "text"])},
    "crew_plan": {
        "name": "crew_plan",
        "description": "Open a parent card, independent children and a close-out from a plan; a plan with a gap, "
                       "no children or two writers on one artifact is refused, and opening is refused outside a "
                       "/crew turn.",
        "parameters": _obj({"spec": {"type": "object", "description": "the plan: title, goal, children[]"},
                            "dry_run": {"type": "boolean", "description": "check the plan, open nothing"}},
                           ["spec"])},
    "crew_diagnose": {
        "name": "crew_diagnose",
        "description": "Read why each card in one board state is there (reason, wait, runs, spend, the "
                       "coordinator's last decision); read-only, an unknown state is refused.",
        "parameters": _obj({"state": {"type": "string", "enum": list(_diag.STATES)},
                            "card": {"type": "string", "description": "one card id, any state"},
                            "card_id": {"type": "string", "description": "alias for card"}})},
}


def _present():
    """The tools are offered only where the card script they call is installed."""
    return os.path.isfile(os.path.join(HERE_SCRIPTS, "crew_card.py"))


def register_tools(ctx):
    """Register the six tools. One failing registration is logged and does not stop the others."""
    done = []
    for name, handler in HANDLERS.items():
        schema = SCHEMAS[name]
        try:
            ctx.register_tool(name=name, toolset=TOOLSET, schema=schema, handler=handler,
                              description=schema["description"], check_fn=_present)
            done.append(name)
        except Exception:  # noqa: BLE001 - the others still register
            log.exception("crew: could not register tool %s", name)
    return done
