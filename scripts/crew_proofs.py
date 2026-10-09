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
  crew_proofs.py --changed           proofs touched by the working tree, for a pre-push gate

Exit: 0 when every proof that ran passed, 1 when one failed, 2 when the runner itself could not run.

Every proof runs on the kernel's `crew-proofs` board, never the live one: the runner creates the board
(`hermes kanban boards create crew-proofs`, idempotent) and gives every child the env that pins it
(crew_proof_board.proofs_env). A proof that seeds cards calls crew_proof_board.require_proof_board first
and exits 2 when it would write to the live default board.

Live-service proofs are held back by default: they send a real message or drive the desktop
panel, so they need a reachable server and they leave traces. They run with --all, and they are named
in --list as skipped, never silently dropped.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_proof_board  # noqa: E402

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
LIVE_READERS = {"crew_tokens_section_proof.py", "crew_route_trail_proof.py"}

# A check that cannot run on its own: it takes an explicit card. It is held back with that reason
# rather than reported as a failure, and it runs as soon as --card says which card to walk.
NEEDS_ARGS = {"crew_graph_flow_check.py": "--card <id> [--package <path>]"}


def candidates():
    """Every runnable proof/check in this directory, in a stable order."""
    out = []
    for name in sorted(os.listdir(HERE)):
        if not name.endswith(".py") or name == os.path.basename(__file__):
            continue
        if re.search(r"(_proof|_check|signature_gate)\.py$", name):
            out.append(name)
    return out


def choose(args):
    picked, skipped = [], []
    for name in candidates():
        if args.only:
            words = [w.strip().lower() for w in args.only.split(",") if w.strip()]
            if not any(w in name.lower() for w in words):
                continue
        if name in NEEDS_ARGS and not getattr(args, "card", ""):
            skipped.append({"file": name, "why": "takes %s" % NEEDS_ARGS[name]})
            continue
        if name in LIVE and not args.all:
            skipped.append({"file": name, "why": LIVE[name]})
            continue
        picked.append(name)
    return picked, skipped


def child_env(name):
    """The env one proof runs in: the crew-proofs board pinned, except the live-service proofs (LIVE_BOARD)
    and the read-only live readers."""
    if name in LIVE_BOARD or name in LIVE_READERS:
        return dict(os.environ)
    return dict(os.environ, **crew_proof_board.proofs_env())


def run_one(name, timeout, extra=()):
    started = time.time()
    path = os.path.join(HERE, name)
    try:
        p = subprocess.run([sys.executable, path] + list(extra), cwd=HERE, capture_output=True,
                           text=True, timeout=timeout, env=child_env(name), stdin=subprocess.DEVNULL)
        out = (p.stdout or "") + (p.stderr or "")
        rc = p.returncode
    except subprocess.TimeoutExpired:
        out, rc = "timed out after %ss" % timeout, 124
    except Exception as exc:  # noqa: BLE001 - one broken proof must not stop the run
        out, rc = "runner error: %s" % exc, 125
    return {"file": name, "rc": rc, "seconds": round(time.time() - started, 1),
            "tail": "\n".join(out.strip().splitlines()[-3:])}


def _git_lines(args):
    try:
        p = subprocess.run(["git"] + args, cwd=os.path.dirname(HERE), capture_output=True, text=True,
                           timeout=120)
        return [x for x in p.stdout.split() if x]
    except Exception:  # noqa: BLE001
        return []


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
    names = {os.path.basename(x) for x in _git_lines(args)}
    if not committed_only and rev != "HEAD":
        names |= {os.path.basename(x) for x in _git_lines(["diff", "--name-only", rev, "HEAD"])}
    if names is None:
        return None
    known = set(candidates())
    picked = [n for n in known if n in names]
    for stem in {os.path.splitext(n)[0] for n in names if n.endswith(".py") and n not in known}:
        for proof in sorted(known):
            if proof in picked:
                continue
            try:
                if re.search(r"\b%s\b" % re.escape(stem), open(os.path.join(HERE, proof)).read()):
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
    ap.add_argument("--changed", nargs="?", const="HEAD", default=None,
                    help="run only the proofs the tree changed (optionally since a revision)")
    ap.add_argument("--quiet", action="store_true",
                    help="say nothing when every proof passes, so a nightly job speaks only on failure")
    ap.add_argument("--card", default="",
                    help="card id for the checks that cannot run without one (see --list)")
    a = ap.parse_args()

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
    results = []
    for name in picked:
        extra = ["--card", a.card] if a.card and name in NEEDS_ARGS else []
        r = run_one(name, a.timeout, extra)
        results.append(r)
        if not a.json and not a.quiet:
            print("%-6s %-40s %6.1fs  %s" % ("PASS" if r["rc"] == 0 else "FAIL", r["file"],
                                             r["seconds"], "" if r["rc"] == 0 else r["tail"][:200]))

    failed = [r for r in results if r["rc"] != 0]
    if a.json:
        print(json.dumps({"ran": len(results), "failed": len(failed), "skipped": skipped,
                          "results": results}, indent=1))
    elif a.quiet and not failed:
        return 0
    else:
        print("\n%d proof(s) ran, %d failed, %d held back (live services)"
              % (len(results), len(failed), len(skipped)))
        for r in failed:
            print("  FAIL %s (exit %d)\n    %s" % (r["file"], r["rc"], r["tail"]))
    if failed:
        print("RUNNER FAIL: %s" % ", ".join(r["file"] for r in failed))
        return 1
    print("RUNNER OK: every proof that ran passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
