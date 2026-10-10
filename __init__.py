"""Crew: kanban roles with a contract, one writer per card and independent verification.

The owner's surface is five entries:

  /crew <what you want>   intake by the coordinator in this chat (the `crew` skill). It checks
                          the ask critically, asks numbered questions while any contract field is
                          missing and opens the card (kanban_create, guarded and completed by this
                          plugin) only once the contract is complete, then the turn ends.
  /crew-status            the cards in flight, each with the coordinator's last decision and, when a
                          card waits on the owner, its one question.
  /crew-graph <card>      one card's flow graph: terminal box graph, two frames apart (--watch), or an
                          HTML file (--html).
  /crew-stop [<card>]     park one card, or every open crew card: worker killed, card held, history kept
                          (--archive drops one card for good).
  /crew-unstuck <card>    the owner's fallback when the coordinator gave up: a triage card leaves triage
                          unchanged, a blocked card (or one /crew-stop parked) is unblocked.
  /crew-diagnose [state]  a skill like the intake, so it runs in the invoking session's own turn: every
                          card in one board state with its id and reason, then how each would resume.
                          Read-only - it diagnoses, it never retries, unblocks or dispatches.

The plugin commands (/crew-status, /crew-graph, /crew-stop, /crew-unstuck) are deterministic and make no model call, and
each option is its own command, so the command list in /help and in every platform menu IS the option
list. Install and role checks are not commands: `python3 <crew repo>/install.py --check [--profile P]`
(`hermes plugins doctor` only validates that a plugin loads and registers; it prints nothing about roles,
crons or profile drift).

`/crew` is owned by the skill: a plugin slash command is always handled before skills and its
handler can only return text (gateway/run_inbound.py and cli.py treat any registered plugin
command as handled), so the plugin registers `crew-status`, `crew-graph` and `crew-stop`, never `crew`.

Once a card is open the coordinator owns it: the dispatch-tick hook below starts
scripts/crew_coordinator.py (one detached pass, no model unless a card needs a decision) and that pass heals,
retries, rescopes, splits or asks the owner one question. Nothing else routes a blocked card anywhere.

In role profiles (config `crew.role` set by the installer) the plugin also enforces the per-card
token budget as a hard stop and, for the verifier, blocks write/send commands on the terminal.
Roles come from $HERMES_HOME/roles/crew/roles.json; the installer records the package source
under `crew.source_dir`, which the scripts use to find the package when an installed copy lacks one.
"""

import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time

HOME = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
HERE = os.path.dirname(os.path.abspath(__file__))
USAGE = ("Usage: /crew <what you want>  (intake, asks its questions) | /crew-status"
         " | /crew-graph <card id|latest> [--watch N | --html [PATH]] | /crew-stop [<card id>] [--archive] [--dry-run] | /crew-unstuck <card id>"
         " | /crew-diagnose [state]  (read-only)")

# One slash command per option: the option lives in the command name, so /crew-status takes no
# argument and an argument-less option is discoverable in /help instead of hidden behind a sub.
# Each entry: (command name, option, args hint, one-line description for /help and the menus).
# The ORDER is importance, not alphabet. /crew itself and /crew-diagnose are skills and never a row here
# (a plugin command would shadow /crew, and /crew-diagnose must run in the invoking session's own turn),
# so the first row is the most important crew option, and any surface that leads with /crew puts this
# table right behind it (install.py CREW_MENU_ORDER is the same list, skills included).
COMMANDS = [
    ("crew-status", "status", "", "Crew cards in flight: the coordinator's last decision and any question for you"),
    ("crew-graph", "graph", "<card id|latest> [--watch N | --html [NAME]]",
     "One card's flow graph: terminal box graph, two frames apart (--watch), or an HTML file (--html)"),
    ("crew-stop", "stop", "[<card id>] [--archive] [--dry-run]",
     "Park one card, or every open crew card: kill its worker, close its session, hold the card (/crew-unstuck "
     "continues it; --archive drops one for good)"),
    ("crew-unstuck", "unstuck", "<card id>",
     "Put a stuck or parked card back in the queue: out of triage with no change, or unblock it"),
    ("crew-safety", "safety", "[brave|safe]",
     "How careful unattended proof commands are: no argument shows the mode, brave stops asking, safe restores it"),
    ("crew-proof", "proof", "<card> <yes|brave>",
     "Answer a card's proof question: yes accepts a proposed proof command, brave runs a blocked one"),
]


def _hermes_bin():
    return os.environ.get("HERMES_BIN") or shutil.which("hermes") or "hermes"


def _tasks_db():
    """The active board's kanban.db, or None: scripts/crew_card.py kanban_db() is the one resolver."""
    resolve = getattr(_card_tool(), "kanban_db", None)
    return resolve() if callable(resolve) else None


def _card_body(task_id):
    db = _tasks_db()
    if not db or not task_id:
        return ""
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        row = conn.execute("select body from tasks where id = ?", (task_id,)).fetchone()
        conn.close()
        return (row or [""])[0] or ""
    except Exception:
        return ""


WRITER_ROLES = ("worker", "content")
CREW_ROLES = ("coordinator", "worker", "content", "verifier")


def _card_tool():
    """Load scripts/crew_card.py (the plugin's own copy, see _script_path) as a module."""
    return _load_script("crew_card.py", "crew_card_tool")


_RESULT_TOOL = None


def _result_tool():
    """scripts/crew_result.py (the one reader of a tool result row), loaded once per process: the thrash
    stop calls it after every tool call, so it must not re-read the file each time."""
    global _RESULT_TOOL
    if _RESULT_TOOL is None:
        _RESULT_TOOL = _load_script("crew_result.py", "crew_result_tool")
    return _RESULT_TOOL


def _load_script(name, module_name):
    path = _script_path(name)
    if not path:
        return None
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- the option commands


def _session_origin():
    """`<platform>:<chat id>` of the chat this command came from, or "" off a chat (CLI, cron,
    kanban worker). The card carries it as `Origin:` so its done report goes back there."""
    try:
        from gateway.session_context import get_session_env
        platform = (get_session_env("HERMES_SESSION_PLATFORM", "") or "").strip().lower()
        chat = (get_session_env("HERMES_SESSION_CHAT_ID", "") or "").strip()
    except Exception:
        return ""
    if os.environ.get("HERMES_KANBAN_TASK") or not platform or not chat:
        return ""
    if platform in ("cli", "tui", "desktop", "kanban", "cron", "api_server", "local", "webhook"):
        return ""
    return "%s:%s" % (platform, chat)


def _cmd_status(_rest=""):
    tool = _card_tool()
    if tool is None:
        return "crew_card.py not found - run install.py --check"
    try:
        return tool.status_text()
    except Exception as exc:  # noqa: BLE001 - a status read must never break the chat turn
        return "crew-status failed: %s" % exc


# The one pass that walks the whole board rather than one card: (script, timeout seconds).
_MAINTENANCE = {
    # stop kills processes and waits for each signal to land, so it gets the longer ceiling
    "stop": ("crew_stop.py", 600),
}


def _cmd_maintenance(action, rest):
    """Run the whole-board stop pass and return its own output, not a summary of it.

    The script is the proof: its lines say what it lifted, fixed or decided. Arguments are passed
    through as separate words (no shell), so a typo comes back as the script's own usage error.
    """
    script, timeout = _MAINTENANCE[action]
    path = _script_path(script)
    if not path:
        return "%s not found - run install.py --check" % script
    try:
        r = subprocess.run([sys.executable, path] + [a for a in (rest or "").split() if a],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "%s timed out after %ds" % (action, timeout)
    except Exception as exc:  # noqa: BLE001 - a pass must never break the chat turn
        return "%s failed: %s" % (action, exc)
    out = (r.stdout + r.stderr).strip()
    if not out:
        return "%s: nothing to do (exit %d)" % (action, r.returncode)
    return out if r.returncode == 0 else "%s (exit %d):\n%s" % (action, r.returncode, out)


# Hermes approvals.mode that "brave" sets (hermes_cli config: manual | smart | off). "safe" puts back what each
# profile had before brave (kept in <base home>/crew/safety-approvals.json), "manual" when nothing was kept.
BRAVE_APPROVALS, SAFE_FALLBACK = "off", "manual"


def _cmd_safety(rest=""):
    """/crew-safety [brave|safe]: show, or set for good, how careful unattended proofs are.

    The mode lives where Hermes keeps it - approvals.mode in each crew role profile - so one switch covers
    the proofs (crew_safety.permanent_mode reads the coordinator's) and the workers' own terminal tool."""
    tool = _card_tool()
    if tool is None:
        return "crew_card.py not found - run install.py --check"
    want = (rest or "").strip().lower()
    if not want:
        mode = tool.crew_safety.permanent_mode()
        return ("crew proof safety: %s. %s Change it with /crew-safety brave or /crew-safety safe." % (mode, (
            "Nothing stops a proof except Hermes's hardline list and your approvals.deny rules."
            if mode == "brave" else "A proof Hermes flags as dangerous stops the card and asks you.")))
    if want not in ("brave", "safe"):
        return "usage: /crew-safety [brave|safe]"
    names = [r.get("name") for r in tool.roles_defaults().get("roles", []) if r.get("name")] or list(CREW_ROLES)
    state_path = os.path.join(tool.base_home(), "crew", "safety-approvals.json")
    try:
        with open(state_path) as fh:
            kept = json.load(fh)
    except (OSError, ValueError):
        kept = {}

    def hermes(profile, *args):
        return subprocess.run([_hermes_bin(), "-p", profile, "config"] + list(args), capture_output=True, text=True,
                              timeout=60)

    shown, failed = [], []
    for name in names:
        profile = tool.profile_prefix() + name
        if not tool.profile_exists(profile):
            continue
        try:
            got = hermes(profile, "get", "approvals.mode")
            cur = (got.stdout or "").strip().splitlines()[-1].strip() if got.returncode == 0 and (got.stdout or "").strip() else ""
            if want == "brave":
                target = BRAVE_APPROVALS
                if cur and cur != BRAVE_APPROVALS:
                    kept[profile] = cur            # what safe puts back
            elif cur.lower() in ("off", "false"):
                target = kept.pop(profile, None) or SAFE_FALLBACK
            else:
                target = cur or SAFE_FALLBACK      # already careful: leave the owner's value alone
            if target != cur:
                if hermes(profile, "set", "approvals.mode", target).returncode != 0:
                    raise OSError("config set failed")
            shown.append("%s: %s -> %s" % (profile, cur or "unset", target))
        except Exception:  # noqa: BLE001 - a missing hermes binary is a failed profile, not a broken chat turn
            failed.append(profile)
    try:
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, "w") as fh:
            json.dump(kept, fh, indent=1)
    except OSError:
        failed.append("(could not save %s)" % state_path)
    text = "crew proof safety: %s (approvals.mode %s)." % (want, "; ".join(shown) or "no profile")
    if failed:
        text += " FAILED on %s." % ", ".join(failed)
    if want == "brave":
        text += (" Brave also lets the workers' own terminal commands run unprompted, not only the proofs; "
                 "Hermes's hardline list and your approvals.deny rules still apply.")
    return text


def _cmd_proof(rest):
    """/crew-proof <card> <yes|brave>: the owner's answer to a card's proof question. The one place a proof
    command other than the opening one, or a flagged one, gets the owner's go-ahead; a worker, the verifier or
    the coordinator can never run it (owner_proof_answer refuses inside any agent run)."""
    words = (rest or "").split()
    if not words:
        return "usage: /crew-proof <card> <yes|brave>"
    card = words[0]
    flag = words[1].strip().lower() if len(words) > 1 else ""
    if flag not in ("yes", "brave"):
        return "usage: /crew-proof <card> <yes|brave>"
    tool = _card_tool()
    if tool is None:
        return "crew_card.py not found - run install.py --check"
    try:
        return tool.owner_proof_answer(card, brave=(flag == "brave"))
    except Exception as exc:  # noqa: BLE001 - an owner answer must never break the chat turn
        return "crew-proof failed: %s" % exc


def _option_handler(action):
    """One slash command per option: the name carries the option, the text after it is its args."""
    run = {"status": _cmd_status, "graph": _cmd_graph, "unstuck": _cmd_unstuck,
           "stop": lambda rest: _cmd_maintenance("stop", rest), "safety": _cmd_safety,
           "proof": _cmd_proof}[action]

    def handler(raw_args):
        return run((raw_args or "").strip())

    return handler


def _config_get(key):
    try:
        r = subprocess.run([_hermes_bin(), "config", "get", key],
                           capture_output=True, text=True, timeout=30)
        out = r.stdout.strip()
        return out if r.returncode == 0 and out else None
    except Exception:
        return None


def _script_path(name):
    """A crew script from the plugin's own tree: <plugin dir>/scripts first, then `crew.source_dir` (the package
    checkout the installer ran from). Never $HERMES_HOME/scripts: that directory is the owner's, and code found
    there is not code this plugin shipped."""
    path = os.path.join(HERE, "scripts", name)
    if os.path.exists(path):
        return path
    src = _config_get("crew.source_dir")
    if src:
        path = os.path.join(src, "scripts", name)
        if os.path.exists(path):
            return path
    return None


_WALLS_SEEN = set()


def crew_quota_reroute(status_code=None, error=None, model=None, provider=None, **_kw):
    """api_request_error observer: a card never keeps spinning on a model that hit its quota wall.

    The wall is recorded on the card, the card is re-pinned on a fresh Jev pick over the agent-floor menu
    (the router's own ledger already holds the spent model) - or, when nothing on that menu is live, its
    pin is cleared so the role profile's own model runs - and the next run continues from the previous
    run's work through the crew hand-off. When there is nowhere to move and the wall repeats, the card is
    stopped with a transient block (the coordinator loop's) instead of burning more stalled attempts.
    """
    card = os.environ.get("HERMES_KANBAN_TASK")
    if not card or not _crew_role():
        return None
    low = ("%s %s" % (status_code or "", error or "")).lower()
    if not ("429" in low or "rate limit" in low or "rate_limit" in low or "quota" in low):
        return None
    key = (card, str(os.environ.get("HERMES_KANBAN_RUN_ID") or ""), str(model or ""))
    if key in _WALLS_SEEN:
        return None
    _WALLS_SEEN.add(key)
    tool = _card_tool()
    if tool is None or not hasattr(tool, "reroute_after_wall"):
        return None
    try:
        res = tool.reroute_after_wall(card, model=model, provider=provider)
    except Exception as exc:  # noqa: BLE001 - never break the worker's own error path
        _log_quota_failure(card, exc)
        return None
    if res.get("action") == "rerouted":
        to = res.get("to") or {}
        return {"context": "[crew] your model hit a quota wall. The card has been re-pinned to "
                           "%s/%s for the next run, and that run is handed the work already done, "
                           "so nothing is repeated." % (to.get("provider"), to.get("model"))}
    if res.get("action") == "unpinned":
        return {"context": "[crew] your model hit a quota wall and no free model can carry this card. The "
                           "pin is cleared: the next run uses the role profile's own model and is handed "
                           "the work already done, so nothing is repeated."}
    return None


def _log_quota_failure(card, exc):
    try:
        path = os.path.join(HOME, "crew", "quota-errors.log")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as fh:
            fh.write("%s card=%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), card, exc))
    except Exception:
        pass


def _handoff_text(card):
    """The previous runs' work for a retried card, built by scripts/crew_handoff.py."""
    path = _script_path("crew_handoff.py")
    if not path:
        return ""
    try:
        r = subprocess.run([sys.executable, path, "--card", str(card), "--record"],
                           capture_output=True, text=True, timeout=60)
    except Exception:  # noqa: BLE001 - a hand-off must never break the worker's turn
        return ""
    return (r.stdout or "").strip()


_HANDOFF_GIVEN = set()


def crew_handoff_hook(user_message=None, session_id=None, **_kw):
    """A worker picking up a card that already ran: hand it the work already done, once per session.

    Without this the new run (possibly on a different model - the router's pick can change between
    attempts) re-explores everything the previous run did.
    """
    card = os.environ.get("HERMES_KANBAN_TASK")
    role = _crew_role()
    if not card or not role:
        return None
    key = str(session_id or card)
    if key in _HANDOFF_GIVEN:
        return None
    _HANDOFF_GIVEN.add(key)
    text = "\n\n".join(t for t in (_handoff_text(card), _lessons_block(role)) if t)
    if not text:
        return None
    return {"context": text}


def _lessons_block(role=None):
    """The lessons file (scripts/crew_lessons.py) as context: a role's own plus `all`, or just `all` for the intake."""
    try:
        mod = _load_script("crew_lessons.py", "crew_lessons_tool")
        if mod is None:
            return ""
        return mod.block(role) if role else mod.intake_block()
    except Exception:  # noqa: BLE001 - no lessons is the old behaviour, never a broken turn
        return ""


def _graph_script():
    return _script_path("crew_graph.py")


def _run_graph(args, timeout=120):
    script = _graph_script()
    if not script:
        return None, "crew_graph.py not found - run install.py --check"
    cmd = [sys.executable, script] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "crew graph timed out"
    except Exception as exc:
        return None, "crew graph failed: %s" % exc
    return r.returncode, (r.stdout + r.stderr).strip()


def _fence(s):
    return "```\n%s\n```" % s


def _cmd_unstuck(rest):
    """The owner's fallback when the coordinator gave up on a card (crew_card.unstuck_card)."""
    words = (rest or "").split()
    if len(words) != 1:
        return "Usage: /crew-unstuck <card id>"
    tool = _card_tool()
    if tool is None:
        return "crew_card.py not found - run install.py --check"
    try:
        return tool.unstuck_card(words[0])[1]
    except Exception as exc:  # noqa: BLE001 - a board call must never break the chat turn
        return "crew-unstuck failed: %s" % exc


def _cmd_graph(rest):
    """One option, three modes: the terminal graph, `--watch N` (two frames), `--html [PATH]` (a file).
    The modes are flags on /crew-graph, not commands of their own."""
    parts = (rest or "").strip().split()
    card = parts[0] if parts and not parts[0].startswith("-") else "latest"
    words = parts[1:] if parts and not parts[0].startswith("-") else parts

    watch, html, i = None, None, 0
    while i < len(words):
        word = words[i]
        nxt = words[i + 1] if i + 1 < len(words) else ""
        if word in ("--watch", "-w"):
            if re.match(r"^\d+(\.\d+)?$", nxt):
                watch, i = max(1.0, min(float(nxt), 120.0)), i + 2
            else:
                watch, i = 4.0, i + 1
            continue
        if word in ("--html", "--page"):
            if nxt and not nxt.startswith("-"):
                html, i = nxt, i + 2
            else:
                html, i = "", i + 1
            continue
        i += 1

    if html is not None:
        # the file lands in the profile's own scratch dir and nowhere else: a bare file name only, so a
        # chat command cannot make the plugin write to an arbitrary path
        outdir = os.path.join(HOME, "cache", "scratch")
        if html and (html != os.path.basename(html) or html in (".", "..")):
            return "--html takes a file name only (it is written under %s)" % outdir
        os.makedirs(outdir, exist_ok=True)
        _code, out = _run_graph(["--card", card, "--html", html, "--outdir", outdir])
        return out

    if watch:
        c1, f1 = _run_graph(["--card", card])
        if c1 is None:
            return f1
        time.sleep(watch)
        c2, f2 = _run_graph(["--card", card])
        head = "live watch: two frames %.0fs apart\n" % watch
        return _fence("%s\n--- frame 1 ---\n%s\n--- frame 2 ---\n%s" % (
            head, f1 if c1 == 0 else "(error)", f2 if c2 == 0 else "(error)"))

    code, out = _run_graph(["--card", card])
    if code is None or code != 0:
        return out
    return _fence(out)


def _profile_name():
    h = os.path.abspath(HOME)
    if os.path.basename(os.path.dirname(h)) == "profiles":
        return os.path.basename(h)
    return "default"


# ---------------------------------------------------------------- role profile guards
# Active only in a role profile (config crew.role) and only inside a dispatcher-spawned worker
# (HERMES_KANBAN_TASK set), so the owner's own chat profile is never affected.

_ROLE = None
_BUDGET_CACHE = {}
ALWAYS_ALLOWED_OVER_BUDGET = {"kanban_block", "kanban_comment", "kanban_show", "kanban_heartbeat"}
# Allowed over budget only when the card passes the close rule (a PASS line for its proof command).
CLOSE_TOOLS_AFTER_PASS = {"kanban_complete", "kanban_request_review", "kanban_block"}
VERIFIER_BLOCKED_TOOLS = {"write_file", "patch", "skill_manage", "memory", "kanban_create", "kanban_link",
                          "cronjob_manage", "delegate_task", "execute_code", "send_message"}
# The coordinator's decision turn (crew_coordinator.py sets CREW_COORDINATOR_TURN) reads and decides; the loop
# applies the answer. The same write filter as the verifier, plus the verbs that would move the card itself.
COORDINATOR_TURN_BLOCKED = VERIFIER_BLOCKED_TOOLS | {"kanban_complete", "kanban_block", "kanban_unblock",
                                                     "kanban_request_review", "kanban_request_changes"}
# Terminal commands that write, move, delete, commit, publish or send. The proof command itself
# runs inside crew_card.py verdict (a subprocess), so it is not subject to this filter.
VERIFIER_WRITE_RX = re.compile(
    r"(?<![0-9&])>>?(?!&)|\btee\b|\brm\b|\bmv\b|\bcp\b|\bdd\b|\bchmod\b|\bchown\b|\bln\b|\btouch\b|"
    r"\bmkdir\b|\btruncate\b|\binstall\b|\bsed\s+-i|\bperl\s+-i|\bgit\s+(commit|push|add|reset|checkout|"
    r"merge|rebase|tag|stash|clean|restore|rm|mv)\b|\bcurl\b[^|;]*\s(-X\s*(POST|PUT|PATCH|DELETE)|"
    r"--data|-d\s|-F\s|--upload-file|-T\s)|\bwget\b[^|;]*--post|\b(ssh|scp|rsync|sendmail|mail|mutt)\b|"
    r"\bhermes\b[^|;]*\b(send|config\s+set|kanban\s+(create|complete|edit|assign|archive|link))\b|"
    r"\bsystemctl\b|\bkill\b|\bpip\b|\bnpm\b|\bapt\b|\bsudo\b|\bsqlite3\b|\b(?:python3?|python)\s+-c\b")


# Direct board/consent writes a role agent must never make from its own shell: the sqlite3 CLI, or anything
# (an inline python one-liner, a heredoc) that names the consent function or the board's event tables/kinds.
# Consent and board state change only through the kernel tools and crew scripts, never a raw shell write.
BOARD_WRITE_RX = re.compile(r"\bsqlite3\b|\b(?:owner_proof_answer|proof_confirm|task_events|kanban\.db|kanban_db)\b",
                            re.I)


# The same write arriving as a FILE: a shell it cannot name the board in, but a script it writes can. A write whose
# body writes the board - an INSERT/UPDATE/DELETE naming a board table, or a call to the consent function - is
# refused for every role, so the script never exists to be run. Reads are untouched: a proof script may select.
BOARD_WRITE_FILE_RX = re.compile(
    r"\b(?:insert|replace)\s+into\s+[^\n]{0,30}?\b(?:task_events|task_runs|tasks)\b"
    r"|\bdelete\s+from\s+[^\n]{0,30}?\b(?:task_events|task_runs|tasks)\b"
    r"|\bupdate\s+[^\n]{0,30}?\b(?:task_events|task_runs|tasks)\b\s+set\b"
    r"|\bowner_proof_answer\b", re.I)


# The safety switch and a crew profile's own config are the owner's: `/crew-safety` writes approvals.mode in the
# crew profiles from the owner's session, never through an agent tool call. A role agent flipping it from its
# terminal would make every proof brave, exactly like forging consent, so every crew role is refused here.
CREW_CONFIG_WRITE_RX = re.compile(
    r"\bhermes\b[^|;]{0,200}?\bconfig\s+(?:set|unset|edit|import|reset)\b"
    r"|\bapprovals\.mode\b", re.I)
CREW_PROFILE_CONFIG_RX = re.compile(r"(?:^|/)profiles/crew-[^/]+/config\.yaml$")


def _crew_config_write_attempt(tool_name, args):
    """True when this call writes a crew profile's config or flips approvals.mode: a shell running
    `hermes ... config set ...`, or a file write to a crew role profile's config.yaml."""
    args = args if isinstance(args, dict) else {}
    if tool_name == "terminal":
        return bool(CREW_CONFIG_WRITE_RX.search(str(args.get("command") or "")))
    if tool_name in FILE_WRITE_TOOLS:
        return any(CREW_PROFILE_CONFIG_RX.search(p) for p in _file_tool_paths(args))
    return False


def _board_write_attempt(tool_name, args):
    """True when this call writes board state or proof consent, however it is dressed: a shell command that names
    the board (BOARD_WRITE_RX) or a file write whose body writes it (BOARD_WRITE_FILE_RX)."""
    args = args if isinstance(args, dict) else {}
    if tool_name == "terminal":
        return bool(BOARD_WRITE_RX.search(str(args.get("command") or "")))
    if tool_name in FILE_WRITE_TOOLS:
        body = " ".join(str(args.get(k) or "") for k in ("content", "patch", "new_string", "new_str", "old_string"))
        return bool(BOARD_WRITE_FILE_RX.search(body))
    return False


# Proof scripts live in a `.crew/` folder and belong to the verifier: a writer never creates or changes one, and the
# verifier's file tools reach nothing else.
CREW_DIR_RX = re.compile(r"(?:^|[\s'\"=/])\.crew(?:/|$)")
PATCH_FILE_RX = re.compile(r"^\*\*\* (?:Update|Add|Delete|Move to)[^:\n]*:\s*(.+)$", re.M)
FILE_WRITE_TOOLS = ("write_file", "patch")


def _file_tool_paths(args):
    return [p for p in [str(args.get("path") or "")] + PATCH_FILE_RX.findall(str(args.get("patch") or "")) if p.strip()]


def _only_crew_dir(args):
    """A file tool call whose every target is under `.crew/`: the one write the verifier has."""
    paths = _file_tool_paths(args if isinstance(args, dict) else {})
    return bool(paths) and all(CREW_DIR_RX.search(p) for p in paths)


def _writes_crew_dir(tool_name, args):
    """True when this call writes under a `.crew/` folder: write_file / patch on such a path (a V4A patch names its
    files in `*** Update File:` lines) or a terminal command that both writes (VERIFIER_WRITE_RX) and names `.crew/`.
    Reading a proof script is not a write."""
    args = args if isinstance(args, dict) else {}
    if tool_name in FILE_WRITE_TOOLS:
        return any(CREW_DIR_RX.search(p) for p in _file_tool_paths(args))
    if tool_name == "terminal":
        cmd = str(args.get("command") or "")
        return bool(CREW_DIR_RX.search(cmd) and VERIFIER_WRITE_RX.search(cmd))
    return False


def _crew_role():
    global _ROLE
    if _ROLE is None:
        _ROLE = ""
        try:
            with open(os.path.join(HOME, "config.yaml")) as fh:
                inside = False
                for line in fh:
                    if re.match(r"^crew:\s*$", line):
                        inside = True
                        continue
                    if inside:
                        if line.strip() and not line.startswith(" "):
                            break
                        m = re.match(r"^\s+role:\s*['\"]?([a-z]+)", line)
                        if m:
                            _ROLE = m.group(1)
                            break
        except OSError:
            pass
    return _ROLE


def _budget_file(card):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(card))
    return os.path.join(HOME, "crew", "budget", safe + ".json")


def _card_budget(card):
    if card not in _BUDGET_CACHE:
        m = re.search(r"^\s*Budget:\s*([0-9]+)", _card_body(card), re.M | re.I)
        _BUDGET_CACHE[card] = int(m.group(1)) if m else None
    return _BUDGET_CACHE[card]


def _budget_used(card):
    try:
        with open(_budget_file(card)) as fh:
            return int(json.load(fh).get("used", 0))
    except Exception:
        return 0


CACHE_READ_WEIGHT = 0.1     # a cache read bills at a tenth of the input rate (Anthropic)
CACHE_WRITE_WEIGHT = 1.25   # a cache write bills at 1.25x the input rate (Anthropic)


def _billed_tokens(usage):
    """One call's billed-token count for the card budget.

    The budget is a billed-token meter, not raw prompt volume: summing ``total_tokens`` charges a
    cache read at the full input rate. Measured on a whole-corpus audit card: 17 calls booked
    1,928,928 (1,660,642 of it cache-read, 86.1%) against 5,344 output tokens, so a 1,500,000
    ceiling bought ~13 calls while the billed equivalent of the same run was 500,077. Providers
    that report no cache buckets keep the old ``total_tokens`` behaviour.
    """
    try:
        total = int(usage.get("total_tokens") or 0)
    except Exception:
        total = 0
    try:
        cache_read = int(usage.get("cache_read_tokens") or 0)
        cache_write = int(usage.get("cache_write_tokens") or 0)
    except Exception:
        cache_read = cache_write = 0
    if not (cache_read or cache_write):
        return total
    try:
        plain = int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0)
    except Exception:
        plain = max(0, total - cache_read - cache_write)
    return int(round(plain + CACHE_READ_WEIGHT * cache_read + CACHE_WRITE_WEIGHT * cache_write))


def crew_budget_account(usage=None, **kwargs):
    """post_api_request observer: add this call's billed tokens to the card's running total."""
    card = os.environ.get("HERMES_KANBAN_TASK")
    if not card or not _crew_role() or not isinstance(usage, dict):
        return None
    tokens = _billed_tokens(usage)
    if not tokens:
        return None
    try:
        raw = int(usage.get("total_tokens") or 0)
    except Exception:
        raw = 0
    try:
        path = _budget_file(card)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path) as fh:
                prev = json.load(fh)
            if not isinstance(prev, dict):
                prev = {}
        except Exception:
            prev = {}

        def _int(key):
            try:
                return int(prev.get(key) or 0)
            except (TypeError, ValueError):
                return 0

        data = dict(prev)
        data.update({"card": card, "used": _int("used") + tokens, "budget": _card_budget(card),
                     "raw_total": _int("raw_total") + raw, "calls": _int("calls") + 1,
                     "raw_last": raw, "profile": _profile_name(), "updated": time.time()})
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(data, fh)
        os.replace(tmp, path)
    except Exception:
        pass
    return None


def _close_ok(card):
    """(ok, reason): the crew close rule for this card (crew_card.close_check), read from the one verdict log."""
    tool = _card_tool()
    if tool is None:
        return True, "crew_card.py not found"
    body = _card_body(card)
    return tool.close_check(card, body, tool.claimed_at(card))


def _verdict_fails(card):
    """FAIL lines on this card since it was last started over (crew_card.rework_fails)."""
    tool = _card_tool()
    return tool.rework_fails(card) if tool is not None else 0


def _stop_message(lead, kind, reason):
    """Every hard stop names the exact kanban_block call that ends the run, so the model never has to work out
    how to stop: the budget stop, the rework cap and the thrash stop all read through this one sentence."""
    return "%s Call kanban_block(kind='%s', reason='%s') and end." % (lead, kind, reason)


# Failed tool calls per card, this process only: a worker process is one card run, and the count is about the
# run in front of it, not about the card's history. kanban_* tools are not counted (a refused kanban_complete
# is the rule working). Two rules read it: a streak (an ok result starts the count again) and a rate (failures
# among the last few calls, for the run whose failures are scattered between ok results).
_FAIL_STREAK = {}
_FAIL_WINDOW = {}           # card -> the last `failure_window_calls` results, True where the call failed
_FAIL_LIMIT = None
_WINDOW_LIMITS = None


def _max_consecutive_failures():
    """roles.json `max_consecutive_failures` through crew_card, read once per process."""
    global _FAIL_LIMIT
    if _FAIL_LIMIT is None:
        tool = _card_tool()
        _FAIL_LIMIT = int(tool.max_consecutive_failures()) if tool is not None else 5
    return _FAIL_LIMIT


def _window_limits():
    """(max_window_failures, failure_window_calls) from roles.json through crew_card, read once per process."""
    global _WINDOW_LIMITS
    if _WINDOW_LIMITS is None:
        tool = _card_tool()
        _WINDOW_LIMITS = ((int(tool.max_window_failures()), int(tool.failure_window_calls()))
                          if tool is not None else (8, 25))
    return _WINDOW_LIMITS


def crew_thrash_hook(tool_name=None, result=None, **kwargs):
    """post_tool_call observer in a role profile: count failed tool results for the card, in a row and in a window.

    The classifier is crew_result.result_state, the one the dashboard's steps use, so a step the panel draws
    as failed is a step this counts as failed.
    """
    card = os.environ.get("HERMES_KANBAN_TASK")
    if not card or not _crew_role() or not tool_name or str(tool_name).startswith("kanban_"):
        return None
    reader = _result_tool()
    if reader is None:
        return None
    state, note, _out = reader.result_row(result)
    window = _FAIL_WINDOW.setdefault(card, [])
    window.append(state == "err")
    del window[:-_window_limits()[1]]
    if state == "err":
        n = _FAIL_STREAK.get(card, (0, ""))[0] + 1
        _FAIL_STREAK[card] = (n, note or "no reason given")
    else:
        _FAIL_STREAK.pop(card, None)
    return None


def _thrash_guard(card, tool_name):
    """pre_tool_call: after max_consecutive_failures failed calls in a row, refuse every tool except the ones a
    blocked card may still use, and say how to hand the card to the coordinator."""
    if tool_name in ALWAYS_ALLOWED_OVER_BUDGET:
        return None
    n, note = _FAIL_STREAK.get(card, (0, ""))
    if n >= _max_consecutive_failures():
        lead = "%d tool calls in a row failed (%s). Stop." % (n, note)
    else:
        window = _FAIL_WINDOW.get(card, [])
        if sum(window) < _window_limits()[0]:
            return None
        lead = "%d of the last %d tool calls failed (%s). Stop." % (
            sum(window), len(window), note or "no reason given")
    reader = _result_tool()
    reason = "crew: %s: %s" % (reader.THRASH_REASON if reader else "repeated tool failure", note)
    return {"action": "block", "message": _stop_message(lead, "transient", reason.replace("'", ""))}


def _note_overrun(card, used, budget, tool_name):
    """Record a budget overrun on a PASS card as a warning in the card's budget file."""
    try:
        path = _budget_file(card)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path) as fh:
                data = json.load(fh)
        except Exception:
            data = {"card": card, "used": used, "budget": budget}
        data["overrun_warning"] = {"used": used, "budget": budget, "tool": tool_name, "ts": time.time()}
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(data, fh)
        os.replace(tmp, path)
    except Exception:
        pass


# ---------------------------------------------------------------- the /crew trigger
# Crew starts only on /crew. The pre_llm_call preload records (session, turn) and opens an intake
# window for that session when the turn's user message is the literal `/crew ...` command (raw, or
# already expanded into the crew skill by the gateway / CLI slash rewrite).
#
# The guard allows a hand-made `crew_card.py open` inside such a turn, and inside that session's
# live intake window: the owner's answers to the intake's questions arrive in the NEXT turn - the
# reply to a `clarify` form, or a plain answer - which is not a /crew turn, and retyping the command
# to make the card openable is the friction this window removes.
#
# The window closes on the first card opened in it, and expires INTAKE_WINDOW_SECONDS after the owner's last
# turn in it (a /crew turn or, while the window is live, any later owner message: crew_intake_preload extends it,
# so an intake that stays in conversation - the owner chose to discuss first - is not cut off at 30 minutes). A
# session that never saw /crew has no window, so the gate itself is unchanged. Everything lives in
# this process's memory - no session database read on any tool call.

_CREW_TURNS = {}          # (session_id, turn_id) -> time recorded
_CREW_TURNS_MAX = 512
# How long a /crew turn (or the owner's latest message in its live window) leaves its session able to open the card. The clarify form's own wait is
# 600s (config clarify_timeout); 1800 leaves room for a slow answer without holding the door open
# for an ordinary session half an hour later.
INTAKE_WINDOW_SECONDS = 1800
_CREW_WINDOWS = {}        # session_id -> expiry epoch
# The gateway and the interactive CLI rewrite `/crew <ask>` into the skill prompt before the turn;
# this is the marker agent/skill_commands.build_skill_invocation_message writes for that rewrite.
CREW_SKILL_INVOKED_RX = re.compile(r"\[IMPORTANT: The user has invoked the \"crew\" skill\b")
CARD_OPEN_RX = re.compile(r"crew_card\.py[\"']?\s+open(?=\s|$|[;&|])")
PROBE_TITLE_RX = re.compile(r"--title(?:\s+|=)[\"']?PROBE\b")


# Answering crew's report. The in-session watcher (scripts/crew_watch.py, started by the intake as a
# background process with notify_on_complete) ends by delivering its output into the owner's session as a
# new turn wrapped by Hermes: `[IMPORTANT: Background process <id> completed ...` / `Command: ...crew_card.py
# watch --card <id>`. That turn - seen by the plugin, never written by a model - opens a REPORT window for
# that session and card. The owner's next message there ("do it again") runs the intake for a follow-up card
# without retyping /crew: the window is consumed by that message, which opens the session's intake window
# and gets the crew skill injected once. Other sessions and non-watcher completions open nothing.
REPORT_WINDOW_SECONDS = 1800
_REPORT_WINDOWS = {}      # session_id -> (card_id, expiry epoch); consumed by the owner's next message
WATCH_REPORT_RX = re.compile(
    r"\A\s*\[IMPORTANT: Background process \S+ completed\b[^\n]*\n\s*Command:[^\n]*"
    r"crew_card\.py[\"']?\s+watch\s+--card\s+(\S+)")


def _note_report(session_id, card_id):
    sid = str(session_id or "")
    if not sid:
        return
    _REPORT_WINDOWS[sid] = (card_id, time.time() + REPORT_WINDOW_SECONDS)
    if len(_REPORT_WINDOWS) > _CREW_TURNS_MAX:
        _REPORT_WINDOWS.pop(next(iter(_REPORT_WINDOWS)), None)


def _take_report(session_id):
    """The card id of this session's live report window, consumed (None when absent or expired)."""
    entry = _REPORT_WINDOWS.pop(str(session_id or ""), None)
    if entry and time.time() <= entry[1]:
        return entry[0]
    return None


def _crew_skill_text():
    try:
        with open(os.path.join(HERE, "skills", "crew", "SKILL.md"), encoding="utf-8") as fh:
            return _strip_frontmatter(fh.read())
    except OSError:
        return None


def _turn_key(session_id, turn_id):
    return (str(session_id or ""), str(turn_id or ""))


def _record_crew_turn(session_id, turn_id):
    if not (session_id or turn_id):
        return
    _CREW_TURNS[_turn_key(session_id, turn_id)] = time.time()
    if len(_CREW_TURNS) > _CREW_TURNS_MAX:
        for key, _ts in sorted(_CREW_TURNS.items(), key=lambda kv: kv[1])[:len(_CREW_TURNS) - _CREW_TURNS_MAX]:
            _CREW_TURNS.pop(key, None)


def _open_window(session_id):
    """A /crew turn leaves its session able to open the card for INTAKE_WINDOW_SECONDS."""
    sid = str(session_id or "")
    if not sid:
        return
    _CREW_WINDOWS[sid] = time.time() + INTAKE_WINDOW_SECONDS
    if len(_CREW_WINDOWS) > _CREW_TURNS_MAX:
        for key, _exp in sorted(_CREW_WINDOWS.items(), key=lambda kv: kv[1])[:len(_CREW_WINDOWS) - _CREW_TURNS_MAX]:
            _CREW_WINDOWS.pop(key, None)


def _close_window(session_id):
    """The window closes on the first card opened from it: one /crew, one card."""
    _CREW_WINDOWS.pop(str(session_id or ""), None)


def _window_live(session_id):
    sid = str(session_id or "")
    expiry = _CREW_WINDOWS.get(sid)
    if expiry is None:
        return False
    if time.time() > expiry:
        _CREW_WINDOWS.pop(sid, None)
        return False
    return True


def _is_crew_turn(session_id, turn_id):
    """The turn itself began with /crew, or its session has a live intake window from one."""
    return _turn_key(session_id, turn_id) in _CREW_TURNS or _window_live(session_id)


def _open_guard(tool_name, args, session_id, turn_id):
    """Refuse a direct `crew_card.py open` outside a /crew turn and its session's intake window
    (PROBE titles pass)."""
    if tool_name != "terminal":
        return None
    cmd = str((args or {}).get("command") or "")
    if not CARD_OPEN_RX.search(cmd) or PROBE_TITLE_RX.search(cmd):
        return None
    if _is_crew_turn(session_id, turn_id):
        return None
    return {"action": "block",
            "message": "crew cards open only from the owner's /crew command. This session has no "
                       "open crew intake, so crew_card.py open is refused. Answer the owner "
                       "normally; if they want crew work they type /crew <ask> and the intake "
                       "runs in that turn."}


def _session_get(name):
    """One session variable: the gateway's per-request context first (the hook runs inside the gateway
    process, where the chat is a context variable, not in os.environ), then the process environment."""
    try:
        from gateway.session_context import get_session_env
        value = get_session_env(name, "")
        if value:
            return value
    except Exception:
        pass
    return os.environ.get(name) or ""


_CREW_BRIEFS = {}         # session_id -> the owner's /crew ask, kept until the card it opens records it
_PENDING_ROUTES = {}      # (session_id, title) -> the router pick the guard pinned, for the route event


def _is_crew_create(args, tool):
    """A kanban_create that makes a crew card: assigned to a crew writer profile, or carrying the crew
    body lines. Any other kanban card the owner makes in the chat is not crew's to gate."""
    args = args if isinstance(args, dict) else {}
    writers = {tool.profile_prefix() + r for r in WRITER_ROLES}
    return str(args.get("assignee") or "") in writers or tool.is_crew_body(str(args.get("body") or ""))


def _create_refusal(text):
    return {"action": "block", "message": "crew card refused: " + text}


def _create_guard(args, session_id, turn_id):
    """pre_tool_call for the intake's `kanban_create`: the same gate as `crew_card.py open`, plus the
    contract check on the body the model wrote, and the canonical card the tool then creates.

    Returns a block, a `modify` (the body rebuilt by crew_card.render_body, so Coordinator, Verifier, Origin
    and the budget floor are the plugin's and never the model's guess, plus assignee, skills, runtime and the
    model pin) or None when the call is not a crew card. A coordinator or worker process (HERMES_KANBAN_TASK
    set) may create children: crew_card.py plan validates those."""
    if os.environ.get("HERMES_KANBAN_TASK"):
        return None
    tool = _card_tool()
    args = args if isinstance(args, dict) else {}
    if tool is None:
        if str(args.get("assignee") or "").startswith("crew-"):
            return _create_refusal("crew_card.py not found - run the installer.")
        return None
    if not _is_crew_create(args, tool):
        return None
    if not _is_crew_turn(session_id, turn_id):
        return _create_refusal(
            "crew cards open only from the owner's /crew command. This session has no open crew intake, "
            "so kanban_create for a crew card is refused. Answer the owner normally; if they want crew "
            "work they type /crew <ask> and the intake runs in that turn.")
    title = str(args.get("title") or "").strip()
    c = tool.parse_contract(str(args.get("body") or ""))
    c["title"] = title
    origin = _session_origin()
    if origin:  # the chat is known to the plugin, not to the model: the plugin's value wins
        c["origin"] = origin
    c["coordinator"] = tool.coordinator_id(_session_get("HERMES_SESSION_ID"))
    try:
        c = tool.prepare_contract(c)
    except ValueError as exc:
        return _create_refusal("%s. Ask the owner for exactly these fields (clarify), then call "
                               "kanban_create again." % exc)
    assignee = tool.role_profile(c["role"])
    body = tool.render_body(c)
    notes = tool.unparsed_lines(str(args.get("body") or ""))
    if notes:  # a field the model wrote over several lines: nothing it wrote is dropped
        body += "\nIntake notes (lines beyond the contract fields):\n" + "\n".join(notes) + "\n"
    new = {"body": body, "assignee": assignee,
           "skills": tool.card_skills(assignee, c["role"]),
           "max_runtime_seconds": 3600}
    model, provider, pick = c.get("model"), c.get("provider"), None
    if c.get("route") == "auto":
        pick = tool.route_pick(tool.role_task_class(c.get("role")), title or c.get("goal") or "",
                               profile=assignee)
        if pick:
            model, provider = pick["model"], pick["provider"]
    if model and provider:
        new["model"], new["provider"] = model, provider
        if len(_PENDING_ROUTES) > 64:
            _PENDING_ROUTES.pop(next(iter(_PENDING_ROUTES)), None)
        _PENDING_ROUTES[(str(session_id or ""), title)] = pick
    return {"action": "modify", "args": new}


def _drop_kernel_subscription(card_id):
    """Remove the notify subscription kanban_create's auto-subscribe just wrote for a crew card.

    The kernel notifier wakes the chat on every blocked / review_requested / changes_requested /
    gave_up event (gateway/kanban_watchers_notifier.py TERMINAL_KINDS), which would put the owner back
    in every retry the coordinator is handling. crew_notify (run by the coordinator pass) reports the ending once
    and raises an owner question only through an ask_owner decision, so a crew card has exactly one return path."""
    try:
        from hermes_cli import kanban_db_connect as kbc
        from hermes_cli import kanban_db_notify as kbn
        conn = kbc.connect()
        try:
            for sub in kbn.list_notify_subs(conn, card_id):
                kbn.remove_notify_sub(conn, task_id=card_id, platform=sub["platform"],
                                      chat_id=sub["chat_id"], thread_id=sub.get("thread_id") or None)
        finally:
            conn.close()
        return True
    except Exception:
        return False


def _created_card_id(result):
    parsed = result
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except (TypeError, ValueError):
            return ""
    if not isinstance(parsed, dict) or parsed.get("error") or parsed.get("ok") is False:
        return ""
    return str(parsed.get("task_id") or "")


def _finish_created_card(card_id, session_id, title):
    """post_tool_call for the intake's kanban_create: what crew_card.open_card does after
    `hermes kanban create` - the units file, the route record, the origin, the brief - and the window."""
    tool = _card_tool()
    body = _card_body(card_id)
    if tool is None or not tool.is_crew_body(body):
        return
    c = tool.parse_contract(body)
    c["title"] = title
    model, provider = tool.card_pin(card_id)
    pick = _PENDING_ROUTES.pop((str(session_id or ""), title), None)
    if model and provider and pick is None:
        pick = {"provider": provider, "model": model, "task_class": "hand",
                "why": "pinned by the intake's Route line"}
    sid = str(session_id or "")
    c["brief"] = _CREW_BRIEFS.pop(sid, "")
    env = tool.session_env(_session_get)
    tool.finish_card(card_id, c, tool.role_profile(c["role"]), env=env, pick=pick,
                     pinned=bool(model and provider))
    _drop_kernel_subscription(card_id)
    _close_window(session_id)


def _close_guard(tool_name, args):
    """One close rule, in every profile that loads the plugin (worker, verifier, coordinator, the owner's chat):
    `kanban_complete` on a crew card is refused unless the card's proof command has a PASS line in the verdict log
    (crew_card.close_check). The owner's override is `hermes kanban complete --force` from the CLI: it is not a
    tool call, so this guard never sees it, and the coordinator loop records it as an `owner_close` decision."""
    if tool_name != "kanban_complete":
        return None
    card = str((args or {}).get("task_id") or os.environ.get("HERMES_KANBAN_TASK") or "").strip()
    tool = _card_tool()
    if not card or tool is None:
        return None
    body = _card_body(card)
    if not tool.needs_pass(body):
        return None
    ok, why = tool.close_check(card, body, tool.claimed_at(card))
    if ok:
        return None
    return {"action": "block",
            "message": "crew close rule: card %s cannot be completed - %s. The card is done only when its proof "
                       "command has a PASS line in the verdict log; the owner can override from the CLI "
                       "(hermes kanban complete --force)." % (card, why)}


def _review_guard(tool_name, args):
    """`kanban_request_review` on a crew card follows the card's `Verify:` line. `proof`: the writer proves it and
    closes it (the coordinator audits afterwards), so no verifier session is opened - the call is refused with the
    two steps that do finish it. `closeout` (a part of a split): refused, it is completed directly.
    `independent`: the review goes ahead, after the card's model pin is swapped for
    the router's `review` pick (the writer's pin would otherwise carry over to the verifier's run). A card with no
    `Verify:` line keeps the old flow."""
    if tool_name != "kanban_request_review":
        return None
    card = str((args or {}).get("task_id") or os.environ.get("HERMES_KANBAN_TASK") or "").strip()
    tool = _card_tool()
    if not card or tool is None:
        return None
    mode = tool.verify_mode(_card_body(card))
    if mode == "proof":
        return {"action": "block",
                "message": "card %s is `Verify: proof`: no verifier session runs on it. Run `python3 \"$HERMES_HOME/"
                           "plugins/crew/scripts/crew_card.py\" verdict --card %s`, then kanban_complete with its raw output "
                           "(the coordinator audits the proof afterwards)." % (card, card)}
    if mode == "closeout":
        return {"action": "block",
                "message": "card %s is `Verify: closeout`: it is one part of a split and has no proof of its own. "
                           "kanban_complete it with the artifact paths; the close-out card runs the split card's "
                           "proof once every part is done." % card}
    if mode == "independent":
        if _crew_role() == "verifier":
            return {"action": "block",
                    "message": "card %s: the verifier never requests review: it would become the card's "
                               "implementer and every request-changes would come back to the verifier, not the "
                               "writer. PASS: kanban_complete; FAIL: kanban_request_changes naming the exact fix." % card}
        try:
            tool.repin_for_review(card)
        except Exception:  # noqa: BLE001 - a pin that could not be swapped must not stop the review
            pass
    return None


def _crew_skill_names():
    """The skills this plugin ships: the directories under its skills/ (install.py's skill_names, the same list)."""
    try:
        d = os.path.join(HERE, "skills")
        return {n for n in os.listdir(d) if os.path.isfile(os.path.join(d, n, "SKILL.md"))}
    except OSError:
        return set()


def _skill_edit_guard(tool_name, args):
    """pre_tool_call, every profile: `skill_manage` on one of crew's own skills is refused. The installed copy is
    overwritten on the next install and fails crew_parity_check; a lesson belongs in the lessons file. skill_manage
    names its target per op (`operations[].name`, `category/name` allowed) or, in the legacy flat shape, in `name`."""
    if tool_name != "skill_manage" or not isinstance(args, dict):
        return None
    ops = args.get("operations")
    named = [args.get("name")] + [o.get("name") for o in ops if isinstance(o, dict)] if isinstance(ops, list) \
        else [args.get("name")]
    mine = _crew_skill_names()
    hit = sorted({str(n).strip().split("/")[-1] for n in named if n} & mine)
    if not hit:
        return None
    return {"action": "block",
            "message": "crew's skills are shipped by the plugin and overwritten on update (%s); record the lesson with: "
                       "python3 \"$HERMES_HOME/plugins/crew/scripts/crew_card.py\" lesson --role <role> --text \"...\""
                       % ", ".join(hit)}


def crew_tool_guard(tool_name=None, args=None, **kwargs):
    """pre_tool_call policy: the /crew open gate everywhere (coordinator included), and in role
    profiles the per-card budget hard stop and the read-only verifier."""
    blocked = _open_guard(tool_name, args, kwargs.get("session_id"), kwargs.get("turn_id")) \
        or _skill_edit_guard(tool_name, args)
    if blocked:
        return blocked
    if tool_name == "kanban_create":
        try:
            verdict = _create_guard(args, kwargs.get("session_id"), kwargs.get("turn_id"))
        except Exception as exc:  # noqa: BLE001 - a hook error lets the call through, so fail closed here
            return _create_refusal("the crew guard failed (%s); nothing was created." % exc)
        if verdict is not None:
            return verdict  # not a crew card: the role guards below (the coordinator's read-only turn) still apply
    try:
        blocked = _close_guard(tool_name, args)
    except Exception as exc:  # noqa: BLE001 - a hook error lets the call through, so fail closed here
        blocked = {"action": "block", "message": "the crew close guard failed (%s); nothing was completed." % exc}
    if blocked:
        return blocked
    try:
        blocked = _review_guard(tool_name, args)
    except Exception as exc:  # noqa: BLE001 - a hook error lets the call through, so fail closed here
        blocked = {"action": "block", "message": "the crew review guard failed (%s); nothing was requested." % exc}
    if blocked:
        return blocked
    role = _crew_role()
    if role in CREW_ROLES and _crew_config_write_attempt(tool_name, args):
        return {"action": "block",
                "message": "the proof safety switch and the crew profiles' config belong to the owner: ask them "
                           "for /crew-safety brave|safe instead of setting approvals.mode yourself."}
    if role in CREW_ROLES and _board_write_attempt(tool_name, args):
        return {"action": "block",
                "message": "board state and proof consent change only through the crew's tools, never a raw shell "
                           "or a script of your own (sqlite3, task_events, proof_confirm, owner_proof_answer)."}
    if role in WRITER_ROLES and _writes_crew_dir(tool_name, args):
        return {"action": "block",
                "message": "proof files belong to the verifier: %s writes under .crew/ are refused. Fix the work, never "
                           "the proof (reading .crew/ is fine)." % role}
    if role == "coordinator" and os.environ.get("CREW_COORDINATOR_TURN"):
        if tool_name in COORDINATOR_TURN_BLOCKED:
            return {"action": "block",
                    "message": "the coordinator's decision turn changes nothing on the board (%s). Read, "
                               "decide, and end with the one JSON decision line; the loop applies it." % tool_name}
        if tool_name == "terminal" and VERIFIER_WRITE_RX.search(str((args or {}).get("command") or "")):
            return {"action": "block",
                    "message": "the decision turn's terminal is read/run only; this command writes, moves, "
                               "deletes, commits or sends. Answer with the JSON decision instead."}
    card = os.environ.get("HERMES_KANBAN_TASK")
    if not card or not role:
        return None
    if tool_name in ("kanban_request_review", "kanban_complete") and _verdict_fails(card) >= 2:
        return {"action": "block",
                "message": _stop_message(
                    "crew rework cap: card %s has two failed verifications. Stop writing." % card,
                    "transient", "crew: two failed verifications: <what is missing>")
                + " The coordinator decides what happens next."}
    blocked = _thrash_guard(card, tool_name)
    if blocked:
        return blocked
    budget = _card_budget(card)
    used = _budget_used(card)
    if budget and tool_name not in ALWAYS_ALLOWED_OVER_BUDGET and used >= budget:
        # A card the verifier already proved must still be closable: blocking the close only forces
        # a second run to finish work that passed. The overrun becomes a warning in the summary.
        if tool_name in CLOSE_TOOLS_AFTER_PASS and _close_ok(card)[0]:
            _note_overrun(card, used, budget, tool_name)
            warning = "WARNING: crew budget exceeded (%d of %d tokens); verdict already PASS." % (used, budget)
            for key in ("summary", "result", "reason"):
                if isinstance((args or {}).get(key), str) and args[key].strip():
                    return {"action": "modify", "args": {key: args[key].rstrip() + "\n" + warning}}
            return None
        return {"action": "block",
                "message": _stop_message(
                    "crew budget exhausted for card %s (%d of %d tokens). Hard stop." % (card, used, budget),
                    "needs_input", "Needs you: budget exhausted")}
    if role == "verifier":
        if tool_name in VERIFIER_BLOCKED_TOOLS and not (tool_name in FILE_WRITE_TOOLS and _only_crew_dir(args)):
            return {"action": "block",
                    "message": "verifier has no write/send tools (%s) outside .crew/. Judge the artifact; never fix it; "
                               "the proof script is the one file you write, under .crew/." % tool_name}
        if tool_name == "terminal":
            cmd = str((args or {}).get("command") or "")
            if VERIFIER_WRITE_RX.search(cmd):
                return {"action": "block",
                        "message": "verifier terminal is read/run only; this command writes, moves, deletes, "
                                   "commits or sends. Run the card's proof with "
                                   "`python3 \"$HERMES_HOME/plugins/crew/scripts/crew_card.py\" verdict --card %s`." % card}
    return None


CREW_SLASH_RX = re.compile(r"^\s*/crew(?:\s+(.*))?\s*$", re.S)
# /crew-diagnose is a skill, not a plugin command: a plugin command's handler can only return text, and
# this pass has to run in the invoking session's own turn. The CLI and the gateway expand the skill
# slash; a one-shot `hermes chat -q "/crew-diagnose ..."` does not, so the hook below supplies the text.
CREW_DIAGNOSE_SLASH_RX = re.compile(r"^\s*/crew-diagnose(?:\s+(.*))?\s*$", re.S)
CREW_DIAGNOSE_INVOKED_RX = re.compile(r'\[IMPORTANT: The user has invoked the "crew-diagnose" skill\b')


def _strip_frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


def _expanded_ask(message):
    """The owner's ask out of a `/crew <ask>` the gateway or CLI already rewrote into the skill prompt."""
    try:
        from agent.skill_commands import extract_user_instruction_from_skill_message
        ask = extract_user_instruction_from_skill_message(message)
    except Exception:
        return ""
    return (ask or "").strip() if ask is not message else ""


def _record_brief(session_id, ask):
    """Keep the owner's ask for the card this intake opens: the card view draws it above the coordinator.
    A later /crew turn in the same session replaces it, and the card that opens consumes it."""
    if ask and session_id:
        _CREW_BRIEFS[str(session_id)] = ask
        if len(_CREW_BRIEFS) > _CREW_TURNS_MAX:
            _CREW_BRIEFS.pop(next(iter(_CREW_BRIEFS)), None)


def _intake_facts():
    """The facts the intake would otherwise dig for (2026-10-03: a /crew turn spent ~8 tool calls grepping
    crew_card.py for the budget and running `crew_card.py safety`): each writer role's default budget and the
    proof safety mode. Only what is true wherever the work lands - the target folder is the owner's answer."""
    tool = _card_tool()
    if tool is None:
        return ""
    try:
        budgets = ", ".join("%s %d" % (r, tool.default_budget(r)) for r in ("worker", "content"))
        mode = tool.crew_safety.permanent_mode()
    except Exception:  # noqa: BLE001 - no facts is the old behaviour, never a broken /crew turn
        return ""
    facts = ("<crew-facts>\nBudget defaults (tokens): %s. Write the role's number on the Budget line; the plugin "
             "raises it to the floor itself.\nProof safety mode: %s. Do not run `crew_card.py safety` or read "
             "crew's files for these values.\n</crew-facts>" % (budgets, mode))
    lessons = _lessons_block()
    return facts + "\n" + lessons if lessons else facts


# The invocation line. A plugin cannot write to the owner's terminal (a plugin slash command returns
# text, and /crew is the skill - a plugin command named /crew would shadow it), so the line rides the
# intake preload: the model opens its first reply with it. The version is read from plugin.yaml, so it
# follows the manifest with no second edit.
def _crew_version():
    """The plugin's own declared version (plugin.yaml), or "" when it cannot be read."""
    try:
        with open(os.path.join(HERE, "plugin.yaml"), encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("version:"):
                    return line.split(":", 1)[1].strip().strip("\"'")
    except OSError:
        pass
    return ""


def _crew_banner():
    """The HERMES.CREW line with its version, the first line of a /crew reply."""
    ver = _crew_version()
    return ("HERMES.CREW v%s" % ver) if ver else "HERMES.CREW"


def _banner_open():
    """The preload prefix that makes the intake open its reply with the line."""
    return ("Open your reply with this line, verbatim, as its first line, then carry on with the intake:\n\n"
            "%s\n\n" % _crew_banner())


def crew_intake_preload(user_message=None, session_id=None, turn_id=None, **_kw):
    """Record a /crew turn, open its intake window, and preload the crew skill when `/crew <ask>`
    reaches the model unexpanded.

    Crew starts only on /crew: a bare "crew ..." or any ordinary message returns None and records
    nothing. The interactive CLI and gateway expand the skill slash before the turn (the turn is
    recorded, the skill is already in the message, nothing is added); a one-shot
    `hermes chat -q "/crew ..."` hands the raw text to the model, so the skill text is supplied
    here and the model can answer from the text alone. No tool is called.
    """
    if not isinstance(user_message, str):
        return None
    report = WATCH_REPORT_RX.match(user_message)
    if report:
        _note_report(session_id, report.group(1))
        return None
    if _REPORT_WINDOWS.get(str(session_id or "")) and not CREW_SLASH_RX.match(user_message) \
            and not CREW_SKILL_INVOKED_RX.match(user_message.lstrip()[:200]):
        card = _take_report(session_id)
        if card and not _window_live(session_id):
            body = _crew_skill_text()
            if body is not None:
                _open_window(session_id)
                return {"context": (
                    "The owner is answering crew's report on card %s. If they ask for more work on it "
                    "(rework, redo, change), run the crew intake for a follow-up card now - the `crew` skill "
                    "is already loaded below; do not call skill_view. Make it a NEW card titled "
                    "\"rework %s: ...\" and put the prior card id in its Inputs so the writer starts from the "
                    "existing artifact. Otherwise just answer.\n\n<skill name=\"crew\">\n%s\n</skill>\n%s"
                    % (card, card, body, _intake_facts()))}
    if _window_live(session_id) and not CREW_SLASH_RX.match(user_message) \
            and not CREW_SKILL_INVOKED_RX.match(user_message.lstrip()[:200]):
        _open_window(session_id)    # the owner is still talking in a live intake: the window runs from their last turn
        return None
    if CREW_SKILL_INVOKED_RX.match(user_message.lstrip()[:200]):
        _record_crew_turn(session_id, turn_id)
        _open_window(session_id)
        _record_brief(session_id, _expanded_ask(user_message))
        facts = _intake_facts()
        return {"context": _banner_open() + facts}
    m = CREW_SLASH_RX.match(user_message)
    if not m:
        return None
    _record_crew_turn(session_id, turn_id)
    _open_window(session_id)
    _record_brief(session_id, (m.group(1) or "").strip())
    body = _crew_skill_text()
    if body is None:
        return None
    ask = (m.group(1) or "").strip()
    return {"context": _banner_open() + (
        "The `crew` skill is already loaded; its full text follows. Do not call skill_view or "
        "skills_list for it. The owner's ask is: \"%s\". Apply Rule 1 first: if the ask names no "
        "target and no measurable end state, ask through the clarify tool - one batch, no research "
        "call.\n\n"
        "<skill name=\"crew\">\n%s\n</skill>\n%s" % (ask, body, _intake_facts())
    )}


def crew_diagnose_preload(user_message=None, **_kw):
    """Supply the /crew-diagnose skill text when the raw slash reaches the model unexpanded.

    Nothing is added in an interactive CLI or gateway turn: the skill slash is expanded before the
    turn, so the skill body is already in the message. A one-shot `hermes chat -q "/crew-diagnose ..."`
    hands the raw text to the model, and the body is supplied here so the pass can still run. No tool
    is called here, and the hook changes nothing about the board.
    """
    if not isinstance(user_message, str):
        return None
    if CREW_DIAGNOSE_INVOKED_RX.match(user_message.lstrip()[:200]):
        return None
    m = CREW_DIAGNOSE_SLASH_RX.match(user_message)
    if not m:
        return None
    path = os.path.join(HERE, "skills", "crew-diagnose", "SKILL.md")
    try:
        with open(path, encoding="utf-8") as fh:
            body = _strip_frontmatter(fh.read())
    except OSError:
        return None
    state = (m.group(1) or "").strip() or "blocked"
    return {"context": (
        "The `crew-diagnose` skill is already loaded; its full text follows. Do not call skill_view or "
        "skills_list for it. The owner named: \"%s\". Run the reader once for that state and report "
        "every card in it with a resume path per card. This turn is read-only: no retry, no unblock, "
        "no stop, no dispatch, no comment, no card.\n\n"
        "<skill name=\"crew-diagnose\">\n%s\n</skill>" % (state, body)
    )}


# ---------------------------------------------------------------- the coordinator tick
# on_kanban_dispatch_tick fires in the DISPATCHER process (the gateway) once per tick, after the dispatch lock
# is released. It must stay fast: it only starts `crew_coordinator.py --once` detached when no pass is live
# AND the board has a crew event newer than the pass cursor (`has_work`, one read-only query in this process).
# A board with nothing new starts no process at all. Blocked cards are never re-assigned anywhere: the card stays with its writer profile
# and the coordinator acts on it in place (hermes_cli/plugins.py, hermes_cli/kanban_db.py _fire_dispatch_tick_hook).

_COORDINATOR_MOD = None


def _coordinator_tool():
    """scripts/crew_coordinator.py loaded once as a module: the gateway needs only lock_live and has_work from it, and
    runs every tick, so a subprocess per tick would bring back the cost of a process on an idle board.

    The script imports its siblings by bare name (crew_card, crew_handoff, crew_heal) and puts its own directory on
    sys.path to do it. Here it is loaded under a prefixed module name, and sys.path and sys.modules are restored
    afterwards, so nothing it pulled in stays importable by bare name inside the gateway; the module keeps its own
    references to what it imported. The decision pass itself always runs in its own process (crew_tick)."""
    global _COORDINATOR_MOD
    if _COORDINATOR_MOD is None:
        path = _script_path("crew_coordinator.py")
        if not path:
            return None
        saved_path, saved_modules = list(sys.path), set(sys.modules)
        try:
            spec = importlib.util.spec_from_file_location("crew_plugin_crew_coordinator", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        finally:
            sys.path[:] = saved_path
            scripts = os.path.dirname(path) + os.sep
            for name in set(sys.modules) - saved_modules:
                if str(getattr(sys.modules[name], "__file__", "") or "").startswith(scripts):
                    sys.modules.pop(name, None)
        _COORDINATOR_MOD = mod
    return _COORDINATOR_MOD


def crew_tick(board=None, dry_run=False, outcome=None, **_kw):
    """Start one detached coordinator pass for this board unless one is already live."""
    if dry_run or outcome == "skipped_locked":
        return None
    try:
        tool = _coordinator_tool()
        if tool is None or tool.lock_live(board) or not tool.has_work(board):
            return None
        log = os.path.join(HOME, "crew", "coordinator.log")
        os.makedirs(os.path.dirname(log), exist_ok=True)
        args = [sys.executable, tool.__file__, "--once"] + (["--board", board] if board else [])
        with open(log, "ab") as fh:
            subprocess.Popen(args, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             start_new_session=True, cwd=os.path.dirname(tool.__file__),
                             env=tool.crew_safety.proof_env())      # the gateway's secrets stay behind
    except Exception:  # noqa: BLE001 - a hook on the dispatcher must never break the tick
        pass
    return None


def crew_open_hook(tool_name=None, args=None, result=None, **kwargs):
    """post_tool_call observer: the first card opened out of an intake window closes that window, so
    a later ordinary turn in the same session is refused again. One /crew, one card. For the intake's
    kanban_create it also records what `crew_card.py open` records (see _finish_created_card)."""
    if tool_name == "kanban_create":
        card_id = _created_card_id(result)
        if card_id and not os.environ.get("HERMES_KANBAN_TASK"):
            try:
                _finish_created_card(card_id, kwargs.get("session_id"),
                                     str((args or {}).get("title") or "").strip())
            except Exception:  # noqa: BLE001 - bookkeeping never fails the intake turn
                pass
        return None
    if tool_name != "terminal":
        return None
    cmd = str((args or {}).get("command") or "")
    if not CARD_OPEN_RX.search(cmd) or PROBE_TITLE_RX.search(cmd):
        return None
    parsed = result
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except (TypeError, ValueError):
            parsed = None
    if isinstance(parsed, dict) and parsed.get("error"):
        return None
    _close_window(kwargs.get("session_id"))
    return None


def register(ctx):
    skill_path = os.path.join(HERE, "skills", "crew-verifier", "SKILL.md")
    try:
        ctx.register_skill(
            "crew-verifier",
            skill_path,
            description="Verification pass for a crew card. Runs the proof itself, never trusts the writer.",
            frontmatter={"version": "0.2.0"},
        )
    except Exception:
        pass
    # Every option as its own command: the option is in the name, so /help and the platform menus
    # list the crew's options directly instead of hiding them behind one command's sub-arguments.
    for name, action, hint, desc in COMMANDS:
        ctx.register_command(
            name,
            handler=_option_handler(action),
            description=desc,
            args_hint=hint,
        )
    ctx.register_hook("pre_tool_call", crew_tool_guard)
    ctx.register_hook("post_api_request", crew_budget_account)
    ctx.register_hook("api_request_error", crew_quota_reroute)
    ctx.register_hook("pre_llm_call", crew_intake_preload)
    ctx.register_hook("pre_llm_call", crew_diagnose_preload)
    ctx.register_hook("pre_llm_call", crew_handoff_hook)
    ctx.register_hook("on_kanban_dispatch_tick", crew_tick)
    ctx.register_hook("post_tool_call", crew_open_hook)
    ctx.register_hook("post_tool_call", crew_thrash_hook)
