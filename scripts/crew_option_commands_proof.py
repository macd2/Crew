#!/usr/bin/env python3
"""Proof that every crew option is a slash command of its own, in the registry Hermes reads.

The option is in the command name, so the command list is the option list:

  1. the plugin source carries one row per option and registers a command for each row
  2. loading the installed plugin and registering it against a stub host yields exactly the option
     commands and nothing else, each with a description, none of them the commands that were removed
     (/crew-run, /crew-verify, /crew-roles, /crew-install, /crew-ops and the passes the coordinator loop
     replaced) and none named `crew` (the intake stays a skill, so `/crew <ask>` still reaches the model)
  3. every option handler runs and returns text - /crew-graph in its plain mode and in each of its
     two flag modes (--watch, --html) - and the whole-board stop pass is exercised with --dry-run
     so this proof mutates nothing
  4. /crew-status lists exactly the crew cards in flight of the board it reads, each with its id
  5. the live Hermes registry resolves every one of them to the crew plugin, and the manifest
     declares every hook the plugin actually registers

Run:  python3 crew_option_commands_proof.py
Exit: 0 when every check passes, 1 otherwise.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402 - the owner profile, the base home and the package checkout
PKG = crew_card.package_dir() or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE = os.environ.get("CREW_PROFILE") or crew_card.owner_home()
HERMES_SRC = os.environ.get("HERMES_SRC") or os.path.expanduser("~/.hermes/hermes-agent")
HERMES_PY = os.environ.get("HERMES_PY", os.path.join(HERMES_SRC, ".venv", "bin", "python"))
PLUGIN = os.path.join(PROFILE, "plugins", "crew", "__init__.py")
# The plugin resolves its scripts from HERMES_HOME at import, and the gateway always runs a profile with it
# set; the proof does the same, or it would run whatever crew copy the base home holds.
os.environ.setdefault("HERMES_HOME", PROFILE)
MANIFEST = os.path.join(PROFILE, "plugins", "crew", "plugin.yaml")
OPTIONS = ["status", "graph", "stop"]
# The commands the owner surface no longer has. None may be registered, and the usage text names none.
REMOVED = ["crew-run", "crew-verify", "crew-roles", "crew-install", "crew-ops", "crew-unblock", "crew-unstale",
           "crew-heal", "crew-triage"]
# One representative invocation per option, so no handler is left unexercised. The whole-board
# pass is dry-run: this proof reads and reports - a dry run is the only safe way to invoke a stop,
# which would otherwise archive real cards.
CALLS = {
    "status": "", "graph": "latest",
    "stop": "--dry-run",
}
# graph merged three options into one command with two flag modes: both modes are exercised here, so
# the merge cannot quietly drop one of them. --watch 1 is one second, well under the proof's ceiling.
GRAPH_MODES = ["latest --watch 1", "latest --html"]
FAILS = []


def check(name, ok, detail=""):
    print("%-62s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + str(detail)[:90]) if detail else ""))
    if not ok:
        FAILS.append(name)
    return ok


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


class Host:
    """A stand-in for the plugin host's context: records what register() asks for."""

    def __init__(self):
        self.commands = {}
        self.hooks = []

    def register_command(self, name, handler, description="", args_hint="", **kw):
        self.commands[name] = {"handler": handler, "description": description, "args_hint": args_hint}

    def register_hook(self, name, fn):
        self.hooks.append(name)

    def register_skill(self, *a, **kw):
        pass


def load(path):
    spec = importlib.util.spec_from_file_location("crew_cmd_proof_plugin", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    src = read(PLUGIN)
    check("the installed plugin is the package's own copy",
          src == read(os.path.join(PKG, "__init__.py")), PLUGIN)

    # 1 - one row per option, and the rows are what gets registered
    rows = {m.group(2): m.group(1) for m in
            re.finditer(r'\("(crew-[a-z]+)",\s*"([a-z]+)"', src)}
    check("the source carries a command row per option",
          all(o in rows for o in OPTIONS), "%d row(s)" % len(rows))
    check("register() loops those rows instead of hand-listing commands",
          bool(re.search(r"for name, action, hint, desc in COMMANDS:", src)))

    mod = load(PLUGIN)
    host = Host()
    mod.register(host)

    # 2 - the option set is the registered set
    option_cmds = set(host.commands)
    expected = {rows[o] for o in OPTIONS if o in rows}
    check("every option is registered as its own command", option_cmds == expected,
          "missing=%s extra=%s" % (sorted(expected - option_cmds), sorted(option_cmds - expected)))
    check("no plugin command shadows /crew (the intake stays the skill)",
          "crew" not in host.commands and not re.search(r'register_command\(\s*"crew"', src))
    check("none of the removed commands is registered", not [c for c in REMOVED if c in host.commands],
          sorted(c for c in REMOVED if c in host.commands))
    check("the usage text names none of the removed commands",
          not [c for c in REMOVED if "/" + c in mod.USAGE], mod.USAGE[:70])
    check("every command carries a description",
          all((host.commands[c]["description"] or "").strip() for c in host.commands))
    check("the manifest declares every hook the plugin registers",
          set(host.hooks) <= set(re.findall(r"^\s*-\s*([a-z_]+)\s*$", read(MANIFEST), re.M)),
          "hooks=%s" % sorted(set(host.hooks)))

    # 3 - every handler runs (the stop pass dry-run, so nothing is mutated)
    for opt in OPTIONS:
        cmd = rows.get(opt)
        if not cmd or opt not in CALLS:
            continue
        try:
            out = host.commands[cmd]["handler"](CALLS[opt])
        except Exception as exc:  # noqa: BLE001
            check("/%s runs" % cmd, False, "%s: %s" % (type(exc).__name__, exc))
            continue
        text = "" if out is None else str(out)
        ok = bool(text.strip())
        if opt == "stop":
            ok = ok and "dry run" in text.lower()      # the pass prints its mode
        check("/%s runs and answers" % cmd, ok, text.strip().splitlines()[0][:70] if text.strip() else "")

    # 3b - the merged graph modes: --watch N and --html [PATH] answer through the one command
    for mode in GRAPH_MODES:
        arg = mode
        tmp = None
        if "--html" in mode:
            import tempfile
            tmp = tempfile.mkdtemp(prefix="crew-graph-proof-")
            arg = "%s %s" % (mode, os.path.join(tmp, "card.graph.html"))
        try:
            text = str(host.commands[rows["graph"]]["handler"](arg) or "")
        except Exception as exc:  # noqa: BLE001
            check("/crew-graph %s answers" % mode, False, "%s: %s" % (type(exc).__name__, exc))
            continue
        head = text.strip().splitlines()[0][:70] if text.strip() else ""
        wrote = (not tmp) or os.path.exists(os.path.join(tmp, "card.graph.html"))
        check("/crew-graph %s answers" % mode, bool(text.strip()) and wrote, head)
        if tmp:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    # 4 - /crew-status is the crew cards in flight of the board it reads
    try:
        import sqlite3
        board = mod._tasks_db()
        conn = sqlite3.connect("file:%s?mode=ro" % board, uri=True)
        expect = [r[0] for r in conn.execute(
            "select id, body from tasks where status in ('ready','running','blocked','review')") if
            re.search(r"^\s*(Coordinator|Role):", r[1] or "", re.M | re.I)]
        conn.close()
        text = str(host.commands["crew-status"]["handler"]("") or "")
        shown = re.findall(r"ID: (t_[0-9a-f]+)", text)
        check("/crew-status lists the crew cards in flight, newest %d" % min(len(expect), 8),
              len(shown) == min(len(expect), 8) and set(shown) <= set(expect),
              "sql=%d shown=%d" % (len(expect), len(shown)))
    except Exception as exc:  # noqa: BLE001
        check("/crew-status lists the crew cards in flight", False, "%s: %s" % (type(exc).__name__, exc))

    # 5 - the live registry Hermes itself reads
    names = [rows[o] for o in OPTIONS if rows.get(o)]
    probe = (
        "import json,sys\n"
        "from hermes_cli.plugins import get_plugin_commands\n"
        "c=get_plugin_commands()\n"
        "print(json.dumps({n:(c.get(n) or {}).get('plugin') for n in %r}))\n" % names)
    env = dict(os.environ, HERMES_HOME=PROFILE)
    try:
        r = subprocess.run([HERMES_PY, "-c", probe], capture_output=True, text=True, timeout=240,
                           cwd=HERMES_SRC, env=env)
    except Exception as exc:  # noqa: BLE001
        r = None
        check("the live registry was queried", False, "%s: %s" % (type(exc).__name__, exc))
    if r is not None:
        try:
            live = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            live = {}
            check("the live registry answered", False, (r.stdout + r.stderr)[-120:])
        if live:
            check("every crew command resolves in the live Hermes registry",
                  all(v == "crew" for v in live.values()),
                  "resolved %d/%d" % (sum(1 for v in live.values() if v == "crew"), len(names)))

    if FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("PROOF OK: every crew option is its own slash command, answers on its own, keeps /crew "
          "for the intake, and resolves in the registry Hermes reads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
