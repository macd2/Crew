#!/usr/bin/env python3
"""Every profile that runs the crew must carry the same crew: parity by md5, per shipped file.

The crew is installed as a copy per profile (plugin with its scripts, skills). A copy that drifts means one
role runs different code from the next, and only the copy tells you about it. This compares each file
the package ships against the copy in every profile that has the plugin installed, and reports the
pair count, the mismatches and the missing copies.

Run:  python3 crew_parity_check.py [--package DIR] [--profiles DIR] [--json]
Exit: 0 when every copy matches, 1 on any mismatch or missing copy, 2 when it cannot run.
"""
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402

# The package checkout (CREW_PACKAGE, else crew_card.package_dir); the profiles it was installed into.
PACKAGE = os.environ.get("CREW_PACKAGE") or crew_card.package_dir() or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def release_tree(package=None):
    """The RELEASE checkout's HEAD commit, exported to a temp dir - the comparison target parity uses.

    Parity answers one question: do the homes carry what was released? Comparing against the package working
    tree made every dev edit after a release read as a defect (nightlies of 10-20 and 10-24 went red with no
    code fault). A dirty release working copy is ignored too - HEAD is the release. None when there is no
    release checkout beside the package, and the caller keeps comparing against the package tree.
    """
    base = os.path.dirname(os.path.abspath(package or PACKAGE))
    rel = os.environ.get("CREW_RELEASE") or os.path.join(base, "release")
    if not os.path.exists(os.path.join(rel, ".git")):
        return None
    # The target is GitHub's latest main (owner, 2026-11-09), never a local commit: a release commit that was
    # made here but not pushed is not a release. Fetch first; with no reachable origin/main, HEAD is the fallback.
    ref = os.environ.get("CREW_RELEASE_REF") or "origin/main"
    try:
        subprocess.run(["git", "-C", rel, "fetch", "-q", "origin", "main"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        pass                                              # offline: the last fetched origin/main still answers
    if subprocess.run(["git", "-C", rel, "rev-parse", "--verify", "-q", ref], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL).returncode != 0:
        ref = "HEAD"
    try:
        sha = subprocess.check_output(["git", "-C", rel, "rev-parse", ref], text=True,
                                      stderr=subprocess.DEVNULL).strip()
        tar = subprocess.check_output(["git", "-C", rel, "archive", "--format=tar", ref],
                                      stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        return None
    out = os.path.join(tempfile.gettempdir(), "crew-release-%s" % sha[:12])
    if not os.path.isfile(os.path.join(out, "plugin.yaml")):
        os.makedirs(out, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(tar)) as tf:
            tf.extractall(out)
    return out if os.path.isfile(os.path.join(out, "plugin.yaml")) else None


PROFILES = os.path.join(crew_card.default_home(), "profiles")
# Where each shipped file lands inside a profile, read from the installer so the two can never
# disagree about what "installed" means.
def shipped_files(package, mod=None):
    # `mod` is the installer module when the installer itself asks (install.py checks parity after an install).
    if mod is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("crew_install", os.path.join(package, "install.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    out = []
    # PLUGIN_FILES carries the scripts too (plugins/crew/scripts/...): nothing crew runs lives in <profile>/scripts.
    for rel in getattr(mod, "PLUGIN_FILES", []):
        out.append((rel, "plugins/crew/" + rel))
    for rel in getattr(mod, "ROLE_FILES", []):
        out.append(("roles/" + rel, "roles/crew/" + rel))
    # The role skills a profile loads by name live in its skills/crew/ (the only skills dir a slim role
    # profile keeps), a second copy next to the plugin's own.
    for name in getattr(mod, "skill_names", lambda: [])():
        out.append(("skills/%s/SKILL.md" % name, "skills/crew/%s/SKILL.md" % name))
    return out


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def installed_profiles(profiles):
    out = []
    for name in sorted(os.listdir(profiles)):
        root = os.path.join(profiles, name)
        if os.path.isfile(os.path.join(root, "plugins", "crew", "__init__.py")):
            out.append((name, root))
    return out


def compare(package, profiles, skip=(), mod=None):
    """Every shipped file against its copy in each (name, root) profile: {pairs, mismatches, missing, skipped, detail}."""
    pairs = mismatches = missing = skipped = 0
    detail = []
    for rel, target in shipped_files(package, mod):
        src = os.path.join(package, rel)
        if not os.path.isfile(src):
            missing += 1
            detail.append({"file": rel, "problem": "not in the package"})
            continue
        want = md5(src)
        for name, root in profiles:
            copy = os.path.join(root, target)
            if any(rel.endswith(sk) for sk in skip):
                skipped += 1
                continue
            if not os.path.isfile(copy):
                missing += 1
                detail.append({"file": rel, "profile": name, "problem": "copy missing"})
                continue
            pairs += 1
            got = md5(copy)
            if got != want:
                mismatches += 1
                detail.append({"file": rel, "profile": name, "problem": "md5 differs",
                               "package": want, "copy": got})
    return {"pairs": pairs, "mismatches": mismatches, "missing": missing, "skipped": skipped, "detail": detail}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default=None,
                    help="the tree to compare against (default: the release checkout's HEAD, else the package)")
    ap.add_argument("--profiles", default=PROFILES)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skip", nargs="*", default=[],
                    help="files to leave out of the comparison (retired proofs)")
    a = ap.parse_args()

    if not a.package:
        a.package = release_tree() or PACKAGE
        print("comparing against %s" % (a.package,), file=sys.stderr)

    if not os.path.isdir(a.package) or not os.path.isdir(a.profiles):
        print("cannot read the package (%s) or the profiles (%s)" % (a.package, a.profiles))
        return 2
    # A plugin copy is not a package checkout: it ships no roles/ and no installer, so comparing a whole install
    # against it reports role files as "missing" and fails with nothing wrong on the box. Say what is missing and
    # stop (2), instead of a red that reads like drift.
    if not os.path.isdir(os.path.join(a.package, "roles")):
        print("%s holds no roles/ - that is a plugin copy, not the crew package; point --package at the "
              "installer's checkout" % a.package, file=sys.stderr)
        return 2

    profiles = installed_profiles(a.profiles)
    if not profiles:
        print("no profile has the crew plugin installed under %s" % a.profiles)
        return 2

    r = compare(a.package, profiles, a.skip)
    pairs, mismatches, missing, skipped, detail = (r["pairs"], r["mismatches"], r["missing"], r["skipped"],
                                                   r["detail"])
    if a.json:
        print(json.dumps({"package": a.package, "profiles": [n for n, _r in profiles],
                          "pairs": pairs, "mismatches": mismatches, "missing": missing,
                          "skipped": skipped, "detail": detail}, indent=1))
    else:
        for d in detail:
            print("  %-34s %-18s %s" % (d["file"], d.get("profile", "-"), d["problem"]))
        print("%d profile(s), %d pair(s) compared, %d mismatch(es), %d missing, %d retired skipped"
              % (len(profiles), pairs, mismatches, missing, skipped))
    if mismatches or missing:
        print("PARITY FAIL: %d mismatch(es), %d missing copy(ies) - run install.py again"
              % (mismatches, missing))
        return 1
    print("PARITY OK: every profile carries the package's crew, md5 for md5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
