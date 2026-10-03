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
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402

# The package checkout (CREW_PACKAGE, else crew_card.package_dir); the profiles it was installed into.
PACKAGE = os.environ.get("CREW_PACKAGE") or crew_card.package_dir() or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES = os.path.join(os.path.expanduser("~/.hermes"), "profiles")
# Where each shipped file lands inside a profile, read from the installer so the two can never
# disagree about what "installed" means.
def shipped_files(package):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default=PACKAGE)
    ap.add_argument("--profiles", default=PROFILES)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skip", nargs="*", default=[],
                    help="files to leave out of the comparison (retired proofs)")
    a = ap.parse_args()

    if not os.path.isdir(a.package) or not os.path.isdir(a.profiles):
        print("cannot read the package (%s) or the profiles (%s)" % (a.package, a.profiles))
        return 2
    profiles = installed_profiles(a.profiles)
    if not profiles:
        print("no profile has the crew plugin installed under %s" % a.profiles)
        return 2

    pairs = mismatches = missing = skipped = 0
    detail = []
    for rel, target in shipped_files(a.package):
        src = os.path.join(a.package, rel)
        if not os.path.isfile(src):
            missing += 1
            detail.append({"file": rel, "problem": "not in the package"})
            continue
        want = md5(src)
        for name, root in profiles:
            copy = os.path.join(root, target)
            if any(rel.endswith(sk) for sk in a.skip):
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
