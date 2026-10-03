#!/usr/bin/env python3
"""Proof that the card page carries a dedicated, always well-formatted box for the pending reason.

Done when the card page shows the reason a card is waiting on in its own box with a fixed layout -
never as loose text folded into the chip strip at the top - and hides that box when there is no
reason to show.

Contract pinned here (drives the live page in headless Chrome over the DevTools protocol):
  /card/<id>.json  situation gains
                     reason        the full pending-reason text, untruncated
                     reason_source where it came from: "run <id>", "task" or "comment"
                     reason_age_s  whole seconds since it was recorded, or null
                     reason_actor  who has to act: "you" or "nobody"
                   `why` stays as it is for existing readers.
  /card/<id>       the top of the page is two parts:
                     #sit      the chip strip only - status, headline, counts, units (the tokens
                              live in the rail). No
                               sentence-length reason text in it.
                     #sitbox   the reason box, between #sit and #row:
                                 #sitboxHead  label ("needs you") + the status badge
                                 #sitboxWhy   the reason, wrapped, full text
                                 #sitboxMeta  source and age
                   With nothing pending (reason empty) #sitbox is hidden - no empty box.

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
PORT = 9336
CHROME = (shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser"))
FAILURES = []
MIN_SHARE = 0.95          # of the JSON reason length that must be visible in the box


def check(name, ok, detail=""):
    print("%-58s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + detail) if detail else ""))
    if not ok:
        FAILURES.append(name)
    return ok


def crew_module():
    spec = importlib.util.spec_from_file_location("cg", os.path.join(HERE, "crew_graph.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def http_json(path):
    with urllib.request.urlopen(URL + path, timeout=15) as fh:
        return json.loads(fh.read().decode())


def seed_probe(suffix, status, reason=None):
    """A probe card in the state under test, seeded straight into the board database.

    No CLI: an agent context (worker, verifier) must be able to run this proof too, so it cannot
    depend on `crew_card.py open` succeeding in that context. The card needs a run row - the page
    builds its graph from runs and a card that never ran has no page.
    """
    card = "t_" + uuid.uuid4().hex[:8]
    now = int(time.time())
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute(
            "insert into tasks (id, title, body, assignee, status, priority, created_by, created_at, "
            "workspace_kind, block_kind) values (?, ?, ?, 'crew-worker', ?, 0, 'probe', ?, 'scratch', ?)",
            (card, "PROBE sitbox %s" % suffix,
             "Coordinator: %s/\nGoal: probe card, the reason box proof seeds it\n"
             "Role: worker\nProof-cmd: true\n" % (os.environ.get("CREW_ROLE") or crew_card.owner_profile()),
             status, now, "needs_input" if status == "blocked" else None))
        conn.execute("insert into task_runs (task_id, profile, status, started_at, ended_at, outcome, "
                     "summary, last_heartbeat_at) values (?, 'crew-worker', ?, ?, ?, ?, ?, ?)",
                     (card, "done" if status == "done" else "blocked", now - 900, now - 600,
                      "completed" if status == "done" else "blocked", reason, now - 600))
        if reason:
            conn.execute("insert into task_comments (task_id, author, body, created_at) "
                         "values (?, 'probe', ?, ?)", (card, reason, now - 900))
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


JS = r"""
(function(){
  var box = document.getElementById('sitbox'),
      sit = document.getElementById('sit'),
      row = document.getElementById('row'),
      why = document.getElementById('sitboxWhy'),
      head = document.getElementById('sitboxHead'),
      meta = document.getElementById('sitboxMeta');
  function vis(el){ return !!el && el.offsetParent !== null && getComputedStyle(el).display !== 'none'; }
  var ws = '', wrapOk = null, height = null;
  if (why) {
    var cs = getComputedStyle(why);
    ws = cs.whiteSpace || '';
    wrapOk = why.scrollWidth <= why.clientWidth + 2;
    height = why.clientHeight;
  }
  return {
    box: !!box, visible: vis(box),
    inMain: !!document.querySelector('#main #sitbox'),
    afterSit: !!(box && sit && (sit.compareDocumentPosition(box) & Node.DOCUMENT_POSITION_FOLLOWING)),
    beforeRow: !!(box && row && (box.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING)),
    whyText: why ? why.innerText : '',
    headText: head ? head.innerText : '',
    metaText: meta ? meta.innerText : '',
    sitText: sit ? sit.innerText : '',
    whiteSpace: ws, wrapOk: wrapOk, whyHeight: height,
    boxBorder: box ? getComputedStyle(box).borderTopWidth : '',
    cardId: (document.body && document.body.dataset ? document.body.dataset.card : '') || '',
    copy: !!document.getElementById('sitCopy'),
    copyTag: document.getElementById('sitCopy') ? document.getElementById('sitCopy').tagName : '',
    copyLabel: document.getElementById('sitCopy') ? document.getElementById('sitCopy').innerText : '',
    copyInHead: !!(head && head.querySelector('#sitCopy')),
    boxScrolls: box ? (box.scrollHeight > box.clientHeight + 2) : null
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


def check_pending(ws, card):
    data = http_json("/card/%s.json" % card)
    sit = (data.get("situation") or {})
    reason = str(sit.get("reason") or "")
    check("%s publishes its pending reason" % card, bool(reason),
          "situation.reason is empty, falling back to situation.why")
    if not reason:
        reason = str(sit.get("why") or "")
    if not reason:
        check("there is a reason to render at all", False, "nothing in situation.reason or .why")
        return
    state = inspect(ws, card)
    check("the box exists inside #main", state.get("inMain"))
    check("the box sits after the chip strip", bool(state.get("afterSit")))
    check("the box sits before the rail and stage", bool(state.get("beforeRow")))
    check("the box is visible on a card that is waiting", bool(state.get("visible")))
    check("the box is bordered", state.get("boxBorder") not in ("", "0px"), str(state.get("boxBorder")))
    head = str(state.get("headText") or "")
    check("the box head names the state", "needs you" in head.lower() or "you" in head.lower(),
          head[:60])
    shown = " ".join(str(state.get("whyText") or "").split())
    want = " ".join(reason.split())
    share = (len(shown) / len(want)) if want else 0
    check("the reason is shown in full, untruncated", share >= MIN_SHARE,
          "%d of %d characters (%.0f%%)" % (len(shown), len(want), share * 100))
    first = want[:40]
    check("no sentence-length reason in the chip strip", first not in str(state.get("sitText") or ""))
    check("a copy button sits in the reason box head",
          state.get("copy") and state.get("copyTag") in ("BUTTON", "A") and state.get("copyInHead"),
          "%s in head=%s" % (state.get("copyTag"), state.get("copyInHead")))
    check("the copy button is labelled copy",
          "copy" in str(state.get("copyLabel") or "").lower(), str(state.get("copyLabel"))[:30])
    check("the page carries the card's own id for the copy",
          state.get("cardId") == card, "data-card=%s" % state.get("cardId"))
    if state.get("copy"):
        granted = False
        try:
            ws.call(9, "Browser.grantPermissions",
                    {"origin": URL, "permissions": ["clipboardReadWrite", "clipboardSanitizedWrite"]})
            granted = True
        except Exception:                                          # noqa: BLE001
            granted = False
        ws.evaluate("document.getElementById('sitCopy').click()")
        time.sleep(1.0)
        after_copy = ws.evaluate(JS) or {}
        check("the copy button confirms the copy",
              "copied" in str(after_copy.get("copyLabel") or "").lower(),
              str(after_copy.get("copyLabel"))[:30])
        if granted:
            try:
                clip = " ".join(str(ws.evaluate("navigator.clipboard.readText()") or "").split())
                wants = " ".join(str(want).split())
                check("the copy starts with the card's identifier", clip.startswith(card),
                      clip[:40])
                check("and carries the whole reason after it", wants and wants in clip,
                      "%d of %d characters copied" % (len(clip), len(wants)))
            except Exception as exc:                               # noqa: BLE001
                check("the copy starts with the card's identifier", False,
                      "clipboard read failed: %s" % exc)
    check("the reason wraps instead of running off the side",
          "pre" in str(state.get("whiteSpace") or "") and state.get("wrapOk") is True,
          "white-space=%s wrap=%s" % (state.get("whiteSpace"), state.get("wrapOk")))
    check("the reason is more than one line or scrolls inside the box",
          (state.get("whyHeight") or 0) > 12 or state.get("boxScrolls") is True,
          "height=%s" % state.get("whyHeight"))
    meta = str(state.get("metaText") or "")
    check("the box meta names the source", any(w in meta.lower() for w in ("run", "task", "comment")),
          meta[:60])
    check("the box meta carries an age", any(ch.isdigit() for ch in meta), meta[:60])


def check_quiet(ws, card, status):
    data = http_json("/card/%s.json" % card)
    sit = (data.get("situation") or {})
    if str(sit.get("reason") or ""):
        check("%s has nothing pending, so the box hides" % card, False,
              "reason is set on a %s card" % status)
        return
    state = inspect(ws, card)
    check("the box hides on a %s card with no reason" % status, not state.get("visible"),
          "present=%s visible=%s" % (state.get("box"), state.get("visible")))


PENDING_REASON = (
    "Needs you: the proof command cannot run.\n"
    "(1) crew_tokens_section_proof.py parses the percentage as an integer, so 17.9% reads as 17 and "
    "the check can never pass. The fix is a float parse on that one row.\n"
    "(2) The service restart needs a human: the unattended approval gate refused "
    "`systemctl --user restart crew-graph-http.service`.\n"
    "(3) Everything else is deployed and pushed (688f473) and the remaining checks pass."
)


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
    pending = seed_probe("waiting %s" % stamp, "blocked", PENDING_REASON)
    quiet = seed_probe("quiet %s" % stamp, "done")
    if not pending or not quiet:
        print("PROOF FAIL: could not seed the probe cards")
        return 2

    profile = tempfile.mkdtemp(prefix="crew-sitbox-")
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--password-store=basic", "--disable-gpu", "--no-sandbox", "--remote-debugging-port=%d" % PORT,
         "--user-data-dir=" + profile, "--window-size=1400,900", "%s/card/%s" % (URL, pending)],
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
            check_pending(ws, pending)
            check_quiet(ws, quiet, "done")
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
        for card in (pending, quiet):
            drop_probe(card)

    if FAILURES:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILURES), "; ".join(FAILURES)))
        return 1
    print("PROOF OK: the pending reason renders in its own box on %s, chips stay text-free, and the "
          "box hides on a card with nothing pending" % pending)
    return 0


if __name__ == "__main__":
    sys.exit(main())
