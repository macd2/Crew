#!/usr/bin/env python3
"""Crew lineups: a JSON file that names the writer roles of a crew (the coordinator and verifier are always the
shipped ones). This module finds, validates, previews, fetches and builds lineups.

A lineup lives at <crew folder>/lineups/<name>.json; the package ships its own in <package>/crew-home/lineups/
(the installer copies them into <crew folder>/lineups/), and a name falls back to those. build() turns one into an overlay at
<crew folder>/lineup-build/<name>/ holding the roles.json, briefs, profile templates and role skills the
installer then uses instead of the shipped ones.
`*_file` keys are paths relative to the crew folder only (<base Hermes home>/crew).

Run:  python3 crew_lineup.py {list | show NAME | validate NAME | build NAME | state}
"""
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.parse
import urllib.request

HERE_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LINEUP_NAME_RX = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
ROLE_NAME_RX = re.compile(r"^[a-z]{2,24}$")
TOOLSET_RX = re.compile(r"^[a-z0-9_-]+$")
SKILL_PATH_RX = re.compile(r"^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$")
RESERVED_LINEUPS = ("default",)
RESERVED_ROLES = ("coordinator", "verifier", "all")
TASK_CLASSES = ("code", "write", "review")
DEFAULT_TOOLSETS = ("terminal", "file", "web", "kanban", "crew")
FORCED_TOOLSETS = ("kanban", "crew")
MAX_ROLES = 12
MAX_JSON = 256 * 1024
MAX_FILE = 64 * 1024
FETCH_TIMEOUT = 20
TEXTS = ("soul", "brief", "skill")
TOP_KEYS = ("name", "description", "inherit", "roles")
ROLE_KEYS = ("name", "purpose", "description", "artifact", "proof", "task_class", "model", "provider", "base_url",
             "toolsets", "no_toolsets", "budget_tokens", "max_turns", "skills_extra", "inherit",
             "soul", "soul_file", "brief", "brief_file", "skill", "skill_file")
# What a role profile takes from which profile (it is created bare): `env` its credentials (.env and the credential
# sections of config.yaml), `hooks` the shell hooks, `skills` skills beyond the crew's own, `mcp` MCP servers. env and
# hooks: a profile name ("owner" = the crew's owner profile) or false. skills and mcp, the sets, also take a list (exactly
# those items: "name" from the owner, "profile/name" from that profile) or {"from": profile|false, "add": [items],
# "drop": [names]}. The top-level block applies to every role, a role's own block overrides it key by key.
INHERIT_KEYS = ("env", "hooks", "skills", "mcp")
INHERIT_SETS = ("skills", "mcp")
SET_KEYS = ("from", "add", "drop")
INHERIT_DEFAULTS = {"env": "owner", "hooks": "owner", "skills": False, "mcp": False}
PROFILE_RX = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
MCP_NAME_RX = re.compile(r"^[A-Za-z0-9_.-]+$")
SKILL_NAME_RX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
SET_WHAT = {"skills": "skill", "mcp": "MCP server"}


class LineupError(Exception):
    pass


def _crew_card():
    """scripts/crew_card.py, imported with this directory on sys.path for the length of the import (this module is
    also loaded by file path inside the Hermes process, where its siblings are not importable by name)."""
    here = os.path.dirname(os.path.abspath(__file__))
    added = here not in sys.path
    if added:
        sys.path.insert(0, here)
    try:
        import crew_card
    finally:
        if added and here in sys.path:
            sys.path.remove(here)
    return crew_card


def _is_package(d):
    return bool(d) and os.path.isfile(os.path.join(d, "roles", "roles.json")) \
        and os.path.isdir(os.path.join(d, "templates", "lineup"))


def package_dir():
    """The crew package checkout holding roles/, templates/ and crew-home/lineups/. A profile's plugin copy
    ($HERMES_HOME/plugins/crew) has none of them, so: config `crew.source_dir` (the installer records it in every
    crew profile, then the owner's), else the folder above scripts/ when it is a package, else crew_card's
    package_dir(). Raises LineupError when none is."""
    cc = _crew_card()
    cands = [cc.config_value("source_dir")]
    try:
        cands.append(cc.config_value("source_dir", home=cc.owner_home()))
    except Exception:
        pass
    cands += [HERE_PKG]
    try:
        cands.append(cc.package_dir())
    except Exception:
        pass
    for c in cands:
        if c and _is_package(os.path.expanduser(c)):
            return os.path.abspath(os.path.expanduser(c))
    raise LineupError("crew package not found (config crew.source_dir is unset or not a crew checkout)")


def crew_dir():
    return os.path.join(_crew_card().base_home(), "crew")


def _shipped_roles():
    with open(os.path.join(package_dir(), "roles", "roles.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _template(name):
    with open(os.path.join(package_dir(), "templates", "lineup", name), encoding="utf-8") as fh:
        return fh.read()


def _fill(text, name, purpose):
    return text.replace("{Name}", name.capitalize()).replace("{name}", name).replace("{purpose}", purpose)


def _version():
    try:
        with open(os.path.join(package_dir(), "plugin.yaml"), encoding="utf-8") as fh:
            m = re.search(r"^version:\s*(\S+)", fh.read(), re.M)
        return m.group(1) if m else ""
    except OSError:
        return ""


# ---------------------------------------------------------------- finding

def _is_pathish(s):
    return s.endswith(".json") or "/" in s or os.sep in s or s.startswith(".")


def shipped_dir():
    """The lineups the package ships: <package>/crew-home/lineups/, a mirror of <crew folder>/lineups/ that the
    installer copies them into. Looked up after the owner's own folder, so a name works before the first install."""
    return os.path.join(package_dir(), "crew-home", "lineups")


def _search_dirs():
    dirs = [(os.path.join(crew_dir(), "lineups"), "user")]
    try:
        dirs.append((shipped_dir(), "package"))
    except LineupError:
        pass
    return dirs


def find(name_or_path):
    """Absolute path of a lineup json: a path as given, else <crew>/lineups/<name>.json, else the package's."""
    s = str(name_or_path or "").strip()
    if not s:
        raise LineupError("no lineup named")
    if _is_pathish(s):
        p = os.path.abspath(os.path.expanduser(s))
        if not os.path.isfile(p):
            raise LineupError("lineup file not found: %s" % p)
        return p
    if s in RESERVED_LINEUPS:
        raise LineupError("'default' is the shipped crew (worker + content), not a lineup file")
    if not LINEUP_NAME_RX.match(s):
        raise LineupError("bad lineup name %r (lowercase letters, digits, '-', max 32)" % s)
    for d, _src in _search_dirs():
        p = os.path.join(d, s + ".json")
        if os.path.isfile(p):
            return os.path.abspath(p)
    raise LineupError("no lineup %r (looked in %s)" % (s, ", ".join(d for d, _ in _search_dirs())))


def _read_json(path):
    try:
        if os.path.getsize(path) > MAX_JSON:
            raise LineupError("%s: larger than %d KB" % (path, MAX_JSON // 1024))
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, UnicodeDecodeError, ValueError) as e:
        raise LineupError("%s: cannot read lineup json: %s" % (path, e))


# ---------------------------------------------------------------- validation

def _check_rel(path):
    """The textual refusals of a *_file path; '' when acceptable."""
    if not isinstance(path, str) or not path.strip():
        return "must be a non-empty relative path"
    p = path.replace("\\", "/")
    if p.startswith("~"):
        return "'~' is not allowed (paths are relative to the crew folder)"
    if p.startswith("/") or os.path.isabs(path) or re.match(r"^[A-Za-z]:", p):
        return "absolute paths are not allowed (paths are relative to the crew folder)"
    norm = os.path.normpath(p)
    if norm == ".." or norm.startswith("../") or norm.startswith(".." + os.sep):
        return "leaves the crew folder"
    return ""


def _read_rel(root, path):
    """(text, error) for a *_file path under root, symlinks resolved."""
    err = _check_rel(path)
    if err:
        return None, err
    base = os.path.realpath(root)
    full = os.path.realpath(os.path.join(base, path.replace("\\", "/")))
    if full != base and not full.startswith(base.rstrip(os.sep) + os.sep):
        return None, "leaves the crew folder (resolves to %s)" % full
    if not os.path.isfile(full):
        return None, "file not found: %s" % full
    if os.path.getsize(full) > MAX_FILE:
        return None, "larger than %d KB" % (MAX_FILE // 1024)
    try:
        with open(full, "rb") as fh:
            return fh.read().decode("utf-8"), ""
    except UnicodeDecodeError:
        return None, "not UTF-8 text"
    except OSError as e:
        return None, "cannot read: %s" % e


def _one_line(v):
    return isinstance(v, str) and v.strip() != "" and "\n" not in v and "\r" not in v


def _pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def _default_sources():
    """How a lineup finds the profiles its inherit blocks name: {home_of(profile) -> its home, servers_of(profile) ->
    its config.yaml mcp_servers mapping, or None when it cannot be read}. "owner" is the crew's owner profile."""
    cc = _crew_card()
    return {"home_of": lambda p: cc.owner_home() if p == "owner" else cc.profile_home(p),
            "servers_of": lambda p: yaml_section(cc.owner_home() if p == "owner" else cc.profile_home(p),
                                                 "mcp_servers")}


def yaml_section(home, key):
    """A top-level section of <home>/config.yaml as written ({} when the file or the key is absent); None when there is
    no yaml module to read it with (then whatever needs it checks it later, the installer reads with Hermes's python)."""
    try:
        import yaml
    except ImportError:
        return None
    try:
        with open(os.path.join(home, "config.yaml"), encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, yaml.YAMLError):
        return None
    return data.get(key) if isinstance(data, dict) else None


def _source_name(p):
    return isinstance(p, str) and p not in ("false", "true") and bool(PROFILE_RX.match(p))


def _set_item(key, item):
    """(source profile, name) of one list/add item, or None when it is not "name" or "profile/name"."""
    if not isinstance(item, str):
        return None
    src, _, name = item.rpartition("/")
    if (src and not _source_name(src)) or name in (".", "..") \
            or not (SKILL_NAME_RX if key == "skills" else MCP_NAME_RX).match(name):
        return None
    return src or "owner", name


def _inherit(v, where, errs, exists):
    """The keys an `inherit` block sets, normalized ({} when absent); every problem appended to errs. A value is False, a
    profile name, and for the sets a list of items or {"from", "add", "drop"} (both kept as given, deduplicated).
    exists(profile) says whether a named profile is there ("owner" always is)."""
    if v is None:
        return {}
    if not isinstance(v, dict):
        errs.append("%s: inherit must be an object with keys %s" % (where, ", ".join(INHERIT_KEYS)))
        return {}
    out = {}

    def profile(k, p, what):
        if not _source_name(p):
            errs.append("%s: inherit.%s %s %r: must be a profile name or \"owner\"" % (where, k, what, p))
            return False
        if p != "owner" and not exists(p):
            errs.append("%s: inherit.%s: no Hermes profile %r" % (where, k, p))
            return False
        return True

    def items(k, val, what):
        if not isinstance(val, list):
            errs.append("%s: inherit.%s%s must be a list" % (where, k, what))
            return None
        bad = [x for x in val if _set_item(k, x) is None]
        if bad:
            errs.append("%s: inherit.%s%s must list %s names, \"name\" (from the owner) or \"profile/name\": %s" % (
                where, k, what, SET_WHAT[k], ", ".join(repr(x) for x in bad)))
            return None
        ok = all([profile(k, _set_item(k, x)[0], "item %r: profile" % x) for x in val])
        return list(dict.fromkeys(val)) if ok else None

    for k, val in v.items():
        if k not in INHERIT_KEYS:
            errs.append("%s: inherit has unknown key %r (keys: %s)" % (where, k, ", ".join(INHERIT_KEYS)))
            continue
        kinds = "a profile name, \"owner\" or false" + (
            ", a list of names or {\"from\", \"add\", \"drop\"}" if k in INHERIT_SETS else "")
        if val is False:
            out[k] = False
        elif isinstance(val, str) and val.strip():
            p = val.strip()
            if p in ("false", "true") or not PROFILE_RX.match(p):
                errs.append("%s: inherit.%s %r: must be %s" % (where, k, val, kinds))
            elif profile(k, p, "profile"):
                out[k] = p
        elif isinstance(val, list) and k in INHERIT_SETS:
            got = items(k, val, "")
            if got is not None:
                out[k] = got or False      # [] = exactly nothing = false
        elif isinstance(val, dict) and k in INHERIT_SETS:
            unknown = [x for x in val if x not in SET_KEYS]
            if unknown:
                errs.append("%s: inherit.%s has unknown key %s (keys: %s)" % (
                    where, k, ", ".join(repr(x) for x in unknown), ", ".join(SET_KEYS)))
                continue
            if "from" not in val:
                errs.append("%s: inherit.%s needs \"from\": a profile name, \"owner\" or false" % (where, k))
                continue
            frm = val["from"]
            if frm is not False and not (isinstance(frm, str) and profile(k, frm, "from")):
                if not isinstance(frm, str):
                    errs.append("%s: inherit.%s.from must be a profile name, \"owner\" or false" % (where, k))
                continue
            add = items(k, val.get("add", []), ".add")
            drop = val.get("drop", [])
            if not isinstance(drop, list) or not all(
                    isinstance(x, str) and (SKILL_NAME_RX if k == "skills" else MCP_NAME_RX).match(x)
                    and x not in (".", "..") for x in drop):
                errs.append("%s: inherit.%s.drop must list %s names (no profile/)" % (where, k, SET_WHAT[k]))
                continue
            if add is not None:
                out[k] = {"from": frm, "add": add, "drop": list(dict.fromkeys(drop))}
        else:
            errs.append("%s: inherit.%s must be %s" % (where, k, kinds))
    return out


def skill_names(home):
    """{skill name: path under <home>/skills} of every skill a profile has (a folder holding a SKILL.md), crew's own
    (skills/crew/) and hidden folders left out; the first in sorted order wins a name two categories share."""
    root = os.path.join(home, "skills")
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and not (rel == "." and d == "crew"))
        if rel != "." and "SKILL.md" in filenames:
            out.setdefault(os.path.basename(dirpath), rel)
            dirnames[:] = []
        elif rel.count("/") >= 3:
            dirnames[:] = []
    return out


def _who(p):
    return "the owner profile" if p == "owner" else "profile %r" % p


def resolve_set(key, spec, sources):
    """What an inherit.skills / inherit.mcp value comes to: ({name: (profile, what)}, [problems]), in merge order - the
    `from` profile's set, then each added item (an added name replaces an inherited one of the same name; the first add
    of a name wins), then the drops. what = the path under the profile's skills/ (skills), the server's config (mcp).
    A profile whose MCP servers cannot be read here is not checked (the installer checks it)."""
    if spec is False:
        return {}, []
    if isinstance(spec, str):
        spec = {"from": spec, "add": [], "drop": []}
    elif isinstance(spec, list):
        spec = {"from": False, "add": spec, "drop": []}
    spec = {"from": spec.get("from", False), "add": spec.get("add", []), "drop": spec.get("drop", [])}
    errs, cache = [], {}

    def members(p):
        if p not in cache:
            if key == "skills":
                cache[p] = skill_names(sources["home_of"](p))
            else:
                got = sources["servers_of"](p)
                cache[p] = None if got is None else (got if isinstance(got, dict) else {})
        return cache[p]

    out, unchecked = {}, False
    if spec["from"]:
        m = members(spec["from"])
        unchecked = m is None
        for n in sorted(m or {}):
            out[n] = (spec["from"], m[n])
    added = set()
    for item in spec["add"]:
        src, name = _set_item(key, item)
        if name in added:
            continue
        m = members(src)
        if m is None:
            unchecked = True
            out[name] = (src, None)
        elif name not in m:
            errs.append("inherit.%s: %s has no %s %r" % (key, _who(src), SET_WHAT[key], name))
            continue
        else:
            out[name] = (src, m[name])
        added.add(name)
    for name in spec["drop"]:
        if name in out:
            del out[name]
        elif not unchecked:
            errs.append("inherit.%s: drop %r is not in the set (%s)" % (key, name, ", ".join(sorted(out)) or "empty"))
    return out, errs


def conf_value(text):
    """One settings.conf inherit value: false/empty -> False, a JSON list or object, a bare [a,b] list, else the text."""
    v = (text or "").strip()
    if v in ("", "false"):
        return False
    if v[:1] in "[{":
        try:
            return json.loads(v)
        except ValueError:
            if v[:1] == "[":
                return [x.strip() for x in v.strip("[]").split(",") if x.strip()] or []
    return v


def conf_inherit(pairs, exists, where="settings.conf"):
    """({env, hooks, skills, mcp} with the defaults for what is not named, [problems]) of the inherit.* lines among
    settings.conf (key, value) pairs."""
    errs = []
    raw = {k[len("inherit."):]: conf_value(v) for k, v in pairs if k.startswith("inherit.")}
    out = dict(INHERIT_DEFAULTS)
    out.update(_inherit(raw, where, errs, exists))
    return out, errs


def _validate(data, default_name, files_root, sources=None):
    """(normalized dict, [problems])."""
    errs = []
    sources = sources or _default_sources()

    def exists(p):
        return os.path.isdir(sources["home_of"](p))
    if not isinstance(data, dict):
        return None, ["lineup must be a JSON object"]
    for k in data:
        if k not in TOP_KEYS:
            errs.append("unknown key %r at top level" % k)
    name = data.get("name", default_name)
    if not isinstance(name, str) or not LINEUP_NAME_RX.match(name):
        errs.append("lineup name %r: must match ^[a-z][a-z0-9-]{0,31}$" % (name,))
    elif name in RESERVED_LINEUPS:
        errs.append("lineup name 'default' is reserved (the shipped crew)")
    desc = data.get("description", "")
    if not isinstance(desc, str):
        errs.append("description must be a string")
        desc = ""
    roles = data.get("roles")
    if not isinstance(roles, list) or not roles:
        errs.append("roles must be a non-empty list (1..%d writer roles)" % MAX_ROLES)
        roles = []
    elif len(roles) > MAX_ROLES:
        errs.append("too many roles: %d (max %d)" % (len(roles), MAX_ROLES))
    top_inherit = _inherit(data.get("inherit"), "top level", errs, exists)
    shipped = _shipped_roles()
    worker = next((r for r in shipped.get("roles", []) if r.get("name") == "worker"), {})
    default_budget = shipped.get("default_budget_tokens", 1500000)
    seen = set()
    out_roles = []
    for i, r in enumerate(roles):
        if not isinstance(r, dict):
            errs.append("role #%d: must be an object" % (i + 1))
            continue
        rn = r.get("name")
        label = "role %r" % rn if isinstance(rn, str) and rn else "role #%d" % (i + 1)
        if not isinstance(rn, str) or not ROLE_NAME_RX.match(rn):
            errs.append("%s: name must be 2-24 lowercase letters (^[a-z]{2,24}$)" % label)
        elif rn in RESERVED_ROLES:
            errs.append("%s: name is reserved (%s)" % (label, ", ".join(RESERVED_ROLES)))
        elif rn in seen:
            errs.append("%s: duplicate role name" % label)
        seen.add(rn)
        for k in r:
            if k not in ROLE_KEYS:
                errs.append("%s: unknown key %r" % (label, k))
        purpose = r.get("purpose")
        if not _one_line(purpose):
            errs.append("%s: purpose is required (one line of text)" % label)
            purpose = ""
        purpose = purpose.strip()
        rn_s = rn if isinstance(rn, str) else ""
        n = {"name": rn_s, "purpose": purpose}
        for k, dflt in (("description", "Crew %s: %s" % (rn_s, purpose)),
                        ("artifact", worker.get("artifact", "")), ("proof", worker.get("proof", ""))):
            v = r.get(k, dflt)
            if not _one_line(v):
                errs.append("%s: %s must be one line of text" % (label, k))
                v = dflt
            n[k] = v.strip()
        tc = r.get("task_class", "code")
        if tc not in TASK_CLASSES:
            errs.append("%s: task_class must be one of %s" % (label, "|".join(TASK_CLASSES)))
            tc = "code"
        n["task_class"] = tc
        for k in ("model", "provider", "base_url"):
            v = r.get(k)
            if v is not None and (not _one_line(v) or re.search(r"[\s\[\],]", v.strip())):
                errs.append("%s: %s must be a single word/URL" % (label, k))
                v = None
            n[k] = v.strip() if isinstance(v, str) else None
        for k in ("toolsets", "no_toolsets"):
            v = r.get(k, [])
            if not isinstance(v, list) or not all(isinstance(t, str) and TOOLSET_RX.match(t) for t in v):
                errs.append("%s: %s must be a list of toolset names (^[a-z0-9_-]+$)" % (label, k))
                v = []
            n[k] = list(v)
        for t in n["no_toolsets"]:
            if t in FORCED_TOOLSETS:
                errs.append("%s: no_toolsets may not remove %r (crew cards need kanban and crew)" % (label, t))
        tools = [t for t in DEFAULT_TOOLSETS if t not in n["no_toolsets"] or t in FORCED_TOOLSETS]
        tools += [t for t in n["toolsets"] if t not in tools]
        n["tools"] = tools
        for k, dflt in (("budget_tokens", default_budget), ("max_turns", None)):
            v = r.get(k, dflt)
            if v is not None and not _pos_int(v):
                errs.append("%s: %s must be a positive integer" % (label, k))
                v = dflt
            n[k] = v
        se = r.get("skills_extra", [])
        if not isinstance(se, list) or not all(isinstance(s, str) and SKILL_PATH_RX.match(s) and ".." not in s
                                               for s in se):
            errs.append("%s: skills_extra must be a list of skill paths such as category/skill" % label)
            se = []
        n["skills_extra"] = list(se)
        own = _inherit(r.get("inherit"), label, errs, exists)
        n["inherit"] = dict(INHERIT_DEFAULTS, **top_inherit)
        n["inherit"].update(own)
        for k in INHERIT_SETS:
            where = label if k in own else "top level"
            if k in own or k in top_inherit:
                for e in resolve_set(k, n["inherit"][k], sources)[1]:
                    if "%s: %s" % (where, e) not in errs:
                        errs.append("%s: %s" % (where, e))
        for t in TEXTS:
            parts = []
            fk = t + "_file"
            if fk in r:
                text, err = _read_rel(files_root, r[fk])
                if err:
                    errs.append("%s: %s %r: %s" % (label, fk, r[fk], err))
                elif text.strip():
                    parts.append(text.strip())
            if t in r:
                v = r[t]
                if not isinstance(v, str):
                    errs.append("%s: %s must be a string" % (label, t))
                elif len(v.encode("utf-8")) > MAX_FILE:
                    errs.append("%s: %s is larger than %d KB" % (label, t, MAX_FILE // 1024))
                elif v.strip():
                    parts.append(v.strip())
            n[fk] = r.get(fk)
            n[t] = r.get(t)
            n[t + "_text"] = "\n\n".join(parts) if parts else _fill(
                _template({"soul": "SOUL.md", "brief": "brief.md", "skill": "skill.md"}[t]), rn_s, purpose).strip()
        out_roles.append(n)
    return {"name": name, "description": desc.strip(), "inherit": top_inherit, "roles": out_roles}, errs


def _load(path, files_root=None, name=None, sources=None):
    data = _read_json(path)
    stem = os.path.splitext(os.path.basename(path))[0]
    if name and isinstance(data, dict):
        data = dict(data, name=name)
    out, errs = _validate(data, stem, files_root or crew_dir(), sources)
    if errs:
        raise LineupError("lineup %s has %d problem(s):\n" % (path, len(errs)) + "\n".join("- " + e for e in errs))
    out["source"] = path
    return out


def load(name_or_path, sources=None):
    """The validated, normalized lineup; LineupError lists every problem. sources: how the profiles named by its
    inherit blocks are found (_default_sources; the installer passes its own, with the profile it installs from)."""
    return _load(find(name_or_path), sources=sources)


# ---------------------------------------------------------------- build

def _conf_list(items):
    return "[" + ",".join(items) + "]"


def _inherit_conf(v):
    """One inherit value as settings.conf writes it: false, a profile name, [a,b] or the object as JSON (conf_value
    reads each back)."""
    if v is False:
        return "false"
    if isinstance(v, list):
        return _conf_list(v)
    return json.dumps(v, sort_keys=True) if isinstance(v, dict) else v


def _settings(role):
    with open(os.path.join(package_dir(), "templates", "profiles", "worker", "settings.conf"), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    subs = {"crew.role": role["name"], "platform_toolsets.cli": _conf_list(role["tools"])}
    for k in ("model", "provider", "base_url"):
        if role.get(k):
            subs["model.default" if k == "model" else "model." + k] = role[k]
    if role.get("max_turns"):
        subs["agent.max_turns"] = str(role["max_turns"])
    if role.get("skills_extra"):
        subs["skills_extra"] = _conf_list(role["skills_extra"])
    for k in INHERIT_KEYS:
        subs["inherit." + k] = _inherit_conf(role["inherit"][k])
    out, done = [], set()
    for ln in lines:
        m = re.match(r"^([A-Za-z0-9_.]+)\s*=\s*(.*)$", ln)
        if m and m.group(1) in subs:
            out.append("%s = %s" % (m.group(1), subs[m.group(1)]))
            done.add(m.group(1))
        elif m and m.group(1) == "agent.disabled_toolsets":
            # a toolset the role asks for is taken off the disabled list
            cur = [t.strip() for t in m.group(2).strip().strip("[]").split(",") if t.strip()]
            out.append("agent.disabled_toolsets = " + _conf_list([t for t in cur if t not in role["tools"]]))
        else:
            out.append(ln)
    out += ["%s = %s" % (k, v) for k, v in subs.items() if k not in done]
    return "\n".join(out) + "\n"


def _skill_md(role):
    rules = _fill(_template("writer-rules.md"), role["name"], role["purpose"]).strip()
    desc = "Crew %s pass: %s" % (role["name"], role["purpose"])
    head = "---\nname: crew-role-%s\ndescription: %s\n" % (role["name"], json.dumps(desc, ensure_ascii=False))
    v = _version()
    if v:
        head += "version: %s\n" % v
    body = [head + "---", "# Crew %s pass" % role["name"], role["purpose"], role["skill_text"], rules]
    return "\n\n".join(p for p in body if p) + "\n"


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _build_into(tmp, lu):
    shipped = _shipped_roles()
    core = {r.get("name"): r for r in shipped.get("roles", []) if isinstance(r, dict)}
    writers = []
    for r in lu["roles"]:
        writers.append({"name": r["name"], "kind": "writer", "task_class": r["task_class"], "purpose": r["purpose"],
                        "description": r["description"], "artifact": r["artifact"], "proof": r["proof"],
                        "tools_allowed": r["tools"], "model_class": "cheap", "brief": "briefs/%s.md" % r["name"],
                        "budget_tokens": r["budget_tokens"]})
    roles_json = dict(shipped)
    roles_json["roles"] = [core["coordinator"]] + writers + [core["verifier"]]
    roles_json["lineup"] = lu["name"]
    _write(os.path.join(tmp, "roles", "roles.json"), json.dumps(roles_json, indent=2, ensure_ascii=False) + "\n")
    for c in ("coordinator", "verifier"):
        os.makedirs(os.path.join(tmp, "roles", "briefs"), exist_ok=True)
        shutil.copy2(os.path.join(package_dir(), "roles", "briefs", c + ".md"), os.path.join(tmp, "roles", "briefs", c + ".md"))
        shutil.copytree(os.path.join(package_dir(), "templates", "profiles", c), os.path.join(tmp, "templates", "profiles", c))
    for r in lu["roles"]:
        _write(os.path.join(tmp, "roles", "briefs", r["name"] + ".md"), r["brief_text"] + "\n")
        _write(os.path.join(tmp, "templates", "profiles", r["name"], "SOUL.md"), r["soul_text"] + "\n")
        _write(os.path.join(tmp, "templates", "profiles", r["name"], "settings.conf"), _settings(r))
        _write(os.path.join(tmp, "skills", "crew-role-" + r["name"], "SKILL.md"), _skill_md(r))


def build(name_or_path, out_root=None, sources=None):
    """Write the overlay for a lineup to <out_root or crew/lineup-build>/<name>/, atomically; returns its path."""
    lu = load(name_or_path, sources)
    root = os.path.abspath(out_root or os.path.join(crew_dir(), "lineup-build"))
    os.makedirs(root, exist_ok=True)
    final = os.path.join(root, lu["name"])
    tmp = tempfile.mkdtemp(prefix="." + lu["name"] + ".tmp-", dir=root)
    try:
        _build_into(tmp, lu)
        old = None
        if os.path.exists(final):
            old = final + ".old-%d-%d" % (os.getpid(), int(time.time() * 1000))
            os.rename(final, old)
        os.rename(tmp, final)
        if old:
            shutil.rmtree(old, ignore_errors=True)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return final


# ---------------------------------------------------------------- listing, preview, state

def list_lineups():
    out, seen = [], set()
    for d, src in _search_dirs():
        try:
            names = sorted(f for f in os.listdir(d) if f.endswith(".json"))
        except OSError:
            continue
        for f in names:
            path = os.path.join(d, f)
            stem = f[:-5]
            entry = {"name": stem, "description": "", "roles": [], "source": src, "path": path}
            try:
                data = _read_json(path)
                if isinstance(data, dict):
                    entry["name"] = str(data.get("name") or stem)
                    entry["description"] = str(data.get("description") or "")
                    entry["roles"] = [str(r.get("name")) for r in data.get("roles") or [] if isinstance(r, dict)]
            except LineupError as e:
                entry["error"] = str(e)
            if entry["name"] in seen:
                continue
            seen.add(entry["name"])
            out.append(entry)
    return out


def _preview(lu):
    lines = ["Lineup %s%s" % (lu["name"], (": " + lu["description"]) if lu["description"] else ""),
             "Source: %s" % lu.get("source", ""),
             "Writer roles (%d), plus the shipped coordinator and verifier:" % len(lu["roles"])]
    for r in lu["roles"]:
        model = r.get("model") or "(template default)"
        if r.get("provider"):
            model += " via " + r["provider"]
        lines += ["", "== %s: %s" % (r["name"], r["purpose"]),
                  "task_class %s | model %s | toolsets %s | budget %s tokens%s" % (
                      r["task_class"], model, ",".join(r["tools"]), r["budget_tokens"],
                      (" | max_turns %d" % r["max_turns"]) if r.get("max_turns") else ""),
                  "artifact: %s" % r["artifact"], "proof: %s" % r["proof"]]
        if r["skills_extra"]:
            lines.append("skills_extra: %s" % ", ".join(r["skills_extra"]))
        lines.append("inherit: " + " | ".join("%s %s" % (k, _inherit_conf(r["inherit"][k])) for k in INHERIT_KEYS))
        for t in TEXTS:
            lines += ["--- %s%s" % (t, "" if (r.get(t) or r.get(t + "_file")) else " (generated)"), r[t + "_text"]]
    return "\n".join(lines) + "\n"


def preview(name_or_path):
    return _preview(load(name_or_path))


def _state_path():
    return os.path.join(crew_dir(), "lineup.json")


def read_state():
    """<crew>/lineup.json as a dict; {} when missing or unreadable (= the default crew)."""
    try:
        with open(_state_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(**fields):
    """Merge fields into <crew>/lineup.json (atomic write), stamping `updated`; returns the new state."""
    state = read_state()
    state.update(fields)
    state["updated"] = int(time.time())
    path = _state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".lineup.", dir=os.path.dirname(path))
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)
    return state


# ---------------------------------------------------------------- fetch / commit

def _is_url(s):
    return bool(re.match(r"^https?://", s or "", re.I))


def _http_get(url, limit):
    req = urllib.request.Request(url, headers={"User-Agent": "crew-lineup"})
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            data = resp.read(limit + 1)
    except Exception as e:
        raise LineupError("cannot fetch %s: %s" % (url, e))
    if len(data) > limit:
        raise LineupError("%s: larger than %d KB" % (url, limit // 1024))
    return data


def _pending_dir(name):
    return os.path.join(crew_dir(), "lineups", ".pending", name)


def fetch(src, dest_name=None):
    """Stage a lineup from an http(s) URL or a local path into <crew>/lineups/.pending/<name>/ (the json as
    <name>.json, every *_file under files/<relative path>). *_file entries come from the source's directory + the
    same relative path (for a local file in a `lineups/` folder, also from that folder's parent, the crew layout).
    Nothing outside .pending is written. Returns (name, preview_text)."""
    src = str(src or "").strip()
    if _is_url(src):
        raw = _http_get(src, MAX_JSON)
        stem = os.path.splitext(os.path.basename(urllib.parse.urlparse(src).path))[0]
    else:
        path = find(src) if not _is_pathish(src) else os.path.abspath(os.path.expanduser(src))
        if not os.path.isfile(path):
            raise LineupError("lineup file not found: %s" % path)
        if os.path.getsize(path) > MAX_JSON:
            raise LineupError("%s: larger than %d KB" % (path, MAX_JSON // 1024))
        with open(path, "rb") as fh:
            raw = fh.read()
        stem = os.path.splitext(os.path.basename(path))[0]
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise LineupError("%s: not a lineup json: %s" % (src, e))
    if not isinstance(data, dict):
        raise LineupError("%s: lineup must be a JSON object" % src)
    name = dest_name or data.get("name") or stem
    if not isinstance(name, str) or not LINEUP_NAME_RX.match(name) or name in RESERVED_LINEUPS:
        raise LineupError("bad lineup name %r (^[a-z][a-z0-9-]{0,31}$, not 'default')" % (name,))
    data["name"] = name
    rels, errs = [], []
    for r in data.get("roles") or []:
        if not isinstance(r, dict):
            continue
        for t in TEXTS:
            p = r.get(t + "_file")
            if p is None:
                continue
            err = _check_rel(p)
            if err:
                errs.append("role %r: %s_file %r: %s" % (r.get("name"), t, p, err))
            elif p not in rels:
                rels.append(p)
    if errs:
        raise LineupError("lineup %s has %d problem(s):\n" % (src, len(errs)) + "\n".join("- " + e for e in errs))
    stage = _pending_dir(name)
    shutil.rmtree(stage, ignore_errors=True)
    files = os.path.join(stage, "files")
    os.makedirs(files, exist_ok=True)
    try:
        for rel in rels:
            relp = os.path.normpath(rel.replace("\\", "/"))
            if _is_url(src):
                blob = _http_get(urllib.parse.urljoin(src, rel.replace("\\", "/")), MAX_FILE)
            else:
                blob = None
                roots = [os.path.dirname(path)]
                if os.path.basename(roots[0]) == "lineups":
                    roots.append(os.path.dirname(roots[0]))
                last = ""
                for root in roots:
                    text, err = _read_rel(root, rel)
                    if not err:
                        blob = text.encode("utf-8")
                        break
                    last = err
                if blob is None:
                    raise LineupError("%s: %s" % (rel, last))
            dst = os.path.join(files, relp)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as fh:
                fh.write(blob)
        jpath = os.path.join(stage, name + ".json")
        with open(jpath, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        lu = _load(jpath, files_root=files)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    lu["source"] = src
    return name, _preview(lu)


def commit_pending(name):
    """Move a fetched lineup into place: json -> <crew>/lineups/<name>.json, files -> their crew-relative paths.
    Returns {"path": <lineup json>, "files": [written paths], "overwritten": [paths that existed before]}."""
    stage = _pending_dir(name)
    jpath = os.path.join(stage, name + ".json")
    if not os.path.isfile(jpath):
        raise LineupError("nothing pending for %r (fetch it first)" % name)
    crew = crew_dir()
    files_root = os.path.join(stage, "files")
    moves = []
    for dirpath, _dirs, fnames in os.walk(files_root):
        for f in fnames:
            srcf = os.path.join(dirpath, f)
            moves.append((srcf, os.path.join(crew, os.path.relpath(srcf, files_root))))
    moves.append((jpath, os.path.join(crew, "lineups", name + ".json")))
    overwritten, written = [], []
    for srcf, dst in moves:
        if os.path.exists(dst):
            overwritten.append(dst)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(srcf, dst)
        written.append(dst)
    shutil.rmtree(stage, ignore_errors=True)
    return {"path": os.path.join(crew, "lineups", name + ".json"), "files": written, "overwritten": overwritten}


# ---------------------------------------------------------------- uninstall

def uninstall_plan(name):
    """What uninstalling lineup `name` takes away - the reverse of installing it - without changing anything:
    {"name", "roles": [role names], "dirs": [abs paths]}. The role profiles go (install.py --uninstall-lineup removes
    them, with their role skills in the other crew profiles); dirs is the lineup's build overlay. The lineup file and
    its *_file texts are the recipe: they always stay."""
    s = str(name or "").strip()
    if s in RESERVED_LINEUPS:
        raise LineupError("'default' is the shipped crew (worker + content); it cannot be uninstalled")
    path = find(s)
    try:
        data = _read_json(path)
    except LineupError:
        data = {}                    # an unreadable lineup can still be uninstalled by the roles it left
    stem = os.path.splitext(os.path.basename(path))[0]
    lname = str(data.get("name") or stem) if isinstance(data, dict) else stem
    roles = [str(r.get("name")) for r in (data.get("roles") if isinstance(data, dict) else None) or []
             if isinstance(r, dict) and isinstance(r.get("name"), str) and ROLE_NAME_RX.match(r["name"])]
    dirs = [d for d in {os.path.join(crew_dir(), "lineup-build", n) for n in (lname, stem)} if os.path.isdir(d)]
    return {"name": lname, "path": path, "roles": roles, "dirs": sorted(dirs)}


def remove_build(plan):
    """Delete the build overlay(s) of an uninstall plan. Never the lineup file."""
    for d in plan["dirs"]:
        shutil.rmtree(d, ignore_errors=True)


def describe_uninstall(plan, prefix="crew-"):
    """An uninstall plan as owner text."""
    lines = ["lineup %s (the lineup file %s stays):" % (plan["name"], plan["path"])]
    if plan["roles"]:
        lines.append("  role profiles removed entirely: %s" % ", ".join(prefix + r for r in plan["roles"]))
    for d in plan["dirs"]:
        lines.append("  build folder removed: %s" % d)
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    usage = "usage: crew_lineup.py {list|show NAME|validate NAME|build NAME|state|uninstall-plan NAME}"
    if not argv or argv[0] in ("-h", "--help"):
        print(usage)
        return 0 if argv else 2
    cmd, rest = argv[0], argv[1:]
    try:
        if cmd == "list":
            for e in list_lineups():
                print("%-16s %-8s %s%s" % (e["name"], e["source"], ",".join(e["roles"]),
                                           ("  - " + e["description"]) if e["description"] else ""))
                if e.get("error"):
                    print("  error: %s" % e["error"])
            return 0
        if cmd == "state":
            print(json.dumps(read_state() or {"active": "default"}, indent=2))
            return 0
        if cmd == "uninstall-plan" and len(rest) == 1:
            print(describe_uninstall(uninstall_plan(rest[0])))
            return 0
        if cmd in ("show", "validate", "build") and len(rest) == 1:
            if cmd == "show":
                sys.stdout.write(preview(rest[0]))
            elif cmd == "validate":
                lu = load(rest[0])
                print("ok: lineup %s, roles %s" % (lu["name"], ", ".join(r["name"] for r in lu["roles"])))
            else:
                print(build(rest[0]))
            return 0
    except LineupError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(usage, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
