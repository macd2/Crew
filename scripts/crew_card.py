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


def _config_value(key):
    """Read one `crew:` scalar from this profile's config.yaml without a YAML dependency."""
    path = os.path.join(hermes_home(), "config.yaml")
    try:
        with open(path) as fh:
            lines = fh.read().splitlines()
    except OSError:
        return None
    inside = False
    for line in lines:
        if re.match(r"^crew:\s*$", line):
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
    return os.environ.get("CREW_PROFILE_PREFIX") or _config_value("profile_prefix") or DEFAULT_PREFIX


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


HERE_SCRIPTS = os.path.dirname(os.path.abspath(__file__))


def kanban_db():
    for path in (os.environ.get("HERMES_KANBAN_DB") or "", os.environ.get("KANBAN_DB") or "",
                 os.path.join(base_home(), "kanban.db")):
        if path and os.path.exists(path):
            return path
    return None


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


def verify_mode(body):
    """The card's `Verify:` line: "proof" (the writer proves it, the coordinator audits), "independent" (a
    verifier session runs it too), or "" for a card opened before the line existed."""
    mode = (field(body, "Verify") or "").strip().lower()
    return mode if mode in VERIFY_MODES else ""


def contract_gaps(c, allow_no_proof=False):
    gaps = []
    for key, label in REQUIRED:
        if key == "proof_cmd" and allow_no_proof:
            continue
        if not str(c.get(key) or "").strip():
            gaps.append(label)
    if str(c.get("role") or "").strip().lower() not in WRITER_ROLES:
        gaps.append("role (worker or content)")
    if str(c.get("verify") or "").strip().lower() not in ("",) + VERIFY_MODES:
        gaps.append("Verify (proof or independent)")
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
        "done_when": field(body, "Done when") or "",
        "proof_cmd": proof_cmd(body),
        "verify": (field(body, "Verify") or "").strip().lower(),
        "units": "|".join(units),
        "route": route, "model": model, "provider": provider,
    }


CONTRACT_KEY_RX = re.compile(
    r"^\s*(Role|Coordinator|Verifier|Verify|Budget|Origin|Route|GOAL|Artifact|Lands at|For|Constraints|Units|"
    r"Done when|proof command)\s*:", re.I)


def unparsed_lines(body):
    """The non-empty lines of an intake body that are not a contract field line (a field written over
    several lines keeps its continuation here, so rebuilding the body from the parsed contract loses nothing)."""
    return [ln.rstrip() for ln in (body or "").splitlines() if ln.strip() and not CONTRACT_KEY_RX.match(ln)]


def default_verify(c):
    """`proof` when the card names a proof command (the writer proves it, the coordinator audits it),
    `independent` when it names none: a verifier has to judge it, there is nothing to re-run."""
    mode = str(c.get("verify") or "").strip().lower()
    if mode in VERIFY_MODES:
        return mode
    return "proof" if str(c.get("proof_cmd") or "").strip() else "independent"


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
    units = [u.strip() for u in str(c.get("units") or "").split("|") if u.strip()]
    if units:
        lines += ["", "Units (one entry each in $HERMES_HOME/crew/progress/<card>.json):"]
        lines += ["  - %s" % u for u in units]
        lines += ["Mark a unit: python3 %s progress --card <card id> --unit \"<unit>\" --pass "
                  "--evidence \"<raw evidence>\" [--by verifier]" % SELF]
    lines += ["", "Done when: %s" % c["done_when"].strip()]
    if str(c.get("proof_cmd") or "").strip():
        lines += ["", "proof command: %s" % c["proof_cmd"].strip()]
    else:
        lines += ["", "proof command: (none - the verifier asks for one before accepting)"]
    if mode == "proof":
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


def _append_card_event(card_id, kind, payload):
    db = kanban_db()
    if not db:
        return False
    conn = sqlite3.connect(db)
    try:
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)",
                     (card_id, None, kind, json.dumps(payload), int(time.time())))
        conn.commit()
    finally:
        conn.close()
    return True


def apply_route(card_id, pick, pin=True):
    """Pin the card's worker to the model the router chose, and record why on the card.

    `pin=False` only records the `route` event: the intake's kanban_create already created the card
    with the model and provider, so the dispatcher can not spawn it on the profile's model first."""
    if not pick or not card_id:
        return False
    db = kanban_db()
    if not db:
        return False
    conn = sqlite3.connect(db)
    try:
        if pin:
            conn.execute("update tasks set model_override = ?, provider_override = ? where id = ?",
                         (pick["model"], pick["provider"], card_id))
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)",
                     (card_id, None, "route",
                      json.dumps({"provider": pick["provider"], "model": pick["model"],
                                  "task_class": pick.get("task_class"), "floor": pick.get("floor"),
                                  "menu_size": pick.get("menu_size"), "why": pick.get("why"),
                                  "by": current_profile(), "ts": time.time()}), int(time.time())))
        conn.commit()
    finally:
        conn.close()
    return True


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


def record_origin(card_id, env=None, note="", proof_cmd=None):
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
    conn = sqlite3.connect(db)
    try:
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)",
                     (card_id, None, "origin", json.dumps(payload), int(time.time())))
        conn.commit()
    finally:
        conn.close()
    return True


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
    it. Clearing that stale error lets the dispatcher spawn the card on the new model.
    """
    db = kanban_db()
    if not db or not card_id:
        return False
    conn = sqlite3.connect(db)
    try:
        if clear_error:
            conn.execute("update tasks set last_failure_error = null where id = ?", (card_id,))
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)",
                     (card_id, None, "hold_released",
                      json.dumps({"cleared_failure_error": bool(clear_error), "by": current_profile(),
                                  "ts": time.time()}), int(time.time())))
        conn.commit()
    finally:
        conn.close()
    return True


def workspace_root():
    return os.environ.get("CREW_WORKSPACE_ROOT") or os.path.join(base_home(), "kanban", "workspaces")


def repoint_workspace(card_id, path=None, release=True):
    """Give a card whose workspace is missing or unwritable a hermes-owned scratch dir.

    A card can be held forever by the respawn guard when its workspace path is unreadable (the guard
    reads a permission error as an auth blocker). Repointing it and clearing that stale error lets
    the card run again instead of sitting silently in the ready lane.
    """
    db = kanban_db()
    if not db or not card_id:
        return {"ok": False, "why": "no kanban db or no card"}
    target = path or os.path.join(workspace_root(), card_id)
    try:
        os.makedirs(target, exist_ok=True)
    except OSError as exc:
        return {"ok": False, "why": "cannot create %s (%s)" % (target, exc)}
    if not os.access(target, os.W_OK):
        return {"ok": False, "why": "%s is not writable by this user" % target}
    conn = sqlite3.connect(db)
    try:
        conn.execute("update tasks set workspace_kind = ?, workspace_path = ? where id = ?",
                     ("scratch", target, card_id))
        conn.commit()
    finally:
        conn.close()
    released = release_hold(card_id) if release else False
    _append_card_event(card_id, "workspace_repointed",
                       {"to": target, "kind": "scratch", "released": bool(released),
                        "by": current_profile(), "ts": time.time()})
    return {"ok": True, "workspace": target, "released": bool(released)}


def record_brief(card_id, text, source="owner", origin=None):
    """Store the owner's own words on the card, so the card view can show the brief above the
    coordinator: the page then reads from the /crew invocation to the close-out."""
    db = kanban_db()
    if not db or not text:
        return False
    now = time.time()
    conn = sqlite3.connect(db)
    try:
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)",
                     (card_id, None, "brief",
                      json.dumps({"text": text, "source": source, "by": current_profile(),
                                  "origin": origin or "", "ts": now}), int(now)))
        conn.commit()
    finally:
        conn.close()
    return True


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
    record_origin(card_id, env=env, note=c.get("title") or c.get("goal") or "",
                  proof_cmd=c.get("proof_cmd") or "")
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


def run_plan(spec, dry_run=False):
    """Parent contract card, independent children, coordinator close-out."""
    children = spec.get("children") or []
    if not children:
        raise ValueError("plan has no children")
    arts = [str(ch.get("artifact") or "").strip().lower() for ch in children]
    dup = sorted(set(a for a in arts if a and arts.count(a) > 1))
    if dup:
        raise ValueError("two writers on one artifact refused: %s" % ", ".join(dup))
    for i, ch in enumerate(children, 1):
        gaps = contract_gaps(ch)
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
        made.append(open_card(ch, dry_run=dry_run, parents=[parent.get("id") or "PARENT"]))
    close_parents = [m.get("id") or "CHILD" for m in made]
    cbody = ("Role: coordinator\nCoordinator: %s\n\nGOAL: close out %s\n\n"
             "Done when: every child card is done and its latest verdict line is PASS.\n\n"
             "proof command: python3 %s closeout --cards %s\n\n"
             "Run `python3 %s verdict --card $HERMES_KANBAN_TASK` (it runs the proof command and records the "
             "verdict). Exit 0: kanban_complete with its output. Otherwise kanban_block with kind 'transient' "
             "and the output.\n"
             % (current_profile(), parent.get("id") or "PARENT", SELF, ",".join(close_parents), SELF))
    closeout = create_card("close-out: " + (spec.get("title") or goal), cbody, coord,
                           parents=close_parents, dry_run=dry_run)
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
    role = (field(body, "Role") or "").strip().lower()
    return not (role == "coordinator" and not proof_cmd(body))


def proof_snapshot(card_id):
    """The proof command this card was opened with, or None for a card that has no snapshot (opened before
    snapshots existed, or a plan's close-out, which is not opened through `finish_card`).

    The `origin` event written when the card opened carries it in `proof_cmd`; the coordinator's applied
    `rescope` decision carries the one it changed it to. The newest of those wins. A `proof command:` line
    edited on the card afterwards is neither, so it can never produce a PASS."""
    db = kanban_db()
    if not db:
        return None
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        try:
            rows = conn.execute("select kind, payload from task_events where task_id = ? and kind in "
                                "('origin', 'crew_decision') order by id", (card_id,)).fetchall()
        finally:
            conn.close()
    except Exception:
        return None
    snap = None
    for kind, payload in rows:
        try:
            data = json.loads(payload or "{}")
        except ValueError:
            continue
        if not isinstance(data, dict):
            continue
        if kind == "origin" and "proof_cmd" in data:
            snap = str(data["proof_cmd"] or "").strip()
        elif (kind == "crew_decision" and data.get("decision") == "rescope" and data.get("applied")
              and str(data.get("proof_cmd") or "").strip()):
            snap = str(data["proof_cmd"]).strip()
    return snap


def close_proof_command(card_id, body):
    """The proof command a PASS line has to have run: the snapshot taken when the card opened (spec step 6), so
    a rewritten body line can never produce a PASS. A card with no snapshot falls back to its body line."""
    snap = proof_snapshot(card_id)
    return snap if snap is not None else proof_cmd(body)


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


def close_check(card_id, body, claimed_ts=None, verdicts=None):
    """(ok, reason): may this card be closed now? `reason` is the exact thing missing when it may not.

    The rule: the newest run of the card's proof command is a PASS, recorded since the newest claim by a crew
    profile, and the newest verdict line of any kind is a PASS too (a check that failed after the proof passed
    holds the card). `claimed_ts` is the newest claim's time (None: never claimed, no age limit). The dashboard's
    verdict chip shows `verdict_lines(...)[-1]`, the same line this rule ends on."""
    if not needs_pass(body):
        return True, "no proof to run on this card"
    cmd = close_proof_command(card_id, body)
    if not cmd:
        return False, ("the card has no proof command, so no PASS line can exist for it. Block it and let the "
                       "owner close it (hermes kanban complete) or name a proof")
    vs = verdict_lines(card_id, claimed_ts, verdicts)
    proof = [v for v in vs if (v.get("command") or "") == cmd]
    if not proof:
        return False, ("no verdict line for the card's proof command `%s` since the newest claim; run "
                       "`python3 \"$HERMES_HOME/scripts/crew_card.py\" verdict --card %s`" % (cmd[:120], card_id))
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


FIX_DECISIONS = ("retry", "rescope", "split")      # the coordinator decisions that start a card over


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


def cmd_verdict(args):
    row = card_row(args.card)
    if not row:
        print("no such card: %s" % args.card)
        return 2
    snap = close_proof_command(args.card, row[4])
    cmd = (args.command or "").strip() or snap
    if not (args.command or "").strip() and proof_cmd(row[4]) and proof_cmd(row[4]) != snap:
        print("note: the proof command line on the card (%s) differs from the one the card opened with; "
              "the opening one runs" % proof_cmd(row[4])[:80])
    for_event = getattr(args, "for_event", None)
    if not cmd:
        print("card %s has no proof command; FAIL until the contract names one" % args.card)
        rec = record_verdict(args.card, "", 1, "no proof command on the card", 0, by=args.by, for_event=for_event)
        rc = 1
    else:
        t0 = time.time()
        try:
            done = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=args.timeout)
            out, rc = (done.stdout or "") + (done.stderr or ""), done.returncode
        except subprocess.TimeoutExpired:
            out, rc = "proof command timed out after %ss" % args.timeout, 124
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
        ok = ok and status == "done" and last == "PASS"
    return 0 if ok else 1


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


def _lift_triage(db, card_id):
    """triage -> ready (todo while a parent is open). The kernel's own way out of triage is an aux-model
    specifier that rewrites the card; a crew card is never rewritten by one, so the coordinator lifts it
    with the same narrow write crew_heal.release_block makes, and records it as an `unblocked` event."""
    conn = sqlite3.connect(db, timeout=10)
    try:
        open_parents = conn.execute(
            "select count(*) from task_links l join tasks p on p.id = l.parent_id "
            "where l.child_id = ? and p.status not in ('done', 'archived')", (card_id,)).fetchone()[0]
        new = "todo" if open_parents else "ready"
        cur = conn.execute("update tasks set status = ?, consecutive_failures = 0, last_failure_error = null "
                           "where id = ? and status = 'triage'", (new, card_id))
        if cur.rowcount:
            conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                         "values (?,?,?,?,?)",
                         (card_id, None, "unblocked",
                          json.dumps({"status": new, "from": "triage", "by": current_profile()}),
                          int(time.time())))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _reset_block_loop(db, card_id):
    """Forget the kernel's same-kind block counter once a retry has been decided.

    The kernel keeps `block_kind`/`block_recurrences` across an unblock so a cron that unblocks blindly
    cannot loop forever, and routes the second same-kind block to `triage`. A retry that the coordinator
    (or the owner) decided is not a blind unblock - the coordinator caps its own retries per card - so the
    counter starts again and the next block lands in `blocked`, where the board and the feed read it."""
    conn = sqlite3.connect(db, timeout=10)
    try:
        conn.execute("update tasks set block_kind = null, block_recurrences = 0 "
                     "where id = ? and status in ('ready', 'todo')", (card_id,))
        conn.commit()
    finally:
        conn.close()


def lift_block(card_id, profile=None):
    """Put a blocked (or triaged) card back in the queue. Returns {rc, out, status}."""
    row = card_row(card_id)
    if not row:
        return {"rc": 2, "out": "no such card", "status": None}
    db = kanban_db()
    if row[2] == "triage":
        ok = _lift_triage(db, card_id)
        res = {"rc": 0 if ok else 1, "out": "lifted from triage" if ok else "not in triage any more"}
    elif row[2] == "blocked":
        cmd = [hermes_bin()] + (["-p", profile] if profile else []) + ["kanban", "unblock", card_id]
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        lines = (done.stdout + done.stderr).strip().splitlines()
        res = {"rc": done.returncode, "out": lines[-1] if lines else ""}
    else:
        res = {"rc": 0, "out": "already %s" % row[2]}
    if res["rc"] == 0:
        _reset_block_loop(db, card_id)
    res["status"] = (card_row(card_id) or [None] * 3)[2]
    return res


def retry_card(card_id, budget=None, dry_run=False, unblock=True, profile=None):
    """Raise a card's budget ceiling, reset the counter and let it run again. Returns a result dict."""
    row = card_row(card_id)
    if not row:
        return {"ok": False, "why": "no such card: %s" % card_id}
    status, assignee, body = row[2], row[3], row[4]
    used = spent_tokens(card_id)
    budget = budget or max(int(used * 1.6), budget_floor())
    new_body, hits = re.subn(r"(?mi)^(Budget:).*$", "Budget: %d tokens" % budget, body or "")
    if not hits:
        new_body = (body or "").rstrip() + "\nBudget: %d tokens\n" % budget
    res = {"ok": True, "card": card_id, "status": status, "assignee": assignee, "spent": used,
           "budget": budget, "dry_run": bool(dry_run), "ledgers_moved": 0, "unblock": None}
    if dry_run:
        return res
    conn = sqlite3.connect(kanban_db(), timeout=10)
    try:
        conn.execute("update tasks set body = ? where id = ?", (new_body, card_id))
        conn.commit()
    finally:
        conn.close()
    for path in ledger_files(card_id):
        try:
            os.replace(path, path + ".spent")
            res["ledgers_moved"] += 1
        except OSError:
            pass
    if unblock:
        res["unblock"] = lift_block(card_id, profile)
    return res


def decision_detail(rec, limit=160):
    """The one line of substance in a coordinator decision record (`crew_decision` event payload): the fix,
    the owner question, the reason or the problem, whichever the decision carries. One owner for the order,
    so the card graph, the diagnose pass and the live feed all quote the same words."""
    for key in ("fix", "question", "why", "problem"):
        if isinstance(rec, dict) and rec.get(key):
            return " ".join(str(rec[key]).split())[:limit]
    return ""


IN_FLIGHT_STATUSES = ("ready", "running", "blocked", "review")


def status_cards(limit=8):
    """(cards, total): the crew cards in flight, newest first, each with the coordinator's last decision.

    A card is in flight while its status is in IN_FLIGHT_STATUSES and its body is a crew body. `decision` is the
    newest `crew_decision` payload (or None); `question` is its owner question while the card is still blocked
    on it: the decision is an ask_owner recorded after the card's newest block event (the feed's own rule). `total` counts every card in flight, `cards` only the newest `limit`. None when there is no board."""
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
        cards.append({"id": cid, "title": title or "", "status": status, "assignee": assignee or "-",
                      "decision": decision, "question": str(decision.get("question") or "") if ask else ""})
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
        vs = [v for v in all_verdicts(cid) if v.get("verdict") in ("PASS", "FAIL")]
        if vs:
            verified += 1
            first = vs[0]["verdict"] == "PASS"
            n_fail = 0
            for v in vs:
                if v["verdict"] == "PASS":
                    break
                n_fail += 1
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


def main():
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
    o.add_argument("--route", default=None, metavar="CLASS",
                   choices=["auto", "short", "code", "doc", "agentic", "research"],
                   help="let the model router pick this card's worker model "
                        "(worker_route.py plan --class CLASS); the pick is pinned on the card")

    rp = sub.add_parser("repoint", help="a card whose workspace is missing or unwritable: give it "
                                         "a scratch dir and lift the respawn hold")
    rp.add_argument("--card", required=True)
    rp.add_argument("--workspace", default=None)

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
    args = ap.parse_args()

    try:
        if args.cmd == "open":
            spec = {k.replace("-", "_"): getattr(args, k.replace("-", "_")) for k in
                    ("title", "goal", "role", "artifact", "lands", "audience", "done-when", "proof-cmd",
                     "constraints", "assignee", "max-runtime", "brief", "brief_source",
                     "model", "provider", "route", "verify")}
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
        if args.cmd == "repoint":
            print(json.dumps(repoint_workspace(args.card, path=args.workspace), indent=2))
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
