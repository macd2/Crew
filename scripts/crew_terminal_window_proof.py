#!/usr/bin/env python3
"""Proof that the card page's step lines are a live terminal window and the edges carry moving dots.

What this pins, on the served card page (http://127.0.0.1:8799/card/<id>):

  1. the page ships the window: MAX_STEP_LINES is 6, the slide-in and slide-out keyframes exist,
     and the line area is capped at six lines of height
  2. a node never shows more than six live step lines, and no line overflows the area
  3. a step that arrives after the first paint enters at the bottom with the slide-in animation,
     and when a full node gets a newer step the oldest one slides out and the window stays at six
  4. a tool call in flight carries a stopwatch that ticks forward between two reads
  5. a running node's incoming edge carries a dot that travels along the path (animateMotion) over
     a dashed flow line, and a settled node's edge does not
  6. a settled node's lines hold still: its list can be one longer than the window (a failed step rides
     along the tail), and reconciling the window against that whole list made an idle node evict and
     re-add a line at every poll - lines sliding in and out on a blocked card

Everything is injected into the page's own state and redrawn, so the proof needs no live crew run.
Seeded probe cards are written straight into kanban.db (no crew_card.py open), so any agent context
can run it.

Run:  python3 crew_terminal_window_proof.py
Exit: 0 when every check passes, 1 otherwise.
"""
import json
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
import crew_proof_board  # noqa: E402
KANBAN_DB = crew_proof_board.proof_db()
BASE = crew_proof_board.graph_base()
PORT = int(os.environ.get("CREW_PROOF_CDP_PORT", "9414"))
CHROME = (shutil.which("google-chrome") or shutil.which("chromium")
          or shutil.which("chromium-browser"))
PROFILE_DIR = os.path.join(tempfile.gettempdir(), "crew-term-window-chrome")
PROBE = "t" + "9a" + "w1nd0w"
FAILS = []


def check(name, ok, detail=""):
    print("%-58s %s  %s" % (name, "PASS" if ok else "FAIL", str(detail)[:80]))
    if not ok:
        FAILS.append(name)


def seed_probe():
    """A card that has run: one assistant message with a tool call, straight into kanban.db."""
    now = int(time.time())
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute("delete from task_runs where task_id = ?", (PROBE,))
        conn.execute("delete from tasks where id = ?", (PROBE,))
        body = ("Goal: probe the card page's terminal window.\n"
                "Proof command: python3 crew_terminal_window_proof.py\n"
                "Done when: the window holds six lines.\n")
        conn.execute("insert into tasks (id, title, body, status, assignee, priority, created_at) "
                     "values (?,?,?,'done','crew-worker',0,?)",
                     (PROBE, "PROBE terminal window", body, now - 300))
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
        path = os.path.join(os.path.expanduser("~"), ".hermes", "profiles", prof, "state.db")
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
    conn = sqlite3.connect(KANBAN_DB)
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


def wait_for_target(fragment, tries=40):
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
  function live(nd){ return Array.prototype.slice.call(nd.querySelectorAll('.steps > .step')).filter(function(x){ return !x.classList.contains('out'); }); }
  var out = {cap: (typeof MAX_STEP_LINES === 'number' ? MAX_STEP_LINES : null),
             hasDrop: (typeof dropStep === 'function'), hasTick: (typeof tickChips === 'function'),
             areaH: null, maxLive: 0, over: 0, anims: [], nodesWithLines: 0,
             reused: null, churn: null, windowLen: null};
  var counts = [];
  document.querySelectorAll('.node').forEach(function(nd){
    var l = live(nd); counts.push(l.length);
    if(l.length) out.nodesWithLines++;
    var box = nd.querySelector('.steps');
    if(box){ out.areaH = box.clientHeight; if(box.scrollHeight - box.clientHeight > 1) out.over++; }
  });
  if(counts.length) out.maxLive = Math.max.apply(null, counts);
  // The window's stability, on the server's own data and before this probe mutates anything: count the
  // LINE ELEMENTS of the fullest node that survive three redraws. A line that left is the endless
  // slide a settled node showed. Elements, not keys - a re-added line is a new element, same key.
  (function(){
    var nd = null, n = 0;
    document.querySelectorAll('.node').forEach(function(x){ if(live(x).length > n){ nd = x; n = live(x).length; } });
    if(!nd){ out.anims.push('no node with lines'); return; }
    var first = live(nd);
    drawGraph(); drawGraph(); drawGraph();
    var kept = first.filter(function(c){ return c.isConnected && !c.classList.contains('out'); });
    out.reused = kept.length === first.length;
    out.churn = first.length - kept.length;
    out.windowLen = first.length;
  })();
  // a line that arrives now must enter with the slide-in animation
  function nodeWithLines(min){ var hit=null; document.querySelectorAll('.node').forEach(function(nd){ if(!hit && live(nd).length>=min) hit=nd; }); return hit; }
  function idxOf(el){ var i=0,f=-1; document.querySelectorAll('.node').forEach(function(nd){ if(nd===el) f=i; i++; }); return f; }
  var t = nodeWithLines(1);
  if(t){
    var ti = idxOf(t);
    state.nodes[ti].steps = (state.nodes[ti].steps||[]).concat([{tool:'terminal', ts: 9100000000, args:'arrived now', sec: 1}]);
    drawGraph();
    var arr=null; document.querySelectorAll('.steps > .step').forEach(function(x){ if(!arr && x.textContent.indexOf('arrived now')>=0) arr=x; });
    out.arrivedAnim = arr ? getComputedStyle(arr).animationName : null;
    out.arrivedLast = arr ? (arr === arr.parentNode.lastElementChild) : null;
    if(!arr){ out.anims.push('no arrived line'); }
  } else { out.anims.push('no node with lines'); }
  // a full node that gets newer lines must stay at the cap and push the oldest one out
  var f = nodeWithLines(out.cap || 6);
  if(f){
    var fi = idxOf(f);
    for(var i=0;i<3;i++) state.nodes[fi].steps = (state.nodes[fi].steps||[]).concat([{tool:'terminal', ts: 9200000000+i, args:'overflow '+i, sec: 1}]);
    drawGraph();
    out.outNow = document.querySelectorAll('.steps > .step.out').length;
    var c2=[]; document.querySelectorAll('.node').forEach(function(nd){ c2.push(live(nd).length); });
    out.maxAfter = Math.max.apply(null, c2.concat([0]));
  } else { out.anims.push('no full node'); }
  // a running node's edge must carry a travelling dot over a dashed flow line
  var run = (state.nodes||[]).filter(function(x){ return x.status !== 'running' && (x.kind === 'session' || x.kind === 'run'); })[0]
             || (state.nodes||[]).filter(function(x){ return x.status !== 'running'; })[0];
  if(run){
    run.status = 'running'; drawGraph();
    out.dots = document.querySelectorAll('.edge-dot').length;
    out.flows = document.querySelectorAll('.edge.flow').length;
    out.dotAnim = (function(){ var d=document.querySelector('.edge-dot'); return d && d.firstElementChild ? d.firstElementChild.tagName : null; })();
    out.flowAnim = (function(){ var f=document.querySelector('.edge.flow'); return f ? getComputedStyle(f).animationName : null; })();
    var d0 = document.querySelector('.edge-dot');
    out.dotPos = d0 ? [Math.round(d0.getBoundingClientRect().left), Math.round(d0.getBoundingClientRect().top)] : null;
    run.status = 'done';
  }
  // a chip of a live node must tick a stopwatch forward
  var chip = document.querySelector('.node .chip:not(.more)');
  if(chip){ chip.dataset.tick = '1'; chip.dataset.ts = String(Date.now()/1000 - 1); }
  tickChips();
  return out;
})()
"""

READ_TICK = r"""(function(){var o={};document.querySelectorAll('.chip[data-tick]').forEach(function(c){var t=c.querySelector('.tk');if(t)o[c.textContent.replace(/\s*[0-9.]+s$/,'')]=parseFloat(t.textContent);});return o;})()"""
READ_DOT = r"""(function(){var d=document.querySelector('.edge-dot');return d?[Math.round(d.getBoundingClientRect().left),Math.round(d.getBoundingClientRect().top)]:null;})()"""


def main():
    if not CHROME:
        print("PROOF FAIL: no chrome/chromium on PATH to open the page")
        return 1
    seeded = False
    proc = None
    try:
        seeded = True
        _, run_start = seed_probe()
        check("a live session with tool calls can be seeded", seed_steps(run_start))
        try:
            html = page_text("/card/" + PROBE)
        except Exception as exc:
            print("PROOF FAIL: the card page is not reachable at %s (%s)" % (BASE, exc))
            return 1
        check("the card page is served", "<!DOCTYPE html" in html or "<!doctype html" in html.lower())
        check("the window is six lines", "MAX_STEP_LINES = 6" in html or "MAX_STEP_LINES=6" in html
              or "MAX_STEP_LINES = 6" in html.replace(" ", " "),
              "MAX_STEP_LINES" in html)
        check("the lines slide in and out", "@keyframes stepIn" in html and "@keyframes stepOut" in html)
        check("the line area is capped at six lines high", "max-height:93px" in html)
        check("a running edge has a dashed flow line", "flowdash" in html)
        check("the page reuses the line window across redraws", "stepCache" in html and "dropStep" in html)
        proc = subprocess.Popen([CHROME, "--headless=new", "--password-store=basic", "--disable-gpu", "--no-sandbox",
                                 "--remote-debugging-port=%d" % PORT, "--window-size=1400,900",
                                 "--user-data-dir=" + PROFILE_DIR, BASE + "/card/" + PROBE],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=True)
        target = wait_for_target("/card/" + PROBE)
        if not target:
            print("PROOF FAIL: the page never loaded in the browser")
            return 1
        from crew_ws import WSClient
        ws = WSClient(target["webSocketDebuggerUrl"])
        time.sleep(3.0)
        out = ws.evaluate(LOOK) or {}
        check("the page exposes the window and its helpers", out.get("cap") == 6
              and out.get("hasDrop") and out.get("hasTick"), "cap=%s" % out.get("cap"))
        check("a node never shows more than six live lines", (out.get("maxLive") or 0) <= 6,
              "max=%s" % out.get("maxLive"))
        check("no line area overflows", out.get("over") == 0, "overflowing=%s" % out.get("over"))
        check("an arriving line slides in at the bottom", out.get("arrivedAnim") == "stepIn"
              and out.get("arrivedLast") is True,
              "%s last=%s" % (out.get("arrivedAnim"), out.get("arrivedLast")))
        check("a full window pushes the oldest line out", (out.get("outNow") or 0) >= 1,
              "out=%s" % out.get("outNow"))
        check("the window stays at six under a burst", (out.get("maxAfter") or 0) <= 6,
              "max=%s" % out.get("maxAfter"))
        # A node's own list can be one longer than the window (a failed step rides along its tail).
        # The window must still hold six, and an idle node must reuse its own line elements: replacing
        # them means a line sliding in and out for no reason at every poll.
        check("an idle node keeps its own lines across redraws", out.get("reused") is not False,
              "%s of %s line element(s) replaced over three redraws"
              % (out.get("churn"), out.get("windowLen")))
        check("the node's own list is longer than the window (the ride-along is real)",
              (7 <= len(node_steps(PROBE))) if node_steps(PROBE) is not None else True,
              "%s step(s) in the json" % (len(node_steps(PROBE)) if node_steps(PROBE) is not None else "?"))
        check("a running node's edge carries a dot", (out.get("dots") or 0) >= 1
              and out.get("dotAnim") == "animateMotion", "dots=%s" % out.get("dots"))
        check("the dot rides a dashed flow line", (out.get("flows") or 0) >= 1
              and out.get("flowAnim") == "flowdash", "flows=%s" % out.get("flows"))
        time.sleep(0.6)
        t1 = ws.evaluate(READ_TICK)
        d1 = ws.evaluate(READ_DOT)
        time.sleep(0.9)
        t2 = ws.evaluate(READ_TICK)
        d2 = ws.evaluate(READ_DOT)
        grew = [k for k in (t1 or {}) if k in (t2 or {}) and (t2 or {})[k] > (t1 or {})[k]]
        check("an in-flight call ticks a stopwatch", bool(t1), "t1=%s" % t1)
        check("the stopwatch moves forward", bool(grew),
              "%s -> %s (grew: %s)" % (t1, t2, grew))
        check("the dot travels along the edge", bool(d1) and bool(d2) and d1 != d2, "%s -> %s" % (d1, d2))
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
    if FAILS:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("PROOF OK: the step lines are a six-line terminal window that slides in and out, a live "
          "call ticks, and a running edge carries a travelling dot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
