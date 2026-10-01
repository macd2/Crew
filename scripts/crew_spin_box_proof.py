#!/usr/bin/env python3
"""Proof that the card page puts the "spinning" note in its own box with a working copy button.

Done when a card that keeps stopping on the same reason shows that note in a dedicated box instead
of as a loose line in the chip strip, the box carries the full reason text rather than the
170-character truncation the json keeps, one click copies it, and a card with no such note hides the
box.

Contract pinned here (drives the live page in headless Chrome over the DevTools protocol):
  /card/<id>   with situation.repeat set:
                 #spinbox      inside #main, after #sit, before #row (after #sitbox when that box
                               exists). Hidden when repeat is empty.
                 #spinboxHead  the counts: "<stops> of <runs> runs stopped"
                 #spinboxText  the repeated reason, full text, untruncated, wrapped
                 #spinCopy     a button, labelled "copy", that copies #spinboxText's text and then
                               says "copied"
               and the chip strip #sit carries no "spinning:" line any more.
  clipboard    read back over CDP after the click; when the browser refuses the clipboard read the
               check reports that and only the button's own confirmation is required.

Exit 0 = every check passed. Non-zero = it did not, and the failing check is printed.
"""
import importlib.util
import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_proof_board  # noqa: E402
import crew_card  # noqa: E402 - the owner profile and the base home
URL = crew_proof_board.graph_base()
KANBAN_DB = crew_proof_board.proof_db()
PORT = 9338
CHROME = (shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser"))
FAILURES = []
MIN_SHARE = 0.95
STOPS = 8
REASON = (
    "Needs you: 3 failed verifications on this card. no proof command on the card\n"
    "The verifier ran the card's proof three times and each run returned the same failure, so the "
    "card is now parked: raise the ceiling, add the missing proof command, or split the card.\n"
    "Nothing else is left to try - the writer stopped for the same reason on every attempt."
)


def check(name, ok, detail=""):
    print("%-58s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + detail) if detail else ""))
    if not ok:
        FAILURES.append(name)
    return ok


def http_json(path):
    with urllib.request.urlopen(URL + path, timeout=15) as fh:
        return json.loads(fh.read().decode())


def devtools_json(path):
    with urllib.request.urlopen("http://127.0.0.1:%d%s" % (PORT, path), timeout=10) as fh:
        return json.loads(fh.read().decode())


def seed_probe(suffix, stops, reason=None):
    """A card that stopped on the same reason `stops` times, seeded straight into the board database.

    No CLI: an agent context (worker, verifier) must be able to run this proof too, so it cannot
    depend on `crew_card.py open` succeeding there. A run row per attempt, because the page builds
    its graph from runs.
    """
    card = "t_" + uuid.uuid4().hex[:8]
    now = int(time.time())
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute(
            # block_kind matters: the kernel re-classifies a blocked card with no kind and the
            # dispatcher then spawns a real worker on this probe
            "insert into tasks (id, title, body, assignee, status, priority, created_by, created_at, "
            "workspace_kind, block_kind) values (?, ?, ?, 'crew-worker', 'blocked', 0, 'probe', ?, "
            "'scratch', 'needs_input')",
            (card, "PROBE spinbox %s" % suffix,
             "Coordinator: %s/\nGoal: probe card, the spin box proof seeds it\n"
             "Role: worker\nProof-cmd: true\n" % (os.environ.get("CREW_ROLE") or crew_card.owner_profile()),
             now))
        for i in range(max(1, stops)):
            conn.execute(
                "insert into task_runs (task_id, profile, status, started_at, ended_at, outcome, "
                "summary, last_heartbeat_at) values (?, 'crew-worker', ?, ?, ?, ?, ?, ?)",
                (card, "done" if not reason else "blocked", now - 900 + i * 60, now - 870 + i * 60,
                 "completed" if not reason else "blocked", reason, now - 870 + i * 60))
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        print("note: seeding %s failed: %s" % (card, str(exc)[:90]))
        return None
    finally:
        conn.close()
    return card


def drop_probe(card):
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute("update tasks set status = 'archived' where id = ?", (card,))
        conn.commit()
    finally:
        conn.close()


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


JS = r"""
(function(){
  var box = document.getElementById('spinbox'),
      sit = document.getElementById('sit'),
      sitbox = document.getElementById('sitbox'),
      row = document.getElementById('row'),
      text = document.getElementById('spinboxText'),
      head = document.getElementById('spinboxHead'),
      btn = document.getElementById('spinCopy');
  function vis(el){ return !!el && el.offsetParent !== null && getComputedStyle(el).display !== 'none'; }
  var ws = '', wrapOk = null;
  if (text) { var cs = getComputedStyle(text); ws = cs.whiteSpace || '';
              wrapOk = text.scrollWidth <= text.clientWidth + 2; }
  return {
    box: !!box, visible: vis(box),
    inMain: !!document.querySelector('#main #spinbox'),
    afterSit: !!(box && sit && (sit.compareDocumentPosition(box) & Node.DOCUMENT_POSITION_FOLLOWING)),
    afterSitbox: sitbox ? !!((sitbox.compareDocumentPosition(box) & Node.DOCUMENT_POSITION_FOLLOWING)) : null,
    beforeRow: !!(box && row && (box.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING)),
    headText: head ? head.innerText : '',
    textText: text ? text.innerText : '',
    sitText: sit ? sit.innerText : '',
    button: !!btn, buttonTag: btn ? btn.tagName : '', label: btn ? btn.innerText : '',
    whiteSpace: ws, wrapOk: wrapOk
  };
})()
"""


def inspect(ws, card):
    ws.call(1, "Page.navigate", {"url": "%s/card/%s" % (URL, card)})
    for _ in range(40):
        try:
            if ws.evaluate("!!document.getElementById('sit')"):
                break
        except Exception:
            pass
        time.sleep(0.5)
    return ws.evaluate(JS) or {}


def check_spin(ws, card):
    data = http_json("/card/%s.json" % card)
    sit = (data.get("situation") or {})
    repeat = str(sit.get("repeat") or "")
    reason = str(sit.get("reason") or "") or str(sit.get("why") or "")
    check("%s reports the repeated stop" % card, bool(repeat), repeat[:70] or "situation.repeat empty")
    if not repeat:
        return
    state = inspect(ws, card)
    check("the spin box exists inside #main", state.get("inMain"))
    check("the spin box sits after the chip strip", bool(state.get("afterSit")))
    check("the spin box sits after the reason box", state.get("afterSitbox") in (None, True))
    check("the spin box sits before the rail and stage", bool(state.get("beforeRow")))
    check("the spin box is visible on a card that keeps stopping", bool(state.get("visible")))
    head = str(state.get("headText") or "")
    counts = re.match(r"\s*(\d+)\s+of\s+(\d+)", head)
    check("the box head carries the run counts",
          bool(counts) and counts.group(1) == str(STOPS) and counts.group(2) == str(STOPS),
          head[:60])
    shown = " ".join(str(state.get("textText") or "").split())
    want = " ".join(reason.split())
    share = (len(shown) / len(want)) if want else 0
    check("the box shows the full reason, not the 170 character cut", share >= MIN_SHARE,
          "%d of %d characters (%.0f%%)" % (len(shown), len(want), share * 100))
    check("the chip strip carries no spinning line",
          "spinning" not in str(state.get("sitText") or "").lower())
    check("the box wraps instead of running off the side",
          "pre" in str(state.get("whiteSpace") or "") and state.get("wrapOk") is True,
          "white-space=%s wrap=%s" % (state.get("whiteSpace"), state.get("wrapOk")))
    check("a copy button is there", state.get("button") and
          state.get("buttonTag") in ("BUTTON", "A"))
    check("the button is labelled copy", "copy" in str(state.get("label") or "").lower(),
          str(state.get("label"))[:40])

    if not state.get("button"):
        check("the copy button can be clicked", False, "no #spinCopy on the page yet")
        return
    granted = False
    try:
        ws.call(9, "Browser.grantPermissions",
                {"origin": URL, "permissions": ["clipboardReadWrite", "clipboardSanitizedWrite"]})
        granted = True
    except Exception:
        granted = False
    ws.evaluate("document.getElementById('spinCopy').click()")
    time.sleep(1.0)
    after = ws.evaluate(JS) or {}
    check("the button confirms the copy", "copied" in str(after.get("label") or "").lower()
          or "copied" in str(after.get("headText") or "").lower(),
          str(after.get("label"))[:40])
    if granted:
        try:
            clip = ws.evaluate("navigator.clipboard.readText()")
        except Exception as exc:  # noqa: BLE001
            clip = None
            print("note: the browser refused the clipboard read (%s)" % str(exc)[:60])
        if clip:
            check("the clipboard holds exactly the box text",
                  " ".join(str(clip).split()) == " ".join(str(after.get("textText") or "").split()),
                  "%d characters" % len(str(clip)))
        else:
            print("note: clipboard empty or unreadable in headless chrome; button confirmation only")


def check_quiet(ws, card):
    data = http_json("/card/%s.json" % card)
    sit = (data.get("situation") or {})
    if str(sit.get("repeat") or ""):
        check("the quiet card reports no repeated stop", False, sit.get("repeat")[:60])
        return
    state = inspect(ws, card)
    check("the spin box hides on a card without the note", not state.get("visible"),
          "present=%s visible=%s" % (state.get("box"), state.get("visible")))


def main():
    if not CHROME:
        print("PROOF FAIL: no chrome binary to render the page with")
        return 2
    try:
        with urllib.request.urlopen(URL + "/healthz", timeout=15) as fh:
            probe = fh.read().decode("utf-8", "replace")
        if "ok" not in probe:
            raise RuntimeError("/healthz said %r" % probe[:60])
    except Exception as exc:  # noqa: BLE001
        print("PROOF FAIL: crew graph not reachable at %s (%s)" % (URL, exc))
        return 2

    stamp = str(int(time.time()))
    spinning = seed_probe("spinning %s" % stamp, STOPS, REASON)
    quiet = seed_probe("quiet %s" % stamp, 1)
    if not spinning or not quiet:
        print("PROOF FAIL: could not seed the probe cards")
        return 2

    profile = tempfile.mkdtemp(prefix="crew-spinbox-")
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--remote-debugging-port=%d" % PORT,
         "--user-data-dir=" + profile, "--window-size=1400,900", "%s/card/%s" % (URL, spinning)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    try:
        target = wait_for_target("/card/")
        if not target:
            print("PROOF FAIL: the page never loaded")
            return 2
        sys.path.insert(0, HERE)
        from crew_ws import WSClient
        ws = WSClient(target["webSocketDebuggerUrl"])
        try:
            check_spin(ws, spinning)
            check_quiet(ws, quiet)
        finally:
            ws.close()
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:                                          # noqa: BLE001
            proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)
        for card in (spinning, quiet):
            drop_probe(card)

    if FAILURES:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILURES), "; ".join(FAILURES)))
        return 1
    print("PROOF OK: the spinning note renders in its own box with the full reason, one click copies "
          "it, and the box hides when there is no note")
    return 0


if __name__ == "__main__":
    sys.exit(main())
