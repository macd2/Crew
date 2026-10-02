"""Prove the crew guard's three rules on the real decision function, with real verdict lines on disk.

The guard is `crew_tool_guard` in the crew plugin. Three things are proved, each over its quadrants:

  1. the budget ceiling: a card at its ceiling may only be closed on a valid PASS; every write stays blocked
  2. the rework cap: after two failed verifications the writer may not re-submit or close
  3. the close rule: `kanban_complete` on a crew card needs a PASS line for its proof command, in every
     profile that loads the plugin (worker, verifier, the owner's chat), whatever the budget

    python3 scripts/crew_guard_quadrants.py

Verdict lines are written to a scratch home through crew_card.record_verdict (nothing is stubbed but the card
row); no kanban call is made and the live board is never read. Exit 0 only when every row behaves.
"""
import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crew_card  # noqa: E402 - the package checkout
PLUGIN = os.environ.get("CREW_PLUGIN", os.path.join(crew_card.package_dir() or os.path.dirname(HERE), "__init__.py"))
CARD = "t_guard_quadrants"
PROOF = "sh -c 'exit 0'"
BODY = ("Role: worker\nCoordinator: crew-coordinator\nBudget: 1000 tokens\n\nGOAL: prove the guard\n\n"
        "Done when: the guard behaves\n\nproof command: %s\n" % PROOF)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def action(res):
    a = "allow" if res is None else res.get("action", "allow")
    return "allow" if a == "modify" else a


def main():
    scratch = tempfile.mkdtemp(prefix="crew-quadrants-")
    home = os.path.join(scratch, "home")
    os.makedirs(os.path.join(home, "profiles", "crew-verifier"))
    db = os.path.join(scratch, "kanban.db")
    conn = sqlite3.connect(db)
    conn.executescript(
        "create table tasks (id text primary key, title text, status text, assignee text, body text, result text,"
        " workspace_path text);"
        "create table task_events (id integer primary key autoincrement, task_id text, run_id integer, kind text,"
        " payload text, created_at integer);")
    conn.execute("insert into tasks (id, title, status, assignee, body) values (?,?,?,?,?)",
                 (CARD, "guard", "running", "crew-worker", BODY))
    t_claim = int(time.time()) - 60
    conn.execute("insert into task_events (task_id, kind, payload, created_at) values (?, 'claimed', '{}', ?)",
                 (CARD, t_claim))
    conn.commit()
    conn.close()
    os.environ.update(HERMES_HOME=home, HERMES_KANBAN_DB=db)
    os.environ.pop("HERMES_KANBAN_TASK", None)
    os.environ.pop("HERMES_KANBAN_RUN_ID", None)
    tool = load("crew_card_quadrants", os.path.join(HERE, "crew_card.py"))
    mod = load("crew_plugin_under_test", PLUGIN)
    rows, bad = [], []

    def check(group, label, got, want):
        rows.append((group, label, got, want))
        if got != want:
            bad.append((group, label, got, want))

    def verdict(rc, command=PROOF, by="crew-worker", age=0):
        rec = tool.record_verdict(CARD, command, rc, "out", 0.1, by=by)
        if age:
            path = tool.verdict_path(CARD)
            lines = [json.loads(x) for x in open(path)]
            lines[-1]["ts"] -= age
            with open(path, "w") as fh:
                fh.write("".join(json.dumps(x) + "\n" for x in lines))
        return rec

    def reset():
        try:
            os.remove(tool.verdict_path(CARD))
        except OSError:
            pass

    def as_profile(profile):
        """Worker/verifier processes carry HERMES_KANBAN_TASK; the owner's chat has neither that nor a role."""
        os.environ.pop("HERMES_KANBAN_TASK", None)
        mod._ROLE = ""
        if profile in ("worker", "verifier"):
            os.environ["HERMES_KANBAN_TASK"] = CARD
            mod._ROLE = profile

    mod._BUDGET_CACHE.clear()
    mod._card_budget = lambda card: 0           # the close rule is proved with no ceiling in play
    mod._budget_used = lambda card: 0
    mod._note_overrun = lambda *a, **k: None

    # 3. the close rule, per profile
    for profile in ("worker", "verifier", "chat"):
        for label, setup, want in (
                ("no verdict line", lambda: None, "block"),
                ("PASS on the proof command", lambda: verdict(0), "allow"),
                ("FAIL on the proof command", lambda: verdict(1), "block"),
                ("PASS on another command only", lambda: verdict(0, command="echo hi"), "block"),
                ("PASS older than the newest claim", lambda: verdict(0, age=3600), "block"),
                ("PASS run by the owner's chat profile", lambda: verdict(0, by="owner-chat"), "block"),
                ("PASS, then a later check FAILs", lambda: (verdict(0), verdict(1, command="test -f nothing")),
                 "block")):
            reset()
            setup()
            as_profile(profile)
            res = mod.crew_tool_guard(tool_name="kanban_complete", args={"task_id": CARD, "summary": "done"})
            check("close rule / %s" % profile, label, action(res), want)
    # a card that is not a crew card is not the guard's business
    conn = sqlite3.connect(db)
    conn.execute("insert into tasks (id, title, status, assignee, body) values ('t_plain', 'p', 'running', 'x', "
                 "'just a card')")
    conn.commit()
    conn.close()
    as_profile("chat")
    check("close rule / chat", "a non-crew card",
          action(mod.crew_tool_guard(tool_name="kanban_complete", args={"task_id": "t_plain", "summary": "s"})),
          "allow")

    # 1. the budget ceiling (used 1000 of 1000), role worker
    mod._card_budget = lambda card: 1000
    mod._budget_used = lambda card: 1000
    for label, setup in (("PASS", lambda: verdict(0)), ("FAIL", lambda: verdict(1))):
        for tool_name, args in (("kanban_complete", {"task_id": CARD, "summary": "done"}),
                                ("write_file", {"path": "x"})):
            reset()
            setup()
            as_profile("worker")
            want = "allow" if (label == "PASS" and tool_name == "kanban_complete") else "block"
            check("budget ceiling", "%s / %s" % (label, tool_name),
                  action(mod.crew_tool_guard(tool_name=tool_name, args=args)), want)

    # 2. the rework cap: two FAIL lines stop the writer re-submitting or closing
    mod._card_budget = lambda card: 0
    mod._budget_used = lambda card: 0
    for tool_name in ("kanban_request_review", "kanban_complete"):
        reset()
        verdict(1)
        verdict(1)
        as_profile("worker")
        res = mod.crew_tool_guard(tool_name=tool_name, args={"task_id": CARD, "summary": "done"})
        check("rework cap", "%s after 2 FAILs" % tool_name, action(res), "block")
    reset()
    verdict(1)
    as_profile("worker")
    check("rework cap", "kanban_request_review after 1 FAIL",
          action(mod.crew_tool_guard(tool_name="kanban_request_review", args={"summary": "s"})), "allow")

    group = None
    for g, label, got, want in rows:
        if g != group:
            print("\n%s" % g)
            group = g
        print("  %-42s %-6s %s%s" % (label, got, want, "" if got == want else "   <-- MISMATCH"))
    print("\n%d rows, %d as expected, %d wrong" % (len(rows), len(rows) - len(bad), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
