#!/usr/bin/env python3
"""Proof that the board's topic moves no longer make Notification Bot talk, both directions.

Run against the live realm:
  1. move a probe message with the PATCHED mover        -> no new notification-bot message
  2. move a probe message with the default parameters   -> exactly one notification-bot message (control)

The probe messages are deleted at the end (the control's notice stays in #sandbox: it is
notification-bot's message, and only its owner can remove it) or reports so. Nothing is posted to
a channel the owner reads.
"""
import base64
import importlib.util
import os
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request

FEED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kanban_zulip_feed.py")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402 - the owner profile, the base home and the package checkout
PROFILE_ENV = os.path.join(crew_card.owner_home(), ".env")
failures = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + (f"  [{detail}]" if detail else ""))
    if not ok:
        failures.append(label)


spec = importlib.util.spec_from_file_location("feed", FEED)
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)
env = feed.load_env(PROFILE_ENV)
z = feed.Zulip(env)

site = env["ZULIP_SITE"].rstrip("/")
auth = "Basic " + base64.b64encode(f"{env['ZULIP_BOT_EMAIL']}:{env['ZULIP_API_KEY']}".encode()).decode()
ctx = ssl.create_default_context()


def api(path, method="GET", fields=None):
    data = urllib.parse.urlencode(fields).encode() if fields else None
    req = urllib.request.Request(site + path, method=method, data=data)
    req.add_header("Authorization", auth)
    try:
        return json.load(urllib.request.urlopen(req, context=ctx))
    except urllib.error.HTTPError as e:
        return {"__http": e.code, "msg": e.read().decode()[:160]}


def notices_since(mid):
    q = urllib.parse.urlencode({
        "anchor": str(mid), "num_before": 0, "num_after": 40,
        "narrow": json.dumps([{"operator": "sender", "operand": "notification-bot@zulip.com"}]),
        "apply_markdown": "false"})
    return api("/api/v1/messages?" + q).get("messages", [])


def newest_id():
    return api("/api/v1/messages?" + urllib.parse.urlencode({
        "anchor": "newest", "num_before": 1, "num_after": 0,
        "narrow": json.dumps([{"operator": "stream", "operand": "sandbox"}]),
        "apply_markdown": "false"}))["messages"][-1]["id"]


def move_with_defaults(mid, topic):
    """The pre-fix call: no notice flags, so the new-thread notice defaults to true."""
    return api(f"/api/v1/messages/{mid}", "PATCH", {"topic": topic, "propagate_mode": "change_one"})


tag = time.strftime("%H%M%S")
# 1. patched mover
a_topic = f"notice probe {tag}"
probe_a = z.post_to("sandbox", a_topic, "probe: moved with the patched mover")
check("probe message posted (patched path)", isinstance(probe_a, int), f"id={probe_a}")
base = newest_id()
z.move(probe_a, a_topic + " b")
time.sleep(6)
new = notices_since(base)
check("patched move produces NO notification-bot message", len(new) == 0,
      f"notices={[m['id'] for m in new]}")

# 2. control: the same move with the previous call
b_topic = f"ctrl probe {tag}"
probe_b = z.post_to("sandbox", b_topic, "probe: moved the pre-fix way")
base2 = newest_id()
move_with_defaults(probe_b, b_topic + " b")
time.sleep(6)
new2 = notices_since(base2)
check("control: the pre-fix call DOES produce a notification-bot message", len(new2) == 1,
      f"notices={[m['id'] for m in new2]}")
if new2:
    where = new2[0].get("display_recipient")
    print(f"      control notice landed in {where} > {new2[0].get('subject')}: "
          f"{new2[0]['content'][:80].replace(chr(10), ' ')}")

# 3. clean up the probes
for mid in (probe_a, probe_b):
    r = api(f"/api/v1/messages/{mid}", "DELETE")
    check(f"probe {mid} deleted", r.get("result") == "success", str(r.get('msg') or ''))

print()
print("PROOF FAILED: " + "; ".join(failures) if failures else
      "PROOF OK: board topic moves are silent, and the same move without the flags still notifies")
sys.exit(1 if failures else 0)
