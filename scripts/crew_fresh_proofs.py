#!/usr/bin/env python3
"""Install a crew tree into a throwaway home and run its proofs there, the way a user gets them.

Why: 0.11.0 shipped crew_option_commands_proof.py still listing six options after /crew-lineup was added. The
proof failed on every machine that installed the release, and nothing caught it: CI and publish.py ran pytest
only, never a proof. This is the one gate both of them call, so a release whose own proofs fail is refused
before it is public, and a pull request that leaves a proof stale fails its build.

  crew_fresh_proofs.py                        this checkout, every proof (live-service ones held back)
  crew_fresh_proofs.py --tree DIR             another tree (publish.py passes the exact tree it will push)
  crew_fresh_proofs.py --only option_commands only the proofs whose name matches (comma-separated words)
  crew_fresh_proofs.py --keep                 leave the throwaway home for a look afterwards

The home is new every run (HOME points into it, so `hermes -p <role>` and every profile are the scratch ones,
never the real ones), the real hermes source is linked in, the real install.py installs the tree, and the
INSTALLED crew_proofs.py runs, one proof after another (--jobs 1: a gate has to give the same answer every run).

Exit: 0 every proof that ran passed, 1 a proof failed, 2 the install itself failed or the runner could not run.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_card  # noqa: E402 - the one place crew names Hermes's platform home
# Read before HOME moves: where this machine keeps the Hermes source and the hermes CLI.
REAL_HERMES_SRC = crew_card.hermes_root()
# Hermes's home relative to HOME on this platform (~/.hermes, or AppData/Local/hermes on Windows), so the
# throwaway home has the same layout a user's machine has.
HOME_REL = os.path.relpath(crew_card.default_home(), os.path.expanduser("~"))
# Env that would point a child at the real home, the live board or another checkout.
DROP = ("PYTHONPATH", "HERMES_HOME", "KANBAN_DB", "HERMES_KANBAN_DB", "HERMES_KANBAN_BOARD",
        "CREW_PKG", "CREW_PROFILE", "CREW_OWNER_PROFILE", "HERMES_PROFILE")


def scratch_root():
    """Outside every Hermes home: a scratch HERMES_HOME under <home>/profiles/<p>/ resolves to the live root."""
    root = os.environ.get("CREW_TEST_TMPDIR") or (
        "/data/hermes/scratch/crew-fresh-proofs" if os.path.isdir("/data/hermes/scratch") else tempfile.gettempdir())
    os.makedirs(root, exist_ok=True)
    return root


def box_env(home, tree):
    env = {k: v for k, v in os.environ.items() if k not in DROP}
    hermes = os.environ.get("HERMES_BIN") or shutil.which("hermes") or ""
    env.update(HOME=home, TMPDIR=home, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", CREW_PKG=tree,
               # parity compares the fresh install against the tree it came from, never against whatever
               # release checkout sits beside it (that answers "is this box on GitHub main", not this gate)
               CREW_PACKAGE=tree, CREW_RELEASE=os.path.join(home, "no-release-checkout"))
    if hermes:
        env["HERMES_BIN"] = hermes
    return env


def make_home():
    home = tempfile.mkdtemp(prefix="home-", dir=scratch_root())
    os.makedirs(os.path.join(home, HOME_REL))
    if os.path.isdir(REAL_HERMES_SRC):
        os.symlink(os.path.abspath(REAL_HERMES_SRC), os.path.join(home, HOME_REL, "hermes-agent"))
    return home


def run(tree, only="", jobs=1, timeout=600, keep=False, out=sys.stdout):
    """Install *tree* into a new home and run its proofs. Returns (rc, text): rc as the exit codes above."""
    tree = os.path.abspath(tree)
    if not os.path.isfile(os.path.join(tree, "install.py")):
        return 2, "not a crew tree (no install.py): %s" % tree
    home = make_home()
    env = box_env(home, tree)
    lines = []

    def say(msg):
        lines.append(msg)
        print(msg, file=out, flush=True)

    try:
        started = time.time()
        inst = subprocess.run([sys.executable, os.path.join(tree, "install.py"), "--no-service", "--no-cron"],
                              cwd=tree, env=env, capture_output=True, text=True, timeout=1500,
                              stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")
        if inst.returncode != 0:
            say("FAILED: install.py into a throwaway home exited %d (%.0fs):" % (inst.returncode, time.time() - started))
            say((inst.stdout + inst.stderr).strip()[-3000:])
            return 2, "\n".join(lines)
        say("installed %s into a throwaway home in %.0fs" % (tree, time.time() - started))
        runner = os.path.join(home, HOME_REL, "plugins", "crew", "scripts", "crew_proofs.py")
        if not os.path.isfile(runner):
            say("FAILED: the install left no crew_proofs.py at %s" % runner)
            return 2, "\n".join(lines)
        cmd = [sys.executable, runner, "--jobs", str(jobs), "--timeout", str(timeout)]
        if only:
            cmd += ["--only", only]
        p = subprocess.run(cmd, cwd=os.path.dirname(runner), env=env, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")
        say((p.stdout + p.stderr).strip())
        if p.returncode not in (0, 1):
            say("FAILED: crew_proofs.py could not run (exit %d)" % p.returncode)
            return 2, "\n".join(lines)
        ran = re.search(r"(\d+) proof\(s\) ran", p.stdout)
        if not ran or int(ran.group(1)) == 0:
            say("FAILED: no proof ran - a gate that checks nothing passes nothing")
            return 2, "\n".join(lines)
        return p.returncode, "\n".join(lines)
    finally:
        if keep:
            say("throwaway home kept: %s" % home)
        else:
            shutil.rmtree(home, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tree", default=os.path.dirname(HERE), help="crew tree to install (default: this checkout)")
    ap.add_argument("--only", default="", help="comma-separated words matched against proof names")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=600, help="per-proof ceiling in seconds")
    ap.add_argument("--keep", action="store_true", help="keep the throwaway home")
    a = ap.parse_args()
    rc, _text = run(a.tree, a.only, a.jobs, a.timeout, a.keep)
    sys.exit(rc)


if __name__ == "__main__":
    main()
