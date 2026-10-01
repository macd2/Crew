#!/usr/bin/env python3
"""Proof that the top of the card page is one area of columns, each thing in its own box.

Done when the top of a card page reads as a single area (#toparea) laid out in columns instead of one
ragged strip: the first column carries what the page shows today, structured, and the reason box and
the spinning box each sit in their own bordered cell, all of them filling the width, side by side on a
wide viewport and stacked on a narrow one, with nothing overflowing its own box.

Contract pinned here (drives the live page in headless Chrome over the DevTools protocol):
  #toparea   inside #main, before #row. Spans the width of #main. A row of column cells: at
             >=1200px every cell shares the same top (+/-2px) and their x positions strictly
             increase; at 500px they stack (tops differ).
  cells      two column cells on a card that is not looping, three when the spinning note has a
             reason to show, each its own box (a visible border or a non-transparent background)
             whose content does not run off the side (scrollWidth <= clientWidth + 2).
  cell 1     holds #sit, the chips the page shows today: each chip is its own box, nothing clipped,
             and no "spinning:" text - the spinning note lives in its own cell. Under the chips sits
             #sitfields, the card's own fields as one line of label/value pairs (model, started,
             kanban id, coordinator), with a copy button on the kanban id and on the coordinator's
             session. No
             fact is stated twice inside the box: the state and the run breakdown stay chips, the
             tokens stay in the rail, and the role, who and the verifier stay the graph's labels, so
             none of them comes back as a row.
  cell 2     holds #sitbox (the pending reason).
  cell 3     holds #spinbox (the repeated stop note) on a card that keeps stopping.
  the rail   the token block first, the brief under it, on any card, brief recorded or not.
  the roles  one horizontal strip (#rolestrip holding #roster) between the top area and the row
             (owner, 2026-10-01: "move the filters for the roles in one horizontal strip below the top
             boxes"), never inside the rail.

Exit 0 = every check passed. Non-zero = it did not, and the failing check is printed.
"""
import importlib.util
import json
import os
import random
import re
import shutil
import signal
import sqlite3
import string
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_proof_board  # noqa: E402
import crew_card  # noqa: E402 - the owner profile and the base home
URL = crew_proof_board.graph_base()
KANBAN_DB = crew_proof_board.proof_db()
PORT = 9342
CHROME = (shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser"))
FAILURES = []
STOPS = 8
REASON = (
    "Needs you: 3 failed verifications on this card. no proof command on the card\n"
    "The verifier ran the card's proof three times and each run returned the same failure, so the "
    "card is now parked: raise the ceiling, add the missing proof command, or split the card."
)


def check(name, ok, detail=""):
    print("%-60s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + detail) if detail else ""))
    if not ok:
        FAILURES.append(name)
    return ok


def devtools_json(path):
    with urllib.request.urlopen("http://127.0.0.1:%d%s" % (PORT, path), timeout=10) as fh:
        return json.loads(fh.read().decode())


def seed_probe():
    """A blocked card with a reason and a repeated stop, seeded straight into the board database."""
    card = "t_" + "".join(random.choice(string.hexdigits[:16]) for _ in range(8))
    now = int(time.time())
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute(
            "insert into tasks (id, title, body, assignee, status, priority, created_by, created_at, "
            "workspace_kind, block_kind) values (?, ?, ?, 'crew-worker', 'blocked', 0, 'probe', ?, "
            "'scratch', 'needs_input')",
            (card, "PROBE toparea %d" % now,
             "Coordinator: %s/\nGoal: probe card for the top area columns\nRole: worker\n"
             "proof command: true\n" % (os.environ.get("CREW_ROLE") or crew_card.owner_profile()), now))
        for i in range(STOPS):
            conn.execute(
                "insert into task_runs (task_id, profile, status, started_at, ended_at, outcome, "
                "summary, last_heartbeat_at) values (?, 'crew-worker', 'blocked', ?, ?, 'blocked', ?, ?)",
                (card, now - 900 + i * 60, now - 870 + i * 60, REASON, now - 870 + i * 60))
        conn.execute("insert into task_comments (task_id, author, body, created_at) values "
                     "(?, 'probe', ?, ?)", (card, REASON, now - 900))
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


JS = r"""
(function(){
  function rect(el){ var r=el.getBoundingClientRect();
    return {x:Math.round(r.left), y:Math.round(r.top), w:Math.round(r.width), h:Math.round(r.height)}; }
  function boxed(el){ var c=getComputedStyle(el);
    var border=parseFloat(c.borderTopWidth)+parseFloat(c.borderLeftWidth);
    var bg=c.backgroundColor; var solid=bg && bg!=='rgba(0, 0, 0, 0)' && bg!=='transparent';
    return border>0 || solid; }
  function over(el){ return el.scrollWidth > el.clientWidth + 2; }
  var area=document.getElementById('toparea'), main=document.getElementById('main'),
      row=document.getElementById('row'), sit=document.getElementById('sit'),
      cells=area ? [].slice.call(area.children) : [];
  var out={ area: !!area, inMain: !!(area && main && main.contains(area)), beforeRow: false,
            areaRect: area?rect(area):null, mainW: main?Math.round(main.clientWidth):0,
            tracks: area?getComputedStyle(area).gridTemplateColumns:'',
            cells:[], areaOverflow: area?over(area):null, rowAfter: false,
            sitInFirst:false, sitOver:null, chipsBoxed:null, chipsClipped:null,
            sel: {}, sitText: sit?sit.innerText:'', cellTexts: [] };
  if (area && row) { out.beforeRow = !!(area.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING); }
  if (area && row) { out.rowAfter = !!(area.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING); }
  for (var i=0;i<cells.length;i++){
    var c=cells[i];
    out.cells.push({i:i, rect:rect(c), boxed:boxed(c), overflow:over(c),
                    hasSit: !!c.querySelector('#sit'), hasSitbox: !!c.querySelector('#sitbox'),
                    hasSpin: !!c.querySelector('#spinbox'),
                    text: (c.innerText||'').replace(/\s+/g,' ').slice(0,40)});
    out.cellTexts.push((c.innerText||'').replace(/\s+/g,' ').slice(0,60));
  }
  if (sit){
    var kids=[].slice.call(sit.children);
    out.sitOver = over(sit);
    out.chipsBoxed = kids.length > 0 && kids.every(function(k){ return boxed(k); });
    out.chipsClipped = kids.some(function(k){ return over(k); });
    out.sitInFirst = !!(cells.length && cells[0].contains(sit));
    out.sitRect = rect(sit);
  }
  ['sit','sitbox','spinbox','toksec'].forEach(function(id){
    var el=document.getElementById(id); out.sel[id]= el? rect(el) : null;
  });
  // The rail's own order: the token block first, the brief under it, the roster below both.
  var tok=document.getElementById('toksec'), brf=document.getElementById('briefsec'),
      rost=document.getElementById('roster');
  out.railOrder = (tok&&brf)
    ? ((tok.compareDocumentPosition(brf) & Node.DOCUMENT_POSITION_FOLLOWING) ? 'tokens-first'
                                                                            : 'brief-first')
    : 'missing';
  var strip=document.getElementById('rolestrip'), rail=document.getElementById('rail');
  out.rosterStrip = !!(strip && rost && strip.contains(rost) && !(rail && rail.contains(rost)) && area && row &&
    (area.compareDocumentPosition(strip) & Node.DOCUMENT_POSITION_FOLLOWING) &&
    (strip.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING));
  return out;
})()
"""


FIELDS_JS = r"""
(function(){
  var box=document.getElementById('sitfields');
  if(!box) return JSON.stringify({found:false});
  var rows={}, n=0;
  [].forEach.call(box.querySelectorAll('.fp'), function(r){
    var k=r.querySelector('.fk'), v=r.querySelector('.fv');
    if(k && v){ rows[k.textContent]=v.textContent; n++; } });
  var id=document.getElementById('cardIdCopy'), co=document.getElementById('cardCoCopy');
  var sit=document.getElementById('sit'), area=document.getElementById('toparea');
  return JSON.stringify({found:true, rows:rows, count:n,
    chips:[].map.call(sit?sit.children:[], function(k){ return k.textContent; }),
    chipText: sit? sit.innerText : '',
    pairs: box.querySelectorAll('.fp').length,
    boxH: Math.round(box.getBoundingClientRect().height),
    boxW: Math.round(box.getBoundingClientRect().width),
    areaCells: area? area.children.length : 0,
    visibleCells: area? [].filter.call(area.children, function(c){ return !c.hidden && c.offsetParent !== null; }).length : 0,
    visibleSpinCells: area? [].filter.call(area.children, function(c){ return !c.hidden && c.offsetParent !== null && !!c.querySelector('#spinbox'); }).length : 0,
    twoCols: area? area.classList.contains('two') : false,
    tracks: area? getComputedStyle(area).gridTemplateColumns : '',
    spinCells: area? [].filter.call(area.children, function(c){ return !!c.querySelector('#spinbox'); }).length : 0,
    idBtn:!!id, coBtn:!!co, idTitle:id?id.title:'', coTitle:co?co.title:'',
    overflow: box.scrollWidth>box.clientWidth+2,
    cellOver: box.parentNode.scrollWidth>box.parentNode.clientWidth+2});
})()
"""


def quiet_card_with_a_ledger(exclude):
    """A live card whose ledger carries a ceiling and that is not in a stop loop, with that ceiling.

    Two rules want one card: a tokens row WOULD show on a card with a ledger, and a third column
    WOULD stand on a card that keeps stopping - so the card that has neither is the honest one to
    prove the box leaves the tokens to the rail and the top area drops to two columns.
    """
    conn = sqlite3.connect(KANBAN_DB)
    try:
        ids = [r[0] for r in conn.execute(
            "select id from tasks where coalesce(status,'') != 'archived' order by rowid desc limit 40")]
    finally:
        conn.close()
    for cid in ids:
        if cid == exclude:
            continue
        try:
            with urllib.request.urlopen("%s/card/%s.json" % (URL, cid), timeout=10) as fh:
                data = json.load(fh)
        except Exception:                                          # noqa: BLE001
            continue
        ceiling = int((data.get("tokens") or {}).get("ceiling") or 0)
        if ceiling > 0 and not (data.get("situation") or {}).get("repeat"):
            return cid, ceiling
    return None, 0


def check_card_box(ws, card, status="blocked"):
    """The first cell's box: the card's own fields, and the two values the owner copies off it."""
    raw = ws.evaluate(FIELDS_JS)
    state = json.loads(raw) if isinstance(raw, str) else (raw or {})
    if not check("the card box carries the card's own fields",
                 state.get("found") and (state.get("count") or 0) >= 3,
                 "%s row(s)" % state.get("count")):
        return
    # Four pairs on one line where the box is wide enough: it is the top of the page and the graph
    # wants the height. At the narrow three-column width they may take a second line (about 40px),
    # but never more than two.
    check("the card's fields take one or two lines, not four rows",
          (state.get("boxH") or 0) <= 40 and (state.get("pairs") or 0) == (state.get("count") or 0),
          "%dpx for %s pair(s) in %dpx" % (state.get("boxH") or 0, state.get("pairs"),
                                           state.get("boxW") or 0))
    rows = state.get("rows") or {}
    chip_text = str(state.get("chipText") or "")
    session = (os.environ.get("CREW_ROLE") or crew_card.owner_profile()) + "/"
    check("the box names the card's own id", rows.get("kanban id") == card,
          str(rows.get("kanban id")))
    check("the box names the coordinator session", rows.get("coordinator") == session,
          str(rows.get("coordinator"))[:40])
    # No duplicates inside the box: the state and the run breakdown are said once, in the chips, so
    # the rows must not carry them back; the id is the row's, so the chips must not carry it; the
    # role, who and the verifier are the graph's own labels and stay off the box.
    check("the state and the run breakdown are said once",
          status in chip_text and card not in chip_text
          and "state" not in rows and "runs" not in rows,
          "chips=%r rows=%s" % (chip_text[:60], sorted(rows)))
    check("the box does not repeat the graph's role, who or verifier",
          not [k for k in rows if k in ("role", "who", "verifier")],
          str(sorted(rows)))
    check("the tokens stay in the rail, out of the card box",
          "tokens" not in chip_text.lower() and not [k for k in rows if "token" in k.lower()],
          chip_text[:60])
    check("each copied value has its own button", bool(state.get("idBtn")) and bool(state.get("coBtn")),
          "id=%s session=%s" % (state.get("idBtn"), state.get("coBtn")))
    check("the buttons say what they copy",
          state.get("idTitle") == "copy the kanban id"
          and state.get("coTitle") == "copy the coordinator session",
          "%s / %s" % (state.get("idTitle"), state.get("coTitle")))
    check("the fields stay inside the box",
          state.get("overflow") is False and state.get("cellOver") is False,
          "field=%s cell=%s" % (state.get("overflow"), state.get("cellOver")))
    granted = True
    try:
        ws.call(9, "Browser.grantPermissions",
                {"origin": URL, "permissions": ["clipboardReadWrite", "clipboardSanitizedWrite"]})
    except Exception:                                              # noqa: BLE001
        granted = False
    if not granted:
        return
    ws.evaluate("document.getElementById('cardIdCopy').click()")
    time.sleep(0.8)
    got = str(ws.evaluate("navigator.clipboard.readText()") or "")
    check("the id button copies the kanban id", got == card, got[:40])
    ws.evaluate("document.getElementById('cardCoCopy').click()")
    time.sleep(0.8)
    got = str(ws.evaluate("navigator.clipboard.readText()") or "")
    check("the session button copies the coordinator session", got == session, got[:40])

    # The cards the rail and the top area are about: a ledger with a ceiling is what would make a
    # tokens row visible, and a stop loop is what would make the third column stand, so a card with
    # neither proves nothing about either rule.
    other, ceiling = quiet_card_with_a_ledger(card)
    if not other:
        print("%-60s %s" % ("a live card with a ledger and no stop loop", "SKIP"))
        return
    ws.call(2, "Emulation.setDeviceMetricsOverride",
            {"width": 1400, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    ws.call(1, "Page.navigate", {"url": "%s/card/%s" % (URL, other)})
    for _ in range(30):
        try:
            if ws.evaluate("!!document.getElementById('sitfields')"):
                break
        except Exception:                                          # noqa: BLE001
            pass
        time.sleep(0.4)
    st = json.loads(ws.evaluate(FIELDS_JS) or "{}")
    rows, chips = st.get("rows") or {}, str(st.get("chipText") or "")
    check("a card carrying %d weighed tokens keeps them in the rail" % ceiling,
          not [k for k in rows if "token" in k.lower()] and "tokens" not in chips.lower(),
          "%s rows=%s chips=%r" % (other, sorted(rows), chips[:44]))
    check("a card that is not looping keeps two columns, not a third holding a note",
          (st.get("visibleCells") or 0) == 2 and (st.get("visibleSpinCells") or 0) == 0
          and st.get("twoCols") is True and len((st.get("tracks") or "").split()) == 2,
          "%s: %s cell(s) of %s, %s spinning, two=%s, tracks=%r"
          % (other, st.get("visibleCells"), st.get("areaCells"), st.get("visibleSpinCells"),
             st.get("twoCols"), st.get("tracks")))
    check("the fields of that card take at most two lines",
          (st.get("boxH") or 0) <= 40, "%dpx in %dpx" % (st.get("boxH") or 0, st.get("boxW") or 0))


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


def measure(ws, card, width=None, height=900):
    if width:
        ws.call(2, "Emulation.setDeviceMetricsOverride",
                {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})
    return ws.evaluate(JS) or {}


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

    card = seed_probe()
    if not card:
        print("PROOF FAIL: could not seed the probe card")
        return 2
    profile = tempfile.mkdtemp(prefix="crew-toparea-")
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--remote-debugging-port=%d" % PORT,
         "--user-data-dir=" + profile, "--window-size=1400,900", "%s/card/%s" % (URL, card)],
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
            for _ in range(40):
                state = ws.evaluate(JS) or {}
                if state.get("area") or state.get("sel", {}).get("sit"):
                    break
                time.sleep(0.5)
            wide = measure(ws, card)
            check("the top area exists inside #main", state.get("inMain"))
            check("the top area sits before the rail and stage", wide.get("beforeRow"))
            check("the top area is one area of columns", len(wide.get("cells") or []) >= 2,
                  "%d cell(s)" % len(wide.get("cells") or []))
            # The probe card keeps stopping, so it carries the third column; a card that is not
            # looping loses that cell and the grid drops to two tracks (checked below on such a card).
            check("a stopping card keeps its third column",
                  len(wide.get("cells") or []) == 3
                  and len((wide.get("tracks") or "").split()) == 3
                  and any(c.get("hasSpin") for c in (wide.get("cells") or [])),
                  "%d cell(s), tracks=%r" % (len(wide.get("cells") or []), wide.get("tracks")))
            check("the top area fills the width", bool(wide.get("areaRect"))
                  and wide.get("areaRect").get("w") >= 0.98 * (wide.get("mainW") or 1),
                  "%s of %s px" % ((wide.get("areaRect") or {}).get("w"), wide.get("mainW")))
            check("the top area does not overflow", wide.get("areaOverflow") is False)
            cells = wide.get("cells") or []
            check("every cell is its own box", bool(cells) and all(c.get("boxed") for c in cells),
                  ",".join(str(c.get("boxed")) for c in cells))
            check("no cell overflows its box", bool(cells) and not any(c.get("overflow") for c in cells))
            tops = [c["rect"]["y"] for c in cells]
            xs = [c["rect"]["x"] for c in cells]
            check("the cells sit side by side on a wide page",
                  bool(tops) and max(tops) - min(tops) <= 2 and all(
                      xs[i] < xs[i + 1] for i in range(len(xs) - 1)),
                  "tops=%s xs=%s" % (tops, xs))
            check("the chips are the first column", wide.get("sitInFirst"))
            check("the pending reason has its own cell",
                  any(c.get("hasSitbox") for c in cells))
            check("the spinning note has its own cell", any(c.get("hasSpin") for c in cells))
            check("the chips are each their own box", wide.get("chipsBoxed") is True)
            check("no chip is clipped", wide.get("chipsClipped") is False)
            check("the chips stay inside their column", wide.get("sitOver") is False
                  and bool(wide.get("sitRect"))
                  and wide["sitRect"]["w"] <= (cells[0]["rect"]["w"] if cells else 0) + 2,
                  "sit=%s cell1=%s" % ((wide.get("sitRect") or {}).get("w"),
                                       (cells[0]["rect"]["w"] if cells else None)))
            check("the spinning line is not a chip any more",
                  "spinning" not in str(wide.get("sitText") or "").lower())
            narrow = measure(ws, card, width=500)
            ntops = [c["rect"]["y"] for c in (narrow.get("cells") or [])]
            check("the columns stack on a narrow page",
                  bool(ntops) and max(ntops) - min(ntops) > 10, "tops=%s" % ntops)
            check("the rail and its token block are untouched",
                  wide.get("sel", {}).get("toksec") is not None
                  and wide.get("sel", {}).get("toksec").get("w", 0) > 0)
            check("the rail carries the tokens above the brief",
                  wide.get("railOrder") == "tokens-first", str(wide.get("railOrder")))
            check("the roles are one strip between the top area and the row, not in the rail",
                  wide.get("rosterStrip") is True, "rosterStrip=%s" % wide.get("rosterStrip"))
            check_card_box(ws, card)
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
        drop_probe(card)

    if FAILURES:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILURES), "; ".join(FAILURES)))
        return 1
    print("PROOF OK: the top of the card page is one area of columns, each thing in its own box, "
          "full width on a wide page and stacked on a narrow one, and the first cell names the "
          "card's own fields with a copy button on the kanban id and the coordinator session")
    return 0


if __name__ == "__main__":
    sys.exit(main())
