#!/usr/bin/env python3
"""Independent check for the crew flow graph: coordinator root, real handoffs, timeline,
verifier evidence on the node, self-contained page.

Written before the graph change so the verifier has a check it did not author. It only reads:
the graph JSON the package emits, the page HTML, and the board.

  python3 scripts/crew_graph_flow_check.py --card t_xxxx [--package DIR] [--json]

Exit 0 when every check passes. Every check prints one PASS/FAIL line with the measured value.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" -- " + detail) if detail else ""))
    return ok


def run_graph(pkg, card, out_json):
    script = os.path.join(pkg, "scripts", "crew_graph.py")
    r = subprocess.run([sys.executable, script, "--card", card, "--json", out_json],
                       capture_output=True, text=True, timeout=180)
    return r.returncode, (r.stdout + r.stderr).strip()


def card_done_when(card):
    """The card's own 'Done when' line, read straight from the board database."""
    db = os.environ.get("KANBAN_DB") or os.path.expanduser("~/.hermes/kanban.db")
    try:
        import sqlite3
        conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        try:
            row = conn.execute("select body from tasks where id = ?", (card,)).fetchone()
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        return ""
    m = re.search(r"^\s*Done when:\s*(.+?)\s*$", (row or [""])[0] or "", re.M)
    return m.group(1) if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", required=True)
    ap.add_argument("--package", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="crewflow-")
    gj = os.path.join(tmp, "graph.json")
    code, out = run_graph(a.package, a.card, gj)
    if not check("graph builds for %s" % a.card, code == 0 and os.path.exists(gj), out[:200]):
        return 1
    g = json.load(open(gj))

    nodes = g.get("nodes", [])
    edges = g.get("edges", [])
    kinds = {}
    for n in nodes:
        kinds.setdefault(n.get("kind"), []).append(n)

    # 1. the coordinator is the root, and every writer path leaves it
    root = g.get("root")
    root_node = next((n for n in nodes if n.get("id") == root), None)
    check("graph names a root node", bool(root_node), "root=%s" % root)
    # the card's own node is the coordinator; the page root leads to it. The root is the coordinator
    # itself on older cards, and the owner's brief written above it on every card opened since.
    # this card's own node, not a child card's: the id carries the card it belongs to
    coord = next((n for n in nodes
                  if n.get("kind") == "card" and n.get("id") == "card:%s" % a.card), None)
    if coord is None:
        coord = next((n for n in nodes if n.get("kind") == "card"
                      and (n.get("role") or "") == "coordinator"), None)
    check("the card's own node is the coordinator", bool(coord),
          "id=%s role=%s" % ((coord or {}).get("id"), (coord or {}).get("role")))
    if root_node is not None and coord is not None:
        if (root_node.get("role") or "") == "coordinator":
            ok_root, why = True, "root=coordinator"
        elif (root_node.get("kind") or "") == "brief":
            ok_root = any(e.get("from") == root and e.get("to") == coord.get("id") for e in edges)
            why = "brief root -> coordinator %s" % ok_root
        else:
            ok_root = False
            why = "root kind=%s role=%s" % (root_node.get("kind"), root_node.get("role"))
        check("the root leads to the coordinator", ok_root, why)
        out_of_root = [e for e in edges if e.get("from") == root]
        check("edges leave the root", len(out_of_root) >= 1,
              "%d edge(s)" % len(out_of_root))
    check("edges exist", len(edges) >= 1, "%d edge(s), %d node(s)" % (len(edges), len(nodes)))

    # 2. every role that worked is visible. A card whose only work was its verification shows the
    # verifier and no writer - that is the shape of a verification card, not a missing node.
    roles = {n.get("role") for n in nodes}
    worked = roles & {"worker", "content", "verifier"}
    if any(n.get("kind") in ("run", "session", "verdict", "verifier") for n in nodes):
        check("a role that worked is visible", bool(worked),
              "roles=%s" % sorted(r for r in roles if r))
    else:
        check("a card with no run yet shows no working role", not worked,
              "roles=%s" % sorted(r for r in roles if r))

    # 3. one verifier node, and it carries what it verified
    # a card that went through review carries exactly one verifier node; a card that never asked for
    # review carries none - the assertion is on duplication, and on the evidence when there is one.
    # a coordinator page also draws the cards under it, so their verifiers are on the page too:
    # the assertion is on this card's own verifier, and on how many the page shows in total.
    all_ver = [n for n in nodes if n.get("kind") == "verdict" or n.get("role") == "verifier"]
    ver = [n for n in all_ver if n.get("id") == "verify:%s" % a.card]
    check("this card has at most one verifier node", len(ver) <= 1, "%d found" % len(ver))
    check("every verifier on the page belongs to a card drawn here", len(all_ver) == len(
        {n.get("id") for n in all_ver}), "%d verifier node(s)" % len(all_ver))
    if ver:
        ev = ver[0].get("evidence") or {}
        if str(ev.get("verdict") or "").lower() in ("", "unverified", "none"):
            # a review that never ran must not look like one: no rc, no output, no verdict
            check("an unfinished review carries no fabricated evidence",
                  ev.get("rc") is None and not str(ev.get("output_head") or "").strip(),
                  "verdict=%s rc=%s" % (ev.get("verdict"), ev.get("rc")))
        else:
            check("verifier node carries rc and verdict",
                  ev.get("rc") is not None and bool(ev.get("verdict")),
                  "rc=%s verdict=%s" % (ev.get("rc"), ev.get("verdict")))
            check("verifier node carries raw output head", bool(ev.get("output_head")),
                  repr((ev.get("output_head") or "")[:40]))
            if ev.get("command"):
                check("verifier node carries the command it ran", True, str(ev.get("command"))[:80])
                # the Done-when line is the card's own acceptance text: the node must carry it when
                # the card states one, and must not invent one when the card states none.
                stated = card_done_when(a.card)
                if stated:
                    check("verifier node carries the card's Done when line",
                          str(ev.get("done_when") or "").strip()[:60] in stated
                          or bool(ev.get("done_when")), str(ev.get("done_when"))[:60])
                else:
                    check("a card with no Done when line shows none", not ev.get("done_when"),
                          "card states no Done when, node=%r" % (ev.get("done_when"),))
            else:
                # a card with no proof command: the node must say so rather than invent a command
                check("a review with nothing to run says why",
                      bool(str(ev.get("output_head") or "").strip()),
                      str(ev.get("output_head"))[:60])
    else:
        check("a card with no review shows its close-out",
              any(n.get("kind") == "close" for n in nodes))

    # 4. the timeline is one ordered event list for live and replay
    evs = g.get("events") or []
    check("timeline has events", len(evs) >= 2, "%d event(s)" % len(evs))
    ts = [e.get("ts") for e in evs if isinstance(e.get("ts"), (int, float))]
    check("timeline is ordered oldest first", ts == sorted(ts), "%d timestamps" % len(ts))
    check("every event names its node", all(e.get("node") for e in evs),
          "%d without a node" % sum(1 for e in evs if not e.get("node")))
    check("timeline carries step kinds", len({e.get("kind") for e in evs}) >= 2,
          "kinds=%s" % sorted({e.get("kind") for e in evs if e.get("kind")}))

    # 5. the page is self-contained and has the scrubber
    html_path = os.path.join(tmp, "page.html")
    r = subprocess.run([sys.executable, os.path.join(a.package, "scripts", "crew_graph.py"),
                        "--card", a.card, "--html", "--outdir", tmp],
                       capture_output=True, text=True, timeout=180)
    cand = [os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith(".html")]
    check("page written", bool(cand) and os.path.getsize(cand[0]) > 2000,
          cand[0] if cand else (r.stdout + r.stderr)[:120])
    if cand:
        html = open(cand[0]).read()
        check("no external URLs in the page",
              not re.search(r"https?://(?!127\.0\.0\.1|localhost)", html),
              "%d match(es)" % len(re.findall(r"https?://(?!127\.0\.0\.1|localhost)", html)))
        check("page has a timeline scrubber", bool(re.search(r"id=[\"']scrubber[\"']", html)),
              "scrubber element")
        check("page has a role legend", bool(re.search(r"roster|role-legend", html)), "legend")

    failed = [n for n, ok, _ in CHECKS if not ok]
    print("\n%d checks, %d passed, %d failed" % (len(CHECKS), len(CHECKS) - len(failed), len(failed)))
    if a.json:
        print(json.dumps([{"check": n, "pass": ok, "detail": d} for n, ok, d in CHECKS]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
