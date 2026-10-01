#!/usr/bin/env python3
"""Proof for the overview de-duplication fix in kanban_zulip_feed.py, both directions.

The three overview versions the owner called identical reposts used to be read straight out of the
live `📌 overview` topic by message id. Those messages are gone (moved or deleted since), so the proof
seeds its own: it renders the feed's real `overview_content` over a fixture board at three successive
clock times (plus once more for an older, genuinely different board state), posts the four versions
into its own probe topic in #sandbox, reads them back from the realm, and deletes them again - and a
run that was killed before its cleanup gets its leftovers removed by the next run. Nothing
the owner reads is written to, and no assertion depends on a message that can move or disappear.

1. The three seeded versions must compare EQUAL after `_stable`, UNEQUAL as raw text
   (the older board state must stay different).
2. Their round trip through the realm must keep that shape.
3. A frozen overview continued by an age tick alone -> zero posts.
4. A frozen overview continued by a real board change -> exactly one post.
5. An unfrozen overview -> edited in place, zero posts, never marked frozen.
6. A first run with no message id -> exactly one post.

Run: python3 kanban_overview_dedupe_proof.py
"""
import base64
import importlib.util
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

FEED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kanban_zulip_feed.py")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402 - the owner profile, the base home and the package checkout
PROFILE_ENV = os.path.join(crew_card.owner_home(), ".env")
PROBE_STREAM = "sandbox"                       # never the owner's #Kanban: the proof posts its own
PROBE_TOPIC = "dedupe probe " + time.strftime("%H%M%S")
failures = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + (f"  [{detail}]" if detail else ""))
    if not ok:
        failures.append(label)


spec = importlib.util.spec_from_file_location("kanban_feed", FEED)
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)

# ------------------------------------------------- the proof's own overview versions
# A fixture board (the columns the digest renders) put through the feed's own generator at three
# successive clock times: the versions then differ in nothing but the age the digest prints, which is
# exactly the shape the three reposted messages had.
def fixture_board(now, changed=False):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("create table tasks (id text primary key, title text, status text, assignee text,"
                 " created_at integer, started_at integer, completed_at integer)")
    conn.execute("create table task_events (id integer primary key autoincrement, task_id text,"
                 " kind text, payload text, created_at integer)")
    day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    done_at = max(int(now) - 600, int(day_start) + 60)   # stays inside "Done today" even at 00:05
    rows = [
        ("t_block", "a card the worker is stuck on", "blocked", "worker-a",
         int(now) - 7200, int(now) - 3600, None),
        ("t_run", "a card that is running now", "running", "worker-b",
         int(now) - 1800, int(now) - 1500, None),
        ("t_ready", "a card waiting to start", "ready", None, int(now) - 300, None, None),
        ("t_done", "a card that ended today", "done", "worker-c",
         int(now) - 3600, int(now) - 3500, done_at),
    ]
    events = [("t_block", "blocked", '{"reason": "hit its quota wall"}')]
    if changed:                # an older board: a card moved column and a new one appeared
        rows = [(i, t, ("blocked" if i == "t_run" else s), a, c, st, cp)
                for (i, t, s, a, c, st, cp) in rows]
        rows.append(("t_new", "a card that was not on the board before", "todo", None,
                     int(now) - 60, None, None))
        events.append(("t_run", "blocked", '{"reason": "the first card went down too"}'))
    for row in rows:
        conn.execute("insert into tasks values (?,?,?,?,?,?,?)", row)
    for tid, kind, payload in events:
        conn.execute("insert into task_events (task_id, kind, payload, created_at) values (?,?,?,?)",
                     (tid, kind, payload, int(now)))
    return conn


class Clock:
    """The feed reads `time.time()`: this renders the SAME fixture board at another moment, the way
    the daemon rendered the same board again a minute later and posted the same digest a second time."""

    def __init__(self, at):
        self.at = float(at)

    def time(self):
        return self.at


def render(conn, at):
    real, feed.time = feed.time, Clock(at)
    try:
        return feed.overview_content(conn)
    finally:
        feed.time = real


base = time.time()
board = fixture_board(base)
versions = [render(board, base + off) for off in (0, 60, 7200)]
older = render(fixture_board(base, changed=True), base)
newest = versions[-1]
ages = feed.AGE_RX.findall(newest)
print("age tokens found in the newest overview:", ages)
check("the three overview versions the owner called identical are distinct raw text",
      len(set(versions)) == 3, f"raw variants={len(set(versions))} of {len(versions)}")
check("those three collapse to ONE stable text", len({feed._stable(t) for t in versions}) == 1,
      f"stable variants={len({feed._stable(t) for t in versions})}")
check("an older, genuinely different board state stays different",
      feed._stable(older) != feed._stable(newest))

tick = feed.AGE_RX.sub(" · 99m", newest, count=1)
check("the age tick the fix must ignore is a real difference in raw text", tick != newest)
clocked = feed.CLOCK_RX.sub(lambda m: " · 00:01" if m.group(0) != " · 00:01" else " · 23:59",
                            newest, count=1)
check("a done-today clock tick is a real difference in raw text, and is blanked too",
      clocked != newest and feed._stable(clocked) == feed._stable(newest))

# ------------------------------------------------- seeded into the proof's own probe topic
env = {}
for line in open(PROFILE_ENV, encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
site = env["ZULIP_SITE"].rstrip("/")
auth = "Basic " + base64.b64encode(f"{env['ZULIP_BOT_EMAIL']}:{env['ZULIP_API_KEY']}".encode()).decode()
ctx = ssl.create_default_context()


def api(method, path, fields=None):
    """One realm call; a failure comes back as a dict so a check can name it instead of a traceback."""
    data = urllib.parse.urlencode(fields).encode() if fields else None
    req = urllib.request.Request(site + "/api/v1" + path, method=method, data=data)
    req.add_header("Authorization", auth)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        try:
            return {"result": "error", "msg": json.loads(exc.read().decode("utf-8", "replace")).get("msg", "")}
        except ValueError:
            return {"result": "error", "msg": str(exc)}
        finally:
            exc.close()
    except Exception as exc:
        return {"result": "error", "msg": f"{type(exc).__name__}: {exc}"}


def topic_messages(stream, topic):
    q = urllib.parse.urlencode({"anchor": "newest", "num_before": 20, "num_after": 0,
                                "narrow": json.dumps([{"operator": "stream", "operand": stream},
                                                      {"operator": "topic", "operand": topic}]),
                                "apply_markdown": "false"})
    return api("GET", "/messages?" + q).get("messages") or []


STALE_TOPIC_RX = re.compile(r"^dedupe probe \d{6}$")


def topic_of(msg):
    """This realm answers `subject`; newer Zulip also carries `topic`. Read either."""
    return msg.get("topic") or msg.get("subject") or ""


PROBE_MIN_AGE_S = 300          # a probe topic younger than this may belong to a run still going


def probe_age_seconds(topic):
    """Seconds since the HHMMSS stamp a probe topic is named for, or -1 when it carries none."""
    try:
        t = int(topic.rsplit(" ", 1)[-1])
    except (ValueError, IndexError):
        return -1
    hh, mm, ss = t // 10000, (t // 100) % 100, t % 100
    now = time.localtime()
    return (now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec) - (hh * 3600 + mm * 60 + ss)


def sweep_stale_probes(keep_topic):
    """A killed run can leave its four probe messages behind; this run clears them.

    Only topics that are exactly another dedupe probe, never the one this run is about to use, only
    ones at least PROBE_MIN_AGE_S old (a younger one may belong to a run still in flight) and only
    messages this bot posted (Zulip refuses anyone else's). A realm whose edit window has closed
    refuses the delete: that is reported, not treated as a failure of the dedupe rule. A listing that
    fails is reported too - a sweep that cannot see must not look like a clean sweep.
    """
    q = urllib.parse.urlencode({"anchor": "newest", "num_before": 100, "num_after": 0,
                                "narrow": json.dumps([{"operator": "stream", "operand": PROBE_STREAM}]),
                                "apply_markdown": "false"})
    got = api("GET", "/messages?" + q)
    if got.get("result") != "success":
        return 0, 0, 0, str(got.get("msg") or "listing failed")
    msgs = got.get("messages") or []
    stale = []
    for m in msgs:
        topic = topic_of(m)
        if not STALE_TOPIC_RX.match(topic) or topic == keep_topic:
            continue
        age = probe_age_seconds(topic)
        if age >= PROBE_MIN_AGE_S:
            stale.append(m)
    gone = refused = 0
    for m in stale:
        if api("DELETE", "/messages/%d" % m["id"]).get("result") == "success":
            gone += 1
        else:
            refused += 1
    return len(stale), gone, refused, ""


stale_seen, stale_gone, stale_refused, stale_err = sweep_stale_probes(PROBE_TOPIC)
check("no earlier probe run left a message behind", stale_refused == 0 and not stale_err,
      ("stale=%d deleted=%d refused=%d %s" % (stale_seen, stale_gone, stale_refused, stale_err)).strip())


posted, back = [], []                          # the probe's own topic, never the owner's
try:
    for text in versions + [older]:
        r = api("POST", "/messages", {"type": "stream", "to": PROBE_STREAM, "topic": PROBE_TOPIC,
                                      "content": text})
        if r.get("result") == "success":
            posted.append(r["id"])
    check("the four versions are seeded into the probe's own topic", len(posted) == 4,
          f"seeded={len(posted)} of 4 in #{PROBE_STREAM} > {PROBE_TOPIC}")
    back = sorted((m for m in topic_messages(PROBE_STREAM, PROBE_TOPIC) if m["id"] in posted),
                  key=lambda m: m["id"])
    seeded = [m["content"] for m in back]
    check("the realm hands all four seeded messages back", len(seeded) == 4,
          f"read back={len(seeded)}")
    check("the realm stored the seeded versions verbatim", seeded == versions + [older])
    sig = seeded[:3]                            # always checked: an empty read-back fails by name
    check("the realm's three repost-shaped messages are distinct raw text",
          len(set(sig)) == 3, f"raw variants={len(set(sig))} of {len(sig)}")
    check("the realm's copies still collapse to ONE stable text",
          len({feed._stable(t) for t in sig}) == 1,
          f"stable variants={len({feed._stable(t) for t in sig})}")
    check("the realm's copy of the older board state stays different",
          len(seeded) == 4 and feed._stable(seeded[3]) != feed._stable(seeded[2]))
finally:                                        # the proof never leaves its probe messages behind
    for mid in posted:
        check(f"probe message {mid} deleted",
              api("DELETE", f"/messages/{mid}").get("result") == "success")

# The digest message the proof carries its run in: its own newest seeded message, or a plain stand-in
# when the realm seeding above already failed on a named check (the checks below must still run).
PROBE_MSG = back[2]["id"] if len(back) == 4 else 90000


# ---------------------------------------------------------------- stub zulip
class FakeZulip:
    def __init__(self, edit_raises=False):
        self.posted = []            # list of (topic, content, id)
        self.edits = []             # list of (msg_id, content)
        self.edit_raises = edit_raises
        self.next_id = 90000

    def edit(self, msg_id, content):
        self.edits.append((msg_id, content))
        if self.edit_raises:
            raise feed.ZulipEditLimit("The time limit for editing this message has passed")

    def post(self, topic, content):
        self.next_id += 1
        self.posted.append((topic, content, self.next_id))
        return self.next_id


real = newest + "\n**🔵 Working** (1)\n- a card that just moved\n"


def run(content, state, edit_raises):
    z = FakeZulip(edit_raises=edit_raises)
    feed.overview_content = lambda _k: content
    feed.update_overview(state, None, z)
    return z


# 1. frozen + age tick only -> no post, stays frozen, text absorbed
st = {"overview_msg": PROBE_MSG, "overview_text": newest, "overview_frozen": True}
z = run(tick, st, edit_raises=True)
check("age tick on a frozen message posts NOTHING", not z.posted and not z.edits,
      f"posts={len(z.posted)} edits={len(z.edits)}")
check("state stays frozen and absorbs the tick",
      st.get("overview_frozen") is True and st["overview_text"] == tick)

# 2. frozen + real change -> exactly one post, unfrozen again
st = {"overview_msg": PROBE_MSG, "overview_text": newest, "overview_frozen": True}
z = run(real, st, edit_raises=True)
check("a real change on a frozen message posts exactly ONCE", len(z.posted) == 1 and not z.edits,
      f"posts={len(z.posted)}")
check("the continuation message becomes the live message and unfreezes",
      st["overview_msg"] == z.posted[0][2] and st.get("overview_frozen") is False,
      f"msg={st['overview_msg']} posted_id={z.posted[0][2]}")

# 3. unfrozen: edit in place, no post
st = {"overview_msg": PROBE_MSG, "overview_text": newest}
z = run(real, st, edit_raises=False)
check("an unfrozen message is edited, never reposted", not z.posted and len(z.edits) == 1,
      f"posts={len(z.posted)} edits={len(z.edits)}")

# 4. first run: one post
st = {}
z = run(real, st, edit_raises=False)
check("first run posts once and records the id",
      len(z.posted) == 1 and st["overview_msg"] == z.posted[0][2])

# 5. transition into frozen: the edit is refused -> flag set, nothing posted in that pass
st = {"overview_msg": PROBE_MSG, "overview_text": newest}
z = run(tick, st, edit_raises=True)
check("the pass that hits the edit window posts nothing and freezes",
      not z.posted and st.get("overview_frozen") is True,
      f"posts={len(z.posted)} frozen={st.get('overview_frozen')}")

# 6. after the freeze, an idle board stays silent over many age ticks
st = {"overview_msg": PROBE_MSG, "overview_text": newest, "overview_frozen": True}
posts = 0
for i in range(30):
    t = feed.AGE_RX.sub(f" · {100 + i}m", newest, count=1)
    posts += len(run(t, st, edit_raises=True).posted)
check("30 age ticks on a frozen overview produce 0 posts", posts == 0, f"posts={posts}")

# 7. the old code path would have posted on every one of those ticks (control)
st_ctrl = {"overview_msg": PROBE_MSG, "overview_text": newest}
ctrl_posts = []
for i in range(30):
    t = feed.AGE_RX.sub(f" · {100 + i}m", newest, count=1)
    z = FakeZulip(edit_raises=True)
    # the pre-fix body: edit, and on ZulipEditLimit post the same content
    try:
        z.edit(st_ctrl["overview_msg"], t)
    except feed.ZulipEditLimit:
        st_ctrl["overview_msg"] = z.post(t, t)
    ctrl_posts.append(t)
check("control: the old body reposts on all 30 ticks (the fault the owner saw)",
      len(st_ctrl) == 2 and st_ctrl["overview_msg"] != PROBE_MSG, f"ctrl posts={len(ctrl_posts)}")

print()
print("PROOF FAILED: " + "; ".join(failures) if failures else
      "PROOF OK: edited while the realm allows it, and after the freeze only a real change reposts")
sys.exit(1 if failures else 0)
