#!/usr/bin/env python3
"""The crew's lessons file: what agents learned that the shipped skills do not say yet.

Lives at <base home>/crew/lessons.md - the crew data dir, never shipped, never touched by install.py, ignored by
crew_parity_check (which compares shipped files only). One lesson per line:

    - 2026-10-03 [content,verifier] A structural proof passing says nothing about whether citations are real ...

The plugin injects the lessons that apply to a role into that role's turn (and the `all` ones into /crew's intake).
Agents record one with the crew_lesson tool (role, text); they never edit a skill (an installed
skill is overwritten on the next install). A maintainer promotes a lesson into skills/ in a release.

Run:  python3 crew_lessons.py add --role content,verifier --text "..."   |   show --role content
"""
import argparse
import os
import re
import sys
import time

ROLES = ("worker", "content", "verifier", "coordinator", "all")   # the shipped crew: only a fallback; read known_roles()
MAX_ENTRIES = 50
MAX_BYTES = 8192
MAX_TEXT = 400
HEADER = ("# crew lessons\n\nRecorded with the crew_lesson tool; injected into the matching role's turn. "
          "Newest last; oldest are dropped past %d entries / %d KB.\n\n" % (MAX_ENTRIES, MAX_BYTES // 1024))
ENTRY_RX = re.compile(r"^- (\d{4}-\d{2}-\d{2}) \[([a-z,]+)\] (.+)$")


def _crew_card():
    """The sibling crew_card module. This module is loaded by file path inside the Hermes process, so its siblings
    are not importable by name until the scripts directory is on sys.path for the length of the import."""
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


def _base_home():
    """crew_card.base_home(), the one resolver (it knows Windows' %LOCALAPPDATA%\\hermes default)."""
    return _crew_card().base_home()


def known_roles():
    """Every role a lesson can name: the installed crew's roles (roles.json, read now) plus `all`."""
    try:
        return tuple(_crew_card().all_roles()) + ("all",)
    except Exception:  # noqa: BLE001 - an unreadable crew falls back to the shipped one
        return ROLES


def path():
    return os.path.join(_base_home(), "crew", "lessons.md")


def _parse_roles(roles):
    out = []
    known = known_roles()
    for r in re.split(r"[,\s]+", (roles or "").lower()):
        if not r:
            continue
        if r not in known:
            raise ValueError("unknown role %r (use: %s)" % (r, ", ".join(known)))
        if r not in out:
            out.append(r)
    if not out:
        raise ValueError("--role is required (%s)" % ", ".join(known))
    return ["all"] if "all" in out else out


def _agent_run():
    """True inside a dispatcher-spawned worker/verifier run or the coordinator's decision turn."""
    return bool(os.environ.get("HERMES_KANBAN_TASK") or os.environ.get("CREW_COORDINATOR_TURN"))


def entries():
    """[(date, [roles], text)] in file order; a missing or unreadable file is no lessons."""
    try:
        with open(path(), encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        m = ENTRY_RX.match(line)
        if m:
            out.append((m.group(1), m.group(2).split(","), m.group(3)))
    return out


def _line(e):
    return "- %s [%s] %s" % (e[0], ",".join(e[1]), e[2])


def add(roles, text):
    """Record a lesson. Returns 'added' or 'duplicate'. Identical (roles, text) is not recorded twice; past the cap
    the oldest entries go."""
    roles = _parse_roles(roles)
    if _agent_run() and roles == ["all"]:
        raise ValueError("an agent may not write `--role all` lessons (that channel reaches /crew's intake; "
                         "tag your own role instead and the owner promotes it)")
    text = " ".join((text or "").split())
    if not text:
        raise ValueError("--text is required")
    if len(text) > MAX_TEXT:
        raise ValueError("a lesson is one or two lines (%d characters max, got %d)" % (MAX_TEXT, len(text)))
    cur = entries()
    if any(e[1] == roles and e[2] == text for e in cur):
        return "duplicate"
    cur.append((time.strftime("%Y-%m-%d"), roles, text))
    cur = cur[-MAX_ENTRIES:]
    while len(cur) > 1 and len((HEADER + "\n".join(_line(e) for e in cur)).encode("utf-8")) > MAX_BYTES:
        cur.pop(0)
    os.makedirs(os.path.dirname(path()), exist_ok=True)
    tmp = path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(HEADER + "\n".join(_line(e) for e in cur) + "\n")
    os.replace(tmp, path())
    return "added"


def for_role(role):
    """The lesson texts that apply to one role: tagged with it, or `all`."""
    return [e[2] for e in entries() if role in e[1] or "all" in e[1]]


def block(role):
    """The <crew-lessons> context block for a role's turn; '' when none apply."""
    texts = for_role(role) if role in known_roles() else []
    if not texts:
        return ""
    return "<crew-lessons>\nLearned on earlier cards; apply them. Record a new one with " \
           "the crew_lesson tool, never by editing a skill.\n%s\n</crew-lessons>" % "\n".join("- " + t for t in texts)


def intake_block():
    """What /crew's intake gets: only the lessons for `all`."""
    texts = [e[2] for e in entries() if "all" in e[1]]
    if not texts:
        return ""
    return "<crew-lessons>\n%s\n</crew-lessons>" % "\n".join("- " + t for t in texts)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--role", required=True)
    a.add_argument("--text", required=True)
    s = sub.add_parser("show")
    s.add_argument("--role", required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "add":
            print("lesson %s: %s" % (add(args.role, args.text), path()))
        else:
            print(block(args.role))
    except ValueError as exc:
        print("refused: %s" % exc)
        return 4
    return 0


if __name__ == "__main__":
    import crew_proc
    crew_proc.utf8_stdio()
    sys.exit(main())
