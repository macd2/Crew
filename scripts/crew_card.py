#!/usr/bin/env python3
"""Crew card tool: open contract cards on the kanban board and record verifier verdicts.

Deterministic, stdlib only. Used by the plugin's kanban_create hooks, by the coordinator loop and by the
crew-verifier profile. The contract gate lives here, not only in a prompt: a card is refused
unless it carries a goal, the artifact, where it lands, who it is for, "Done when:", a proof
command the verifier can run and a token budget.

  crew_card.py open   --title T --goal G --role worker|content --artifact A --lands L
                      --audience W --done-when D --proof-cmd C [--budget N] [--constraints X]
                      [--parent ID ...] [--max-runtime 60m] [--dry-run] [--json]
  crew_card.py plan   --spec plan.json [--dry-run] [--json]
      parent contract card + independent child cards (one writer each, distinct artifacts)
      + a coordinator close-out card that waits for every child.
  crew_card.py verdict --card ID [--command '<extra check>'] [--timeout 300]
      runs the card's proof command itself, stores the raw output with the verdict under
      $HERMES_HOME/crew/verdicts/<card>.jsonl; exit 0 PASS, 1 FAIL, 3 second FAIL (handed back: request-changes or a transient block).
  crew_card.py retry --card ID [--budget N] [--dry-run]   raise the ceiling, unblock, run again
  crew_card.py show-contract --card ID
      prints only the contract fields of a card (what the verifier may read).
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if HERE_SCRIPTS not in sys.path:
    sys.path.insert(0, HERE_SCRIPTS)
import crew_safety  # noqa: E402 - the one runner of a proof command, and the mode it runs in

WRITER_ROLES = ("worker", "content")
DEFAULT_PREFIX = "crew-"
DEFAULT_BUDGET = 1000000
BUDGET_FLOOR = 120000   # used when roles.json carries no budget_floor_tokens
MAX_CONSECUTIVE_FAILURES = 5   # used when roles.json carries no max_consecutive_failures
MAX_WINDOW_FAILURES = 8        # used when roles.json carries no max_window_failures
FAILURE_WINDOW_CALLS = 25      # used when roles.json carries no failure_window_calls
DEFAULT_RUNTIME = "60m"
OUTPUT_KEEP = 4000
SELF = os.path.abspath(__file__)


def hermes_home():
    return os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")


def base_home():
    h = os.path.abspath(hermes_home())
    if os.path.basename(os.path.dirname(h)) == "profiles":
        return os.path.dirname(os.path.dirname(h))
    return h


def current_profile():
    h = os.path.abspath(hermes_home())
    if os.path.basename(os.path.dirname(h)) == "profiles":
        return os.path.basename(h)
    return "default"


def owner_profile():
    """The profile crew was installed into: the owner's own chat profile, where cards are opened from and
    reported back to. CREW_OWNER_PROFILE wins; else the name install.py recorded in
    <base home>/crew/owner.json; else "default" (the base home itself)."""
    env = (os.environ.get("CREW_OWNER_PROFILE") or "").strip()
    if env:
        return env
    try:
        with open(os.path.join(base_home(), "crew", "owner.json")) as fh:
            name = str(json.load(fh).get("profile") or "").strip()
        if name:
            return name
    except (OSError, ValueError, AttributeError):
        pass
    return "default"


def profile_home(name):
    """A profile's home: <base home>/profiles/<name>, or the base home itself for "default"."""
    name = (name or "").strip()
    if not name or name == "default":
        return base_home()
    return os.path.join(base_home(), "profiles", name)


def owner_home():
    return profile_home(owner_profile())


def package_dir():
    """The crew package checkout (the one install.py ran from): CREW_PKG, else the checkout this script sits in,
    else the path install.py recorded in <base home>/crew/owner.json. None when none of them is a checkout."""
    here = os.path.dirname(HERE_SCRIPTS)
    cands = [os.environ.get("CREW_PKG") or "", here]
    try:
        with open(os.path.join(base_home(), "crew", "owner.json")) as fh:
            cands.append(str(json.load(fh).get("package") or ""))
    except (OSError, ValueError, AttributeError):
        pass
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "install.py")) and os.path.isfile(os.path.join(c, "plugin.yaml")):
            return c
    return None


def dashboard_url():
    """Where the crew board is reached, for links: CREW_DASHBOARD_URL, else the public URL install.py --publish
    recorded in <base home>/crew/owner.json, else the local http service."""
    env = (os.environ.get("CREW_DASHBOARD_URL") or "").strip()
    if env:
        return env.rstrip("/")
    try:
        with open(os.path.join(base_home(), "crew", "owner.json")) as fh:
            url = str(json.load(fh).get("dashboard_url") or "").strip()
        if url:
            return url.rstrip("/")
    except (OSError, ValueError, AttributeError):
        pass
    return "http://127.0.0.1:%s" % (os.environ.get("CREW_GRAPH_PORT") or "8799")


def hermes_bin():
    return os.environ.get("HERMES_BIN") or shutil.which("hermes") or os.path.expanduser("~/.local/bin/hermes")


def config_value(key, section="crew", home=None):
    """Read one scalar of a top-level section of a profile's config.yaml (this profile's `crew:` by default)
    without a YAML dependency."""
    path = os.path.join(home or hermes_home(), "config.yaml")
    try:
        with open(path) as fh:
            lines = fh.read().splitlines()
    except OSError:
        return None
    inside = False
    for line in lines:
        if re.match(r"^%s:\s*$" % re.escape(section), line):
            inside = True
            continue
        if inside:
            if line and not line.startswith(" "):
                break
            m = re.match(r"^\s+%s:\s*(.+?)\s*$" % re.escape(key), line)
            if m:
                return m.group(1).strip("'\"")
    return None


def profile_prefix():
    return os.environ.get("CREW_PROFILE_PREFIX") or config_value("profile_prefix") or DEFAULT_PREFIX


def profile_exists(name):
    if name == "default":
        return True
    return os.path.isfile(os.path.join(base_home(), "profiles", name, "config.yaml"))


def role_profile(role):
    """Assignee for a role: <prefix><role> when that profile exists, else the current profile."""
    name = profile_prefix() + role
    return name if profile_exists(name) else current_profile()


def roles_defaults():
    for path in (os.path.join(hermes_home(), "roles", "crew", "roles.json"),
                 os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "roles", "roles.json")):
        try:
            with open(path) as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def budget_floor():
    val = roles_defaults().get("budget_floor_tokens")
    return val if isinstance(val, int) else BUDGET_FLOOR


def max_consecutive_failures():
    """Failed tool calls in a row after which a role's run is stopped (the plugin's thrash stop)."""
    val = roles_defaults().get("max_consecutive_failures")
    return val if isinstance(val, int) and val > 0 else MAX_CONSECUTIVE_FAILURES


def max_window_failures():
    """Failed tool calls among the last failure_window_calls after which a role's run is stopped: the thrash
    stop for a run whose failures are scattered between ok results, which the streak never sees."""
    val = roles_defaults().get("max_window_failures")
    return val if isinstance(val, int) and val > 0 else MAX_WINDOW_FAILURES


def failure_window_calls():
    val = roles_defaults().get("failure_window_calls")
    return val if isinstance(val, int) and val > 0 else FAILURE_WINDOW_CALLS


def default_budget(role):
    data = roles_defaults()
    for r in data.get("roles", []):
        if r.get("name") == role and isinstance(r.get("budget_tokens"), int):
            return r["budget_tokens"]
    val = data.get("default_budget_tokens")
    return val if isinstance(val, int) else DEFAULT_BUDGET


DEFAULT_BOARD = "default"
# Hermes's own slug rule (hermes_cli/kanban_db.py _BOARD_SLUG_RE): strict enough to stop traversal and separators.
SLUG_RX = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def kanban_home():
    """Root the boards hang off, as Hermes's kanban_home(): HERMES_KANBAN_HOME, else the base home."""
    override = (os.environ.get("HERMES_KANBAN_HOME") or "").strip()
    return os.path.expanduser(override) if override else base_home()


def _valid_board_slug(candidate):
    """The slug Hermes would accept (stripped, lowercased, SLUG_RX), or "" for an empty or malformed one, so a
    stale or hand-edited `current` such as `../x` never becomes a path."""
    s = str(candidate or "").strip().lower()
    return s if SLUG_RX.match(s) else ""


def _board_holds_live_board(b_dir):
    """A named board dir is a board only with its board.json (Hermes's identity marker) and not archived: an
    archived board leaves a tombstone board.json that must not be revived. A malformed board.json still marks a
    board, as Hermes's read_board_metadata treats it."""
    meta = os.path.join(b_dir, "board.json")
    if not os.path.isfile(meta):
        return False
    try:
        with open(meta, encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return True
    return not (isinstance(data, dict) and data.get("archived"))


def _kanban_db_fallback():
    """The bare-interpreter resolver (no hermes_cli to ask), mirroring hermes_cli.kanban_db.kanban_db_path():
    HERMES_KANBAN_BOARD, then <kanban home>/kanban/current, each only for a valid slug naming a live board,
    else `default`, whose db stays at <kanban home>/kanban.db. None when the resolved file does not exist."""
    root = kanban_home()
    slug = DEFAULT_BOARD
    candidates = [os.environ.get("HERMES_KANBAN_BOARD") or ""]
    try:
        with open(os.path.join(root, "kanban", "current"), encoding="utf-8-sig") as fh:
            candidates.append(fh.read())
    except OSError:
        pass
    for cand in candidates:
        s = _valid_board_slug(cand)
        if s == DEFAULT_BOARD:
            break
        if s and _board_holds_live_board(os.path.join(root, "kanban", "boards", s)):
            slug = s
            break
    if slug == DEFAULT_BOARD:
        path = os.path.join(root, "kanban.db")
    else:
        path = os.path.join(root, "kanban", "boards", slug, "kanban.db")
    return path if os.path.exists(path) else None


def _hermes_kanban_db_path():
    """hermes_cli.kanban_db.kanban_db_path() as a string, or None when hermes_cli is not importable here."""
    try:
        kb, _ = hermes_kb()
        return str(kb.kanban_db_path())
    except Exception:
        return None


def kanban_db():
    """The crew's board file, or None. A HERMES_KANBAN_DB / KANBAN_DB pin naming an existing file wins (the proof
    board sets them); then Hermes's own resolver where hermes_cli is importable; else _kanban_db_fallback()."""
    for path in (os.environ.get("HERMES_KANBAN_DB") or "", os.environ.get("KANBAN_DB") or ""):
        path = path.strip()
        if path and os.path.exists(path):
            return path
    path = _hermes_kanban_db_path()
    if path is not None:
        return path if os.path.exists(path) else None
    return _kanban_db_fallback()


def card_row(card_id):
    db = kanban_db()
    if not db:
        return None
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        row = conn.execute("select id, title, status, assignee, body from tasks where id = ?",
                           (card_id,)).fetchone()
        conn.close()
        return row
    except Exception:
        return None


def card_pin(card_id):
    """(model_override, provider_override) the card was created with, or ('', '')."""
    db = kanban_db()
    if not db:
        return "", ""
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        row = conn.execute("select model_override, provider_override from tasks where id = ?",
                           (card_id,)).fetchone()
        conn.close()
    except Exception:
        return "", ""
    return ((row or ("", ""))[0] or "", (row or ("", ""))[1] or "")


def field(body, key):
    m = re.search(r"^\s*%s:\s*(.+)$" % re.escape(key), body or "", re.M | re.I)
    return m.group(1).strip() if m else None


def is_crew_body(body):
    """A crew card carries a Coordinator: or Role: line in its body (render_body writes both)."""
    return bool(re.search(r"^\s*(Coordinator|Role):", body or "", re.M | re.I))


# A card opened without a proof carries this prose where the command belongs (render_body below).
# It is a note to the owner, never something to hand to a shell: every reader of "proof command"
# goes through proof_cmd() so none of them can mistake it for a command.
NO_PROOF_RX = re.compile(r"^\s*\(\s*none\b", re.I)


def proof_cmd(body):
    """The proof command a card body names, or '' - the '(none - ...)' template text is not one."""
    m = re.search(r"^\s*proof command:\s*(.+)$", body or "", re.M | re.I)
    cmd = m.group(1).strip() if m else ""
    return "" if not cmd or NO_PROOF_RX.match(cmd) else cmd


# Every proof seeds its live-board fixture cards with this in tasks.created_by and deletes them in a
# finally, so it is the one marker that says "this card belongs to a run that is in flight right now".
PROBE_OWNER = "probe"

# The assignee every fixture card carries. No Hermes profile answers to this name, and the dispatcher
# claims a card only when its assignee resolves to one (`_profile_exists_fn` in the host's
# kanban_db_dispatch), so a fixture can never be picked up and worked by a real agent: measured
# 2026-09-30, fixtures seeded 'ready' with assignee crew-worker started 20 real crew-worker sessions in
# 20 minutes, and one of those runs edited the crew's own script mid-proof.
FIXTURE_ASSIGNEE = "crew-probe"


def probe_card(created_by):
    """True for a card a proof seeded on the live board (created_by='probe')."""
    return (created_by or "").strip().lower() == PROBE_OWNER


def filter_probes(cards, include_probe=False):
    """The card list a whole-board pass walks: another run's probe cards are left alone.

    The three board-wide passes (heal, unstale, triage) run every few minutes on a schedule while a proof is
    seeding and asserting on its own probe cards. A scheduled pass acting on that fixture is how the proof
    fails on its own probe - a lifted card lifted again, a probe card no longer blocked - which reads as a
    defect in the change that shipped. A proof passes include_probe=True (its `--probe` flag) because those
    cards are its own; nobody else ever needs it.
    """
    if include_probe:
        return list(cards)
    return [c for c in cards if not probe_card(c.get("created_by"))]


# ------------------------------------------------------------------ contract


REQUIRED = [("goal", "GOAL"), ("artifact", "Artifact"), ("lands", "Lands at"),
            ("audience", "For"), ("done_when", "Done when"), ("proof_cmd", "proof command")]


VERIFY_MODES = ("proof", "independent")
PROOF_MODES = crew_safety.PROOF_MODES


def contract_proof_mode(body):
    """The intake's `Proof mode:` line (the owner's per-card safety choice): "safe", "brave" or "". It is read
    once, when the card opens, and lives on in the card's snapshot; the body line itself decides nothing."""
    mode = (field(body, "Proof mode") or "").strip().lower()
    return mode if mode in PROOF_MODES else ""


def contract_proof_approved(body):
    """The intake's `Proof approved: yes` line. It is read for the contract round-trip only: `finish_card` ignores
    it for a flagged command, so it never binds a hash to the snapshot - a flagged proof runs only after the
    owner answers `/crew-proof <card> brave`."""
    return (field(body, "Proof approved") or "").strip().lower() in ("yes", "true")


# `closeout`: a split child. It carries no proof command of its own; the parent's owner-confirmed proof runs in the
# plan's close-out card once every child is done. Only `run_plan(closeout_proof=...)` (crew code) opens one: it is
# not a choice of `open --verify`, and a spec file cannot ask for it.
CLOSEOUT_MODE = "closeout"


# A proof command that runs a script from a `.crew/` folder (`python3 /x/site/.crew/verify.py`). The verifier writes
# that script, never the writer, so such a card is always `Verify: independent`.
PROOF_SCRIPT_RX = re.compile(r"(?:^|[\s'\"=/])\.crew/")


def proof_script_cmd(cmd):
    return bool(PROOF_SCRIPT_RX.search(str(cmd or "")))


def coerce_verify(mode, cmd):
    """`proof` becomes `independent` when the proof command runs a `.crew/` script: the one place the rule lives
    (verify_mode reads it back from a card, default_verify writes it into a new one)."""
    return "independent" if mode == "proof" and proof_script_cmd(cmd) else mode


def verify_mode(body):
    """The card's `Verify:` line: "proof" (the writer proves it, the coordinator audits), "independent" (a
    verifier session runs it too), or "" for a card opened before the line existed. A `proof` card whose proof
    command runs a `.crew/` script reads as `independent` (coerce_verify), whatever its line says."""
    mode = (field(body, "Verify") or "").strip().lower()
    return coerce_verify(mode, proof_cmd(body)) if mode in VERIFY_MODES + (CLOSEOUT_MODE,) else ""


INPUTS_RX = re.compile(r"^[ \t]*Inputs:[ \t]*(.*)$", re.I)
INPUTS_MAX = 2000       # characters: longer pasted text goes in a file the owner names


def inputs_block(body):
    """(first line index, last line index + 1) of the `Inputs:` field in a body, or None: the field line and the
    `>` quoted lines right under it (short pasted text), the one contract field that spans lines."""
    lines = (body or "").splitlines()
    for i, line in enumerate(lines):
        if INPUTS_RX.match(line):
            end = i + 1
            while end < len(lines) and lines[end].lstrip().startswith(">"):
                end += 1
            return i, end
    return None


def contract_inputs(body):
    """The card's `Inputs:` material as text: the paths / URLs on the field line, then any quoted pasted text
    (`> ...` lines), one entry per line. '' when the card names none."""
    block = inputs_block(body)
    if not block:
        return ""
    lines = (body or "").splitlines()[block[0]:block[1]]
    head = INPUTS_RX.match(lines[0]).group(1).strip()
    return "\n".join(([head] if head else []) + [ln.strip() for ln in lines[1:]])


def render_inputs(text):
    """The `Inputs:` lines for a body: paths and URLs on the field line, every other line quoted with `> `."""
    entries = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]
    if not entries:
        return []
    head = "" if entries[0].startswith(">") else entries.pop(0)
    return ["Inputs: %s" % head if head else "Inputs:"] + [e if e.startswith(">") else "> " + e for e in entries]


def crew_script_paths(cmd):
    """The `.crew/` proof scripts a proof command names (absolute paths, crew_safety.SCRIPT_RX)."""
    import crew_safety
    return [p for p in crew_safety.SCRIPT_RX.findall(str(cmd or "")) if PROOF_SCRIPT_RX.search(p)]


def proof_script_taken(cmd):
    """The open card already proving itself with one of this command's `.crew/` scripts, or ''. Two cards on one
    script would judge each other's work and break each other's hash binding (2026-10-03: two /crew in one
    folder both pointed at <folder>/.crew/verify.py), so each card's script lives in its own folder."""
    mine = set(crew_script_paths(cmd))
    db = kanban_db()
    if not mine or not db:
        return ""
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=10)
        ids = [r[0] for r in conn.execute("select id from tasks where status not in ('done', 'archived')")]
        conn.close()
    except sqlite3.Error:
        return ""
    for cid in ids:
        if mine & set(crew_script_paths(proof_snapshot(cid) or "")):
            return cid
    return ""


def contract_gaps(c, allow_no_proof=False):
    gaps = []
    taken = proof_script_taken(c.get("proof_cmd"))
    if taken:
        gaps.append("proof command (its .crew/ script is already card %s's: give this card its own folder, "
                    "<landing folder>/.crew/<YYYYMMDD-HHMMSS>-<slug>/verify.py)" % taken)
    for key, label in REQUIRED:
        if key == "proof_cmd" and allow_no_proof:
            continue
        if not str(c.get(key) or "").strip():
            gaps.append(label)
    if str(c.get("role") or "").strip().lower() not in WRITER_ROLES:
        gaps.append("role (worker or content)")
    if str(c.get("verify") or "").strip().lower() not in ("",) + VERIFY_MODES + (CLOSEOUT_MODE,):
        gaps.append("Verify (proof or independent)")
    if len(str(c.get("inputs") or "")) > INPUTS_MAX:
        gaps.append("Inputs (pasted text over %d characters: ask the owner for a file path instead)" % INPUTS_MAX)
    return gaps


def coordinator_id(session=None):
    """The coordinator that opened the card: profile plus the session it ran in.

    A card belongs to the coordinator that kicked it off, so the session has to be on the card, not
    just the role name. `session` is the session id when the caller knows it better than this process's
    environment (the plugin hook runs inside the gateway, where the session is a context variable).
    """
    sid = (session or os.environ.get("HERMES_SESSION_ID") or os.environ.get("HERMES_SESSION_KEY") or "").strip()
    return "%s/%s" % (current_profile(), sid or "no-session")


def origin_id(value):
    """The chat that opened the card, `<platform>:<chat id>` (Zulip: `zulip:stream:<s>|<topic>`),
    kept verbatim. Only an explicit --origin sets it: a card opened by a worker, the CLI or a probe
    is not a chat's card and stays silent when it ends. A value with an empty platform or chat
    (an unset `$HERMES_SESSION_PLATFORM:$HERMES_SESSION_CHAT_ID` expansion) counts as none.
    """
    value = str(value or "").strip()
    platform, _, chat = value.partition(":")
    if not platform.strip() or not chat.strip():
        return ""
    return value


def parse_route(value):
    """The contract's `Route:` line -> (route class or '', model, provider).

    `auto` asks the router for a pick; `<model>/<provider>` pins by hand (the provider is the last
    path part, model ids carry slashes themselves); `none` or empty keeps the role profile's model."""
    value = str(value or "").strip()
    if not value or value.lower() == "none":
        return "", "", ""
    if value.lower() == "auto":
        return "auto", "", ""
    if "/" in value:
        model, _, provider = value.rpartition("/")
        if model.strip() and provider.strip():
            return "", model.strip(), provider.strip()
    return "", "", ""


def parse_contract(body):
    """The contract a card body (or the intake's `kanban_create` body) states, as the dict
    `contract_gaps` and `render_body` work on. The inverse of render_body for every contract field."""
    budget = re.search(r"\d[\d_,]*", field(body, "Budget") or "")
    units = [u.strip() for u in (field(body, "Units") or "").split("|") if u.strip()]
    if not units:  # the rendered form: a "Units (...):" header, then one "  - unit" line each
        inside = False
        for line in (body or "").splitlines():
            if line.startswith("Units ("):
                inside = True
            elif inside and re.match(r"^\s+-\s+\S", line):
                units.append(line.strip()[2:].strip())
            elif inside:
                break
    route, model, provider = parse_route(field(body, "Route"))
    return {
        "role": (field(body, "Role") or "").strip().lower(),
        "budget": int(re.sub(r"\D", "", budget.group(0))) if budget else None,
        "origin": field(body, "Origin") or "",
        "goal": field(body, "GOAL") or "",
        "artifact": field(body, "Artifact") or "",
        "lands": field(body, "Lands at") or "",
        "audience": field(body, "For") or "",
        "constraints": field(body, "Constraints") or "",
        "inputs": contract_inputs(body),
        "done_when": field(body, "Done when") or "",
        "proof_cmd": proof_cmd(body),
        "proof_mode": contract_proof_mode(body),
        "proof_approved": contract_proof_approved(body),
        "verify": (field(body, "Verify") or "").strip().lower(),
        "units": "|".join(units),
        "route": route, "model": model, "provider": provider,
    }


CONTRACT_KEY_RX = re.compile(
    r"^\s*(Role|Coordinator|Verifier|Verify|Budget|Origin|Route|GOAL|Artifact|Lands at|For|Constraints|Inputs|Units|"
    r"Done when|proof command|Proof mode|Proof approved|Proof script)\s*:", re.I)


def unparsed_lines(body):
    """The non-empty lines of an intake body that are not a contract field line (a field written over
    several lines keeps its continuation here, so rebuilding the body from the parsed contract loses nothing)."""
    block = inputs_block(body)
    quoted = set(range(block[0] + 1, block[1])) if block else set()     # the Inputs field's own quoted lines
    return [ln.rstrip() for i, ln in enumerate((body or "").splitlines())
            if ln.strip() and i not in quoted and not CONTRACT_KEY_RX.match(ln)]


def default_verify(c):
    """`proof` when the card names a proof command (the writer proves it, the coordinator audits it),
    `independent` when it names none: a verifier has to judge it, there is nothing to re-run."""
    mode = str(c.get("verify") or "").strip().lower()
    if mode in VERIFY_MODES + (CLOSEOUT_MODE,):
        return coerce_verify(mode, c.get("proof_cmd"))
    if not str(c.get("proof_cmd") or "").strip():
        return "independent"
    return coerce_verify("proof", c.get("proof_cmd"))


def render_body(c):
    verifier = profile_prefix() + "verifier"
    origin = origin_id(c.get("origin"))
    mode = default_verify(c)
    lines = [
        "Role: %s" % c["role"],
        "Coordinator: %s" % (c.get("coordinator") or coordinator_id()),
        "Verifier: %s" % verifier,
        "Verify: %s" % mode,
        "Budget: %d tokens" % int(c["budget"]),
    ]
    if origin:
        lines.append("Origin: %s" % origin)
    if c.get("route"):
        lines.append("Route: %s" % c["route"])
    elif c.get("model") and c.get("provider"):
        lines.append("Route: %s/%s" % (c["model"], c["provider"]))
    lines += [
        "",
        "GOAL: %s" % c["goal"].strip(),
    ]
    for key, label in (("artifact", "Artifact"), ("lands", "Lands at"), ("audience", "For"),
                       ("constraints", "Constraints")):
        if str(c.get(key) or "").strip():
            lines.append("%s: %s" % (label, str(c[key]).strip()))
    lines += render_inputs(c.get("inputs"))
    units = [u.strip() for u in str(c.get("units") or "").split("|") if u.strip()]
    if units:
        lines += ["", "Units (one entry each in $HERMES_HOME/crew/progress/<card>.json):"]
        lines += ["  - %s" % u for u in units]
        lines += ["Mark a unit: python3 %s progress --card <card id> --unit \"<unit>\" --pass "
                  "--evidence \"<raw evidence>\" [--by verifier]" % SELF]
    lines += ["", "Done when: %s" % c["done_when"].strip()]
    if str(c.get("proof_cmd") or "").strip():
        lines += ["", "proof command: %s" % c["proof_cmd"].strip()]
        if c.get("proof_mode") in PROOF_MODES:
            lines.append("Proof mode: %s" % c["proof_mode"])
        if c.get("proof_approved"):
            lines.append("Proof approved: yes")
    else:
        lines += ["", "proof command: (none - %s)" % (
            "the close-out card runs the split card's proof" if mode == CLOSEOUT_MODE
            else "the verifier asks for one before accepting")]
    if mode == CLOSEOUT_MODE:
        lines += [
            "",
            "Contract: one writer per card; state on disk, not in context. This card has no proof command of "
            "its own: it is one part of a split, and the split card's owner-confirmed proof runs in the close-out "
            "card once every part is done. Finish: kanban_complete(summary=...) with the artifact paths. "
            "kanban_request_review is refused. Budget is a hard stop.",
        ]
    elif mode == "proof":
        lines += [
            "",
            "Contract: one writer per card; state on disk, not in context. Nothing is done on the writer's "
            "word: the proof command is snapshotted when the card opens, `verdict` runs that snapshot and stores "
            "the raw output, and the coordinator runs it once more after the card is done. kanban_complete is "
            "refused without a PASS line for the proof command. Two failed verifications hand the card back to the "
            "coordinator, who decides. Budget is a hard stop.",
            "Finish: python3 %s verdict --card <this card id> (runs the proof command, writes "
            "$HERMES_HOME/crew/verdicts/<card>.jsonl, exit 0 = PASS), then kanban_complete(summary=...) with the "
            "artifact paths and the raw proof output. No verifier session runs on this card; "
            "kanban_request_review is refused." % SELF,
        ]
    else:
        lines += [
            "",
            "Contract: one writer per card; state on disk, not in context. Nothing is done on the writer's "
            "word: %s runs the proof command itself and stores the raw output with its verdict. "
            "Two failed verifications hand the card back to the coordinator, who decides. kanban_complete is "
            "refused without a PASS line for the proof command run by the verifier. Budget is a hard stop." % verifier,
            "Finish: run the proof command yourself, then kanban_request_review(summary=..., "
            "reviewer=\"%s\"). Never kanban_complete this card yourself." % verifier,
            "Verifier, finish with: python3 %s verdict --card <this card id> (runs the proof, writes "
            "$HERMES_HOME/crew/verdicts/<card>.jsonl, exit 0 = PASS). A verdict with no verdict file "
            "does not count." % SELF,
        ]
    return "\n".join(lines) + "\n"


def _kanban(args, timeout=120):
    return subprocess.run([hermes_bin(), "kanban"] + args, capture_output=True, text=True, timeout=timeout)


def _created_id(result):
    out = (result.stdout or "").strip()
    try:
        return json.loads(out).get("id")
    except Exception:
        m = re.search(r"Created\s+(t_[0-9a-f]+)", out)
        return m.group(1) if m else None


def create_card(title, body, assignee, skills=(), parents=(), max_runtime=DEFAULT_RUNTIME,
                initial_status=None, dry_run=False, model=None, provider=None):
    cmd = ["create", title[:120], "--assignee", assignee, "--max-runtime", max_runtime, "--json"]
    if model:
        cmd += ["--model", model]
        if provider:
            cmd += ["--provider", provider]
    for s in skills:
        cmd += ["--skill", s]
    for p in parents:
        cmd += ["--parent", p]
    if initial_status:
        cmd += ["--initial-status", initial_status]
    if dry_run:
        return {"dry_run": True, "argv": ["hermes", "kanban"] + cmd, "body": body}
    fd, path = tempfile.mkstemp(prefix="crew-card-", suffix=".md")
    with os.fdopen(fd, "w") as fh:
        fh.write(body)
    try:
        r = _kanban(cmd + ["--body-file", path])
    finally:
        os.unlink(path)
    cid = _created_id(r)
    if not cid:
        raise RuntimeError("kanban create failed: %s" % ((r.stderr or r.stdout or "").strip()[-300:]))
    return {"id": cid, "assignee": assignee, "title": title[:120]}


def profile_home_of(name):
    return base_home() if name == "default" else os.path.join(base_home(), "profiles", name)


def skill_in_home(home, name):
    root = os.path.join(home, "skills")
    for dirpath, dirnames, filenames in os.walk(root):
        if os.path.basename(dirpath) == name and "SKILL.md" in filenames:
            return True
        if dirpath.count(os.sep) - root.count(os.sep) >= 4:
            dirnames[:] = []
    return False


def skill_available(name):
    roots = [os.path.join(hermes_home(), "skills")]
    ext = _config_list("skills", "external_dirs")
    roots += [os.path.expanduser(p) for p in ext]
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            if os.path.basename(dirpath) == name and "SKILL.md" in filenames:
                return True
            if dirpath.count(os.sep) - root.count(os.sep) >= 4:
                dirnames[:] = []
    return False


def _config_list(section, key):
    path = os.path.join(hermes_home(), "config.yaml")
    out, state = [], 0
    try:
        with open(path) as fh:
            for line in fh.read().splitlines():
                if state == 0 and re.match(r"^%s:\s*$" % section, line):
                    state = 1
                elif state == 1:
                    if line and not line.startswith(" "):
                        break
                    if re.match(r"^\s+%s:\s*$" % key, line):
                        state = 2
                elif state == 2:
                    m = re.match(r"^\s*-\s*(.+?)\s*$", line)
                    if m:
                        out.append(m.group(1).strip("'\""))
                    else:
                        break
    except OSError:
        pass
    return out


def router_path():
    """The one model router on this box (worker_route.py), wherever this profile can see it."""
    env = (os.environ.get("CREW_ROUTER") or "").strip()
    if env:  # an explicit setting wins, including when it points nowhere
        return env if os.path.isfile(env) else None
    for c in (os.path.join(hermes_home(), "scripts", "worker_route.py"),
              os.path.join(owner_home(), "scripts", "worker_route.py")):
        if os.path.isfile(c):
            return c
    return None


def router_plugin_path():
    """The free_first_router plugin dir, wherever this profile can see it."""
    env = (os.environ.get("CREW_ROUTER_PLUGIN") or "").strip()
    if env:  # an explicit setting wins, including when it points nowhere
        return env if os.path.isfile(os.path.join(env, "__init__.py")) else None
    for c in (os.path.join(hermes_home(), "plugins", "free_first_router"),
              os.path.join(owner_home(), "plugins", "free_first_router")):
        if os.path.isfile(os.path.join(c, "__init__.py")):
            return c
    return None


ROLE_TASK_CLASS = {"worker": "code", "content": "write", "verifier": "review"}


def role_task_class(role):
    """The task class the router is told for a card: what its role does, not how short its title is.
    A wall used to ask for "short" on every card, which is how a 205-call card got a short-answer model."""
    return ROLE_TASK_CLASS.get((role or "").strip().lower(), "code")


def route_answer(task_class="code", label="", profile=None):
    """The router's raw answer for one card (crew_route_pick.py's JSON), or None when there is no router
    or it could not answer. `label` "parent" is an answer: nothing clears the agent floor."""
    rp = router_plugin_path()
    if not rp:
        return None
    text = "%s (task class: %s)" % ((label or "").strip(), task_class or "code")
    cmd = [sys.executable, os.path.join(HERE_SCRIPTS, "crew_route_pick.py"), "--text", text[:1200]]
    if profile:
        cmd += ["--profile", profile]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.SubprocessError:
        return None
    out = (r.stdout or "").strip().splitlines()
    if not out:
        return None
    try:
        d = json.loads(out[-1])
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def route_pick(task_class="code", label="", no_log=False, profile=None):
    """One delegate-fit pick for one card: {provider, model, why, floor, menu_size}. None when there is no pick.

    A crew card runs an autonomous agent, so the pick comes from the router's own delegate menu
    (gateway / gemini / openrouter - the free hosts that can hold an agent's context) cut to the agent
    floor, through the free_first_router plugin's decider. ``provider`` is the Hermes provider id the
    worker profile can actually resolve ("ai-gateway"), never the router's internal host name ("groq" is
    not a provider any profile knows - pinning it kills the worker before it boots).
    """
    return pick_from_answer(route_answer(task_class, label, profile), task_class, label)


def pick_from_answer(d, task_class="code", label=""):
    """A usable pick out of the router's raw answer, or None ("parent", no model, no answer)."""
    if not d:
        return None
    label_out = d.get("label")
    if label_out in (None, "", "parent") or not d.get("provider") or not d.get("model"):
        return None
    return {"provider": d["provider"], "model": d["model"], "router_label": label_out,
            "paid": bool(d.get("paid")),
            "router_provider": d.get("router_provider"), "decider": d.get("decider"),
            "task_class": d.get("task_class") or task_class, "why": (d.get("why") or "")[:400],
            "floor": d.get("floor"), "menu_size": d.get("menu_size"),
            "label": (label or "")[:120]}


def wall_count(card_id, minutes=60):
    """Quota walls recorded on this card in the last N minutes (a completed run clears the count)."""
    db = kanban_db()
    if not db:
        return 0
    conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    try:
        row = conn.execute("select max(created_at) from task_events where task_id = ? "
                           "and kind = 'completed'", (card_id,)).fetchone()
        # a completed run clears the count: only walls strictly after it (and outside the window) count
        since = max(int(time.time()) - minutes * 60, int((row or [0])[0] or 0) + 1)
        n = conn.execute("select count(*) from task_events where task_id = ? and kind = 'quota_wall' "
                         "and created_at >= ?", (card_id, since)).fetchone()
        return int((n or [0])[0] or 0)
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def reroute_after_wall(card_id, model=None, provider=None, reason="quota wall",
                       max_walls=2, force_pick=None):
    """A quota wall on this card's model: count it, then move the card to a model that can carry it.

    The pick is asked with the agent floor (crew_route_pick.py), so a wall never lands a card on a model
    that cannot run an agent. Three outcomes:
      - a floor model is live: the card is re-pinned on it ("rerouted");
      - the router answers "parent" (nothing clears the floor) and the card carries a pin: the pin is cleared
        (`hermes kanban set-model <id>`, which clears model and provider together) so the role profile's own
        model runs, and the hold on the dead model is lifted ("unpinned");
      - no pin to clear (the wall is on the profile's own model) or no router: the kernel's
        rate_limit_cooldown holds the card ("counted"); the second wall blocks it as `transient`, the kind
        the coordinator loop handles, instead of asking the owner.
    The next run starts with the previous work handed over."""
    db = kanban_db()
    if not db or not card_id:
        return {"action": "skipped", "why": "no kanban db or no card"}
    conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    try:
        row = conn.execute("select model_override, provider_override, assignee, title, body "
                           "from tasks where id = ?", (card_id,)).fetchone()
    except sqlite3.Error:
        row = None
    finally:
        conn.close()
    if not row:
        return {"action": "skipped", "why": "unknown card %s" % card_id}
    cur_model, cur_prov, assignee, title, body = row
    spent_model = model or cur_model or ""
    spent_prov = provider or cur_prov or ""
    stalls = wall_count(card_id) + 1
    _append_card_event(card_id, "quota_wall",
                       {"model": spent_model, "provider": spent_prov, "reason": reason[:200],
                        "wall_number": stalls, "run": kanban_run_id()})
    answer = None
    if force_pick:
        pick = force_pick
    else:
        answer = route_answer(role_task_class(field(body, "Role")), title or (body or "")[:200],
                              profile=assignee)
        pick = pick_from_answer(answer, role_task_class(field(body, "Role")), title)
    floor_holds_none = bool(answer) and answer.get("label") == "parent"
    same = (not pick) or (pick.get("model") == cur_model and pick.get("provider") == cur_prov) \
        or (spent_model and pick.get("model") == spent_model)
    if pick and not same:
        apply_route(card_id, pick)
        # the hold on this card was for the dead model: with a fresh pin it must not stand
        release_hold(card_id)
        _append_card_event(card_id, "reroute",
                           {"from_model": cur_model, "from_provider": cur_prov,
                            "to_model": pick["model"], "to_provider": pick["provider"],
                            "floor": pick.get("floor"), "menu_size": pick.get("menu_size"),
                            "why": "quota wall on %s/%s; %s" % (spent_prov, spent_model,
                                                                pick.get("why") or "")[:300]})
        return {"action": "rerouted", "to": pick, "wall_number": stalls}
    if floor_holds_none and cur_model:
        why = ("quota wall on %s/%s and no live model clears the agent floor (%s): the pin is cleared, the "
               "role profile's own model runs" % (spent_prov or "?", spent_model or "?",
                                                  (answer.get("why") or "")[:160]))
        r = _kanban(["set-model", card_id])
        if r.returncode == 0:
            release_hold(card_id)
            _append_card_event(card_id, "reroute",
                               {"from_model": cur_model, "from_provider": cur_prov, "to_model": None,
                                "to_provider": None, "floor": answer.get("floor"),
                                "menu_size": answer.get("menu_size"), "why": why[:300]})
            return {"action": "unpinned", "why": why, "wall_number": stalls, "rc": 0}
        return {"action": "error", "why": "set-model failed: %s" % (r.stderr or r.stdout or "").strip()[-200:],
                "rc": r.returncode, "wall_number": stalls}
    if stalls >= max_walls:
        why = ("the worker model %s/%s hit its quota wall %d time(s) and the router has no other "
               "model for this card - it is stopped here instead of spinning"
               % (spent_prov or "?", spent_model or "?", stalls))
        r = _kanban(["block", card_id, "--kind", "transient", why[:400]])
        return {"action": "blocked", "why": why, "rc": r.returncode, "wall_number": stalls}
    return {"action": "counted", "wall_number": stalls,
            "why": "no alternative pick yet; the card keeps its model"}


def _append_card_event(card_id, kind, payload, run_id=None, db=None):
    """The crew's one audit-event writer (origin, brief, route, reroute, quota_wall, hold_released, crew_decision,
    self_heal, handoff). Hermes has no public call that appends an event of a kind of its own, so this is the
    single place the crew inserts into task_events: append-only rows of crew-namespaced kinds that no kernel
    invariant reads (status, claims, counters and links are never touched here; every state change goes through
    `hermes kanban` or hermes_cli.kanban_db)."""
    db = db or kanban_db()
    if not db:
        return False
    conn = sqlite3.connect(db, timeout=10)
    try:
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)",
                     (card_id, run_id, kind, json.dumps(payload), int(time.time())))
        conn.commit()
    finally:
        conn.close()
    return True


def hermes_root():
    """Hermes's source tree: HERMES_AGENT_DIR, HERMES_SRC (the proofs' name for it), this home's, then the default."""
    for path in (os.environ.get("HERMES_AGENT_DIR"), os.environ.get("HERMES_SRC"),
                 os.path.join(base_home(), "hermes-agent"), os.path.expanduser("~/.hermes/hermes-agent")):
        if path and os.path.isdir(path):
            return path
    return os.path.expanduser("~/.hermes/hermes-agent")


def hermes_python(root=None):
    """Path of a python that can import hermes_cli, or "". Order: the package manager's committed venv (the
    layout where the gateway runs under a bare interpreter and Hermes's dependencies live in a venv it
    commits), then the legacy in-tree venv/ or .venv/, then nothing."""
    root = root or hermes_root()
    added = root not in sys.path
    if added:
        sys.path.insert(0, root)
    try:
        from pm.environments import committed_venv
        venv = committed_venv(Path(root))
        if venv:
            py = os.path.join(str(venv), "bin", "python")
            if os.path.exists(py):
                return py
    except Exception:       # an older Hermes has no pm module; fall through to the legacy venvs
        pass
    finally:
        if added and root in sys.path:
            sys.path.remove(root)
    for d in ("venv", ".venv"):
        py = os.path.join(root, d, "bin", "python")
        if os.path.exists(py):
            return py
    return ""


def hermes_kb():
    """(hermes_cli.kanban_db, hermes_cli.kanban_db_connect) or a RuntimeError naming the missing interpreter.
    The few kernel calls with no `hermes kanban` command (leaving triage with a body, clearing a stale failure)
    need Hermes's own python; `main` re-executes under it when a script was started with another one."""
    root = hermes_root()
    if root not in sys.path and os.path.isdir(root):
        sys.path.append(root)       # the editable install maps hermes_cli but not the root modules it imports
    try:
        from hermes_cli import kanban_db as kb, kanban_db_connect as kbc
    except ImportError as exc:
        raise RuntimeError("hermes_cli is not importable from this python (%s); run under the Hermes python" % exc)
    return kb, kbc


def kb_conn(db=None):
    """A kernel connection to the crew's board (the file kanban_db() names unless `db` says), for
    hermes_cli.kanban_db calls."""
    from pathlib import Path
    kb, kbc = hermes_kb()
    db = db or kanban_db()
    if not db:
        raise RuntimeError("no kanban db")
    return kb, kbc.connect(Path(db))


def apply_route(card_id, pick, pin=True):
    """Pin the card's worker to the model the router chose, and record why on the card.

    `pin=False` only records the `route` event: the intake's kanban_create already created the card
    with the model and provider, so the dispatcher can not spawn it on the profile's model first."""
    if not pick or not card_id:
        return False
    if pin:
        # the kernel's own call: it validates the pair, refuses an archived card and records model_override_set
        r = _kanban(["set-model", card_id, pick["model"]] + (["--provider", pick["provider"]] if pick.get("provider") else []))
        if r.returncode != 0:
            return False
    return _append_card_event(card_id, "route", {
        "provider": pick["provider"], "model": pick["model"], "task_class": pick.get("task_class"),
        "floor": pick.get("floor"), "menu_size": pick.get("menu_size"), "why": pick.get("why"),
        "by": current_profile(), "ts": time.time()})


def repin_for_review(card_id):
    """Before a `Verify: independent` card goes to its verifier: the writer's model pin is not the verifier's.

    The dispatcher starts a review run with the card's `model_override`, so the writer's pick (made for code or
    writing) would otherwise carry over. The router is asked for a `review` pick over the same agent floor the
    writers get and the card is pinned to it; when nothing clears the floor the pin is cleared with the kernel's
    own `set-model` and the verifier profile's model runs. Returns {"action": "pinned"|"cleared"|"unchanged",...}."""
    row = card_row(card_id)
    if not row:
        return {"action": "unchanged", "why": "unknown card"}
    body = row[4]
    if verify_mode(body) != "independent":
        return {"action": "unchanged", "why": "not an independent-verification card"}
    cur_model, cur_prov = card_pin(card_id)
    verifier = role_profile("verifier")
    answer = route_answer(role_task_class("verifier"), row[1] or (body or "")[:200], profile=verifier)
    pick = pick_from_answer(answer, role_task_class("verifier"), row[1])
    if pick:
        if (pick["model"], pick["provider"]) != (cur_model, cur_prov):
            apply_route(card_id, pick)
        return {"action": "pinned", "to": pick}
    if cur_model:
        r = _kanban(["set-model", card_id])
        if r.returncode == 0:
            _append_card_event(card_id, "route", {"provider": None, "model": None, "task_class": "review",
                                                  "floor": (answer or {}).get("floor"),
                                                  "menu_size": (answer or {}).get("menu_size"),
                                                  "why": "the writer's pin is not the verifier's: cleared, the "
                                                         "verifier profile's own model runs",
                                                  "by": current_profile(), "ts": time.time()})
            return {"action": "cleared"}
        return {"action": "error", "why": (r.stderr or r.stdout or "").strip()[-200:]}
    return {"action": "unchanged", "why": "no pin to clear and no router pick"}


def session_env(get=None):
    """Where this card is being opened from: the chat (if any) and the session id, always.

    `get(name)` replaces the process environment as the source (the plugin hook passes the gateway's
    per-request session variables, which are not in os.environ)."""
    get = get or (lambda name: os.environ.get(name))
    plat = (get("HERMES_SESSION_PLATFORM") or "").strip()
    chat = (get("HERMES_SESSION_CHAT_ID") or "").strip()
    sess = (get("HERMES_SESSION_ID") or get("HERMES_SESSION") or "").strip()
    kind = (get("HERMES_SESSION_CHAT_TYPE") or "").strip()
    origin = ""
    if plat and chat:
        origin = "%s:%s" % (plat, chat)
    return {"origin": origin, "platform": plat, "chat": chat, "chat_type": kind, "session": sess,
            "by": current_profile()}


def record_origin(card_id, env=None, note="", proof_cmd=None, proof_mode=None, proof_approved=False):
    """Always write down where this card came from - chat or not - so the loop can be closed.

    The opening session is recorded even when it is a CLI session with no chat: a card whose origin
    has no chat still has a session that must be told, and a card the decomposer later creates under
    it inherits this record (see origin_of).
    """
    env = env or session_env()
    db = kanban_db()
    if not db or not card_id:
        return False
    payload = dict(env)
    payload.update({"ts": time.time(), "note": note[:200]})
    if proof_cmd is not None:  # the proof command as the card opened: the only one a PASS line can be for
        payload["proof_cmd"] = str(proof_cmd).strip()
    if proof_mode in PROOF_MODES:  # the owner's per-card safety choice (crew_safety)
        payload["proof_mode"] = proof_mode
    if proof_approved and str(proof_cmd or "").strip():  # the owner's yes to THIS flagged command, by hash
        payload["approved_flagged"] = crew_safety.cmd_hash(proof_cmd)
    return _append_card_event(card_id, "origin", payload)


def own_origin(db, card_id):
    """This card's own origin record: the 'origin' event first, then its body's Origin: line."""
    row = qone_db(db, "select payload from task_events where task_id = ? and kind = 'origin' "
                      "order by created_at limit 1", (card_id,))
    if row:
        try:
            data = json.loads(row[0] or "{}")
        except ValueError:
            data = {}
        if data.get("origin") or data.get("session"):
            return data
    body = qone_db(db, "select body from tasks where id = ?", (card_id,))
    body = (body or [None])[0] or ""
    m = re.search(r"^\s*Origin:\s*(.+?)\s*$", body, re.M)
    if m:
        return {"origin": m.group(1), "session": "", "inherited_from": ""}
    return {}


def ancestors(db, card_id, max_hops=6):
    """The cards this one came from: task_links parents first, then the decomposer's own record."""
    seen, frontier, out = {card_id}, [card_id], []
    for _ in range(max_hops):
        nxt = []
        for cid in frontier:
            for r in q_db(db, "select parent_id from task_links where child_id = ?", (cid,)):
                if r[0] and r[0] not in seen:
                    seen.add(r[0])
                    out.append(r[0])
                    nxt.append(r[0])
            for r in q_db(db, "select payload from task_events where task_id = ? and kind = 'created'",
                          (cid,)):
                try:
                    data = json.loads(r[0] or "{}")
                except ValueError:
                    continue
                src = data.get("from_decompose_of")
                if src and src not in seen:
                    seen.add(src)
                    out.append(src)
                    nxt.append(src)
        if not nxt:
            break
        frontier = nxt
    return out


def origin_of(card_id, max_hops=6):
    """(origin dict, card it came from, hops) for a card, inheriting up the chain when it has none."""
    db = kanban_db()
    if not db or not card_id:
        return {}, "", 0
    mine = own_origin(db, card_id)
    if mine:
        return mine, card_id, 0
    for hops, cid in enumerate(ancestors(db, card_id, max_hops), start=1):
        found = own_origin(db, cid)
        if found:
            found = dict(found)
            found["inherited"] = True
            return found, cid, hops
    return {}, "", 0


def qone_db(db, sql, args=()):
    rows = q_db(db, sql, args)
    return rows[0] if rows else None


def q_db(db, sql, args=()):
    conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    try:
        return conn.execute(sql, args).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def release_hold(card_id, clear_error=True):
    """Lift the dispatcher's hold on a card the crew has moved to a fresh model.

    The respawn guard skips a card whose last_failure_error carries a quota/auth error, which is
    right while the card is still pinned to the dead model - and wrong the moment the crew re-pins
    it. The kernel's own reset (`_clear_failure_counter`, what complete_task and a reassign to a new profile
    call) clears that stale error and the failure streak with it: a new model is a fresh streak. There is no
    public command for a ready card (`unblock` only takes blocked ones), so this is the one private kernel
    function the crew calls.
    """
    if not kanban_db() or not card_id:
        return False
    if clear_error:
        kb, conn = kb_conn()
        try:
            kb._clear_failure_counter(conn, card_id)
        finally:
            conn.close()
    _append_card_event(card_id, "hold_released", {"cleared_failure_error": bool(clear_error),
                                                  "by": current_profile(), "ts": time.time()})
    return True


def record_brief(card_id, text, source="owner", origin=None):
    """Store the owner's own words on the card, so the card view can show the brief above the
    coordinator: the page then reads from the /crew invocation to the close-out."""
    db = kanban_db()
    if not db or not text:
        return False
    return _append_card_event(card_id, "brief", {"text": text, "source": source, "by": current_profile(),
                                                 "origin": origin or "", "ts": time.time()})


def prepare_contract(c, allow_no_proof=False):
    """A contract ready to become a card: role normalised, gaps refused (ValueError), budget defaulted
    and raised to the floor. The one place the intake tool guard and `open_card` agree on what a card is."""
    c = dict(c)
    c["role"] = (c.get("role") or "").strip().lower()
    gaps = contract_gaps(c, allow_no_proof)
    if gaps:
        raise ValueError("contract incomplete, missing: " + ", ".join(gaps))
    if not c.get("budget"):
        c["budget"] = default_budget(c["role"])
    # A worker's first API call already carries the role prompt and the tool list (install.py --check
    # prints the measured size per role against roles.json prompt_budget_tokens). A budget under the
    # floor guarantees the card stops on "budget exhausted" before it does any work, so raise it and
    # say so.
    floor = budget_floor()
    if int(c["budget"]) < floor:
        c["budget"] = floor
        c["budget_note"] = ("budget raised to the floor %d tokens: every worker call carries the role "
                            "prompt and tool list, a smaller budget fails before the work starts" % floor)
    return c


def card_skills(assignee, role):
    """The role skill to force-load, or [] when it resolves nowhere (a forced skill that resolves
    nowhere makes the worker refuse to start): installed in the assignee's home or reachable from this one."""
    skill = "crew-role-%s" % role
    return [skill] if skill_in_home(profile_home_of(assignee), skill) or skill_available(skill) else []


def finish_card(card_id, c, assignee, env=None, pick=None, pinned=False):
    """Everything a new card gets after it exists: units file, route record, origin, brief.

    Shared by `open_card` (`crew_card.py open`, which creates the card through `hermes kanban create`)
    and the plugin's post_tool_call hook (the intake's `kanban_create`). `pinned` says the card was
    created with its model and provider already (the hook's case), so only the `route` event is written;
    `pick` is the router pick behind that pin, when there was one."""
    res = {}
    units = [u.strip() for u in str(c.get("units") or "").split("|") if u.strip()]
    if units:
        res["units"] = units
        res["progress_file"] = start_progress(card_id, units)
    if c.get("route") and pick is None and not pinned:
        pick = route_pick(role_task_class(c.get("role")), c.get("title") or c.get("goal") or "", profile=assignee)
    if pick:
        apply_route(card_id, pick, pin=not pinned)
        res["route"] = pick
    # The intake's `Proof mode:` / `Proof approved:` lines are model-written, so they are honoured only when the
    # command would not be flagged in safe mode. A flagged command records no consent here: it runs only through
    # the owner's /crew-proof answer. This is what stops a prompt-injected intake from writing brave or an approval.
    proof_mode = c.get("proof_mode")
    proof_approved = bool(c.get("proof_approved"))
    if (proof_mode == "brave" or proof_approved) and c.get("proof_cmd"):
        if not crew_safety.check_proof(c.get("proof_cmd"), "safe")[0]:
            proof_mode, proof_approved = None, False
    record_origin(card_id, env=env, note=c.get("title") or c.get("goal") or "",
                  proof_cmd=c.get("proof_cmd") or "", proof_mode=proof_mode,
                  proof_approved=proof_approved)
    if c.get("brief"):
        res["brief_recorded"] = record_brief(card_id, c["brief"], source=c.get("brief_source") or "owner",
                                             origin=c.get("origin"))
    return res


def open_card(c, dry_run=False, allow_no_proof=False, parents=(), initial_status=None):
    c = prepare_contract(c, allow_no_proof)
    assignee = c.get("assignee") or role_profile(c["role"])
    skills = card_skills(assignee, c["role"])
    title = c.get("title") or c["goal"]
    res = create_card(title, render_body(c), assignee, skills, parents or c.get("parents") or (),
                      model=c.get("model"), provider=c.get("provider"), initial_status=initial_status,
                      max_runtime=c.get("max_runtime") or DEFAULT_RUNTIME, dry_run=dry_run)
    card_id = res.get("id")
    if card_id and not dry_run:
        done = finish_card(card_id, c, assignee)
        if done.get("units"):
            print("units file: %s (%d unit(s))" % (done["progress_file"], len(done["units"])))
        res.update(done)
    res.update({"role": c["role"], "budget": c["budget"], "proof_cmd": c.get("proof_cmd")})
    if c.get("budget_note"):
        res["budget_note"] = c["budget_note"]
    return res


def run_plan(spec, dry_run=False, closeout_proof=None):
    """Parent contract card, independent children, coordinator close-out.

    `closeout_proof` (crew code only, never read from the spec) is the owner-confirmed proof of a split card.
    Given, the children carry no proof command of their own (`Verify: closeout`) and the close-out card runs
    the children check and then this proof, so the tree is closed by a command the owner confirmed."""
    children = [dict(ch) for ch in (spec.get("children") or [])]
    if not children:
        raise ValueError("plan has no children")
    for ch in children:
        if closeout_proof:
            ch["verify"], ch["proof_cmd"] = CLOSEOUT_MODE, ""
        elif str(ch.get("verify") or "").strip().lower() == CLOSEOUT_MODE:
            raise ValueError("a child cannot skip its proof outside a split")
    arts = [str(ch.get("artifact") or "").strip().lower() for ch in children]
    dup = sorted(set(a for a in arts if a and arts.count(a) > 1))
    if dup:
        raise ValueError("two writers on one artifact refused: %s" % ", ".join(dup))
    children = [{k: v for k, v in ch.items() if k not in ("proof_mode", "proof_approved")} for ch in children]  # only the owner picks it
    for i, ch in enumerate(children, 1):
        gaps = contract_gaps(ch, allow_no_proof=bool(closeout_proof))
        if gaps:
            raise ValueError("child %d contract incomplete, missing: %s" % (i, ", ".join(gaps)))
    coord = role_profile("coordinator")
    goal = spec.get("goal") or spec.get("title") or "crew plan"
    pbody = ("Role: coordinator\nCoordinator: %s\n\nGOAL: %s\n\nDone when: %s\n\n"
             "Parent contract card. Children run in parallel, one writer each, each verified by %s.\n"
             % (current_profile(), goal, spec.get("done_when") or "every child card is done with a PASS verdict",
                profile_prefix() + "verifier"))
    parent = create_card(spec.get("title") or goal, pbody, coord, initial_status="blocked", dry_run=dry_run)
    made = []
    for ch in children:
        made.append(open_card(ch, dry_run=dry_run, parents=[parent.get("id") or "PARENT"],
                              allow_no_proof=bool(closeout_proof)))
    close_parents = [m.get("id") or "CHILD" for m in made]
    check = "python3 %s closeout --cards %s" % (SELF, ",".join(close_parents))
    cproof = "%s && (%s)" % (check, closeout_proof) if closeout_proof else check
    # a split card's proof that runs a `.crew/` script is the verifier's like any such proof (coerce_verify): the
    # close-out card is `Verify: independent`, its run hands it to the verifier, who writes and runs the script
    independent = coerce_verify("proof", closeout_proof) == "independent"
    finish = ("Do not run the proof yourself: its script is written by the verifier, not by you. kanban_request_review("
              "summary=\"every child card is done\", reviewer=\"%s\"). Never kanban_complete this card yourself."
              % role_profile("verifier") if independent else
              "Run `python3 %s verdict --card $HERMES_KANBAN_TASK` (it runs the proof command and records the "
              "verdict). Exit 0: kanban_complete with its output. Otherwise kanban_block with kind 'transient' "
              "and the output." % SELF)
    cbody = ("Role: coordinator\nCoordinator: %s\n\nGOAL: close out %s\n\n%s"
             "Done when: every child card is done and %s.\n\n"
             "proof command: %s\n\n%s\n"
             % (current_profile(), parent.get("id") or "PARENT", "Verify: independent\n\n" if independent else "",
                "the split card's own proof exits 0" if closeout_proof else "its latest verdict line is PASS",
                cproof, finish))
    closeout = create_card("close-out: " + (spec.get("title") or goal), cbody, coord,
                           parents=close_parents, dry_run=dry_run)
    if closeout.get("id") and not dry_run:
        # code-authored (crew's closeout check, plus for a split the split card's owner-confirmed proof), so it is
        # its own snapshot; no origin or session in it, so the card still inherits its chat
        _append_card_event(closeout["id"], "proof_confirm", {"proof_cmd": cproof, "by": "crew",
                                                             "note": "close-out", "ts": time.time()})
    released = None
    if not dry_run:
        r = _kanban(["complete", parent["id"], "--summary",
                     "contract accepted; %d child card(s) released" % len(made)])
        released = r.returncode == 0
        if not released:
            raise RuntimeError("could not release parent %s: %s" % (parent["id"], (r.stderr or r.stdout)[-300:]))
    return {"parent": parent, "children": made, "closeout": closeout, "parent_released": released}


# ------------------------------------------------------------------ verdicts


def verdict_path(card_id):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(card_id))
    return os.path.join(hermes_home(), "crew", "verdicts", safe + ".jsonl")


def all_verdicts(card_id):
    """Every verdict line of a card, oldest first, from the base home and each profile home: the ONE reader.

    The verdict log is the only verdict record; the graph, the guard, the coordinator and the close rule
    all read it through here. A line copied into two homes (a symlinked dir) counts once; `ts` is a float
    and `rc` an int; `_home` and `_file` say where the line was found."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(card_id))
    homes = [base_home()]
    pd = os.path.join(base_home(), "profiles")
    if os.path.isdir(pd):
        homes += [os.path.join(pd, n) for n in sorted(os.listdir(pd))]
    out, seen = [], set()
    for h in homes:
        p = os.path.join(h, "crew", "verdicts", safe + ".jsonl")
        try:
            real = os.path.realpath(p)
            with open(p) as fh:
                for line in fh:
                    try:
                        v = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(v, dict):
                        continue
                    try:
                        v["ts"] = float(v.get("ts"))
                    except (TypeError, ValueError):
                        v["ts"] = 0.0
                    try:
                        v["rc"] = int(v.get("rc"))
                    except (TypeError, ValueError):
                        pass
                    key = (v["ts"], v.get("command"), v.get("rc"), v.get("verdict"))
                    if key in seen:
                        continue
                    seen.add(key)
                    v["_home"], v["_file"] = h, real
                    out.append(v)
        except OSError:
            continue
    out.sort(key=lambda v: v.get("ts") or 0)
    return out


def verdict_by(v):
    """The profile that ran a verdict line: `by`, or `profile` on a line written before `by` existed."""
    return str(v.get("by") or v.get("profile") or "")


def kanban_run_id():
    """The dispatcher's run id for this process (the kernel pins HERMES_KANBAN_RUN_ID), or None."""
    raw = (os.environ.get("HERMES_KANBAN_RUN_ID") or "").strip()
    return int(raw) if raw.isdigit() else None


def record_verdict(card_id, command, rc, output, duration, by=None, for_event=None):
    os.makedirs(os.path.dirname(verdict_path(card_id)), exist_ok=True)
    line = {
        "ts": time.time(),
        "card": card_id,
        "by": by or current_profile(),
        "run_id": kanban_run_id(),
        "command": command,
        "rc": rc,
        "verdict": "PASS" if rc == 0 else "FAIL",
        "output_head": (output or "")[:OUTPUT_KEEP],
        "duration_s": round(float(duration), 3),
    }
    if for_event is not None:  # the coordinator's audit of one `completed` event: one line per event id
        line["for_event"] = int(for_event)
    with open(verdict_path(card_id), "a") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    return line


# ------------------------------------------------------------------ the close rule
# One rule for closing a crew card, used by the plugin's kanban_complete guard (every profile) and by the
# coordinator loop's audit of a completion that got around it: the card's latest run of its proof command
# is a PASS, recorded after the newest claim, by a crew profile, with no FAIL line after it.


def needs_pass(body):
    """Does closing this card need a PASS line? Every crew card does except the plan's parent contract card:
    a coordinator card with no proof command is released by the plan itself, it is not work to verify."""
    if not is_crew_body(body):
        return False
    if verify_mode(body) == CLOSEOUT_MODE and not proof_cmd(body):
        return False        # a split child: the close-out card's proof is what closes the tree
    role = (field(body, "Role") or "").strip().lower()
    return not (role == "coordinator" and not proof_cmd(body))


SNAPSHOT_KINDS = ("origin", "proof_confirm", "proof_script_hash")
OWNER_BY = "owner"    # a proof_confirm written by the owner's /crew-proof answer: the only consent the snapshot trusts


def snapshot_events(card_id, db=None):
    """The card's snapshot events, oldest first, as (kind, payload) pairs: the `origin` written when it opened and any
    `proof_confirm` added since (the owner's /crew-proof answer, or the plan's own close-out card). A separate kind,
    not a second `origin`: origin events are the chat/session record (origin_of, crew_notify) and stay as written.
    `proof_script_hash` rides here too (the scripts a proof ran, see proof_script_hashes). `db` reads another board."""
    db = db or kanban_db()
    if not db:
        return []
    marks = ",".join("?" * len(SNAPSHOT_KINDS))
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        try:
            rows = conn.execute("select kind, payload from task_events where task_id = ? and kind in (%s) order by id"
                                % marks, (card_id,) + SNAPSHOT_KINDS).fetchall()
        finally:
            conn.close()
    except Exception:
        return []
    out = []
    for kind, payload in rows:
        try:
            data = json.loads(payload or "{}")
        except ValueError:
            continue
        if isinstance(data, dict):
            out.append((kind, data))
    return out


def _snapshot_trusts(kind, data):
    """May a snapshot event's `proof_cmd` be the card's snapshot? `origin` (the intake at open), the owner's
    /crew-proof answer, or crew code carrying an already-owner-confirmed command (the plan's close-out card)."""
    return kind == "origin" or (kind == "proof_confirm" and
                                (data.get("by") == OWNER_BY
                                 or (data.get("by") == "crew" and data.get("note") == "close-out")))


def _consent_trusts(kind, data):
    """May a snapshot event carry the owner's consent (`proof_mode` / `approved_flagged`)? Only `origin` (the
    intake, itself gated so a flagged command records no consent) or the owner's /crew-proof answer. A
    proof_confirm written by anything else - a raw sqlite insert, the plan's close-out carry - is never consent."""
    return kind == "origin" or (kind == "proof_confirm" and data.get("by") == OWNER_BY)


def proof_snapshot(card_id, db=None):
    """The proof command this card was opened with (or the owner confirmed since), or None for a card that has
    no snapshot (opened before snapshots existed).

    This is the ONLY command a proof ever runs. The `proof command:` line on the card is model-authored text that
    anyone can edit, and a coordinator `rescope` is a model's proposal: neither can change what runs. A new
    command becomes the snapshot only through the owner's answer (a `proof_confirm` event)."""
    snap = None
    for kind, data in snapshot_events(card_id, db):
        if "proof_cmd" in data and _snapshot_trusts(kind, data):
            snap = str(data["proof_cmd"] or "").strip()
    return snap


def proof_snapshot_mode(card_id):
    """The per-card safety mode the owner chose ("safe", "brave"), newest first, or ''."""
    for kind, data in reversed(snapshot_events(card_id)):
        if data.get("proof_mode") in PROOF_MODES and _consent_trusts(kind, data):
            return data["proof_mode"]
    return ""


def proof_snapshot_approved(card_id):
    """Hashes of the flagged commands the owner approved for this card (see crew_safety.cmd_hash)."""
    return {d["approved_flagged"] for kind, d in snapshot_events(card_id)
            if d.get("approved_flagged") and _consent_trusts(kind, d)}


def close_proof_command(card_id, db=None):
    """The proof command a PASS line has to have run: the card's snapshot, '' when it has none. No body-line
    fallback: a card without an owner-confirmed command has no proof to run (spec step 6)."""
    return proof_snapshot(card_id, db) or ""


def proof_script_hashes(card_id):
    """{absolute path: sha256} of the proof scripts this card's proof has run, newest record per path.

    The snapshot binds the proof COMMAND string, but `python3 /x/.crew/verify.py` is only as good as the file
    behind it: on 2026-10-03 a worker rewrote verify.py to make its own proof pass (t_d3c396cd's audit follow-up).
    crew_safety.run_proof records each script's hash the first time it runs (a `proof_script_hash` event: at
    intake the script does not exist yet; the verifier writes it) and refuses a changed one. This guards against a
    writer grading its own homework, not against the coordinator: its `revise_script` decision records the new hash
    with its reason, or has the verifier rewrite the script (authorize_script_revision, send_to_verifier). The owner
    is never asked."""
    out = {}
    for kind, data in snapshot_events(card_id):
        if isinstance(data.get("script_hashes"), dict):
            out.update(data["script_hashes"])
    return out


def record_script_hashes(card_id, hashes, by="crew", why="", authorized_by=None):
    """Append the scripts' hashes to the card's snapshot (a no-op for an empty set); `why` is the reason of a
    revision and `authorized_by` the id of the coordinator decision that allowed it."""
    if not hashes:
        return False
    payload = {"script_hashes": dict(hashes), "by": by, "why": why, "ts": time.time()}
    if authorized_by is not None:
        payload["authorized_by"] = authorized_by
    return _append_card_event(card_id, "proof_script_hash", payload)


def authorize_script_revision(card_id, why):
    """The coordinator's permission for this card's verifier to rewrite the proof script once: an event written by
    crew code from a coordinator decision (never a body line a model could type). Consumed by the next run that
    records the changed hash (crew_safety.script_change)."""
    return _append_card_event(card_id, "proof_script_hash", {"authorizes": why, "by": "coordinator",
                                                              "ts": time.time()})


def decision_id(card_id, kind, db=None):
    """The event id of the card's newest `crew_decision` of this kind, None when there is none."""
    db = db or kanban_db()
    if not db:
        return None
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        try:
            row = conn.execute("select max(id) from task_events where task_id = ? and kind = 'crew_decision' "
                               "and json_extract(payload, '$.decision') = ?", (card_id, kind)).fetchone()
        finally:
            conn.close()
    except Exception:
        return None
    return row[0] if row else None


def lift_into_review(card_id, reviewer, summary):
    """A stopped card into the kernel's `review` for `reviewer` with no gap a dispatcher could claim it in: the
    kernel calls run back to back in this process (no `hermes` subprocess between them), and a card the dispatcher
    claimed in between still goes (request_review refuses only a claim whose worker process is alive; a bare claim
    has no run to protect). Returns (ok, reason)."""
    kb, conn = kb_conn()
    try:
        task = kb.get_task(conn, card_id)
        if task is None:
            return False, "no such card"
        if task.status == "triage":
            kb.specify_triage_task(conn, card_id, author=current_profile())
        elif task.status == "blocked":
            kb.unblock_task(conn, card_id)
        ok, why = kb.request_review(conn, card_id, summary=summary, reviewer=reviewer, with_reason=True)
        if not ok:
            task = kb.get_task(conn, card_id)
            if task.status == "review" and task.assignee == reviewer:     # the kernel's own unblock resumed it there
                return True, reviewer
        return ok, why or reviewer
    finally:
        conn.close()


def send_to_verifier(card_id, summary):
    """Hand a card to its verifier's review step without a writer run: the card's model pin is swapped for the
    router's `review` pick (repin_for_review, as for any `Verify: independent` card), then the card goes into `review`
    with the verifier as reviewer (lift_into_review). A stopped card is lifted by that same step, never before it:
    the pin is swapped while the card cannot be claimed. Returns {"ok", "why"}."""
    row = card_row(card_id)
    if not row:
        return {"ok": False, "why": "no such card"}
    if verify_mode(row[4]) != "independent":
        return {"ok": False, "why": "not an independent-verification card"}
    repin_for_review(card_id)
    ok, why = lift_into_review(card_id, role_profile("verifier"), summary[:400])
    return {"ok": ok, "why": str(why)[-200:]}


def pending_script_authorization(card_id):
    """The reason of an authorization no later hash record has used up, else ''."""
    why = ""
    for kind, data in snapshot_events(card_id):
        if data.get("authorizes"):
            why = str(data["authorizes"])
        elif isinstance(data.get("script_hashes"), dict):
            why = ""
    return why


def script_revisions(card_id, db=None):
    """The reasons proof scripts of this card were revised, oldest first (a revision record carries a `why`)."""
    return [str(d["why"]) for kind, d in snapshot_events(card_id, db) if d.get("why") and d.get("script_hashes")]


def carry_script_hashes(src_card, dst_card):
    """An audit follow-up starts with its parent's hashes (and any authorization the coordinator gave the parent),
    so it cannot rewrite the script it was opened to fix unless the coordinator allowed it."""
    done = record_script_hashes(dst_card, proof_script_hashes(src_card), by="carried from %s" % src_card)
    why = pending_script_authorization(src_card)
    if why:
        authorize_script_revision(dst_card, why)
    return done


def closer_profiles(body=""):
    """The profiles whose verdict line counts toward closing this card. `Verify: proof`: the writer's profile;
    `Verify: independent`: the verifier's. The coordinator's own run counts in both (its `verify` decision and its
    audit are a second run of the proof, by nobody who wrote the card). A card with no `Verify:` line (opened
    before it existed) keeps the old rule: every crew role."""
    coord = {profile_prefix() + "coordinator", role_profile("coordinator")}
    mode = verify_mode(body)
    if mode == "independent":
        return {profile_prefix() + "verifier", role_profile("verifier")} | coord
    if mode == "proof":
        role = (field(body, "Role") or "").strip().lower()
        writers = [role] if role in WRITER_ROLES else list(WRITER_ROLES)
        return {profile_prefix() + r for r in writers} | {role_profile(r) for r in writers} | coord
    roles = ("worker", "content", "verifier", "coordinator")
    return {profile_prefix() + r for r in roles} | {role_profile(r) for r in roles}


def claimed_at(card_id, before_event_id=None):
    """Epoch seconds of the card's newest `claimed` event (before `before_event_id` when given), or None."""
    db = kanban_db()
    if not db:
        return None
    sql, args = "select max(created_at) from task_events where task_id = ? and kind = 'claimed'", [card_id]
    if before_event_id is not None:
        sql, args = sql + " and id < ?", args + [int(before_event_id)]
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        try:
            row = conn.execute(sql, args).fetchone()
        finally:
            conn.close()
    except Exception:
        return None
    return row[0] if row and row[0] is not None else None


def verdict_lines(card_id, claimed_ts=None, verdicts=None):
    """The card's PASS/FAIL lines, oldest first, since its newest claim when `claimed_ts` is given (a line from
    before the run that is finishing now proves nothing about that run)."""
    vs = [v for v in (all_verdicts(card_id) if verdicts is None else verdicts) if v.get("verdict") in ("PASS", "FAIL")]
    if claimed_ts is not None:
        vs = [v for v in vs if (v.get("ts") or 0) >= claimed_ts]
    return vs


def judge_verdicts(card_id):
    """The card's PASS/FAIL lines run by someone who did not write it - the verifier or the coordinator (its
    verify decision and its audit). "Passed first try" is about these: the writer's own PASS proves nothing
    independent (2026-10-03, t_d3c396cd: the worker's PASS, then the coordinator's audit FAIL, showed as
    "passed first try")."""
    judges = {profile_prefix() + r for r in ("verifier", "coordinator")} | \
        {role_profile(r) for r in ("verifier", "coordinator")}
    return [v for v in verdict_lines(card_id) if v.get("by") in judges]


def first_pass(card_id):
    """{passes, fails, first_pass, rounds} over the judge lines, or {} when no judge has run the proof yet."""
    lines = judge_verdicts(card_id)
    if not lines:
        return {}
    fails = 0
    for rec in lines:
        if rec["verdict"] == "PASS":
            return {"passes": sum(1 for v in lines if v["verdict"] == "PASS"),
                    "fails": fails, "first_pass": fails == 0, "rounds": len(lines)}
        fails += 1
    return {"passes": 0, "fails": fails, "first_pass": False, "rounds": len(lines)}


def close_check(card_id, body, claimed_ts=None, verdicts=None):
    """(ok, reason): may this card be closed now? `reason` is the exact thing missing when it may not.

    The rule: the newest run of the card's proof command is a PASS, recorded since the newest claim by a crew
    profile, and the newest verdict line of any kind is a PASS too (a check that failed after the proof passed
    holds the card). `claimed_ts` is the newest claim's time (None: never claimed, no age limit). The dashboard's
    verdict chip shows `verdict_lines(...)[-1]`, the same line this rule ends on."""
    if not needs_pass(body):
        return True, "no proof to run on this card"
    cmd = close_proof_command(card_id)
    if not cmd:
        return False, ("the card has no owner-confirmed proof command, so no PASS line can exist for it. Block it "
                       "and let the owner close it (hermes kanban complete) or name a proof")
    vs = verdict_lines(card_id, claimed_ts, verdicts)
    proof = [v for v in vs if (v.get("command") or "") == cmd]
    if not proof:
        return False, ("no verdict line for the card's proof command `%s` since the newest claim; run "
                       "`python3 \"$HERMES_HOME/plugins/crew/scripts/crew_card.py\" verdict --card %s`" % (cmd[:120], card_id))
    if proof[-1]["verdict"] != "PASS":
        return False, "the newest run of the proof command `%s` is a FAIL (rc=%s)" % (cmd[:120], proof[-1].get("rc"))
    if vs[-1]["verdict"] != "PASS":
        return False, "a check failed after the PASS line: `%s` (rc=%s)" % (
            (vs[-1].get("command") or "")[:120], vs[-1].get("rc"))
    closers = closer_profiles(body)
    if verdict_by(proof[-1]) not in closers:
        mode = verify_mode(body)
        who = {"proof": "the writer", "independent": "the verifier (kanban_request_review, reviewer %sverifier)"
               % profile_prefix()}.get(mode, "a crew role profile")
        return False, "the PASS line was run by %r, not by %s" % (verdict_by(proof[-1]) or "unknown", who)
    return True, "PASS by %s" % verdict_by(proof[-1])


FIX_DECISIONS = ("retry", "rescope", "split", "revise_script")      # the coordinator decisions that start a card over


def rework_fails(card_id):
    """FAIL lines since the card was last started over. Two end a rework loop; a coordinator fix (a `retry`,
    `rescope` or `split` decision) is a new start, so the count begins again after the newest one."""
    reset = None
    db = kanban_db()
    if db:
        marks = ",".join("?" * len(FIX_DECISIONS))
        try:
            conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
            try:
                row = conn.execute("select max(created_at) from task_events where task_id = ? and "
                                   "kind = 'crew_decision' and json_extract(payload, '$.decision') in (%s)"
                                   % marks, (card_id,) + FIX_DECISIONS).fetchone()
            finally:
                conn.close()
            reset = row[0] if row else None
        except Exception:
            reset = None
    return sum(1 for v in all_verdicts(card_id)
               if v.get("verdict") == "FAIL" and (reset is None or (v.get("ts") or 0) > reset))


PROOF_BLOCKED = 5       # `verdict` exit code: the safety floor refused the proof, nothing ran, no verdict line


def cmd_verdict(args):
    row = card_row(args.card)
    if not row:
        print("no such card: %s" % args.card)
        return 2
    cmd = close_proof_command(args.card)
    given = (args.command or "").strip()
    if given and given != cmd:
        print("refused: `verdict` runs only the card's owner-confirmed proof command%s. A different command "
              "is not run: the verifier runs its extra check with its own terminal tool."
              % ((" (%s)" % cmd[:80]) if cmd else ""))
        return 4
    if proof_cmd(row[4]) and proof_cmd(row[4]) != cmd:
        print("note: the proof command line on the card (%s) is not the one the card opened with; it is "
              "ignored" % proof_cmd(row[4])[:80])
    for_event = getattr(args, "for_event", None)
    if not cmd:
        print("card %s has no owner-confirmed proof command; FAIL until the owner confirms one" % args.card)
        rec = record_verdict(args.card, "", 1, "no owner-confirmed proof command on the card", 0, by=args.by,
                             for_event=for_event)
        rc = 1
    else:
        t0 = time.time()
        res = crew_safety.run_proof(cmd, None, args.timeout, crew_safety.proof_mode(args.card, cmd), card=args.card)
        if res.blocked:
            print("proof command: %s" % cmd)
            print("proof BLOCKED by Hermes safety, not run: %s" % res.blocked)
            return PROOF_BLOCKED
        out, rc = res.out, res.rc
        rec = record_verdict(args.card, cmd, rc, out, time.time() - t0, by=args.by, for_event=for_event)
        print("proof command: %s" % cmd)
        print("rc=%d" % rc)
        print("raw output:")
        print(out.rstrip()[:OUTPUT_KEEP] or "(no output)")
    fails = rework_fails(args.card)
    print("verdict: %s  (fails on this card: %d)  file: %s" % (rec["verdict"], fails, verdict_path(args.card)))
    if rec["verdict"] == "PASS":
        return 0
    if fails >= 2:
        reason = ("crew: %d failed verifications on this card. %s" % (
            fails, (rec.get("output_head") or "").strip().splitlines()[0][:180] if rec.get("output_head") else ""))
        print("second FAIL: the rework loop is closed - %s" % (
            "not handed back (--no-hand-back)" if args.no_hand_back else hand_back(args.card, reason)))
        return 3
    return 1


def hand_back(card_id, reason):
    """Two failed verifications end the rework loop, and the owner is not asked: the coordinator decides.

    A verifier's review run goes back to its writer through the kernel's request-changes. Any other run (the
    writer proving its own card, a coordinator audit) has no review to return, so the card blocks as
    `transient`; the coordinator loop handles both on the next tick and its decision turn is handed the FAIL
    lines. Returns one line saying which happened."""
    res = _kanban(["request-changes", card_id, reason], timeout=120)
    out = ((res.stdout or "") + (res.stderr or "")).strip()
    if res.returncode == 0:
        return "returned to its writer (request-changes): %s" % (out.splitlines()[-1] if out else "ok")
    res = _kanban(["block", card_id, "--kind", "transient", reason], timeout=120)
    out = ((res.stdout or "") + (res.stderr or "")).strip()
    return "blocked as transient for the coordinator (rc=%d): %s" % (res.returncode,
                                                                    out.splitlines()[-1] if out else "no output")


def progress_path(card_id):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(card_id))
    return os.path.join(hermes_home(), "crew", "progress", safe + ".json")


def load_progress(card_id):
    try:
        with open(progress_path(card_id)) as fh:
            return json.load(fh)
    except Exception:
        return {}


def start_progress(card_id, units):
    """One entry per unit of work, so the verifier can see which units passed.

    A single proof command says the card is done or not; a card with several deliverables needs
    per-unit evidence (the feature_list.json pattern from the round-2 research).
    """
    units = [u.strip() for u in units if u and u.strip()]
    if not units:
        return None
    data = {"card": card_id, "units": [{"unit": u, "pass": None, "evidence": "", "by": ""}
                                       for u in units],
            "created_at": time.time(), "updated_at": time.time()}
    os.makedirs(os.path.dirname(progress_path(card_id)), exist_ok=True)
    with open(progress_path(card_id), "w") as fh:
        json.dump(data, fh, indent=1)
    return progress_path(card_id)


def cmd_progress(args):
    data = load_progress(args.card)
    if not data:
        data = {"card": args.card, "units": [], "created_at": time.time()}
    if not args.unit:
        units = data.get("units") or []
        passed = sum(1 for u in units if u.get("pass") is True)
        print("card %s - %d of %d units passed" % (args.card, passed, len(units)))
        for u in units:
            mark = "PASS" if u.get("pass") is True else ("FAIL" if u.get("pass") is False else "open")
            print("  [%s] %s%s" % (mark, u.get("unit"), (" - " + u.get("evidence", "")) if u.get("evidence") else ""))
        return 0
    hit = None
    for u in data["units"]:
        if u.get("unit") == args.unit:
            hit = u
            break
    if hit is None:
        hit = {"unit": args.unit, "pass": None, "evidence": "", "by": ""}
        data["units"].append(hit)
    if args.pass_ is not None:
        hit["pass"] = args.pass_
    if args.evidence is not None:
        hit["evidence"] = args.evidence
    hit["by"] = args.by
    data["updated_at"] = time.time()
    os.makedirs(os.path.dirname(progress_path(args.card)), exist_ok=True)
    with open(progress_path(args.card), "w") as fh:
        json.dump(data, fh, indent=1)
    passed = sum(1 for u in data["units"] if u.get("pass") is True)
    print("card %s - unit %r: %s by %s (%d of %d units passed)" % (
        args.card, args.unit,
        "PASS" if hit.get("pass") is True else ("FAIL" if hit.get("pass") is False else "open"),
        args.by, passed, len(data["units"])))
    return 0


def cmd_closeout(args):
    ok = True
    for cid in [c for c in args.cards.split(",") if c]:
        row = card_row(cid)
        vs = all_verdicts(cid)
        last = vs[-1]["verdict"] if vs else "none"
        status = row[2] if row else "missing"
        print("%s status=%s latest_verdict=%s" % (cid, status, last))
        unproven = last == "none" and row and not needs_pass(row[4])     # a split child: the close-out proof counts
        ok = ok and status == "done" and (last == "PASS" or bool(unproven))
    return 0 if ok else 1


def rewrite_line(body, label, value):
    """Replace the `Label: ...` line, or append it: one owner for editing a contract line."""
    line = "%s: %s" % (label, " ".join(str(value).split()))
    new, hits = re.subn(r"(?mi)^\s*%s:.*$" % re.escape(label), lambda _m: line, body or "", count=1)
    return new if hits else (body or "").rstrip() + "\n" + line + "\n"


def pending_proof_ask(card_id):
    """The proof question the owner has not answered, or None: the newest `ask_owner` decision that carries a
    `proof_ask` ({kind: "rescope", proposed} or {kind: "blocked", command, reason}), unless a `proof_confirm`
    written by the owner came after it. The coordinator writes it (crew_coordinator.ask_proof),
    the owner's /crew-proof answer closes it."""
    db = kanban_db()
    if not db:
        return None
    rows = q_db(db, "select kind, payload from task_events where task_id = ? and kind in "
                    "('crew_decision', 'proof_confirm') order by id", (card_id,))
    ask = None
    for kind, payload in rows:
        try:
            data = json.loads(payload or "{}")
        except ValueError:
            continue
        if kind == "proof_confirm" and isinstance(data, dict) and data.get("by") == OWNER_BY:
            ask = None
        elif isinstance(data, dict) and data.get("decision") == "ask_owner" and isinstance(data.get("proof_ask"), dict):
            ask = data["proof_ask"]
    return ask


def owner_proof_answer(card_id, brave=False):
    """The owner's answer to the coordinator's proof question, through /crew-proof: the ONE way a proof command
    other than the opening one, or a flagged one, ever runs. Refused inside any agent run (a worker, the verifier,
    the coordinator's turn): only the owner's own /crew-proof answer counts, never the model whose proposal it is."""
    if os.environ.get("HERMES_KANBAN_TASK") or os.environ.get("CREW_COORDINATOR_TURN"):
        return "refused: a proof question is answered by the owner (/crew-proof), not from inside a card's run"
    ask = pending_proof_ask(card_id)
    if not ask:
        return "no open proof question on %s" % card_id
    if ask.get("kind") == "rescope":
        cmd = str(ask.get("proposed") or "").strip()
    elif brave:
        cmd = close_proof_command(card_id)
    else:
        return ("this proof was blocked by Hermes safety: answer `/crew-proof %s brave` to run it for this card, "
                "or ask the coordinator for a different proof" % card_id)
    if not cmd:
        return "nothing to confirm: the question carries no proof command"
    payload = {"proof_cmd": cmd, "by": OWNER_BY, "ts": time.time()}
    if brave:
        payload["proof_mode"] = "brave"
    _append_card_event(card_id, "proof_confirm", payload)
    row = card_row(card_id)
    if ask.get("kind") == "rescope" and row:
        _kanban(["edit", card_id, "--body", rewrite_line(row[4], "proof command", cmd)])
    res = lift_block(card_id)
    return ("confirmed proof for %s: %s%s; card %s" % (card_id, cmd[:120], " (brave)" if brave else "",
                                                       res.get("status") or "not blocked"))


def ledger_files(card_id):
    """Every budget ledger for this card, in this home and in every profile home."""
    base = base_home()
    roots = [os.path.join(base, "crew", "budget")]
    profdir = os.path.join(base, "profiles")
    if os.path.isdir(profdir):
        for name in sorted(os.listdir(profdir)):
            roots.append(os.path.join(profdir, name, "crew", "budget"))
    found = []
    for root in roots:
        path = os.path.join(root, card_id + ".json")
        if os.path.exists(path):
            found.append(path)
    return found


def spent_tokens(card_id):
    """Highest 'used' recorded for the card across all its ledgers."""
    used = 0
    for path in ledger_files(card_id):
        try:
            with open(path) as fh:
                used = max(used, int(json.load(fh).get("used") or 0))
        except Exception:
            continue
    return used


def triage_exit(card_id, body=None, author=None):
    """triage -> todo (ready when no parent is open) through the kernel's own exit, `specify_triage_task`: one
    transaction that writes `body` when given (None leaves every field alone), moves the card and records a
    `specified` event plus an audit comment. The kernel's second same-kind block (BLOCK_RECURRENCE_LIMIT) is what
    sends a card to triage, and its block counter is left as it is. True when the card left triage."""
    kb, conn = kb_conn()
    try:
        return bool(kb.specify_triage_task(conn, card_id, body=body, author=author or current_profile()))
    finally:
        conn.close()


# The words /crew-stop writes into the block (or the schedule) it parks a card with. Everything that must leave an
# owner-stopped card alone (coordinator, heal, notify) recognises the card by them, so there is ONE owner.
OWNER_STOP_MARK = "stopped by owner (/crew-stop)"


def owner_stop_reason(card_id):
    return "%s - continue with /crew-unstuck %s" % (OWNER_STOP_MARK, card_id)


def parked_by_owner(db, card_id):
    """The id of the event that parked this card when it is parked by /crew-stop right now, else 0.

    Parked = status blocked/scheduled AND the newest lifecycle event is a `blocked`/`scheduled` whose reason is the
    owner-stop words. An unblock (/crew-unstuck, the kernel's own) is newer than the park, so a continued card
    reads as not parked at once. Read-only; any error answers 0 (never parked)."""
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=10)
        try:
            st = conn.execute("select status from tasks where id = ?", (card_id,)).fetchone()
            if not st or st[0] not in ("blocked", "scheduled"):
                return 0
            ev = conn.execute("select id, kind, payload from task_events where task_id = ? and kind in "
                              "('blocked','scheduled','unblocked','block_loop_detected','gave_up') "
                              "order by id desc limit 1", (card_id,)).fetchone()
        finally:
            conn.close()
        if not ev or ev[1] not in ("blocked", "scheduled"):
            return 0
        reason = str((json.loads(ev[2] or "{}") or {}).get("reason") or "")
        return ev[0] if reason.startswith(OWNER_STOP_MARK) else 0
    except Exception:  # noqa: BLE001
        return 0


def lift_block(card_id, profile=None, body=None):
    """Put a blocked or triaged card back in the queue. Returns {rc, out, status}.

    triage: `triage_exit`, with `body` (the coordinator's rewrite: the new approach) when given.
    blocked / scheduled (a card /crew-stop parked): `hermes kanban unblock`."""
    row = card_row(card_id)
    if not row:
        return {"rc": 2, "out": "no such card", "status": None}
    if row[2] == "triage":
        try:
            ok = triage_exit(card_id, body=body)
            res = {"rc": 0 if ok else 1, "out": "left triage" if ok else "not in triage any more"}
        except (RuntimeError, ValueError) as exc:
            res = {"rc": 2, "out": str(exc)[:200]}
    elif row[2] in ("blocked", "scheduled"):
        cmd = [hermes_bin()] + (["-p", profile] if profile else []) + ["kanban", "unblock", card_id]
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        lines = (done.stdout + done.stderr).strip().splitlines()
        res = {"rc": done.returncode, "out": lines[-1] if lines else ""}
    else:
        res = {"rc": 0, "out": "already %s" % row[2]}
    res["status"] = (card_row(card_id) or [None] * 3)[2]
    return res


def verifier_block(card_id):
    """The verifier's finding when this card is blocked by the verifier's own run, else None.

    A `Verify: independent` card whose newest run is a verifier run that ended `blocked` is stopped by the
    verifier's judgement (t_3f619c1d: fabricated citations, a quality call a passing proof script cannot make).
    No proof result may lift it: it goes to the coordinator, who sends the fix to the writer, rescopes or asks the
    owner. Returns {"run", "reason"} (the reason is the `blocked` event the run wrote)."""
    db = kanban_db()
    if not db:
        return None
    row = card_row(card_id)
    if not row or row[2] != "blocked" or verify_mode(row[4]) != "independent":
        return None
    judges = {profile_prefix() + "verifier", role_profile("verifier")}
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        try:
            run = conn.execute("select id, profile, outcome from task_runs where task_id = ? order by id desc limit 1",
                               (card_id,)).fetchone()
            if not run or run[1] not in judges or run[2] != "blocked":
                return None
            ev = conn.execute("select payload from task_events where task_id = ? and kind = 'blocked' "
                              "order by id desc limit 1", (card_id,)).fetchone()
        finally:
            conn.close()
        reason = str((json.loads(ev[0] or "{}") if ev else {}).get("reason") or "")
    except Exception:
        return None
    return {"run": run[0], "reason": reason}


def hand_to_writer(card_id):
    """After a coordinator retry lifted an `independent` card: the WRITER runs next, never the verifier again.

    The kernel resumes a card whose block came from a review run in `review` (unblock_task), i.e. straight back to
    the verifier with nothing changed (t_3f619c1d, run 8). `reopen_review_task` sends it to `ready` for the
    implementer; a card still assigned to the verifier (an implementer recorded wrongly) is given to the card's
    writer profile (its `Role:` line, else the worker). Returns {"reopened", "assigned"}."""
    out = {"reopened": False, "assigned": ""}
    row = card_row(card_id)
    if not row or verify_mode(row[4]) != "independent":
        return out
    judges = {profile_prefix() + "verifier", role_profile("verifier")}
    role = (field(row[4], "Role") or "").strip().lower()
    writer = role_profile(role if role in WRITER_ROLES else "worker")
    if row[2] != "review" and not (row[2] in ("ready", "todo") and row[3] in judges):
        return out                    # nothing to hand back: the writer is already next
    kb, conn = kb_conn()
    try:
        if row[2] == "review":
            out["reopened"] = bool(kb.reopen_review_task(conn, card_id))
        now = card_row(card_id) or row
        if now[2] in ("ready", "todo") and now[3] in judges and kb.assign_task(conn, card_id, writer):
            out["assigned"] = writer
    finally:
        conn.close()
    return out


def unstuck_card(card_id):
    """The owner's way out when the coordinator has given up: (ok, text). A card in triage leaves it through the
    kernel's own exit with no field changed (it lands in todo, ready when no parent is open); a blocked card is
    unblocked with `hermes kanban unblock`; so is a card /crew-stop parked (blocked, or scheduled when it was
    parent-gated), which then resumes with its whole history. Any other state has nothing to unstick."""
    row = card_row(card_id)
    if not row:
        return False, "no such card: %s" % card_id
    if not is_crew_body(row[4]):
        return False, "%s is not a crew card" % card_id
    parked = row[2] == "scheduled" and parked_by_owner(kanban_db(), card_id)
    if row[2] not in ("triage", "blocked") and not parked:
        return False, "%s is %s: nothing to unstick" % (card_id, row[2])
    res = lift_block(card_id)
    if res["rc"] != 0:
        return False, "%s stays %s: %s" % (card_id, row[2], res["out"] or "the board refused")
    return True, "%s: %s -> %s" % (card_id, row[2], res["status"])


def retry_card(card_id, budget=None, dry_run=False, unblock=True, profile=None, body=None):
    """Raise a card's budget ceiling, reset the counter and let it run again. Returns a result dict.

    `body` is the card text to retry with (the coordinator's fix already written into it); default the card's
    own. The Budget line is rewritten in it and the result is written once: with the card's way out of triage
    (`specify_triage_task`) for a triaged card, with `hermes kanban edit --body` for any other."""
    row = card_row(card_id)
    if not row:
        return {"ok": False, "why": "no such card: %s" % card_id}
    status, assignee = row[2], row[3]
    body = row[4] if body is None else body
    used = spent_tokens(card_id)
    budget = budget or max(int(used * 1.6), budget_floor())
    new_body, hits = re.subn(r"(?mi)^(Budget:).*$", "Budget: %d tokens" % budget, body or "")
    if not hits:
        new_body = (body or "").rstrip() + "\nBudget: %d tokens\n" % budget
    res = {"ok": True, "card": card_id, "status": status, "assignee": assignee, "spent": used,
           "budget": budget, "dry_run": bool(dry_run), "ledgers_moved": 0, "unblock": None}
    if dry_run:
        return res
    if status == "triage" and unblock:
        res["unblock"] = lift_block(card_id, profile, body=new_body)      # the one write, in the kernel's exit
    elif new_body != (row[4] or ""):
        r = _kanban(["edit", card_id, "--body", new_body])
        if r.returncode != 0:
            return {"ok": False, "why": "could not write the budget into the card: %s"
                                        % (r.stderr or r.stdout or "").strip()[-160:]}
    for path in ledger_files(card_id):
        try:
            os.replace(path, path + ".spent")
            res["ledgers_moved"] += 1
        except OSError:
            pass
    if unblock and status != "triage":
        res["unblock"] = lift_block(card_id, profile)
    return res


def decision_detail(rec, limit=160):
    """The one line of substance in a coordinator decision record (`crew_decision` event payload): the fix,
    the owner question, the reason or the problem, whichever the decision carries. One owner for the order,
    so the card graph, the diagnose pass and the owner's message all quote the same words."""
    for key in ("fix", "question", "why", "problem"):
        if isinstance(rec, dict) and rec.get(key):
            return " ".join(str(rec[key]).split())[:limit]
    return ""


IN_FLIGHT_STATUSES = ("triage", "ready", "running", "blocked", "review")


def status_cards(limit=8):
    """(cards, total): the crew cards in flight, newest first, each with the coordinator's last decision.

    A card is in flight while its status is in IN_FLIGHT_STATUSES and its body is a crew body. `decision` is the
    newest `crew_decision` payload (or None); `question` is its owner question while the card is still blocked
    on it: the decision is an ask_owner recorded after the card's newest block event (crew_notify's own rule). `total` counts every card in flight, `cards` only the newest `limit`. None when there is no board."""
    db = kanban_db()
    if not db:
        return None
    conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    try:
        rows = conn.execute(
            "select t.id, t.title, t.status, t.assignee, t.body, "
            "(select e.payload from task_events e where e.task_id = t.id and e.kind = 'crew_decision' "
            " order by e.id desc limit 1), "
            "(select e.id from task_events e where e.task_id = t.id and e.kind = 'crew_decision' "
            " order by e.id desc limit 1), "
            "coalesce((select max(e.id) from task_events e where e.task_id = t.id and e.kind in "
            " ('blocked', 'block_loop_detected', 'gave_up')), 0) from tasks t where t.status in (%s) order by t.created_at desc"
            % ",".join("?" * len(IN_FLIGHT_STATUSES)), IN_FLIGHT_STATUSES).fetchall()
    finally:
        conn.close()
    cards = []
    for cid, title, status, assignee, body, payload, decision_id, stop_id in rows:
        if not is_crew_body(body):
            continue
        try:
            decision = json.loads(payload) if payload else None
        except ValueError:
            decision = None
        if not isinstance(decision, dict):
            decision = None
        ask = (decision and decision.get("decision") == "ask_owner" and status == "blocked"
               and (decision_id or 0) > stop_id)
        # a card in triage is the kernel's second same-kind block: the coordinator tries to rewrite it out, and
        # when it has not, it waits for the owner's /crew-unstuck
        cards.append({"id": cid, "title": title or "", "status": status, "assignee": assignee or "-",
                      "decision": decision, "question": str(decision.get("question") or "") if ask else "",
                      "unstuck": status == "triage"})
    return cards[:limit], len(cards)


def status_text(limit=8):
    """The /crew-status reply: one block per card in flight, its last coordinator decision and, when the card
    waits on the owner, the question."""
    got = status_cards(limit)
    if got is None or not got[1]:
        return "no cards in flight"
    cards, total = got
    blocks = []
    for c in cards:
        lines = ["Title: %s\n  ID: %s    status: %s    assignee: %s" % (c["title"], c["id"], c["status"], c["assignee"])]
        d = c["decision"]
        if d:
            detail = decision_detail(d, 100)
            lines.append("  Coordinator: %s%s" % (d.get("decision", "?"), (" - " + detail) if detail else ""))
        if c["question"]:
            lines.append("  Needs you: %s" % c["question"])
        if c["unstuck"]:
            lines.append("  Needs you: /crew-unstuck %s" % c["id"])
        blocks.append("\n".join(lines))
    more = "\n\n(+%d more)" % (total - len(cards)) if total > len(cards) else ""
    return "open cards: %d\n\n%s%s" % (total, "\n\n".join(blocks), more)


def ledger_spent(card_id):
    """(used, budget) over every budget ledger of the card, this home and every profile home, the
    `.spent` copies a retry keeps included: what the card has cost so far and what it was given."""
    used = budget = 0
    base = base_home()
    roots = [os.path.join(base, "crew", "budget")]
    profdir = os.path.join(base, "profiles")
    if os.path.isdir(profdir):
        for name in sorted(os.listdir(profdir)):
            roots.append(os.path.join(profdir, name, "crew", "budget"))
    for root in roots:
        for suffix in ("", ".spent"):
            path = os.path.join(root, card_id + ".json" + suffix)
            try:
                with open(path) as fh:
                    data = json.load(fh)
                used = max(used, int(data.get("used") or 0))
                budget = max(budget, int(data.get("budget") or 0))
            except (OSError, ValueError, TypeError, AttributeError):
                continue
    return used, budget


def cmd_retry(args):
    res = retry_card(args.card, budget=args.budget, dry_run=args.dry_run,
                     unblock=not args.no_unblock,
                     profile=args.profile or (owner_profile() if owner_profile() != "default" else None))
    if not res["ok"]:
        print(res["why"])
        return 2
    print("card %s  status=%s  assignee=%s" % (res["card"], res["status"], res["assignee"]))
    print("spent so far: %s tokens  new ceiling: %s tokens" % (format(res["spent"], ","),
                                                               format(res["budget"], ",")))
    if args.dry_run:
        print("would rewrite the Budget line and unblock %s" % res["card"])
        return 0
    print("budget line rewritten, %d ledger(s) kept as *.spent, counter resets" % res["ledgers_moved"])
    if res["unblock"]:
        print("unblock: %s (rc=%d)" % (res["unblock"]["out"], res["unblock"]["rc"]))
    return 0


def _pct(values, q):
    if not values:
        return 0
    vals = sorted(values)
    idx = min(len(vals) - 1, int(round((len(vals) - 1) * q)))
    return vals[idx]


def cmd_stats(args):
    """Tokens per card and first-pass verifier rate - the two numbers the research says to watch."""
    db = kanban_db()
    cards = []
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=10)
        sql = "select id from tasks"
        params = ()
        if args.days:
            sql += " where coalesce(started_at, created_at) > ?"
            params = (time.time() - args.days * 86400,)
        cards = [r[0] for r in conn.execute(sql, params).fetchall()]
        conn.close()
    except Exception as exc:
        print("cannot read the board: %s" % exc)
        return 2
    first_pass = 0
    verified = 0
    fails_before_pass = []
    tokens = []
    worst = []
    for cid in cards:
        fp = first_pass(cid)
        if fp:
            verified += 1
            first = fp["first_pass"]
            n_fail = fp["fails"]
            fails_before_pass.append(n_fail)
            if first:
                first_pass += 1
            elif n_fail >= 2:
                worst.append((n_fail, cid))
        spent = spent_tokens(cid)
        if spent:
            tokens.append(spent)
    rate = (100.0 * first_pass / verified) if verified else 0.0
    print("cards on the board: %d   with a verdict: %d" % (len(cards), verified))
    print("first-pass verifier rate: %.1f%% (%d of %d passed on the first verifier run)"
          % (rate, first_pass, verified))
    print("fail rounds before a pass: median %s, p90 %s, max %s"
          % (_pct(fails_before_pass, 0.5), _pct(fails_before_pass, 0.9),
             max(fails_before_pass) if fails_before_pass else 0))
    print("tokens per card: median %s, p75 %s, p90 %s, max %s (n=%d)"
          % (fmt_tokens(_pct(tokens, 0.5)), fmt_tokens(_pct(tokens, 0.75)),
             fmt_tokens(_pct(tokens, 0.9)), fmt_tokens(max(tokens) if tokens else 0), len(tokens)))
    for n_fail, cid in sorted(worst, reverse=True)[:3]:
        print("  needs the owner: %s had %d failed verifications" % (cid, n_fail))
    return 0


def fmt_tokens(n):
    n = int(n or 0)
    if n >= 1000000:
        return "%.1fM" % (n / 1000000.0)
    if n >= 1000:
        return "%.0fk" % (n / 1000.0)
    return str(n)


def cmd_show_contract(args):
    row = card_row(args.card)
    if not row:
        print("no such card: %s" % args.card)
        return 2
    print("card: %s  status: %s  assignee: %s" % (row[0], row[2], row[3]))
    for key in ("Role", "Verify", "Budget", "GOAL", "Artifact", "Lands at", "For", "Constraints",
                "Done when", "proof command"):
        val = field(row[4], key)
        if val:
            print("%s: %s" % (key, val))
    snap = proof_snapshot(args.card)
    if snap is not None and snap != proof_cmd(row[4]):
        print("proof command at open (the one a PASS line counts for): %s" % (snap or "(none)"))
    return 0


def reexec_under_hermes_python(script):
    """Start `script` again under the Hermes venv's python when this one cannot import hermes_cli (a script run
    as plain `python3`): the few kernel calls with no `hermes kanban` command (leaving triage with a body,
    clearing a stale failure) need it. Returns when no switch is needed or possible; never loops."""
    if os.environ.get("CREW_REEXEC") == "1":
        return
    try:
        import hermes_cli  # noqa: F401
        return
    except ImportError:
        pass
    py = hermes_python()
    # abspath, not realpath: a venv's python is a symlink to the very binary a bare run uses, and is the one
    # whose site-packages count, so the two must not compare equal.
    if py and os.path.abspath(py) != os.path.abspath(sys.executable):
        os.environ["CREW_REEXEC"] = "1"
        os.execv(py, [py, script] + sys.argv[1:])


def main():
    reexec_under_hermes_python(SELF)
    ap = argparse.ArgumentParser(description="crew contract cards and verdicts")
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open")
    for name in ("title", "goal", "role", "artifact", "lands", "audience", "done-when", "proof-cmd",
                 "constraints", "assignee", "max-runtime", "units", "brief", "brief-source",
                 "model", "provider"):
        o.add_argument("--" + name, default=None)
    o.add_argument("--verify", default=None, choices=list(VERIFY_MODES),
                   help="proof: the writer proves it and the coordinator audits it; independent: a verifier "
                        "session runs it too (default: proof when a proof command is named)")
    o.add_argument("--proof-mode", default=None, choices=list(PROOF_MODES),
                   help="the owner's choice at intake: safe (Hermes stops a flagged proof and asks) or brave")
    o.add_argument("--route", default=None, metavar="CLASS",
                   choices=["auto", "short", "code", "doc", "agentic", "research"],
                   help="let the model router pick this card's worker model "
                        "(worker_route.py plan --class CLASS); the pick is pinned on the card")

    og = sub.add_parser("origin", help="where this card came from: own record, else inherited")
    og.add_argument("--card", required=True)

    rl = sub.add_parser("release", help="lift the dispatcher's hold on a card moved to a fresh model")
    rl.add_argument("--card", required=True)

    rr = sub.add_parser("reroute", help="a quota wall: re-pin the card on a fresh pick, or block it")
    rr.add_argument("--card", required=True)
    rr.add_argument("--model", default=None, help="the model that hit the wall")
    rr.add_argument("--provider", default=None, help="its Hermes provider id")
    rr.add_argument("--reason", default=None)
    rr.add_argument("--force-model", default=None, help="tests: apply this pick instead of asking")
    rr.add_argument("--force-provider", default=None)

    r = sub.add_parser("route", help="ask the model router for one pick (no card opened)")
    r.add_argument("--class", dest="route_class", default="code",
                   choices=["short", "code", "write", "doc", "agentic", "research"])
    r.add_argument("--task", default="", help="short task label for the routing log")
    r.add_argument("--no-log", action="store_true", help="do not write the pick to routing.jsonl")
    o.add_argument("--origin", default=None,
                   help="chat that opened the card, <platform>:<chat id> (e.g. "
                        "zulip:stream:<stream>|<topic>); its done report goes back there. "
                        "No default: without it the card stays silent when it ends")
    o.add_argument("--budget", type=int, default=None)
    o.add_argument("--parent", action="append", default=[])
    o.add_argument("--allow-no-proof-cmd", action="store_true")
    o.add_argument("--dry-run", action="store_true")
    o.add_argument("--json", action="store_true")
    p = sub.add_parser("plan")
    p.add_argument("--spec", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    v = sub.add_parser("verdict")
    v.add_argument("--card", required=True)
    v.add_argument("--command", default=None,
                   help="run this check instead of the card's proof command (extra evidence)")
    v.add_argument("--timeout", type=int, default=300)
    v.add_argument("--no-hand-back", action="store_true",
                   help="record and report only: a second FAIL does not return or block the card (the coordinator "
                        "loop runs verdicts for a card it is deciding about, and moves the card itself)")
    v.add_argument("--by", default=None,
                   help="profile named on the verdict line (the coordinator loop runs outside its own profile)")
    v.add_argument("--for-event", type=int, default=None,
                   help="the `completed` event this run audits (the coordinator loop's audit: one line per event)")
    pr = sub.add_parser("progress")
    pr.add_argument("--card", required=True)
    pr.add_argument("--unit", default=None)
    pr.add_argument("--pass", dest="pass_", action="store_true", default=None)
    pr.add_argument("--fail", dest="pass_", action="store_false")
    pr.add_argument("--evidence", default=None)
    pr.add_argument("--by", default="writer", choices=["writer", "verifier"])
    st = sub.add_parser("stats")
    st.add_argument("--days", type=int, default=0)
    c = sub.add_parser("closeout")
    c.add_argument("--cards", required=True)
    r = sub.add_parser("retry")
    r.add_argument("--card", required=True)
    r.add_argument("--budget", type=int, default=None,
                   help="new ceiling; default is 1.6x what was spent, with a floor")
    r.add_argument("--profile", default=None, help="profile that owns the board (default: the owner profile)")
    r.add_argument("--no-unblock", action="store_true")
    r.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("show-contract")
    s.add_argument("--card", required=True)
    pc = sub.add_parser("proof-check", help="read-only: would a proof command run in safe mode? ok | flagged: "
                                            "<reason> | hardline: <reason>")
    pc.add_argument("--command", required=True)
    sub.add_parser("safety", help="print the permanent proof-safety mode (safe or brave); /crew-safety sets it")
    w = sub.add_parser("watch", help="wait for the card's ending or owner question, print it, exit (crew_watch.py; "
                                     "the intake runs it as a background terminal so the session is told)")
    w.add_argument("--card", required=True)
    w.add_argument("--poll", type=int, default=None)
    w.add_argument("--lifetime", type=int, default=None)
    le = sub.add_parser("lesson", help="record a lesson for a role (crew_lessons.py): the plugin adds it to that "
                                       "role's later turns; use this, never edit a skill")
    le.add_argument("--role", required=True, help="worker, content, verifier, coordinator or all (comma list)")
    le.add_argument("--text", required=True, help="one or two lines")
    args = ap.parse_args()

    try:
        if args.cmd == "open":
            spec = {k.replace("-", "_"): getattr(args, k.replace("-", "_")) for k in
                    ("title", "goal", "role", "artifact", "lands", "audience", "done-when", "proof-cmd",
                     "constraints", "assignee", "max-runtime", "brief", "brief_source",
                     "model", "provider", "route", "verify", "proof_mode")}
            spec["budget"] = args.budget
            spec["origin"] = args.origin
            res = open_card(spec, dry_run=args.dry_run, allow_no_proof=args.allow_no_proof_cmd,
                            parents=args.parent)
            print(json.dumps(res, indent=1) if args.json else
                  "Created %s  assignee=%s  role=%s  budget=%s tokens%s%s" % (
                      res.get("id", "(dry run)"), res.get("assignee") or res.get("argv"), res["role"],
                      res["budget"], ("\nNote: " + res["budget_note"]) if res.get("budget_note") else "",
                      ("\nowner brief recorded" if res.get("brief_recorded") else "",
                       ("\nworker model pinned by the router: %s / %s"
                        % (res["route"]["provider"], res["route"]["model"]))
                       if res.get("route") else "")))
            return 0
        if args.cmd == "origin":
            found, src, hops = origin_of(args.card)
            print(json.dumps({"card": args.card, "origin": found.get("origin") or "",
                              "session": found.get("session") or "",
                              "source_card": src, "hops": hops,
                              "inherited": bool(found.get("inherited")),
                              "chat_type": found.get("chat_type") or ""}, indent=2))
            return 0 if found else 1
        if args.cmd == "release":
            print(json.dumps({"card": args.card, "released": release_hold(args.card)}, indent=2))
            return 0
        if args.cmd == "reroute":
            res = reroute_after_wall(args.card, model=args.model, provider=args.provider,
                                     reason=args.reason or "quota wall",
                                     force_pick=({"provider": args.force_provider,
                                                  "model": args.force_model, "why": "forced by --force"}
                                                 if args.force_model and args.force_provider else None))
            print(json.dumps(res, indent=2, default=str))
            return 0
        if args.cmd == "route":
            pick = route_pick(args.route_class, args.task or "", no_log=args.no_log)
            print(json.dumps(pick or {"provider": None, "model": None,
                                      "why": "no router pick (router absent or it said parent)"},
                             indent=2))
            return 0 if pick else 1
        if args.cmd == "plan":
            with open(args.spec) as fh:
                spec = json.load(fh)
            res = run_plan(spec, dry_run=args.dry_run)
            if args.json:
                print(json.dumps(res, indent=1))
            else:
                print("parent %s (%s) released=%s" % (res["parent"].get("id"), res["parent"].get("assignee"),
                                                      res["parent_released"]))
                for m in res["children"]:
                    print("child  %s  assignee=%s  role=%s" % (m.get("id"), m.get("assignee"), m.get("role")))
                print("close-out %s (%s)" % (res["closeout"].get("id"), res["closeout"].get("assignee")))
            return 0
        if args.cmd == "verdict":
            return cmd_verdict(args)
        if args.cmd == "closeout":
            return cmd_closeout(args)
        if args.cmd == "progress":
            return cmd_progress(args)
        if args.cmd == "retry":
            return cmd_retry(args)
        if args.cmd == "show-contract":
            return cmd_show_contract(args)
        if args.cmd == "proof-check":
            print(crew_safety.proof_check(args.command))
            return 0
        if args.cmd == "safety":
            print(crew_safety.permanent_mode())
            return 0
        if args.cmd == "watch":
            import crew_watch
            return crew_watch.main(["--card", args.card] + (["--poll", str(args.poll)] if args.poll else [])
                                   + (["--lifetime", str(args.lifetime)] if args.lifetime else []))
        if args.cmd == "lesson":
            import crew_lessons
            return crew_lessons.main(["add", "--role", args.role, "--text", args.text])
        if args.cmd == "stats":
            return cmd_stats(args)
    except ValueError as exc:
        print("refused: %s" % exc)
        return 4
    except Exception as exc:
        print("error: %s: %s" % (type(exc).__name__, exc))
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
