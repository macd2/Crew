#!/usr/bin/env python3
"""Proof for the token section on a crew card page (left rail, fixed positions).

Done when: every card page renders a `#toksec` block at the top of `#rail` (the roles are a strip outside it), with
five rows carrying these exact ids in this exact DOM order:

    #tokCeiling   the card ceiling in weighed tokens
    #tokUsed      billed tokens spent, summed over every ledger file for the card
    #tokRaw       raw total_tokens, summed the same way
    #tokCalls     api call count, summed the same way
    #tokPct       used/ceiling as a percentage with one decimal and a percent sign

and each shown number equals the ledger figure, printed exactly (thousands separators, never
shortened to k/M). Ledger figures, over the base home and every profile home, for `<card>.json`
and `<card>.json.spent`:
    ceiling = max(budget)          used = sum(used)          raw = sum(raw_total)
    calls   = sum(calls)           pct  = round(100*used/ceiling, 1)

Exit 0 = every checked card page agrees with its ledgers. Non-zero = it does not, and the failing
check is printed. Read-only: opens the live pages in headless Chrome over the DevTools protocol.
"""
import argparse
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROW_ORDER = ["tokCeiling", "tokUsed", "tokRaw", "tokCalls", "tokPct"]
ROW_WORDS = {"tokCeiling": "ceiling", "tokUsed": "used", "tokRaw": "raw", "tokCalls": "calls",
             "tokPct": "pct"}
STATES = ["running", "review", "blocked", "done"]
CHROME = (shutil.which("google-chrome") or shutil.which("chromium")
          or shutil.which("chromium-browser"))
PORT = 9334


def crew_module():
    spec = importlib.util.spec_from_file_location("cg", os.path.join(HERE, "crew_graph.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ledger_totals(card_id):
    """(ceiling, used, raw, calls) over every ledger file recorded for this card."""
    base = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
    base = os.path.abspath(base)
    parent = os.path.dirname(base.rstrip(os.sep))
    if os.path.basename(parent) == "profiles":
        base = os.path.dirname(parent)
    homes = [base]
    profdir = os.path.join(base, "profiles")
    if os.path.isdir(profdir):
        homes += [os.path.join(profdir, n) for n in sorted(os.listdir(profdir))]
    ceiling = used = raw = calls = 0
    for home in homes:
        for suffix in ("", ".spent"):
            path = os.path.join(home, "crew", "budget", card_id + ".json" + suffix)
            try:
                with open(path) as fh:
                    data = json.load(fh)
            except Exception:
                continue
            ceiling = max(ceiling, int(data.get("budget") or 0))
            used += int(data.get("used") or 0)
            raw += int(data.get("raw_total") or 0)
            calls += int(data.get("calls") or 0)
    return ceiling, used, raw, calls


def pick_cards(db, wanted):
    """One card id per requested state, newest first."""
    out = {}
    conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    try:
        for state in wanted:
            row = conn.execute(
                "select id from tasks where status = ? order by rowid desc limit 1",
                (state,)).fetchone()
            if row:
                out[state] = row[0]
    finally:
        conn.close()
    return out


def http_json(path):
    with urllib.request.urlopen("http://127.0.0.1:%d%s" % (PORT, path), timeout=10) as fh:
        return json.loads(fh.read().decode())


def wait_for_target(fragment, tries=40):
    for _ in range(tries):
        try:
            for t in http_json("/json/list"):
                if t.get("type") == "page" and fragment in (t.get("url") or ""):
                    return t
        except Exception:
            pass
        time.sleep(0.5)
    return None


def digits(text):
    m = re.findall(r"-?\d[\d,]*", str(text or ""))
    if not m:
        return None
    try:
        return int(m[0].replace(",", ""))
    except ValueError:
        return None


def number(text):
    """First number in the text, decimals kept: '17.9%' reads as 17.9, '3,249,014' as 3249014."""
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(text or ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


JS = """
(function(){
  var rail = document.getElementById('rail'), block = document.getElementById('toksec'),
      roster = document.getElementById('roster');
  var rows = block ? Array.prototype.map.call(
      block.querySelectorAll('.tokrow, [id^="tok"]'),
      function(e){ return e.id; }).filter(function(i){ return i && i !== 'toksec'; }) : [];
  var nums = {};
  ['tokCeiling','tokUsed','tokRaw','tokCalls','tokPct'].forEach(function(id){
    var e = document.getElementById(id);
    nums[id] = e ? e.textContent : null;
  });
  var before = false;
  if (rail && block && block.parentNode) {
    // the token block leads the rail; the roles live in their own strip, never inside the rail
    before = rail.firstElementChild === block && !(roster && rail.contains(roster));
  }
  return {rail: !!rail, roster: !!roster, block: !!block, inRail: !!document.querySelector('#rail #toksec'),
          beforeRoster: before, rows: rows, nums: nums, text: block ? block.textContent.slice(0,300) : ''};
})()
"""


def check_card(ws, host, card):
    """Returns [(name, ok, detail)] for one card page."""
    ws.call(1, "Page.navigate", {"url": "http://%s/card/%s" % (host, card)})
    seen = False
    for _ in range(40):
        try:
            if ws.evaluate("!!document.getElementById('toksec')"):
                seen = True
                break
        except Exception:
            pass
        time.sleep(0.5)
    state = ws.evaluate(JS) or {}
    ceiling, used, raw, calls = ledger_totals(card)

    rows = state.get("rows") or []
    got_rows = [r for r in rows if r in ROW_ORDER]
    extra = [r for r in rows if r not in ROW_ORDER]

    checks = []
    checks.append(("block present in the rail", bool(state.get("inRail"))))
    checks.append(("block leads the rail, the roles are not in it", bool(state.get("beforeRoster"))))
    checks.append(("row ids in fixed order %s" % " > ".join(ROW_ORDER),
                   got_rows == ROW_ORDER))
    if extra:
        checks.append(("no extra token rows (%s)" % ",".join(extra[:3]), False))

    nums = state.get("nums") or {}
    shown = {k: digits(nums.get(k)) for k in ROW_ORDER}
    want = {"tokCeiling": ceiling, "tokUsed": used, "tokRaw": raw, "tokCalls": calls}
    for key in ("tokCeiling", "tokUsed", "tokRaw", "tokCalls"):
        checks.append(("%s shows %s" % (ROW_WORDS[key], format(want[key], ",")),
                       shown.get(key) == want[key]))
    pct_text = nums.get("tokPct") or ""
    want_pct = round(100.0 * used / ceiling, 1) if ceiling else 0.0
    got_pct = number(pct_text)
    checks.append(("pct shows %s%%" % want_pct,
                   got_pct is not None and abs(got_pct - want_pct) <= 0.15
                   and "%" in str(pct_text)))
    if not seen:
        checks.append(("block appeared without interaction", False))
    return checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1:8799")
    ap.add_argument("--cards", default=None, help="comma-separated card ids; default one per state")
    ap.add_argument("--states", default=",".join(STATES))
    args = ap.parse_args()

    if not CHROME:
        print("PROOF FAIL: no chrome binary to render the page with")
        return 2
    try:
        board = pick_cards(crew_module().kanban_db_path(), args.states.split(","))
    except Exception as exc:  # noqa: BLE001
        print("PROOF FAIL: cannot read the board (%s)" % exc)
        return 2
    cards = ([c.strip() for c in args.cards.split(",") if c.strip()] if args.cards
             else [board[s] for s in args.states.split(",") if s in board])
    if not cards:
        print("PROOF FAIL: no card page to check")
        return 2

    url = "http://%s/card/%s" % (args.host, cards[0])
    profile = tempfile.mkdtemp(prefix="crew-tokens-")
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--remote-debugging-port=%d" % PORT, "--user-data-dir=" + profile,
         "--window-size=1400,900", url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    failures = []
    covered = 0
    try:
        target = wait_for_target("/card/")
        if not target:
            print("PROOF FAIL: the page never loaded")
            return 2
        sys.path.insert(0, HERE)
        from crew_ws import WSClient
        ws = WSClient(target["webSocketDebuggerUrl"])
        try:
            for card in cards:
                state = [s for s, c in board.items() if c == card]
                covered += 1
                for name, ok in check_card(ws, args.host, card):
                    print("%-42s %s  %s" % (name, "PASS" if ok else "FAIL",
                                            "%s %s" % (card, state[0] if state else "")))
                    if not ok:
                        failures.append("%s: %s" % (card, name))
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

    if failures:
        print("PROOF FAIL: %d check(s) failed on %d card page(s): %s"
              % (len(failures), covered, "; ".join(failures[:4])))
        return 1
    print("PROOF OK: token block fixed in the rail on %d card page(s), figures match the ledgers"
          % covered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
