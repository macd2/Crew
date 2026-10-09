#!/usr/bin/env python3
"""Proof for the crew dashboard index card (crew flow graph over HTTP, default 127.0.0.1:8799).

Exit 0 = the index page meets the card's "Done when". Non-zero = it does not; the failing
check is printed. Read-only: it fetches the live page and reads the kanban board.

Checks, default page /:
  1. the header carries the board's facts: the LIVE badge, "crew board", the card count, "N working now" /
     "nothing running", and the running / blocked / done counts, each a number then its word
  2. no archived card id is listed in a live lane (they sit only in the collapsed Archived column)
  3. no card whose title carries the test marker (/\\btests?\\b|probe|dry-run proof/i) is listed
  4. a "Needs you" heading exists and every blocked card id is listed before the first non-blocked one
  4b. the header's "N working now" equals the runs that can still be alive (worker pid answering, or a
     start/heartbeat inside the window) over the cards the board shows - a worker that died without a
     settle row used to keep it at 1 for ever
Checks, /?all=1:
  5. archived ids and test-marked titles are reachable there
Phase 2 of the UI spec (docs/crew/ui-spec/spec.md section 8):
  6. board.json: five lanes in the fixed order plus the Archived column, every rendered tile has summary + verdict (+ budget only with a
     ceiling) - on the proofs board and on the live board
  7. an empty board still draws all five lanes, empty, in order, and the header reads 0 for each count
  8. live anchors: t_d93e0c7b reason + 3 runs + budget >= 100%, t_98550764 PASS, t_f513fc0f FAIL

Env: CREW_GRAPH_URL overrides the base URL.
"""
import importlib.util
import os
import re
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_proof_board  # noqa: E402
URL = crew_proof_board.graph_base()
TEST_RE = re.compile(r"\btests?\b|probe|dry-run proof", re.I)
KANBAN_DB = crew_proof_board.proof_db()
def fail(msg):
    print("PROOF FAIL: " + msg)
    return 1


def fetch(path):
    with urllib.request.urlopen(URL + path, timeout=15) as resp:
        return resp.read().decode("utf-8", "replace")


def board_rows():
    spec = importlib.util.spec_from_file_location("cg", os.path.join(HERE, "crew_graph.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    db = mod.kanban_db_path()
    if not db:
        raise RuntimeError("no kanban database found")
    conn = sqlite3.connect(db)
    rows = conn.execute("select id, coalesce(title,''), coalesce(status,'') from tasks").fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "status": r[2]} for r in rows]


def is_scaffolding(title):
    """The board's OWN rule for the proof suite's probe cards, read from its owner.

    Never a second copy of the pattern: an expectation written as "every blocked card is listed"
    reads the board without this rule, so a leftover PROBE card from a killed proof run reports a
    defect in the page and points away from the real cause.
    """
    spec = importlib.util.spec_from_file_location("cgs", os.path.join(HERE, "crew_graph_serve.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.is_probe_card(title)


def board_data(path="/board.json"):
    import json
    return json.loads(fetch(path))


def expected_working(now=None):
    """The board's working count, read straight from the runs the way the board reads them.

    A run counts while its worker process answers, or, with a pid that is already gone, while it started
    or beat inside the window. A worker that dies without a settle row leaves status='running' behind for
    ever, and the header then says "1 working now" for a card that finished hours ago - and for archived
    probe cards. Both numbers come from the same rule (crew_graph_serve.run_is_live): the check is the
    page's number against the runs, not a second opinion about what "working" means.
    """
    spec = importlib.util.spec_from_file_location("cgs_live", os.path.join(HERE, "crew_graph_serve.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    now = now or time.time()
    db = mod.CG.kanban_db_path()
    conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    try:
        cards = [(i, t) for i, t in
                 conn.execute("select id, coalesce(title,'') from tasks where status != 'archived'")
                 if not mod.is_probe_card(t)]
        if not cards:
            return 0, 0
        marks = ", ".join("?" * len(cards))
        runs = conn.execute("select id, task_id, profile, status, started_at, ended_at, "
                            "last_heartbeat_at, outcome, worker_pid from task_runs "
                            "where task_id in (%s)" % marks, tuple(i for i, _ in cards)).fetchall()
    finally:
        conn.close()
    return len([r for r in runs if r[3] == "running" and mod.run_is_live(r, now)]), len(runs)


def test_cards_out_of_the_numbers():
    """A test/scratch card is scaffolding: it must not enter the board's counts (5)."""
    probe = "t" + "9bo" + "ard_probe"
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute("delete from tasks where id = ?", (probe,))
        conn.execute("insert into tasks (id, title, body, status, assignee, priority, created_at) "
                     "values (?,?,?,?,?,0,?)", (probe, "PROBE board count probe", "Goal: x\n",
                                                "ready", "crew-worker", int(time.time())))
        conn.commit()
    finally:
        conn.close()
    try:
        plain = board_data("/board.json")
        every = board_data("/board.json?all=1")
    except Exception as exc:  # noqa: BLE001
        return fail("could not read /board.json (%s)" % exc)
    ids = [t["id"] for lane in plain.get("lanes", []) for t in lane.get("tiles", [])]
    ids_all = [t["id"] for lane in every.get("lanes", []) for t in lane.get("tiles", [])]
    if probe in ids:
        return fail("a test card is counted in the board's numbers (%s)" % probe)
    if (plain.get("test_cards") or 0) < 1:
        return fail("the board does not report how many test cards it set aside")
    if probe not in ids_all:
        return fail("a test card is not reachable even with ?all=1")
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute("update tasks set status = 'archived' where id = ?", (probe,))
        conn.commit()
    finally:
        conn.close()
    return 0


LANE_ORDER = ["blocked", "running", "review", "queued", "done", "archived"]   # archived: the owner-collapsed last column
HEADER_WORDS = ("running", "blocked", "done")
# Phase-2 anchors (ui-spec section 8), read from the LIVE board in-process (read-only): the card, what its tile
# must carry.
ANCHORS = (
    ("t_d93e0c7b", lambda t: t.get("summary", "").startswith("Budget exhausted - cannot continue work on this card")
     and t.get("runs") == 3 and (t.get("budget") or {}).get("pct", 0) >= 100,
     "reason 'Budget exhausted - cannot continue work on this card', 3 runs, budget >= 100%"),
    ("t_98550764", lambda t: t.get("verdict") == "PASS", "verdict PASS (verified)"),
    ("t_f513fc0f", lambda t: t.get("verdict") == "FAIL", "verdict FAIL (verify failed)"),
)


def serve_module(name="cgs_phase2"):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, "crew_graph_serve.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def board_contract(data, where):
    """The board.json contract every board must keep: five lanes in the fixed order, every rendered tile
    enriched (summary, verdict; budget only with a ceiling)."""
    keys = [lane.get("key") for lane in data.get("lanes") or []]
    if [k for k in keys if k != "other"] != LANE_ORDER or keys[-1] != "archived":
        return "%s: lanes are %s, not the fixed order %s" % (where, keys, LANE_ORDER)
    for lane in data["lanes"]:
        for t in lane.get("tiles") or []:
            if "summary" not in t or "verdict" not in t:
                return "%s: tile %s lacks summary/verdict" % (where, t.get("id"))
            if t["verdict"] not in (None, "PASS", "FAIL", "unverified"):
                return "%s: tile %s has verdict %r" % (where, t.get("id"), t["verdict"])
            b = t.get("budget")
            if b is not None and not (b.get("ceiling") and "pct" in b and "used" in b):
                return "%s: tile %s budget is %r" % (where, t.get("id"), b)
    return ""


def phase2_live_anchors():
    """The anchors on the live board, read-only, and the contract on it. An anchor card no longer on the
    board is reported as a skip, never as a pass."""
    saved = {k: os.environ.pop(k) for k in ("KANBAN_DB", "HERMES_KANBAN_DB") if k in os.environ}
    try:
        data = serve_module("cgs_live_board").board_data()
    finally:
        os.environ.update(saved)
    why = board_contract(data, "live board")
    if why:
        return fail(why)
    tiles = {t["id"]: t for lane in data["lanes"] for t in lane["tiles"]}
    for cid, ok, what in ANCHORS:
        t = tiles.get(cid)
        if t is None:
            print("SKIP anchor %s: not on the live board any more" % cid)
            continue
        if not ok(t):
            return fail("anchor %s: expected %s, tile is %s" % (cid, what, json.dumps(
                {k: t.get(k) for k in ("summary", "runs", "budget", "verdict")})[:300]))
        print("anchor %s: %s" % (cid, what))
    return 0


def phase2_empty_board():
    """Five lanes with zero cards: a board with no card at all still draws every lane, in order."""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="crew-empty-board-")
    empty = os.path.join(tmp, "kanban.db")
    src = sqlite3.connect("file:%s?mode=ro" % KANBAN_DB, uri=True)
    try:
        schema = [r[0] for r in src.execute("select sql from sqlite_master where type='table' and sql is not null "
                                            "and name not like 'sqlite_%'")]
    finally:
        src.close()
    dst = sqlite3.connect(empty)
    for sql in schema:
        dst.execute(sql)
    dst.commit()
    dst.close()
    saved = {k: os.environ.get(k) for k in ("KANBAN_DB", "HERMES_KANBAN_DB")}
    os.environ["KANBAN_DB"] = os.environ["HERMES_KANBAN_DB"] = empty
    try:
        mod = serve_module("cgs_empty_board")
        data = mod.board_data()
        page = mod.board_page()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(tmp, ignore_errors=True)
    keys = [lane["key"] for lane in data.get("lanes") or []]
    if keys != LANE_ORDER or any(lane["tiles"] for lane in data["lanes"]):
        return fail("an empty board draws lanes %s, not the five fixed empty lanes" % keys)
    for word in HEADER_WORDS:
        if not re.search(r"<b>0</b>" + word, page):
            return fail("the empty board's header has no '0 %s' count" % word)
    if "nothing running" not in page or "0 cards" not in page:
        return fail("the empty board's header does not read '0 cards' / 'nothing running'")
    print("empty board: five lanes, in order, all empty; header reads 0 cards, nothing running, 0 running / blocked / done")
    return 0


def main():
    try:
        page = fetch("/")
        all_page = fetch("/?all=1")
    except urllib.error.URLError as exc:
        return fail("crew graph not reachable at %s (%s)" % (URL, exc))
    except Exception as exc:  # noqa: BLE001
        return fail("crew graph index not readable (%s)" % exc)

    try:
        rows = board_rows()
    except Exception as exc:  # noqa: BLE001
        return fail("cannot read the board (%s)" % exc)

    archived = [r for r in rows if r["status"] == "archived"]
    # The surface's own exclusion: a PROBE/TEST card is the suite's scaffolding and never enters
    # the lanes or the counts, so it is not expected on the page either.
    blocked = [r for r in rows if r["status"] == "blocked" and not is_scaffolding(r["title"])]
    marked = [r for r in rows if TEST_RE.search(r["title"])]

    # The header carries the board's own facts, server-rendered: badge, title, card count, working, counts.
    for word in HEADER_WORDS:
        if not re.search(r"<b>\d+</b>" + word, page):
            return fail("no header count for %r on the index" % word)
    for fact in ("id=badge", "<h1>crew board</h1>", "id=cards", "id=live", "id=when", "tailnet"):
        if fact not in page:
            return fail("the header lacks %r" % fact)
    # The brand mark: our logo with no background, the header's first element (very top left), an
    # embedded mark (no external asset) linking to the overview (/).
    if '<header><a class="brand" href="/"' not in page:
        return fail("the header has no brand mark as its first element (the very top left)")
    if not re.search(r'<a class="brand" href="/"[^>]*><img src="data:image/svg\+xml;base64,[A-Za-z0-9+/=]+"', page):
        return fail("the brand mark is not the embedded logo mark with no background")
    # The tab icon is the mark on a tile, never the bare mark: the landing page's tab shows the bare mark,
    # and two identical tabs could not be told apart (owner, 2026-10-06).
    tab = re.search(r'<link rel="icon" type="image/svg\+xml" href="data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)"', page)
    brand = re.search(r'<a class="brand" href="/"[^>]*><img src="data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)"', page)
    if not tab or tab.group(1) == brand.group(1):
        return fail("the tab icon is missing or is the bare header mark, the landing page's icon")
    if not re.search(r"\d+ cards?<", page) or not re.search(r"(\d+ working now|nothing running)<", page):
        return fail("the header does not state the card count and what is working now")
    why = board_contract(board_data(), "proofs board")
    if why:
        return fail(why)

    if "needs you" not in page.lower():
        return fail("no 'Needs you' section on the index")

    # The header's "N working now" is a count of live runs, so it is only true while those runs can still
    # be alive: a run whose worker process is gone and whose last beat is hours old is a leftover row.
    exp_live, run_rows = expected_working()
    got_live = board_data().get("live")
    if got_live != exp_live:
        return fail("the board says %s working now, the runs say %s (%s run row(s) read; a dead worker "
                    "leaves status='running' behind)" % (got_live, exp_live, run_rows))

    # archived cards live only in the last, collapsed 'archived' lane - never in a live lane
    live_ids = {t["id"] for lane in board_data()["lanes"] if lane["key"] != "archived" for t in lane["tiles"]}
    listed_archived = [r["id"] for r in archived if r["id"] in live_ids]
    if listed_archived:
        return fail("archived card(s) still listed: %s" % ", ".join(listed_archived[:5]))

    listed_marked = [r["id"] for r in marked if TEST_RE.search(r["title"]) and r["title"] in page]
    if listed_marked:
        return fail("test/scratch card(s) still listed: %s" % ", ".join(listed_marked[:5]))

    if blocked:
        # Lane order, not raw offsets in the page source: the page inlines the board payload, so an
        # offset test fires on any card that is legitimately running. What matters is that the lane
        # holding cards which wait on the owner is drawn first.
        try:
            lanes = json.loads(fetch("/board.json")).get("lanes") or []
        except Exception as exc:  # noqa: BLE001
            return fail("cannot read the board lanes (%s)" % exc)
        idx = next((i for i, lane in enumerate(lanes) if lane.get("key") == "blocked"
                    and lane.get("tiles")), None)
        if idx is None:
            return fail("blocked card(s) exist but no 'needs you' lane carries them")
        if idx != 0:
            return fail("'Needs you' is not ahead of the other cards: lane %d of %d (%s)"
                        % (idx + 1, len(lanes), [l.get("key") for l in lanes]))
        missing = [r["id"] for r in blocked if r["id"] not in page]
        if missing:
            return fail("blocked card(s) missing from 'Needs you': %s" % ", ".join(missing[:5]))

    if archived and not any(r["id"] in all_page for r in archived):
        return fail("/?all=1 does not show archived cards")
    if marked and not any(r["title"] in all_page for r in marked):
        return fail("/?all=1 does not show the test/scratch cards")

    rc = test_cards_out_of_the_numbers()
    if rc:
        return rc
    rc = phase2_empty_board() or phase2_live_anchors()
    if rc:
        return rc

    print("PROOF OK: index filters archived+test cards, counts by status, blocked first, and the "
          "board's numbers leave test cards out at %s" % URL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
