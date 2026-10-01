"""Prove the intake fix: a vague `/crew <ask>` spends no research tool call and opens no card.

    python3 scripts/crew_intake_proof.py

Runs the real one-shot intake against a profile, then measures the session it created and the
board card count before and after. Exit 0 only when both hold.

The one call the intake may spend is `clarify`: the questions ARE the deliverable of that turn, and
they go through the tool so the owner answers a form instead of retyping the command. Anything
else - a board query, a file read, a search, a count - is research the vague ask does not license,
and fails this proof.

Zero research calls is a property of the profile's hook-output spill cap. The plugin hands the model
the crew skill through a pre_llm_call context; Hermes replaces any hook context above
hooks.output_spill.max_chars (default 10000) with a head/tail preview plus a file path, and the model
logs one read_file to get the text back - because skills/crew/SKILL.md is ~12.5k. install.py keeps
that cap above the preload for the profiles it provisions; a failure here prints the cap and the tool
call it counted, so the drop from 0 to 1 is never a mystery.
"""
import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_proof_board  # noqa: E402
import crew_card  # noqa: E402 - the owner profile

HERMES = os.environ.get("HERMES_BIN") or shutil.which("hermes") or os.path.expanduser("~/.local/bin/hermes")
VAGUE = "/crew make it better"


def newest_session(db):
    con = sqlite3.connect(db)
    try:
        row = con.execute("select id from sessions order by started_at desc limit 1").fetchone()
        return row[0] if row else None
    finally:
        con.close()


def tool_calls(db, session_id):
    con = sqlite3.connect(db)
    try:
        return con.execute("select count(*) from messages where session_id=? and role='tool'",
                           (session_id,)).fetchone()[0]
    finally:
        con.close()


def tool_call_detail(db, session_id):
    """What the turn called, '<name>(<first 70 chars of args>)' per call, read from the assistant
    rows. The intake turn is allowed zero, so a failure has to name the call - a read_file of the
    session's own hook-output spill (HERMES_HOME/hook_outputs/<session>/) is Hermes delivering the
    plugin's larger-than-cap preload, not the model researching the ask."""
    con = sqlite3.connect(db)
    try:
        rows = con.execute("select coalesce(tool_calls, '') from messages"
                           " where session_id=? and role='assistant'", (session_id,)).fetchall()
    finally:
        con.close()
    calls = []
    for (raw,) in rows:
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            continue
        for call in parsed or []:
            fn = call.get("function") or {}
            calls.append("%s(%s)" % (fn.get("name") or "?",
                                     " ".join(str(fn.get("arguments") or "").split())[:70]))
    return calls


def spill_cap(profile_home):
    """The profile's hooks.output_spill.max_chars as written, or None when it is not set (Hermes
    default 10000). Above the cap a pre_llm_call hook's context is replaced by a preview + file path,
    so the injected skill text costs the turn a read_file tool call."""
    import re
    try:
        with open(os.path.join(profile_home, "config.yaml"), encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return None
    hit = next((i for i, l in enumerate(lines) if re.match(r"^hooks:\s*$", l)), None)
    if hit is None:
        return None
    for line in lines[hit + 1:]:
        if line.strip() and not line.startswith((" ", "\t")):
            break                       # left the hooks block
        m = re.match(r"^    max_chars:\s*(\S+)\s*$", line)
        if m:
            return m.group(1)
    return None


def cards(board):
    con = sqlite3.connect(board)
    try:
        return con.execute("select count(*) from tasks").fetchone()[0]
    finally:
        con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=None)
    # The one-shot turn inherits this env, so a card the intake wrongly opens lands on the pinned proofs
    # board - the board counted here - and never on the live one.
    ap.add_argument("--board", default=None,
                    help="the kanban file to count (default: the pinned proofs board)")
    args = ap.parse_args()
    pinned = crew_proof_board.proof_db()        # exit 2 when the turn would open cards on the live board
    args.board = args.board or pinned

    if not args.profile:
        args.profile = crew_card.owner_profile()
    home = crew_card.profile_home(args.profile)
    db = os.path.join(home, "state.db")
    if not os.path.exists(db):
        print("no state.db at %s" % db)
        return 2

    before_session = newest_session(db)
    before_cards = cards(args.board)
    t0 = time.time()
    proc = subprocess.run([HERMES, "-p", args.profile, "chat", "-q", VAGUE],
                          capture_output=True, text=True, timeout=600)
    after_session = newest_session(db)
    after_cards = cards(args.board)
    session = after_session if after_session != before_session else None
    tools = tool_calls(db, session) if session else None
    calls = tool_call_detail(db, session) if session else []
    research = [c for c in calls if not c.startswith("clarify")]

    print("ask: %s" % VAGUE)
    print("exit code: %s   seconds: %.1f" % (proc.returncode, time.time() - t0))
    print("session: %s" % session)
    print("tool messages in that session: %s" % tools)
    for call in calls:
        print("   %s" % call)
    print("research calls (everything but clarify): %s" % (research or "none"))
    print("hooks.output_spill.max_chars: %s (no key = Hermes default 10000; the intake preload is "
          "larger, so a cap below it spills the skill text and the turn spends one read_file)"
          % (spill_cap(home) or "unset"))
    print("cards before: %s   after: %s" % (before_cards, after_cards))

    ok = (proc.returncode == 0 and session is not None and not research and len(calls) <= 1
          and tools == len(calls) and after_cards == before_cards)
    print("intake proof: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
