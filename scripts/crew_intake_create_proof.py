#!/usr/bin/env python3
"""Proof that the intake's `kanban_create` path works against the kernel's own tool and schema.

    python3 scripts/crew_intake_create_proof.py

What is real: the kernel's `kanban_create` handler (tools/kanban_tools.py), the kernel's schema and
notify-subscription code, and this package's plugin hooks, driven in the order the runtime drives them:
pre_tool_call guard -> merged `modify` args -> handler -> post_tool_call hook. What is scratch: the board
(a throwaway file, HERMES_KANBAN_DB pinned, see crew_proof_board.py) and the chat (session variables say
zulip:stream:Kanban|PROBE intake create). No model call, no hermes CLI, nothing on the live board.

Anchor: a body that states `Budget: 1000` and a made-up `Origin:` must come out of the real tool as a
card whose Budget line is the role floor and whose Origin is the session's chat, because the model cannot
know the chat and a card under the floor stops before its first call.

Exit 0 = every check passed.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crew_proof_board as board  # noqa: E402
import crew_card  # noqa: E402 - the owner profile and the base home
PKG = crew_card.package_dir() or os.path.dirname(HERE)

CHAT = "stream:Kanban|PROBE intake create"
ASK = "put up a status page for the on-call team"
BODY = """Role: worker
Budget: 1000
Route: none
Origin: made-up:chat
GOAL: Ship the status page
Artifact: a static page
Lands at: /srv/status/index.html
For: the on-call team
Constraints: no new dependencies
Done when: the page answers 200 with the word OK
proof command: curl -fsS http://127.0.0.1:8081/ | grep -q OK
"""
FAILURES = []


def check(name, ok, detail=""):
    print("%-66s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + str(detail)[:90]) if detail else ""))
    if not ok:
        FAILURES.append(name)
    return ok


def inner():
    import importlib.util
    import sqlite3
    db = os.environ["HERMES_KANBAN_DB"]
    spec = importlib.util.spec_from_file_location("crew_plugin_create_proof", os.path.join(PKG, "__init__.py"))
    plug = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plug)
    from tools import kanban_tools as kt

    def q(sql, *args):
        conn = sqlite3.connect(db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def call(args, session="S1", turn="T1"):
        """One tool call the way the runtime makes it: guard, merge the modify, run the real handler, post hook."""
        verdict = plug.crew_tool_guard(tool_name="kanban_create", args=args, session_id=session, turn_id=turn)
        if isinstance(verdict, dict) and verdict.get("action") == "block":
            return verdict, None
        merged = {**args, **verdict["args"]} if isinstance(verdict, dict) else args
        result = kt._handle_create(merged)
        plug.crew_open_hook(tool_name="kanban_create", args=merged, result=result, session_id=session)
        return verdict, json.loads(result)

    want_assignee = "crew-worker" if os.path.isdir(os.path.expanduser("~/.hermes/profiles/crew-worker")) \
        else os.path.basename(os.environ["HERMES_HOME"].rstrip("/"))
    args = {"title": "Status page", "assignee": "crew-worker", "body": BODY}

    verdict, res = call(args, session="S-plain")
    check("a crew card outside a /crew turn is refused", verdict.get("action") == "block" and res is None,
          verdict.get("message"))
    check("and nothing reached the board", q("select count(*) from tasks")[0][0] == 0)

    plug.crew_intake_preload(user_message="/crew " + ASK, session_id="S1", turn_id="T1")
    verdict, res = call({**args, "body": BODY.replace("For: the on-call team\n", "")})
    check("a missing field is refused by name", verdict.get("action") == "block" and "For" in verdict["message"],
          verdict.get("message"))
    check("and the window stays open for the owner's answer", plug._window_live("S1"))

    verdict, res = call(args)
    check("a complete contract in the /crew window creates the card", res is not None and res.get("ok") is True,
          res)
    cid = (res or {}).get("task_id")
    check("the real tool's result carries the id as task_id (what the hook reads)", bool(cid))
    body = (q("select body from tasks where id = ?", cid) or [[""]])[0][0] if cid else ""
    row = (q("select status, assignee from tasks where id = ?", cid) or [("", "")])[0] if cid else ("", "")
    roles = next((p for p in (os.path.join(os.environ["HERMES_HOME"], "roles", "crew", "roles.json"),
                              os.path.join(PKG, "roles", "roles.json")) if os.path.isfile(p)))
    floor = json.load(open(roles)).get("budget_floor_tokens")
    check("the card is ready and on the role's profile", row == ("ready", want_assignee), row)
    check("anchor: Budget 1000 became the role floor", ("Budget: %s tokens" % floor) in body, (floor, body[:80]))
    check("anchor: the model's made-up Origin is the session's chat", ("Origin: zulip:%s" % CHAT) in body
          and "made-up" not in body)
    check("the plugin wrote the Coordinator and Verifier lines", "\nCoordinator: " in "\n" + body
          and "Verifier: crew-verifier" in body)
    events = dict((k, json.loads(p)) for k, p in q("select kind, payload from task_events where task_id = ? "
                                                   "and kind in ('origin', 'brief')", cid)) if cid else {}
    check("the origin event is recorded with the chat", events.get("origin", {}).get("origin") == "zulip:" + CHAT,
          events.get("origin"))
    check("the brief event is the owner's /crew ask", events.get("brief", {}).get("text") == ASK, events.get("brief"))
    subs = q("select count(*) from kanban_notify_subs where task_id = ?", cid)[0][0] if cid else -1
    check("the kernel's auto-subscription is dropped for a crew card (the feed reports it once)",
          res.get("subscribed") is True and subs == 0, "subscribed=%s rows=%s" % (res.get("subscribed"), subs))
    verdict2, res2 = call(args, turn="T2")
    check("one /crew, one card: a later turn of that session may not create another",
          verdict2.get("action") == "block" and res2 is None, verdict2.get("message"))

    before = q("select count(*) from tasks")[0][0]
    verdict3, res3 = call({"title": "buy milk", "assignee": "helper", "body": "milk"}, session="S-plain")
    cid3 = (res3 or {}).get("task_id")
    check("a kanban card that is not crew's passes through untouched", verdict3 is None and bool(cid3), verdict3)
    check("and the hook leaves it alone (no origin, no brief)",
          cid3 and q("select count(*) from task_events where task_id = ? and kind in ('origin','brief')", cid3)[0][0] == 0)
    check("one card per create", q("select count(*) from tasks")[0][0] == before + 1)
    return 0


def main():
    if "--inner" in sys.argv:
        rc = inner()
        if FAILURES:
            print("PROOF FAIL: %d check(s): %s" % (len(FAILURES), "; ".join(FAILURES)))
            return 1
        print("PROOF OK: the intake's kanban_create is gated, completed and recorded on the kernel's own tool")
        return rc
    tmp = tempfile.mkdtemp(prefix="crew-intake-create-proof-")
    db = os.path.join(tmp, "kanban.db")
    if not board.init_board(db):
        print("PROOF FAIL: the scratch board could not be created")
        return 2
    home = os.environ.get("HERMES_HOME") or crew_card.owner_home()
    env = dict(os.environ, PYTHONPATH=board.AGENT, HERMES_KANBAN_DB=db, HERMES_HOME=home,
               HERMES_SESSION_PLATFORM="zulip", HERMES_SESSION_CHAT_ID=CHAT, HERMES_SESSION_ID="proof-session",
               CREW_ROUTER_PLUGIN=os.path.join(tmp, "no-router"))
    for key in ("HERMES_KANBAN_TASK",):
        env.pop(key, None)
    try:
        r = subprocess.run([board.VENV_PY, os.path.abspath(__file__), "--inner"], env=env, cwd=board.AGENT,
                           timeout=180)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
