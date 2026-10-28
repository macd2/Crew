#!/usr/bin/env python3
"""Always-on crew surface over HTTP (tailnet-friendly).

  /                 the page: a thin shell that loads /app.js (the React app: board, card page, flow graph)
  /app.js           the app, built from ui/src (crew_dashboard/app.js)
  /board            the same shell; the app reads location.pathname (/, /card/<id>) and ?all=1
  /board.json       the same board data, polled every 2s by the page; carries attention.rows
  POST /ack/<id>    clear ONE notification off the list (?undo=1 restores it)
  POST /ack/all     clear every listed notification at once (?undo=1 restores them); both writes go
                    into <dir of the board's kanban.db>/crew/attention_acks.json (CREW_ACK_FILE overrides) - never into the board. POST only, and
                    only from a same-origin page: a GET answers 405, a cross-site Origin answers 403.
  /crew?card=<id>   the same shell, showing one card's live flow graph (polls /card/<id>.json every 2s): the card
                    link crew sends out (crew_card.card_url); /crew alone is the board
  /card/<id>        the same card page, the older address (kept so links already sent still open)
  /card/<id>.json   the graph, rebuilt per request
  /healthz          text probe

Read-only against the board and the session stores. No external assets; the only write is the ack file.
Bind address and port come from CREW_GRAPH_BIND / CREW_GRAPH_PORT.

The Host header must name this server: 127.0.0.1 / localhost / [::1] on the bound port, or a name listed in
CREW_GRAPH_HOSTS (comma list, e.g. the tailnet name; a bare name or name:port) - anything else answers 421,
which closes the DNS-rebinding route to the board. Every HTML response carries a strict CSP: this origin
only, no inline script.
"""
import importlib.util
import json
import os
import platform
import random
import re
import sys
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_proc  # noqa: E402
DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = 8799
BOARD_LIMIT = 200
DONE_SHOWN = 15
ARCHIVED_SHOWN = 30            # the Archived column draws the newest of these; its count is the total
# Five lanes in a fixed order that never changes (ui-spec section 4): an empty lane stays in place and the
# page draws it as a thin rail, so a column never moves between polls. What waits on the owner comes first.
# 'ready' and 'todo' are one lane: two columns with the same label is a duplicate, not a status.
LANES = [("blocked", "Needs you", ("blocked", "triage")),
         ("running", "Working", ("running",)),
         ("review", "In review", ("review",)),
         ("queued", "Queued", ("ready", "todo")),
         ("done", "Done", ("done",))]
BUDGET_SHOWN_PCT = 80          # a tile shows its token budget only from here on (amber), red at 100


def load_graph_module():
    path = os.path.join(HERE, "crew_graph.py")
    spec = importlib.util.spec_from_file_location("crew_graph_lib", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CG = load_graph_module()


# The board's own rule for the proof suite's scaffolding: a card titled PROBE/TEST is the suite's
# own, and it stays out of the lanes, the counts, the bell - and out of a clear-all. One owner, so
# the page and the clear-all walk cannot disagree about which cards are scaffolding.
PROBE_RX = re.compile(r"\s*(PROBE|TEST)\b", re.I)


def is_probe_card(title):
    return bool(PROBE_RX.match((title or "").strip()))


def ago(sec):
    if sec is None:
        return ""
    sec = int(max(0, sec))
    if sec < 60:
        return "%ds" % sec
    if sec < 3600:
        return "%dm" % (sec // 60)
    if sec < 86400:
        return "%dh" % (sec // 3600)
    return "%dd" % (sec // 86400)


# A worker that dies without a settle row leaves status='running' behind for ever, so the board
# claimed "1 working now" for a card that finished hours earlier (and for archived probe cards). A run
# counts as working only while it can still be: its worker process answers, or - for a row whose pid is
# a launch wrapper that is already gone - it started or beat inside this window.
RUN_QUIET_SECONDS = 1800


def pid_alive(pid):
    return crew_proc.alive(pid)


def run_is_live(run, now):
    """run: (id, task_id, profile, status, started_at, ended_at, last_heartbeat_at, outcome, worker_pid)."""
    beat = run[6] if len(run) > 6 else None
    started = run[4] if len(run) > 4 else None
    pid = run[8] if len(run) > 8 else None
    if pid and pid_alive(pid):
        return True
    return (now - (beat or started or now)) <= RUN_QUIET_SECONDS


def tile_verdict(db, card_id, body):
    """The verdict chip of a tile, from the one verdict record (crew_card.all_verdicts, section 9 of the spec):
    the newest line since the newest claim - the line the close rule ends on, as the card page's verifier node
    reads it. 'unverified' for a card with a verifier and no such line; None for a card with no verifier."""
    verdicts = CG.crew_card.all_verdicts(card_id)
    if not verdicts and not CG.body_field(body, "Verifier"):
        return None
    claims = [ts for kind, ts, _ in CG.load_task_events(db, card_id) if kind == "claimed"]
    since = CG.crew_card.verdict_lines(card_id, max(claims) if claims else None, verdicts)
    last = since[-1] if since else None
    verdict = str((last or {}).get("verdict") or "").upper()
    return verdict if verdict in ("PASS", "FAIL") else "unverified"


def tile_summary(db, card_id, status, last_failure_error):
    """One line about the work: why it waits (blocked/triage), else what the newest run reported."""
    runs = CG.load_runs(db, card_id)
    if status in ("blocked", "triage"):
        reason = CG.load_block_reason(db, card_id, runs, last_failure_error, status)[0]
        if reason:
            return " ".join(reason.split())[:300]
    for run in reversed(runs):
        if run[4] and str(run[4]).strip():
            return " ".join(str(run[4]).split())[:300]
    return ""


def tile_budget(card_id):
    """{used, ceiling, pct} of the card's token ledger, or None when it has no ceiling."""
    led = CG.load_ledger_totals(card_id)
    if not led.get("ceiling"):
        return None
    return {"used": led["used"], "ceiling": led["ceiling"], "pct": led["pct"]}


def board_data(include_all=False, older=False):
    """Every live card with its role and, when a run is alive, the profile working on it now.

    include_all (the page's ?all=1) also lists the proof suite's test cards. Archived cards never enter the
    counts or the live lanes: they fill the last, owner-collapsed 'archived' lane - the newest ARCHIVED_SHOWN,
    with `hidden` the rest, so lane tiles + hidden is the total. older (the Done lane's "Show N older")
    lists every done card instead of the newest DONE_SHOWN."""
    db = CG.kanban_db_path()
    if not db:
        return {"error": "no kanban database", "lanes": [], "counts": {}}
    tasks = CG.q(db, "select id, title, status, assignee, created_at, started_at, completed_at, "
                     "body, skills, last_failure_error from tasks where status != 'archived' "
                     "order by created_at desc limit ?", (BOARD_LIMIT,))
    arch_all = [r for r in CG.q(db, "select id, title from tasks where status = 'archived' "
                                    "order by created_at desc") if include_all or not is_probe_card(r[1])]
    arch_ids = [r[0] for r in arch_all[:ARCHIVED_SHOWN]]
    if arch_ids:
        tasks += CG.q(db, "select id, title, status, assignee, created_at, started_at, completed_at, "
                          "body, skills, last_failure_error from tasks where id in (%s) "
                          "order by created_at desc" % ",".join("?" * len(arch_ids)), tuple(arch_ids))
    ids = [t[0] for t in tasks]
    runs = {}
    if ids:
        marks = ",".join("?" * len(ids))
        for r in CG.q(db, "select id, task_id, profile, status, started_at, ended_at, "
                           "last_heartbeat_at, outcome, worker_pid from task_runs where task_id in (%s) "
                           "order by id" % marks, tuple(ids)):
            runs.setdefault(r[1], []).append(r)
    now = time.time()
    tiles = []
    facts = {}
    for tid, title, status, assignee, created, started, completed, body, skills, lfe in tasks:
        facts[tid] = (body or "", lfe)
        my_runs = runs.get(tid, [])
        live = [r for r in my_runs if r[3] == "running" and run_is_live(r, now)]
        profile = (live[0][2] if live else assignee) or ""
        role = CG.card_role(body or "", skills) or CG.profile_role(profile, "worker")
        if live:
            beat = live[0][6] or live[0][4]
            active = {"profile": profile, "run": live[0][0],
                      "for_s": int(now - (live[0][4] or now)),
                      "quiet_s": int(now - (beat or now)) if beat else None}
            # what this run has verifiably done, read off its own session: the step count and the tool it is
            # in. Facts only - the tile says nothing about how long is left (issue #9 option 1).
            active.update(CG.live_run_facts(db, tid, live[0][0], live[0][2]))
        else:
            active = None
        ended = completed or (my_runs[-1][5] if my_runs and my_runs[-1][5] else None)
        tiles.append({
            "id": tid, "title": (title or "").strip(), "status": status,
            "test": is_probe_card(title),
            "assignee": assignee or "", "role": role,
            "color": CG.ROLE_COLOURS.get(role, CG.ROLE_FALLBACK),
            "runs": len(my_runs), "active": active,
            "age_s": int(now - (created or now)),
            "settled_s": int(now - ended) if ended else None,
            "last_outcome": (my_runs[-1][7] or "") if my_runs else "",
        })
    # test cards (the proof suite's PROBE cards) are scaffolding: they never enter the counts or the
    # lanes, so the board's numbers describe the real work. ?all=1 still lists them.
    archived = [t for t in tiles if t["status"] == "archived"]
    tiles = [t for t in tiles if t["status"] != "archived"]
    test_cards = [t for t in tiles if t.get("test")]
    if not include_all:
        tiles = [t for t in tiles if not t.get("test")]
    lanes = []
    claimed = set()
    for key, label, statuses in LANES:
        rows = [t for t in tiles if t["status"] in statuses]
        claimed |= set(statuses)
        hidden = 0
        if key == "done" and not older and len(rows) > DONE_SHOWN:
            hidden = len(rows) - DONE_SHOWN
            rows = rows[:DONE_SHOWN]
        lanes.append({"key": key, "label": label, "tiles": rows, "hidden": hidden})   # empty lanes stay
    other = [t for t in tiles if t["status"] not in claimed]
    if other:
        lanes.append({"key": "other", "label": "Other", "tiles": other, "hidden": 0})
    lanes.append({"key": "archived", "label": "Archived", "tiles": archived,
                  "hidden": len(arch_all) - len(archived)})        # always last, far right
    # Only the tiles the page draws are enriched (0.8 ms a card measured): every open card and the shown done.
    for lane in lanes:
        for t in lane["tiles"]:
            body, lfe = facts.get(t["id"], ("", None))
            t["summary"] = tile_summary(db, t["id"], t["status"], lfe)
            t["verdict"] = tile_verdict(db, t["id"], body)
            budget = tile_budget(t["id"])
            if budget:
                t["budget"] = budget
            # the Desktop action buttons on the tile (Proof) are enabled by the same question the card page reads
            # (a file read per card, so only where the question can wait: a blocked or triage card)
            t["proof_ask"] = CG.proof_ask_kind(t["id"]) if t["status"] in STUCK else ""
    counts = {}
    for t in tiles:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    return {"generated_at": int(now), "node": platform.node(),
            # the board page header draws these two in the browser; the React page reads them from here instead
            "board": CG.crew_card.board_slug(), "dashboard_url": CG.crew_card.dashboard_url(),
            "live": sum(1 for t in tiles if t["active"]), "lanes": lanes, "counts": counts,
            "cards": len(tiles), "test_cards": len(test_cards),
            "attention": attention_data(db, tiles, now),
            # the Board header draws a warning strip when the gateway (the kanban dispatcher) is not running
            "dispatcher": CG.crew_card.dispatcher_state()}


# ---------------------------------------------------------------- notifications
# The list lives BEHIND the bell in the header, not in a block over the lanes: the bell carries the
# count of what is waiting, a click opens the list - every stuck card (blocked/triage, oldest
# waiting first), then the done cards (newest first, capped like the done lane) - and each row is
# cleared on its own (/ack/<id>) or the whole list at once (/ack/all).
# A clear is written to disk, so it survives a reload and a restart, and it is scoped to the state
# the row was in: a cleared done card stays cleared (done is terminal), a cleared blocked card comes
# back when that card changes state - the owner dismisses a notification, never the card. ?undo=1
# puts one row, or every row, back.
STUCK = ("blocked", "triage")
STATE_KINDS = ("created", "blocked", "gave_up", "crashed", "timed_out", "status", "completed",
               "unblocked", "promoted", "review_requested", "changes_requested")


def legacy_ack_path():
    """Where acks lived before they belonged to the board: beside this plugin copy. Read only, never deleted."""
    return os.path.join(os.path.dirname(HERE), "crew", "attention_acks.json")


def ack_path():
    """CREW_ACK_FILE, else <dir of the active board's kanban.db>/crew/attention_acks.json: the acks belong to the board,
    so two processes (daemon, dashboard plugin, any plugin copy) on one board share one file and two boards never do.
    With no board file, the legacy plugin-side path."""
    env = os.environ.get("CREW_ACK_FILE")
    if env:
        return env
    db = CG.kanban_db_path()
    if not db:
        return legacy_ack_path()
    return os.path.join(os.path.dirname(os.path.abspath(db)), "crew", "attention_acks.json")


def load_acks():
    """The board's acks; until it has its own file, the legacy plugin-side file (the first write copies it over)."""
    path = ack_path()
    if not os.path.exists(path) and not os.environ.get("CREW_ACK_FILE"):
        path = legacy_ack_path()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_acks(acks):
    path = ack_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(acks, fh, indent=1, sort_keys=True)
    os.replace(tmp, path)


def state_since(db, ids):
    """Newest state-changing event per card: what "the state this row is in" means.

    One owner for the rule, because the clear token and the row's age both read it."""
    if not ids:
        return {}
    rows = CG.q(db, "select task_id, max(created_at) from task_events where task_id in (%s) "
                    "and kind in (%s) group by task_id"
                    % (",".join("?" * len(ids)), ",".join("?" * len(STATE_KINDS))),
                tuple(ids) + STATE_KINDS)
    return {tid: ts for tid, ts in rows}


def ack_token(status, entered_ts):
    """What clearing a row writes down. A finished card is cleared for good; a waiting one is
    cleared only for the state it is in, so it comes back when the card moves on."""
    if status == "done":
        return "done"
    return "%s@%d" % (status, int(entered_ts or 0))


def row_cleared(row, acks):
    """True when this row was already cleared and nothing has moved since."""
    return acks.get(row["id"]) == ack_token(row["status"], row.get("entered_ts"))


def attention_data(db, tiles, now):
    pick = [t for t in tiles if t["status"] in STUCK + ("done",)]
    since = state_since(db, [t["id"] for t in pick])
    acks = load_acks()
    stuck, done = [], []
    for t in pick:
        entered = since.get(t["id"])
        if t["status"] == "done" and t["settled_s"] is not None:
            age = t["settled_s"]
        elif entered:
            age = int(now - entered)
        else:
            age = t["age_s"]
        row = {"id": t["id"], "status": t["status"], "title": t["title"],
               "who": t["assignee"] or t["role"] or "", "age_s": max(0, int(age)),
               "entered_ts": int(entered or 0), "ack_url": "/ack/%s" % t["id"],
               "color": t["color"]}
        if row_cleared(row, acks):
            continue
        (stuck if t["status"] in STUCK else done).append(row)
    stuck = sorted(stuck, key=lambda r: -r["age_s"])
    done = sorted(done, key=lambda r: r["age_s"])[:DONE_SHOWN]
    return {"rows": stuck + done, "stuck": len(stuck), "done": len(done),
            "total": len(stuck) + len(done), "ack_all": "/ack/all"}


def ack_card(card, undo=False):
    """(http code, text) for one click on one row: clear it, or restore it with ?undo=1."""
    db = CG.kanban_db_path()
    row = CG.qone(db, "select status from tasks where id = ?", (card,)) if db else None
    if not row:
        return 404, "no card %s\n" % card
    acks = load_acks()
    if undo:
        acks.pop(card, None)
        save_acks(acks)
        return 200, "restored %s\n" % card
    status = row[0]
    if status not in STUCK + ("done",):
        return 409, "%s is %s: only a row on the list is cleared\n" % (card, status)
    entered = state_since(db, [card]).get(card)
    acks[card] = ack_token(status, entered)
    save_acks(acks)
    return 200, "cleared %s\n" % card


def notifiable_cards(db):
    """(id, status) of every card the bell can show: the stuck ones and every done card on the board.

    Read from the board, never from the lanes or the capped rows: the lanes hold at most DONE_SHOWN
    done cards (the rest are counted as "not shown"), so a clear-all that read them would leave the
    next 15 behind and the bell reading 15 again - which is not what 'clear all' means. The
    scaffolding rule is the board's own, applied through is_probe_card."""
    statuses = STUCK + ("done",)
    rows = CG.q(db, "select id, status, title from tasks where status in (%s)"
                    % ",".join("?" * len(statuses)), statuses)
    return [(tid, status) for tid, status, title in rows if not is_probe_card(title)]


def ack_all(undo=False):
    """(http code, text) for the list's own clear-all: every notification, not just the shown rows."""
    acks = load_acks()
    if undo:
        count = len(acks)
        save_acks({})
        return 200, "restored %d row(s)\n" % count
    db = CG.kanban_db_path()
    cards = notifiable_cards(db)
    entered = state_since(db, [cid for cid, status in cards if status in STUCK])
    for cid, status in cards:
        acks[cid] = ack_token(status, entered.get(cid))
    save_acks(acks)
    return 200, "cleared %d row(s)\n" % len(cards)


# The page every browser route serves: a thin shell. The board, the card page and the flow graph are the React app in
# crew_dashboard/app.js (built from ui/src by ui/build.mjs); it reads location.pathname for its route and polls the
# JSON routes below. No inline script, so the CSP below needs no nonce.
APP_JS = os.path.join(HERE, "crew_dashboard", "app.js")
CARD_PAGE_RX = re.compile(r"^/card/[A-Za-z0-9_-]+/?$")
CARD_ID_RX = re.compile(r"^[A-Za-z0-9_-]+$")


def shell_page():
    return ("<!doctype html><html lang=en><head><meta charset=utf-8>"
            "<meta name=viewport content='width=device-width, initial-scale=1'><title>Crew</title>"
            "%s</head><body><div id=crew-app data-crew-shell></div><script src=/app.js></script></body></html>"
            % CG.favicon_link())


def app_js():
    """The bytes of crew_dashboard/app.js, or None when the file is missing (a broken install answers 404)."""
    try:
        with open(APP_JS, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def allowed_hosts(port):
    """Host header values this server answers to: loopback on the bound port, plus CREW_GRAPH_HOSTS."""
    ok = {"127.0.0.1:%d" % port, "localhost:%d" % port, "[::1]:%d" % port}
    for name in (os.environ.get("CREW_GRAPH_HOSTS") or "").split(","):
        name = name.strip().lower()
        if name:
            ok.add(name)
            if ":" not in name or name.endswith("]"):
                ok.add("%s:%d" % (name, port))
    return ok


_WHOIS = {}   # tailnet ip -> (expires, tags): one `tailscale whois` per device per minute


def peer_tags(ip):
    """The tags of the tailnet device at `ip` (`tailscale whois`). Tagged devices carry no user, so for them the
    tag is the identity. Any failure answers no tags: a lookup that cannot be made lets nobody in."""
    ip = (ip or "").split(",")[0].strip()
    if not ip:
        return set()
    hit = _WHOIS.get(ip)
    if hit and hit[0] > time.time():
        return hit[1]
    try:
        r = subprocess.run(["tailscale", "whois", "--json", ip], capture_output=True, text=True, timeout=3, encoding="utf-8", errors="replace")
        tags = set((json.loads(r.stdout).get("Node") or {}).get("Tags") or []) if r.returncode == 0 else set()
    except (OSError, ValueError, subprocess.SubprocessError):
        tags = set()
    _WHOIS[ip] = (time.time() + 60, tags)
    return tags


def _env_set(name):
    return {v.strip().lower() for v in (os.environ.get(name) or "").split(",") if v.strip()}


def tailnet_user_ok(host, login, port, peer=""):
    """A request that came in under a CREW_GRAPH_HOSTS name was proxied by `tailscale serve`, which names the caller:
    Tailscale-User-Login for a person's device, X-Forwarded-For (its tailnet ip) for every device. It is answered
    for a login in CREW_GRAPH_USERS, or for a device carrying a tag in CREW_GRAPH_TAGS (a tagged device has no
    login - 2026-10-03, the owner's own laptop is `tag:admin`). install.py --publish writes all three. Loopback
    requests are this machine's own. Nothing configured: no tailnet."""
    if (host or "").lower() in {"127.0.0.1:%d" % port, "localhost:%d" % port, "[::1]:%d" % port}:
        return True
    if login and login.strip().lower() in _env_set("CREW_GRAPH_USERS"):
        return True
    tags = _env_set("CREW_GRAPH_TAGS")
    return bool(tags) and bool({t.lower() for t in peer_tags(peer)} & tags)


FACE_RX = re.compile(r"^/avatars/role/([a-z0-9][a-z0-9_-]{0,39})\.svg$")
AVATAR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crew_dashboard", "avatars")
_FACE_LOCK = threading.Lock()


def face_files():
    return sorted(n for n in os.listdir(AVATAR_DIR) if re.match(r"^blobs-\d\d\.svg$", n))


def role_face(role):
    """The face file a role shows: picked at random from the shipped set the first time the role is shown (an unused
    one while any is left) and kept in <base home>/crew/faces.json, so a role keeps its face across restarts,
    upgrades and pages. `crew-<role>` is <role>."""
    role = role[len("crew-"):] if role.startswith("crew-") else role
    files = face_files()
    if not files:
        return None
    path = os.path.join(CG.crew_card.base_home(), "crew", "faces.json")
    with _FACE_LOCK:
        try:
            with open(path, encoding="utf-8") as fh:
                faces = json.load(fh)
            faces = faces if isinstance(faces, dict) else {}
        except (OSError, ValueError):
            faces = {}
        if faces.get(role) in files:
            return faces[role]
        free = [f for f in files if f not in faces.values()] or files
        faces[role] = random.choice(free)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(faces, fh, indent=1, sort_keys=True)
            os.replace(tmp, path)
        except OSError:
            pass   # an unwritable home still shows a face, it just is not kept
        return faces[role]


# The page policy: nothing but this origin, and scripts only from it (the shell has no inline script). The app
# puts its stylesheets into the page as <style> elements, so style-src keeps 'unsafe-inline'; img-src allows the
# data: URL of the tab icon.
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; "
       "frame-ancestors 'none'")


def board_json(show_all=False, older=False):
    """The /board.json body: one owner for the standalone server and the dashboard plugin."""
    return json.dumps(board_data(show_all, older=older))


def face_svg(role):
    """The bytes of the face file a role shows (role_face), or None when there is none / it cannot be read.
    The name comes from role_face, never from a path in the URL."""
    name = role_face(role)
    try:
        with open(os.path.join(AVATAR_DIR, name or ""), "rb") as fh:
            return fh.read()
    except OSError:
        return None


def card_response(rest):
    """(code, body, content type) for /card/<rest>.json: the card's graph JSON. Anything else under /card/ is the
    app's page (the shell), not this function's. One owner for the standalone server and the dashboard plugin."""
    if not rest.endswith(".json"):
        return 404, "not found\n", "text/plain; charset=utf-8"
    graph, err = CG.build_graph(rest[:-len(".json")])
    if err:
        return 404, json.dumps({"error": err}), "application/json"
    return 200, json.dumps(graph), "application/json"


class Handler(BaseHTTPRequestHandler):
    server_version = "crew-graph"

    def _send(self, code, body, ctype, extra=()):
        raw = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if ctype.startswith("text/html"):
            self.send_header("Content-Security-Policy", CSP)
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(raw)
        except BrokenPipeError:
            pass

    def _host_ok(self):
        host = (self.headers.get("Host") or "").strip().lower()
        port = self.server.server_address[1]
        if host not in allowed_hosts(port):
            self._send(421, "misdirected request: unknown Host\n", "text/plain; charset=utf-8")
            return False
        login = self.headers.get("Tailscale-User-Login") or ""
        if not tailnet_user_ok(host, login, port, self.headers.get("X-Forwarded-For") or ""):
            # the refused identity, so an owner locked out of their own board can see what tailscale sent
            sys.stderr.write("refused tailnet login %r from %r on host %r (allowed: %r, tags %r)\n"
                             % (login, self.headers.get("X-Forwarded-For") or "", host,
                                os.environ.get("CREW_GRAPH_USERS") or "", os.environ.get("CREW_GRAPH_TAGS") or ""))
            self._send(403, "forbidden: this tailnet login is not the dashboard's owner\n", "text/plain; charset=utf-8")
            return False
        return True

    def _same_origin(self):
        """A write must come from this server's own page: Origin (else Referer) names the Host it was sent to."""
        if (self.headers.get("Sec-Fetch-Site") or "same-origin") not in ("same-origin", "none"):
            return False
        src = self.headers.get("Origin") or self.headers.get("Referer") or ""
        return bool(src) and urlparse(src).netloc.lower() == (self.headers.get("Host") or "").strip().lower()

    def do_POST(self):
        if not self._host_ok():
            return
        parts = urlparse(self.path)
        path = unquote(parts.path)
        if not path.startswith("/ack/"):
            return self._send(404, "not found\n", "text/plain; charset=utf-8")
        if not self._same_origin():
            return self._send(403, "cross-site write refused\n", "text/plain; charset=utf-8")
        rest = path[len("/ack/"):].strip("/")
        undo = "undo=1" in (parts.query or "")
        code, text = ack_all(undo=undo) if rest == "all" else ack_card(rest, undo=undo)
        return self._send(code, text, "text/plain; charset=utf-8")

    def do_GET(self):
        if not self._host_ok():
            return
        path = unquote(urlparse(self.path).path)
        if path in ("/healthz", "/health"):
            try:
                board = board_data()
                body = "ok crew board cards=%s live=%s\n" % (board.get("cards"), board.get("live"))
            except Exception as exc:
                sys.stderr.write("crew health: board data failed: %r\n" % (exc,))
                body = "ok crew board (no data; the reason is in the crew log)\n"
            return self._send(200, body, "text/plain; charset=utf-8")
        show_all = "all=1" in (urlparse(self.path).query or "")
        if path in ("/", "/index.html", "/board"):
            return self._send(200, shell_page(), "text/html; charset=utf-8")
        if path in ("/crew", "/crew/"):
            # the card link (crew_card.card_url): /crew?card=<id>; no card in the query is the board
            card_id = (parse_qs(urlparse(self.path).query or "").get("card") or [""])[0]
            if not card_id:
                return self._send(200, shell_page(), "text/html; charset=utf-8")
            if not CARD_ID_RX.match(card_id):
                return self._send(404, "not found\n", "text/plain; charset=utf-8")
            _graph, err = CG.build_graph(card_id)
            if err:
                return self._send(404, "no graph for %s (%s)\n" % (card_id, err), "text/plain; charset=utf-8")
            return self._send(200, shell_page(), "text/html; charset=utf-8")
        if CARD_PAGE_RX.match(path):
            # the shell for a card that exists; an id that names no card is a 404 here, not a page that fails to load
            card_id = path[len("/card/"):].strip("/")
            _graph, err = CG.build_graph(card_id)
            if err:
                return self._send(404, "no graph for %s (%s)\n" % (card_id, err), "text/plain; charset=utf-8")
            return self._send(200, shell_page(), "text/html; charset=utf-8")
        if path == "/app.js":
            js = app_js()
            if js is None:
                return self._send(404, "not found\n", "text/plain; charset=utf-8")
            return self._send(200, js, "text/javascript; charset=utf-8")
        if path in ("/board.json", "/index.json"):
            older = "older=1" in (urlparse(self.path).query or "")
            return self._send(200, board_json(show_all, older), "application/json")
        if path.startswith("/ack/"):
            return self._send(405, "use POST\n", "text/plain; charset=utf-8", extra=(("Allow", "POST"),))
        m = FACE_RX.match(path)
        if m:   # a role's face: the shipped file the role was given (role_face), never a path from the URL
            svg = face_svg(m.group(1))
            if svg is None:
                return self._send(404, "not found\n", "text/plain; charset=utf-8")
            return self._send(200, svg, "image/svg+xml")
        if path.startswith("/card/"):
            code, body, ctype = card_response(path[len("/card/"):])
            return self._send(code, body, ctype)
        return self._send(404, "not found\n", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))


def main():
    bind = os.environ.get("CREW_GRAPH_BIND", DEFAULT_BIND)
    try:
        port = int(os.environ.get("CREW_GRAPH_PORT", DEFAULT_PORT))
    except ValueError:
        port = DEFAULT_PORT
    srv = ThreadingHTTPServer((bind, port), Handler)
    sys.stderr.write("crew graph http on http://%s:%d/\n" % (bind, port))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    crew_proc.utf8_stdio()
    main()
