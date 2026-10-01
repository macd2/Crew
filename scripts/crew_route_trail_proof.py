#!/usr/bin/env python3
"""Proof for phase 4 of the dashboard UI spec (docs/crew/ui-spec/spec.md section 8): the model chooser's trail
and the true call counts, in the card json and on the rendered panel.

Anchor, the spec's own: card t_d93e0c7b on the live board.
  1. /card/<id>.json carries a top-level `route`: 7 rows oldest first - 2 picks (the 09-30 01:07 `route` +
     `reroute` pair written for ONE decision is one row) and 5 quota walls - each with ts, kind, provider,
     model, why, wall_number
  2. the session of run 3190 carries `calls_failed` over EVERY call: 205 calls, 24 failed (the kept tail of
     27 steps would have said otherwise)
  3. rendered: the card node's Route tab lists those 7 rows, the 5 walls in the blocked tone
  4. rendered: run 3190's panel reads 205 tool calls and 24 failed, its Calls tab is labelled 205, and its
     Details tab has the Model pick row carrying the route's own `why`

Read-only: it serves the repo's own copy on a free port, reading the live board, and seeds nothing. An anchor
that is no longer on the board is reported as SKIP, never as a pass.
Exit 0 = every check passed. Non-zero = it did not, and the failing check is printed.
"""
import importlib.util
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CARD = "t_d93e0c7b"
RUN = 3190
WANT_ROWS, WANT_PICKS, WANT_WALLS = 7, 2, 5
WANT_CALLS, WANT_FAILED = 205, 24
CHROME = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
FAILURES = []
CHECKS = 0


def check(name, ok, detail=""):
    global CHECKS
    CHECKS += 1
    print("%-64s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + str(detail)) if detail else ""))
    if not ok:
        FAILURES.append(name)
    return ok


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def live_env():
    """The live board, read-only: no pin (a runner's proofs-board pin would hide the anchor)."""
    env = dict(os.environ)
    for k in ("KANBAN_DB", "HERMES_KANBAN_DB"):
        env.pop(k, None)
    return env


def graph_json():
    saved = {k: os.environ.pop(k) for k in ("KANBAN_DB", "HERMES_KANBAN_DB") if k in os.environ}
    try:
        spec = importlib.util.spec_from_file_location("cg_route_trail", os.path.join(HERE, "crew_graph.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.build_graph(CARD)
    finally:
        os.environ.update(saved)


def wait_http(url, tries=40):
    for _ in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=5) as fh:
                return fh.read().decode("utf-8", "replace")
        except Exception:                                          # noqa: BLE001
            time.sleep(0.25)
    return None


def wait_target(port, fragment, tries=40):
    for _ in range(tries):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=5) as fh:
                for t in json.load(fh):
                    if t.get("type") == "page" and fragment in (t.get("url") or ""):
                        return t
        except Exception:                                          # noqa: BLE001
            pass
        time.sleep(0.4)
    return None


PANEL_JS = r"""
(function(){
  var p = document.getElementById('panel');
  if(!p || !p.classList.contains('open')) return JSON.stringify({open:false});
  var t = function(s){ var e = p.querySelector(s); return e ? e.textContent : ''; };
  return JSON.stringify({open:true, title:t('.pt'), tab:t('.ptabs .on'), kpis:t('.pkpi'), tabs:t('.ptabs'),
    routeRows:p.querySelectorAll('.pdoc .route .rr').length,
    routeWalls:p.querySelectorAll('.pdoc .route .rr span.bad').length,
    pick:(function(){ var out=''; [].forEach.call(p.querySelectorAll('.pdoc .kvr'), function(r){
      if((r.querySelector('dt')||{}).textContent === 'Model pick') out = (r.querySelector('dd')||{}).textContent; }); return out; })(),
    err:window.__jserr || []});
})()
"""


def render(base, cdp, graph):
    profile = tempfile.mkdtemp(prefix="crew-route-trail-")
    url = "%s/card/%s#node=card:%s&tab=route" % (base, CARD, CARD)
    proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                             "--remote-debugging-port=%d" % cdp, "--user-data-dir=" + profile,
                             "--window-size=1600,1000", url],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        target = wait_target(cdp, "/card/")
        if not check("the card page loads in a browser", bool(target)):
            return
        sys.path.insert(0, HERE)
        from crew_ws import WSClient
        ws = WSClient(target["webSocketDebuggerUrl"])
        try:
            ws.evaluate("window.__jserr=[];window.addEventListener('error',function(e){window.__jserr.push(String(e.message));});1")
            state = {}
            for _ in range(40):
                state = json.loads(ws.evaluate(PANEL_JS) or "{}")
                if state.get("routeRows"):
                    break
                time.sleep(0.4)
            check("the card node's Route tab opens from the hash", state.get("tab", "").startswith("Route"),
                  "title=%r tab=%r" % (state.get("title"), state.get("tab")))
            check("the Route tab lists %d rows" % WANT_ROWS, state.get("routeRows") == WANT_ROWS,
                  "%s row(s)" % state.get("routeRows"))
            check("the %d quota walls are in the blocked tone" % WANT_WALLS, state.get("routeWalls") == WANT_WALLS,
                  "%s wall row(s)" % state.get("routeWalls"))
            ws.evaluate("selectNode('run:%d');1" % RUN)
            time.sleep(0.4)
            ws.evaluate("(function(){var t=document.querySelector('#panel .ptabs [data-tab=\"Details\"]'); if(t) t.click(); return 1;})()")
            time.sleep(0.4)
            state = json.loads(ws.evaluate(PANEL_JS) or "{}")
            kpis = state.get("kpis") or ""
            check("run %d's panel reads %d tool calls, %d failed" % (RUN, WANT_CALLS, WANT_FAILED),
                  ("%d" % WANT_CALLS) in kpis and ("%d failed" % WANT_FAILED) in kpis, repr(kpis))
            check("its Calls tab is labelled %d" % WANT_CALLS, ("Calls%d" % WANT_CALLS) in (state.get("tabs") or ""),
                  repr(state.get("tabs")))
            picks = [r for r in (graph.get("route") or []) if r.get("kind") != "quota_wall"]
            want_why = (picks[-1].get("why") or "")[:40] if picks else ""
            check("its Details tab carries the Model pick with the route's own why",
                  bool(want_why) and want_why in (state.get("pick") or ""),
                  "%r in %r" % (want_why, (state.get("pick") or "")[:90]))
            err = str(ws.evaluate("JSON.stringify(window.__jserr||[])"))
            check("no script error", err in ("[]", "", "None"), err[:140])
        finally:
            ws.close()
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:                                          # noqa: BLE001
            proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


def main():
    graph, err = graph_json()
    if err or not graph:
        print("SKIP: anchor %s is not on the live board any more (%s)" % (CARD, err))
        return 0
    route = graph.get("route")
    check("the card json carries a top-level route", isinstance(route, list), type(route).__name__)
    route = route or []
    picks = [r for r in route if r.get("kind") != "quota_wall"]
    walls = [r for r in route if r.get("kind") == "quota_wall"]
    check("route: %d rows = %d picks + %d quota walls" % (WANT_ROWS, WANT_PICKS, WANT_WALLS),
          (len(route), len(picks), len(walls)) == (WANT_ROWS, WANT_PICKS, WANT_WALLS),
          "%d rows, %d picks, %d walls" % (len(route), len(picks), len(walls)))
    check("route rows are oldest first", [r.get("ts") for r in route] == sorted(r.get("ts") for r in route))
    check("every route row has ts, kind, provider, model, why, wall_number",
          all(all(k in r for k in ("ts", "kind", "provider", "model", "why", "wall_number")) for r in route))
    check("the route + reroute pair of one decision is one row",
          sum(1 for r in route if r.get("kind") == "reroute") == 1 and not any(
              a.get("kind") == "route" and b.get("kind") == "reroute" and a.get("model") == b.get("model")
              and abs((a.get("ts") or 0) - (b.get("ts") or 0)) <= 5 for a, b in zip(route, route[1:])),
          [r.get("kind") for r in route])
    sess = next((n for n in graph.get("nodes") or [] if n.get("kind") == "session" and n.get("run_id") == RUN), None)
    ev = (sess or {}).get("evidence") or {}
    check("run %d's session: %d calls, %d failed over every call" % (RUN, WANT_CALLS, WANT_FAILED),
          (ev.get("tool_call_count"), ev.get("calls_failed")) == (WANT_CALLS, WANT_FAILED),
          "tool_call_count=%s calls_failed=%s (kept steps: %d)"
          % (ev.get("tool_call_count"), ev.get("calls_failed"), len((sess or {}).get("steps") or [])))
    roles = graph.get("roles") or []
    check("roster rows carry last_text and last_node", all("last_text" in r and "last_node" in r for r in roles),
          [r.get("name") for r in roles if "last_node" not in r])

    if not CHROME:
        check("a chrome binary to render the panel with", False)
    else:
        port, cdp = free_port(), free_port()
        env = dict(live_env(), CREW_GRAPH_PORT=str(port), CREW_GRAPH_BIND="127.0.0.1")
        srv = subprocess.Popen([sys.executable, os.path.join(HERE, "crew_graph_serve.py")], env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            base = "http://127.0.0.1:%d" % port
            if check("the repo's dashboard serves on a spare port", bool(wait_http(base + "/healthz"))):
                render(base, cdp, graph)
        finally:
            try:
                os.killpg(os.getpgid(srv.pid), signal.SIGTERM)
            except Exception:                                      # noqa: BLE001
                srv.terminate()

    if FAILURES:
        print("PROOF FAIL: %d of %d check(s) failed: %s" % (len(FAILURES), CHECKS, "; ".join(FAILURES)))
        return 1
    print("PROOF OK (%d checks): %s's route trail is %d rows (%d picks, %d walls) in the json and on the Route tab; "
          "run %d reads %d calls, %d failed, with its Model pick" % (CHECKS, CARD, WANT_ROWS, WANT_PICKS, WANT_WALLS,
                                                                      RUN, WANT_CALLS, WANT_FAILED))
    return 0


if __name__ == "__main__":
    sys.exit(main())
