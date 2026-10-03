#!/usr/bin/env python3
"""Proof that /crew-diagnose is a skill turn, not a plugin command, and that its reader is read-only.

The pass has to run in the invoking session's own turn, which a plugin slash command cannot do: its
handler returns text and the turn ends. So the pins here are:

  1. the package ships the skill, its frontmatter names it `crew-diagnose`, and every installed profile
     carries the same bytes (the slash only resolves where the skill file is)
  2. the slash is NOT a plugin command (it would shadow the skill and the turn would never happen),
     and the live skill registry of the profile does resolve `/crew-diagnose`
  3. the pre-llm hook supplies the skill text for a raw one-shot slash, returns nothing for a bare
     word, for the already-expanded skill turn and for the /crew intake
  4. the reader answers from a board: it lists a seeded card with its id and its recorded reason,
     exits 0 on an empty state, 1 on an unknown state, and its SQL is read-only
  5. the skill body carries the rules that make the pass safe: read-only, and the three acting
     passes it must not run

Run:  python3 crew_diagnose_proof.py
Exit: 0 when every check passes, 1 otherwise.
"""
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402 - the owner profile, the base home and the package checkout
PKG = crew_card.package_dir() or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE = os.environ.get("CREW_PROFILE") or crew_card.owner_home()
PROFILES_ROOT = os.environ.get("CREW_PROFILES_ROOT") or os.path.join(crew_card.base_home(), "profiles")
HERMES_SRC = os.environ.get("HERMES_SRC") or os.path.expanduser("~/.hermes/hermes-agent")
HERMES_PY = os.environ.get("HERMES_PY", os.path.join(HERMES_SRC, ".venv", "bin", "python"))
SKILL = "crew-diagnose"
COMMAND = "/crew-diagnose"
READER = os.path.join(PKG, "scripts", "crew_diagnose.py")
FAILS = []


def check(name, ok, detail=""):
    print("%-64s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + str(detail)[:88]) if detail else ""))
    if not ok:
        FAILS.append(name)
    return ok


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Host:
    def __init__(self):
        self.commands, self.skills, self.hooks = {}, [], []

    def register_command(self, name, handler, description="", args_hint="", **kw):
        self.commands[name] = handler

    def register_skill(self, name, path, description="", frontmatter=None, **kw):
        self.skills.append(name)

    def register_hook(self, name, fn):
        self.hooks.append(name)


def seed_board(path):
    """A minimal board with the columns the reader reads: one blocked card with a recorded reason."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        create table tasks (id text, title text, status text, assignee text, block_kind text,
                            created_at integer, result text, last_failure_error text,
                            consecutive_failures integer);
        create table task_runs (id integer, task_id text, summary text, error text);
        create table task_events (id integer, task_id text, kind text, payload text, created_at integer);
    """)
    conn.execute("insert into tasks values ('t_seed01', 'publish the branch', 'blocked', 'crew-worker',"
                 " 'needs_input', 1000, null, null, 0)")
    conn.execute("insert into task_events values (1, 't_seed01', 'blocked', ?, 1000)",
                 (json.dumps({"reason": "waiting on the owner's publish token", "kind": "needs_input"}),))
    conn.commit()
    conn.close()


def main():
    src = read(os.path.join(PKG, "skills", SKILL, "SKILL.md"))

    # 1 - the skill ships, is named right, and is installed with the same bytes
    check("the package ships the skill", bool(src), os.path.join("skills", SKILL, "SKILL.md"))
    front = re.search(r"^---\s*\nname:\s*([^\n]+)", src or "", re.M)
    check("its frontmatter names it", bool(front) and front.group(1).strip() == SKILL,
          front.group(1).strip() if front else "")
    installed = [d for d in sorted(os.listdir(PROFILES_ROOT))
                 if os.path.isdir(os.path.join(PROFILES_ROOT, d, "plugins", "crew"))]
    missing, drifted = [], []
    for profile in installed:
        path = os.path.join(PROFILES_ROOT, profile, "skills", "crew", SKILL, "SKILL.md")
        if not os.path.exists(path):
            missing.append(profile)
        elif read(path) != src:
            drifted.append(profile)
    check("every installed profile carries the same skill", not missing and not drifted,
          "profiles=%d missing=%s drifted=%s" % (len(installed), missing, drifted))

    # 2 - it is a skill, never a plugin command (a command would shadow it and end the turn)
    mod = load(os.path.join(PROFILE, "plugins", "crew", "__init__.py"), "crew_diagnose_proof_plugin")
    host = Host()
    mod.register(host)
    check("the plugin registers no command of that name",
          SKILL not in host.commands, "commands=%d" % len(host.commands))
    probe = ("import json\n"
             "from agent.skill_commands import scan_skill_commands\n"
             "print(json.dumps(sorted(scan_skill_commands())))\n")
    env = dict(os.environ, HERMES_HOME=PROFILE)
    try:
        r = subprocess.run([HERMES_PY, "-c", probe], capture_output=True, text=True, timeout=300,
                           cwd=HERMES_SRC, env=env)
        names = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception as exc:  # noqa: BLE001
        names = []
        check("the live skill registry answered", False, "%s: %s" % (type(exc).__name__, exc))
    check("the live skill registry resolves the slash", COMMAND in names,
          "%d skill command(s)" % len(names))
    check("it does not take the /crew intake's slash", "/crew" in names)

    # 3 - the hook: the raw one-shot slash, and only that
    asked = mod.crew_diagnose_preload(user_message="%s todo" % COMMAND) or {}
    check("the hook supplies the skill text for a raw slash",
          "<skill name=\"%s\">" % SKILL in str(asked.get("context") or ""))
    check("the hook carries the state the owner named", "todo" in str(asked.get("context") or ""))
    check("the hook answers the bare word with nothing",
          mod.crew_diagnose_preload(user_message="stuck cards please") is None)
    check("the hook leaves an expanded skill turn alone",
          mod.crew_diagnose_preload(user_message='[IMPORTANT: The user has invoked the "%s" skill, '
                                              'loading it for this turn.]' % SKILL) is None)
    check("the hook leaves the /crew intake alone",
          mod.crew_diagnose_preload(user_message="/crew publish the branch") is None)
    check("plain chat is untouched",
          mod.crew_diagnose_preload(user_message="is anything stuck?") is None)

    # 4 - the reader, on a board of its own
    tmp = tempfile.mkdtemp(prefix="crew-diagnose-proof-")
    try:
        db = os.path.join(tmp, "kanban.db")
        seed_board(db)
        env = dict(os.environ, HERMES_KANBAN_DB=db, HERMES_HOME=tmp)
        r = subprocess.run([sys.executable, READER, "--state", "blocked", "--json"],
                           capture_output=True, text=True, timeout=120, env=env)
        try:
            data = json.loads(r.stdout)
        except ValueError:
            data = {}
        cards = data.get("cards") or []
        check("the reader lists the seeded card", len(cards) == 1 and cards[0]["id"] == "t_seed01",
              "exit=%d cards=%d" % (r.returncode, len(cards)))
        check("it reports the reason recorded when the card was blocked",
              bool(cards) and "publish token" in cards[0]["reason"],
              (cards[0]["reason"][:60] if cards else ""))
        check("it reports the block kind", bool(cards) and cards[0]["kind"] == "needs_input")
        empty = subprocess.run([sys.executable, READER, "--state", "running"],
                               capture_output=True, text=True, timeout=120, env=env)
        check("an empty state is a result, not an error",
              empty.returncode == 0 and "0 card(s)" in empty.stdout, empty.stdout.strip()[:50])
        bad = subprocess.run([sys.executable, READER, "--state", "nope"],
                             capture_output=True, text=True, timeout=120, env=env)
        check("an unknown state is refused", bad.returncode == 1 and "blocked|" in bad.stdout,
              bad.stdout.strip()[:50])
        live = subprocess.run([sys.executable, READER], capture_output=True, text=True, timeout=180,
                              env=dict(os.environ, HERMES_HOME=PROFILE))
        check("the live board answers the default state",
              live.returncode == 0 and re.match(r"^diagnose: \d+ card\(s\) in state blocked$",
                                                live.stdout.strip().splitlines()[0] or ""),
              live.stdout.strip().splitlines()[0] if live.stdout.strip() else "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    reader_src = read(READER)
    check("the reader opens the board read-only", "mode=ro" in reader_src)
    check("the reader's SQL holds no write statement",
          bool(reader_src) and not re.search(
              r"\b(insert\s+into|update\s+\w+\s+set|delete\s+from|drop\s+\w+|alter\s+\w+)\b",
              reader_src, re.I))

    # 5 - the skill body's rules
    check("the skill says it is read-only", "Read-only" in src)
    check("the skill names the acting passes it must not run",
          all(word in src for word in ("/crew-stop", "crew_coordinator.py")))
    check("the skill names the reader it runs",
          "$HERMES_HOME/plugins/crew/scripts/crew_diagnose.py" in src)
    check("the skill names every state the reader takes",
          all(state in src for state in ("blocked", "triage", "todo", "ready", "running", "done",
                                         "archived")))

    if FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("PROOF OK: /crew-diagnose is a skill turn that reads the board and plans, and touches nothing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
