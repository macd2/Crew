#!/usr/bin/env python3
"""Proof that the crew role profiles carry no usable Slack at all.

Done when every crew role profile has Slack off - in the installed profile and in the template the
installer provisions it from, so a re-provision does not bring it back - the config the gateway loads
for it is structurally sound (an unparseable config silently discards the off switch, so the role
would start a second Slack on crew-content's token), and the running gateway serves no Slack for a
role profile.

Checks (stdlib only, no network):
  1. every templates/profiles/<role>/settings.conf disables Slack (platforms.slack.enabled = false
     or accounts.slack = []).
  2. every installed crew-<role> config.yaml shows Slack off: it names no slack account AND carries
     the explicit `platforms.slack.enabled: false` that beats an inherited SLACK_* credential.
  3. every installed crew-<role> config.yaml is structurally valid: no mapping key appears twice
     under the same parent. A duplicate key is the failure mode that matters - Hermes refuses the
     whole file and keeps running on the settings it had, so the off switch never reaches the
     gateway and the role's Slack comes back from the inherited token.
  4. gateway_state.json carries no crew-<role>:slack platform that the running gateway actually
     started (any state other than the refusal 'fatal'). Records of an earlier config state stay in
     this file until the gateway restarts, so they are reported as history rather than as a start.
  5. hermes-gateway.service is active.

Exit 0 = every check passed. Non-zero = it did not, and the failing check is printed.

Overrides for the proofs' own probe data (copies of profiles/ and the package):
  CREW_PKG, CREW_PROFILES_DIR, CREW_GATEWAY_STATE.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402 - the owner profile, the base home and the package checkout
PKG = crew_card.package_dir() or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES = os.environ.get("CREW_PROFILES_DIR") or os.path.join(crew_card.base_home(), "profiles")
ROLES = ("coordinator", "worker", "verifier")
KEEPS_SLACK = "crew-content"          # holds the only Slack credential; out of scope, must not change
STATE_FILE = os.environ.get("CREW_GATEWAY_STATE") or os.path.join(crew_card.base_home(), "gateway_state.json")
SERVICE = "hermes-gateway.service"
FAILURES = []


def check(name, ok, detail=""):
    print("%-58s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + detail) if detail else ""))
    if not ok:
        FAILURES.append(name)
    return ok


def run(argv):
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    return (proc.stdout or "") + (proc.stderr or "")


def dotted_value(text, path):
    """Effective inline value of a dotted key in a config.yaml (2 spaces per level).

    Returns the value text ('false', '[]'), None when the key is absent, or '' when the key is a
    block whose value lives on deeper lines.
    """
    lines = text.splitlines()
    start, end = 0, len(lines)
    value = None
    for depth, part in enumerate(path):
        pat = re.compile(r"^%s%s:[ \t]*(.*)$" % (" " * (2 * depth), re.escape(part)))
        hit = next((i for i in range(start, end) if pat.match(lines[i])), None)
        if hit is None:
            return None
        value = pat.match(lines[hit]).group(1).strip()
        if value:
            return value if depth == len(path) - 1 else None
        j = hit + 1
        while j < end and (not lines[j].strip() or lines[j].startswith(" " * (2 * depth + 1))):
            j += 1
        start, end = hit + 1, j
    return value


def duplicate_keys(text):
    """[(line, key)] for a mapping key repeated under the same parent - YAML forbids it, and Hermes
    throws the whole file away when it sees one. Sequence items are separate instances, so the
    repeated `matcher:`/`command:` keys inside a hook list are not duplicates."""
    stack = []      # [(indent, instance label)] of enclosing mappings/sequence items
    seen = {}       # (parent path, indent) -> {key: first line}
    dups = []
    for n, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        body = raw.strip()
        if body.startswith("- "):
            # A sequence item opens a new instance: nothing above it can own the keys below.
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack.append((indent, "item@%d" % n))
            body = body[2:].strip()
            if not body:
                continue
            indent += 2
        m = re.match(r"([A-Za-z_][A-Za-z0-9_.-]*):(\s|$)", body)
        if not m:
            continue
        key = m.group(1)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = ".".join(label for _i, label in stack)
        bucket = seen.setdefault((parent, indent), {})
        if key in bucket:
            dups.append((n, key, bucket[key]))
        else:
            bucket[key] = n
        stack.append((indent, key))
    return dups


def gateway_identity():
    """(pid, start_time) of the gateway that is running now; (0, None) when it is not."""
    try:
        pid = int(run(["systemctl", "--user", "show", SERVICE, "-p", "MainPID", "--value"]).strip())
    except ValueError:
        return 0, None
    if not pid:
        return 0, None
    try:
        # /proc/<pid>/stat field 22 (starttime) is what the gateway stamps as writer_start_time, so a
        # recycled pid cannot pass for the process that is running now.
        with open("/proc/%d/stat" % pid, encoding="utf-8") as fh:
            fields = fh.read().rsplit(") ", 1)[1].split()
        return pid, int(fields[19])
    except (OSError, IndexError, ValueError):
        return pid, None


def main():
    for role in ROLES:
        path = os.path.join(PKG, "templates", "profiles", role, "settings.conf")
        if not os.path.exists(path):
            check("template settings.conf exists for %s" % role, False, path)
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        off = (re.search(r"(?mi)^\s*platforms\.slack\.enabled\s*=\s*false\s*$", text)
               or re.search(r"(?mi)^\s*accounts\.slack\s*=\s*\[\s*\]\s*$", text))
        check("template %s disables Slack" % role, bool(off))

    # the role profiles the installer creates: one per template, not every crew-* folder on disk (a retired
    # role can leave an empty folder behind)
    roles = sorted(os.listdir(os.path.join(PKG, "templates", "profiles")))
    profiles = ["crew-%s" % r for r in roles]
    missing = [n for n in profiles if not os.path.isdir(os.path.join(PROFILES, n))]
    check("every role profile exists (%d, one per template)" % len(profiles), not missing, ", ".join(missing) or "all")
    for name in profiles:
        cfg = os.path.join(PROFILES, name, "config.yaml")
        if not os.path.exists(cfg):
            check("%s has a config.yaml" % name, False, cfg)
            continue
        with open(cfg, encoding="utf-8") as fh:
            text = fh.read()
        # The account list is what the gateway reads to start a platform; a profile that names no
        # Slack account cannot start Slack, whatever the platform toggle says. The explicit off
        # matters on top of that: it is the only thing that beats a SLACK_* credential the profile
        # inherited from the profile it was cloned from.
        if name == KEEPS_SLACK:
            check("%s keeps its own Slack, untouched" % name, "hermes-slack" in text)
        else:
            check("%s names no Slack account" % name, "hermes-slack" not in text)
            check("%s sets platforms.slack.enabled = false" % name,
                  dotted_value(text, ["platforms", "slack", "enabled"]) == "false")
        dups = duplicate_keys(text)
        check("%s config.yaml has no duplicate mapping key" % name, not dups,
              ", ".join("line %d: %s (first at %d)" % d for d in dups[:3]))

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as fh:
            state = json.load(fh)
        # gateway_state.json keeps the last record of every platform key it has ever written, and the
        # gateway only drops a `<profile>:<platform>` key when it restarts or the profile is unserved:
        # a record written mid-life survives the config that produced it. So what counts is whether
        # the running gateway STARTED that Slack, not how old the record is - a refusal ('fatal',
        # duplicate_credential) is the gateway declining to start it, and is reported as history.
        pid, start_time = gateway_identity()
        started, history = [], []
        for k, v in (state.get("platforms") or {}).items():
            if not (k.startswith("crew-") and ":slack" in k) or not isinstance(v, dict):
                continue
            mine = ((pid and v.get("writer_pid") == pid)
                    or (start_time is not None and v.get("writer_start_time") == start_time))
            if not mine:
                history.append("%s=%s (previous gateway pid %s)" % (k, v.get("state"), v.get("writer_pid")))
            elif (v.get("state") or "") == "fatal":
                history.append("%s=fatal %s at %s" % (k, v.get("error_code"), v.get("updated_at")))
            else:
                started.append("%s=%s" % (k, v.get("state")))
        check("the running gateway starts no Slack for a crew profile", not started,
              "; ".join(started) or ("not started; refused records from an earlier config state: "
                                     + "; ".join(history[:4]) if history else "no crew slack record"))
    else:
        check("gateway_state.json is readable", False, STATE_FILE)

    active = run(["systemctl", "--user", "is-active", SERVICE]).strip()
    check("%s is active" % SERVICE, active == "active", active)

    if FAILURES:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILURES), "; ".join(FAILURES)))
        return 1
    print("PROOF OK: Slack is off in the role templates and in every crew profile config the gateway "
          "loads, no crew profile runs a Slack adapter, and the gateway is up")
    return 0


if __name__ == "__main__":
    sys.exit(main())
