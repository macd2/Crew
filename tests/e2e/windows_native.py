#!/usr/bin/env python3
"""End-to-end check of crew on a real native Windows Hermes, run by .github/workflows/tests.yml (job e2e-windows).

It needs what a Desktop "This device" user has: Hermes installed by its own scripts/install.ps1 under
%LOCALAPPDATA%\\hermes, a profile, and crew installed into that profile with install.py. It then walks the paths
that used to break on a Windows layout, one STEP each, and exits 1 if any step fails (all steps run, so one CI
round shows every break):

  layout          the files a native install leaves (hermes.exe, hermes-agent\\venv\\Scripts\\python.exe), and the
                  crew copy in the profile being the version under test
  hermes-python   crew_card.hermes_python()/venv_python()/hermes_root()/default_home() on that layout
  guard           crew_safety loads Hermes's tools.approval_detection from a bare interpreter (Hermes source and
                  Lib\\site-packages found), refuses `rm -rf /`, flags `rm -rf build` in safe mode
  proof           a proof runs in Git Bash and its exit code comes back; the guard blocks a dangerous one; the
                  interpreter crew writes into proof commands (crew_card.PYTHON) works inside Git Bash
  reexec          a crew script started with a bare python is re-run under the Hermes venv python and its exit
                  status comes back (Windows has no exec: os.execv would return 0 at once)
  cli             the crew_card.py command line (proof-check) answers through that same re-exec
  board           a card made with the real `hermes kanban create` lands in <home>\\kanban.db, crew_card.kanban_db()
                  finds it, and crew_stop.py --dry-run reads it
  dashboard       (under the Hermes venv python) the dashboard plugin api renders /board.json and the card page for
                  that board, and crew_graph_serve.py serves /board.json over real HTTP
  agent-commands  the exact commands crew's skills give an agent, run through Hermes's own terminal mechanism
                  (tools.environments.local.LocalEnvironment: Git Bash on Windows) with no python3 on PATH
  card-run        (only with --only card-run, push builds with a model key) ONE real crew card, worked by a real
                  model through `hermes kanban dispatch`, ending done with a PASS verdict; skips when no key is set
  stop            crew_proc.alive/cmdline_of/terminate_tree and crew_stop.kill_run on a real spawned process

Run:  python tests/e2e/windows_native.py --profile e2e [--only STEP]
card-run settings (one place, the job env in tests.yml): CREW_E2E_PROVIDER, CREW_E2E_MODEL, CREW_E2E_BASE_URL,
CREW_E2E_KEY_ENV (the env var name the provider reads its key from) and CREW_E2E_KEY (the key itself: env only,
never printed, never written to a file or log). A box whose worker profile is already logged in (a subscription
login, no key) sets CREW_E2E_PROFILE_AUTH=1 instead of CREW_E2E_KEY: the card runs on the profile's own credentials.
The plugin copy under test is the one in the profile (what Hermes loads), not the checkout.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.dirname(os.path.dirname(HERE))
IS_WINDOWS = os.name == "nt"


def say(msg):
    print(msg, flush=True)


def norm(path):
    return os.path.normcase(os.path.realpath(path))


def check(cond, what):
    if not cond:
        raise AssertionError(what)
    say("    ok: %s" % what)


def run(argv, env=None, timeout=300, cwd=None):
    done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env, cwd=cwd,
                          encoding="utf-8", errors="replace")
    return done.returncode, (done.stdout or "") + (done.stderr or "")


class Ctx:
    """Where everything is on this host, and the crew modules loaded from the installed plugin copy."""

    def __init__(self, profile):
        self.profile = profile
        local = os.environ.get("LOCALAPPDATA")
        self.home = os.path.join(local, "hermes") if IS_WINDOWS and local else os.path.expanduser("~/.hermes")
        self.profile_home = self.home if profile in ("", "default") else os.path.join(self.home, "profiles", profile)
        self.plugin = os.path.join(self.profile_home, "plugins", "crew")
        self.scripts = os.path.join(self.plugin, "scripts")
        self.agent = os.path.join(self.home, "hermes-agent")
        os.environ["HERMES_HOME"] = self.profile_home      # what Hermes sets for a process of this profile
        os.environ["PYTHONUTF8"] = "1"
        for name in ("HERMES_BIN", "HERMES_AGENT_SRC", "HERMES_AGENT_DIR", "HERMES_SRC", "KANBAN_DB", "HERMES_KANBAN_DB"):
            os.environ.pop(name, None)       # nothing pinned: crew must find all of it by itself
        if self.scripts not in sys.path:
            sys.path.insert(0, self.scripts)
        import crew_card
        import crew_proc
        import crew_safety
        self.card, self.proc, self.safety = crew_card, crew_proc, crew_safety
        self.card_id = None

    def script_env(self):
        return dict(os.environ, HERMES_HOME=self.profile_home)


# ---------------------------------------------------------------------------------------------- the steps

def step_layout(c):
    exe = "hermes.exe" if IS_WINDOWS else "hermes"
    check(os.path.isdir(c.agent), "Hermes source tree at %s" % c.agent)
    if IS_WINDOWS:
        check(os.path.isfile(os.path.join(c.home, "bin", exe)), "launcher %s\\bin\\%s" % (c.home, exe))
        check(os.path.isfile(os.path.join(c.agent, "venv", "Scripts", "python.exe")), "venv\\Scripts\\python.exe")
        check(not os.path.exists(os.path.join(c.agent, "venv", "bin", "python")), "no POSIX venv/bin/python here")
    check(os.path.isfile(os.path.join(c.scripts, "crew_card.py")), "crew installed in the profile: %s" % c.plugin)
    want = re.search(r"^version:\s*['\"]?([\w.]+)", open(os.path.join(SOURCE, "plugin.yaml"), encoding="utf-8").read(), re.M).group(1)
    have = re.search(r"^version:\s*['\"]?([\w.]+)", open(os.path.join(c.plugin, "plugin.yaml"), encoding="utf-8").read(), re.M).group(1)
    check(want == have, "installed crew version %s == checkout %s" % (have, want))


def step_hermes_python(c):
    cc = c.card
    check(norm(cc.default_home()) == norm(c.home), "default_home() = %s" % cc.default_home())
    check(norm(cc.base_home()) == norm(c.home), "base_home() from the profile home = %s" % cc.base_home())
    check(norm(cc.hermes_root()) == norm(c.agent), "hermes_root() = %s" % cc.hermes_root())
    py = cc.hermes_python()
    check(bool(py) and os.path.isfile(py), "hermes_python() = %s" % py)
    if IS_WINDOWS:
        # install.ps1 puts the venv at <hermes-agent>\venv; Hermes Desktop's managed runtime keeps it under
        # installs\<id>\environments\<hash>\venv. Either way it is <venv>\Scripts\python.exe.
        check(os.path.normcase(py).endswith(os.path.normcase(os.path.join(os.sep + "venv", "Scripts", "python.exe"))), "it is <venv>\\Scripts\\python.exe")
        venv = os.path.dirname(os.path.dirname(py))
        check(norm(cc.venv_python(venv)) == norm(py), "venv_python(venv) agrees")
        sites = cc.venv_site_packages(venv)
        check(any(s.lower().endswith(os.path.join("lib", "site-packages")) for s in sites), "venv_site_packages = %s" % sites)
    rc, out = run([py, "-c", "import hermes_cli, sys; print('hermes_cli', sys.version.split()[0])"])
    check(rc == 0 and "hermes_cli" in out, "that python imports hermes_cli (%s)" % out.strip())
    exe = cc.hermes_bin()
    check(os.path.isfile(exe) or bool(__import__("shutil").which(exe)), "hermes_bin() = %s" % exe)
    rc, out = run([exe, "--version"], env=c.script_env())
    check(rc == 0, "`hermes --version` runs: %s" % out.strip().splitlines()[0:1])


def step_guard(c):
    bare = __import__("importlib.util").util.find_spec("hermes_cli") is None
    say("    bare interpreter (no hermes_cli of its own): %s" % bare)
    c.safety._hermes()
    import tools.approval_detection as ad
    check(norm(ad.__file__).startswith(norm(c.agent)), "tools.approval_detection imported from %s" % ad.__file__)
    ok, why = c.safety.check_proof("echo hi", "safe")
    check(ok, "a plain command passes the guard")
    ok, why = c.safety.check_proof("rm -rf /", "brave")
    check(not ok and "hardline" in why, "`rm -rf /` refused even in brave mode: %s" % why[:80])
    ok, why = c.safety.check_proof("rm -rf build", "safe")
    check(not ok and "flagged" in why, "`rm -rf build` flagged in safe mode: %s" % why[:80])
    ok, why = c.safety.check_proof("rm -rf build", "brave")
    check(ok, "the same command passes in brave mode")


def step_proof(c):
    s = c.safety
    bash = s.git_bash() if IS_WINDOWS else "/bin/bash"
    check(bool(bash), "Git Bash found: %s" % bash)
    if IS_WINDOWS:
        check(os.path.basename(bash).lower() == "bash.exe" and "system32" not in bash.lower(), "it is Git's bash, not WSL's")
    r = s.run_proof("echo crew-e2e-out; exit 3", timeout=120)
    check(r.rc == 3 and "crew-e2e-out" in r.out and not r.blocked, "exit code 3 comes back with the output (rc=%s)" % r.rc)
    r = s.run_proof("echo fine", timeout=120)
    check(r.rc == 0 and "fine" in r.out, "exit code 0 comes back")
    r = s.run_proof("rm -rf /", timeout=120, mode="brave")
    check(r.rc == s.BLOCKED_RC and r.blocked, "`rm -rf /` is blocked and never ran: %s" % r.blocked[:60])
    r = s.run_proof("%s -V" % c.card.PYTHON, timeout=120)
    check(r.rc == 0 and "Python 3" in r.out, "crew_card.PYTHON (%s) runs in Git Bash: %s" % (c.card.PYTHON, r.out.strip()))
    r = s.run_proof("python3 -V", timeout=120)      # information only: what crew's skills tell a worker to type
    say("    info: `python3 -V` in Git Bash -> rc=%s %s" % (r.rc, r.out.strip()[:80]))
    r = s.run_proof("%s %s safety" % (c.card.PYTHON, c.card.SELF), timeout=300)
    check(r.rc == 0 and r.out.strip().splitlines()[-1] in ("safe", "brave"),
          "a proof that runs crew_card.py itself works: %s" % r.out.strip()[-40:])


def step_reexec(c):
    with tempfile.TemporaryDirectory() as tmp:
        probe = os.path.join(tmp, "probe.py")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("import os, sys\n"
                     "import hermes_cli\n"
                     "print('PROBE', sys.executable, os.environ.get('CREW_REEXEC'))\n"
                     "sys.exit(7)\n")
        code = ("import sys; sys.path.insert(0, %r); import crew_card; "
                "crew_card.reexec_under_hermes_python(%r); print('NOT RE-EXECUTED'); sys.exit(0)" % (c.scripts, probe))
        t0 = time.time()
        rc, out = run([sys.executable, "-c", code], env=c.script_env(), timeout=300)
        check("PROBE" in out and "NOT RE-EXECUTED" not in out, "the probe ran under another python: %s" % out.strip()[:200])
        py = c.card.hermes_python()
        check(norm(out.split("PROBE", 1)[1].split()[0]) == norm(py), "that python is the Hermes venv python")
        check(rc == 7, "the probe's exit status 7 came back to the caller (rc=%s, %.1fs)" % (rc, time.time() - t0))


def step_cli(c):
    script = os.path.join(c.scripts, "crew_card.py")
    rc, out = run([sys.executable, script, "proof-check", "--command", "echo hi"], env=c.script_env())
    check(rc == 0 and out.strip().splitlines()[-1] == "ok", "crew_card.py proof-check 'echo hi' -> %s" % out.strip()[-60:])
    rc, out = run([sys.executable, script, "proof-check", "--command", "rm -rf /"], env=c.script_env())
    check(out.strip().splitlines()[-1].startswith("hardline"), "crew_card.py proof-check 'rm -rf /' -> %s" % out.strip()[-80:])


def step_board(c):
    exe = c.card.hermes_bin()
    body = "Role: worker\nCoordinator: owner/s\nBudget: 200000 tokens\n\nGOAL: e2e\nDone when: d\n\nproof command: true\n"
    rc, out = run([exe, "kanban", "create", "crew e2e card", "--body", body], env=c.script_env(), timeout=300)
    m = re.search(r"\bt_[0-9a-f]{6,}\b", out)
    check(rc == 0 and m is not None, "`hermes kanban create` made a card: %s" % out.strip()[:120])
    c.card_id = m.group(0)
    db = os.path.join(c.home, "kanban.db")
    check(os.path.isfile(db), "the board is %s" % db)
    found = c.card.kanban_db()
    check(found and norm(found) == norm(db), "crew_card.kanban_db() = %s" % found)
    row = c.card.card_row(c.card_id)
    check(row is not None and row[1] == "crew e2e card", "crew_card.card_row(%s) reads it back: %s" % (c.card_id, row and row[1]))
    rc, out = run([sys.executable, os.path.join(c.scripts, "crew_stop.py"), "--dry-run", "--json"], env=c.script_env())
    check(rc == 0 and c.card_id in out, "crew_stop.py --dry-run sees the card (rc=%s)" % rc)
    with open(os.path.join(c.home, "e2e-card-id.txt"), "w", encoding="utf-8") as fh:
        fh.write(c.card_id)


def step_dashboard(c):
    """Runs inside the Hermes venv python (re-launched by main): the dashboard plugin imports fastapi."""
    if not c.card_id:
        c.card_id = open(os.path.join(c.home, "e2e-card-id.txt"), encoding="utf-8").read().strip()
    from starlette.requests import Request
    sys.path.insert(0, os.path.join(c.plugin, "dashboard"))
    import plugin_api
    scope = {"type": "http", "method": "GET", "path": "/api/plugins/crew/board.json", "query_string": b"",
             "headers": [], "scheme": "http", "server": ("127.0.0.1", 9119)}
    res = plugin_api.get_board_json(Request(scope))
    body = res.body.decode("utf-8")
    check(res.status_code == 200, "plugin api /board.json -> 200")
    data = json.loads(body)
    check("crew e2e card" in body and c.card_id in body, "the board JSON carries card %s (%d bytes, keys %s)" % (c.card_id, len(body), sorted(data)[:6]))
    # 0.10.0: the card route is JSON only (the React page asks for <id>.json; a bare id answers 404)
    res = plugin_api.get_card(c.card_id + ".json", Request(dict(scope, path="/api/plugins/crew/card/" + c.card_id + ".json")))
    check(res.status_code == 200 and c.card_id in res.body.decode("utf-8"), "plugin api /card/%s.json -> 200" % c.card_id)
    res = plugin_api.get_app_js(Request(dict(scope, path="/api/plugins/crew/app.js")))
    check(res.status_code == 200 and b"page-board" in res.body, "plugin api /app.js -> 200 with the app (%d bytes)" % len(res.body))
    # the standalone server, the way WINDOWS.md starts it, over real HTTP
    port = 18799
    env = dict(c.script_env(), CREW_GRAPH_PORT=str(port), CREW_GRAPH_BIND="127.0.0.1")
    srv = subprocess.Popen([sys.executable, os.path.join(c.scripts, "crew_graph_serve.py")], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, start_new_session=not IS_WINDOWS)
    try:
        body = ""
        for _ in range(60):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/board.json" % port, timeout=5) as r:
                    body = r.read().decode("utf-8")
                break
            except OSError:
                if srv.poll() is not None:
                    raise AssertionError("crew_graph_serve.py exited: %s" % srv.stderr.read().decode("utf-8", "replace")[-400:])
                time.sleep(1)
        check(c.card_id in body, "crew_graph_serve.py serves /board.json over HTTP with the card")
    finally:
        c.proc.terminate_tree(srv.pid)
        srv.wait(timeout=30)


# ---------------------------------------------------------------------------------- agent commands (no python3)

# The one launcher line a skill still gives an agent: the background watcher (everything else is a crew_* tool).
WATCH_RX = re.compile(r"""terminal\(background=true, notify_on_complete=true, command='([^']*crew_card\.py watch --card <id>)'\)""")
# Any other crew_card.py subcommand in a skill would send an agent back to a shell line the tools replaced.
OLD_CMD_RX = re.compile(r"crew_card\.py\s+(?!watch\b)\S+")
# Tool name each role skill must call (file -> names)
SKILL_TOOLS = {"crew-verifier": ("crew_verdict(", "crew_progress("), "crew-role-worker": ("crew_verdict(",),
               "crew-role-content": ("crew_verdict(",), "crew": ("crew_proof_check(", "crew_plan(", "crew_lesson("),
               "crew-diagnose": ("crew_diagnose(",)}

# Runs under the Hermes venv python: executes each command in the shell Hermes gives an agent's terminal tool.
AGENT_TERMINAL = r"""
import json, sys, tempfile
from tools.environments.local import LocalEnvironment
cmds = json.load(sys.stdin)
out = []
with tempfile.TemporaryDirectory() as tmp:
    env = LocalEnvironment(cwd=tmp, timeout=240)
    try:
        for cmd in cmds:
            r = env.execute(cmd)
            out.append({"cmd": cmd, "rc": r.get("returncode"), "out": r.get("output", "")})
    finally:
        env.cleanup()
print("@@RESULT@@" + json.dumps(out))
"""

# Runs under the Hermes venv python the way a role process does: the tools called in-process, no shell, no launcher.
# argv[1] = the board step's card id.
TOOLS_IN_PROCESS = r"""
import json, os, sys, types
import crew_tools
card = sys.argv[1]
names = []
crew_tools.register_tools(types.SimpleNamespace(register_tool=lambda **kw: names.append(kw["name"])))
out = {"registered": sorted(names)}
out["proof_check"] = json.loads(crew_tools.crew_proof_check({"command": "rm -rf build"}))
out["verdict"] = json.loads(crew_tools.crew_verdict({"card": card}))
out["diagnose"] = json.loads(crew_tools.crew_diagnose({"state": "todo"}))
les = json.loads(crew_tools.crew_lesson({"role": "worker", "text": "e2e lesson"}))
les["exists"] = bool(les.get("file")) and os.path.isfile(les["file"])
out["lesson"] = les
print("@@RESULT@@" + json.dumps(out))
"""


def posix_path(p):
    """C:\\Users\\x or /c/Users/x -> /c/users/x style, so a Git Bash path and a Windows path compare."""
    p = p.replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        p = "/" + p[0].lower() + p[2:]
    return p


def path_without_python():
    """PATH minus every directory that provides python3 / python / py (setup-python's, the Windows Store stubs')."""
    names = ("python3", "python", "py", "python3.exe", "python.exe", "py.exe")
    keep = [d for d in os.environ.get("PATH", "").split(os.pathsep)
            if d and not any(os.path.isfile(os.path.join(d, n)) for n in names)]
    return os.pathsep.join(keep)


def step_agent_commands(c):
    texts = {}
    for name in sorted(os.listdir(os.path.join(c.plugin, "skills"))):
        with open(os.path.join(c.plugin, "skills", name, "SKILL.md"), encoding="utf-8") as fh:
            texts[name] = fh.read()
    bad = [n for n, t in texts.items() if re.search(r"\bpython3\b", t)]
    check(not bad, "no installed skill tells an agent to run python3 (checked %d)" % len(texts))
    launcher = os.path.join(c.scripts, "crew-run.sh")
    check(os.path.isfile(launcher), "launcher installed: %s" % launcher)
    for skill, names in SKILL_TOOLS.items():
        miss = [n for n in names if n not in texts.get(skill, "")]
        check(not miss, "%s/SKILL.md names its tools %s (missing: %s)" % (skill, ", ".join(names), miss or "none"))
    old = ["%s: %s" % (n, m.group(0)) for n, t in texts.items() for m in OLD_CMD_RX.finditer(t)]
    check(not old, "no installed skill gives a crew_card.py command except watch (%s)" % (old[:3] or "none found"))
    watch = WATCH_RX.search(texts["crew"])
    check(watch is not None, "crew/SKILL.md gives the background watcher command")
    card = c.card_id or open(os.path.join(c.home, "e2e-card-id.txt"), encoding="utf-8").read().strip()
    # --lifetime 1 makes the watcher give up after a second ("still running") instead of waiting for the card to end
    cmds = ['for n in python3 python py; do command -v "$n"; done; echo @@PYEND',
            watch.group(1).replace("<id>", card) + " --lifetime 1"]
    # the owner's CLI: still there, still answers the same way
    cli = 'sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" crew_card.py '
    cmds += [cli + "safety", cli + "proof-check --command 'rm -rf build'", cli + "verdict --card " + card]
    env = dict(os.environ, HERMES_HOME=c.profile_home, PATH=path_without_python() if IS_WINDOWS else os.environ["PATH"])
    py = c.card.hermes_python()
    done = subprocess.run([py, "-c", AGENT_TERMINAL], input=json.dumps(cmds), capture_output=True, text=True,
                          timeout=900, env=env, encoding="utf-8", errors="replace")
    body = (done.stdout or "")
    check("@@RESULT@@" in body, "Hermes's terminal environment ran the commands (rc=%s %s)" % (done.returncode, (done.stderr or "")[-300:]))
    res = json.loads(body.split("@@RESULT@@", 1)[1])
    found = [ln.strip() for ln in res[0]["out"].split("@@PYEND")[0].splitlines() if ln.strip()]
    if IS_WINDOWS:
        # The point: an agent never depends on a system Python. Newer Hermes (0.23.x) puts the Python it ships itself
        # (<home>\tools\python-*) on its terminal PATH; that one is Hermes's own and allowed. Anything else fails.
        own = posix_path(os.path.join(c.home, "tools")).lower().rstrip("/") + "/"
        foreign = [p for p in found if not posix_path(p).lower().startswith(own)]
        check(not foreign, "inside the agent terminal: no python3 / python / py on PATH except Hermes's own "
              "(found: %s)" % (found or "none"))
    else:
        say("    info: python on PATH inside the agent terminal on this host: %s" % (found or "none"))
    for r in res[1:]:
        say("    $ %s\n      rc=%s\n%s" % (r["cmd"][:150], r["rc"], "\n".join("      | " + ln for ln in r["out"].strip().splitlines()[-6:])))
    wout = res[1]["out"]
    check(res[1]["rc"] == 0 and (card in wout or "still running" in wout),
          "the skill's watcher line through the agent terminal exited 0 and reported: %s" % wout.strip()[-80:])
    check(res[2]["rc"] == 0 and res[2]["out"].strip().splitlines()[-1] in ("safe", "brave"), "owner CLI `crew_card.py safety` through crew-run.sh: %s" % res[2]["out"].strip()[-20:])
    check(res[3]["rc"] == 0 and (res[3]["out"].strip().splitlines()[-1] == "ok" or "flagged" in res[3]["out"] or "hardline" in res[3]["out"]),
          "owner CLI `crew_card.py proof-check` through crew-run.sh answered: %s" % res[3]["out"].strip()[-40:])
    # the board step's card has no owner-confirmed proof, so FAIL is the right verdict: what is proven is that the
    # command ran and crew answered, not that this card passes
    check("verdict:" in res[-1]["out"], "owner CLI `crew_card.py verdict --card %s` through crew-run.sh answered: %s" % (card, res[-1]["out"].strip().splitlines()[-1][:60]))
    # the tools, in-process, as a role process runs them (no shell between the model and crew)
    tenv = dict(env, PYTHONPATH=c.scripts + os.pathsep + env.get("PYTHONPATH", ""))
    done = subprocess.run([py, "-c", TOOLS_IN_PROCESS, card], capture_output=True, text=True, timeout=900,
                          env=tenv, encoding="utf-8", errors="replace")
    body = done.stdout or ""
    check("@@RESULT@@" in body, "crew_tools ran in-process under the Hermes python (rc=%s %s)" % (done.returncode, (done.stderr or "")[-300:]))
    t = json.loads(body.split("@@RESULT@@", 1)[1])
    want = ["crew_diagnose", "crew_lesson", "crew_plan", "crew_proof_check", "crew_progress", "crew_verdict"]
    check(t["registered"] == sorted(want), "register_tools registers the six crew tools: %s" % t["registered"])
    pc = t["proof_check"]
    check(pc.get("check") in ("ok", "flagged", "hardline") and pc.get("safety_mode") in ("safe", "brave"),
          "crew_proof_check({'command': 'rm -rf build'}) answered JSON: %s" % pc)
    v = t["verdict"]
    check(v.get("verdict") in ("PASS", "FAIL"), "crew_verdict({'card': %s}) answered JSON, FAIL expected without proof: %s" % (card, str(v)[:120]))
    dg = t["diagnose"]
    check(isinstance(dg.get("count"), int) and isinstance(dg.get("text"), str), "crew_diagnose({'state': 'todo'}) answered count=%s and text" % dg.get("count"))
    ls = t["lesson"]
    check(ls.get("exists"), "crew_lesson wrote the lessons file: %s" % ls.get("file"))


# ------------------------------------------------------------------------------------------------ one real card

def redact(text, secret):
    return text.replace(secret, "<key>") if secret else text


def step_card_run(c):
    key = os.environ.get("CREW_E2E_KEY", "")
    provider = os.environ.get("CREW_E2E_PROVIDER", "")
    model = os.environ.get("CREW_E2E_MODEL", "")
    base_url = os.environ.get("CREW_E2E_BASE_URL", "")
    key_env = os.environ.get("CREW_E2E_KEY_ENV", "")
    own_auth = bool(os.environ.get("CREW_E2E_PROFILE_AUTH"))
    if not key and not own_auth:
        say("    SKIPPED card-run: no model key in CREW_E2E_KEY (the repository secret is absent: forks and "
            "pull requests never get it). No card was run.")
        return
    check(bool(provider and model and (key_env or own_auth)), "card-run settings: provider=%s model=%s key env=%s base_url=%s" % (provider, model, key_env or "(the profile's own login)", base_url or "(provider default)"))
    worker = c.card.role_profile("worker")
    check(worker != c.profile and c.card.profile_exists(worker), "the crew worker profile exists: %s" % worker)
    exe = c.card.hermes_bin()
    env = dict(c.script_env(), **({key_env: key} if key else {}))
    for k, v in (("model.provider", provider), ("model.default", model), ("model.base_url", base_url), ("model.key_env", key_env if key else "")):
        if not v:
            continue
        rc, out = run([exe, "-p", worker, "config", "set", k, v], env=env)
        check(rc == 0, "hermes -p %s config set %s (rc=%s)" % (worker, k, rc))
    # Hermes sends a graded reasoning_effort by default; Groq's gpt-oss accepts one but Hermes sends "default" to
    # api.groq.com, which it 400s. Marking the model as not reasoning leaves the field off the wire for every provider.
    if key:                      # CI's throwaway profile; a logged-in box's own profile is left as it is
        with open(os.path.join(c.home, "profiles", worker, "config.yaml"), "a", encoding="utf-8") as fh:
            fh.write('\nmodel_overrides:\n  %s:\n    "%s":\n      supports_reasoning: false\n' % (provider, model))
    # A dispatched worker gets its profile's .env, not this process's environment: the key goes there (a file in
    # the runner's throwaway profile, removed in the finally below), never on a command line.
    env_file = os.path.join(c.home, "profiles", worker, ".env")
    had_env = os.path.exists(env_file)
    saved = open(env_file, encoding="utf-8").read() if had_env else ""
    land = tempfile.mkdtemp(prefix="crew-e2e-card-")
    posix = land.replace("\\", "/")
    card = ""
    try:
        if key:
            with open(env_file, "w", encoding="utf-8") as fh:
                fh.write(saved + ("\n" if saved and not saved.endswith("\n") else "") + "%s=%s\n" % (key_env, key))
        script = os.path.join(c.scripts, "crew_card.py")
        rc, out = run([sys.executable, script, "open", "--role", "worker", "--title", "crew e2e hello",
                       "--goal", "Create the file hello.txt in the landing folder whose only line is: crew-e2e-ok",
                       "--artifact", "hello.txt", "--lands", posix, "--audience", "CI",
                       "--done-when", "hello.txt exists in the landing folder and contains the text crew-e2e-ok",
                       "--constraints", "Do nothing else. One tool call to write the file is enough.",
                       "--proof-cmd", 'grep -q crew-e2e-ok "%s/hello.txt"' % posix, "--max-runtime", "600"], env=env, timeout=300)
        out = redact(out, key)
        m = re.search(r"\bt_[0-9a-f]{6,}\b", out)
        check(rc == 0 and m is not None, "crew_card.py open made the card: %s" % out.strip()[-200:])
        card = m.group(0)
        deadline = time.time() + 15 * 60
        status = ""
        while time.time() < deadline:
            rc, out = run([exe, "kanban", "dispatch", "--max", "1"], env=env, timeout=300)
            row = c.card.card_row(card)
            status = row[2] if row else "?"
            say("    %s status=%s (dispatch: %s)" % (time.strftime("%H:%M:%S"), status, redact(out, key).strip().splitlines()[-1:][:1]))
            if status in ("done", "blocked", "archived"):
                break
            time.sleep(30)
        if status != "done":
            rc, out = run([exe, "kanban", "log", card], env=env, timeout=120)
            say("    card log tail:\n" + redact(out, key)[-3000:])
        check(status == "done", "card %s reached done (status=%s)" % (card, status))
        verdicts = c.card.all_verdicts(card)
        check(bool(verdicts) and verdicts[-1].get("verdict") == "PASS", "a PASS verdict is recorded: %s" % (verdicts[-1:] and verdicts[-1].get("verdict")))
        check(os.path.isfile(os.path.join(land, "hello.txt")) and "crew-e2e-ok" in open(os.path.join(land, "hello.txt"), encoding="utf-8").read(),
              "the worker's artifact exists and says crew-e2e-ok")
    finally:
        # Archive before the landing folder goes: the coordinator re-runs a done card's proof command, and with the
        # folder removed that audit fails and opens a follow-up card nobody dispatches on a box without a gateway.
        if card:
            archive_card_tree(c, card, env)
        __import__("shutil").rmtree(land, ignore_errors=True)
        if key and had_env:
            with open(env_file, "w", encoding="utf-8") as fh:
                fh.write(saved)
        elif key:
            os.remove(env_file)


def step_stop(c):
    p = c.proc
    check(p.alive(os.getpid()), "crew_proc.alive(this process) is true")
    check(not p.alive(2 ** 22 + 123), "crew_proc.alive(a pid nobody has) is false")
    card_id = "t_e2e00001"
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)", "work kanban task " + card_id],
                             start_new_session=not IS_WINDOWS)     # a worker leads its own group; killpg must not reach us
    try:
        time.sleep(1.0)
        check(p.alive(child.pid), "spawned pid %d reads alive" % child.pid)
        cmd = p.cmdline_of(child.pid)
        check("work kanban task" in cmd and card_id in cmd, "cmdline_of(%d) = %s" % (child.pid, cmd[-70:]))
        import crew_stop
        check(crew_stop.is_our_worker(cmd, card_id), "crew_stop recognises it as card %s's worker" % card_id)
        word, landed = crew_stop.kill_run({"id": 1, "worker_pid": child.pid}, card_id, False)
        check(landed and "dead" in word, "crew_stop.kill_run: %s" % word)
        check(not p.alive(child.pid), "the process is gone")
    finally:
        if child.poll() is None:
            p.terminate_tree(child.pid)
        child.wait(timeout=30)


STEPS = [("layout", step_layout), ("hermes-python", step_hermes_python), ("guard", step_guard),
         ("proof", step_proof), ("reexec", step_reexec), ("cli", step_cli), ("board", step_board),
         ("dashboard", step_dashboard), ("agent-commands", step_agent_commands),
         ("stop", step_stop), ("card-run", step_card_run)]
OPT_IN = ("card-run",)      # a real model run: only with --only card-run


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--profile", default="e2e")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    c = Ctx(args.profile)
    failed = []
    for name, fn in STEPS:
        if (args.only and name != args.only) or (not args.only and name in OPT_IN):
            continue
        if not args.only and name == "dashboard":
            # needs the Hermes venv python (fastapi); re-run this script under it for that one step
            say("STEP %s (under the Hermes venv python)" % name)
            py = c.card.hermes_python()
            rc, out = run([py, os.path.abspath(__file__), "--profile", args.profile, "--only", "dashboard"], timeout=600)
            say(out.rstrip())
            if rc != 0:
                failed.append(name)
                say("STEP %s FAILED (rc=%s)" % (name, rc))
            continue
        say("STEP %s" % name)
        try:
            fn(c)
            say("STEP %s PASSED" % name)
        except Exception:     # noqa: BLE001 - every step is reported, then the run fails
            failed.append(name)
            say("STEP %s FAILED\n%s" % (name, traceback.format_exc()))
    if not args.only:
        archive_e2e_card(c)
    say("RESULT: %s" % ("FAILED steps: " + ", ".join(failed) if failed else "all steps passed"))
    return 1 if failed else 0


def archive_card_tree(c, card, env):
    """Archive the card-run card and every card opened under it (audit follow-ups), so a run on a person's box
    leaves nothing ready on their board."""
    tree, frontier = [card], [card]
    while frontier:
        kids = [r[0] for cid in frontier
                for r in c.card.q_db(c.card.kanban_db(), "select child_id from task_links where parent_id = ?", (cid,))
                if r[0] and r[0] not in tree]
        tree += kids
        frontier = kids
    for cid in tree:
        rc, out = run([c.card.hermes_bin(), "kanban", "archive", cid], env=env, timeout=120)
        say("    cleanup: archived card-run card %s (rc=%s)" % (cid, rc) if rc == 0 else
            "    cleanup: could not archive card-run card %s (rc=%s): %s" % (cid, rc, out.strip()[-160:]))


def archive_e2e_card(c):
    """The board step's card sits `ready` with no assignee on the profile's real board: archive it, so a run on
    a person's box leaves no card behind (CI's board is thrown away; a person's is not)."""
    path = os.path.join(c.home, "e2e-card-id.txt")
    card = c.card_id or (open(path, encoding="utf-8").read().strip() if os.path.isfile(path) else "")
    if not card:
        return
    rc, out = run([c.card.hermes_bin(), "kanban", "archive", card], env=c.script_env(), timeout=120)
    say("    cleanup: archived e2e card %s (rc=%s)" % (card, rc) if rc == 0 else
        "    cleanup: could not archive e2e card %s (rc=%s): %s" % (card, rc, out.strip()[-160:]))
    if os.path.isfile(path):
        os.remove(path)


if __name__ == "__main__":
    sys.exit(main())
