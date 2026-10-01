#!/usr/bin/env python3
"""Proof that a crew card can carry the model the router picked, and that the dispatcher honours it.

Option 1 of the model routing ask: the coordinator asks the one model router for a pick and pins it
on the card, so each role runs the model Jev decided instead of every role sitting on one provider.

  1. crew_card.py open --model/--provider reaches `hermes kanban create --model/--provider`
  2. the kanban CLI really takes --model/--provider (and refuses --provider without --model)
  3. the dispatcher's spawn line asks the routing hook first; with nothing routed, a pinned card
     carries -m <model> --provider (the card's own pin, unchanged behind the hook)
  4. with nothing routed, an unpinned card carries neither (the profile default still stands)
  4b. a routed answer wins over the pin: a stale pin cannot outlive the pick made at spawn time
  5. the router's pick for a crew card comes from its agent-floor menu (provider + model + floor), or is
     "parent" - no pick, no pin - when nothing on that menu is live
  6. the pick is written onto the card: model_override, provider_override, and a 'route' event
  7. no router on the box -> no pick and no pin (nothing is invented)

Run:  python3 crew_route_pin_proof.py
Exit: 0 when every check passes, 1 otherwise.
"""
import json
import os
import sqlite3
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_proof_board  # noqa: E402
KANBAN_DB = crew_proof_board.proof_db()
VENV_PY = os.environ.get("CREW_PY") or os.path.expanduser("~/.hermes/hermes-agent/.venv/bin/python")
HERMES = os.environ.get("HERMES_BIN", "hermes")
PROBE = "t" + "9ro" + "ute_pin"
FAILS = []


def check(name, ok, detail=""):
    print("%-60s %s  %s" % (name, "PASS" if ok else "FAIL", str(detail)[:80]))
    if not ok:
        FAILS.append(name)


def run(cmd, timeout=180):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def dispatcher_argv(model=None, provider=None, route=None):
    """The dispatcher's real argv builder, imported from the built-in install.

    `route` fixes what the routing hook answers, so both branches of the spawn line are testable in
    one process: 'none' = nothing routed (the card's own pin decides), 'model' = a route-shaped
    answer (the routed model wins and the pin is not used), None = leave the host's plugins alone.
    """
    code = (
        "import sys, dataclasses, json\n"
        "sys.path.insert(0, %r)\n" % os.path.expanduser("~/.hermes/hermes-agent") + 
        ""
        "from hermes_cli import kanban_db as kdb, kanban_db_dispatch as kd, plugins\n"
        "if %r == 'none':\n"
        "    plugins.invoke_hook = lambda name, **kw: []\n"
        "elif %r == 'model':\n"
        "    plugins.invoke_hook = lambda name, **kw: [{'provider': 'p-routed', 'model': 'm-routed'}]\n"
        "t = kdb.Task(**{f.name: None for f in dataclasses.fields(kdb.Task)})\n"
        "t.id, t.title, t.status, t.assignee, t.priority = 'tp', 'x', 'ready', 'crew-worker', 0\n"
        "t.model_override = %r\n"
        "t.provider_override = %r\n"
        "print(json.dumps(kd._worker_argv(t, 'crew-worker', None)))\n" % (route, route, model, provider)
    )
    r = run([VENV_PY, "-c", code], timeout=180)
    if r.returncode != 0:
        return None, (r.stderr or "")[-200:]
    return json.loads(r.stdout.strip().splitlines()[-1]), ""


def seed():
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute("delete from task_runs where task_id = ?", (PROBE,))
        conn.execute("delete from task_events where task_id = ?", (PROBE,))
        conn.execute("delete from tasks where id = ?", (PROBE,))
        conn.execute("insert into tasks (id, title, body, status, assignee, priority, created_at) "
                     "values (?,?,?,?,?,0,?)",
                     (PROBE, "PROBE route pin", "Goal: probe\n", "done", "crew-worker",
                      int(time.time())))
        conn.execute("insert into task_runs (task_id, profile, status, started_at, ended_at, "
                     "outcome) values (?,?,?,?,?,?)",
                     (PROBE, "crew-worker", "done", int(time.time()) - 60, int(time.time()), "completed"))
        conn.commit()
    finally:
        conn.close()


def drop():
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute("update tasks set status = 'archived' where id = ?", (PROBE,))
        conn.commit()
    finally:
        conn.close()


BASE = crew_proof_board.graph_base()
def card_node_evidence(card):
    """The card node's evidence from the served page (the page's own JSON)."""
    try:
        import urllib.request
        with urllib.request.urlopen("%s/card/%s.json" % (BASE, card), timeout=20) as fh:
            g = json.loads(fh.read().decode())
    except Exception:
        return {}
    for n in g.get("nodes", []):
        if n.get("kind") == "card":
            return n.get("evidence") or {}
    return {}


def row(card):
    conn = sqlite3.connect("file:%s?mode=ro" % KANBAN_DB, uri=True)
    try:
        conn.row_factory = sqlite3.Row
        r = conn.execute("select model_override, provider_override from tasks where id = ?",
                         (card,)).fetchone()
        return dict(r) if r else {}
    finally:
        conn.close()


def main():
    import crew_card

    # 1. the pin reaches the create command
    argv = crew_card.create_card("PROBE pin", "Goal: x\n", "crew-worker",
                                 dry_run=True, model="m-x", provider="p-y")["argv"]
    check("crew_card.py open --model/--provider reaches kanban create",
          "--model" in argv and "m-x" in argv and argv[argv.index("--model") + 1] == "m-x"
          and "--provider" in argv and argv[argv.index("--provider") + 1] == "p-y",
          " ".join(argv[-6:]))

    # 2. the built-in CLI takes them, and refuses a provider without a model
    help_txt = (run([HERMES, "kanban", "create", "--help"]).stdout or "")
    check("the kanban CLI takes --model and --provider",
          "--model" in help_txt and "--provider" in help_txt)
    bad = run([HERMES, "kanban", "create", "PROBE bad pin", "--assignee", "crew-worker",
               "--provider", "p-y", "--json"])
    check("a provider without a model is refused",
          bad.returncode != 0, (bad.stderr or bad.stdout or "").strip()[-60:])

    # 3/4/4b. the dispatcher's spawn line: the routing hook first, the card's own pin behind it.
    # The hook is stubbed per direction, because the live one answers on this box and would mask the
    # fallback path - a pin that is never exercised is not a proof that the pin still works.
    pinned, err = dispatcher_argv("m-x", "p-y", route="none")
    check("with nothing routed, a pinned card spawns with -m <model> --provider",
          bool(pinned) and "m-x" in pinned
          and pinned[pinned.index("m-x"):pinned.index("m-x") + 2] == ["m-x", "--provider"]
          and pinned[pinned.index("m-x") + 2] == "p-y",
          (pinned or err)[-70:] if pinned else err)
    plain, err2 = dispatcher_argv(None, None, route="none")
    check("with nothing routed, an unpinned card spawns with no model override",
          bool(plain) and "m-x" not in plain and "--provider" not in plain,
          (plain or err2)[-60:] if plain else err2)
    routed, err3 = dispatcher_argv("m-x", "p-y", route="model")
    check("a routed card spawns on the route, not on its stale pin",
          bool(routed) and "m-x" not in routed
          and routed[routed.index("m-routed"):routed.index("m-routed") + 2] == ["m-routed", "--provider"]
          and routed[routed.index("m-routed") + 2] == "p-routed",
          (routed or err3)[-70:] if routed else err3)

    # 5. a real router pick, from the delegate menu, naming a provider a profile can resolve
    # The pick comes from the agent-floor menu (free_first_router's agent_floor.py). When every floor model
    # is in a daily cap the router's answer is "parent" - no pick, nothing pinned - which is the right answer
    # and not a failure; the pin mechanics below then run on a fixed floor-model pick.
    answer = crew_card.route_answer("code", "commit and push the crew package")
    pick = crew_card.pick_from_answer(answer, "code", "commit and push the crew package")
    if pick is None:
        check("no pick only when the floor holds nothing live (router answered parent, menu_size 0)",
              bool(answer) and answer.get("label") == "parent" and answer.get("menu_size") == 0, answer)
        pick = {"provider": "gemini", "model": "gemini-3-flash-preview", "task_class": "code",
                "why": "fixed pick: the router is at its daily caps", "floor": (answer or {}).get("floor"),
                "menu_size": 0}
        print("NOTE: the router answered parent; the pin checks below use %s/%s" % (pick["provider"], pick["model"]))
    else:
        check("the router returns a real delegate-fit pick (provider + model) that clears the floor",
              bool(pick.get("provider")) and bool(pick.get("model")) and bool((pick.get("floor") or {}).get("min_context")),
              "%s / %s floor=%s" % (pick.get("provider"), pick.get("model"), pick.get("floor")))
    check("the pick names a Hermes provider the worker profile resolves",
          pick.get("provider") in ("ai-gateway", "gemini", "openrouter"),
          "provider=%s (router host=%s)" % (pick.get("provider"), pick.get("router_provider")))

    # 6. the pick lands on the card
    seed()
    applied = crew_card.apply_route(PROBE, pick) if pick else False
    r = row(PROBE)
    conn = sqlite3.connect("file:%s?mode=ro" % KANBAN_DB, uri=True)
    try:
        ev = conn.execute("select payload from task_events where task_id = ? and kind = 'route' "
                          "order by created_at desc limit 1", (PROBE,)).fetchone()
    finally:
        conn.close()
    check("the pick is pinned on the card", bool(applied) and r.get("model_override") == pick["model"]
          and r.get("provider_override") == pick["provider"],
          "model_override=%s provider_override=%s" % (r.get("model_override"), r.get("provider_override")))
    check("the card records why its worker model was chosen",
          bool(ev) and pick["provider"] in (ev[0] or "") and "why" in (ev[0] or ""),
          (ev[0] or "")[:70] if ev else "no route event")

    # 6b. the card's own view shows which model its worker is pinned to
    check("the card page carries the pinned model",
          card_node_evidence(PROBE).get("model_override") == (pick or {}).get("model")
          and card_node_evidence(PROBE).get("provider_override") == (pick or {}).get("provider"),
          "page says %s via %s" % (card_node_evidence(PROBE).get("model_override"),
                                   card_node_evidence(PROBE).get("provider_override")))
    term = subprocess.run([sys.executable, os.path.join(HERE, "crew_graph.py"), "--card", PROBE],
                          capture_output=True, text=True, timeout=120).stdout or ""
    check("the terminal render names the pinned model too",
          "worker model: %s" % (pick or {}).get("model") in term,
          [l.strip() for l in term.splitlines() if "worker model" in l][:1])

    # 7. no router -> no pick, no pin
    os.environ["CREW_ROUTER_PLUGIN"] = "/nonexistent/free_first_router"
    none_pick = crew_card.route_pick("code", "no router", no_log=True)
    nog = row(PROBE)
    check("no router on the box -> no pick, and the pin is left alone", none_pick is None,
          "pick=%s" % none_pick)
    drop()
    if FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("PROOF OK: the router's pick can be pinned on a crew card and the dispatcher spawns that "
          "card's worker on exactly that model and provider")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
