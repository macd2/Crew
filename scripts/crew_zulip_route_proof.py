#!/usr/bin/env python3
"""Proof that a stuck card reaches the owner in the chat it came from, and that the overview links land.

Two defects, both in the kanban -> Zulip feed:

  A card that gets stuck only ever alerts the shared crew-alerts topic, so the person who started the
  crew in a chat does not hear about it where they are. A stuck card must also arrive in the chat the
  card was opened from, so it can be unblocked and the card continues.

  The `📌 overview` digest links every card as `#Kanban>t_<id>`, but the feed itself moves each card's
  live message into its column topic (Ready, Running, Blocked, Done), so that topic no longer exists
  and the link goes nowhere. Every row must link somewhere that answers.

Done when a dry pass prints:
  - a done report for a card with an origin into that origin topic;
  - for a blocked card WITH an origin: an alert into #Kanban > crew-alerts AND one into the origin
    topic;
  - for a blocked card WITHOUT an origin: the crew-alerts alert only;
  - an overview whose every card row carries a link to that card's page as an http(s) URL, plus the
    column the card sits in, and no `#Kanban>t_<id>` topic link;
  - and every one of those http(s) card links answers 200 when fetched.

Exit 0 = every check passed. Non-zero = it did not, and the failing check is printed.
"""
import json
import os
import random
import re
import sqlite3
import string
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402 - the owner profile, the base home and the package checkout
HOME = os.environ.get("HERMES_HOME") or crew_card.owner_home()
KANBAN_DB = os.environ.get("KANBAN_DB") or os.path.join(crew_card.base_home(), "kanban.db")
FEED = os.path.join(HERE, "kanban_zulip_feed.py")
ORIGIN = "zulip:stream:Kanban|PROBE origin thread"
FAILURES = []


def check(name, ok, detail=""):
    print("%-58s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + detail) if detail else ""))
    if not ok:
        FAILURES.append(name)
    return ok


def seed(status, origin=True, reason=None, done=False):
    card = "t_" + "".join(random.choice(string.hexdigits[:16]) for _ in range(8))
    now = int(time.time())
    body = ("Coordinator: %s/\n" % crew_card.owner_profile() +
            "Goal: probe card for the Zulip routing proof\nRole: worker\nproof command: true\n")
    if origin:
        body += "Origin: %s\n" % ORIGIN
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute(
            "insert into tasks (id, title, body, assignee, status, priority, created_by, created_at, "
            "workspace_kind, completed_at) values (?, ?, ?, 'crew-worker', ?, 0, 'probe', ?, 'scratch', "
            "?)", (card, "PROBE route %d" % now, body, status, now, now if done else None))
        conn.execute("insert into task_runs (task_id, profile, status, started_at, ended_at, outcome, "
                     "summary, last_heartbeat_at) values (?, 'crew-worker', ?, ?, ?, ?, ?, ?)",
                     (card, "done" if done else "blocked", now - 120, now - 60,
                      "completed" if done else "blocked",
                      "probe run finished" if done else reason, now - 60))
        if not done:
            conn.execute("insert into task_events (task_id, kind, payload, created_at) "
                         "values (?, 'blocked', ?, ?)",
                         (card, json.dumps({"kind": "needs_input", "reason": reason}), now - 60))
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        print("note: seeding %s failed: %s" % (card, str(exc)[:90]))
        return None
    finally:
        conn.close()
    return card


def drop(card):
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute("update tasks set status = 'archived' where id = ?", (card,))
        conn.commit()
    finally:
        conn.close()


def feed_pass(state, seed_cursor=False):
    if seed_cursor:
        # A first pass on a fresh state file only baselines its cursor and returns before the overview
        # is built. Give it a cursor so this pass reaches the overview; the dry run never saves state,
        # so the other pass still starts fresh and prints the endings.
        conn = sqlite3.connect(KANBAN_DB)
        try:
            newest = conn.execute("select coalesce(max(id),0) from task_events").fetchone()[0]
        finally:
            conn.close()
        with open(state, "w", encoding="utf-8") as fh:
            json.dump({"cursor": int(newest), "live": {}}, fh)
    env = dict(os.environ, HERMES_HOME=HOME, KANBAN_FEED_STATE=state)
    proc = subprocess.run([sys.executable, FEED, "--dry-run", "--once"], capture_output=True, text=True,
                          timeout=180, env=env)
    return (proc.stdout or "") + (proc.stderr or "")


def lines_for(text, card):
    """The posted-lines a dry pass printed for one card: (kind, target, label)."""
    out = []
    for line in text.splitlines():
        if card in line and line.lstrip().startswith("---"):
            m = re.search(r"---\s+#(\S+)\s*>\s*([^()]+?)\s*\((\w+)\s+%s\)" % card, line)
            if m:
                out.append((m.group(1), m.group(2).strip(), m.group(3)))
    return out


def overview_block(text):
    i = text.find("overview")
    if i < 0:
        return ""
    tail = text[i:]
    rows = [l for l in tail.splitlines() if l.startswith("- ")]
    return "\n".join(rows)


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as fh:
            return fh.getcode()
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:  # noqa: BLE001
        return 0


def main():
    if not os.path.exists(FEED):
        print("PROOF FAIL: the feed is not where it should be (%s)" % FEED)
        return 2
    state = os.path.join(tempfile.mkdtemp(prefix="crew-route-"), "state.json")
    ok_card = seed("done", origin=True, done=True)
    stuck = seed("blocked", origin=True, reason="Needs you: the proof needs a service restart")
    lonely = seed("blocked", origin=False, reason="Needs you: stuck with no origin chat")
    if not (ok_card and stuck and lonely):
        print("PROOF FAIL: could not seed the probe cards")
        return 2
    try:
        # One pass for the endings (fresh state) and one for the overview (state with a cursor).
        text = feed_pass(os.path.join(os.path.dirname(state), "endings.json")) + feed_pass(state, True)
        check("the feed pass ran", "kanban feed" not in text.lower() or "error" not in text.lower(),
              text[:80].replace("\n", " "))

        want = [("Kanban", "PROBE origin thread", "report")]
        got = lines_for(text, ok_card)
        check("a done card reports into its origin chat",
              any(g[1] == "PROBE origin thread" and g[2] == "report" for g in got),
              str(got))
        check("the shared alert topic is not spammed with done reports",
              not any(g[1] == "crew-alerts" for g in got), str(got))

        got = lines_for(text, stuck)
        check("a stuck card still alerts crew-alerts",
              any(g[1] == "crew-alerts" and g[2] == "alert" for g in got), str(got))
        check("a stuck card also reaches the chat it came from",
              any(g[1] == "PROBE origin thread" and g[2] == "alert" for g in got), str(got))

        got = lines_for(text, lonely)
        check("a stuck card with no origin alerts crew-alerts only",
              any(g[1] == "crew-alerts" for g in got)
              and not any(g[1] == "PROBE origin thread" for g in got), str(got))

        block = overview_block(text)
        check("the overview lists the probe cards", stuck in block and ok_card in block,
              "%d row(s)" % len(block.splitlines()))
        rows = [l for l in block.splitlines() if stuck in l or ok_card in l]
        check("no row links to a topic that no longer exists",
              not any(re.search(r"#\*{0,2}Kanban>t_%s" % c[2:], l) for c in (stuck, ok_card, lonely)
                      for l in block.splitlines()),
              rows[0][:90] if rows else block[:90])
        urls = []
        for row in rows:
            urls += re.findall(r"https?://[^\s\)\]<>]+", row)
        check("every row links to the card's page", len(urls) >= 2
              and all("/card/" in u for u in urls), str(urls[:3]))
        check("every row names the column the card sits in",
              all(re.search(r"\b(Done|Blocked|Ready|Running|Todo|Triage|Review|Archived)\b", r)
                  for r in rows), rows[0][:90] if rows else "")
        codes = [(u, fetch(u)) for u in urls]
        check("every link in the overview answers", bool(codes) and all(c == 200 for _, c in codes),
              str(codes[:4]))
    finally:
        for card in (ok_card, stuck, lonely):
            drop(card)

    if FAILURES:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILURES), "; ".join(FAILURES)))
        return 1
    print("PROOF OK: a stuck card reaches the chat it came from, and every overview link lands")
    return 0


if __name__ == "__main__":
    sys.exit(main())
