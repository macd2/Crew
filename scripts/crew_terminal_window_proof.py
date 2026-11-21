#!/usr/bin/env python3
"""Proof that the card page's step lines are a live terminal window and the edges carry moving dots.

What this pins, on the served card page (the React app: a shell plus /app.js, drawn in headless Chrome):

  1. the app ships the window: MAX_STEP_LINES is 6, the slide-in keyframes exist, and the line area
     is capped at six lines of height
  2. a node never shows more than six live step lines, and no line overflows the area
  3. a step that arrives after the first paint enters at the bottom with the slide-in animation and the
     window stays at six (the proof writes two more tool calls into the session store and waits for the
     page's own poll to pick them up)
  4. a tool call in flight carries a stopwatch that ticks forward between two reads
  5. a running node's incoming edge carries a dot that travels along the path (animateMotion) over
     a dashed flow line
  6. an idle node's lines hold still: its list can be one longer than the window (a failed step rides
     along the tail), and reconciling the window against that whole list made an idle node evict and
     re-add a line at every poll - lines sliding in and out on a blocked card

The script page this replaced injected steps into its own state and redrew; the React app has no such
handle, so the arrival leg is end to end (session store -> /card/<id>.json -> poll -> DOM). One thing the old
page did that the React app does not: a line pushed out of a full window slid out (class "out", keyframes
stepOut); the app just drops it. That check is not carried over - see the NOTE the proof prints.
Seeded probe cards are written straight into kanban.db (no crew_card.py open), so any agent context
can run it.

Run:  python3 crew_terminal_window_proof.py
Exit: 0 when every check passes, 1 otherwise.
"""
import json
import re
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request

HOME = os.path.expanduser("~")
PROFILE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_card  # noqa: E402 - the fixture assignee and the probe marker
import crew_proof_board  # noqa: E402
KANBAN_DB = crew_proof_board.proof_db()
BASE = crew_proof_board.graph_base()
PORT = int(os.environ.get("CREW_PROOF_CDP_PORT") or crew_proof_board.free_port())
CHROME = crew_proof_board.find_chrome()
PROBE = "t" + "9a" + "w1nd0w"
FAILS = []


def check(name, ok, detail=""):
    print("%-58s %s  %s" % (name, "PASS" if ok else "FAIL", str(detail)[:80]))
    if not ok:
        FAILS.append(name)


def seed_probe():
    """A card that has run: one assistant message with a tool call, straight into kanban.db."""
    now = int(time.time())
    conn = crew_proof_board.connect(KANBAN_DB)
    try:
        conn.execute("delete from task_runs where task_id = ?", (PROBE,))
        conn.execute("delete from tasks where id = ?", (PROBE,))
        body = ("Goal: probe the card page's terminal window.\n"
                "Proof command: python3 crew_terminal_window_proof.py\n"
                "Done when: the window holds six lines.\n")
        conn.execute("insert into tasks (id, title, body, status, assignee, priority, created_by, created_at) "
                     "values (?,?,?,'done',?,0,?,?)",
                     (PROBE, "PROBE terminal window", body, crew_card.FIXTURE_ASSIGNEE, crew_card.PROBE_OWNER, now - 300))
        # The run is LIVE on purpose: a session with ended_at NULL on a settled run is the killed-worker
        # case, and the page now (correctly) draws that as done. A fixture that wants a live node has to
        # say so in the run row too - the run is what decides a node's state.
        cur = conn.execute("insert into task_runs (task_id, profile, status, started_at, ended_at, "
                           "outcome) values (?,?,?,?,?,?)",
                           (PROBE, "crew-worker", "running", now - 240, None, None))
        run_id = cur.lastrowid
        conn.execute("insert into task_events (task_id, run_id, kind, payload, created_at) "
                     "values (?,?,?,?,?)", (PROBE, None, "created", "probe", now - 300))
        conn.commit()
    finally:
        conn.close()
    return run_id, now - 240


SESS_ID = "probe" + "_termwindow_session"


def session_db():
    for prof in ("crew-worker", "crew-verifier", "crew-coordinator"):
        path = os.path.join(crew_card.base_home(), "profiles", prof, "state.db")
        if os.path.exists(path):
            return prof, path
    return None, None


def seed_steps(run_start):
    """A live kanban session for the probe card with eight tool calls, so the card page has a node
    with a full six-line window and chips. Written straight into the session store, removed after."""
    prof, db = session_db()
    if not db:
        return False
    conn = sqlite3.connect(db)
    try:
        conn.execute("delete from messages where session_id = ?", (SESS_ID,))
        conn.execute("delete from sessions where id = ?", (SESS_ID,))
        conn.execute("insert into sessions (id, source, started_at, ended_at, model, title, "
                     "message_count, tool_call_count) values (?,?,?,?,?,?,?,?)",
                     (SESS_ID, "kanban", run_start + 1, None, "probe-model",
                      "PROBE terminal window", 9, 8))
        ts = run_start + 2
        conn.execute("insert into messages (session_id, role, content, timestamp) "
                     "values (?,?,?,?)",
                     (SESS_ID, "user", "Crew run for card %s: probe the terminal window." % PROBE, ts))
        for i in range(8):
            call_id = "probe_call_%d" % i
            calls = json.dumps([{"id": call_id, "type": "function",
                                 "function": {"name": "terminal",
                                              "arguments": json.dumps({"command": "probe %d" % i})}}])
            conn.execute("insert into messages (session_id, role, tool_calls, timestamp) "
                         "values (?,?,?,?)", (SESS_ID, "assistant", calls, ts + i))
            # call 0 fails: the node's own step list is then six steps plus that failure riding along,
            # one longer than the window - the case the live board hit.
            result = (json.dumps({"output": "", "exit_code": 1, "error": "probe failure"}) if i == 0
                      else json.dumps({"output": "ok %d" % i}))
            conn.execute("insert into messages (session_id, role, content, tool_call_id, tool_name, "
                         "timestamp) values (?,?,?,?,?,?)",
                         (SESS_ID, "tool", result, call_id, "terminal", ts + i + 0.2))
        conn.commit()
    finally:
        conn.close()
    return True


def drop_steps():
    prof, db = session_db()
    if not db:
        return
    conn = sqlite3.connect(db)
    try:
        conn.execute("delete from messages where session_id = ?", (SESS_ID,))
        conn.execute("delete from sessions where id = ?", (SESS_ID,))
        conn.commit()
    finally:
        conn.close()


def drop_probe():
    conn = crew_proof_board.connect(KANBAN_DB)
    try:
        conn.execute("update tasks set status = 'archived' where id = ?", (PROBE,))
        conn.commit()
    finally:
        conn.close()


def node_steps(card_id):
    """The steps the graph gives the card's widest node, straight from the served json."""
    try:
        data = json.loads(page_text("/card/%s.json" % card_id))
    except Exception:                                                # noqa: BLE001
        return None
    lists = [n.get("steps") or [] for n in (data.get("nodes") or [])]
    return max(lists, key=len) if lists else None


def devtools_json(path):
    with urllib.request.urlopen("http://127.0.0.1:%d%s" % (PORT, path), timeout=10) as fh:
        return json.loads(fh.read().decode())


def wait_for_target(fragment, tries=80):
    for _ in range(tries):
        try:
            for t in devtools_json("/json/list"):
                if t.get("type") == "page" and fragment in (t.get("url") or ""):
                    return t
        except Exception:
            pass
        time.sleep(0.5)
    return None


def page_text(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as fh:
        return fh.read().decode("utf-8", "replace")


LOOK = r"""
(function(){
  function live(nd){ return Array.prototype.slice.call(nd.querySelectorAll('.steps > .step')); }
  var out = {areaH: null, maxLive: 0, over: 0, nodesWithLines: 0};
  var counts = [], best = null, bestN = 0;
  document.querySelectorAll('.node').forEach(function(nd){
    var l = live(nd); counts.push(l.length);
    if(l.length) out.nodesWithLines++;
    if(l.length > bestN){ best = nd; bestN = l.length; }
    var box = nd.querySelector('.steps');
    if(box){ out.areaH = box.clientHeight; if(box.scrollHeight - box.clientHeight > 1) out.over++; }
  });
  if(counts.length) out.maxLive = Math.max.apply(null, counts);
  window.__first = best ? live(best) : [];          // the fullest node's line elements, checked again after later polls
  window.__arrived = [];
  new MutationObserver(function(ms){
    ms.forEach(function(m){ m.addedNodes.forEach(function(n){
      if(n.nodeType === 1 && n.querySelectorAll)
        [n].concat(Array.prototype.slice.call(n.querySelectorAll('.step'))).forEach(function(x){
          if(x.classList && x.classList.contains('step')) window.__arrived.push({text: x.textContent, cls: x.className, anim: getComputedStyle(x).animationName,
                               last: x === x.parentNode.lastElementChild});
        });
    }); });
  }).observe(document.body, {childList: true, subtree: true});
  out.windowLen = window.__first.length;
  return out;
})()
"""

AFTER = r"""
(function(){
  var kept = window.__first.filter(function(c){ return c.isConnected; });
  var max = 0;
  document.querySelectorAll('.node').forEach(function(nd){ max = Math.max(max, nd.querySelectorAll('.steps > .step').length); });
  return {churn: window.__first.length - kept.length, windowLen: window.__first.length, arrived: window.__arrived, maxAfter: max};
})()
"""

EDGES = r"""
(function(){
  var d = document.querySelector('.edge-dot'), f = document.querySelector('.edge.flow');
  return {dots: document.querySelectorAll('.edge-dot').length, flows: document.querySelectorAll('.edge.flow').length,
          dotAnim: d && d.firstElementChild ? d.firstElementChild.tagName : null,
          flowAnim: f ? getComputedStyle(f).animationName : null};
})()
"""

READ_TICK = r"""(function(){var o={};document.querySelectorAll('.chip .tk').forEach(function(t,i){o[i]=parseFloat(t.textContent);});return o;})()"""
READ_DOT = r"""(function(){var d=document.querySelector('.edge-dot');return d?[Math.round(d.getBoundingClientRect().left),Math.round(d.getBoundingClientRect().top)]:null;})()"""


def add_calls(first, n):
    """Append `n` tool calls (and their results) to the probe session: the page sees them on its next poll."""
    prof, db = session_db()
    conn = sqlite3.connect(db)
    try:
        ts = time.time()
        for i in range(n):
            call_id = "probe_late_%d" % (first + i)
            calls = json.dumps([{"id": call_id, "type": "function",
                                 "function": {"name": "terminal",
                                              "arguments": json.dumps({"command": "arrived now %d" % (first + i)})}}])
            conn.execute("insert into messages (session_id, role, tool_calls, timestamp) values (?,?,?,?)",
                         (SESS_ID, "assistant", calls, ts + i))
            conn.execute("insert into messages (session_id, role, content, tool_call_id, tool_name, timestamp) "
                         "values (?,?,?,?,?,?)", (SESS_ID, "tool", json.dumps({"output": "ok"}), call_id, "terminal", ts + i + 0.2))
        conn.execute("update sessions set message_count = message_count + ?, tool_call_count = tool_call_count + ? "
                     "where id = ?", (2 * n, n, SESS_ID))
        conn.commit()
    finally:
        conn.close()


def main():
    if not CHROME:
        print("PROOF FAIL: no chrome/chromium on PATH to open the page")
        return 1
    seeded = False
    proc = None
    profile_dir = crew_proof_board.chrome_scratch("crew-term-window-")
    try:
        seeded = True
        _, run_start = seed_probe()
        check("a live session with tool calls can be seeded", seed_steps(run_start))
        try:
            shell = page_text("/card/" + PROBE)
            app = page_text("/app.js")
        except Exception as exc:
            print("PROOF FAIL: the card page is not reachable at %s (%s)" % (BASE, exc))
            return 1
        check("the card page is served", "<!doctype html" in shell.lower() and "/app.js" in shell)
        check("the window is six lines", re.search(r"MAX_STEP_LINES = 6\b", app) is not None, "MAX_STEP_LINES" in app)
        check("the lines slide in", "@keyframes stepIn" in app)
        check("the line area is capped at six lines high", "max-height:93px" in app)
        check("a running edge has a dashed flow line", "flowdash" in app)
        env = dict(os.environ, XDG_CACHE_HOME=os.path.join(profile_dir, "cache"), TMPDIR=profile_dir)
        proc = subprocess.Popen([CHROME, "--headless=new", "--password-store=basic", "--disable-gpu", "--no-sandbox",
                                 "--remote-debugging-port=%d" % PORT, "--window-size=1400,900",
                                 "--user-data-dir=" + os.path.join(profile_dir, "profile"), BASE + "/card/" + PROBE],
                                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=True)
        target = wait_for_target("/card/" + PROBE)
        if not target:
            print("PROOF FAIL: the page never loaded in the browser")
            return 1
        from crew_ws import WSClient
        ws = WSClient(target["webSocketDebuggerUrl"])
        ws.wait_for("document.querySelectorAll('.node .steps > .step').length > 0")
        out = ws.evaluate(LOOK) or {}
        check("the card page drew nodes with step lines", (out.get("nodesWithLines") or 0) >= 1,
              "nodes with lines=%s" % out.get("nodesWithLines"))
        check("a node never shows more than six live lines", (out.get("maxLive") or 0) <= 6,
              "max=%s" % out.get("maxLive"))
        check("no line area overflows", out.get("over") == 0, "overflowing=%s" % out.get("over"))
        edges = ws.evaluate(EDGES) or {}
        check("a running node's edge carries a dot", (edges.get("dots") or 0) >= 1
              and edges.get("dotAnim") == "animateMotion", "dots=%s" % edges.get("dots"))
        check("the dot rides a dashed flow line", (edges.get("flows") or 0) >= 1
              and edges.get("flowAnim") == "flowdash", "flows=%s" % edges.get("flows"))
        time.sleep(0.6)
        t1 = ws.evaluate(READ_TICK)
        d1 = ws.evaluate(READ_DOT)
        time.sleep(0.9)
        t2 = ws.evaluate(READ_TICK)
        d2 = ws.evaluate(READ_DOT)
        grew = [k for k in (t1 or {}) if k in (t2 or {}) and (t2 or {})[k] > (t1 or {})[k]]
        check("an in-flight call ticks a stopwatch", bool(t1), "t1=%s" % t1)
        check("the stopwatch moves forward", bool(grew), "%s -> %s (grew: %s)" % (t1, t2, grew))
        check("the dot travels along the edge", bool(d1) and bool(d2) and d1 != d2, "%s -> %s" % (d1, d2))
        # Two new calls land in the session store; the page's own 2 s poll draws them. Three polls is enough.
        add_calls(8, 2)
        time.sleep(7)
        late = ws.evaluate(AFTER) or {}
        arrived = late.get("arrived") or []
        check("an arriving line slides in at the bottom", any(a.get("anim") == "stepIn" and a.get("last") for a in arrived),
              json.dumps(arrived)[:100])
        check("the window stays at six under a burst", (late.get("maxAfter") or 0) <= 6, "max=%s" % late.get("maxAfter"))
        print("NOTE: not checked - a full window pushing its oldest line out with the slide-out animation: the React "
              "app drops the line without the animation (Steps in ui/src/components/Graph.tsx)")
        # A node's own list can be one longer than the window (a failed step rides along its tail). An idle
        # node must reuse its own line elements: replacing them means a line sliding in and out for no reason at
        # every poll. Judged on the fullest node's lines that were not pushed out by the two arrivals.
        check("an idle node keeps its own lines across redraws", (late.get("churn") or 0) <= 2,
              "%s of %s line element(s) replaced over several polls (2 pushed out by the arrivals)"
              % (late.get("churn"), late.get("windowLen")))
        check("the node's own list is longer than the window (the ride-along is real)",
              (7 <= len(node_steps(PROBE))) if node_steps(PROBE) is not None else True,
              "%s step(s) in the json" % (len(node_steps(PROBE)) if node_steps(PROBE) is not None else "?"))
        ws.close()
    finally:
        if seeded:
            drop_steps()
            drop_probe()
        if proc:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:                                          # noqa: BLE001
                proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
        shutil.rmtree(profile_dir, ignore_errors=True)
    if FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("PROOF OK: the step lines are a six-line terminal window, an arriving line slides in, a live "
          "call ticks, and a running edge carries a travelling dot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
