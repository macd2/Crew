#!/usr/bin/env python3
"""Live mirror of the Hermes kanban board into Zulip #Kanban.

One topic per desktop-kanban COLUMN (Triage, Todo, Scheduled, Ready, Running, Blocked, Review, Done,
Archived - the same names the desktop board uses) and one message per task card inside it, edited in
place while the run moves: board events (created, claimed, spawned, commented, blocked, completed, ...)
plus every tool step the worker takes, read from the worker's own session. The message follows the card
when its column changes. Heartbeats fold into a counter; the header shows status, elapsed time and step
count, with a spinner while the card is running. A card ends at its last real state - the `archived`
transition is never rendered. History in per-task topics is moved by `kanban_zulip_columns.py`.

  python3 kanban_zulip_feed.py --daemon     # live mode (systemd user service), polls every 3s
  python3 kanban_zulip_feed.py [--once]     # one pass
  python3 kanban_zulip_feed.py --dry-run    # print what would be posted, change nothing

A crew card whose body carries `Origin: <platform>:<chat>` and `Coordinator: <owner profile>/...`
also pings once per ending (see notify_endings): `done` posts a report into the origin chat,
`blocked` posts an alert into #Kanban > crew-alerts AND into the origin chat; a blocked crew card
without an origin still alerts crew-alerts. Routed states are kept in STATE["notified"].

State (event cursor + per-task live message ids + the last event id each card rendered) lives in
STATE. The first start baselines to the newest event, so board history is never replayed. Zulip
freezes a message once the realm's edit window has passed, so the feed then continues that run in a
fresh message instead of failing; a failed send never stalls the event cursor, and a card only gets a
new message for events it has not rendered yet (the absence of that guard once re-posted identical
cards every poll). Credentials come from the profile .env and are never printed; secret-looking
strings in tool arguments are redacted before posting.
"""
import argparse
import base64
import json
import os
import re
import sqlite3
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402 - the shared readers (decision_detail)

# The board, and the owner profile whose .env holds the Zulip credentials (install.py records it).
KANBAN_DB = os.environ.get("KANBAN_DB") or os.path.join(crew_card.base_home(), "kanban.db")
PROFILE_ENV = os.path.join(crew_card.owner_home(), ".env")
STATE = os.environ.get("KANBAN_FEED_STATE",
                       os.path.join(crew_card.owner_home(), "cron", "state", "kanban_zulip_feed.json"))
STREAM = os.environ.get("KANBAN_FEED_STREAM", "Kanban")
# Per-topic mute list: `<channel>` (whole channel) or `<channel>|<topic>` entries, comma separated.
# A muted destination gets no feed output at all - no column card message, no overview digest. The
# owner scopes silence per topic (`KANBAN_FEED_MUTE=Kanban|📌 overview` in the service unit), because a
# topic he does not read should not collect board chatter.
MUTE = tuple(e.strip().lower() for e in os.environ.get("KANBAN_FEED_MUTE", "").split(",") if e.strip())
POLL_S = float(os.environ.get("KANBAN_FEED_POLL", "3"))
MAX_STEPS = 30          # newest tool steps kept visible; older ones fold into a count
MSG_LIMIT = 9000        # realm limit is 10000
CLOSED = ("done", "blocked", "archived")

ICON = {
    "created": "🆕", "claimed": "🙋", "spawned": "🚀", "promoted": "⏫", "commented": "💬",
    "completed": "✅", "blocked": "⛔", "unblocked": "🔓", "crashed": "💥", "gave_up": "🏳️",
    "timed_out": "⌛", "status": "🔁", "linked": "🔗", "decomposed": "🧩", "assigned": "👤",
    "review_requested": "🔍", "changes_requested": "✏️", "archived": "📦",
}
STATUS_ICON = {"ready": "⚪", "todo": "⚪", "running": "🔵", "done": "🟢", "blocked": "🔴",
               "triage": "🟡", "archived": "⚫"}
TOOL_ICON = {"terminal": "💻", "execute_code": "🐍", "read_file": "📖", "write_file": "✍️",
             "patch": "🔧", "search_files": "🔎", "web_search": "🌐", "web_extract": "🌐",
             "delegate_task": "👥", "skill_view": "📚"}
SECRET_RX = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|(?i:(?:api[_-]?key|token|secret|password)\s*[=:]\s*)\S+)")
QUIET_EVENTS = ("heartbeat", "claimed", "tip_scratch_workspace")
# One topic per desktop-kanban column (same names the desktop board uses), not one per task: a card
# message is posted into the topic of its current column and moved when the column changes.
COLUMN_LABEL = {"triage": "Triage", "todo": "Todo", "scheduled": "Scheduled", "ready": "Ready",
                "running": "Running", "blocked": "Blocked", "review": "Review", "done": "Done",
                "archived": "Archived"}


def muted(topic, stream=None):
    """True when the feed must stay quiet in that destination (see MUTE).

    A muted destination gets no card message, no move and no endings ping; the overview topic is
    checked the same way, so `KANBAN_FEED_MUTE=Kanban|📌 overview` silences the digest alone.
    """
    chan = (stream or STREAM).lower()
    return chan in MUTE or f"{chan}|{(topic or '').lower()}" in MUTE


# ------------------------------------------------------------------------------------ helpers
def load_env(path):
    vals = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


class ZulipEditLimit(Exception):
    """The realm's edit window for that message has passed: it is frozen, so the feed must post a
    continuation message instead of editing. Raised out of Zulip._call; never fatal to a pass."""


class Zulip:
    def __init__(self, env):
        self.base = env["ZULIP_SITE"].rstrip("/") + "/api/v1"
        tok = base64.b64encode(f"{env['ZULIP_BOT_EMAIL']}:{env['ZULIP_API_KEY']}".encode()).decode()
        self.auth = "Basic " + tok
        self.ctx = ssl.create_default_context()

    def _call(self, method, path, fields):
        req = urllib.request.Request(self.base + path, method=method,
                                     data=urllib.parse.urlencode(fields).encode())
        req.add_header("Authorization", self.auth)
        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=30) as r:
                body = json.load(r)
        except urllib.error.HTTPError as exc:
            try:
                msg = json.loads(exc.read().decode("utf-8", "replace")).get("msg", "")
            except ValueError:
                msg = str(exc)
            finally:
                exc.close()             # an HTTPError holds the response socket open until closed
            if "time limit for editing" in msg or "time limit for deleting" in msg:
                raise ZulipEditLimit(msg) from None
            raise RuntimeError(f"zulip {method} {path}: {msg[:160]}") from None
        if body.get("result") != "success":
            raise RuntimeError("zulip refused: " + str(body.get("msg"))[:120])
        return body

    def post(self, topic, content):
        return self._call("POST", "/messages",
                          {"type": "stream", "to": STREAM, "topic": topic, "content": content})["id"]

    def edit(self, msg_id, content):
        self._call("PATCH", f"/messages/{msg_id}", {"content": content})

    def post_dm(self, user_ids, content):
        return self._call("POST", "/messages", {"type": "private", "to": json.dumps(user_ids),
                                                "content": content})["id"]

    def post_to(self, stream, topic, content):
        return self._call("POST", "/messages",
                          {"type": "stream", "to": stream, "topic": topic, "content": content})["id"]

    def move(self, msg_id, topic):
        """Move one message to another topic (only this message, never its neighbours).

        Both move notices are suppressed: Zulip's Notification Bot posts an automated
        "[A message] was moved here from ..." into the destination topic by default
        (send_notification_to_new_thread defaults to true), which reads in the board's
        column topic as the bot talking (owner, 2026-09-29)."""
        self._call("PATCH", f"/messages/{msg_id}",
                   {"topic": topic, "propagate_mode": "change_one",
                    "send_notification_to_new_thread": "false",
                    "send_notification_to_old_thread": "false"})


def hhmm(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def short(text, n):
    text = SECRET_RX.sub("[redacted]", " ".join(str(text or "").split()))
    return text if len(text) <= n else text[: n - 1] + "…"


def topic_for(task_id, title):
    t = f"{task_id} · {title or ''}".strip()
    return t if len(t) <= 60 else t[:59] + "…"


def column_topic(status, task_id, title):
    """The topic a card belongs in: the desktop-kanban column name, falling back to the task topic."""
    return COLUMN_LABEL.get(status) or topic_for(task_id, title)


def dur(sec):
    sec = int(max(0, sec))
    return f"{sec // 60}m{sec % 60:02d}s" if sec >= 60 else f"{sec}s"


# ------------------------------------------------------------------------------------ data
def render_event(kconn, ev):
    kind, payload = ev["kind"], {}
    try:
        payload = json.loads(ev["payload"] or "{}") or {}
    except ValueError:
        pass
    detail = ""
    if kind == "created":
        detail = f"→ {payload.get('assignee') or 'unassigned'}" + (" · goal loop" if payload.get("goal_mode") else "")
    elif kind == "commented":
        row = kconn.execute("select author, body from task_comments where task_id=? and created_at<=? "
                            "order by id desc limit 1", (ev["task_id"], ev["created_at"])).fetchone()
        if row:
            detail = f"**{row['author']}**: {short(row['body'], 220)}"
    elif kind in ("blocked", "unblocked", "status"):
        detail = short(payload.get("reason") or payload.get("status") or "", 200)
    elif kind in ("completed", "crashed", "gave_up", "timed_out"):
        run = kconn.execute("select summary, error from task_runs where task_id=? order by id desc limit 1",
                            (ev["task_id"],)).fetchone()
        if run:
            detail = short(run["summary"] or run["error"] or "", 400)
    elif kind == "spawned":
        detail = f"pid {payload.get('pid')}" if payload.get("pid") else ""
    elif kind == "crew_decision":
        detail = f"{payload.get('decision')}: {short(crew_card.decision_detail(payload), 160)}".rstrip(": ")
    elif payload:
        detail = short(", ".join(f"{k}={v}" for k, v in payload.items() if v not in (None, "", [])), 140)
    return (ev["created_at"], f"`{hhmm(ev['created_at'])}` {ICON.get(kind, '•')} **{kind}**"
            + (f" - {detail}" if detail else ""))


def profile_home(profile):
    """Hermes home of a profile: `default` lives at the root, every other one under profiles/."""
    return crew_card.profile_home(profile)


def worker_steps(profile, task_id, since_ts):
    """Tool steps from the worker session of this task (source 'kanban', first prompt names the task)."""
    db = f"{profile_home(profile)}/state.db"
    if not os.path.exists(db):
        return []
    s = None
    try:
        s = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
        row = s.execute(
            "select m.session_id from messages m join sessions ss on ss.id=m.session_id "
            "where ss.source='kanban' and ss.started_at>=? and m.role='user' and m.content like ? "
            "order by m.id desc limit 1", (since_ts - 5, f"%kanban task {task_id}%")).fetchone()
        if not row:
            return []
        steps = []
        for ts, calls in s.execute("select timestamp, tool_calls from messages where session_id=? and "
                                   "role='assistant' and tool_calls is not null order by id", (row[0],)):
            try:
                calls = json.loads(calls or "[]")
            except ValueError:
                continue
            for c in calls:
                fn = c.get("function") or {}
                name = fn.get("name") or "?"
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except ValueError:
                    args = {}
                arg = (args.get("command") or args.get("path") or args.get("query") or args.get("pattern")
                       or args.get("code") or args.get("task_id") or "")
                steps.append((ts, f"`{hhmm(ts)}` {TOOL_ICON.get(name, '🔹')} {name}"
                                  + (f" · `{short(arg, 90).replace('`', chr(39))}`" if arg else "")))
        return steps
    except sqlite3.Error:
        return []
    finally:
        if s is not None:       # an unclosed connection per card per poll leaked every descriptor
            s.close()


def publish(zulip, msg_id, topic, content, dry_run=False):
    """Put `content` in the run's message: post it first time, edit in place after. When the realm's
    edit window for that message has passed it is frozen, so post a continuation message instead of
    failing. Returns the id of the message that now carries the run."""
    if dry_run:
        print(f"--- #{STREAM} > {topic} ({'edit' if msg_id else 'new'})\n{content}\n")
        return msg_id
    if msg_id is None:
        return zulip.post(topic, content)
    try:
        zulip.edit(msg_id, content)
        return msg_id
    except ZulipEditLimit:
        return zulip.post(topic, content)


def build_message(task, run_started, events, steps, beats):
    status = task["status"]
    hidden = max(0, len(steps) - MAX_STEPS)
    visible = sorted(events + steps[hidden:], key=lambda x: x[0])
    body = ([f"_… {hidden} earlier steps folded_"] if hidden else []) + [line for _, line in visible]
    end = task["completed_at"] if status in CLOSED and task["completed_at"] else time.time()
    elapsed = dur(end - run_started) if run_started else "-"
    spinner = " ⏳" if status == "running" else ""
    head = (f"{STATUS_ICON.get(status, '⚪')} **{status}**{spinner} · {task['assignee'] or '-'} · "
            f"{elapsed} · {len(steps)} steps" + (f" · 💓×{beats}" if beats else ""))
    content = head + "\n" + "\n".join(body)
    while len(content) > MSG_LIMIT and len(body) > 5:
        body.pop(1 if hidden else 0)
        content = head + "\n" + "\n".join(body)
    return content


# ------------------------------------------------------------------------------------ one pass
def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    os.replace(tmp, STATE)


def one_pass(state, zulip, dry_run=False):
    """One feed pass over a read-only board connection that is always closed again: the old pass
    left its connection to the garbage collector, and a daemon polling every 3 s ran out of file
    descriptors (Errno 24) with ~500 kanban.db handles open."""
    kconn = sqlite3.connect(f"file:{KANBAN_DB}?mode=ro", uri=True, timeout=10)
    kconn.row_factory = sqlite3.Row
    try:
        return _one_pass(kconn, state, zulip, dry_run)
    finally:
        kconn.close()


def _one_pass(kconn, state, zulip, dry_run=False):
    newest = kconn.execute("select coalesce(max(id),0) from task_events").fetchone()[0]
    if "cursor" not in state:                       # first start: baseline, no replay
        state.update({"cursor": newest, "live": {}})
        notify_endings(state, kconn, zulip, dry_run)
        return state
    cursor = int(state["cursor"])
    live = state.setdefault("live", {})
    fresh = {r[0] for r in kconn.execute("select distinct task_id from task_events where id>?", (cursor,))}
    todo = fresh | {tid for tid, v in live.items() if not v.get("closed")}
    state["cursor"] = newest      # advance before the loop: a failed send must never stall the cursor

    for tid in sorted(todo):
        task = kconn.execute("select * from tasks where id=?", (tid,)).fetchone()
        if not task:
            live.pop(tid, None)
            continue
        run = kconn.execute("select id, started_at, profile from task_runs where task_id=? "
                            "order by id desc limit 1", (tid,)).fetchone()
        run_id = run["id"] if run else None
        slot = live.get(tid)
        seen = max(slot.get("seen", 0), slot.get("from_event", cursor)) if slot else 0
        evs = kconn.execute("select * from task_events where task_id=? and id>? order by id",
                            (tid, slot["from_event"] if slot else cursor)).fetchall()
        maxev = max([e["id"] for e in evs], default=seen)
        if task["status"] == "archived":
            if slot is not None:       # the card ends at its last real state: never render the archive
                slot["seen"] = max(slot["seen"], maxev)
                slot["closed"] = True
                slot["run_id"] = run_id
                live[tid] = slot
            continue
        if slot and slot.get("closed") and maxev > seen:
            slot = None                # the card moved again after closing: continue in a new message
            evs = [e for e in evs if e["id"] > seen]
        if slot is None:
            slot = {"msg": None, "from_event": cursor, "run_id": run_id, "sig": "", "closed": False,
                    "seen": seen, "topic": None, "ts": time.time()}
        beats = sum(1 for e in evs if e["kind"] == "heartbeat")
        events = [render_event(kconn, e) for e in evs if e["kind"] not in QUIET_EVENTS]
        run_started = (run["started_at"] if run else None) or task["started_at"] or task["created_at"]
        steps = worker_steps(run["profile"], tid, run_started or 0) if run else []
        slot["seen"] = max(slot["seen"], maxev)   # these events are rendered now: never re-post them
        slot["run_id"] = run_id
        slot["closed"] = task["status"] in CLOSED
        if not events and not steps:
            live[tid] = slot
            continue
        tick = int(time.time()) // 15 if task["status"] == "running" else 0   # refresh elapsed every 15s
        sig = f"{len(events)}|{len(steps)}|{beats}|{task['status']}|{tick}"
        topic = column_topic(task["status"], tid, task["title"])
        if muted(topic):
            live[tid] = slot
            continue
        if slot["msg"] is not None and slot.get("topic") not in (None, topic):
            try:                       # the card changed column: its message follows it
                zulip.move(slot["msg"], topic)
                slot["topic"] = topic
            except Exception as exc:
                print(f"kanban feed move failed for {tid}: {type(exc).__name__}: {str(exc)[:160]}",
                      flush=True)
        if sig != slot["sig"]:
            content = build_message(task, run_started, events, steps, beats)
            try:
                slot["msg"] = publish(zulip, slot["msg"], topic, content, dry_run)
                slot["sig"] = sig
                slot["topic"] = topic
            except Exception as exc:   # one bad send must not abort the pass nor re-open the slot
                print(f"kanban feed send failed for {tid}: {type(exc).__name__}: {str(exc)[:160]}",
                      flush=True)
        live[tid] = slot

    for tid in [t for t, v in live.items() if v.get("closed") and v.get("ts", 0) < time.time() - 86400]:
        live.pop(tid, None)
    notify_endings(state, kconn, zulip, dry_run)
    update_overview(state, kconn, zulip, dry_run)
    return state


# ------------------------------------------------------------------------------------ endings
# A crew card opened from a chat carries `Origin: <platform>:<chat id>` (crew_card.py open
# --origin). When its status becomes `done` the feed posts one report into that chat, and only
# there. When it becomes `blocked` it posts one alert into the shared #Kanban > crew-alerts topic
# AND one into the origin chat, so whoever started the crew hears it where they are and can unblock
# it. A blocked crew card with no Origin line still alerts crew-alerts; a done card without one stays
# silent. Keyed off the card status and recorded in STATE["notified"][<card>] = [statuses already
# routed] (plus `<state>@<target>` for a target already reached while the other one failed and is
# retried next pass), so each card+state+target pings exactly once. Cards opened by any coordinator
# other than the owner profile stay silent.
ALERT_TOPIC = os.environ.get("KANBAN_ALERT_TOPIC", "crew-alerts")
NOTIFY_COORDINATOR = crew_card.owner_profile() + "/"
NOTIFY_STATES = ("done", "blocked", "triage")
# A blocked crew card is the coordinator's to decide (crew_coordinator.py, one pass per dispatch tick): the
# owner hears about it when the coordinator asks the owner (an `ask_owner` crew_decision, whose question the
# alert carries), not on every block the coordinator is about to retry. No decision within this many seconds
# of the block means the coordinator is not running, and the alert goes out as it always did.
DECISION_GRACE_S = int(os.environ.get("KANBAN_DECISION_GRACE", "600"))
STOP_EVENT_KINDS = ("blocked", "block_loop_detected", "gave_up")
NOTIFY_WINDOW_S = int(os.environ.get("KANBAN_NOTIFY_WINDOW", "3600"))   # never replay old endings
ORIGIN_RX = re.compile(r"^\s*Origin:\s*(.+?)\s*$", re.M)
COORD_RX = re.compile(r"^\s*Coordinator:\s*(\S+)", re.M)


def card_origin(body):
    m = ORIGIN_RX.search(body or "")
    return m.group(1) if m else None


def resolved_origin(tid, body):
    """(origin, session, source_card) - the card's own record, else inherited up its chain.

    A card the decomposer created under a crew card has no Origin line of its own; without this the
    session that kicked the brief off never hears that its child is stuck. crew_card.origin_of reads
    the card's own 'origin' event and walks task_links parents + the decomposer's from_decompose_of
    record, so the loop closes on the card that came from the chat.
    """
    own = card_origin(body)
    if own:
        return own, "", tid
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("crew_card_origin",
                                                      os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                   "crew_card.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        found, src, _hops = mod.origin_of(tid)
    except Exception:
        return None, "", tid
    return (found.get("origin") or None), (found.get("session") or ""), src


def origin_target(origin):
    """(kind, stream_or_user, topic) for a Zulip origin, else None.
    `zulip:stream:<stream>|<topic>` -> stream topic; `zulip:dm:<user id>` -> direct message."""
    platform, _, chat = (origin or "").partition(":")
    if platform.strip().lower() != "zulip":
        return None
    if chat.startswith("stream:"):
        stream, _, topic = chat[len("stream:"):].partition("|")
        if stream.strip() and topic.strip():
            return ("stream", stream.strip(), topic.strip())
    if chat.startswith("dm:") and chat[3:].strip():
        return ("dm", chat[3:].strip(), None)
    return None


def owner_question(kconn, tid, now):
    """(alert?, question) for a blocked crew card: ask the owner when the coordinator's newest decision after
    the newest block is ask_owner (its question), or when the block is older than DECISION_GRACE_S with no
    decision at all; otherwise the coordinator still owns the card and nothing goes out."""
    stop = kconn.execute("select id, created_at from task_events where task_id=? and kind in (%s) "
                         "order by id desc limit 1" % ",".join("?" * len(STOP_EVENT_KINDS)),
                         (tid,) + STOP_EVENT_KINDS).fetchone()
    dec = kconn.execute("select id, payload from task_events where task_id=? and kind='crew_decision' "
                        "order by id desc limit 1", (tid,)).fetchone()
    if dec and (not stop or dec["id"] > stop["id"]):
        try:
            data = json.loads(dec["payload"] or "{}")
        except ValueError:
            data = {}
        if data.get("decision") == "ask_owner":
            return True, str(data.get("question") or "")
        return False, ""
    if stop and now - (stop["created_at"] or 0) > DECISION_GRACE_S:
        return True, ""
    return (not stop), ""


def _ending_text(kconn, task, status, session="", inherited_from="", question=""):
    tid = task["id"]
    title = short(task["title"], 120)
    tail = ""
    if inherited_from and inherited_from != tid:
        tail = f"\nFrom card: `{inherited_from}` (this card was created under it)"
    if session:
        tail += f"\nOpened by session: `{session}`"
    if status == "done":
        run = kconn.execute("select summary from task_runs where task_id=? and summary is not null "
                            "order by id desc limit 1", (tid,)).fetchone()
        summary = short((run["summary"] if run else None) or task["result"] or "", 600)
        return (f"🟢 **done** · `{tid}` · {title}\n"
                + (f"{summary}\n" if summary else "")
                + tail
            + f"\nCard: {card_url(tid)}")
    ev = kconn.execute("select payload from task_events where task_id=? and kind in "
                       "('blocked','gave_up','crashed','timed_out') order by id desc limit 1",
                       (tid,)).fetchone()
    try:
        reason = (json.loads(ev["payload"] or "{}") or {}).get("reason") if ev else ""
    except ValueError:
        reason = ""
    reason = short(question or reason or task["last_failure_error"] or "", 300)
    return (f"🔴 **blocked** · `{tid}` · {title} · {task['assignee'] or '-'}\n"
            + (f"Why: {reason}\n" if reason and reason != "initial_status" else "")
            + tail
            + f"\nCard: {card_url(tid)}")


def notify_endings(state, kconn, zulip, dry_run=False):
    """Route done reports to the origin chat, blocked alerts to crew-alerts and the origin chat;
    once per card, state and target."""
    notified = state.setdefault("notified", {})
    now = time.time()
    # every card in a notifying state inside the window: a crew card by its Coordinator line, or a
    # card that has an origin of its own or inherits one (the decomposer's children have no body).
    rows = kconn.execute("select * from tasks where status in (%s) and coalesce(created_at,0) > ?"
                         % ",".join("?" * len(NOTIFY_STATES)),
                         NOTIFY_STATES + (now - NOTIFY_WINDOW_S,)).fetchall()
    for task in rows:
        tid, status, body = task["id"], task["status"], task["body"] or ""
        coord = COORD_RX.search(body)
        origin, session, src_card = resolved_origin(tid, body)
        if not coord or not coord.group(1).startswith(NOTIFY_COORDINATOR):
            if not origin and not session:
                continue                          # nothing to loop in and not a crew card
            if status == "done":
                continue                          # a done card only reports into its origin chat
        if status == "done" and not origin:        # a done card reports into its origin only
            continue
        done_states = notified.get(tid) or []
        if status in done_states:
            continue
        last_ev = kconn.execute("select coalesce(max(created_at),0) from task_events where task_id=?",
                                (tid,)).fetchone()[0]
        changed = max(task["completed_at"] or 0, task["created_at"] or 0, last_ev or 0)
        if now - changed > NOTIFY_WINDOW_S:        # an old ending: record it, never replay it
            notified[tid] = done_states + [status]
            continue
        question = ""
        if status in ("blocked", "triage") and coord:
            alert, question = owner_question(kconn, tid, now)
            if not alert:                          # the coordinator still owns it: no ping, no mark
                continue
        target = origin_target(origin) if origin else None
        if origin and target is None:
            print(f"kanban feed: {tid} origin platform not routable, origin {status} ping skipped",
                  flush=True)
        targets = []                               # (key, kind, where, topic)
        if status in ("blocked", "triage"):
            targets.append(("alerts", "stream", STREAM, ALERT_TOPIC))
        if target is not None:
            targets.append(("origin",) + tuple(target))
        label = "report" if status == "done" else "alert"
        content, failed = None, False
        for key, kind, where, topic in targets:
            mark = f"{status}@{key}"
            if mark in done_states:                # reached on an earlier pass: never twice
                continue
            try:
                content = content or _ending_text(kconn, task, status, session=session,
                                                  inherited_from=src_card, question=question)
                if dry_run:
                    dest = f"#{where} > {topic}" if kind == "stream" else f"dm {where} >"
                    print(f"--- {dest} ({label} {tid})\n{content}\n")
                elif kind == "stream":
                    if muted(topic, where):     # a muted destination is marked reached, never replayed
                        done_states = done_states + [mark]
                        continue
                    zulip.post_to(where, topic, content)
                else:
                    zulip.post_dm([int(where)] if where.isdigit() else [where], content)
                done_states = done_states + [mark]
            except Exception as exc:   # one failed ping must not stall the feed; it retries next pass
                failed = True
                print(f"kanban feed {label} failed for {tid} ({key}): {type(exc).__name__}: "
                      f"{str(exc)[:160]}", flush=True)
        if failed:                                 # keep the reached targets, retry the rest
            notified[tid] = done_states
        else:                                      # every target reached: one record per state
            notified[tid] = [s for s in done_states if not s.startswith(status + "@")] + [status]
    live_ids = {r[0] for r in kconn.execute("select id from tasks where status != 'archived'")}
    for tid in [t for t in notified if t not in live_ids]:
        notified.pop(tid, None)


# ------------------------------------------------------------------------------------ overview
OVERVIEW_TOPIC = "📌 overview"
GROUPS = [  # (title, statuses) in the order the owner reads them: what needs him first
    ("🔴 Needs you", ("blocked", "triage")),
    ("🔍 Ready for review", ("review",)),
    ("🔵 Working", ("running",)),
    ("⚪ Queued", ("ready", "todo", "scheduled")),
]


# Each card's live message is moved into its column topic, so a `#Kanban>t_<id>` topic link goes
# nowhere. A row links to the card page on the crew board and names the column topic the
# card's live message sits in.
CARD_BASE = (os.environ.get("CREW_CARD_BASE") or crew_card.dashboard_url()).rstrip("/")


def card_url(tid):
    return f"{CARD_BASE}/card/{urllib.parse.quote(tid)}"


def _task_link(tid, title, status=None):
    label = short(f"{tid} · {title or ''}", 70).replace("[", "(").replace("]", ")")
    column = COLUMN_LABEL.get(status or "")
    return f"[{label}]({card_url(tid)})" + (f" · {column}" if column else "")


def _age(sec):
    """Whole-minute age (the overview must not change every poll)."""
    m = int(max(0, sec)) // 60
    if m < 60:
        return f"{m}m"
    if m < 48 * 60:
        return f"{m // 60}h{m % 60:02d}m"
    return f"{m // 1440}d"


def overview_content(kconn):
    now = time.time()
    day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    rows = kconn.execute("select id, title, status, assignee, created_at, started_at, completed_at "
                         "from tasks where status != 'archived'").fetchall()
    out, counts = [], {}
    for title, statuses in GROUPS:
        items = sorted((r for r in rows if r["status"] in statuses), key=lambda r: r["created_at"])
        counts[title] = len(items)
        if not items:
            continue
        out.append(f"**{title}** ({len(items)})")
        for r in items:
            age = _age(now - (r["started_at"] or r["created_at"]))
            why = ""
            if r["status"] in ("blocked", "triage"):
                ev = kconn.execute("select payload from task_events where task_id=? and kind in ('blocked','gave_up',"
                                   "'crashed') order by id desc limit 1", (r["id"],)).fetchone()
                try:
                    p = json.loads(ev["payload"] or "{}") if ev else {}
                except ValueError:
                    p = {}
                why = short(p.get("reason") or "", 90)
                why = "" if why == "initial_status" else why
            out.append(f"- {_task_link(r['id'], r['title'], r['status'])} · {age}" + (f" · _{why}_" if why else ""))
    done_today = sorted((r for r in rows if r["status"] == "done" and (r["completed_at"] or 0) >= day_start),
                        key=lambda r: r["completed_at"], reverse=True)
    if done_today:
        out.append(f"**🟢 Done today** ({len(done_today)})")
        out += [f"- {_task_link(r['id'], r['title'], r['status'])} · {hhmm(r['completed_at'])[:5]}" for r in done_today[:15]]
        if len(done_today) > 15:
            out.append(f"- _… {len(done_today) - 15} more_")
    need = counts["🔴 Needs you"] + counts["🔍 Ready for review"]
    head = (f"**{'🔴 ' + str(need) + ' need you' if need else '✅ nothing needs you'}** · "
            f"{counts['🔵 Working']} working · {counts['⚪ Queued']} queued · {len(done_today)} done today")
    return head + "\n\n" + ("\n".join(out) if out else "_board is empty_")


# The overview's identity for the "did the board really change?" decision: an age (`25m`, `1h06m`,
# `2d`) and a done-today clock (`23:01`) move without any card moving, so they are blanked before two
# versions are compared. Without this, a frozen message is continued by an age tick alone (owner,
# 2026-09-29: "it is reposting the same one multiple times ... it should post only changes").
AGE_RX = re.compile(r" · (?:\d+d|\d+h(?:\d{2}m)?|\d+m)(?= · |$)", re.M)
CLOCK_RX = re.compile(r" · \d{2}:\d{2}$", re.M)


def _stable(text):
    return CLOCK_RX.sub(" · ~", AGE_RX.sub(" · ~", text))


def update_overview(state, kconn, zulip, dry_run=False):
    """One pinned-style message in `📌 overview`, edited only when its text changes. Ages are in
    whole minutes there (see _age), so an idle board edits at most once a minute. The realm freezes a
    message against content edits once its edit window has passed (`ZulipEditLimit`), and from then on
    only a REAL change earns a continuation message - an age tick on the frozen message is dropped,
    never posted a second time."""
    content = overview_content(kconn)
    if muted(OVERVIEW_TOPIC):
        return                              # the owner muted this topic: no digest, no edit
    if content == state.get("overview_text"):
        return
    if dry_run:
        print(f"--- #{STREAM} > {OVERVIEW_TOPIC}\n{content}\n")
        return
    if state.get("overview_msg") and not state.get("overview_frozen"):
        try:
            zulip.edit(state["overview_msg"], content)
        except ZulipEditLimit:            # the realm's edit window for that message has passed
            state["overview_frozen"] = True
    if state.get("overview_frozen"):
        if _stable(content) == _stable(state.get("overview_text") or ""):
            state["overview_text"] = content    # ages only: keep the frozen message, post nothing
            return
        state["overview_msg"] = zulip.post(OVERVIEW_TOPIC, content)  # a real change: continue here
        state["overview_frozen"] = False
    elif not state.get("overview_msg"):
        state["overview_msg"] = zulip.post(OVERVIEW_TOPIC, content)
    state["overview_text"] = content


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--once", action="store_true", help="one pass (the default without --daemon)")
    a = ap.parse_args()
    if a.daemon and a.once:
        ap.error("--daemon and --once exclude each other")
    zulip = None if a.dry_run else Zulip(load_env(PROFILE_ENV))
    state = load_state()
    if not a.daemon:
        state = one_pass(state, zulip, a.dry_run)
        if not a.dry_run:
            save_state(state)
        return 0
    errors = 0
    while True:
        try:
            state = one_pass(state, zulip)
            errors = 0
        except Exception as exc:   # keep the service alive; one line to the journal, never a secret
            errors += 1
            print(f"kanban feed error ({errors}): {type(exc).__name__}: {str(exc)[:200]}", flush=True)
        try:                       # the cursor lives on disk even when a pass died half way
            save_state(state)
        except Exception as exc:
            errors += 1
            print(f"kanban feed state error ({errors}): {type(exc).__name__}: {str(exc)[:200]}",
                  flush=True)
        if errors:
            time.sleep(min(60, POLL_S * errors))
        time.sleep(POLL_S)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"kanban feed error: {type(exc).__name__}: {str(exc)[:200]}")
        sys.exit(1)
