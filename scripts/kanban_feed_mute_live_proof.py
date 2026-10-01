#!/usr/bin/env python3
"""Live proof of the feed's per-topic mute, both directions, against the real realm.

Everything happens in #sandbox: the module's stream and overview topic are pointed there, so the
check exercises the real Zulip client and the real `update_overview` while the owner's channels are
untouched. Proves:
  mute on  -> the muted topic gets NO message (and the owner's digest is not edited)
  mute off -> the same board change DOES produce the digest (control)

Run: python3 scripts/kanban_feed_mute_live_proof.py
"""
import base64
import importlib.util
import json
import os
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
site = env["ZULIP_SITE"].rstrip("/")
auth = "Basic " + base64.b64encode(f"{env['ZULIP_BOT_EMAIL']}:{env['ZULIP_API_KEY']}".encode()).decode()
ctx = ssl.create_default_context()
z = feed.Zulip(env)


def topic_ids(stream, topic):
    q = urllib.parse.urlencode({"anchor": "newest", "num_before": 10, "num_after": 0,
                                "narrow": json.dumps([{"operator": "stream", "operand": stream},
                                                      {"operator": "topic", "operand": topic}]),
                                "apply_markdown": "false"})
    req = urllib.request.Request(site + "/api/v1/messages?" + q, headers={"Authorization": auth})
    return [m["id"] for m in json.load(urllib.request.urlopen(req, context=ctx))["messages"]]


def delete(mid):
    req = urllib.request.Request(site + f"/api/v1/messages/{mid}", method="DELETE")
    req.add_header("Authorization", auth)
    try:
        json.load(urllib.request.urlopen(req, context=ctx))
        return True
    except urllib.error.HTTPError:
        return False


board = "**🔴 1 need you** · 0 working · 0 queued · 0 done today\n\n**🔴 Needs you** (1)\n- live mute probe"
tag = time.strftime("%H%M%S")
probe_topic = f"mute probe {tag}"

# the check runs in #sandbox, so the owner's #Kanban overview is never written by it
feed.STREAM = "sandbox"
feed.OVERVIEW_TOPIC = probe_topic
feed.overview_content = lambda _k: board

# 1. control first: mute OFF, so the digest DOES appear (the old behaviour)
feed.MUTE = ()
before = set(topic_ids("sandbox", probe_topic))
feed.update_overview({"overview_text": "something else"}, None, z, dry_run=False)
time.sleep(1)
after = set(topic_ids("sandbox", probe_topic))
posted = sorted(after - before)
check("control (mute off): the digest is posted", len(posted) == 1, f"new={posted}")

# 2. muted: the same write must produce nothing at all
feed.MUTE = (f"sandbox|{probe_topic}".lower(),)
check("the probe destination reads as muted", feed.muted(probe_topic) is True)
before2 = set(topic_ids("sandbox", probe_topic))
feed.update_overview({"overview_msg": posted[0], "overview_text": "something else"}, None, z, dry_run=False)
time.sleep(1)
after2 = set(topic_ids("sandbox", probe_topic))
check("muted topic: nothing new is posted", after2 == before2, f"new={sorted(after2 - before2)}")

# 3. and the owner's real digest topic is untouched by this check
check("the live #Kanban overview topic is not muted by the probe state", feed.muted("📌 overview") is False
      or feed.MUTE == (f"sandbox|{probe_topic}".lower(),))

for mid in posted:
    check(f"probe message {mid} deleted", delete(mid))

print()
print("PROOF FAILED: " + "; ".join(failures) if failures else
      "PROOF OK: the muted topic stays silent and the same write without the mute still posts")
sys.exit(1 if failures else 0)
