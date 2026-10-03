#!/usr/bin/env python3
"""Proof that a card opened from a chat topic records that topic as its origin.

Runs on the SCRATCH board and scratch HERMES_HOME of crew_coordinator_proof.py (the real `hermes kanban` verbs
through its wrapper, no gateway, no model, the live board never opened).

  1  `crew_card.py open` from a session whose chat is a stream topic writes one `origin` event carrying that
     stream and that topic (the row crew_notify reads to send the report back to the same topic)
  2  `crew_card.py origin --card` reads the same record back
  3  the card's body carries the `Origin:` line for the same topic

Run:  python3 crew_origin_open_proof.py
Exit: 0 when every check passes, 1 otherwise.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_coordinator_proof as cp  # noqa: E402

CARD = os.path.join(HERE, "crew_card.py")
STREAM = "Kanban"
TOPIC = "PROBE origin open"
CHAT = "stream:%s|%s" % (STREAM, TOPIC)
check = cp.check


def main():
    cp.setup()
    check("the scratch board is not the live board",
          os.path.realpath(cp.DB) != os.path.realpath(os.path.expanduser("~/.hermes/kanban.db")), cp.DB)
    env = dict(cp.ENV, HERMES_SESSION_PLATFORM="zulip", HERMES_SESSION_CHAT_ID=CHAT,
               HERMES_SESSION_CHAT_TYPE="stream", HERMES_SESSION_ID="walk_origin_open")
    opened = subprocess.run(
        [sys.executable, CARD, "open", "--title", "origin open probe", "--goal", "prove the origin is recorded",
         "--role", "worker", "--artifact", "a log line", "--lands", "scratch", "--audience", "the owner",
         "--done-when", "the origin event names the topic", "--proof-cmd", "true", "--units", "one pass",
         "--constraints", "none", "--origin", "zulip:" + CHAT, "--json"],
        env=env, capture_output=True, text=True, timeout=300)
    m = re.search(r'"id":\s*"(t_[0-9a-f]+)"', opened.stdout or "")
    card = m.group(1) if m else ""
    check("a card opens from that topic", bool(card), ((opened.stdout or "") + (opened.stderr or ""))[-80:].strip())
    if not card:
        print("PROOF FAIL: no card, nothing further to check")
        return 1

    events = [json.loads(r["payload"]) for r in cp.rows(
        "select payload from task_events where task_id = ? and kind = 'origin'", (card,))]
    chat = str(events[0].get("chat") or "") if events else ""
    check("one origin event, carrying the stream and the topic",
          len(events) == 1 and STREAM in chat and TOPIC in chat and events[0].get("platform") == "zulip",
          "chat %r" % chat[:60])

    read = subprocess.run([sys.executable, CARD, "origin", "--card", card], env=env, capture_output=True,
                          text=True, timeout=120)
    check("`crew_card.py origin` reads the same record back",
          read.returncode == 0 and TOPIC in (read.stdout or ""), (read.stdout or read.stderr).strip()[:70])

    body = cp.card(card)["body"]
    check("the card body carries the Origin line for that topic",
          re.search(r"(?m)^Origin:.*%s" % re.escape(TOPIC), body) is not None,
          (re.search(r"(?m)^Origin:.*$", body) or [""])[0][:70])

    if cp.FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(cp.FAILS), ", ".join(cp.FAILS)))
        return 1
    print("PROOF OK: a card opened from a stream topic records that stream and topic as its origin")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        import shutil
        shutil.rmtree(cp.TMP, ignore_errors=True)
