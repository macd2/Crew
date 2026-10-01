"""Drive the crew page in a real browser and check the panel opens on a node click
and closes on a canvas click. Run with the crew graph service up.

    python3 scripts/crew_panel_click_check.py --card t_611c7f18

Uses Chrome headless over the DevTools protocol. No page code is stubbed: the same
handlers the owner clicks are exercised.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

CHROME = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
PORT = 9333


def http_json(path):
    with urllib.request.urlopen("http://127.0.0.1:%d%s" % (PORT, path), timeout=10) as fh:
        return json.loads(fh.read().decode())


def wait_for_target(url_fragment, tries=40):
    for _ in range(tries):
        try:
            for t in http_json("/json/list"):
                if t.get("type") == "page" and url_fragment in (t.get("url") or ""):
                    return t
        except Exception:
            pass
        time.sleep(0.5)
    return None


def evaluate(ws_url, expression):
    """One CDP call over our own stdlib websocket client: no third-party module needed."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from crew_ws import WSClient
    ws = WSClient(ws_url)
    try:
        return ws.evaluate(expression)
    finally:
        ws.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", required=True)
    ap.add_argument("--host", default="127.0.0.1:8799")
    args = ap.parse_args()

    if not CHROME:
        print("no chrome binary found"); return 2

    url = "http://%s/card/%s" % (args.host, args.card)
    profile = tempfile.mkdtemp(prefix="crew-click-")
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--remote-debugging-port=%d" % PORT, "--user-data-dir=" + profile,
         "--window-size=1400,760", url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    checks = []
    try:
        target = wait_for_target("/card/")
        if not target:
            print("page never loaded"); return 2
        ws_url = target["webSocketDebuggerUrl"]

        # wait until the page has drawn the graph
        for _ in range(40):
            n = evaluate(ws_url, "document.querySelectorAll('#nodes .node').length")
            if n:
                break
            time.sleep(0.5)
        checks.append(("graph drawn (%s nodes)" % n, bool(n)))

        open_before = evaluate(ws_url, "document.getElementById('panel').classList.contains('open')")
        checks.append(("panel starts closed", open_before is False))

        clicked = evaluate(ws_url, """
          (function(){
            var n = document.querySelector('#nodes .node .card');
            if(!n) return 'no-node';
            n.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true}));
            return document.getElementById('panel').classList.contains('open');
          })()
        """)
        checks.append(("node click opens the panel", clicked is True))

        canvas = evaluate(ws_url, """
          (function(){
            var st = document.getElementById('stage');
            st.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true}));
            return document.getElementById('panel').classList.contains('open');
          })()
        """)
        checks.append(("canvas click closes it", canvas is False))

        reopened = evaluate(ws_url, """
          (function(){
            document.querySelector('#nodes .node .card').dispatchEvent(new MouseEvent('click',{bubbles:true}));
            var a = document.getElementById('panel').classList.contains('open');
            document.body.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true}));
            return a + '|' + document.getElementById('panel').classList.contains('open');
          })()
        """)
        checks.append(("esc closes it too", reopened == "true|false"))

        after = evaluate(ws_url, """
          (function(){
            document.querySelector('#nodes .node .card').dispatchEvent(new MouseEvent('click',{bubbles:true}));
            var st = document.getElementById('stage');
            st.dispatchEvent(new MouseEvent('mousedown', {bubbles:true, button:0}));
            st.dispatchEvent(new MouseEvent('mouseup', {bubbles:true, button:0}));
            st.dispatchEvent(new MouseEvent('click', {bubbles:true}));
            return document.getElementById('panel').classList.contains('open');
          })()
        """)
        checks.append(("a click after a drag still closes it", after is False))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print("%-42s %s" % (name, "PASS" if ok else "FAIL"))
    print("%d checks, %d passed, %d failed" % (len(checks), len(checks) - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
