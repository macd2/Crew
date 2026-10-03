#!/usr/bin/env python3
"""Proof for the owner's return path (scripts/crew_notify.py): what reaches the chat, and what does not.

Done when, on a scratch board, one dry notify pass prints exactly:
  1. a done card with an Origin: one report whose target is that origin, once (a second pass with the state
     the first one would have left prints nothing: the dedupe is per card+event);
  2. a blocked card the coordinator still owns (no decision, or a retry decision): nothing;
  3. a blocked card whose newest decision is ask_owner: one needs-you message carrying the question, to the origin;
  4. a done card with no Origin: nothing (no chat asked for it);
  5. no credential from the owner profile's .env anywhere in the output.
`--send TARGET` additionally sends one real done report through `hermes send` (the delivery path itself).

Nothing touches the live board or a live chat unless --send is given. Exit 0 = every check passed.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crew_card  # noqa: E402
import crew_notify  # noqa: E402

ORIGIN = "zulip:stream:Kanban|PROBE origin thread"
BARE_URL_RE = re.compile(r"^https?://[A-Za-z0-9.\-]+(:[0-9]+)?/?$")
FAILURES = []
SCHEMA = (
    "create table tasks (id text primary key, title text, body text, status text, assignee text, created_at integer, "
    "completed_at integer, result text, last_failure_error text);"
    "create table task_runs (id integer primary key, task_id text, summary text);"
    "create table task_links (parent_id text, child_id text);"
    "create table task_events (id integer primary key, task_id text, run_id integer, kind text, payload text, "
    "created_at integer);")


def check(name, ok, detail=""):
    print("%-62s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + detail) if detail else ""))
    if not ok:
        FAILURES.append(name)


def seed(conn, cid, status, origin=True, events=()):
    now = int(time.time())
    body = "Coordinator: %s/probe\nRole: worker\nGoal: probe\n" % crew_card.owner_profile()
    if origin:
        body += "Origin: %s\n" % ORIGIN
    conn.execute("insert into tasks values (?,?,?,?,?,?,?,?,?)",
                 (cid, "PROBE %s" % cid, body, status, "crew-worker", now - 60, now if status == "done" else None,
                  "probe result", None))
    for kind, payload in events:
        conn.execute("insert into task_events (task_id, kind, payload, created_at) values (?,?,?,?)",
                     (cid, kind, json.dumps(payload), now))
    conn.commit()


def dry(db, state):
    lines = []
    crew_notify.run(db, state, dry_run=True, say=lines.append)
    return "\n".join(lines)


def main():
    send_to = sys.argv[sys.argv.index("--send") + 1] if "--send" in sys.argv else ""
    tmp = tempfile.mkdtemp(prefix="crew-notify-proof-")
    db, state = os.path.join(tmp, "kanban.db"), os.path.join(tmp, "notify-state.json")
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA)
    seed(conn, "t_done", "done", events=[("completed", {})])
    seed(conn, "t_owned", "blocked", events=[("blocked", {"reason": "stuck"}), ("crew_decision", {"decision": "retry"})])
    seed(conn, "t_ask", "blocked", events=[("blocked", {"reason": "stuck"}),
                                           ("crew_decision", {"decision": "ask_owner", "question": "Which branch?"})])
    seed(conn, "t_plain", "done", origin=False, events=[("completed", {})])
    conn.close()
    text = dry(db, state)
    sends = re.findall(r"^--- (.+?) \((\w+) (t_\w+)\)", text, re.M)
    check("done card: one report into its origin", sends.count((ORIGIN, "done", "t_done")) == 1, str(sends))
    check("blocked card the coordinator owns: silent", not any(c == "t_owned" for _t, _k, c in sends))
    check("ask_owner card: one needs-you with the question into the origin",
          (ORIGIN, "needs", "t_ask") in sends and "Which branch?" in text)
    check("done card with no origin: silent", not any(c == "t_plain" for _t, _k, c in sends))
    check("nothing else went out", len(sends) == 2, str(sends))
    crew_notify.save_state(state, {"since": time.time() - 3600,
                                   "sent": {"t_done": ["done:1"], "t_ask": ["ask:5"]}, "tries": {}})
    check("keys already sent are not printed again", not re.search(r"^--- ", dry(db, state), re.M))
    env_path = os.path.join(crew_card.owner_home(), ".env")
    if os.path.exists(env_path):
        secrets = []
        for line in open(env_path, encoding="utf-8", errors="replace"):
            if "=" in line and not line.strip().startswith("#"):
                v = line.partition("=")[2].strip().strip('"').strip("'")
                if len(v) >= 16 and not BARE_URL_RE.match(v):
                    secrets.append(v)
        check("no credential from .env in the output", not any(s in text for s in secrets))
    if send_to:
        ok, detail = crew_notify.hermes_send(send_to, "🟢 done · t_probe · crew_notify_proof\nreal delivery check")
        check("real send through `hermes send -t %s`" % send_to, ok, detail)
    if FAILURES:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILURES), "; ".join(FAILURES)))
        return 1
    print("PROOF OK: done and owner questions reach the origin once, everything the coordinator owns stays silent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
