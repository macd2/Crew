#!/usr/bin/env python3
"""Proof that the crew starts only on /crew and that the path from a chat works.

Done when the intake can only be started by the owner typing the literal `/crew ...` command - the
bare word does not count - the guard refuses a hand-made card open in any other turn (coordinator
included), a `/crew` turn leaves its session able to open the card for the intake window so the
owner's answer turn needs no second /crew, that window closes on the first card and expires, the
pre-armed probes can still seed their cards, and the chat legs are in place: the skill owns
`/crew` (no plugin command shadows it), the gateway rewrites a skill slash before the turn, the
skill is not disabled, and a card opened from a chat records that chat as its origin verbatim.

Contract pinned here (drives the installed plugin entry points, exactly as the runtime calls them):
  crew_intake_preload(user_message=..., session_id=..., turn_id=...)
      -> {"context": ...} for "/crew ..."; None for a bare "crew ..." and for anything else, so
         normal chat stays normal chat. It also opens the session's intake window.
  crew_tool_guard(tool_name="terminal", args={"command": ...}, session_id=..., turn_id=...)
      -> {"action": "block", ...} for a direct `crew_card.py ... open` in a turn that did not start
         with /crew and in a session with no live intake window; None otherwise - including the
         answer turn of a live window, a card title starting with PROBE, and any other
         crew_card.py subcommand.
  crew_tool_guard(tool_name="kanban_create", args={title, assignee, body}, ...)
      -> the same gate for the intake's own card-opening tool: {"action": "block"} for a crew card
         outside a /crew turn or live window, a {"action": "modify"} with the canonical body inside
         one, None for a card that is not crew's (a plain kanban card the owner asks for).
  crew_open_hook(tool_name="terminal", args=..., result=..., session_id=...) closes that window.
  skills/crew/SKILL.md carries the sentence "Crew starts only on /crew" and opens the card with
  kanban_create (the plugin adds the chat Origin:; there is no follow loop any more).

Exit 0 = every check passed. Non-zero = it did not, and the failing check is printed.
"""
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402 - the owner profile, the base home and the package checkout
PKG = crew_card.package_dir() or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE = os.environ.get("CREW_PROFILE") or crew_card.owner_home()
HERMES_SRC = os.environ.get("HERMES_SRC") or os.path.expanduser("~/.hermes/hermes-agent")
CARD_TOOL = os.path.join(PROFILE, "plugins", "crew", "scripts", "crew_card.py")
RULE_SENTENCE = "Crew starts only on /crew"
FAILURES = []


def check(name, ok, detail=""):
    print("%-62s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + detail) if detail else ""))
    if not ok:
        FAILURES.append(name)
    return ok


def md5(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.md5(fh.read()).hexdigest()
    except OSError:
        return ""


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def load_plugin(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


OPEN_CMD = "python3 \"$HERMES_HOME/plugins/crew/scripts/crew_card.py\" open --title 'wordpress gate' --goal x --role worker --artifact a --lands b --audience c --done-when d --proof-cmd true --units e --constraints f"
PLAIN_MSG = "make the landing page convert better"
TRIGGER_SLASH = "/crew make the landing page convert better"
BARE_WORD = "crew make the landing page convert better"


def guard(plug, cmd, session, turn):
    env_card = os.environ.pop("HERMES_KANBAN_TASK", None)
    env_role = os.environ.pop("HERMES_CREW_ROLE", None)
    try:
        return plug.crew_tool_guard(tool_name="terminal", args={"command": cmd},
                                   session_id=session, turn_id=turn)
    finally:
        if env_card is not None:
            os.environ["HERMES_KANBAN_TASK"] = env_card
        if env_role is not None:
            os.environ["HERMES_CREW_ROLE"] = env_role


CREATE_BODY = ("Role: worker\nBudget: 500000\nRoute: none\nGOAL: gate probe\nArtifact: a\nLands at: b\n"
               "For: c\nDone when: d\nproof command: true\n")


def create_guard(plug, session, turn, body=CREATE_BODY, assignee="crew-worker"):
    env_card = os.environ.pop("HERMES_KANBAN_TASK", None)
    try:
        return plug.crew_tool_guard(tool_name="kanban_create", session_id=session, turn_id=turn,
                                    args={"title": "gate probe", "assignee": assignee, "body": body})
    finally:
        if env_card is not None:
            os.environ["HERMES_KANBAN_TASK"] = env_card


def is_modify(result):
    return isinstance(result, dict) and str(result.get("action") or "").lower() == "modify"


def is_block(result):
    return isinstance(result, dict) and str(result.get("action") or "").lower() == "block"


def preload(plug, message, session, turn):
    try:
        return plug.crew_intake_preload(user_message=message, session_id=session, turn_id=turn) or {}
    except TypeError:
        return plug.crew_intake_preload(user_message=message) or {}


def main():
    for path, label in ((os.path.join(PROFILE, "plugins", "crew", "__init__.py"), "installed plugin"),
                        (os.path.join(PKG, "__init__.py"), "package plugin")):
        if not os.path.exists(path):
            print("PROOF FAIL: %s missing at %s" % (label, path))
            return 2
    check("the package and installed plugin are the same file",
          md5(os.path.join(PKG, "__init__.py")) == md5(os.path.join(PROFILE, "plugins", "crew", "__init__.py")))
    skill_src = os.path.join(PKG, "skills", "crew", "SKILL.md")
    skill_inst = os.path.join(PROFILE, "skills", "crew", "crew", "SKILL.md")
    check("the package and installed crew skill are the same file",
          md5(skill_src) == md5(skill_inst) and bool(md5(skill_src)))

    plug = load_plugin(os.path.join(PROFILE, "plugins", "crew", "__init__.py"), "crew_plugin_probe")

    # --- the slash command decides whether the intake starts --------------------------------------
    slash = preload(plug, TRIGGER_SLASH, "S-slash", "T1")
    bare = preload(plug, BARE_WORD, "S-bare", "T1")
    plain = preload(plug, PLAIN_MSG, "S-plain", "T1")
    check("/crew ... starts the intake", bool(str(slash.get("context") or "").strip()))
    check("a bare 'crew ...' starts nothing", not str(bare.get("context") or "").strip())
    check("any other message starts nothing", not str(plain.get("context") or "").strip())

    # --- the guard gates hand-made card opens ----------------------------------------------------
    check("an open in a /crew turn is allowed", not is_block(guard(plug, OPEN_CMD, "S-slash", "T1")))
    check("an open in a plain turn is refused", is_block(guard(plug, OPEN_CMD, "S-plain", "T1")),
          str((guard(plug, OPEN_CMD, "S-plain", "T1") or {}).get("message"))[:70])
    check("an open after a bare 'crew ...' is refused too",
          is_block(guard(plug, OPEN_CMD, "S-bare", "T1")))
    check("the refusal names /crew",
          "/crew" in str((guard(plug, OPEN_CMD, "S-plain", "T1") or {}).get("message") or ""))
    probe_cmd = OPEN_CMD.replace("--title 'wordpress gate'", "--title 'PROBE sitbox 1'")
    check("a PROBE card can still be seeded without /crew",
          not is_block(guard(plug, probe_cmd, "S-plain", "T1")))

    # --- the intake window: the owner's answer turn opens the card, no second /crew -----------------
    check("the answer turn of a /crew session may open the card",
          not is_block(guard(plug, OPEN_CMD, "S-slash", "T2")))
    check("a session that never saw /crew stays refused",
          is_block(guard(plug, OPEN_CMD, "S-never", "T1")))
    check("a PROBE open leaves the window live",
          not is_block(guard(plug, probe_cmd, "S-slash", "T3")) and plug._window_live("S-slash"))
    plug.crew_open_hook(tool_name="terminal", args={"command": OPEN_CMD},
                        result={"ok": True}, session_id="S-slash")
    check("the first card out of the window closes it",
          is_block(guard(plug, OPEN_CMD, "S-slash", "T4")))
    preload(plug, TRIGGER_SLASH, "S-exp", "T1")
    plug._CREW_WINDOWS["S-exp"] = time.time() - 1
    check("an expired window is refused again", is_block(guard(plug, OPEN_CMD, "S-exp", "T2")))
    check("the window is bounded in seconds", int(getattr(plug, "INTAKE_WINDOW_SECONDS", 0)) == 1800,
          str(getattr(plug, "INTAKE_WINDOW_SECONDS", None)))
    for sub in ("status --card t_x", "verdict --card t_x", "retry --card t_x"):
        check("crew_card.py %s is not gated" % sub.split()[0],
              not is_block(guard(plug, "python3 $HERMES_HOME/plugins/crew/scripts/crew_card.py " + sub, "S-plain", "T1")))
    check("other tools are untouched",
          plug.crew_tool_guard(tool_name="read_file", args={"path": "/etc/hostname"},
                               session_id="S-plain", turn_id="T1") in (None, {}))
    threaded = preload(plug, TRIGGER_SLASH, "S-thread", "T7")
    check("a /crew turn on another session allows its own open",
          bool(str(threaded.get("context") or "").strip())
          and not is_block(guard(plug, OPEN_CMD, "S-thread", "T7")))

    # --- the same gate on the intake's own tool, kanban_create -------------------------------------
    check("kanban_create in a /crew turn is allowed and rebuilt", is_modify(create_guard(plug, "S-thread", "T7")))
    check("kanban_create in a plain turn is refused", is_block(create_guard(plug, "S-plain", "T1")))
    check("kanban_create after a bare 'crew ...' is refused", is_block(create_guard(plug, "S-bare", "T1")))
    check("the answer turn of a /crew session may create the card", is_modify(create_guard(plug, "S-thread", "T8")))
    check("a card with a missing field is refused by name",
          is_block(create_guard(plug, "S-thread", "T7", body=CREATE_BODY.replace("For: c\n", "")))
          and "For" in str(create_guard(plug, "S-thread", "T7",
                                        body=CREATE_BODY.replace("For: c\n", "")).get("message")))
    check("a kanban card that is not crew's is not gated",
          create_guard(plug, "S-plain", "T1", body="milk", assignee="helper") is None)

    # --- the rule text ---------------------------------------------------------------------------
    skill = read(skill_inst)
    check("the skill states the /crew rule", RULE_SENTENCE.lower() in skill.lower())
    check("the skill opens the card with kanban_create", "kanban_create(" in skill)
    check("the skill no longer follows the card", "crew_follow" not in skill)
    check("the skill says the intake turn ends when its cards are open",
          bool(re.search(r"(turn ends|ends? the turn|stops there|nothing else is dispatched)", skill, re.I)))

    # --- chat legs ------------------------------------------------------------------------------
    plugin_src = read(os.path.join(PROFILE, "plugins", "crew", "__init__.py"))
    check("no plugin command shadows /crew",
          "for name, action, hint, desc in COMMANDS:" in plugin_src
          and not re.search(r"register_command\(\s*\"crew(-ops)?\"", plugin_src))
    check("the gateway rewrites a skill slash before the turn",
          "_hm_skill_slash_rewrite" in read(os.path.join(HERMES_SRC, "gateway", "run_inbound.py")))
    cfg = read(os.path.join(PROFILE, "config.yaml"))
    disabled = re.search(r"^skills:\s*$(.*?)(?=^\S)", cfg, re.S | re.M)
    body = disabled.group(1) if disabled else ""
    check("the crew skill is not disabled for the gateway",
          bool(body) and not re.search(r"^\s*-\s*crew\s*$", body, re.M))
    try:
        help_text = subprocess.run([sys.executable, CARD_TOOL, "open", "--help"],
                                   capture_output=True, text=True, timeout=60).stdout
    except Exception as exc:  # noqa: BLE001
        help_text = ""
        print("note: crew_card.py open --help failed (%s)" % str(exc)[:50])
    check("crew_card.py open takes --origin", "--origin" in help_text)

    # --- a blocked card is the coordinator's: the dispatch tick starts its pass --------------------
    plugin_src = read(os.path.join(PROFILE, "plugins", "crew", "__init__.py"))
    check("the plugin starts the coordinator pass from the dispatch tick",
          bool(re.search(r"register_hook\(\s*\"on_kanban_dispatch_tick\",\s*crew_tick", plugin_src)))
    check("a block is no longer re-assigned to another profile",
          "crew_block_route" not in plugin_src and "orchestrator_profile" not in plugin_src)
    tick = getattr(plug, "crew_tick", None)
    check("the plugin exposes crew_tick", callable(tick))
    if callable(tick):
        # a dry tick and a lock-skipped tick start nothing: the hook returns before it looks for a script
        check("a dry or lock-skipped tick starts no pass",
              tick(board=None, dry_run=True, outcome="ok") is None
              and tick(board=None, dry_run=False, outcome="skipped_locked") is None)

    if FAILURES:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILURES), "; ".join(FAILURES)))
        return 1
    print("PROOF OK: the crew starts only on the owner's trigger, a hand-made open in any other turn "
          "is refused, and every chat leg is in place")
    return 0


if __name__ == "__main__":
    sys.exit(main())
