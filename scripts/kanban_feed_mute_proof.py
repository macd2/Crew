#!/usr/bin/env python3
"""Proof that the feed's per-topic mute silences one topic and nothing else, both directions.

Run: python3 kanban_feed_mute_proof.py
"""
import importlib.util
import os
import sys

FEED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kanban_zulip_feed.py")
failures = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + (f"  [{detail}]" if detail else ""))
    if not ok:
        failures.append(label)


spec = importlib.util.spec_from_file_location("feed", FEED)
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)


class FakeZulip:
    def __init__(self):
        self.posted, self.edits, self.next_id = [], [], 70000

    def edit(self, msg_id, content):
        self.edits.append(msg_id)

    def post(self, topic, content):
        self.next_id += 1
        self.posted.append((topic, self.next_id))
        return self.next_id


def run(content, state, mute):
    feed.MUTE = tuple(mute)
    z = FakeZulip()
    feed.overview_content = lambda _k: content
    feed.update_overview(state, None, z)
    return z


BOARD = "**🔴 1 need you** · 0 working · 0 queued · 0 done today\n\n**🔴 Needs you** (1)\n- a card"
CHANGED = BOARD + "\n**⚪ Queued** (1)\n- another card"

# 1. the mute is per topic, not per channel
feed.MUTE = ("kanban|📌 overview",)
check("the overview topic is muted", feed.muted("📌 overview") is True)
check("a column topic in the same channel is NOT muted", feed.muted("Done") is False)
feed.MUTE = ("kanban",)
check("channel-level entry mutes any topic", feed.muted("Done") is True)
feed.MUTE = ("kanban|📌 overview",)
check("matching is case-insensitive", feed.muted("📌 Overview") is True)

# 2. muted overview: a changed board posts and edits nothing
st = {"overview_msg": 11453, "overview_text": BOARD}
z = run(CHANGED, st, ("kanban|📌 overview",))
check("muted topic: no digest post", z.posted == [], f"posts={z.posted}")
check("muted topic: no in-place edit either", z.edits == [], f"edits={z.edits}")
check("muted topic: the stored text is left alone", st["overview_text"] == BOARD)

# 3. control: the same board change with the mute off does update
st = {"overview_msg": 11453, "overview_text": BOARD}
z = run(CHANGED, st, ())
check("control (no mute): the digest is edited in place", z.edits == [11453] and not z.posted,
      f"edits={z.edits} posts={len(z.posted)}")
check("control (no mute): the stored text moves with it", st["overview_text"] == CHANGED)

# 4. a first run with the mute on posts nothing at all
z = run(CHANGED, {}, ("kanban|📌 overview",))
check("muted topic from scratch: no first post", z.posted == [], f"posts={z.posted}")

print()
print("PROOF FAILED: " + "; ".join(failures) if failures else
      "PROOF OK: the muted topic gets no digest, the same change without the mute still does")
sys.exit(1 if failures else 0)
