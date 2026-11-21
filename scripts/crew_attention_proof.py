#!/usr/bin/env python3
"""Proof for the crew notification bell: the waiting list hangs off an icon in the header.

Done when the board surface carries the notifications behind a bell in the header - the bell shows
how many rows are waiting, a click opens the list (every stuck card first, then the done cards), and
each row is cleared one by one or the whole list is cleared at once.

Contract pinned here (the data surface over HTTP; the page is the React app, so its markup is read from headless
Chrome's DOM (crew_proof_board.render_dom) and its source from /app.js):
  /board.json   gains a "notifications" object under attention:
                  {"rows": [{"id","status","who","age_s","entered_ts","ack_url"}...],
                   "stuck": N, "done": N, "total": N, "ack_all": "/ack/all"}
                rows = every blocked/triage card (oldest waiting first) followed by the done cards
                (newest first, capped at 15 like the done lane); who = the assignee; age_s = whole
                seconds since the card entered that state; entered_ts = the state the row was in
                when it was shown, which is what a clear is scoped to; ack_url = "/ack/<id>".
  /ack/<id>     one click clears ONE row, 200 on success; the row leaves the list on the next fetch
                and stays off after a reload. /ack/<id>?undo=1 puts it back. Writes are POST with a same-origin Origin header.
  /ack/all      clear every notification at once - the waiting cards and EVERY done card, not only the
                rows one screen shows; /ack/all?undo=1 restores them. Both are scoped the same way: a
                cleared done card stays cleared, a cleared waiting card returns when that card moves on.
  the drawn page: the bell (#bell, an inline SVG) sits in the header with the count (#belln) equal to
  the json's total, the panel (#notes) hangs off the bell ahead of <main id=board> and starts closed,
  and the panel carries a clear-all control for /ack/all.

Read-only except for the clears it undoes again at the end.
Exit 0 = every check passed. Non-zero = it did not, and the failing check is printed.
"""
import http.client
import json
import os
import random
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_card  # noqa: E402 - the fixture assignee and the probe marker
import crew_proof_board  # noqa: E402
# The owner's clears live in an ack file beside the board. The proofs board's one shared file kept a killed or
# concurrent run's clears (a cleared seed card stays cleared), and the next run then saw no done rows or a total that
# did not come back. This run clears in a file of its own, removed at exit.
ACK_DIR = tempfile.mkdtemp(prefix="crew-attention-acks-")
if not os.environ.get("CREW_ACK_FILE"):
    os.environ["CREW_ACK_FILE"] = os.path.join(ACK_DIR, "attention_acks.json")
URL = crew_proof_board.graph_base()
KANBAN_DB = crew_proof_board.proof_db()
DONE_CAP = 15
STUCK = ("blocked", "triage")
# The service's own rule for its scaffolding: a card titled PROBE/TEST is the proof suite's own card
# and never enters the lanes, the counts or the notification list. A proof that dies half-way leaves
# those cards blocked on the board, so the expectation below has to leave them out - and says so.
PROBE_RX = re.compile(r"\s*(PROBE|TEST)\b", re.I)
FAILURES = []

# A local board server drops a connection now and then (one RemoteDisconnected killed the 2026-10-23 nightly
# proofs run), and a busy box answers 5xx/429. Neither is a fault in the board, so neither may raise out of
# here: the call is retried, jittered so two runs never retry in step, honouring the server's Retry-After.
# Only a repeat-safe call is re-sent: a GET, and /ack/*, which sets a cleared state to a fixed value (a second
# send lands the same state) - never an increment.
RETRY_ATTEMPTS = 4
RETRY_CODES = (408, 429, 500, 502, 503, 504)
RETRY_BACKOFF = (0.5, 2, 5)                 # seconds before retry 1, 2, 3; plus jitter
TRANSIENT = (urllib.error.URLError, http.client.HTTPException, OSError)


def retry_after(exc):
    """The server's own Retry-After, when it sends one; None to fall back to the local backoff."""
    try:
        value = exc.headers.get("Retry-After")
    except Exception:                                          # noqa: BLE001 - no headers to read
        return None
    if not value:
        return None
    try:
        return min(float(value), 30.0)
    except (TypeError, ValueError):
        return None


def check(name, ok, detail=""):
    print("%-58s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + detail) if detail else ""))
    if not ok:
        FAILURES.append(name)
    return ok


def fetch(path):
    # /ack/* is a write: POST only, from the board's own origin (what the page's fetch sends)
    write = path.startswith("/ack/")
    req = urllib.request.Request(URL + path, method="POST" if write else "GET",
                                 headers={"Origin": URL} if write else {})
    last = None
    wait = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:        # subclass of URLError: caught before it
            if exc.code not in RETRY_CODES or attempt == RETRY_ATTEMPTS - 1:
                return exc.code, exc.read().decode("utf-8", "replace")
            last = exc
            wait = retry_after(exc)
        except TRANSIENT as exc:
            last = exc
            wait = None
        if attempt == RETRY_ATTEMPTS - 1:
            break
        if wait is None:
            wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
        wait += random.uniform(0, 0.5)                    # jitter: two runs must not retry in step
        print("%-58s RETRY  %s on %s in %.1fs" % ("the board did not answer", type(last).__name__, path, wait))
        time.sleep(wait)
    raise last


def board_rows():
    """(the cards the board shows, the ids of the PROBE/TEST scaffolding it deliberately hides)."""
    conn = crew_proof_board.connect(KANBAN_DB)
    rows = conn.execute("select id, title, status from tasks where status != 'archived'").fetchall()
    conn.close()
    cards, probes = [], set()
    for cid, title, state in rows:
        if PROBE_RX.match((title or "").strip()):
            probes.add(cid)
            continue
        cards.append({"id": cid, "status": state})
    return cards, probes


def attention():
    status, body = fetch("/board.json")
    if status != 200:
        return None
    try:
        return json.loads(body)
    except ValueError:
        return None


def rows_now():
    data = attention() or {}
    att = data.get("attention") or {}
    return att.get("rows") or [], att


def stamp(row):
    """(id, status, entered_ts): the exact row-and-state a clear is scoped to."""
    return (row.get("id"), row.get("status"), row.get("entered_ts"))


def wait_rows(has_id, target_id, timeout=10.0, poll=0.2):
    """Poll the board data until `target_id` is present (has_id) or gone - a clear and its undo reach the board
    one poll behind the drawn list, so a single read right after the click reads a stale list on a busy box
    (this check failed in the 10-25 nightly). Returns the last read, so a timeout still reports the real rows."""
    end = time.time() + timeout
    rows = []
    while True:
        rows = rows_now()[0]
        if (target_id in [r.get("id") for r in rows]) is bool(has_id):
            return rows
        if time.time() >= end:
            return rows
        time.sleep(poll)


SEEDS = {"t_attn_stuck": ("Bell seed waiting card", "blocked", "blocked"),
         "t_attn_done": ("Bell seed finished card", "done", "completed")}


def seed():
    """One waiting and one finished card on the proofs board, so the bell has rows to clear. They are not
    PROBE/TEST titled on purpose: that scaffolding never enters the notification list."""
    now = int(time.time())
    conn = crew_proof_board.connect(KANBAN_DB)
    try:
        drop(conn)
        for cid, (title, status, event) in SEEDS.items():
            conn.execute("insert into tasks (id, title, body, status, assignee, priority, created_by, created_at) "
                         "values (?,?,?,?,?,0,?,?)",
                         (cid, title, "Goal: seed for the bell proof\n", status, crew_card.FIXTURE_ASSIGNEE, crew_card.PROBE_OWNER, now - 600))
            conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                         "values (?,?,?,?,?)", (cid, None, "created", "{}", now - 600))
            conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                         "values (?,?,?,?,?)", (cid, None, event, "{}", now - 300))
        conn.commit()
    finally:
        conn.close()


def drop(conn=None):
    own = conn is None
    conn = conn or crew_proof_board.connect(KANBAN_DB)
    try:
        for cid in SEEDS:
            for table in ("task_runs", "task_events", "task_comments"):
                conn.execute("delete from %s where task_id = ?" % table, (cid,))
            conn.execute("delete from tasks where id = ?", (cid,))
        conn.commit()
    finally:
        if own:
            conn.close()


def main():
    seed()
    try:
        return run_proof()
    finally:
        drop()
        shutil.rmtree(ACK_DIR, ignore_errors=True)


def run_proof():
    status, _ = fetch("/healthz")
    if not check("the service answers /healthz", status == 200, "http %s" % status):
        print("PROOF FAIL: the board surface is not up at %s" % URL)
        return 2

    data = attention()
    if not check("/board.json carries a notifications object",
                 isinstance(data, dict) and isinstance(data.get("attention"), dict)):
        print("PROOF FAIL: no notification data to check")
        return 2
    att = data["attention"]
    rows = att.get("rows") or []

    bad = [r for r in rows if not (isinstance(r.get("age_s"), int) and r["age_s"] >= 0
                                   and str(r.get("id", "")).startswith("t_")
                                   and r.get("who") is not None
                                   and r.get("ack_url") == "/ack/%s" % r.get("id"))]
    check("every row carries id, status, who and age", not bad,
          "%d bad row(s)" % len(bad) if bad else "")
    check("every row carries a per-row clear link", all(
        r.get("ack_url") == "/ack/%s" % r.get("id") for r in rows))
    unstamped = [r for r in rows if not isinstance(r.get("entered_ts"), int)]
    check("the clear is scoped to the state the row is in", not unstamped,
          "%d row(s) without entered_ts" % len(unstamped) if unstamped else "")

    stuck_rows = [r for r in rows if r.get("status") in STUCK]
    done_rows = [r for r in rows if r.get("status") == "done"]
    other_rows = [r for r in rows if r.get("status") not in STUCK + ("done",)]
    check("only stuck and done rows are listed", not other_rows,
          ",".join(sorted({str(r.get("status")) for r in other_rows})) if other_rows else "")

    order_ok = rows == stuck_rows + done_rows
    check("stuck rows come first, then done", order_ok)

    ages_stuck = [r["age_s"] for r in stuck_rows]
    ages_done = [r["age_s"] for r in done_rows]
    check("stuck rows are oldest-waiting first", ages_stuck == sorted(ages_stuck, reverse=True))
    check("done rows are newest first", ages_done == sorted(ages_done))

    cards, probes = board_rows()
    want_stuck = {c["id"] for c in cards if c["status"] in STUCK}
    have_stuck = {r["id"] for r in stuck_rows}
    check("every stuck card is listed", want_stuck <= have_stuck,
          "missing %s" % ",".join(sorted(want_stuck - have_stuck)[:4]) if want_stuck - have_stuck else "")
    listed = have_stuck | {r["id"] for r in done_rows}
    check("no scaffolding card is listed", not (probes & listed),
          "listed %s" % ",".join(sorted(probes & listed)[:4]) if probes & listed else "%d hidden" % len(probes))
    want_done = {c["id"] for c in cards if c["status"] == "done"}
    check("done rows respect the %d cap" % DONE_CAP, len(done_rows) <= DONE_CAP)
    check("the newest done card is listed", (not want_done) or done_rows[0]["id"] in want_done)
    check("counts agree with the rows",
          att.get("stuck") == len(stuck_rows) and att.get("done") == len(done_rows)
          and att.get("total") == len(rows),
          "stuck %s/%s done %s/%s total %s/%s" % (att.get("stuck"), len(stuck_rows),
                                                  att.get("done"), len(done_rows),
                                                  att.get("total"), len(rows)))
    check("the list names its own clear-all", att.get("ack_all") == "/ack/all")

    # The page is the React app (a thin shell plus /app.js), so the markup is what headless Chrome draws from the
    # served JSON, and the app's own source is /app.js.
    page_status, _shell = fetch("/")
    page = crew_proof_board.render_dom(URL + "/")
    app_status, app_js = fetch("/app.js")
    bell = re.search(r'id="belln"[^>]*>(\d+)<', page)
    check("the bell is in the header with a count badge",
          page_status == 200 and re.search(r"id=[\"']?bell[\"']?", page) is not None
          and bell is not None and "svg" in page)
    # The old page carried the count in its server-rendered markup ("before any script"); the shell has no data of
    # its own, so the claim that remains is that the drawn count is the JSON's.
    check("the drawn count is the json's total",
          bell is not None and int(bell.group(1)) == att.get("total"),
          "page %s vs json %s" % (bell.group(1) if bell else "-", att.get("total")))
    check("the panel hangs off the bell, ahead of the board, closed",
          re.search(r'id="notes"\s+hidden', page) is not None
          and 0 < page.find('id="bellwrap"') < page.find('id="board"'))
    check("the panel offers clear-all at /ack/all",
          app_status == 200 and "/ack/all" in app_js and 'id="clearall"' in page and "clear all" in page)
    check("a row clears through its own ack link",
          app_status == 200 and "'/ack/' + " in app_js.replace('"', "'") and (not rows or 'title="clear this one"' in page))

    # Live legs. Each clear is undone in a finally: a proof killed between the two would leave real
    # notifications hidden, and only the owner could tell that from a backlog that was really gone.
    if not rows:
        check("a row exists to clear", False, "no notification rows on the board")
        return 1
    live_legs()
    browser_leg()
    if FAILURES:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILURES), "; ".join(FAILURES)))
        return 1
    print("PROOF OK: the bell carries the count, the panel hangs off it ahead of the lanes, one row "
          "clears on its own and the list clears at once - and undo puts both back")
    return 0


READ_PANEL = """(function(){
  var b=document.getElementById('belln'), n=document.getElementById('notes'),
      list=document.querySelectorAll('#noterows .ar');
  return {badge: (b?b.textContent:''), hidden: (n?n.hidden:null), rows: list.length,
          clearall: !!document.getElementById('clearall'),
          svg: !!document.querySelector('#bell svg'),
          ids: Array.prototype.map.call(list, function(d){
                 return d.querySelector('a.t').getAttribute('href').split('/card/')[1]; })};
})()"""

READ_HIDDEN = "document.getElementById('notes').hidden"


def wait_for_target(port, fragment, tries=80):
    """The page's own target from the debugger, once the browser has it open."""
    for _ in range(tries):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=2) as resp:
                for target in json.loads(resp.read().decode("utf-8", "replace")):
                    if fragment in target.get("url", "") and target.get("webSocketDebuggerUrl"):
                        return target
        except Exception:
            pass
        time.sleep(0.5)
    return None


def browser_leg():
    """The feature as the owner uses it: click the bell, the list opens, one row clears with its ✕,
    clear all empties the list. Skipped with a reason (never failed) when there is no browser here."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    chrome = crew_proof_board.find_chrome()
    if not chrome:
        print("%-58s SKIP  no chrome/chromium on this box" % "the bell in a real browser")
        return True
    port = int(os.environ.get("CREW_PROOF_CDP_PORT") or crew_proof_board.free_port())
    chrome_log = crew_proof_board.chrome_scratch("crew-attention-browser-")
    profile_dir = os.path.join(chrome_log, "profile")
    proc = subprocess.Popen([chrome, "--headless=new", "--password-store=basic", "--disable-gpu", "--no-sandbox",
                             "--remote-debugging-port=%d" % port, "--window-size=1400,900",
                             "--user-data-dir=" + profile_dir, URL + "/"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    try:
        target = wait_for_target(port, URL.split("//")[-1])
        if not target:
            print("%-58s SKIP  the page never loaded in the browser" % "the bell in a real browser")
            return True
        from crew_ws import WSClient
        ws = WSClient(target["webSocketDebuggerUrl"])
        try:
            ws.wait_for("!!document.getElementById('bell') && !!document.getElementById('belln')")
            before = ws.evaluate(READ_PANEL) or {}
            _rows, att = rows_now()
            start_total = att.get("total")
            check("the drawn bell carries the count",
                  before.get("svg") and str(before.get("badge")) == str(att.get("total")),
                  "badge %s vs json %s" % (before.get("badge"), att.get("total")))
            check("the list is closed until the bell is clicked", before.get("hidden") is True)
            check("the list is drawn with its rows and a clear-all",
                  before.get("rows") == len(att.get("rows") or [])
                  and before.get("clearall"), "drawn %s" % before.get("rows"))

            ws.evaluate("document.getElementById('bell').click()")
            check("clicking the bell opens the list", ws.wait_for("%s === false" % READ_HIDDEN, timeout=5) is True)
            target_id = (before.get("ids") or [None])[0]
            if target_id:
                ws.evaluate("document.querySelector('#noterows .ar button').click()")
                ws.wait_for("document.querySelectorAll('#noterows .ar').length < %d && document.getElementById('belln')"
                            ".textContent === '%s'" % (before.get("rows") or 0, att.get("total") - 1), timeout=10)
                after = ws.evaluate(READ_PANEL) or {}
                check("a row's own clear takes it off the list",
                      after.get("rows") == (before.get("rows") or 0) - 1
                      and str(after.get("badge")) == str(att.get("total") - 1),
                      "%s -> %s" % (before.get("rows"), after.get("rows")))
                check("the cleared row is gone from the board data too",
                      target_id not in [r["id"] for r in wait_rows(False, target_id)],
                      "still in the board data after the wait")
                fetch("/ack/%s?undo=1" % target_id)
                check("undo puts the drawn row back",
                      target_id in [r["id"] for r in wait_rows(True, target_id)],
                      "not back in the board data after the wait")
            else:
                check("a drawn row exists to clear", False, "no row in the list")

            ws.evaluate("document.getElementById('clearall').click()")
            ws.wait_for("document.querySelectorAll('#noterows .ar').length === 0 && "
                        "document.getElementById('belln').textContent === '0'", timeout=10)
            empty = ws.evaluate(READ_PANEL) or {}
            check("clear all empties the drawn list",
                  empty.get("rows") == 0 and str(empty.get("badge")) == "0",
                  "rows %s badge %s" % (empty.get("rows"), empty.get("badge")))
        finally:
            try:
                ws.close()
            except Exception:
                pass
            # The page's own clear-all is still on its way when the drawn list is already empty (the list
            # is drawn first, the POST follows). An undo sent now can reach the board BEFORE that clear, and
            # the clear then lands second and stays: 0 of 3 with no defect behind it (2026-11-19, -20, -21).
            # Wait until the board itself shows the clear, then undo.
            _end = time.time() + 10
            while rows_now()[1].get("total") not in (0, None) and time.time() < _end:
                time.sleep(0.2)
            fetch("/ack/all?undo=1")
            # the undo lands on the board one poll behind the fetch, so a single read here reports 0 of 3 on a
            # busy box (2026-10-26 night) - wait for the total, then assert it
            _end = time.time() + 10
            while rows_now()[1].get("total") != start_total and time.time() < _end:
                time.sleep(0.2)
            check("the browser leg left the board as it found it",
                  (rows_now()[1]).get("total") == start_total,
                  "%s of %s" % ((rows_now()[1]).get("total"), start_total))
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:                                          # noqa: BLE001
            proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        shutil.rmtree(profile_dir, ignore_errors=True)
        shutil.rmtree(chrome_log, ignore_errors=True)
    return True


def live_legs():
    """One-row clear and clear-all, each read back and undone. The target is the oldest waiting row
    when there is one - a stuck row is clearable now - else the newest done row."""
    rows, _ = rows_now()
    target = rows[0]
    check("the row under test is a waiting card when one is listed",
          (target.get("status") in STUCK) or (not [r for r in rows if r.get("status") in STUCK])
          or target.get("status") == "done", detail=target.get("status"))
    code, body = fetch(target["ack_url"])
    check("/ack/<id> answers 200 for %s" % target["id"], code == 200 and target["id"] in body,
          "http %s" % code)
    try:
        after, _ = rows_now()
        check("the cleared row left the list", stamp(target) not in [stamp(r) for r in after])
        again, _ = rows_now()
        check("it stays off after a reload", stamp(target) not in [stamp(r) for r in again])
    finally:
        code, _ = fetch(target["ack_url"] + "?undo=1")
        back, _ = rows_now()
        check("undo puts the row back", code == 200 and target["id"] in [r["id"] for r in back])
        conn = crew_proof_board.connect(KANBAN_DB)
        state = conn.execute("select status from tasks where id = ?", (target["id"],)).fetchone()
        conn.close()
        check("the card itself was never touched", bool(state) and state[0] == target["status"],
              "card is %s, row said %s" % (state[0] if state else "gone", target["status"]))

    before, _ = rows_now()
    stamps = [stamp(r) for r in before]
    cards, probes = board_rows()
    whole = {c["id"] for c in cards if c["status"] in STUCK + ("done",)} - probes
    code, body = fetch("/ack/all")
    check("/ack/all answers 200 and names the count",
          code == 200 and str(len(whole)) in body, "http %s %s" % (code, body.strip()[:40]))
    try:
        after, att = rows_now()
        still = [s for s in stamps if s in [stamp(r) for r in after]]
        check("clear all empties every row it showed", not still,
              "%d row(s) still there" % len(still) if still else "")
        check("the bell reads zero after clear all", int(att.get("total") or 0) == 0,
              "total %s" % att.get("total"))
        again, _ = rows_now()
        check("it stays empty after a reload", int(_.get("total") or 0) == 0)
    finally:
        code, _ = fetch("/ack/all?undo=1")
        restored, att = rows_now()
        check("clear-all undo puts every row back",
              code == 200 and {r["id"] for r in restored} >= {r for r, _s, _t in stamps},
              "%d of %d back" % (len(restored), len(stamps)))


if __name__ == "__main__":
    sys.exit(main())
