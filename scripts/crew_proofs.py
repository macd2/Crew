#!/usr/bin/env python3
"""One command that runs every crew proof and says which one broke.

The proofs are the plugin's own acceptance evidence, but nothing ran them together: a regression sat
in a proof that nobody executed until the owner hit it in chat. This runner is that one command - it
discovers every proof beside it, runs each in its own process, keeps the tail of its output, and
exits non-zero when any of them fails, so a cron job or a git hook can gate on it.

  crew_proofs.py                     every proof, the live-service ones skipped
  crew_proofs.py --all               every proof, including the ones that need a live chat or a desktop
  crew_proofs.py --only heal,unstale run the proofs whose file name matches any of these words
  crew_proofs.py --list              what would run, and what is held back, and why
  crew_proofs.py --json              the same result as data
  crew_proofs.py --timeout 900       per-proof ceiling in seconds (default 600)
  crew_proofs.py --jobs 4            proofs that run at once (default: cores / 2, 2 to 4; 1 = strictly serial)
  crew_proofs.py --changed           proofs touched by the working tree, for a pre-push gate

Exit: 0 when every proof that ran passed, 1 when one failed, 2 when the runner itself could not run.

Every proof runs on the kernel's `crew-proofs` board, never the live one: the runner creates the board
(`hermes kanban boards create crew-proofs`, idempotent) and gives every child the env that pins it
(crew_proof_board.proofs_env). A proof that seeds cards calls crew_proof_board.require_proof_board first
and exits 2 when it would write to the live default board.

Parallel run: only the proofs in ISOLATED run beside each other and beside the rest. Each of them builds a
scratch board, a scratch HERMES_HOME and its own temp dir (or only reads), so they share nothing. Every other
proof seeds or reads the shared `crew-proofs` board, or drives a Chrome on a fixed port, so those run one after
another in a single lane (a proof not listed in ISOLATED is in that lane: a new proof is serial until it is
shown to be independent). The result of every proof is the same serial or parallel; only the wall time differs.

Live-service proofs are held back by default: they send a real message or drive the desktop
panel, so they need a reachable server and they leave traces. They run with --all, and they are named
in --list as skipped, never silently dropped.
"""
import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_proof_board  # noqa: E402

# Hardened git: this runner reads revisions out of the checkout, and a repository's own config must
# never run a program for us (the GitSpawn class - core.fsmonitor, hooks, filter drivers). The
# helper sits in scripts/ beside this one; see git_safe.py for what it pins.
import git_safe  # noqa: E402

# Proofs that need something outside this box: a desktop session, a chat round trip.
LIVE = {
    "crew_panel_click_check.py": "drives the desktop panel",
    "crew_entry_proof.py": "needs the live registry and a chat turn",
}

# Proofs whose subject IS a live service reading the live board (the gateway)
# or a live card the owner names, so they run on the live board on purpose and are not pinned. Each one is
# held back above (LIVE / NEEDS_ARGS), so the nightly run never seeds the live board.
LIVE_BOARD = {"crew_graph_flow_check.py"}
# Proofs that only READ real cards off the live board and the live dashboard (they seed nothing), so they
# run every night and are not pinned: pinned to the proofs board they would find no card to check.
# crew_tokens_section_proof.py left this set (issue #15): it seeds its own probe cards on the proofs board,
# because a fresh board had no card in every state and the proof failed with "no card page to check".
LIVE_READERS = {"crew_route_trail_proof.py"}

# Proofs that share nothing with any other proof: each makes a scratch kanban board (HERMES_KANBAN_DB pinned
# to a file in its own temp dir, or the coordinator proof's TMP), a scratch HERMES_HOME, a free port, and its
# own throwaway Chrome profile; the rest only read. These run in the worker pool. Anything else uses the
# shared crew-proofs board (crew_proof_board.proof_db / graph_base) and stays in the serial lane.
ISOLATED = {
    "crew_coordinator_proof.py", "crew_two_stage_proof.py", "crew_origin_open_proof.py",
    "crew_heal_proof.py", "crew_probe_skip_proof.py", "crew_route_floor_proof.py",
    "crew_intake_create_proof.py", "crew_diagnose_proof.py", "crew_notify_proof.py",
    "crew_permissions_proof.py", "crew_route_trail_proof.py", "crew_parity_check.py",
    "crew_role_platforms_proof.py", "crew_option_commands_proof.py", "crew_panel_steps_proof.py",
    "crew_signature_gate.py",
}
# Per-proof ceilings above the runner's default: this proof is a few dozen real `hermes kanban` CLI starts,
# each seconds on an idle box and far more on a loaded one, so the default 600 s was the wall it hit.
SLOW_TIMEOUT = {"crew_coordinator_proof.py": 1800}

# A check that cannot run on its own: it takes an explicit card. It is held back with that reason
# rather than reported as a failure, and it runs as soon as --card says which card to walk.
NEEDS_ARGS = {"crew_graph_flow_check.py": "--card <id> [--package <path>]"}
# Every proof that takes --card gets the runner's --card (issue #15 follow-up: `--all --card X` started
# crew_panel_click_check.py without it, so it died on argparse instead of checking the panel).
CARD_ARGS = set(NEEDS_ARGS) | {"crew_panel_click_check.py"}


def candidates():
    """Every runnable proof/check in this directory, in a stable order."""
    out = []
    for name in sorted(os.listdir(HERE)):
        if not name.endswith(".py") or name == os.path.basename(__file__):
            continue
        if re.search(r"(_proof|_check|signature_gate)\.py$", name):
            out.append(name)
    return out


def newest_crew_card():
    """--all with no --card: the newest real crew card on the live board that has run, so the card-taking
    checks run instead of being held back (owner, issue #15 follow-up: under --all nothing is skipped).
    Probe fixtures are not real work and are passed over. '' when the board has no such card."""
    import sqlite3
    import crew_card
    db = os.path.join(crew_card.base_home(), "kanban.db")
    if not os.path.exists(db):
        return ""
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
        try:
            row = conn.execute(
                "select t.id from tasks t where t.assignee like 'crew-%' and coalesce(t.created_by,'') != ? "
                "and exists (select 1 from task_runs r where r.task_id = t.id) "
                "order by t.created_at desc limit 1", (crew_card.PROBE_OWNER,)).fetchone()
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 - no readable board: the checks stay held back with their reason
        return ""
    return row[0] if row else ""


def choose(args):
    picked, skipped = [], []
    for name in candidates():
        if args.only:
            words = [w.strip().lower() for w in args.only.split(",") if w.strip()]
            if not any(w in name.lower() for w in words):
                continue
        if name in CARD_ARGS and not getattr(args, "card", ""):
            skipped.append({"file": name, "why": "takes %s" % NEEDS_ARGS.get(name, "--card <id>")})
            continue
        if name in LIVE and not args.all:
            skipped.append({"file": name, "why": LIVE[name]})
            continue
        picked.append(name)
    return picked, skipped


def child_env(name):
    """The env one proof runs in: the crew-proofs board pinned, except the live-service proofs (LIVE_BOARD)
    and the read-only live readers.

    Every child writes UTF-8: the runner decodes the pipe as UTF-8, and on Windows a child's stdout to a pipe
    is otherwise the ANSI code page (cp1252), so a proof printing a box-drawing or check-mark character died
    with UnicodeEncodeError before its first check (issue #15: route_pin, terminal_window). A caller's own
    PYTHONIOENCODING wins."""
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if name in LIVE_BOARD or name in LIVE_READERS:
        return env
    return dict(env, **crew_proof_board.proofs_env())


def run_one(name, timeout, extra=()):
    started = time.time()
    timeout = max(timeout, SLOW_TIMEOUT.get(name, 0))
    path = os.path.join(HERE, name)
    try:
        p = subprocess.run([sys.executable, path] + list(extra), cwd=HERE, capture_output=True,
                           text=True, timeout=timeout, env=child_env(name), stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")
        out = (p.stdout or "") + (p.stderr or "")
        rc = p.returncode
    except subprocess.TimeoutExpired:
        out, rc = "timed out after %ss" % timeout, 124
    except Exception as exc:  # noqa: BLE001 - one broken proof must not stop the run
        out, rc = "runner error: %s" % exc, 125
    return {"file": name, "rc": rc, "seconds": round(time.time() - started, 1),
            "tail": "\n".join(out.strip().splitlines()[-3:]), "log": keep_failure(name, rc, out)}


def keep_failure(name, rc, out):
    """Write a red proof's WHOLE output beside the proofs board and return the path ("" when green).

    The summary keeps three lines, which is the end of a traceback or the last check and almost never the
    cause: a red night could only be explained by re-running, and a load flake does not come back on demand.
    The newest 40 files stay."""
    if rc == 0:
        return ""
    try:
        folder = os.path.join(crew_proof_board.proofs_dir(), "failures")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "%s-%s.txt" % (time.strftime("%Y%m%d-%H%M%S"), name[:-3]))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(out)
        for old in sorted(os.listdir(folder))[:-40]:
            os.remove(os.path.join(folder, old))
        return path
    except OSError:
        return ""


def default_jobs():
    """Half the cores, between 2 and 4: the proofs start Chrome and the hermes CLI, so more workers than
    that only make each one slower (the coordinator proof times out first)."""
    return max(2, min(4, (os.cpu_count() or 4) // 2))


def run_all(picked, timeout, jobs, card, on_done=None):
    """Run the picked proofs and return their results in `picked` order.

    jobs == 1: one after another, as before. Otherwise the proofs outside ISOLATED run one after another in a
    single lane (they share the crew-proofs board) while the ISOLATED ones run beside it in a pool of `jobs`
    workers, the slowest-known first so the long tail starts early."""
    def one(name):
        extra = ["--card", card] if card and name in CARD_ARGS else []
        r = run_one(name, timeout, extra)
        if on_done:
            on_done(r)
        return r

    if jobs <= 1:
        return [one(n) for n in picked]
    lane = [n for n in picked if n not in ISOLATED]
    pool = sorted((n for n in picked if n in ISOLATED), key=lambda n: (-SLOW_TIMEOUT.get(n, 0), n))
    done = {}

    def run_lane():
        for n in lane:
            done[n] = one(n)

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = [ex.submit(run_lane)] if lane else []
        futs += [ex.submit(lambda n=n: done.__setitem__(n, one(n))) for n in pool]
        for f in futs:
            f.result()
    return [done[n] for n in picked]


def _git_lines(args):
    """Changed-file names, or None when git could not answer.

    None is not empty: an empty list means "nothing changed" and lets a pre-push gate pass, so a
    refused or failed git must never look like that. changed_since() turns None into the safe
    answer (run every proof) instead.
    """
    try:
        p = git_safe.run_git(["git"] + args, cwd=os.path.dirname(HERE), capture_output=True,
                             text=True, timeout=120)
    except Exception as exc:  # noqa: BLE001 - a git we will not run is not a clean tree
        print("crew_proofs: git %s failed (%s)" % (" ".join(args), exc), file=sys.stderr)
        return None
    if p.returncode != 0:
        print("crew_proofs: git %s exited %d" % (" ".join(args), p.returncode), file=sys.stderr)
        return None
    return [x for x in p.stdout.split() if x]


def changed_since(rev):
    """Proofs to run for a push or a tree change: the changed proofs, plus the proofs that name a
    changed module, so a fix to a shared helper re-runs the evidence that exercises it.

    A `committed:` prefix looks only at what the commits contain (`rev..HEAD`), never at the working
    tree - the right view for a pre-push gate, since another session's half-finished edits are not
    what this push is carrying.
    """
    committed_only = rev.startswith("committed:")
    if committed_only:
        rev = rev.split(":", 1)[1]
    args = ["diff", "--name-only", rev, "HEAD"] if committed_only else ["diff", "--name-only", rev]
    lines = _git_lines(args)
    if lines is None:
        return None
    names = {os.path.basename(x) for x in lines}
    if not committed_only and rev != "HEAD":
        more = _git_lines(["diff", "--name-only", rev, "HEAD"])
        if more is None:
            return None
        names |= {os.path.basename(x) for x in more}
    known = set(candidates())
    picked = [n for n in known if n in names]
    for stem in {os.path.splitext(n)[0] for n in names if n.endswith(".py") and n not in known}:
        for proof in sorted(known):
            if proof in picked:
                continue
            try:
                if re.search(r"\b%s\b" % re.escape(stem), open(os.path.join(HERE, proof), encoding="utf-8").read()):
                    picked.append(proof)
            except OSError:
                continue
    return sorted(picked)


def main():
    # Started by a bare interpreter (cron on the package-manager layout), switch to the Hermes python before any
    # proof is spawned: each child is [sys.executable, proof], so it inherits the right one.
    import crew_card
    crew_card.reexec_under_hermes_python(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="include the proofs that need live services")
    ap.add_argument("--only", default="", help="comma-separated words matched against proof names")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--jobs", type=int, default=None,
                    help="proofs to run at once (default: %d on this box; 1 = one after another)" % default_jobs())
    ap.add_argument("--changed", nargs="?", const="HEAD", default=None,
                    help="run only the proofs the tree changed (optionally since a revision)")
    ap.add_argument("--quiet", action="store_true",
                    help="say nothing when every proof passes, so a nightly job speaks only on failure")
    ap.add_argument("--card", default="",
                    help="card id for the checks that cannot run without one (see --list)")
    a = ap.parse_args()
    if a.all and not a.card:
        a.card = newest_crew_card()
        if a.card and not a.json and not a.quiet:
            print("--card %s (newest crew card on the live board, for the checks that take one)" % a.card)

    picked, skipped = choose(a)
    if a.changed is not None:
        subset = changed_since(a.changed)
        if subset is not None:
            picked = [n for n in picked if n in subset]

    if a.list:
        for n in picked:
            print("RUN     %s" % n)
        for s in skipped:
            print("SKIP    %s  (%s)" % (s["file"], s["why"]))
        return 0

    if not picked:
        if a.changed is not None:
            if not a.quiet:
                print("nothing changed that a proof covers")
            return 0
        print("nothing to run")
        return 2

    if not crew_proof_board.ensure_proofs_board():
        print("RUNNER ERROR: the crew-proofs board does not exist and `hermes kanban boards create "
              "crew-proofs` did not make it (%s)" % crew_proof_board.proofs_db())
        return 2
    lock = threading.Lock()

    def show(r):
        if a.json or a.quiet:
            return
        with lock:
            print("%-6s %-40s %6.1fs  %s" % ("PASS" if r["rc"] == 0 else "FAIL", r["file"], r["seconds"],
                                             "" if r["rc"] == 0 else r["tail"][:200]), flush=True)

    t0 = time.time()
    results = run_all(picked, a.timeout, max(1, a.jobs if a.jobs else default_jobs()), a.card, show)
    wall = round(time.time() - t0, 1)

    failed = [r for r in results if r["rc"] != 0]
    if a.json:
        print(json.dumps({"ran": len(results), "failed": len(failed), "skipped": skipped,
                          "wall_seconds": wall, "results": results}, indent=1))
    elif a.quiet and not failed:
        return 0
    else:
        print("\n%d proof(s) ran, %d failed, %d held back (live services); wall %.1fs, proofs add up to %.1fs"
              % (len(results), len(failed), len(skipped), wall, sum(r["seconds"] for r in results)))
        print("per proof, slowest first:")
        for r in sorted(results, key=lambda x: -x["seconds"]):
            print("  %7.1fs  %s  %s" % (r["seconds"], "PASS" if r["rc"] == 0 else "FAIL", r["file"]))
        for r in failed:
            print("  FAIL %s (exit %d)\n    %s" % (r["file"], r["rc"], r["tail"]))
            if r.get("log"):
                print("    full output: %s" % r["log"])
    if failed:
        print("RUNNER FAIL: %s" % ", ".join(r["file"] for r in failed))
        return 1
    print("RUNNER OK: every proof that ran passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
