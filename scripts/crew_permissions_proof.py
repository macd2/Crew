#!/usr/bin/env python3
"""Proof for the installer's shell-hook consent step (install.py step_permissions).

Why this exists: the runtime fires a shell hook only when its (event, command) pair sits in that
home's shell-hooks-allowlist.json. Without the entry it logs "not allowlisted - skipped" and the gate
simply never runs - the home still looks installed, and nothing goes red. The installer does not
approve hooks (consent is Hermes's own prompt); it reads the allowlist and reports what is missing.
This proof pins that report, and that the installer never writes the allowlist.

The three checks mirror the runtime's own doctor (hermes_cli/hooks.py `_doctor_one`: exec bit,
allowlist entry, mtime drift), so a home this proof calls healthy is a home `hermes hooks doctor`
calls healthy.

Checks:
  1-7  permission_problems, one fixture per failure it must catch and one that must stay green
  8    an allowlist entry in the runtime's own shape passes the gate
  9    the installer has no approval writer at all
  10   step_permissions reports the fault with Hermes's own approval command, in --check and in apply,
       and never writes the allowlist
  11   the live crew homes: every declared hook approved, role settings in place
  12   install.py --check runs the gate (the step is wired into the installer)
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crew_card  # noqa: E402 - the owner profile
INSTALL = os.path.join(crew_card.package_dir() or os.path.dirname(HERE), "install.py")

spec = importlib.util.spec_from_file_location("crew_install_under_test", INSTALL)
CI = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CI)

CHECKS = 0
FAILS = []


def check(name, ok, detail=""):
    global CHECKS
    CHECKS += 1
    print("%-70s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + str(detail)[:110]) if detail else ""))
    if not ok:
        FAILS.append(name)
    return ok


def write_approval(home, event, script):
    """What Hermes itself records when the owner confirms a hook (agent/shell_hooks.py): the fixture's stand-in
    for the owner's consent. The installer has no such writer."""
    path = os.path.join(home, CI.ALLOWLIST_NAME)
    data = json.load(open(path)) if os.path.exists(path) else {"approvals": []}
    data["approvals"] = [e for e in data["approvals"] if (e["event"], e["command"]) != (event, script)]
    data["approvals"].append({"event": event, "command": script, "approved_at": CI._iso(time.time()),
                              "script_mtime_at_approval": CI._mtime_iso(script)})
    with open(path, "w") as fh:
        json.dump(data, fh)
    os.chmod(path, 0o600)


def fixture(root, name, pairs, approve=True, mode=0o600, drift=False, executable=True, missing=False):
    """A home with config.yaml declaring `pairs`, and the hook scripts those pairs name."""
    home = os.path.join(root, name)
    os.makedirs(os.path.join(home, "hooks"), exist_ok=True)
    lines = ["hooks:"]
    for event, script in pairs:
        lines += ["  %s:" % event, "    - matcher: terminal", "      command: %s" % script,
                  "      timeout: 10"]
    lines += ["  output_spill:", "    max_chars: 19000", "hooks_auto_accept: false"]
    with open(os.path.join(home, "config.yaml"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    for _event, script in pairs:
        if missing:
            continue
        with open(script, "w") as fh:
            fh.write("#!/usr/bin/env python3\nprint('{}')\n")
        os.chmod(script, 0o755 if executable else 0o644)
        if drift:
            old = time.time() - 86400
            os.utime(script, (old, old))
    if approve:
        for event, script in pairs:
            write_approval(home, event, script)
        if drift:                      # the script changed after it was approved
            for _event, script in pairs:
                os.utime(script, None)
        path = os.path.join(home, CI.ALLOWLIST_NAME)
        os.chmod(path, mode)
    return home


def pair(home, name="gate.py"):
    return os.path.join(home, "hooks", name)


def main():
    root = tempfile.mkdtemp(prefix="crew-perm-proof-")
    try:
        # 1: no consent record at all
        a = fixture(root, "no_record", [("pre_tool_call", pair(os.path.join(root, "no_record")))],
                    approve=False)
        f = CI.permission_problems(a)
        check("a home with no consent record is red", bool(f) and "no consent record" in f[0], f)

        # 2: a declared hook with no approval - the silent-skip case
        b_home = os.path.join(root, "partial")
        b = fixture(root, "partial", [("pre_tool_call", os.path.join(b_home, "hooks", "one.py"))],
                    approve=False)
        write_approval(b, "post_tool_call", os.path.join(b_home, "hooks", "one.py"))
        f = CI.permission_problems(b)
        check("a declared hook that is not approved is red",
              any("declared but not approved" in x and "pre_tool_call" in x for x in f), f)

        # 3: the record matches config.yaml
        c_home = os.path.join(root, "healthy")
        c = fixture(root, "healthy", [("pre_tool_call", os.path.join(c_home, "hooks", "one.py")),
                                      ("pre_llm_call", os.path.join(c_home, "hooks", "two.py"))])
        check("a complete, fresh record is green", CI.permission_problems(c) == [], CI.permission_problems(c))

        # 4: the script changed since approval
        d = fixture(root, "drift", [("pre_tool_call", pair(os.path.join(root, "drift")))], drift=True)
        f = CI.permission_problems(d)
        check("an approval older than its script is red",
              any("approval drift" in x for x in f), f)

        # 5: the record is world/group readable
        e = fixture(root, "mode", [("pre_tool_call", pair(os.path.join(root, "mode")))], mode=0o644)
        f = CI.permission_problems(e)
        check("a consent record that is not 0600 is red",
              any("mode 644" in x for x in f), f)

        # 6: the script is not executable
        g = fixture(root, "noexec", [("pre_tool_call", pair(os.path.join(root, "noexec")))],
                    executable=False)
        f = CI.permission_problems(g)
        check("a hook script without its exec bit is red",
              any("not executable" in x for x in f), f)

        # 7: the script is gone
        h = fixture(root, "gone", [("pre_tool_call", pair(os.path.join(root, "gone")))], missing=True)
        f = CI.permission_problems(h)
        check("a hook script that is missing is red", any("missing" in x for x in f), f)

        # 8: an entry in the runtime's shape passes the gate
        i_home = os.path.join(root, "written")
        i = fixture(root, "written", [("pre_tool_call", os.path.join(i_home, "hooks", "one.py"))],
                    approve=False)
        write_approval(i, "pre_tool_call", os.path.join(i_home, "hooks", "one.py"))
        entry = json.load(open(os.path.join(i, CI.ALLOWLIST_NAME)))["approvals"][0]
        check("an entry in the runtime's own shape passes the gate",
              CI.permission_problems(i) == [] and sorted(entry) == ["approved_at", "command", "event",
                                                                    "script_mtime_at_approval"],
              CI.permission_problems(i))

        # 9: the installer cannot approve
        check("install.py has no approval writer and sets no HERMES_ACCEPT_HOOKS",
              not hasattr(CI, "_approve") and "HERMES_ACCEPT_HOOKS" not in open(INSTALL).read())

        # 10: the step reports, with Hermes's own flow, and writes nothing
        j_home = os.path.join(root, "stepped")
        j = fixture(root, "stepped", [("pre_tool_call", os.path.join(j_home, "hooks", "one.py"))],
                    approve=False)
        real_plans = CI._role_plans
        CI._role_plans = lambda prefix: []
        try:
            for apply in (False, True):
                status, detail = CI.step_permissions(j, "stepped", "x-", apply)
                check("step_permissions (apply=%s) is FAILED, names `hermes ... chat`, writes nothing" % apply,
                      status == "FAILED" and "hermes -p stepped chat" in detail
                      and "hooks doctor" in detail and not os.path.exists(os.path.join(j, CI.ALLOWLIST_NAME)),
                      detail)
            write_approval(j, "pre_tool_call", os.path.join(j_home, "hooks", "one.py"))
            status, detail = CI.step_permissions(j, "stepped", "x-", False)
            check("once the owner approved it the step reads OK", status == "OK", detail)
        finally:
            CI._role_plans = real_plans

        # 11: the live crew homes
        homes = [("", CI.resolve_profile_home(crew_card.owner_profile()))]
        homes += [(role, home) for role, _n, home, _tpl in CI._role_plans("crew-") if os.path.isdir(home)]
        bad_hooks, bad_settings = {}, {}
        for role, home in homes:
            problems = CI.permission_problems(home)
            if problems:
                bad_hooks[os.path.basename(home)] = problems
            if role:
                tpl = os.path.join(str(CI.SRC_DIR), "templates", "profiles", role)
                settings = CI.settings_problems(os.path.basename(home), role, tpl)
                if settings:
                    bad_settings[os.path.basename(home)] = settings
        check("every live crew home has all its declared hooks approved", not bad_hooks, bad_hooks)
        check("every live crew home carries its role settings", not bad_settings, bad_settings)
        # the owner profile plus one home per role the installer creates (templates/profiles/<role>)
        want = 1 + len(CI._role_plans("crew-"))
        check("live homes cover the installing profile and all role profiles", len(homes) == want,
              [os.path.basename(h) for _r, h in homes])

        # 12: the installer runs the gate
        args = type("Args", (), {"profile_prefix": "crew-", "no_service": True, "no_cron": True,
                                 "no_profiles": True, "graph_port": CI.GRAPH_PORT,
                                 "https_port": 8445, "spill_cap": False, "chat_kanban": False,
                                 "telegram_menu": False, "nightly_proofs": False,
                                 "proofs_deliver": CI.CRON_PROOFS_DELIVER})()
        steps = [name for name, _fn in CI._steps(CI.resolve_profile_home(crew_card.owner_profile()),
                                                 crew_card.owner_profile(), args)]
        check("install.py wires the permissions step into its step list", "permissions" in steps, steps)
        r = subprocess.run([sys.executable, INSTALL, "--check", "--no-service", "--no-cron",
                            "--no-profiles", "--profile", crew_card.owner_profile()],
                           capture_output=True, text=True, timeout=300)
        out = r.stdout + r.stderr
        # another step may legitimately want to copy a file this proof just created; the gate's own
        # row is what this check owns
        check("install.py --check reports no permission fault once installed",
              "would change: permissions" not in out, out.strip().splitlines()[-1:])
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("\n%s: %d check(s), %d failed" % (os.path.basename(__file__), CHECKS, len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
