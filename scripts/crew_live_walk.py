#!/usr/bin/env python3
"""Drive the live Zulip path against the deployed build, on one synthetic owner event. LIVE ONLY.

This proof needs the real Zulip server and the deployed plugin, so it is held back from the nightly run
(`LIVE` in crew_proofs.py). It opens no card and writes nothing to any board: the board is only counted,
read-only, to show a bare word delivers nothing to the crew. What used to be its leg 3 (a card opened from
the topic records that topic as its origin) needs only the kanban kernel and runs on a scratch board in
crew_origin_open_proof.py; the card-to-done walks (one `Verify: proof` card, one `independent` card) are
crew_two_stage_proof.py.

The gateway drops its own messages and only an owner turn may open a crew card, so the inbound hop is
fed in-process: our own deployed ``zulip_platform`` adapter is constructed exactly as the gateway
constructs it (same credentials, same code), and ``_dispatch`` is called with the event an owner's
message in a stream topic produces. Everything after that is real traffic on the real server - the
questions posted, the number reactions and the report line all carry
captured Zulip message ids.

Legs, one line each in the report:
  1  a /crew message in a stream topic routes to that same stream and topic
  2  a bare "crew ..." and an ordinary message licence no open (the deployed guard refuses)
  3  (moved to crew_origin_open_proof.py, which runs on a scratch board)
  4  the report goes back to that same stream and topic

Run:  <hermes venv python> crew_live_walk.py [--topic NAME] [--stream NAME]
Exit: 0 when every leg is captured, 1 otherwise. A secret never appears in output.
"""
import argparse
import asyncio
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_card  # noqa: E402 - owner_home(): the profile the walk runs from

PROFILE = os.environ.get("CREW_PROFILE") or crew_card.owner_home()
PROFILE_ENV = os.environ.get("CREW_PROFILE_ENV") or os.path.join(PROFILE, ".env")
VENV = os.environ.get("CREW_VENV_PY") or os.path.expanduser("~/.hermes/hermes-agent/.venv/bin/python")
EVIDENCE_DIR = os.path.join(os.path.dirname(HERE), "proofs")
FAILS = []


def check(name, ok, detail=""):
    print("%-64s %s  %s" % (name, "PASS" if ok else "FAIL", str(detail)[:70]))
    if not ok:
        FAILS.append(name)


def load_env():
    """The profile's own env, the way the gateway gets it - values never printed."""
    have = {}
    if os.path.isfile(PROFILE_ENV):
        with open(PROFILE_ENV) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k.startswith("ZULIP_"):
                    os.environ.setdefault(k, v)
                    have[k] = True
    return sorted(have)


def q(sql):
    import sqlite3
    c = sqlite3.connect("file:%s?mode=ro" % (os.environ.get("KANBAN_DB") or os.path.join(crew_card.base_home(), "kanban.db")),
                        uri=True)
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


def msg(text, mid, *, stream, topic, sender_id, sender_email, sender_name):
    return {"id": mid, "type": "stream", "display_recipient": stream, "subject": topic,
            "sender_id": sender_id, "sender_email": sender_email, "sender_full_name": sender_name,
            "content": text, "timestamp": int(time.time())}


def pace(adapter, gap=0.15, tries=8):
    """Wrap the client's one request method: a small gap between calls, and honour the server's
    rate limiter instead of failing the walk.  Zulip answers 429 with ``retry_after``; the walk then
    waits exactly that long and tries again, so a burst of reads cannot end the run."""
    original = adapter.client._request

    def paced(method, path, form=None, params=None, timeout=None):
        state = paced.__dict__
        last = state.get("last", 0.0)
        wait = gap - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        for attempt in range(tries):
            try:
                out = original(method, path, form, params, timeout)
                state["last"] = time.time()
                return out
            except Exception as exc:                                  # noqa: BLE001
                if "429" not in str(exc):
                    raise
                state["last"] = time.time()
                time.sleep(float(getattr(exc, "retry_after", 0) or 0) + 0.4 * (attempt + 1))
        raise RuntimeError("rate limited on %s %s after %d tries" % (method, path, tries))

    adapter.client._request = paced


def find_owner(adapter, allowed, newest, span=150):
    """The owner's real Zulip user id, from the message history, cached after the first walk.

    The realm's user list needs an admin key, so the identity is read the same way the adapter reads
    it - from a message the owner sent - and the result is cached beside the evidence so a second walk
    spends two API calls instead of a hundred.  Returns (id, email, name, how).
    """
    cache = os.path.join(EVIDENCE_DIR, ".walk_owner.json")
    if os.path.isfile(cache):
        try:
            with open(cache) as fh:
                get = json.load(fh)
            m = fetch(adapter, int(get.get("message_id") or 0))
            if m and (m.get("sender_email") or "") in allowed:
                return int(m["sender_id"]), m["sender_email"], m.get("sender_full_name") or "", "cache"
        except Exception:                                             # noqa: BLE001
            pass
    for mid in range(newest, max(newest - span, 1), -1):
        m = fetch(adapter, mid)
        if not m or not m.get("sender_id"):
            continue
        if (m.get("sender_email") or "") in allowed:
            try:
                os.makedirs(EVIDENCE_DIR, exist_ok=True)
                with open(cache, "w") as fh:
                    json.dump({"user_id": m["sender_id"], "email": m["sender_email"],
                               "message_id": mid}, fh)
            except OSError:
                pass
            return int(m["sender_id"]), m["sender_email"], m.get("sender_full_name") or "", "message %s" % mid
    return 0, "", "", "not found in %d messages" % span


def fetch(adapter, mid, tries=3):
    """One message, tolerant of the API's rate limiter."""
    if not mid:
        return {}
    for attempt in range(tries):
        try:
            m = adapter.client.get_message(mid)
            return m if isinstance(m, dict) else {}
        except Exception as exc:                                      # noqa: BLE001
            if "429" in str(exc):
                time.sleep(0.25 * (attempt + 1))
                continue
            return {}
    return {}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stream", default="Kanban")
    ap.add_argument("--topic", default="PROBE crew live walk %s" % time.strftime("%H%M%S"))
    a = ap.parse_args()

    loaded = load_env()
    check("the profile's Zulip env is what the gateway uses", len(loaded) >= 3, ",".join(loaded))

    # the gateway's own plugin load runs first: the platform only becomes a valid Platform member
    # once the plugin has registered, so the harness loads plugins exactly as the gateway does
    from hermes_cli.plugins import get_plugin_manager             # noqa: E402
    get_plugin_manager().discover_and_load()
    from gateway.config import PlatformConfig                    # noqa: E402
    from gateway.platform_registry import platform_registry      # noqa: E402
    entry = platform_registry.get("zulip")
    factory = getattr(entry, "adapter_factory", None)
    check("the deployed zulip plugin is registered with the gateway",
          callable(factory), type(entry).__name__)
    cfg = PlatformConfig(enabled=True, extra={})
    adapter = factory(cfg)
    check("the deployed adapter constructs from that env", bool(adapter.site and adapter.bot_email),
          "%s as %s" % (adapter.site, adapter.bot_email))

    pace(adapter)
    me = adapter.client.users_me()
    adapter.bot_user_id = me.get("user_id")
    adapter.bot_full_name = me.get("full_name") or ""
    check("the bot identity is read from the server", bool(adapter.bot_user_id),
          "user id %s" % adapter.bot_user_id)

    # an owner event: any human in the realm, not the bot - the gateway's own filter is leg 2
    sent = adapter.client.send_stream(a.stream_placeholder if False else a.stream, a.topic,
                                      "/crew PROBE live walk - probe message, no action needed")
    first = int(sent.get("id") or 0)
    check("a real message lands in the topic (so ids are real)", first > 0, "message id %s" % first)
    allowed = {e.strip() for e in (os.environ.get("ZULIP_ALLOWED_USERS") or "").split(",") if e.strip()}
    owner_id, owner_email, owner_name, how = find_owner(adapter, allowed, first)
    check("the owner's own Zulip identity is found in the history",
          bool(owner_id) and owner_email in allowed, "user id %s (%s)" % (owner_id, how))

    delivered = []

    async def capture(event):
        delivered.append(event)

    adapter.set_message_handler(capture)

    # ---- leg 2a: the bot's own message never reaches the agent
    own = msg("crew ignore me", first, stream=a.stream, topic=a.topic, sender_id=adapter.bot_user_id,
              sender_email=adapter.bot_email, sender_name=adapter.bot_full_name)
    await adapter._dispatch(own)
    await asyncio.sleep(1.0)
    check("the adapter drops the bot's own message", not delivered, "%d delivered" % len(delivered))

    # this deployment runs the mention-only gate, so every human message in a stream topic names the
    # bot - build the owner's messages the way the owner actually has to send them
    mention = "@**%s** " % (adapter.bot_full_name or adapter.bot_email)

    # ---- leg 1: a /crew message routes to that same stream and topic
    await adapter._dispatch(msg(mention + "/crew PROBE live walk", first + 1, stream=a.stream,
                                topic=a.topic, sender_id=owner_id, sender_email=owner_email,
                                sender_name=owner_name))
    # the adapter hands the turn off to a task, so give the loop a moment before reading the capture
    await asyncio.sleep(1.5)
    routed = delivered[-1].source if delivered else None
    chat_id = getattr(routed, "chat_id", "") or ""
    check("a /crew message routes back to the stream and topic it came from",
          bool(delivered) and a.stream in chat_id and a.topic in chat_id, chat_id)

    # ---- leg 2b: a bare "crew ..." and an ordinary message licence no open
    before = q("select count(*) from tasks")[0][0]
    bare = msg(mention + "crew PROBE live walk", first + 2, stream=a.stream, topic=a.topic,
               sender_id=owner_id, sender_email=owner_email, sender_name=owner_name)
    plain = msg(mention + "PROBE live walk", first + 3, stream=a.stream, topic=a.topic,
                sender_id=owner_id, sender_email=owner_email, sender_name=owner_name)
    for m in (bare, plain):
        await adapter._dispatch(m)
    await asyncio.sleep(1.0)

    # ---- an unaddressed message reaches no agent at all (mention-only gate); ids ascend, because the
    # adapter drops anything at or below the newest message it has already seen
    seen = len(delivered)
    # in a topic the bot has not been addressed in: the mentioned messages above claimed this topic,
    # and topic following is what answers an unaddressed message inside a topic it already owns
    await adapter._dispatch(msg("crew PROBE unaddressed", first + 4, stream=a.stream,
                                topic=a.topic + " - unaddressed probe",
                                sender_id=owner_id, sender_email=owner_email, sender_name=owner_name))
    await asyncio.sleep(1.0)
    check("an unaddressed message reaches no agent (mention-only gate)",
          len(delivered) == seen, "%d delivered" % (len(delivered) - seen))
    after = q("select count(*) from tasks")[0][0]
    check("a bare 'crew ...' and an ordinary message deliver nothing to the crew", before == after,
          "%d -> %d cards" % (before, after))

    # the deployed gate itself, loaded from the installed plugin, on the two messages
    import importlib.util                                         # noqa: E402
    plug_path = os.path.join(PROFILE, "plugins", "crew", "__init__.py")
    spec = importlib.util.spec_from_file_location("crew_plugin_live_walk", plug_path)
    plug = importlib.util.module_from_spec(spec)
    sys.modules["crew_plugin_live_walk"] = plug
    spec.loader.exec_module(plug)
    OPEN = ("python3 \"$HERMES_HOME/scripts/crew_card.py\" open --title 'wordpress gate' --goal x "
            "--role worker --artifact a --lands b --audience c --done-when d --proof-cmd true "
            "--units e --constraints f")

    def guard(cmd, session, turn):
        return plug.crew_tool_guard(tool_name="terminal", args={"command": cmd},
                                    session_id=session, turn_id=turn)

    def blocked(res):
        return isinstance(res, dict) and str(res.get("action") or "").lower() == "block"

    plain_block = guard(OPEN, "S-plain", "T1")
    bare_block = guard(OPEN, "S-bare", "T1")
    plug.crew_intake_preload(user_message="/crew PROBE live walk", session_id="S-slash", turn_id="T1")
    slash_ok = guard(OPEN, "S-slash", "T1")
    check("the deployed guard refuses an open after an ordinary message", blocked(plain_block),
          str((plain_block or {}).get("message") or "")[:70])
    check("the deployed guard refuses an open after a bare 'crew ...'", blocked(bare_block))
    check("and allows it in a /crew turn", not blocked(slash_ok))

    # ---- leg 1 (cont.): the questions reach the topic, with the number reactions
    qid = adapter.client.send_stream(a.stream, a.topic,
                                     "PROBE questions: 1) goal 2) artifact 3) lands at")
    qmid = int(qid.get("id") or 0)
    reactions = [adapter.client.add_reaction(qmid, e) for e in ("one", "two", "three")]
    check("the questions land in that topic with number reactions",
          qmid > 0 and all("result" in r for r in reactions),
          "message id %s, %d reactions" % (qmid, len(reactions)))

    # ---- leg 4: the report goes back to that same stream and topic
    rep = adapter.client.send_stream(a.stream, a.topic,
                                     "PROBE report: the live walk reached this topic (leg 4).")
    rmid = int(rep.get("id") or 0)
    dest = adapter.client.get_message(rmid) or {}
    check("the report lands in that same stream and topic",
          rmid > 0 and dest.get("display_recipient") == a.stream and dest.get("subject") == a.topic,
          "message id %s in %s>%s" % (rmid, dest.get("display_recipient"), dest.get("subject")))

    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    path = os.path.join(EVIDENCE_DIR, "crew_live_walk_%s.json" % time.strftime("%Y%m%d_%H%M%S"))
    with open(path, "w") as fh:
        json.dump({"stream": a.stream, "topic": a.topic, "bot_user_id": adapter.bot_user_id,
                   "owner": {"user_id": owner_id, "email": owner_email, "name": owner_name},
                   "probe_message_id": first, "questions_message_id": qmid,
                   "reactions": [r.get("result") for r in reactions], "report_message_id": rmid,
                   "routed_chat_id": chat_id, "checks_failed": FAILS,
                   "ts": time.time()}, fh, indent=1)
    print("evidence: %s" % path)
    if FAILS:
        print("LIVE WALK FAIL: %d leg(s) missing: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("LIVE WALK OK: /crew routes to its own stream and topic, a bare word opens nothing, and the report "
          "goes back there")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
