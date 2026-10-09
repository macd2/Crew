#!/usr/bin/env python3
"""Installer for the crew plugin package (self-contained, idempotent, stdlib only).

Usage:
  python3 install.py [--profile NAME] [--check] [--no-service] [--no-cron] [--no-profiles]
                     [--nightly-proofs [--proofs-deliver TARGET]]
                     [--chat-kanban] [--telegram-menu] [--spill-cap]

The installer never prompts. What it does by default: copies the plugin (scripts included) into the
profile, the role profiles, the roles file, the local dashboard unit, the config keys crew reads. Everything
that reaches beyond crew's own files is a flag: --nightly-proofs (cron),
--chat-kanban (kanban toolset on zulip/telegram), --telegram-menu (command menu order), --spill-cap
(hooks.output_spill.max_chars on the installing profile). It never approves a shell hook: consent is
Hermes's own (the TTY prompt), and the installer only reports what is still missing.

--check changes nothing: it prints exactly what would change and exits 0 when the
package is complete, 1 when something is missing or a role's first-call prompt is over
roles.json prompt_budget_tokens (it also prints each role's skills size and measured first call).
Every step is idempotent and prints
OK / CHANGED / SKIP plus what it did. Running twice is safe.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent          # the libs/crew directory (source of truth)
UNIT_GRAPH_NAME = "crew-graph-http.service"
GRAPH_PORT = 8799
UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
# Jobs an earlier install registered that the coordinator loop made redundant: the install removes them.
# self-heal ran crew_heal.py every 5 minutes (now a library the loop calls); the weekly observer was a
# role of its own whose rule proposals nobody read (removed with the owner surface, spec step 9).
OLD_CRON_NAMES = ("crew self-heal", "Crew observer (weekly)")
# the proofs are the acceptance evidence for the plugin: with --nightly-proofs they run every night, and the
# job speaks only when one of them fails. Delivery is the local cron output unless --proofs-deliver names a target.
CRON_PROOFS_NAME = "Crew proofs (nightly)"
CRON_PROOFS_SCHEDULE = "0 3 * * *"
CRON_PROOFS_DELIVER = "local"
# Hermes cron only runs a script that sits inside HERMES_HOME/scripts, and runs a .py one with its own interpreter
# (the one the proofs need; a .sh one runs under bash and a bare python3 lacks Hermes's dependencies). So the one
# file crew keeps there is this Python shim; the proofs themselves run from the plugin's own copy. The name must
# differ from crew_proofs.py, which is in SCRIPT_FILES and which step_scripts removes from <profile>/scripts.
PROOFS_SHIM = "crew_proofs_nightly.py"
OLD_PROOFS_SHIM = "crew_proofs.sh"      # the earlier shim; step_proofs_cron migrates a job off it, then deletes it
PROOFS_SHIM_TEXT = (
    "# Written by the crew installer (--nightly-proofs). Hermes cron runs scripts from HERMES_HOME/scripts only\n"
    "# and runs a .py one with whatever interpreter Hermes itself runs under (on the package-manager layout a bare\n"
    "# one that cannot import Hermes), so this hands over to the plugin's own copy of the proof runner, which\n"
    "# switches to the Hermes python itself.\n"
    "import os\n"
    "import sys\n"
    "\n"
    "runner = os.path.join(os.path.dirname(os.path.abspath(__file__)), \"..\", \"plugins\", \"crew\", \"scripts\",\n"
    "                      \"crew_proofs.py\")\n"
    "os.execv(sys.executable, [sys.executable, runner, \"--quiet\"] + sys.argv[1:])\n")

# Everything in the package's scripts/ ships: one list derived from the tree, so a new script can never be left
# out of the installed copy (crew_safety.py once was, and every importer crashed). Bytecode never ships.
SCRIPT_FILES = sorted(str(p.relative_to(SRC_DIR / "scripts")) for p in (SRC_DIR / "scripts").rglob("*")
                      if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
# Scripts the package once shipped and has since deleted.
RETIRED_SCRIPT_FILES = ["crew_follow.py", "crew_follow_proof.py", "crew_observer.py", "crew_observer.sh",
                        "crew_repeat_escalation_proof.py", "crew_triage.py", "crew_unblock.py",
                        "crew_unstale.py", "crew_unstale_proof.py",
                        "crew_dashboard/favicon.png", "kanban_zulip_feed.py", "kanban_zulip_columns.py",
                        "kanban_feed_mute_proof.py", "kanban_feed_mute_live_proof.py",
                        "kanban_move_notice_proof.py", "kanban_overview_dedupe_proof.py",
                        "crew_zulip_route_proof.py"]
# The plugin copy in a profile is the package's plugin files plus its scripts/: everything crew runs is
# loaded from <profile>/plugins/crew/ and never from <profile>/scripts/. `hermes plugins install` clones the
# whole repo into the same place, so the layout is the same in both install modes.
PLUGIN_FILES = (["plugin.yaml", "__init__.py", "skills/crew-verifier/SKILL.md",
                 "skills/crew-role-worker/SKILL.md", "skills/crew-role-content/SKILL.md",
                 "skills/crew/SKILL.md", "skills/crew-diagnose/SKILL.md"]
                + ["scripts/" + rel for rel in SCRIPT_FILES])
# Files the plugin copy once held and the package has since deleted: their presence makes the copy stale.
PLUGIN_RETIRED_FILES = ["scripts/crew_proofs.sh"]
ROLE_FILES = ["roles.json", "briefs/coordinator.md", "briefs/worker.md", "briefs/content.md",
              "briefs/verifier.md"]


def hermes_bin():
    return shutil.which("hermes") or os.path.expanduser("~/.local/bin/hermes")


def python3_bin():
    # systemd ExecStart needs a stable absolute interpreter, not the caller's venv python.
    if os.path.exists("/usr/bin/python3"):
        return "/usr/bin/python3"
    return shutil.which("python3") or "python3"


def resolve_profile_home(name):
    name = (name or "").strip()
    if not name or name == "default":
        return os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes")
    return str(Path.home() / ".hermes" / "profiles" / name)


def profile_flag(name):
    # "default" is named explicitly: with no -p, hermes acts on the *sticky* profile (`hermes profile use`),
    # so a bare `hermes config set` meant for the default home landed in whichever profile was sticky instead.
    name = (name or "").strip()
    return [] if not name else ["-p", name]


def h(profile, *args):
    if args[:2] == ("config", "set"):
        _CFG_CACHE.pop(profile or "", None)   # a write makes the cached reads of that profile stale
    return subprocess.run([hermes_bin(), *profile_flag(profile), *args],
                          capture_output=True, text=True, timeout=240)


_REAL_H = h

# Reads go through Hermes's own `get_config_value` (what `hermes config get` prints), but many keys in ONE process:
# every `hermes ...` launch costs ~4 s (it loads the secrets provider and the plugins), an in-process read ~0.4 s,
# and the installer reads far more than it writes (2026-10-03: --check took ~85 s). Writes stay `hermes config set`.
_CFG_CACHE = {}
_CFG_READER = r"""
import contextlib, io, json, os, sys
sys.path.insert(0, sys.argv[1])
from hermes_cli.config import get_config_value
out = {}
for key in json.loads(sys.argv[2]):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            get_config_value(key)
        out[key] = [0, buf.getvalue()]
    except SystemExit as exc:
        out[key] = [exc.code if isinstance(exc.code, int) else 1, buf.getvalue()]
    except Exception:
        out[key] = [1, ""]
print(json.dumps(out))
"""


def _hermes_python():
    """(python, root) of the Hermes install that can import hermes_cli: the package manager's committed venv,
    else a legacy in-tree venv (crew_card.hermes_python decides); (None, None) when neither exists."""
    scripts = os.path.join(SRC_DIR, "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import crew_card
    root = os.path.dirname(os.path.dirname(os.path.realpath(hermes_bin())))
    for cand in (os.path.join(Path.home(), ".hermes", "hermes-agent"), root):
        py = crew_card.hermes_python(cand)
        if py:
            return py, cand
    return None, None


def _cfg_raw_many(profile, keys):
    """{key: (rc, stdout)} as `hermes config get` would answer, read in one in-process call (cached per profile);
    falls back to one CLI call per key when Hermes's python cannot be found or the reader fails."""
    if h is not _REAL_H:   # a replaced runner (a test's fake, a wrapper) owns every read, uncached
        return {k: (lambda r: (r.returncode, r.stdout))(h(profile, "config", "get", k)) for k in keys}
    cache = _CFG_CACHE.setdefault(profile or "", {})
    want = [k for k in keys if k not in cache]
    if want:
        py, root = _hermes_python()
        got = None
        if py:
            env = dict(os.environ, HERMES_HOME=resolve_profile_home(profile))
            try:
                r = subprocess.run([py, "-c", _CFG_READER, root, json.dumps(want)], capture_output=True,
                                   text=True, timeout=60, env=env)
                got = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else None
            except (OSError, ValueError, subprocess.SubprocessError, IndexError):
                got = None
        for k in want:
            if got is not None and k in got:
                cache[k] = (got[k][0], got[k][1])
            else:
                r = h(profile, "config", "get", k)
                cache[k] = (r.returncode, r.stdout)
    return {k: cache[k] for k in keys}


def _read(path):
    try:
        return Path(path).read_bytes()
    except Exception:
        return None


def _same(src, dst):
    a, b = _read(src), _read(dst)
    return a is not None and a == b


def _tree_ok(src_root, dst_root, rels):
    return all(_same(os.path.join(src_root, r), os.path.join(dst_root, r)) for r in rels)


def _backup_dir(profile_home):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return os.path.join(profile_home, "backups", "crew-%s" % stamp)


def step_plugin(profile_home, apply):
    """The plugin copy of a profile, scripts/ included: every file crew runs is loaded from here."""
    dst = os.path.join(profile_home, "plugins", "crew")
    if os.path.realpath(dst) == os.path.realpath(SRC_DIR):
        return "OK", "plugin crew (this checkout is the plugin dir: `hermes plugins install` mode)"
    if (os.path.isdir(dst) and _tree_ok(SRC_DIR, dst, PLUGIN_FILES)
            and not any(os.path.lexists(os.path.join(dst, r)) for r in PLUGIN_RETIRED_FILES)):
        return "OK", "plugin crew (up to date)"
    if not apply:
        return "CHANGED", "plugin crew -> copy into %s" % dst
    if os.path.exists(dst):
        backup = _backup_dir(profile_home)
        os.makedirs(os.path.dirname(backup), exist_ok=True)
        shutil.move(dst, backup)
    for rel in PLUGIN_FILES:
        d = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(os.path.join(SRC_DIR, rel), d)
    return "CHANGED", "plugin crew copied into %s" % dst


# ----------------------------------------------------------------- stale script copies
# Earlier installs copied ~60 crew scripts into <profile>/scripts/. Everything now runs from the plugin's own
# copy, so those files are dead weight and, worse, a second version of the code that could be picked up by
# accident. The installer removes exactly the files its own lists name, prints each one, and touches
# nothing else in that directory (the owner's own scripts live there too).

def _stale_scripts(dst):
    """Relative names under <profile>/scripts/ that a crew install put there. The nightly shim is not one of them
    (it is not in either list; step_proofs_cron owns it and the old crew_proofs.sh)."""
    return [r for r in SCRIPT_FILES + RETIRED_SCRIPT_FILES if os.path.isfile(os.path.join(dst, r))]


def _write_shim(dst):
    os.makedirs(dst, exist_ok=True)
    path = os.path.join(dst, PROOFS_SHIM)
    if os.path.islink(path):
        os.unlink(path)      # write_text follows a symlink and would overwrite its target
    Path(path).write_text(PROOFS_SHIM_TEXT)
    os.chmod(path, 0o755)


def step_old_shim(profile_home, apply):
    """Remove the old crew_proofs.sh from a profile no proofs job runs in: a role profile, which only ever got a
    copy, or a profile whose job was never registered. A symlink is unlinked, its target never touched."""
    old = os.path.join(profile_home, "scripts", OLD_PROOFS_SHIM)
    if not os.path.lexists(old):
        return "OK", "no old %s" % OLD_PROOFS_SHIM
    if not apply:
        return "CHANGED", "remove " + old
    os.remove(old)
    print("  removed %s" % old)
    return "CHANGED", "removed " + old


def step_scripts(profile_home, apply):
    """Remove the crew script copies an earlier install left in <profile>/scripts/, listing each one."""
    dst = os.path.join(profile_home, "scripts")
    stale = _stale_scripts(dst)
    if not stale:
        return "OK", "no crew script copies in %s (crew runs from plugins/crew/scripts)" % dst
    what = "remove " + ", ".join(stale)
    if not apply:
        return "CHANGED", "scripts in %s: %s" % (dst, what)
    for rel in stale:
        path = os.path.join(dst, rel)
        os.remove(path)
        print("  removed %s" % path)
    for rel in {os.path.dirname(r) for r in stale if os.path.dirname(r)}:
        try:
            os.rmdir(os.path.join(dst, rel))     # only when nothing else is in it
            print("  removed empty dir %s" % os.path.join(dst, rel))
        except OSError:
            pass
    return "CHANGED", "scripts in %s: %s" % (dst, what)


def step_roles(profile_home, apply):
    src = os.path.join(SRC_DIR, "roles")
    dst = os.path.join(profile_home, "roles", "crew")
    if os.path.isdir(dst) and _tree_ok(src, dst, ROLE_FILES):
        return "OK", "roles (up to date)"
    if not apply:
        return "CHANGED", "roles -> copy into %s" % dst
    os.makedirs(dst, exist_ok=True)
    for rel in ROLE_FILES:
        d = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(os.path.join(src, rel), d)
    return "CHANGED", "roles copied into %s" % dst


def step_crew_dirs(profile_home, apply):
    """$HERMES_HOME/crew/ and crew/verdicts/: where the verdict tool and the coordinator append jsonl."""
    need = [d for d in (os.path.join(profile_home, "crew"), os.path.join(profile_home, "crew", "verdicts"))
            if not os.path.isdir(d)]
    if not need:
        return "OK", "crew data dirs (crew/, crew/verdicts/)"
    if not apply:
        return "CHANGED", "create " + ", ".join(need)
    for d in need:
        os.makedirs(d, exist_ok=True)
    return "CHANGED", "created " + ", ".join(need)


OWNER_RECORD = os.path.join(str(Path.home() / ".hermes"), "crew", "owner.json")


def _owner_record():
    try:
        with open(OWNER_RECORD) as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _owner_record_set(**keys):
    data = _owner_record()
    data.update(keys)
    os.makedirs(os.path.dirname(OWNER_RECORD), exist_ok=True)
    with open(OWNER_RECORD, "w") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)


def step_owner(profile, apply, force=False):
    """<base home>/crew/owner.json: the profile crew is installed into (the owner's chat profile) and, after
    --publish, the dashboard's public URL. The dashboard, crew_notify and the proofs read it through
    crew_card.owner_profile() / dashboard_url(), so no script names a profile or a host.
    The first install records its profile; installing into another profile later never moves the owner
    silently - `--owner` does."""
    name = (profile or "").strip() or "default"
    rec = _owner_record()
    if rec.get("profile") and rec.get("profile") != name and not force:
        return "OK", "owner stays %s (pass --owner to make %s the owner)" % (rec["profile"], name)
    if rec.get("profile") == name and rec.get("package") == str(SRC_DIR):
        return "OK", "owner profile recorded (%s)" % name
    if not apply:
        return "CHANGED", "record owner profile %s and package %s -> %s" % (name, SRC_DIR, OWNER_RECORD)
    _owner_record_set(profile=name, package=str(SRC_DIR))
    return "CHANGED", "owner profile %s and package recorded in %s" % (name, OWNER_RECORD)


def step_other_copies(profile_home, prefix, apply):
    """Every other profile that already has crew gets this version too (owner, 2026-10-01: "only the latest
    released version in every profile"): plugin (scripts included), skills, roles file and the removal of old script
    copies, nothing else - its config, services and ownership are left alone. Only a profile that already has
    plugins/crew is touched; every change is printed. Role profiles are kept current by the profiles step."""
    base = str(Path.home() / ".hermes")
    roles = {home for _r, _n, home, _t in _role_plans(prefix)}
    homes = [base] + sorted(str(p) for p in (Path(base) / "profiles").glob("*") if p.is_dir())
    stale = []
    for home in homes:
        if os.path.abspath(home) in (os.path.abspath(profile_home),) or home in roles:
            continue
        if not os.path.isdir(os.path.join(home, "plugins", "crew")):
            continue
        steps = [f(home, False) for f in (step_plugin, step_skills, step_scripts, step_roles)]
        if any(st == "CHANGED" for st, _d in steps):
            stale.append((home, [d for st, d in steps if st == "CHANGED"]))
    if not stale:
        return "OK", "every other crew copy is this version"
    label = lambda home: os.path.basename(home) if home != base else "default"
    names = ", ".join(label(home) for home, _d in stale)
    if not apply:
        return "CHANGED", "bring crew up to this version in: %s" % "; ".join(
            "%s (%s)" % (label(home), " | ".join(d)) for home, d in stale)
    for home, _d in stale:
        for f in (step_plugin, step_skills, step_scripts, step_roles):
            status, detail = f(home, True)
            if status == "CHANGED":
                print("  %s: %s" % (label(home), detail))
    return "CHANGED", "crew brought up to this version in: %s" % names


def _plugin_enabled(profile):
    r = h(profile, "plugins", "list", "--plain")
    if r.returncode != 0:
        return False
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[-1] == "crew" and parts[0] == "enabled":
            return True
    return False


def step_enable(profile, apply):
    if _plugin_enabled(profile):
        return "OK", "plugin enabled"
    if not apply:
        return "CHANGED", "plugin enable crew"
    h(profile, "plugins", "enable", "crew", "--no-allow-tool-override")
    return "CHANGED", "plugin enabled crew"


def _config_get(profile, key):
    rc, out = _cfg_raw_many(profile, [key])[key]
    out = (out or "").strip()
    return out if rc == 0 and out else None


_LIST_ITEM_RX = re.compile(r"^\s*-\s*(.*)$")


def _cfg(profile, key):
    """The value `hermes config get` prints for a dotted key, as one line: a scalar as it is, a list as
    '[a,b]' ('[]' when empty), None when the key is not set. Hermes does the reading, the way it does the writing."""
    rc, out = _cfg_raw_many(profile, [key])[key]
    out = (out or "").strip()
    if rc != 0 or not out:
        return None
    lines = [l for l in out.splitlines() if l.strip()]
    if all(_LIST_ITEM_RX.match(l) for l in lines):
        return "[%s]" % ",".join(_LIST_ITEM_RX.match(l).group(1).strip() for l in lines)
    return out if len(lines) > 1 else lines[0].strip()


def _cfg_many(profile, keys):
    """{key: _cfg(profile, key)}: all keys read in one in-process call (see _cfg_raw_many)."""
    keys = list(keys)
    _cfg_raw_many(profile, keys)
    return {k: _cfg(profile, k) for k in keys}


def step_config(profile_home, profile, apply):
    roles_path = os.path.join(profile_home, "roles", "crew", "roles.json")
    expected = {"crew.roles_path": roles_path, "crew.source_dir": str(SRC_DIR)}
    missing = [(k, v) for k, v in expected.items() if _config_get(profile, k) != v]
    if not missing:
        return "OK", "config crew.roles_path + crew.source_dir"
    if not apply:
        return "CHANGED", "config set " + ", ".join(k for k, _ in missing)
    for key, val in missing:
        h(profile, "config", "set", key, val)
    return "CHANGED", "config set " + ", ".join(k for k, _ in missing)


def intake_preload_chars():
    """Characters one `/crew <ask>` preload hands the model: the plugin's preamble plus
    skills/crew/SKILL.md without its frontmatter (see __init__.crew_intake_preload).

    Hermes injects a pre_llm_call hook's context into the turn's user message, but above
    ``hooks.output_spill.max_chars`` it replaces the text with a head/tail preview plus a file path -
    and reading that file back is a tool call, which the intake rule ("ask through clarify, no
    research call") forbids. So the cap has to sit above this size."""
    try:
        body = (SRC_DIR / "skills" / "crew" / "SKILL.md").read_text()
    except OSError:
        return 0
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            body = body[end + 4:].lstrip("\n")
    preamble = (
        "The `crew` skill is already loaded; its full text follows. Do not call skill_view or "
        "skills_list for it. The owner's ask is: \"<ask>\". Apply Rule 1 first: if the ask names no "
        "target and no measurable end state, ask through the clarify tool - one batch, no research "
        "call.\n\n"
        "<skill name=\"crew\">\n</skill>"
    )
    return len(body) + len(preamble)


def spill_cap_needed():
    """The spill cap this package needs: the preload plus headroom for a longer ask and the
    preamble, rounded up to 1000. Derived from the shipped skill, so a skill that grows past the
    installed cap is caught by the next install instead of silently costing a tool call per intake."""
    need = intake_preload_chars() + 2000
    return max(15000, -(-need // 1000) * 1000)


def step_spill_cap(profile, apply, enabled):
    """--spill-cap: raise hooks.output_spill.max_chars above the intake preload, in the profile the owner types
    /crew in (the installing profile, never a role profile: a role runs cards, not the /crew intake). Under the cap
    the /crew turn costs one tool call (the read of the spilled skill text) and the intake proof - which asserts
    zero - fails, while the model's answer is unchanged. Opt-in because it changes a profile-wide setting."""
    need = spill_cap_needed()
    cur = _cfg(profile, "hooks.output_spill.max_chars")
    try:
        have = int(str(cur).strip()) if cur is not None else 0
    except (TypeError, ValueError):
        have = 0
    if have >= need:
        return "OK", "hooks.output_spill.max_chars = %d" % have
    if not enabled:
        return "SKIP", ("hooks.output_spill.max_chars is %s, the /crew preload needs %d: a /crew turn costs one extra "
                        "tool call until you pass --spill-cap" % (cur or "unset (Hermes default 10000)", need))
    if not apply:
        return "CHANGED", "config set hooks.output_spill.max_chars %d (was %s)" % (need, cur or "unset")
    h(profile, "config", "set", "hooks.output_spill.max_chars", str(need))
    written = _cfg(profile, "hooks.output_spill.max_chars")
    if str(written).strip() != str(need):
        return "FAILED", "hooks.output_spill.max_chars still %s after config set" % (written or "unset")
    return "CHANGED", "config set hooks.output_spill.max_chars %d (was %s)" % (need, cur or "unset")


# The commands the owner types lead the platform menus, /crew first. Telegram is the one platform with a
# server-side menu (Bot API setMyCommands): its order comes from
# platforms.telegram.extra.command_menu.priority with priority_mode prepend. Without that key the menu is
# core-commands-first with the crew options sorted alphabetically, so /crew (a skill command, tier 2) sits
# under the built-ins. The order here is importance: the intake, then the options typed every day, then the
# recovery passes, then the install.
CREW_MENU_ORDER = ["crew", "crew-status", "crew-graph", "crew-stop", "crew-unstuck", "crew-safety", "crew-proof", "crew-diagnose"]


def _menu_names(raw):
    """The names in a `[a, b, c]` config value, unquoted; [] for anything else."""
    raw = (raw or "").strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        return []
    return [n.strip().strip("'\"") for n in raw[1:-1].split(",") if n.strip()]


def step_menu_priority(profile, apply, enabled):
    """--telegram-menu: put /crew first in the platform command menu, the crew options behind it in importance order."""
    dotted = "platforms.telegram.extra.command_menu.priority"
    if not enabled:
        return "SKIP", "telegram command menu order (--telegram-menu)"
    have = _cfg_many(profile, [dotted + "_mode", dotted])
    if (have[dotted + "_mode"] or "") == "prepend" and _menu_names(have[dotted] or "") == CREW_MENU_ORDER:
        return "OK", "telegram command menu leads with %s" % ", ".join("/" + n for n in CREW_MENU_ORDER)
    if not apply:
        return "CHANGED", "config set %s (/%s first, %d name(s))" % (dotted, CREW_MENU_ORDER[0],
                                                                     len(CREW_MENU_ORDER))
    h(profile, "config", "set", dotted + "_mode", "prepend")
    h(profile, "config", "set", dotted, json.dumps(CREW_MENU_ORDER))
    got = _menu_names(_cfg(profile, dotted) or "")
    if got != CREW_MENU_ORDER:
        return "FAILED", "%s is %s after config set" % (dotted, got or "unset")
    return "CHANGED", "config set %s (/%s first)" % (dotted, CREW_MENU_ORDER[0])


# ------------------------------------------------------------------- shell-hook consent
# A hook only fires when its (event, command) pair sits in that home's shell-hooks-allowlist.json:
# without the entry the runtime logs "not allowlisted - skipped" and the gate is simply absent. The
# approval is the owner's: Hermes asks at its own TTY prompt (or `--accept-hooks`, typed by the owner).
# The installer never writes that file and never passes --accept-hooks; it reads it and reports what is
# still missing.

ALLOWLIST_NAME = "shell-hooks-allowlist.json"
# the runtime's own rule for finding the script inside a hook command
_SCRIPT_EXTENSIONS = (".sh", ".bash", ".zsh", ".fish", ".py", ".pyw", ".rb", ".pl", ".lua", ".js",
                      ".mjs", ".cjs", ".ts")


def _script_path(command):
    """The script a hook command runs, by the runtime's rule: first token with a script extension,
    else the first path-like token, else the first token. Kept identical so the mtime read here
    is the mtime the runtime compares against."""
    parts = (command or "").split()
    if not parts:
        return ""
    for token in parts:
        if token.lower().endswith(_SCRIPT_EXTENSIONS):
            return os.path.expanduser(token)
    for token in parts:
        if "/" in token or token.startswith("~"):
            return os.path.expanduser(token)
    return os.path.expanduser(parts[0])


def _iso(mtime):
    return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _mtime_iso(command):
    try:
        return _iso(os.path.getmtime(_script_path(command)))
    except OSError:
        return None


def _declared_hooks(home):
    """[(event, command)] from a home's own config.yaml - never a hand-typed list.

    Only an entry naming a command is a hook: the `output_spill:` mapping under `hooks:` carries
    settings, not a command. An item is either `- matcher: X` / `- command: X` followed by an
    indented `command:` line (the form this package writes) or a bare path string.
    """
    try:
        lines = Path(os.path.join(home, "config.yaml")).read_text().splitlines()
    except OSError:
        return []
    hooks, event, in_hooks = [], None, False
    for line in lines:
        stripped, indent = line.strip(), len(line) - len(line.lstrip())
        if not stripped or stripped.startswith("#"):
            continue
        if indent == 0:
            in_hooks, event = stripped.startswith("hooks:"), None
            continue
        if not in_hooks:
            continue
        if indent <= 2 and stripped.endswith(":"):
            event = stripped[:-1]
            continue
        if not event:
            continue
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if item.startswith("command:"):
                hooks.append((event, item.split(":", 1)[1].strip().strip("'\"")))
            elif ":" not in item:
                hooks.append((event, item.strip("'\"")))
        elif stripped.startswith("command:"):
            hooks.append((event, stripped.split(":", 1)[1].strip().strip("'\"")))
    return hooks


def _load_allowlist(home):
    """(entries, finding): the home's approvals, or the one finding explaining why there are none."""
    path = Path(home) / ALLOWLIST_NAME
    if not path.exists():
        return None, "no consent record (%s missing)" % ALLOWLIST_NAME
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return None, "consent record unreadable (%s)" % type(exc).__name__
    entries = data.get("approvals") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return None, "consent record has no approvals list"
    return entries, None


def permission_problems(home):
    """What stops this home's declared hooks from firing, as findings ([] when healthy).

    One owner for the rule, so the step, install.py --check and the proof suite cannot disagree.
    A declared hook with no approval is the silent-skip case: the runtime skips it and the gate
    (facts-gate, no-agent-attribution-gate, model-gate, the Windows-path guard) never runs, while
    the home still looks installed. Approval drift (the script changed after it was approved) does not stop the
    hook - Hermes matches the allowlist on event and command only - but the owner approved a different script, so
    it is reported for review, with Hermes's own remedy (revoke, then approve again).
    """
    pairs = _declared_hooks(home)
    if not pairs:
        return []                      # nothing declared, nothing to consent to
    findings = []
    entries, problem = _load_allowlist(home)
    if problem:
        findings.append(problem)
    try:
        mode = os.stat(os.path.join(home, ALLOWLIST_NAME)).st_mode & 0o777
        if mode != 0o600:
            findings.append("consent record mode %o, want 600" % mode)
    except OSError:
        pass
    approved = {(e.get("event"), e.get("command")): e for e in (entries or []) if isinstance(e, dict)}
    for event, command in pairs:
        entry = approved.get((event, command))
        if entry is None:
            findings.append("declared but not approved: [%s] %s" % (event, os.path.basename(command)))
            continue
        script = _script_path(command)
        if not os.path.exists(script):
            findings.append("hook script missing: %s" % script)
        elif not os.access(script, os.X_OK):
            findings.append("hook script not executable: %s" % script)
        now, was = _mtime_iso(command), entry.get("script_mtime_at_approval")
        if now and was and now > was:
            findings.append("approval drift: [%s] %s (approved %s, script %s)"
                            % (event, os.path.basename(command), was, now))
    return findings


PROFILE_PREFIX = "crew-"


def _conf_value(val):
    """A settings.conf value with `{prefix}` replaced by the role profile prefix in force."""
    return val.replace("{prefix}", PROFILE_PREFIX)


# Lines in settings.conf that steer the installer and are NOT config.yaml keys.
INSTALLER_KEYS = ("skills_extra",)


def _conf_lines(conf_path):
    """[(key, value)] for every `key = value` line of a role's settings.conf, installer directives
    included, `{prefix}` resolved. [] when the file is missing."""
    try:
        text = Path(conf_path).read_text()
    except OSError:
        return []
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out.append((key.strip(), _conf_value(val.strip())))
    return out


def _conf_entries(conf_path):
    """The config.yaml keys of a settings.conf: every line except the installer's own directives."""
    return [(k, v) for k, v in _conf_lines(conf_path) if k not in INSTALLER_KEYS]


def _conf_list(conf_path, key):
    """A `key = [a,b]` directive as a list of strings ([] when absent or empty)."""
    for k, v in _conf_lines(conf_path):
        if k == key:
            return [x.strip() for x in v.strip("[]").split(",") if x.strip()]
    return []


def settings_problems(profile, role, tpl):
    """The role's own settings.conf, checked line by line against the profile's config (read by `hermes config get`).

    The gates are only half of it: a role home without crew.role, without the empty
    fallback_providers, or with Slack left on is not the role the card contract assumes.
    """
    entries = [(k, role if k == "crew.role" else v) for k, v in _conf_entries(os.path.join(tpl, "settings.conf"))]
    have = _cfg_many(profile, [k for k, _v in entries])
    return ["%s = %s, want %s" % (key, (have[key] or "unset").strip(), want)
            for key, want in entries if (have[key] or "").strip() != want]


def consent_hint(name):
    """How the owner approves one profile's hooks with Hermes's own flow."""
    flag = " ".join(profile_flag(name))
    cli = "hermes %s" % flag if flag else "hermes"
    return ("approve with Hermes, not the installer: review `%s hooks list`, then run `%s chat` in a terminal and "
            "confirm each hook at its prompt (or `%s chat --accept-hooks` once, yourself); an approval-drift hook keeps "
            "its old entry, which --accept-hooks never refreshes: `%s hooks revoke <command>` it first, then approve "
            "again; check with `%s hooks doctor`"
            % (cli, cli, cli, cli, cli))


def step_permissions(profile_home, profile, prefix, apply):
    """Report-only: which declared shell hooks of the installing profile and of each role profile Hermes would skip.

    Never writes. The coordinator's decision turn (`hermes -p <prefix>coordinator chat -Q`) runs without
    --accept-hooks, so a role profile that inherited the owner's gates (facts-gate, model-gate, ...) only enforces
    them once its own allowlist holds them; kanban workers are started with --accept-hooks by the dispatcher.
    """
    homes = [(profile or "default", profile_home)]
    homes += [(name, home) for _role, name, home, _tpl in _role_plans(prefix) if os.path.isdir(home)]
    findings, hints = [], []
    for name, home in homes:
        found = permission_problems(home)
        if found:
            findings += ["%s: %s" % (name, f) for f in found]
            hints.append("%s: %s" % (name, consent_hint(name)))
    if not findings:
        pairs = sum(len(_declared_hooks(home)) for _name, home in homes)
        return "OK", "%d home(s), %d declared hook(s), every one approved in Hermes's allowlist" % (len(homes), pairs)
    summary = "; ".join(findings[:3]) + ("" if len(findings) <= 3 else " (+%d more)" % (len(findings) - 3))
    return "FAILED", "hook consent missing or stale - %s | %s" % (summary, " | ".join(hints))


def plugin_script(profile_home, name):
    """A crew script inside the profile's plugin copy: where every unit and every skill runs it from."""
    return os.path.join(profile_home, "plugins", "crew", "scripts", name)


def _ts_humans():
    """Tailnet logins of people (not this node's own user, not tagged devices): who --publish may let in."""
    try:
        r = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=10)
        data = json.loads(r.stdout) if r.returncode == 0 else {}
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    return sorted(u.get("LoginName") for u in (data.get("User") or {}).values()
                  if "@" in str(u.get("LoginName") or ""))


def publish_settings(name, user=""):
    """(hosts, users, error) for --publish. The dashboard serves transcript excerpts, so a published one needs an
    identity in front of it: `tailscale serve` adds Tailscale-User-Login to every request it proxies, and the server
    answers a tailnet request only for these logins. --publish-user names the owner; without it the tailnet's single
    human login is used, and anything else is refused rather than guessed."""
    if not name:
        return "", "", "tailscale is not up on this machine"
    users = [user] if user else _ts_humans()
    if len(users) != 1:
        return "", "", ("pass --publish-user <tailnet login> (found %s)" % (", ".join(users) or "no human login"))
    return name, users[0], ""


def render_graph_unit(profile_home, port=GRAPH_PORT):
    script = plugin_script(profile_home, "crew_graph_serve.py")
    rec = _owner_record()
    publish = ""
    if rec.get("publish_hosts") and (rec.get("publish_users") or rec.get("publish_tags")):   # recorded by --publish
        publish = ("Environment=CREW_GRAPH_HOSTS=%s\nEnvironment=CREW_GRAPH_USERS=%s\n"
                   % (rec["publish_hosts"], rec.get("publish_users") or ""))
        if rec.get("publish_tags"):
            publish += "Environment=CREW_GRAPH_TAGS=%s\n" % rec["publish_tags"]
    return (
        "[Unit]\n"
        "Description=Hermes crew flow graph over HTTP (board + session stores, read-only)\n"
        "After=hermes-gateway.service\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        "ExecStart=%s %s\n"
        "Environment=CREW_GRAPH_BIND=127.0.0.1\n"
        "Environment=CREW_GRAPH_PORT=%d\n"
        "%s"
        "Restart=always\n"
        "RestartSec=5\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    ) % (python3_bin(), script, port, publish)


def step_graph_unit(profile_home, apply, no_service, port=GRAPH_PORT):
    if no_service:
        return "SKIP", "graph http unit (--no-service)"
    unit = render_graph_unit(profile_home, port)
    unit_path = UNIT_DIR / UNIT_GRAPH_NAME
    if os.path.exists(str(unit_path)) and _read(str(unit_path)) == unit.encode():
        act = subprocess.run(["systemctl", "--user", "is-active", UNIT_GRAPH_NAME],
                             capture_output=True, text=True).stdout.strip()
        if act == "active":
            return "OK", "graph http unit up to date (active on 127.0.0.1:%d)" % port
        if not apply:
            return "CHANGED", "graph http unit -> start %s" % UNIT_GRAPH_NAME
        subprocess.run(["systemctl", "--user", "enable", "--now", UNIT_GRAPH_NAME],
                       capture_output=True, text=True)
        return "CHANGED", "graph http unit started"
    if not apply:
        return "CHANGED", "graph http unit -> %s" % unit_path
    os.makedirs(UNIT_DIR, exist_ok=True)
    tmp = str(unit_path) + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(unit)
    os.replace(tmp, str(unit_path))
    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, text=True)
    # enable, then restart: `enable --now` leaves an already-running server on the old unit (and, on an upgrade,
    # on the old script path the install just removed - 2026-10-03, the 0.6 server kept answering 500)
    subprocess.run(["systemctl", "--user", "enable", UNIT_GRAPH_NAME], capture_output=True, text=True)
    subprocess.run(["systemctl", "--user", "restart", UNIT_GRAPH_NAME], capture_output=True, text=True)
    return "CHANGED", "graph http unit written + daemon-reload + enable + restart"


def _ts_name():
    try:
        r = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            import json as _json
            data = _json.loads(r.stdout)
            return (data.get("Self", {}) or {}).get("DNSName", "").rstrip(".")
    except Exception:
        pass
    return ""


def _cron_id(profile, name):
    r = h(profile, "cron", "list")
    if r.returncode != 0:
        return None
    last_id = None
    for line in r.stdout.splitlines():
        m = re.match(r"^\s*([0-9a-f]{8,})\s+\[", line)
        if m:
            last_id = m.group(1)
            continue
        if "Name:" in line and name in line:
            return last_id
    return None


def step_retire_crons(profile, apply, no_cron):
    """Remove the crons of OLD_CRON_NAMES: the coordinator loop replaced the heal job and the observer
    role is gone, so a leftover job would run a script that no longer exists."""
    if no_cron:
        return "SKIP", "retire old crons (--no-cron)"
    found = [(name, _cron_id(profile, name)) for name in OLD_CRON_NAMES]
    found = [(name, cid) for name, cid in found if cid]
    if not found:
        return "OK", "no old crew crons (%s)" % ", ".join(OLD_CRON_NAMES)
    if not apply:
        return "CHANGED", "remove %s" % ", ".join("`%s` %s" % f for f in found)
    for name, cid in found:
        h(profile, "cron", "remove", cid)
    left = [name for name, _cid in found if _cron_id(profile, name)]
    if left:
        return "FAILED", "still registered: %s" % ", ".join("`%s`" % n for n in left)
    return "CHANGED", "removed %s" % ", ".join("`%s` %s" % f for f in found)


# The platforms the owner types /crew in. The intake opens the card with the kernel's kanban_create tool,
# and that tool is offered to a chat only where the profile's platform toolset has `kanban` on (it is off
# by default on every chat platform, on for the CLI only): without this step /crew cannot open a card.
CHAT_KANBAN_PLATFORMS = ("zulip", "telegram")
KANBAN_TOOLSET_RX = re.compile(r"\b(enabled|disabled)\s+kanban\b")


def _kanban_toolset_state(profile, platform):
    """'enabled', 'disabled' or '' (unreadable) for the kanban toolset on one platform of the chat profile."""
    r = h(profile, "tools", "list", "--platform", platform)
    if r.returncode != 0:
        return ""
    m = KANBAN_TOOLSET_RX.search(r.stdout)
    return m.group(1) if m else ""


def step_chat_kanban(profile, apply, enabled):
    """--chat-kanban: turn the kanban toolset on for the chat platforms, so the intake's kanban_create tool exists
    there. Opt-in: it lets a chat on that platform create and move cards, which is the owner's call."""
    if not enabled:
        return "SKIP", "kanban toolset on %s (--chat-kanban; without it /crew cannot open a card there)" % ", ".join(
            CHAT_KANBAN_PLATFORMS)
    off = [p for p in CHAT_KANBAN_PLATFORMS if _kanban_toolset_state(profile, p) == "disabled"]
    if not off:
        return "OK", "kanban toolset on for %s" % ", ".join(CHAT_KANBAN_PLATFORMS)
    if not apply:
        return "CHANGED", "tools enable kanban --platform %s" % ", ".join(off)
    for p in off:
        h(profile, "tools", "enable", "kanban", "--platform", p)
    left = [p for p in off if _kanban_toolset_state(profile, p) != "enabled"]
    if left:
        return "FAILED", "kanban toolset still off on %s after tools enable" % ", ".join(left)
    return "CHANGED", "enabled the kanban toolset on %s" % ", ".join(off)


def _proof_board():
    """scripts/crew_proof_board.py, the one place that knows where the proofs board lives."""
    scripts = os.path.join(SRC_DIR, "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import crew_proof_board
    return crew_proof_board


def step_proofs_board(apply, enabled=True):
    """The kernel's own `crew-proofs` board, where every proof seeds its cards (never the live board). Only with
    --nightly-proofs: crew_proofs.py creates it itself when someone runs the proofs by hand.
    `kanban boards create` has mkdir -p semantics, so an existing board is left as it is."""
    if not enabled:
        return "SKIP", "crew-proofs board (--nightly-proofs creates it; crew_proofs.py creates it on a manual run)"
    pb = _proof_board()
    if os.path.exists(pb.proofs_db()):
        return "OK", "crew-proofs board %s" % pb.proofs_db()
    if not apply:
        return "CHANGED", "kanban boards create %s" % pb.PROOFS_BOARD
    if not pb.ensure_proofs_board(hermes=hermes_bin()):
        return "FAILED", "`kanban boards create %s` left no board at %s" % (pb.PROOFS_BOARD, pb.proofs_db())
    return "CHANGED", "created the crew-proofs board at %s" % pb.proofs_db()


def step_proofs_cron(profile, profile_home, apply, no_cron, nightly=False, deliver=CRON_PROOFS_DELIVER):
    """--nightly-proofs: run every crew proof on the crew-proofs board each night; the job stays silent unless one of
    them fails, and its output goes to `deliver` (local unless --proofs-deliver names a target). crew_proofs.py pins
    the board for every proof, so the cron needs no board setting of its own. Hermes cron only runs scripts from
    HERMES_HOME/scripts, so the one file crew keeps there is the Python shim that hands over to the plugin's copy.
    A job an earlier install registered stays registered, and is migrated here: pointed at the Python shim, and
    only then is the old crew_proofs.sh deleted (a symlink is unlinked, its target never touched). This step runs
    after step_scripts, which does not touch either file."""
    if no_cron:
        return "SKIP", "proofs cron (--no-cron)"
    cid = _cron_id(profile, CRON_PROOFS_NAME)
    scripts = os.path.join(profile_home, "scripts")
    shim = os.path.join(scripts, PROOFS_SHIM)
    old = os.path.join(scripts, OLD_PROOFS_SHIM)
    shim_ok = _read(shim) == PROOFS_SHIM_TEXT.encode() and not os.path.islink(shim)
    old_there = os.path.lexists(old)
    if not nightly and not cid:
        if old_there:
            return step_old_shim(profile_home, apply)
        return "SKIP", "proofs cron (--nightly-proofs registers it; delivery %s unless --proofs-deliver)" % deliver
    if cid and shim_ok and not old_there:
        return "OK", "proofs cron %s%s" % (cid, "" if nightly else " (registered earlier; kept)")
    if not apply:
        todo = ([] if shim_ok else ["write " + shim]) + (["point the job at it"] if cid else ["register the job"]) \
            + (["remove " + old] if old_there else [])
        return "CHANGED", "proofs cron%s: %s" % ("" if nightly else " " + cid, ", ".join(todo))
    if not shim_ok:
        _write_shim(scripts)
        print("  wrote %s" % shim)
    if cid:
        h(profile, "cron", "edit", cid, "--script", PROOFS_SHIM)
    else:
        h(profile, "cron", "create", CRON_PROOFS_SCHEDULE, "--name", CRON_PROOFS_NAME,
          "--script", PROOFS_SHIM, "--no-agent", "--deliver", deliver)
        cid = _cron_id(profile, CRON_PROOFS_NAME)
    if old_there:
        os.remove(old)       # on a symlink this removes the link only
        print("  removed %s" % old)
    return "CHANGED", "proofs cron %s (deliver %s)" % (cid or "(not found after create)", deliver)


def skill_names():
    """Every skill the package ships (a directory under skills/ holding a SKILL.md)."""
    src = os.path.join(SRC_DIR, "skills")
    return sorted(d for d in os.listdir(src) if os.path.isfile(os.path.join(src, d, "SKILL.md")))


def step_skills(profile_home, apply):
    """Install every skill the package ships into <profile>/skills/crew/<name>/, so the
    role skills resolve on a fresh install with no shared skills folder configured."""
    src = os.path.join(SRC_DIR, "skills")
    names = skill_names()
    dst_root = os.path.join(profile_home, "skills", "crew")
    stale = [n for n in names
             if not _same(os.path.join(src, n, "SKILL.md"), os.path.join(dst_root, n, "SKILL.md"))]
    if not stale:
        return "OK", "skills %s (up to date)" % ", ".join(names)
    if not apply:
        return "CHANGED", "skills -> install %s into %s" % (", ".join(stale), dst_root)
    for n in stale:
        d = os.path.join(dst_root, n)
        os.makedirs(d, exist_ok=True)
        shutil.copy2(os.path.join(src, n, "SKILL.md"), os.path.join(d, "SKILL.md"))
    return "CHANGED", "skills %s installed into %s" % (", ".join(stale), dst_root)


# ---------------------------------------------------------------- slim role skills
# `hermes profile create --clone-from` copies the source profile's whole skills tree (47 MB here: the
# skill repo's .git, curator backups, every category). A crew role runs one card from its own skill,
# so its skills dir holds skills/crew/ (the role skills this package ships) plus whatever the role's
# settings.conf names in `skills_extra = [category/skill, ...]` (paths under the installing profile's
# skills dir, copied in). The marker keeps `hermes update` from re-seeding the bundled set.

NO_BUNDLED_SKILLS_MARKER = ".no-bundled-skills"
NO_BUNDLED_SKILLS_TEXT = ("A crew role profile carries only skills/crew/ and its skills_extra; the installer\n"
                          "wrote this so `hermes update` does not re-seed the bundled skills.\n")
# What Hermes itself keeps in an opted-out profile's skills dir, so trimming it would only start a fight with
# every `hermes update`: the essential skill it seeds even under the marker (tools/skills_sync.py ESSENTIAL_SKILLS)
# and its own sync/curator records. Measured 2026-10-06: trimmed role profiles were re-seeded within the hour.
HERMES_KEPT_SKILLS = ("autonomous-ai-agents/hermes-agent",)
HERMES_KEPT_FILES = (".bundled_manifest", ".curator_state")


def _extras_clean(extras):
    return [e.strip("/") for e in extras if e.strip("/")]


def _skills_excess(home, extras):
    """Paths under <home>/skills a role profile does not keep, relative to skills/: everything but
    crew/, the opt-out marker and the extras themselves (a category holding an extra is kept only as far
    as the extra). Hidden clone artifacts (.git, .curator_*, .archive) go too."""
    root = os.path.join(home, "skills")
    if not os.path.isdir(root) or os.path.islink(root):
        return []
    # A kept skill's category carries a DESCRIPTION.md that Hermes's sync writes next to it.
    keep = set(_extras_clean(extras)) | set(HERMES_KEPT_SKILLS)
    keep |= {k.split("/")[0] + "/DESCRIPTION.md" for k in keep if "/" in k}
    out = []

    def walk(rel):
        for name in sorted(os.listdir(os.path.join(root, rel) if rel else root)):
            path = "%s/%s" % (rel, name) if rel else name
            if path in keep or (not rel and name in ("crew", NO_BUNDLED_SKILLS_MARKER) + HERMES_KEPT_FILES):
                continue
            if os.path.isdir(os.path.join(root, path)) and not os.path.islink(os.path.join(root, path)) \
                    and any(k.startswith(path + "/") for k in keep):
                walk(path)
            else:
                out.append(path)
    walk("")
    return out


def _extras_missing(home, source_home, extras):
    """Extras that exist in the installing profile's skills dir but not yet in the role's."""
    return [rel for rel in _extras_clean(extras)
            if os.path.isdir(os.path.join(source_home, "skills", rel))
            and not os.path.isdir(os.path.join(home, "skills", rel))]


def role_skills_todo(home, tpl, source_home):
    """(excess entries, missing extras, marker missing) for one role profile; all empty when slim."""
    extras = _conf_list(os.path.join(tpl, "settings.conf"), "skills_extra")
    # Hermes reads the opt-out at the profile root (tools/skills_sync.py: _hermes_home() / marker), not in skills/.
    marker = not os.path.exists(os.path.join(home, NO_BUNDLED_SKILLS_MARKER))
    return _skills_excess(home, extras), _extras_missing(home, source_home, extras), marker


def crew_owned(home):
    """A role profile crew itself created: it carries the record the installer writes into every profile it provisions."""
    return os.path.isfile(os.path.join(home, SHIPPED_RECORD))


def step_role_skills(home, tpl, source_home, apply, owned=True):
    """Cut a role profile's skills dir down to skills/crew/ + skills_extra, printing every path it removes. Only ever
    called on a role profile the installer provisions (never the installing profile), and only deletes in a profile
    crew created (`owned`: created in this run, or carrying crew/template-shipped.json); a symlinked skills dir is
    left alone."""
    root = os.path.join(home, "skills")
    if os.path.islink(root):
        return "FAILED", "%s is a symlink; left alone" % root
    if not owned:
        return "SKIP", "role skills of %s left alone: crew did not create it (no %s)" % (
            os.path.basename(home), SHIPPED_RECORD)
    excess, missing, marker = role_skills_todo(home, tpl, source_home)
    if not (excess or missing or marker):
        return "OK", "role skills slim (%s)" % os.path.basename(home)
    if not apply:
        return "CHANGED", "role skills -> drop %d entr%s from %s%s" % (
            len(excess), "y" if len(excess) == 1 else "ies", root,
            (", add %s" % ", ".join(missing)) if missing else "")
    extras = _conf_list(os.path.join(tpl, "settings.conf"), "skills_extra")
    os.makedirs(root, exist_ok=True)
    for rel in missing:
        shutil.copytree(os.path.join(source_home, "skills", rel), os.path.join(root, rel), symlinks=True)
    for name in _skills_excess(home, extras):
        path = os.path.join(root, name)
        print("  removed %s" % path)
        if os.path.islink(path) or os.path.isfile(path):
            os.unlink(path)
        else:
            shutil.rmtree(path)
    if marker:
        Path(os.path.join(home, NO_BUNDLED_SKILLS_MARKER)).write_text(NO_BUNDLED_SKILLS_TEXT)
    return "CHANGED", "role skills slim: dropped %d entr%s%s" % (
        len(excess), "y" if len(excess) == 1 else "ies", (", added %s" % ", ".join(missing)) if missing else "")


# ---------------------------------------------------------------- first-call prompt budget
# What one worker turn costs before it has done anything: the system prompt and the tool list, every
# call of every card. state.db keeps per-session totals, not per-call, so the first call is bounded from
# above by the smallest per-call average over the newest kanban sessions (exact when a session made one
# call). The average counts cache reads: a provider that caches bills them at a lower rate but they are
# still prompt.

PROMPT_SESSIONS = 10


def roles_budget():
    """prompt_budget_tokens from the package's roles.json (None when the key is absent)."""
    import json
    try:
        with open(SRC_DIR / "roles" / "roles.json") as fh:
            val = json.load(fh).get("prompt_budget_tokens")
        return int(val) if val else None
    except Exception:
        return None


def prompt_first_call(home, limit=PROMPT_SESSIONS):
    """(tokens, sessions looked at) - the upper bound on the first API call of a kanban run in this
    profile - or (None, 0) when state.db holds no kanban session that made a call."""
    import sqlite3
    db = os.path.join(home, "state.db")
    if not os.path.exists(db):
        return None, 0
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=5)
        try:
            rows = conn.execute(
                "select (input_tokens + cache_read_tokens + cache_write_tokens) * 1.0 / api_call_count "
                "from sessions where source = 'kanban' and api_call_count > 0 "
                "order by started_at desc limit ?", (limit,)).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return None, 0
    if not rows:
        return None, 0
    return int(min(r[0] for r in rows)), len(rows)


def skills_bytes(home):
    """Bytes under <home>/skills (links not followed)."""
    total = 0
    for d, _subs, files in os.walk(os.path.join(home, "skills")):
        for f in files:
            try:
                total += os.lstat(os.path.join(d, f)).st_size
            except OSError:
                pass
    return total


def prompt_report(prefix):
    """([one line per role: skills size and first-call prompt], [roles over budget])."""
    budget = roles_budget()
    lines, over = [], []
    for role, name, home, _tpl in _role_plans(prefix):
        if not os.path.isdir(home):
            continue
        head = "%-18s skills %6.2f MB," % (name, skills_bytes(home) / 1e6)
        tokens, seen = prompt_first_call(home)
        if tokens is None:
            lines.append("%s first call: no kanban session yet (budget %s)" % (head, budget or "unset"))
            continue
        flag = ""
        if budget and tokens > budget:
            flag = "  OVER BUDGET"
            over.append(name)
        lines.append("%s first call <= %6d tokens, min of %d newest kanban sessions (budget %s)%s"
                     % (head, tokens, seen, budget or "unset", flag))
    return lines, over


def step_prompt_budget(prefix, apply):
    """Report only: the installer cannot shrink a prompt, it can say a role's is over the budget."""
    lines, over = prompt_report(prefix)
    if over:
        return "FAILED", "first-call prompt over budget: %s" % ", ".join(over)
    return "OK", "first-call prompt within budget (%d role(s) measured)" % sum(
        1 for l in lines if "no kanban session" not in l)


# ---------------------------------------------------------------- role profiles
# One profile per role, created from templates/profiles/<role>/: SOUL.md (persona) and
# settings.conf (config keys). Fields the owner edits in the profile are never overwritten:
# the installer records what it shipped and only replaces a file still equal to that record.

ROLE_ORDER = ["coordinator", "worker", "content", "verifier"]
ROLE_DESCS = {
    "coordinator": "Crew coordinator: turns an ask into a contract, splits independent parts, "
                   "closes on the verifier's verdict.",
    "worker": "Crew worker: code, config, infra and web work on one card; one writer, "
              "proof before report.",
    "content": "Crew content: posts, reports, video, pages and social; rendered artifact "
               "plus its raw source.",
    "verifier": "Crew verifier: runs the card's proof itself, read-only, never fixes; "
                "two fails block the card.",
}
SHIPPED_RECORD = os.path.join("crew", "template-shipped.json")


def _apply_settings(profile, conf_path):
    """Apply key = value lines from a template settings file with `hermes config set` (Hermes's own writer).
    Returns the keys it changed; a key whose set failed is not in the list, so the next check still reports it."""
    entries = _conf_entries(conf_path)
    have = _cfg_many(profile, [k for k, _v in entries])
    changed = []
    for key, val in entries:
        if have[key] == val:
            continue
        r = h(profile, "config", "set", key, val)
        if r.returncode == 0:
            changed.append(key)
        else:
            print("  config set %s failed: %s" % (key, ((r.stderr or r.stdout).strip().splitlines() or ["?"])[-1]))
    return changed


def _shipped_record(profile_home):
    import json
    try:
        with open(os.path.join(profile_home, SHIPPED_RECORD)) as fh:
            return json.load(fh)
    except Exception:
        return {}


def _plugin_version(path):
    """Version line from a plugin.yaml, so drift between package and profile is visible."""
    try:
        for line in Path(path).read_text().splitlines():
            if line.startswith("version:"):
                return line.split(":", 1)[1].strip()
    except OSError:
        return None
    return None


def _sha(text):
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()


def _role_plans(profile):
    """[(role, profile name, profile home, template dir)] for every template on disk."""
    tpl_root = SRC_DIR / "templates" / "profiles"
    if not tpl_root.is_dir():
        return []
    return [(role, "%s%s" % (profile, role), resolve_profile_home("%s%s" % (profile, role)),
             str(tpl_root / role))
            for role in ROLE_ORDER if (tpl_root / role).is_dir()]


def _provision_role_profile(name, home, tpl, source_home, owned):
    """Give a role profile the same plugin (scripts included), crew skills, roles file and crew dirs as the
    installing profile: a clone carries the enabled list but not the plugin itself, and without
    it the role guards (budget hard stop, verifier read-only) and the card tool do not exist.
    Then cut its skills dir down to what the role uses (step_role_skills, crew-created profiles only)."""
    done = []
    for step in (step_plugin, step_skills, step_scripts, step_old_shim, step_roles, step_crew_dirs,
                 lambda h_, a_: step_role_skills(h_, tpl, source_home, a_, owned)):
        try:
            status, detail = step(home, True)
            if status == "CHANGED":
                done.append(detail.split(" - ")[0])
        except Exception as exc:
            done.append("%s failed: %s" % (getattr(step, "__name__", "step"), exc))
    if not _plugin_enabled(name):
        h(name, "plugins", "enable", "crew", "--no-allow-tool-override")
        done.append("plugin enabled")
    return done


def step_profiles(source_profile, prefix, apply, no_profiles=False):
    if no_profiles:
        return "SKIP", "role profiles (--no-profiles)"
    plans = _role_plans(prefix)
    if not plans:
        return "SKIP", "no templates/profiles in the package"
    todo = []
    for role, name, home, tpl in plans:
        exists = os.path.isdir(home)
        soul = os.path.join(tpl, "SOUL.md")
        rec = _shipped_record(home) if exists else {}
        shipped = Path(soul).read_text() if os.path.exists(soul) else ""
        cur = None
        if exists and os.path.exists(os.path.join(home, "SOUL.md")):
            cur = Path(os.path.join(home, "SOUL.md")).read_text()
        # Write SOUL.md when the profile is new, or when the file is still the one we shipped.
        soul_need = (not exists) or (cur != shipped and rec.get("SOUL.md") == _sha(cur or ""))
        settings_need = exists and bool(settings_problems(name, role, tpl))
        # A role profile holds its own copy of the plugin (scripts included), skills and roles file; a clone
        # carries none of them, and a package update has to reach the role copies too.
        provision_need = exists and not (
            # The plugin copy is compared file for file, not by existence: a package update that only
            # touched __init__.py (a new slash command, say) left the role copies stale while this step
            # said "up to date", and the parity proof then failed on 5 profiles. The plugin IS the
            # package root, so its files are compared against plugins/crew/ in the profile.
            _tree_ok(str(SRC_DIR), os.path.join(home, "plugins", "crew"), PLUGIN_FILES)
            and not _stale_scripts(os.path.join(home, "scripts"))
            and not os.path.lexists(os.path.join(home, "scripts", OLD_PROOFS_SHIM))
            and _tree_ok(str(SRC_DIR / "roles"), os.path.join(home, "roles", "crew"), ROLE_FILES)
            and (not crew_owned(home)
                 or not any(role_skills_todo(home, tpl, resolve_profile_home(source_profile)))))
        if soul_need or settings_need or provision_need:
            todo.append((role, name, home, tpl, exists))
    if not todo:
        return "OK", "role profiles (%s)" % ", ".join(p[1] for p in plans)
    if not apply:
        return "CHANGED", "role profiles -> " + ", ".join(
            ("create " if not t[4] else "update ") + t[1] for t in todo)
    done = []
    for role, name, home, tpl, existed in todo:
        if not os.path.isdir(home):
            # --clone-from: Hermes has no partial clone. The role needs the provider credentials (.env) and, through
            # config.yaml, the owner's shell-hook gates; both come with the clone, which also copies SOUL.md (replaced
            # below), skills (cut to skills/crew below) and memories/MEMORY.md + USER.md. Channels are stripped by Hermes.
            r = h(source_profile, "profile", "create", name, "--clone-from", source_profile,
                  "--description", ROLE_DESCS.get(role, ""))
            if r.returncode != 0:
                print("  profile create %s failed: %s" % (name, ((r.stderr or r.stdout).strip().splitlines() or ["?"])[-1]))
        if not os.path.isdir(home):
            done.append("%s FAILED" % name)
            continue
        owned = (not existed) or crew_owned(home)
        os.makedirs(os.path.join(home, "crew"), exist_ok=True)
        rec = _shipped_record(home)
        soul_src = os.path.join(tpl, "SOUL.md")
        if os.path.exists(soul_src):
            shipped = Path(soul_src).read_text()
            dst = os.path.join(home, "SOUL.md")
            cur = Path(dst).read_text() if os.path.exists(dst) else None
            if (not existed) or cur == shipped or rec.get("SOUL.md") == _sha(cur or ""):
                Path(dst).write_text(shipped)
                rec["SOUL.md"] = _sha(shipped)
        keys = _apply_settings(name, os.path.join(tpl, "settings.conf"))
        rec["settings"] = keys
        rec["provisioned"] = _provision_role_profile(name, home, tpl, resolve_profile_home(source_profile), owned)
        Path(os.path.join(home, SHIPPED_RECORD)).write_text(json.dumps(rec, indent=2, sort_keys=True))
        done.append(name if not existed else "%s (%s)" % (name, ",".join(keys) or "up to date"))
    return "CHANGED", "role profiles -> " + ", ".join(done)


def _steps(profile_home, profile, args):
    return [
        ("plugin", lambda a: step_plugin(profile_home, a)),
        ("skills", lambda a: step_skills(profile_home, a)),
        ("scripts", lambda a: step_scripts(profile_home, a)),
        ("roles", lambda a: step_roles(profile_home, a)),
        ("crew-dirs", lambda a: step_crew_dirs(profile_home, a)),
        ("owner", lambda a: step_owner(profile, a, getattr(args, "owner", False))),
        ("enable", lambda a: step_enable(profile, a)),
        ("config", lambda a: step_config(profile_home, profile, a)),
        ("spill-cap", lambda a: step_spill_cap(profile, a, args.spill_cap)),
        ("chat-kanban", lambda a: step_chat_kanban(profile, a, args.chat_kanban)),
        ("menu-priority", lambda a: step_menu_priority(profile, a, args.telegram_menu)),
        ("profiles", lambda a: step_profiles(profile or "default", args.profile_prefix, a, args.no_profiles)),
        ("other-copies", lambda a: step_other_copies(profile_home, args.profile_prefix, a)),
        ("prompt-budget", lambda a: step_prompt_budget(args.profile_prefix, a)),
        ("permissions", lambda a: step_permissions(profile_home, profile, args.profile_prefix, a)),
        ("graph-http", lambda a: step_graph_unit(profile_home, a, args.no_service, args.graph_port)),
        ("proofs-board", lambda a: step_proofs_board(a, args.nightly_proofs and not args.no_cron)),
        ("proofs-cron", lambda a: step_proofs_cron(profile, profile_home, a, args.no_cron, args.nightly_proofs,
                                                   args.proofs_deliver)),
        ("retire-crons", lambda a: step_retire_crons(profile, a, args.no_cron)),
    ]


def report(profile, profile_home, args):
    print("== readiness ==")
    print("plugin: crew %s" % ("enabled" if _plugin_enabled(profile) else "NOT enabled"))
    print("commands: /crew <ask> (intake) | /crew-diagnose [state] (read-only pass, a skill) | "
          "/crew-<option>: status|graph|stop")
    for role, name, home, _tpl in _role_plans(args.profile_prefix):
        print("role profile: %s (%s)" % (name, "present" if os.path.isdir(home) else "MISSING"))
    for line in prompt_report(args.profile_prefix)[0]:
        print(line)
    graph_path = plugin_script(profile_home, "crew_graph.py")
    print("graph script: %s (%s)" % (graph_path, "present" if os.path.exists(graph_path) else "MISSING"))
    roles_path = os.path.join(profile_home, "roles", "crew", "roles.json")
    print("roles file: %s (%s)" % (roles_path, "present" if os.path.exists(roles_path) else "MISSING"))
    if args.no_service:
        print("graph http: skipped (--no-service)")
    else:
        gact = subprocess.run(["systemctl", "--user", "is-active", UNIT_GRAPH_NAME],
                              capture_output=True, text=True).stdout.strip()
        name = _ts_name()
        local = "http://127.0.0.1:%d/" % args.graph_port
        print("graph http state: %s (%s)" % (gact or "unknown", local))
        if name:
            print("tailnet publish: tailscale serve --bg --https 8445 %s" % local)
            print("tailnet url: https://%s:8445/" % name)
    if args.no_cron:
        print("proofs cron: skipped (--no-cron)")
    else:
        pcid = _cron_id(profile, CRON_PROOFS_NAME)
        print("proofs cron: %s" % (pcid or "not registered (--nightly-proofs registers it)"))


def main():
    ap = argparse.ArgumentParser(description="Install the crew plugin package into a profile.")
    ap.add_argument("--profile", default=None)
    ap.add_argument("--owner", action="store_true",
                    help="make --profile the owner profile even when another one is recorded")
    ap.add_argument("--check", action="store_true", help="print what would change, change nothing")
    ap.add_argument("--no-service", action="store_true",
                    help="write no systemd unit (the local dashboard unit)")
    ap.add_argument("--no-cron", action="store_true",
                    help="touch no cron job: no nightly proofs even with --nightly-proofs, and the old "
                         "heal/observer jobs are not retired")
    ap.add_argument("--nightly-proofs", action="store_true",
                    help="register the nightly proofs cron (03:00) and the crew-proofs board it runs on")
    ap.add_argument("--proofs-deliver", default=CRON_PROOFS_DELIVER, metavar="TARGET",
                    help="where the nightly proofs job delivers its output (default %s: the cron's own output; "
                         "any Hermes delivery target, e.g. telegram or platform:chat_id)" % CRON_PROOFS_DELIVER)
    ap.add_argument("--chat-kanban", action="store_true",
                    help="turn the kanban toolset on for zulip and telegram so /crew can open a card there")
    ap.add_argument("--telegram-menu", action="store_true",
                    help="put /crew first in the telegram command menu")
    ap.add_argument("--spill-cap", action="store_true",
                    help="raise hooks.output_spill.max_chars on the installing profile above the /crew preload")
    ap.add_argument("--graph-port", type=int, default=GRAPH_PORT,
                    help="local port for the crew graph http service (default %d)" % GRAPH_PORT)
    ap.add_argument("--https-port", type=int, default=8445,
                    help="tailnet https port used with --publish (default 8445)")
    ap.add_argument("--publish", action="store_true",
                    help="also publish the graph over the tailnet with tailscale serve (only --publish-user gets in)")
    ap.add_argument("--publish-user", default="",
                    help="the tailnet login allowed on the published dashboard (default: the tailnet's one human login)")
    ap.add_argument("--publish-tag", default="",
                    help="tailnet device tags also allowed, comma list (e.g. tag:admin): a tagged device has no login")
    ap.add_argument("--no-profiles", action="store_true",
                    help="do not create/update the role profiles from templates/")
    ap.add_argument("--profile-prefix", default="crew-",
                    help="name prefix for the role profiles (default crew-)")
    args = ap.parse_args()
    global PROFILE_PREFIX
    PROFILE_PREFIX = args.profile_prefix

    profile_home = resolve_profile_home(args.profile)
    profile = (args.profile or "").strip()
    steps = _steps(profile_home, profile, args)

    if args.check:
        print("crew %s (installed %s)" % (
            _plugin_version(os.path.join(SRC_DIR, "plugin.yaml")) or "?",
            _plugin_version(os.path.join(profile_home, "plugins", "crew", "plugin.yaml")) or "?"))
        needed = []
        for name, fn in steps:
            status, detail = fn(False)
            if status in ("CHANGED", "FAILED"):
                needed.append((name, detail))
        if not args.no_profiles:
            for line in prompt_report(args.profile_prefix)[0]:
                print(line)
        if not needed:
            print("crew check: complete - nothing to change")
            return 0
        for name, detail in needed:
            print("would change: %s - %s" % (name, detail))
            if name == "graph-http":
                print(render_graph_unit(profile_home, args.graph_port))
        print("%d change(s) needed" % len(needed))
        return 1

    if args.publish and not args.no_service:
        hosts, user, err = publish_settings(_ts_name(), args.publish_user)
        if err:
            print("publish refused: %s - nothing was changed" % err)
            return 1
        # the unit carries the host and the login, so the published dashboard answers only its owner
        tags = ",".join(t.strip() for t in args.publish_tag.split(",") if t.strip())
        _owner_record_set(publish_hosts="%s,%s:%d" % (hosts, hosts, args.https_port), publish_users=user,
                          publish_tags=tags)

    print("crew installer -> %s" % profile_home)
    for name, fn in steps:
        status, detail = fn(True)
        print("%s %s - %s" % (status, name, detail))
    print("---")
    r = h(profile, "plugins", "doctor", "crew")
    print((r.stdout or "").strip())
    if args.publish and not args.no_service:
        target = "http://127.0.0.1:%d" % args.graph_port
        pub = subprocess.run(["tailscale", "serve", "--bg", "--https", str(args.https_port), target],
                             capture_output=True, text=True)
        print("publish: %s" % ((pub.stdout or pub.stderr or "").strip().splitlines()[-1:] or ["?"])[0])
        name = _ts_name()
        if pub.returncode == 0 and name:      # card links in the owner's messages and the board header point here
            _owner_record_set(dashboard_url="https://%s:%d" % (name, args.https_port))
    report(profile, profile_home, args)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("crew installer error: %s: %s" % (type(exc).__name__, exc))
        sys.exit(2)
