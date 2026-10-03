#!/usr/bin/env python3
"""Proof: the card page's right sidebar (#panel) obeys the owner's rules, on a real card.

What it pins, each read back from the rendered page (never from the source). The DOM is the ui-spec
section 5 panel (docs/crew/ui-spec/spec.md): header, id chips, callout, KPIs, tabs, one scrolling body.
  1 the Transcript tab - newest entry on top: the served json's LAST line is the DOM's FIRST row
  2 a newly arrived line is animated once, and the 2 s poll never replays that animation
  3 model / session_id / kanban id are always shown as id chips; the chip is the copy button
  4 the chip's payload is verbatim "key: value" (read back from a stubbed clipboard, then the
    page's own copy function is put back)
  5 the Calls tab is ONE box scrolling inside the panel, the Failed/Latest filter sits ON TOP of it (Failed
    by default when the run failed calls), every row is folded by default (failed ones too) and the list
    reads newest-first, the same direction as the transcript
  phase 3: the pending-reason box stays fully visible with the panel open at 1600 px (docked, not
    overlaid), no text appears twice in the panel, and a run and its session open the same panel
  6 a redraw in place keeps the scroll offset AND an in-progress text selection - the 2 s poll must
    not steal a selection the reader is about to copy
  7 the panel draws no script error at all: the child rewrite threw "ReferenceError: shown is not
    defined" on every poll and stopped the panel half-drawn, which is why this check exists

It drives a live crew graph. To check the repo's own copy rather than an installed one, serve it on a
spare port first:
    CREW_GRAPH_PORT=8796 python3 scripts/crew_graph_serve.py &
    CREW_GRAPH_URL=http://127.0.0.1:8796 python3 scripts/crew_panel_steps_proof.py

Env: CREW_GRAPH_URL (or CREW_GRAPH_BASE) is the base URL for both the data read and the page;
CREW_GRAPH_CDP_PORT the DevTools port of the headless browser it starts.
Exit 0 = every check passed. Non-zero = it did not, and the failing check is printed.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URL = (os.environ.get("CREW_GRAPH_URL") or os.environ.get("CREW_GRAPH_BASE")
       or "http://127.0.0.1:8799").rstrip("/")
PORT = int(os.environ.get("CREW_GRAPH_CDP_PORT", "9347"))
CHROME = (shutil.which("google-chrome") or shutil.which("chromium")
          or shutil.which("chromium-browser"))
FAILURES = []
CHECKS = 0

# --- what the page says about itself (ui-spec section 5 DOM: .phead, .idc chips, .ptabs, .pbody > .plist) ---
JS = r"""
(function(){
  var p = document.getElementById('panel');
  if(!p || !p.classList.contains('open')) return JSON.stringify({panel:false});
  var q = function(s){ return p.querySelector(s); };
  var qa = function(s){ return [].slice.call(p.querySelectorAll(s)); };
  var txt = function(el){ return el ? (el.textContent||'') : ''; };
  var copies = {};
  qa('.ids .idc').forEach(function(b){
    copies[b.getAttribute('data-k')] = {value: b.getAttribute('data-v'), title: b.title || '', id: b.id || ''};
  });
  var msgs = qa('.plist.transcript > .msg');
  var body = q('.pbody'), cs = body ? getComputedStyle(body) : null;
  var why = document.getElementById('topWhy'), wr = why ? why.getBoundingClientRect() : null, pr = p.getBoundingClientRect();
  var seen = {}, twice = [];
  qa('.msg p, .callout .cb, .ps, .kvr dd, .pt').forEach(function(e){
    var k = (e.textContent||'').trim().slice(0,120); if(k.length < 40) return;
    if(seen[k]) twice.push(k.slice(0,60)); seen[k] = 1; });
  return JSON.stringify({
    panel: true,
    head: txt(q('.phead')),
    title: txt(q('.pt')), sub: txt(q('.ps')),
    tab: txt(q('.ptabs .on')),
    copyButtons: copies,
    sayTexts: msgs.map(function(d){ return txt(d.querySelector('p')).slice(0,80); }),
    sayNew: msgs.filter(function(d){ return d.classList.contains('new'); }).length,
    bodyOverflow: cs ? cs.overflowY : '', bodyH: body ? body.clientHeight : 0, panelH: p.clientHeight,
    sel: [].slice.call(document.querySelectorAll('#nodes .node.sel')).length,
    whyVisible: !!(wr && (wr.right <= pr.left || wr.bottom <= pr.top) && wr.width > 0),
    twice: twice,
    jserr: window.__jserr || []
  });
})()
"""

# --- the Calls tab: one bounded box, the filter on top, every row folded, newest first -----------------
CALLS_JS = r"""
(function(){
  var p = document.getElementById('panel');
  var tab = p.querySelector('.ptabs [data-tab="Calls"]'); if(tab) tab.click();
  var list = p.querySelector('.plist.calls'), body = p.querySelector('.pbody');
  var rows = list ? [].slice.call(list.querySelectorAll(':scope > .call')) : [];
  var filter = p.querySelector('.cbfilter'), first = rows[0] || null, on = p.querySelector('.cbfilter .on');
  var cs = body ? getComputedStyle(body) : null;
  return JSON.stringify({
    boxes: p.querySelectorAll('.plist.calls').length, rows: rows.length,
    tools: rows.map(function(r){ return (r.querySelector('.tn')||{}).textContent || ''; }),
    failedRows: rows.filter(function(r){ return r.classList.contains('failed'); }).length,
    openRows: rows.filter(function(r){ return r.classList.contains('open'); }).length,
    filter: filter ? filter.textContent : '', view: on ? on.getAttribute('data-view') : '',
    filterAbove: !!(filter && first && filter.getBoundingClientRect().top <= first.getBoundingClientRect().top),
    bodyOverflow: cs ? cs.overflowY : '', bodyH: body ? body.clientHeight : 0, panelH: p.clientHeight,
    hint: (p.querySelector('.calltools .hint')||{}).textContent || ''
  });
})()
"""
BACK_TO_TRANSCRIPT_JS = r"""
(function(){ var t = document.querySelector('#panel .ptabs [data-tab="Transcript"]'); if(t) t.click();
  return !!document.querySelector('#panel .plist.transcript'); })()
"""

# --- what the copy chip would actually put on the clipboard ---------------------------------------
COPY_JS = r"""
(function(){
  var out = {}, orig = window.copyText;
  window.copyText = function(text, done){ window.__payload = text; if(done) done(true); };
  [].slice.call(document.querySelectorAll('#panel .ids .idc')).forEach(function(b){
    window.__payload = null;
    b.click();
    out[b.getAttribute('data-k')] = window.__payload;
  });
  window.copyText = orig;
  return JSON.stringify(out);
})()
"""

# --- a line that just arrived: animated once, and not replayed by the next poll -------------------
ARRIVE_JS = r"""
(function(){
  var n = (typeof getSelectedNode === 'function') ? getSelectedNode() : null;
  if(!n) return JSON.stringify({err:'no selected node'});
  var u = unitOf(n), src = (u && (u.session || u.run)) || n;
  var ts = Math.floor(Date.now() / 1000) + 60;
  src.text = (src.text || []).concat([{ts: ts, text: 'PROOF arrival line'}]);
  updatePanel();
  var first = document.querySelector('#panel .plist.transcript > .msg');
  return JSON.stringify({once: !!(first && first.classList.contains('new')),
                         text: first ? first.textContent.slice(0, 60) : '',
                         newCount: document.querySelectorAll('#panel .plist.transcript > .msg.new').length});
})()
"""
REPLAY_JS = r"""
(function(){
  updatePanel();
  return JSON.stringify({newCount: document.querySelectorAll('#panel .plist.transcript > .msg.new').length});
})()
"""

# --- redraw in place: scroll offset and an in-progress selection must survive --------------------
KEEP_JS = r"""
(function(){
  var p = document.getElementById('panel'), body = p.querySelector('.pbody');
  var line = p.querySelector('.plist.transcript > .msg p');
  var node = line ? line.firstChild : null;
  while(node && node.nodeType !== 3) node = node.firstChild;
  if(node && node.textContent.length){
    var r = document.createRange();
    r.setStart(node, 0); r.setEnd(node, Math.min(8, node.textContent.length));
    var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
  }
  body.scrollTop = Math.min(120, Math.max(0, body.scrollHeight - body.clientHeight));
  var want = body.scrollTop;
  updatePanel();
  var sel = String(window.getSelection() || '');
  return JSON.stringify({want: want, got: body.scrollTop, sel: sel.length, selText: sel.slice(0, 20)});
})()
"""
KEEP_CALLS_JS = r"""
(function(){
  var p = document.getElementById('panel'), body = p.querySelector('.pbody');
  body.scrollTop = Math.min(60, Math.max(0, body.scrollHeight - body.clientHeight));
  var want = body.scrollTop;
  updatePanel();
  return JSON.stringify({want: want, got: body.scrollTop});
})()
"""
# --- the other half of the run/session unit opens the same panel ---------------------------------
PARTNER_JS = r"""
(function(){
  var n = getSelectedNode(), u = unitOf(n);
  var other = (u && u.run && u.session) ? (n.id === u.run.id ? u.session.id : u.run.id) : null;
  var before = (document.querySelector('#panel .pt')||{}).textContent || '';
  if(!other) return JSON.stringify({other: null, before: before});
  selectNode(other);
  var after = (document.querySelector('#panel .pt')||{}).textContent || '';
  var sel = document.querySelectorAll('#nodes .node.sel').length;
  selectNode(n.id);
  return JSON.stringify({other: other, before: before, after: after, sel: sel});
})()
"""


def check(name, ok, detail=""):
    global CHECKS
    CHECKS += 1
    print("%-58s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + str(detail)) if detail else ""))
    if not ok:
        FAILURES.append(name)
    return ok


def get(path):
    with urllib.request.urlopen(URL + path, timeout=20) as fh:
        return fh.read().decode("utf-8", "replace")


def groups_of(steps):
    """The json's own call groups, by the page's rule: same tool, same second (panelStepKey)."""
    out = []
    for s in steps or []:
        key = "%s@%s" % (s.get("tool") or "?", s.get("ts") or 0)
        if out and out[-1]["key"] == key:
            out[-1]["n"] += 1
        else:
            out.append({"key": key, "tool": s.get("tool"), "ts": s.get("ts"), "n": 1})
    return out


def pick_card_and_node():
    """A live card whose node has steps AND at least two text lines, so the order check can bite."""
    board = json.loads(get("/board.json"))
    ids = [t["id"] for lane in (board.get("lanes") or [])
           for t in (lane.get("tiles") or []) if t.get("id")]
    best, fallback = None, None
    for cid in ids:
        try:
            data = json.loads(get("/card/%s.json" % cid))
        except Exception:                                          # noqa: BLE001
            continue
        for node in data.get("nodes") or []:
            steps, text = node.get("steps") or [], node.get("text") or []
            if len(steps) < 3 or not node.get("id"):
                continue
            if len(text) >= 2 and best is None:
                best = (cid, node)
            if fallback is None:
                fallback = (cid, node)
    return best or fallback or (None, None)


def wait_for_target(fragment, tries=40):
    for _ in range(tries):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % PORT, timeout=10) as fh:
                targets = json.load(fh)
            for t in targets:
                if t.get("type") == "page" and fragment in (t.get("url") or ""):
                    return t
        except Exception:                                          # noqa: BLE001
            pass
        time.sleep(0.5)
    return None


def main():
    if not CHROME:
        print("PROOF FAIL: no chrome binary to render the page with")
        return 2
    try:
        if "ok" not in get("/healthz"):
            raise RuntimeError("/healthz did not say ok")
    except Exception as exc:                                       # noqa: BLE001
        print("PROOF FAIL: crew graph not reachable at %s (%s)" % (URL, exc))
        return 2
    card, node = pick_card_and_node()
    if not card or not node:
        print("PROOF FAIL: no live card carries a node with steps to check")
        return 2
    steps = node.get("steps") or []
    text = node.get("text") or []
    print("card %s, node %s (%s), %d step(s), %d text line(s) in the json"
          % (card, node.get("id"), node.get("label"), len(steps), len(text)))

    # T15, read from the served data itself: every run/session node says which card owns it, and no
    # session is drawn as running while its own run has already settled.
    data = json.loads(get("/card/%s.json" % card))
    nodes = data.get("nodes") or []
    owned = [n for n in nodes if n.get("kind") in ("run", "session", "subagent")]
    missing = [n.get("id") for n in owned if not n.get("card")]
    check("every run/session node says which card owns it",
          bool(owned) and not missing,
          "%d node(s), %d without a card %s" % (len(owned), len(missing), missing[:3]))
    runs = {n.get("run_id"): n for n in nodes if n.get("kind") == "run"}
    lying = [n.get("id") for n in nodes
             if n.get("kind") == "session" and n.get("status") == "running"
             and n.get("run_id") in runs and (runs[n.get("run_id")] or {}).get("status") != "running"]
    check("no session is drawn running while its own run has settled", not lying, str(lying[:3]))

    # The panel shows a run and its session as ONE unit: the transcript and the calls are the session's.
    src = node
    if node.get("kind") == "run":
        rid = (node.get("evidence") or {}).get("run_id")
        src = next((n for n in nodes if n.get("kind") == "session" and n.get("run_id") == rid), node)
    steps = src.get("steps") or []
    text = src.get("text") or []
    failed_n = (src.get("evidence") or {}).get("calls_failed")
    if failed_n is None:
        failed_n = len([s for s in steps if s.get("state") == "err"])

    profile = tempfile.mkdtemp(prefix="crew-panel-proof-")
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--password-store=basic", "--disable-gpu", "--no-sandbox",
         "--remote-debugging-port=%d" % PORT, "--user-data-dir=" + profile,
         "--window-size=1600,1000", "%s/card/%s#node=%s" % (URL, card, node["id"])],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        target = wait_for_target("/card/")
        if not target:
            print("PROOF FAIL: the page never loaded")
            return 2
        sys.path.insert(0, HERE)
        from crew_ws import WSClient
        ws = WSClient(target["webSocketDebuggerUrl"])
        try:
            ws.evaluate("window.__jserr=[];window.addEventListener('error',"
                        "function(e){window.__jserr.push(String(e.message));});1")
            for _ in range(40):
                if ws.evaluate("!!document.querySelector('#panel.open .phead .pt')"):
                    break
                time.sleep(0.5)
            ws.evaluate(BACK_TO_TRANSCRIPT_JS)

            # 7. no script error - on the first paint and on a redraw
            state = json.loads(ws.evaluate(JS) or "{}")
            if not check("the panel opens", state.get("panel")):
                return 1
            ws.evaluate("(function(){if(typeof drawAll==='function') drawAll();})()")
            time.sleep(0.4)
            errs = str(ws.evaluate("JSON.stringify(window.__jserr||[])"))
            check("the panel renders without a script error", errs in ("[]", "", "None"), errs[:140])
            if errs not in ("[]", "", "None"):
                return 1

            # phase 3 of the UI spec: docked, one template, nothing twice
            check("the pending-reason box is fully visible with the panel open (docked, 1600 px)",
                  state.get("whyVisible") is True, "whyVisible=%s" % state.get("whyVisible"))
            check("no text appears twice in the panel", not state.get("twice"), str(state.get("twice"))[:160])
            partner = json.loads(ws.evaluate(PARTNER_JS) or "{}")
            if partner.get("other"):
                check("the run node and its session node open the same panel",
                      partner.get("before") == partner.get("after") and (partner.get("sel") or 0) >= 2,
                      "%r vs %r, %s node(s) highlighted" % (partner.get("before"), partner.get("after"),
                                                           partner.get("sel")))
            else:
                check("the run node and its session node open the same panel", True,
                      "this node has no run/session partner (%s)" % node.get("id"))

            # 3+4. the three facts, and what their chips would copy
            copies = state.get("copyButtons") or {}
            want_keys = ["model", "session_id", "kanban id"]
            check("the panel shows model, session_id and kanban id",
                  all(k in copies for k in want_keys), "keys: %s" % list(copies.keys()))
            for key in want_keys:
                c = copies.get(key) or {}
                check("copy chip for %s names what it copies" % key,
                      "copy" in (c.get("title") or "").lower() and key in (c.get("title") or ""),
                      repr(c.get("title")))
            payloads = json.loads(ws.evaluate(COPY_JS) or "{}")
            for key in want_keys:
                want = "%s: %s" % (key, (copies.get(key) or {}).get("value", ""))
                check("the %s chip copies 'key: value' verbatim" % key,
                      payloads.get(key) == want,
                      "%r vs %r" % (payloads.get(key), want))

            # 1. Transcript: the json's LAST line is the DOM's FIRST row
            say = state.get("sayTexts") or []
            if text:
                newest = " ".join((text[-1].get("text") or "").split())[:30]
                check("the transcript shows the newest entry on top",
                      len(say) == len(text) and bool(newest) and newest.split("`")[0][:20] in " ".join(say[0].split()),
                      "dom[0]=%r newest=%r (%d row(s) vs %d)"
                      % ((say[0] if say else "")[:40], newest, len(say), len(text)))
            else:
                check("the transcript shows the newest entry on top", len(say) == 0,
                      "node carries no text (nothing to order)")

            # 2. arrival animation, once, never replayed by the poll
            arrive = json.loads(ws.evaluate(ARRIVE_JS) or "{}")
            check("a newly arrived line is animated once",
                  arrive.get("once") is True and arrive.get("newCount") == 1,
                  "first row carries .new: %s (count %s)"
                  % (arrive.get("once"), arrive.get("newCount")))
            time.sleep(0.6)                      # the class removes itself after 420 ms
            replay = json.loads(ws.evaluate(REPLAY_JS) or "{}")
            check("the next poll does not replay the animation",
                  replay.get("newCount") == 0, "new rows after a redraw: %s" % replay.get("newCount"))

            # 6. scroll + selection survive a redraw
            keep = json.loads(ws.evaluate(KEEP_JS) or "{}")
            check("a redraw keeps the scroll offset",
                  abs((keep.get("got") or 0) - (keep.get("want") or 0)) <= 2,
                  "want=%s got=%s" % (keep.get("want"), keep.get("got")))
            check("a redraw keeps an in-progress text selection",
                  (keep.get("sel") or 0) > 0 or not text, "selection=%r" % keep.get("selText"))

            # 5. the Calls tab: one bounded box, the filter on top, all folded, newest first
            calls = json.loads(ws.evaluate(CALLS_JS) or "{}")
            view = "failed" if failed_n > 0 else "latest"
            picked = [st for st in steps if st.get("state") == "err"] if view == "failed" else steps[-6:]
            want_groups = groups_of(picked)
            check("the calls list is ONE box", calls.get("boxes") == 1, "%s .plist.calls" % calls.get("boxes"))
            check("the default view is Failed when the run has failed calls, else Latest",
                  calls.get("view") == view, "view=%r failed=%s" % (calls.get("view"), failed_n))
            check("the box holds every call group of that view",
                  calls.get("rows") == len(want_groups),
                  "%s in the box vs %d in the json" % (calls.get("rows"), len(want_groups)))
            check("the filter sits ON TOP of the box",
                  calls.get("filterAbove") is True or not want_groups,
                  "%r above the first row: %s" % (calls.get("filter"), calls.get("filterAbove")))
            check("the filter labels the failed view", "failed" in (calls.get("filter") or "").lower(),
                  repr(calls.get("filter")))
            check("every call row is folded by default, failed ones too", (calls.get("openRows") or 0) == 0,
                  "open=%s of %s" % (calls.get("openRows"), calls.get("rows")))
            check("the calls box scrolls inside itself (bounded, own overflow)",
                  calls.get("bodyOverflow") == "auto" and 0 < (calls.get("bodyH") or 0) <= (calls.get("panelH") or 0),
                  "overflow-y=%s body=%s panel=%s" % (calls.get("bodyOverflow"), calls.get("bodyH"), calls.get("panelH")))
            check("the list states what it is", "calls" in (calls.get("hint") or ""), repr(calls.get("hint")))
            tools = [t for t in (calls.get("tools") or []) if t]
            if len(want_groups) >= 2:
                check("the calls list reads newest-first, like the transcript",
                      bool(tools) and tools[0].startswith(want_groups[-1]["tool"] or "")
                      and tools[-1].startswith(want_groups[0]["tool"] or ""),
                      "dom %s vs json %s" % (tools[:3], [g["tool"] for g in want_groups][-3:]))
            else:
                check("the calls list reads newest-first, like the transcript", True,
                      "fewer than two call groups in this view (nothing to order)")
            keepc = json.loads(ws.evaluate(KEEP_CALLS_JS) or "{}")
            check("a redraw keeps the reader's scroll inside the calls box",
                  abs((keepc.get("got") or 0) - (keepc.get("want") or 0)) <= 2,
                  "want=%s got=%s" % (keepc.get("want"), keepc.get("got")))

            # liveness comes from the node's own run, never from a stale session row
            lv = src.get("live") or {}
            if lv.get("state") == "pending":
                check("a live run names its tool in the header's sub-line",
                      bool(lv.get("tool")) and (lv.get("tool") or "") in (state.get("sub") or ""),
                      "sub=%r tool=%s" % (state.get("sub"), lv.get("tool")))
            else:
                check("a settled node carries its own last step",
                      bool(lv.get("tool")) or not steps,
                      "state=%s tool=%s" % (lv.get("state"), lv.get("tool")))
        finally:
            ws.close()
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:                                          # noqa: BLE001
            proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:                                          # noqa: BLE001
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)

    if FAILURES:
        print("PROOF FAIL: %d of %d check(s) failed: %s" % (len(FAILURES), CHECKS, "; ".join(FAILURES)))
        return 1
    print("PROOF OK (%d checks): docked panel, one template; model+session_id+kanban id chips copy "
          "'key: value'; the transcript is newest-first with a once-only arrival animation; the Calls tab "
          "is one bounded box with the filter on top, every row folded, newest-first; a redraw keeps "
          "scroll + selection; run and session open one panel; nothing appears twice" % CHECKS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
