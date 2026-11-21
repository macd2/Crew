#!/usr/bin/env python3
"""Proof that every card on the board has a card page, even before its first run.

Clicking a card on the board must open that card's page. Today a card that has not run yet has no
page at all: /card/<id> answers 404 with "no graph for <id> (card <id> has no runs yet - dispatch it
first)". That is the first click a person makes, so it has to work.

Done when:
  /card/<id> for a card in todo, ready or blocked with NO runs answers 200 and serves the card page:
    the card id and title are on it, the rail and the stage are there, and the page says in words
    that the card has not run yet instead of failing.
  /card/<id>.json answers 200 with situation.pending or an equivalent flag, runs as an empty list,
    and a reason that names the missing run rather than an error.
  A card that HAS run is unchanged: /card/<id> still renders its graph (the shell plus /app.js, read as a browser draws it).
  An unknown id still answers 404 - the fallback must not swallow real misses.

Exit 0 = every check passed. Non-zero = it did not, and the failing check is printed.
"""
import json
import os
import random
import sqlite3
import string
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_proof_board  # noqa: E402
import crew_card  # noqa: E402 - the owner profile and the base home
URL = crew_proof_board.graph_base()
KANBAN_DB = crew_proof_board.proof_db()
FAILURES = []


def check(name, ok, detail=""):
    print("%-58s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + detail) if detail else ""))
    if not ok:
        FAILURES.append(name)
    return ok


def has_id(page, name):
    return ("id=%s" % name) in page or ('id="%s"' % name) in page or ("id='%s'" % name) in page


def has_stage(page):
    """The graph's stage. The React page marks it class="stage" (it was id="stage" in the old script page)."""
    return has_id(page, "stage") or 'class="stage' in page


def rendered(path):
    """The card page as a browser shows it: the shell plus what /app.js drew (the dashboard is a React app)."""
    return crew_proof_board.render_dom(URL + path)


def get(path):
    try:
        with urllib.request.urlopen(URL + path, timeout=20) as fh:
            return fh.getcode(), fh.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def seed(status, runs):
    card = "t_" + "".join(random.choice(string.hexdigits[:16]) for _ in range(8))
    now = int(time.time())
    conn = crew_proof_board.connect(KANBAN_DB)
    try:
        conn.execute(
            "insert into tasks (id, title, body, assignee, status, priority, created_by, created_at, "
            "workspace_kind) values (?, ?, ?, ?, ?, 0, ?, ?, 'scratch')",
            (card, "PROBE never-run card %d" % now,
             "Coordinator: %s/\nGoal: probe card that has not run yet\nRole: worker\n"
             "proof command: true\n" % crew_card.owner_profile(), crew_card.FIXTURE_ASSIGNEE, status, crew_card.PROBE_OWNER, now))
        for i in range(runs):
            conn.execute(
                "insert into task_runs (task_id, profile, status, started_at, ended_at, outcome, "
                "summary, last_heartbeat_at) values (?, 'crew-worker', 'blocked', ?, ?, 'blocked', "
                "'probe run', ?)", (card, now - 300 + i, now - 240 + i, now - 240 + i))
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        print("note: seeding %s failed: %s" % (card, str(exc)[:90]))
        return None
    finally:
        conn.close()
    return card


def drop(card):
    conn = crew_proof_board.connect(KANBAN_DB)
    try:
        conn.execute("update tasks set status = 'archived' where id = ?", (card,))
        conn.commit()
    finally:
        conn.close()


def main():
    check("the board is reachable", get("/healthz")[0] == 200)
    fresh = seed("todo", 0)
    ran = seed("blocked", 2)
    if not fresh or not ran:
        print("PROOF FAIL: could not seed the probe cards")
        return 2
    try:
        code, shell = get("/card/%s" % fresh)
        check("a card with no runs still has a page", code == 200 and has_id(shell, "crew-app"), "HTTP %s" % code)
        page = rendered("/card/%s" % fresh)
        check("the page names the card", fresh in page)
        check("the page carries the card title", "PROBE never-run card" in page)
        check("the page keeps its rail", has_id(page, "rail"))
        check("the page keeps its stage", has_stage(page))
        check("the page carries the brand mark, linking to the overview",
              'class="brand" href="/"' in page)
        check("the page says the card has not run", "not run" in page.lower()
              or "no runs" in page.lower() or "hasn't run" in page.lower())
        code, raw = get("/card/%s.json" % fresh)
        check("its json answers", code == 200, "HTTP %s" % code)
        try:
            data = json.loads(raw)
        except Exception:
            data = {}
        sit = (data.get("situation") or {})
        runs = data.get("runs")
        check("its json carries no runs", runs in ([], None) or (isinstance(runs, list) and not runs),
              "runs=%r" % (runs,))
        check("its json explains the empty page",
              bool(str(sit.get("reason") or sit.get("why") or "").strip())
              or sit.get("pending") is True or data.get("pending") is True,
              json.dumps(sit)[:80])
        code, _shell = get("/card/%s" % ran)
        check("a card that has run is unchanged", code == 200 and has_stage(rendered("/card/%s" % ran)),
              "HTTP %s" % code)
        code, _ = get("/card/t_00000000")
        check("an unknown id is still a 404", code == 404, "HTTP %s" % code)
    finally:
        for card in (fresh, ran):
            drop(card)

    if FAILURES:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILURES), "; ".join(FAILURES)))
        return 1
    print("PROOF OK: every card on the board opens its page, before its first run and after it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
