#!/usr/bin/env python3
"""Mechanical re-organiser: put every kanban card message in #Kanban into the topic of its column.

The Zulip board mirrors the Hermes desktop kanban columns: one topic per column, named exactly as the
desktop board names them (Triage, Todo, Scheduled, Ready, Running, Blocked, Review, Done, Archived).
A card message carries its own status in its first line (`⚫ **archived** · ...`), so this script needs
no board database: it reads the stream, maps the status in the message to a column label and moves the
message there with `propagate_mode=change_one`.

  python3 kanban_zulip_columns.py --check      # print what would move, change nothing
  python3 kanban_zulip_columns.py              # move them, print a per-column report
  python3 kanban_zulip_columns.py --headers    # also post one header line in each column topic (once)

Idempotent: a card already in its column topic is left alone. Credentials come from the profile .env
and are never printed.
"""
import argparse
import base64
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402 - owner_home(): the profile whose .env holds the Zulip credentials

PROFILE_ENV = os.path.join(crew_card.owner_home(), ".env")
STREAM = os.environ.get("KANBAN_FEED_STREAM", "Kanban")
COLUMN_ORDER = ("Triage", "Todo", "Scheduled", "Ready", "Running", "Blocked", "Review", "Done",
                "Archived")
LABEL = {"triage": "Triage", "todo": "Todo", "scheduled": "Scheduled", "ready": "Ready",
         "running": "Running", "blocked": "Blocked", "review": "Review", "done": "Done",
         "archived": "Archived"}
STATUS_ICON = {"ready": "⚪", "todo": "⚪", "running": "🔵", "done": "🟢", "blocked": "🔴",
               "triage": "🟡", "archived": "⚫", "scheduled": "⚪", "review": "🔍"}
CARD_RX = re.compile(r"^\s*(⚫|🟢|🔵|⚪|🔴|🟡|🔍)\s+\*\*([a-z_]+)\*\*")
HEADER_RX = re.compile(r"^__column:")


def load_env(path):
    vals = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


class Zulip:
    def __init__(self, env):
        self.base = env["ZULIP_SITE"].rstrip("/") + "/api/v1"
        self.auth = "Basic " + base64.b64encode(
            f"{env['ZULIP_BOT_EMAIL']}:{env['ZULIP_API_KEY']}".encode()).decode()
        self.ctx = ssl.create_default_context()

    def call(self, method, path, fields=None, allow_fail=False):
        data = urllib.parse.urlencode(fields).encode() if fields else None
        req = urllib.request.Request(self.base + path, method=method, data=data)
        req.add_header("Authorization", self.auth)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, context=self.ctx, timeout=30) as r:
                    return json.load(r)
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")
                if exc.code == 429:                       # rate limited: back off and retry
                    time.sleep(2 * (attempt + 1))
                    continue
                if allow_fail:
                    try:
                        return {"error": json.loads(body).get("msg", body[:120])}
                    except ValueError:
                        return {"error": body[:120]}
                raise RuntimeError(f"zulip {method} {path}: {body[:160]}") from None
        return {"error": "rate limited"}


def stream_messages(z):
    """All messages of #Kanban, oldest first (paged by anchor)."""
    out, anchor, seen = [], "newest", set()
    while True:
        params = {"anchor": anchor, "num_before": 500, "num_after": 0, "apply_markdown": "false",
                  "narrow": json.dumps([{"operator": "stream", "operand": STREAM}])}
        batch = z.call("GET", "/messages?" + urllib.parse.urlencode(params))["messages"]
        fresh = [m for m in batch if m["id"] not in seen]
        if not fresh:
            break
        for m in fresh:
            seen.add(m["id"])
        out = fresh + out
        anchor = str(min(m["id"] for m in fresh))
        if len(batch) < 500:
            break
    return sorted(out, key=lambda m: m["id"])


def raw(m):
    return m.get("raw_content") or m["content"]


def header(topic):
    line = f"{STATUS_ICON.get(topic.lower(), '•')} **{topic}** · cards move here as their column changes."
    return f"__column:{topic}__\n{line}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--headers", action="store_true")
    a = ap.parse_args()
    z = Zulip(load_env(PROFILE_ENV))
    msgs = stream_messages(z)
    cards = [(m, CARD_RX.match(raw(m))) for m in msgs]
    cards = [(m, rx.group(2)) for m, rx in cards if rx]
    todo, unknown, already = [], [], 0
    for m, status in cards:
        label = LABEL.get(status)
        if label is None:
            unknown.append((m["id"], status))
            continue
        if m["subject"] == label:
            already += 1
        else:
            todo.append((m, label))
    print(f"stream messages {len(msgs)} | cards {len(cards)} | already in place {already} | "
          f"to move {len(todo)} | unknown status {len(unknown)}")
    for mid, status in unknown:
        print(f"  unknown status {status!r} on message {mid}")
    if a.headers and not a.check:
        have = {m["subject"] for m in msgs if HEADER_RX.match(raw(m))}
        for label in COLUMN_ORDER:
            if label not in have:
                z.call("POST", "/messages", {"type": "stream", "to": STREAM, "topic": label,
                                             "content": header(label)})
                print(f"  header posted in {label}")
    if a.check:
        for m, label in todo:
            print(f"  {m['id']} {m['subject'][:40]!r} -> {label}")
        return 0
    moved, failed = {}, []
    for m, label in todo:
        res = z.call("PATCH", f"/messages/{m['id']}",
                     {"topic": label, "propagate_mode": "change_one",
                      "send_notification_to_new_thread": "false",
                      "send_notification_to_old_thread": "false"},
                     allow_fail=True)
        if res.get("result") == "success":
            moved[label] = moved.get(label, 0) + 1
        else:
            failed.append((m["id"], str(res.get("error"))[:90]))
        time.sleep(0.2)
    print("moved: " + (", ".join(f"{k} {v}" for k, v in sorted(moved.items())) or "nothing"))
    if failed:
        print(f"failed {len(failed)}: {failed[:5]}")
    left = {}
    for m in stream_messages(z):
        if CARD_RX.match(raw(m)):
            left[m["subject"]] = left.get(m["subject"], 0) + 1
    print("cards per topic now: " + json.dumps(left, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
