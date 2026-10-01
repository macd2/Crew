#!/usr/bin/env python3
"""Resolve the tool list a profile's kanban worker really gets, and flag write/send tools.

Mirrors the dispatcher: the assignee's CLI toolsets come from
hermes_cli.tools_config._get_platform_tools(config, "cli") (passed to the worker as
--toolsets), agent.disabled_toolsets is subtracted last (model_tools._select_tool_names),
and the kanban lifecycle toolset is added for dispatcher-spawned workers.

Usage:
  crew_tools_audit.py --profile NAME [--forbid write_file,patch,...] [--json]

Exit 0 when none of the forbidden tools is in the resolved list, 1 when one is, 2 on error.
The Hermes source tree is found from $HERMES_AGENT_SRC, else from `hermes --print-runtime-command`.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_FORBID = [
    "write_file", "patch", "skill_manage", "memory", "cronjob_manage", "delegate_task",
    "execute_code", "send_message", "text_to_speech", "image_generate", "computer_use",
    "zoho_mail_send", "zoho_task_create", "zoho_event_create", "browser_type", "browser_click",
    "browser_vault_fill", "ha_call_service",
]
# Any MCP tool (mcp_*/mcp__*) and any name containing one of these words counts as a send.
SEND_WORDS = ("send", "post_", "publish", "create_email_campaign", "import_contacts")


def hermes_src():
    env = os.environ.get("HERMES_AGENT_SRC")
    if env and os.path.isdir(env):
        return env
    exe = shutil.which("hermes") or os.path.expanduser("~/.local/bin/hermes")
    try:
        out = subprocess.run([exe, "--print-runtime-command"], capture_output=True, text=True,
                             timeout=60).stdout
        m = re.search(r"sys\.path\.insert\(0, '([^']+)'\)", out)
        if m and os.path.isdir(m.group(1)):
            return m.group(1)
    except Exception:
        pass
    guess = os.path.expanduser("~/.hermes/hermes-agent")
    return guess if os.path.isdir(guess) else None


def profile_home(name):
    base = Path.home() / ".hermes"
    return str(base if name in ("", "default") else base / "profiles" / name)


def resolve(profile):
    home = profile_home(profile)
    if not os.path.isdir(home):
        raise SystemExit("no such profile home: %s" % home)
    os.environ["HERMES_HOME"] = home
    # Resolve as a dispatcher-spawned worker would see it.
    os.environ["HERMES_KANBAN_TASK"] = os.environ.get("CREW_AUDIT_TASK", "t_audit")
    src = hermes_src()
    if not src:
        raise SystemExit("hermes source tree not found; set HERMES_AGENT_SRC")
    sys.path.insert(0, src)
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from hermes_cli.config import load_config
        from hermes_cli.tools_config import _get_platform_tools
        import model_tools
        cfg = load_config()
        toolsets = sorted(_get_platform_tools(cfg, "cli"))
        disabled = (cfg.get("agent") or {}).get("disabled_toolsets") or []
        if isinstance(disabled, str):
            disabled = [d.strip() for d in disabled.strip("[]").replace("'", "").split(",") if d.strip()]
        names = set(model_tools._select_tool_names(list(toolsets), list(disabled), True))
        # The dispatcher adds kanban for its own workers; _select_tool_names only does so when
        # it can prove dispatcher ownership, so add it here explicitly.
        from toolsets import resolve_toolset
        names |= set(resolve_toolset("kanban"))
    return home, toolsets, disabled, sorted(names)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--profile", required=True)
    ap.add_argument("--forbid", default=",".join(DEFAULT_FORBID))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        home, toolsets, disabled, names = resolve(args.profile)
    except SystemExit as exc:
        print("audit error: %s" % exc)
        return 2
    except Exception as exc:
        print("audit error: %s: %s" % (type(exc).__name__, exc))
        return 2
    forbid = [f.strip() for f in args.forbid.split(",") if f.strip()]
    bad = sorted(set(n for n in names if n in forbid
                     or n.startswith("mcp_")
                     or any(w in n for w in SEND_WORDS)))
    report = {"profile": args.profile, "home": home, "toolsets": toolsets,
              "disabled_toolsets": disabled, "tools": names, "forbidden_present": bad}
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        print("profile: %s" % args.profile)
        print("toolsets: %s" % ", ".join(toolsets))
        print("disabled_toolsets: %s" % ", ".join(disabled))
        print("tools (%d): %s" % (len(names), ", ".join(names)))
        print("forbidden present: %s" % (", ".join(bad) if bad else "none"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
