#!/usr/bin/env python3
"""Live flow graph for a crew card, modelled on zoetrope's session flow graph.

Reads the shared kanban board and the per-profile session store (both read-only)
and projects one card into a layered graph:

    card -> run(s) -> worker session -> child (subagent) sessions
    card -> verifier (when a verification subagent pass exists)

Node status is carried by colour alone: green = alive/running, red = failed/blocked,
everything else neutral (terminal ANSI: done is yellow; the HTML page takes the dashboard tokens). The layout is a Sugiyama layered layout (topological
layering, barycenter ordering, then x assignment) computed on every render.

Stdlib only. No network. No third-party imports.

Outputs:
  terminal   unicode box nodes in layered rows, ANSI colour only when stdout is
             a tty; --watch SECONDS re-renders in place with a cursor-home escape
  --json     machine-readable JSON
  --html     one self-contained HTML file (inline SVG + inline JS + the crew_dashboard CSS/JS;
             the page inherits the host colours through tokens.css)
             that polls the JSON file written next to it every 2 seconds
"""

import argparse
import base64
import html as _html
import json
import os
import re
import sqlite3
import sys
import textwrap
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_card  # noqa: E402 - the shared readers (decision_detail)
import crew_result  # noqa: E402 - the one reader of a tool result row (ok|err, reason, output)
import crew_watch  # noqa: E402 - done_report: the done summary the owner is sent, shown on the card page

DEFAULT_STEPS = 6
GAP = 3  # horizontal gap between boxes in a layer band
MAX_BOX_W = 58

ANSI = {
    "running": "\x1b[1;32m",
    "done": "\x1b[1;33m",
    "blocked": "\x1b[1;31m",
    "failed": "\x1b[1;31m",
    "reset": "\x1b[0m",
}

# Status colours for the --html page are tokens, not hex: crew_dashboard/tokens.css decides them.
HTML_COLOURS = {
    "running": "var(--crew-tone-running)",
    "done": "var(--crew-tone-done)",
    "blocked": "var(--crew-tone-blocked)",
    "failed": "var(--crew-tone-blocked)",
    "pending": "var(--crew-tone-neutral)",
}


# ----------------------------------------------------------------- path helpers

def base_home():
    """Return the base Hermes home directory (the parent that holds profiles/)."""
    h = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
    h = os.path.abspath(h)
    # If HERMES_HOME points at a profile home (<base>/profiles/<name>), walk up.
    if os.path.basename(os.path.dirname(h)) == "profiles" and os.path.basename(h) != "profiles":
        return os.path.dirname(os.path.dirname(h))
    return h


def kanban_db_path():
    """The active board's kanban.db, or None: crew_card.kanban_db() is the one resolver."""
    return crew_card.kanban_db()


def profile_home(profile):
    profile = (profile or "").strip()
    if not profile or profile == "default":
        return base_home()
    return os.path.join(base_home(), "profiles", profile)


def state_db_for(profile):
    return os.path.join(profile_home(profile), "state.db")


def discover_state_dbs():
    dbs = []
    base = base_home()
    p = os.path.join(base, "state.db")
    if os.path.isfile(p):
        dbs.append(("default", p))
    pd = os.path.join(base, "profiles")
    if os.path.isdir(pd):
        try:
            names = sorted(os.listdir(pd))
        except Exception:
            names = []
        for name in names:
            p = os.path.join(pd, name, "state.db")
            if os.path.isfile(p):
                dbs.append((name, p))
    return dbs


# ----------------------------------------------------------------- db helpers

def q(db_path, sql, params=()):
    """Run a read-only query; return list of rows, or [] on any failure (never raise)."""
    if not db_path or not os.path.exists(db_path):
        return []
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
        try:
            rows = conn.execute(sql, params).fetchall()
            return rows
        finally:
            conn.close()
    except Exception:
        return []


def qone(db_path, sql, params=()):
    rows = q(db_path, sql, params)
    return rows[0] if rows else None


# ----------------------------------------------------------------- formatting

def fmt_ts(sec):
    if sec is None:
        return "-"
    try:
        return time.strftime("%H:%M:%S", time.localtime(float(sec)))
    except Exception:
        return str(sec)


def fmt_dur(a, b):
    """Duration between two unix timestamps (either may be None)."""
    if a is None:
        return "-"
    if b is None:
        b = time.time()
    try:
        d = float(b) - float(a)
    except Exception:
        return "-"
    if d < 0:
        d = 0.0
    if d < 60:
        return "%.1fs" % d
    m = int(d // 60)
    s = int(d % 60)
    return "%dm%02ds" % (m, s)


# ------------------------------------------------------------------- run reader
def load_session_run(db, session_id):
    """Return (run_id, run_status) for a session, or (None, None).

    The session node only tells us what session ran - the run row (its parent)
    carries the outcome and card ownership. A session left open by a killed
    worker has ended_at=None but its run row already records the real status.
    """
    if not db or not session_id:
        return None, None
    try:
        cur = db.execute(
            "select run_id from task_events where kind=? and payload like ? limit 1",
            ("session", "%" + session_id + "%"))
        row = cur.fetchone()
        if not row:
            return None, None
        rid = row[0]
        rcur = db.execute(
            "select status from task_runs where id=? and task_id in ( "
            "select distinct task_id from task_events where run_id=?)",
            (rid, rid))
        rrow = rcur.fetchone()
        return rid, (rrow[0] if rrow else None)
    except Exception:
        return None, None


def wrap(text, width=MAX_BOX_W - 4, maxlines=2):
    if not text:
        return []
    lines = []
    for ln in str(text).splitlines():
        lines.extend(textwrap.wrap(ln, width) or [""])
    if maxlines and len(lines) > maxlines:
        lines = lines[:maxlines]
        lines[-1] = lines[-1][: width - 1] + "~"
    return lines


def short_args(raw, maxlen=44):
    if not raw:
        return ""
    try:
        obj = json.loads(raw)
    except Exception:
        return str(raw).replace("\n", " ")[:maxlen]
    if isinstance(obj, dict):
        for key in ("command", "query", "path", "url", "text", "goal", "expression", "question"):
            if key in obj and isinstance(obj[key], str):
                return obj[key].replace("\n", " ")[:maxlen]
        parts = []
        for k, v in obj.items():
            if isinstance(v, str):
                parts.append("%s=%s" % (k, v[:22].replace("\n", " ")))
            else:
                try:
                    parts.append("%s=%s" % (k, json.dumps(v)[:22]))
                except Exception:
                    parts.append(k)
            if len(parts) >= 3:
                break
        return (", ".join(parts))[:maxlen]
    if isinstance(obj, str):
        return obj.replace("\n", " ")[:maxlen]
    try:
        return json.dumps(obj)[:maxlen]
    except Exception:
        return ""


# ----------------------------------------------------------------- status

def run_status(status, outcome):
    if status == "running":
        return "running"
    if status == "done" or outcome == "completed":
        return "done"
    if status == "blocked" or outcome == "blocked":
        return "blocked"
    bad = {"crashed", "timed_out", "failed", "released",
           "spawn_failed", "gave_up", "reclaimed"}
    if status in bad or outcome in bad:
        return "failed"
    if status == "running" or outcome is None:
        return "running"
    return "done"


RUNNING_RUN_STATUSES = ("running", "pending", "claimed", "in_progress")


def session_status(ended_at, run_status=None):
    """A session's state for the page: its own RUN decides, ended_at is only the fallback.

    A worker killed outright never writes its session's ended_at, so reading that column alone draws
    a dead session as running for ever - the page kept showing session 20260930_142504_7587cd live
    after its run 2789 had already settled "crashed" (owner, 2026-09-30). When the session has a run
    row, that row is the truth; without one (a subagent session of a run that never started) the
    open/closed column is all there is.
    """
    if run_status is not None:
        return "running" if str(run_status) in RUNNING_RUN_STATUSES else "done"
    return "running" if ended_at is None else "done"


def card_status(tstatus, run_statuses):
    m = {"done": "done", "archived": "done", "blocked": "blocked", "running": "running"}
    if tstatus in m:
        return m[tstatus]
    if run_statuses:
        if "running" in run_statuses:
            return "running"
        if all(s in ("failed", "blocked") for s in run_statuses):
            return "failed"
    return "done"


# ----------------------------------------------------------------- graph build

def load_card(card_id):
    db = kanban_db_path()
    if not db:
        return None, None
    row = qone(db, "select id, title, status, assignee, result, model_override, "
                   "session_id, created_at, started_at, completed_at, block_kind "
                   "from tasks where id = ?", (card_id,))
    return row, db


def body_of(db, card_id):
    """The card's own body text (goal, proof command, done-when), or "" when there is none."""
    try:
        row = qone(db, "select body from tasks where id = ?", (card_id,))
    except Exception:
        return ""
    return (row[0] if row else "") or ""


def load_runs(db, card_id):
    return q(db, "select id, profile, status, outcome, summary, error, started_at, "
                 "ended_at, last_heartbeat_at from task_runs where task_id = ? "
                 "order by id", (card_id,))


def find_session_by_id(session_id):
    for profile, db in discover_state_dbs():
        row = qone(db, "select id, parent_session_id, source, model, title, started_at, "
                       "ended_at, message_count, tool_call_count, input_tokens, "
                       "output_tokens, profile_name from sessions where id = ?",
                   (session_id,))
        if row:
            return profile, db, row
    return None, None, None


def exact_session_for_run(board_db, card_id, run_id):
    """The session a run used, from the worker's own record - not a guess.

    The router plugin's on_session_start hook runs inside the worker process and writes one
    task_events row (kind='session', run_id, {"session": ...}) per run, because the dispatcher exports
    HERMES_KANBAN_TASK into that process. That row is ground truth; everything in find_worker_session
    below it is inference (time window, card id in the messages, nearest start).
    """
    if not board_db or not card_id or run_id is None:
        return None
    try:
        rows = q(board_db, "select run_id, payload from task_events where task_id = ? and kind = 'session' "
                           "order by id desc limit 50", (card_id,))
    except Exception:
        return None
    for rid, payload in rows:
        if run_id is not None and rid != run_id:
            continue
        try:
            data = json.loads(payload or "{}")
        except Exception:
            continue
        if data.get("session"):
            return str(data["session"])
    return None


def find_worker_session(card_row, run_row, card_session_id):
    """Locate the worker session for a run, preferring tasks.session_id, then
    matching a source='kanban' session in the run's profile by time window."""
    run_id, profile, status, outcome, summary, error, rstart, rend, rhb = run_row
    # 1. explicit session id on the card
    if card_session_id:
        prof, db, row = find_session_by_id(card_session_id)
        if row:
            return prof, db, row
    # 2. time-window match in the run profile (then any profile)
    start_lo = (rstart or 0) - 10
    start_hi = (rend or (rstart or 0) + 3600) + 30
    candidates = []
    target_profile = profile or (card_row[3] if card_row else None)
    run_live = not rend
    card_hint = card_row[0] if card_row else None
    for prof, db in discover_state_dbs():
        if target_profile and prof != target_profile:
            continue
        rows = q(db, "select id, parent_session_id, source, model, title, started_at, "
                     "ended_at, message_count, tool_call_count, input_tokens, "
                     "output_tokens, profile_name from sessions "
                     "where source = 'kanban' and started_at >= ? and started_at <= ?",
                 (start_lo, start_hi))
        for row in rows:
            # Several crew sessions can start in the same second, so time alone is not enough.
            # Ground truth first: a session that names this card in its own messages is this
            # card's session. Then the nearest start, then the busiest, then live/done parity.
            hint_miss = 1
            if card_hint:
                hit = q(db, "select count(*) from messages where session_id = ? and content like ?",
                        (row[0], "%" + str(card_hint) + "%"))
                hint_miss = 0 if (hit and hit[0][0]) else 1
            live_mismatch = 0 if (row[6] is None) == run_live else 1
            candidates.append((hint_miss, abs((row[5] or 0) - (rstart or 0)), live_mismatch,
                               -(row[7] or 0), -(row[8] or 0), prof, db, row))
    if candidates:
        candidates.sort(key=lambda c: c[:5])
        _, _, _, _, _, prof, db, row = candidates[0]
        return prof, db, row
    return None, None, None


def load_children(db, session_id):
    if not db or not session_id:
        return []
    return q(db, "select id, parent_session_id, source, model, title, started_at, "
                 "ended_at, message_count, tool_call_count, input_tokens, "
                 "output_tokens, profile_name from sessions "
                 "where parent_session_id = ? order by started_at, id", (session_id,))


def tail_steps(steps, n):
    """The last n steps, plus every step whose result failed.

    A failure must never scroll out of a panel: the last n alone hides an old failed step behind
    newer ok ones, and the reader is then shown a run whose visible steps all say ok. Order is kept.
    """
    steps = list(steps or [])
    if n is None or n <= 0 or len(steps) <= n:
        return steps
    start = len(steps) - n
    return [s for i, s in enumerate(steps) if i >= start or s.get("state") == "err"]


def load_prompt(db, session_id, limit=300):
    """The prompt a session was given: its first user message, one line.

    A session node's reader wants to know what this worker was asked to do; the first user message is
    that, in the worker's own terms, and it is stable for the run.
    """
    if not db or not session_id:
        return ""
    rows = q(db, "select content from messages where session_id = ? and role = 'user' "
                 "and content is not null and content != '' order by timestamp, id limit 1",
             (session_id,))
    return " ".join(str(rows[0][0] or "").split())[:limit] if rows else ""


def _say_text(content, limit=240):
    """The words the assistant wrote in the message that made the call - the live session output.

    This is what a reader watching a running step wants: the sentence before the tool ran, with the
    tool plumbing left out. Collapsed to one line, "" when the message carried no text of its own.
    """
    return " ".join(str(content or "").split())[:limit]


def load_session_text(db, session_id, max_lines=400, max_chars=20000):
    """What the model itself wrote in a session - tool calls and tool results filtered out.

    Owner, 2026-09-30: a step box answers "which tool ran"; the worker box in the panel has to answer
    "what did the model say", live. So this reads only role='assistant' messages that carry text of their
    own: a message that exists to call a tool (content empty) and every role='tool' result are dropped on
    purpose. Returns [{"ts", "text"}] oldest first, capped to the tail so the 2s panel poll stays light.
    """
    if not db or not session_id:
        return []
    rows = q(db, "select content, timestamp from messages where session_id = ? and role = 'assistant' "
                 "order by timestamp, id", (session_id,))
    out = []
    for content, ts in rows:
        text = _say_text(content, limit=max_chars)
        if text:
            out.append({"ts": ts, "text": text})
    out = out[-max_lines:]
    while out and sum(len(r["text"]) for r in out) > max_chars:
        out.pop(0)
    return out


def load_steps(db, session_id, start_ts, ended_at=None):
    """Every tool call of a session as a step, each carrying the state of its own result.

    The state is the one `load_tool_calls` reads (ok|err|pending, by tool_call_id), so a step and the
    chip run it belongs to never disagree; `note` is the result's short reason, `out` the last text its
    own output produced (both "" when the result has nothing to say) and `say` the last words the
    assistant wrote at or before the call.
    """
    if not db or not session_id:
        return []
    results = _tool_results(db, session_id)
    steps = []
    last_say = ""
    rows = q(db, "select tool_calls, timestamp, content from messages where session_id = ? "
                 "and role = 'assistant' and tool_calls is not null "
                 "order by timestamp, id", (session_id,))
    for tc, ts, content in rows:
        try:
            calls = json.loads(tc)
        except Exception:
            calls = []
        # The live output carries forward: most messages carry only tool calls, and a reader watching
        # a running step wants the last words the session wrote, not a bare box.
        own = _say_text(content)
        if own:
            last_say = own
        say = last_say
        if isinstance(calls, list):
            for c in calls:
                fn = ((c or {}).get("function")) or {}
                name = fn.get("name")
                if name:
                    cid = (c or {}).get("id") or (c or {}).get("call_id")
                    state, note, out = results.get(
                        cid, ("pending" if ended_at is None else "ok", "", ""))
                    steps.append({
                        "tool": name,
                        "args": short_args(fn.get("arguments") or ""),
                        "sec": round(ts - start_ts, 1) if start_ts is not None else None,
                        "ts": ts,
                        "state": state,
                        "note": note,
                        "out": out,
                        "say": say,
                    })
    if not steps:
        rows = q(db, "select tool_name, timestamp from messages where session_id = ? "
                     "and tool_name is not null order by timestamp, id", (session_id,))
        for tn, ts in rows:
            steps.append({
                "tool": tn,
                "args": "",
                "sec": round(ts - start_ts, 1) if start_ts is not None else None,
                "ts": ts,
                "state": "ok",
                "note": "",
                "out": "",
                "say": "",
            })
    return steps


def session_row_to_dict(row):
    (sid, parent, source, model, title, started_at, ended_at, message_count,
     tool_call_count, input_tokens, output_tokens, profile_name) = row
    return {
        "id": sid,
        "parent_session_id": parent,
        "source": source,
        "model": model,
        "title": title,
        "started_at": started_at,
        "ended_at": ended_at,
        "message_count": message_count,
        "tool_call_count": tool_call_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "profile_name": profile_name,
    }


# ----------------------------------------------------------------- roles

ROLE_ORDER = ["coordinator", "worker", "content", "verifier"]
ROLE_COLOURS = {
    "coordinator": "#a371f7",
    "worker": "#58a6ff",
    "content": "#f778ba",
    "verifier": "#39c5cf",
}
ROLE_FALLBACK = "var(--crew-tone-neutral)"   # a role with no hue of its own
HERE = os.path.dirname(os.path.abspath(__file__))
DASH_DIR = os.path.join(HERE, "crew_dashboard")


def dashboard_asset(*names):
    """The dashboard CSS/JS files joined, for the page to inline: one self-contained document."""
    out = []
    for name in names:
        with open(os.path.join(DASH_DIR, name), encoding="utf-8") as fh:
            out.append(fh.read())
    return "\n".join(out)


def favicon_link():
    """The tab icon as an inline <link>: the logo mark on a dark tile, shipped beside the CSS and embedded
    like it, so the page stays one self-contained document. The tile keeps the dashboard's tab apart from
    the landing page's, which shows the bare mark (dev/make_favicon.py). A missing file costs the icon,
    never the page."""
    try:
        with open(os.path.join(DASH_DIR, "favicon.svg"), "rb") as fh:
            data = base64.b64encode(fh.read()).decode("ascii")
    except OSError:
        return ""
    return '<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,%s">' % data


def logo_link():
    """The header mark as a link home: the logo mark with no background (mark.svg), embedded
    like the CSS so the page stays one self-contained document, pointing at the overview (/). The SVG
    carries the mark for a dark and a light page (dev/make_favicon.py), so the black ring of the
    on-light variant never disappears into a dark host background. A missing file costs the mark,
    never the page."""
    try:
        with open(os.path.join(DASH_DIR, "mark.svg"), "rb") as fh:
            data = base64.b64encode(fh.read()).decode("ascii")
    except OSError:
        return ""
    return ('<a class="brand" href="/" title="overview" aria-label="crew overview">'
            '<img src="data:image/svg+xml;base64,%s" alt="" width="26" height="26"></a>' % data)


def profile_homes():
    """Every Hermes home that exists: the base home and each <base>/profiles/<name>."""
    base = base_home()
    homes = [base] if os.path.isdir(base) else []
    pd = os.path.join(base, "profiles")
    if os.path.isdir(pd):
        try:
            names = sorted(os.listdir(pd))
        except Exception:
            names = []
        for name in names:
            p = os.path.join(pd, name)
            if os.path.isdir(p):
                homes.append(p)
    return homes


def load_roles():
    """Role definitions from roles.json (installed copy first, then the package source)."""
    env_home = os.path.abspath(os.environ.get("HERMES_HOME") or base_home())
    candidates = [os.path.join(env_home, "roles", "crew", "roles.json"),
                  os.path.join(os.path.dirname(HERE), "roles", "roles.json")]
    candidates += [os.path.join(h, "roles", "crew", "roles.json") for h in profile_homes()]
    data = None
    for path in candidates:
        try:
            with open(path) as fh:
                data = json.load(fh)
            break
        except Exception:
            continue
    by_name = {}
    for r in (data or {}).get("roles", []) if isinstance(data, dict) else []:
        if isinstance(r, dict) and r.get("name"):
            by_name[r["name"]] = r
    out = []
    names = ROLE_ORDER + [n for n in by_name if n not in ROLE_ORDER]
    for name in names:
        r = by_name.get(name, {})
        out.append({
            "name": name,
            "color": ROLE_COLOURS.get(name, ROLE_FALLBACK),
            "purpose": r.get("purpose") or "",
            "artifact": r.get("artifact") or "",
            "proof": r.get("proof") or "",
            "model_class": r.get("model_class") or "",
            "tools_allowed": r.get("tools_allowed") or [],
        })
    return out


def card_role(body, skills_raw):
    """Writer role of a card: the body's 'Role:' line, else a crew-role-* skill, else worker."""
    m = re.search(r"^\s*Role:\s*([A-Za-z]+)", body or "", re.M)
    if m:
        return m.group(1).lower()
    try:
        skills = json.loads(skills_raw) if skills_raw else []
    except Exception:
        skills = []
    for s in skills if isinstance(skills, list) else []:
        if isinstance(s, str) and s.startswith("crew-role-"):
            return s[len("crew-role-"):]
    return "worker"


def body_field(body, key):
    """A `Label: value` line out of a card body, read whatever the label's case.

    The labels are written in upper case by the card writer (`GOAL:`, `COORDINATOR:`), so a reader
    written as `Goal:` matches no card on the board and every reader of it silently falls back
    instead of erroring - one reader, case-insensitive, for every field of a body.
    """
    m = re.search(r"^\s*%s:\s*(.+)$" % re.escape(key), body or "", re.M | re.I)
    return m.group(1).strip() if m else None


def pin_label(model, provider):
    """The model pinned on a card, provider-qualified when the pin names one. "" when unpinned."""
    model = (model or "").strip()
    provider = (provider or "").strip()
    if not model:
        return ""
    return "%s/%s" % (provider, model) if provider else model


def home_roots():
    """Every place a crew ledger or verdict file can live: the base home and each profile home."""
    base = base_home()
    roots = [base]
    profdir = os.path.join(base, "profiles")
    if os.path.isdir(profdir):
        roots += [os.path.join(profdir, n) for n in sorted(os.listdir(profdir))]
    return roots


def load_ledger(card_id):
    """Tokens spent and the ceiling recorded for this card, across all profiles."""
    spent = ceiling = 0
    for home in home_roots():
        for suffix in ("", ".spent"):
            path = os.path.join(home, "crew", "budget", card_id + ".json" + suffix)
            try:
                with open(path) as fh:
                    data = json.load(fh)
            except Exception:
                continue
            spent = max(spent, int(data.get("used") or 0))
            ceiling = max(ceiling, int(data.get("budget") or 0))
    return spent, ceiling


def load_ledger_totals(card_id):
    """Card token totals for the rail block, over every ledger file in every home.

    ceiling = max(budget); used, raw_total and calls are summed over `<card>.json` and
    `<card>.json.spent` in the base home and each profile home (a retry keeps the old ledger as
    `.spent`, and each profile books its own calls, so the card total is the sum).
    """
    ceiling = used = raw = calls = 0
    for home in home_roots():
        for suffix in ("", ".spent"):
            path = os.path.join(home, "crew", "budget", card_id + ".json" + suffix)
            try:
                with open(path) as fh:
                    data = json.load(fh)
            except Exception:
                continue
            try:
                ceiling = max(ceiling, int(data.get("budget") or 0))
                used += int(data.get("used") or 0)
                raw += int(data.get("raw_total") or 0)
                calls += int(data.get("calls") or 0)
            except (TypeError, ValueError, AttributeError):
                continue
    pct = round(100.0 * used / ceiling, 1) if ceiling else 0.0
    return {"ceiling": ceiling, "used": used, "raw_total": raw, "calls": calls, "pct": pct}


def load_block_reason(db, card_id, runs, last_failure_error, tstatus):
    """Plain words for why a card sits in blocked/triage, in the order the board recorded it."""
    if tstatus not in ("blocked", "triage"):
        return "", ""
    for run in reversed(runs or []):
        for text in (run[5], run[4]):
            if text and str(text).strip():
                return str(text).strip(), "run %s" % run[0]
    if last_failure_error:
        return str(last_failure_error).strip(), "task"
    try:
        rows = q(db, "select body from task_comments where task_id = ? order by created_at desc limit 1",
                 (card_id,))
        if rows and rows[0][0]:
            body = " ".join(str(rows[0][0]).split())
            return body[:400], "comment"
    except Exception:
        pass
    return "", ""


def pending_reason(db, card_id, runs):
    """(text, source, recorded_at) of a blocked card's reason, full text, same order as
    load_block_reason: newest run with a summary/error, the task's failure error, the newest comment."""
    for run in reversed(runs or []):
        for text in (run[5], run[4]):
            if text and str(text).strip():
                return str(text).strip(), "run %s" % run[0], (run[7] or run[8] or run[6])
    try:
        rows = q(db, "select last_failure_error from tasks where id = ?", (card_id,))
        if rows and rows[0][0] and str(rows[0][0]).strip():
            return str(rows[0][0]).strip(), "task", None
    except Exception:
        pass
    try:
        rows = q(db, "select body, created_at from task_comments where task_id = ? "
                     "order by created_at desc limit 1", (card_id,))
        if rows and rows[0][0] and str(rows[0][0]).strip():
            return str(rows[0][0]).strip(), "comment", rows[0][1]
    except Exception:
        pass
    return "", "", None


def load_done_report(db, card_id, status):
    """The card's done report (crew_watch.done_report: the text crew sends the owner, minus header and link),
    '' for a card that is not done."""
    if status != "done":
        return ""
    conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        return crew_watch.done_report(conn, db, card_id, time.time())
    except sqlite3.Error:
        return ""
    finally:
        conn.close()


def load_decisions(db, card_id):
    """The coordinator's decisions about this card (`crew_decision` events), oldest first."""
    out = []
    for payload, ts in q(db, "select payload, created_at from task_events where task_id = ? "
                             "and kind = 'crew_decision' order by id", (card_id,)):
        try:
            rec = json.loads(payload or "{}")
        except ValueError:
            continue
        if isinstance(rec, dict):
            rec["ts"] = ts
            out.append(rec)
    return out


def decision_label(rec):
    """One plain line for a coordinator decision, as the timeline shows it."""
    kind = str(rec.get("decision") or "")
    words = {
        "retry": "coordinator retried it", "rescope": "coordinator rescoped it",
        "split": "coordinator split it", "close": "coordinator closed it",
        "verify": "coordinator ran the proof", "abandon": "coordinator abandoned it",
        "ask_owner": "coordinator asked the owner", "error": "coordinator could not decide",
        "owner_close": "the owner closed it",
    }
    if kind == "audit":  # the coordinator's re-run of the proof after completion: pass, or fail with a follow-up
        outcome = str(rec.get("outcome") or "")
        follow = " (follow-up %s)" % rec["followup"] if rec.get("followup") else ""
        words["audit"] = ("coordinator audit failed it" + follow if outcome == "fail" else
                          "coordinator audit: the proof was blocked by Hermes safety, owner asked" + follow
                          if outcome == "blocked" else "coordinator audited it: the proof still passes")
    label = words.get(kind, "coordinator decided: %s" % kind)
    detail = crew_card.decision_detail(rec, 70)
    return "%s: %s" % (label, detail) if detail else label


# ----------------------------------------------------------------- tool calls and chip runs

def _tool_results(db, session_id):
    """Every tool result of a session by tool_call_id: {id: (state, note, out)}. One reader of the
    result rows, shared by the chip runs and by the panel's steps."""
    out = {}
    if not db or not session_id:
        return out
    for tcid, content in q(db, "select tool_call_id, content from messages where session_id = ? "
                               "and role = 'tool' and tool_call_id is not null", (session_id,)):
        out[tcid] = crew_result.result_row(content)
    return out


def load_tool_calls(db, session_id, ended_at):
    """Every tool call of a session in order, each with state pending|ok|err.

    State comes from the matching role='tool' result row (by tool_call_id). A call with no
    result row is pending while the session is open; once the session has ended the messages
    table holds no failure signal for it, so it is treated as ok."""
    if not db or not session_id:
        return []
    results = _tool_results(db, session_id)
    calls = []
    rows = q(db, "select tool_calls, timestamp from messages where session_id = ? "
                 "and role = 'assistant' and tool_calls is not null order by timestamp, id",
             (session_id,))
    for tc, ts in rows:
        try:
            items = json.loads(tc)
        except Exception:
            items = []
        for c in items if isinstance(items, list) else []:
            c = c or {}
            name = (c.get("function") or {}).get("name")
            if not name:
                continue
            cid = c.get("id") or c.get("call_id")
            if cid in results:
                state = results[cid][0]
            else:
                state = "pending" if ended_at is None else "ok"
            calls.append({"tool": name, "ts": ts, "state": state})
    return calls


def tool_runs(calls):
    """Collapse consecutive same-name calls into runs (one chip 'bash x5'). A run is pending
    while any call in it is pending, err if any failed, else ok."""
    runs = []
    for c in calls:
        if runs and runs[-1]["tool"] == c["tool"]:
            r = runs[-1]
            r["count"] += 1
            r["_states"].append(c["state"])
            r["last_ts"] = c["ts"]
        else:
            runs.append({"tool": c["tool"], "count": 1, "_states": [c["state"]], "last_ts": c["ts"]})
    for r in runs:
        st = r.pop("_states")
        r["state"] = "pending" if "pending" in st else ("err" if "err" in st else "ok")
    return runs


MAX_RUNS_KEPT = 12


def tool_fields(calls, fallback_count=0):
    runs = tool_runs(calls)
    return {
        "tool_runs": runs[-MAX_RUNS_KEPT:],
        "tool_run_total": len(runs),
        "tool_count": len(calls) or (fallback_count or 0),
        "last_tool": calls[-1]["tool"] if calls else None,
        "last_ts": calls[-1]["ts"] if calls else None,
    }


def load_progress_units(card_id):
    """Units of work and how many passed, written by crew_card.py progress."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(card_id))
    for home in home_roots():
        path = os.path.join(home, "crew", "progress", safe + ".json")
        try:
            with open(path) as fh:
                data = json.load(fh)
        except Exception:
            continue
        units = data.get("units") or []
        if units:
            return {"total": len(units), "passed": sum(1 for u in units if u.get("pass") is True),
                    "failed": sum(1 for u in units if u.get("pass") is False)}
    return {}


def load_first_pass(card_id):
    """Did an independent check (verifier or coordinator) pass the card on its first run? crew_card.first_pass."""
    return crew_card.first_pass(card_id)


def card_box_fields(card_ev):
    """The card's own fields for the card page. Hand it the CARD node's evidence.

    Never graph["root"]: once a brief is recorded the root IS the brief, and every field below then
    reads empty on every card that has one - role and coordinator go blank on exactly the cards that
    were opened properly. `pin_label` and the card page read the same values. The box renders the
    four only it can show (model, started, the id, the coordinator); the rest stay in the page's json
    for any reader that wants them and are deliberately not drawn twice.
    """
    card_ev = card_ev or {}
    return {
        "card_role": card_ev.get("writer_role"),
        "card_assignee": card_ev.get("assignee") or "",
        "card_model": pin_label(card_ev.get("model_override"), card_ev.get("provider_override")),
        "card_block_kind": card_ev.get("block_kind") or "",
        "card_verifier": card_ev.get("verifier") or "",
        "card_created_at": card_ev.get("created_at"),
        "card_run_count": card_ev.get("run_count") or 0,
        "coordinator": card_ev.get("coordinator") or "",
        "budget": {"spent": card_ev.get("spent") or 0, "ceiling": card_ev.get("ceiling") or 0},
    }


def build_situation(db, card_id, card_row, root_ev, runs):
    """What is happening on this card, why it is not moving, and what has already been done.

    The page has to answer those three questions on its own: a picture of nodes says nothing about
    a card that sits at a ceiling, loops on a broken proof, or finished an hour ago.
    """
    tstatus = card_row[2] if len(card_row) > 2 else ""
    def short(text, limit=200):
        return " ".join(str(text or "").split())[:limit]

    counts = {"done": 0, "running": 0, "blocked": 0, "failed": 0, "queued": 0}
    live = None
    last_done = None
    stops = []
    for r in runs:
        st = run_status(r[2], r[3])
        counts[st if st in counts else "queued"] += 1
        if r[2] == "running":
            live = r
        if st == "done":
            last_done = r
        elif st in ("blocked", "failed") and (r[5] or r[4]):
            stops.append(r)

    children = []
    try:
        for crow in q(db, "select t.id, t.status, t.title from task_links l join tasks t "
                          "on t.id = l.child_id where l.parent_id = ? order by t.id", (card_id,)):
            children.append({"id": crow[0], "status": crow[1], "title": short(crow[2], 60)})
    except Exception:
        pass
    child_done = [c for c in children if c["status"] in ("done", "archived")]
    child_open = [c for c in children if c["status"] not in ("done", "archived")]

    blocked_kids = []
    try:
        for crow in q(db, "select t.id, t.status, t.title from task_links l join tasks t "
                          "on t.id = l.parent_id where l.child_id = ?", (card_id,)):
            blocked_kids.append(crow[0])
    except Exception:
        pass

    why = ""
    # The full pending text for the reason box: untruncated, with where it came from and its age.
    reason, reason_source, reason_ts, reason_actor = "", "", None, "nobody"
    if tstatus in ("blocked", "triage"):
        why = root_ev.get("block_reason") or "blocked without a recorded reason"
        reason_actor = "you"
        reason, reason_source, reason_ts = pending_reason(db, card_id, runs)
        if not reason:
            reason = why
            reason_source = root_ev.get("block_source") or "task"
    elif live is None and tstatus not in ("done", "archived"):
        if stops:
            why = short(stops[-1][5] or stops[-1][4])
            s = stops[-1]
            reason = str(s[5] or s[4]).strip()
            reason_source = "run %s" % s[0]
            reason_ts = s[7] or s[8] or s[6]
        elif child_open:
            why = "waiting on %d open child card(s): %s" % (
                len(child_open), ", ".join(c["id"] for c in child_open[:3]))
            reason = "waiting on %d open child card(s): %s" % (
                len(child_open), ", ".join(c["id"] for c in child_open))
            reason_source = "task"
    reason_age_s = None
    if reason_ts:
        try:
            reason_age_s = max(0, int(time.time() - float(reason_ts)))
        except (TypeError, ValueError):
            reason_age_s = None

    done_now = []
    if last_done is not None:
        done_now.append("run %s (%s): %s" % (last_done[0], last_done[1],
                                             short(last_done[4] or last_done[5], 150)))
    for c in child_done[:3]:
        done_now.append("child %s done: %s" % (c["id"], c["title"]))
    if tstatus == "done" and card_row[4]:
        done_now.insert(0, short(card_row[4], 200))

    if tstatus == "done":
        head = "finished"
    elif tstatus in ("blocked", "triage"):
        head = "stopped - needs you"
    elif live is not None:
        head = "working: run %s on %s" % (live[0], live[1])
    elif tstatus == "archived":
        head = "archived"
    else:
        head = "stalled - no run is live"

    repeat = ""
    # The spin box on the page shows the full reason; `repeat` keeps the short cut for the json.
    repeat_text, repeat_stops = "", 0
    if len(stops) >= 3 and tstatus not in ("done", "archived"):
        repeat = "%d of %d runs stopped on the same reason: %s" % (
            len(stops), len(runs), short(stops[-1][5] or stops[-1][4], 170))
        repeat_text = str(stops[-1][5] or stops[-1][4] or "").strip()
        repeat_stops = len(stops)

    return {
        "headline": head,
        "why": why,
        "reason": reason,
        "reason_source": reason_source,
        "reason_age_s": reason_age_s,
        "reason_actor": reason_actor if reason else "nobody",
        "repeat": repeat,
        "repeat_text": repeat_text,
        "repeat_stops": repeat_stops,
        "runs": len(runs),
        "counts": counts,
        "live_run": ({"id": live[0], "profile": live[1], "started_at": live[6],
                      "heartbeat_at": live[8]} if live is not None else None),
        "done": done_now,
        "children": children,
        "parent": blocked_kids[0] if blocked_kids else "",
        "tokens": {"spent": root_ev.get("spent") or 0, "ceiling": root_ev.get("ceiling") or 0},
        "units": load_progress_units(card_id),
        "first_pass": load_first_pass(card_id),
    }


ROUTE_KINDS = ("route", "reroute", "quota_wall")
ROUTE_MERGE_S = 5          # a reroute and the route row written for the same decision land within a second


def load_route(db, card_id):
    """The model chooser's trail for a card, oldest first: [{ts, kind, provider, model, why, wall_number}].

    `route` is a pick, `reroute` a pick made after a wall, `quota_wall` the wall itself. crew_card writes a
    `route` row AND a `reroute` row for one decision after a wall (apply_route, then the reroute record), so
    the pair is folded into one line: the reroute, which carries the wall it answered."""
    rows = []
    for kind, ts, payload in q(db, "select kind, created_at, payload from task_events where task_id = ? "
                                   "and kind in (%s) order by created_at, id"
                                   % ",".join("?" * len(ROUTE_KINDS)), (card_id,) + ROUTE_KINDS):
        try:
            p = json.loads(payload or "{}")
        except ValueError:
            p = {}
        if not isinstance(p, dict):
            p = {}
        if kind == "quota_wall":
            row = {"ts": ts, "kind": kind, "provider": p.get("provider"), "model": p.get("model"),
                   "why": p.get("reason") or "quota wall", "wall_number": p.get("wall_number")}
        elif kind == "reroute":
            row = {"ts": ts, "kind": kind, "provider": p.get("to_provider"), "model": p.get("to_model"),
                   "why": p.get("why") or "", "wall_number": None,
                   "from": "%s/%s" % (p.get("from_provider") or "", p.get("from_model") or "")}
        else:
            row = {"ts": ts, "kind": kind, "provider": p.get("provider"), "model": p.get("model"),
                   "why": p.get("why") or "", "wall_number": None, "task_class": p.get("task_class")}
        prev = rows[-1] if rows else None
        if (prev and {prev["kind"], kind} == {"route", "reroute"} and prev["model"] == row["model"]
                and abs((ts or 0) - (prev["ts"] or 0)) <= ROUTE_MERGE_S):
            keep = row if kind == "reroute" else prev
            other = prev if keep is row else row
            if not keep.get("task_class") and other.get("task_class"):
                keep["task_class"] = other["task_class"]
            if keep is row:
                rows[-1] = row
            continue
        rows.append(row)
    return rows


def role_last_message(mine):
    """(text, node id) a role's roster row carries: the newest line its sessions wrote, else what its newest
    step said or produced; the node is that lane's newest step-carrying node, which the row opens."""
    stepped = [n for n in mine if n.get("steps") or n.get("text")]
    if not stepped:
        return "", None
    newest = max(stepped, key=lambda n: n.get("last_ts") or n.get("t1") or 0)
    text = ""
    for n in sorted(stepped, key=lambda n: n.get("last_ts") or n.get("t1") or 0, reverse=True):
        lines = n.get("text") or []
        lv = n.get("live") or {}
        text = (lines[-1].get("text") if lines else "") or lv.get("say") or lv.get("out") or ""
        if text:
            break
    return " ".join(str(text).split())[:400], newest["id"]


def build_roles(nodes, roles):
    """Role roster: per role whether it is active, how many nodes it owns, its latest action, and its last
    message with the node that message belongs to (ui-spec section 6)."""
    out = []
    for r in roles:
        name = r["name"]
        mine = [n for n in nodes if n.get("role") == name]
        active = any(n["status"] == "running" for n in mine)
        last_text, last_node = role_last_message(mine)
        last_action, last_ts = "idle", None
        if mine:
            newest = max(mine, key=lambda n: n.get("last_ts") or 0)
            last_ts = newest.get("last_ts")
            ev = newest.get("evidence") or {}
            if newest["kind"] == "verifier" and ev.get("verdict"):
                last_action = "%s rc=%s" % (ev.get("verdict"), ev.get("rc"))
            elif newest["kind"] == "card":
                last_action = "card %s - runs %s" % (newest["status"], ev.get("run_count"))
            else:
                parts = [newest["status"]]
                runs = newest.get("tool_runs") or []
                if runs:
                    parts.append("%s x%d" % (runs[-1]["tool"], runs[-1]["count"]))
                last_action = " - ".join(parts)
        out.append({
            "name": name,
            "color": r["color"],
            "purpose": r["purpose"],
            "artifact": r.get("artifact", ""),
            "proof": r.get("proof", ""),
            "active": active,
            "nodes": len(mine),
            "last_action": last_action,
            "last_ts": last_ts,
            "last_text": last_text,
            "last_node": last_node,
        })
    return out


def profile_role(profile, fallback):
    """Role of a run from its profile: crew-<role> profiles map to <role>, anything else
    keeps the card's writer role."""
    p = (profile or "").strip().lower()
    if p.startswith("crew-") and p[len("crew-"):] in ROLE_ORDER:
        return p[len("crew-"):]
    return fallback


# board event kind -> timeline step kind (other board events are bookkeeping and skipped)
EVENT_KIND = {
    "created": "created",
    "claimed": "claimed",
    "review_requested": "review",
    "completed": "done",
    "blocked": "blocked",
}
MAX_TOOL_EVENTS = 300  # per node, newest kept


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_task_events(db, card_id):
    return q(db, "select kind, created_at, run_id from task_events where task_id = ? "
                 "order by created_at, id", (card_id,))


def linked_children(db, card_id):
    """Cards that branch off this one: linked children whose only parent is this card.
    A child with several parents is a fan-in (close-out) card, not a branch of any one of them."""
    out = []
    for (c,) in q(db, "select child_id from task_links where parent_id = ? order by child_id",
                  (card_id,)):
        ps = {r[0] for r in q(db, "select parent_id from task_links where child_id = ?", (c,))}
        if ps == {card_id}:
            out.append(c)
    return out


def created_parents(db, card_id):
    """The parents a card was created with, from its own created event.

    task_links grows afterwards (the decomposer makes its children parents of the card it
    decomposed, so the card waits for them and then closes them out), which turns an at-creation
    child into a many-parent card and hides it from the single-parent branch rule. The created
    event keeps the original parent, so the card view can still put the child under the card that
    spawned it."""
    try:
        for (payload,) in q(db, "select payload from task_events where task_id = ? and kind = 'created' "
                                "order by created_at, id", (card_id,)):
            try:
                rec = json.loads(payload or "{}")
            except (TypeError, ValueError):
                continue
            ps = rec.get("parents")
            if isinstance(ps, list) and ps:
                return [str(p) for p in ps]
    except Exception:
        return []
    return []


def born_children(db, card_id, known=None):
    """Cards this card was the at-creation parent of, even if task_links later gave them more parents."""
    known = set(known or ())
    out = []
    try:
        rows = q(db, "select distinct task_id from task_events where kind = 'created' "
                     "and payload like '%\"parents\"%' order by task_id")
        for (cid,) in rows:
            if cid == card_id or cid in known:
                continue
            if card_id in created_parents(db, cid):
                if qone(db, "select id from tasks where id = ?", (cid,)):
                    out.append(cid)
    except Exception:
        return []
    return out


def load_brief(db, card_id, body=None):
    """The owner's own words when the crew was invoked, for the card view.

    Recorded as a task_events row (kind='brief') by crew_card.py open --brief. Older cards carry
    no such row, so the card body's Goal field stands in, marked as coming from the card so the
    page never pretends a derived line is a quote."""
    try:
        row = qone(db, "select payload, created_at from task_events where task_id = ? and kind = 'brief' "
                       "order by created_at desc, id desc", (card_id,))
        if row:
            try:
                rec = json.loads(row[0] or "{}")
            except (TypeError, ValueError):
                rec = {}
            text = (rec.get("text") or "").strip()
            if text:
                return {"text": text, "ts": rec.get("ts") or row[1],
                        "source": rec.get("source") or "owner", "by": rec.get("by") or "owner",
                        "origin": rec.get("origin") or ""}
    except Exception:
        pass
    # crew_card.py writes the field as "GOAL:", older cards may say "Goal", so match either
    m = re.search(r"^\s*goal:\s*(.+)$", body or "", re.M | re.I)
    goal = m.group(1).strip() if m else None
    if goal:
        return {"text": goal, "ts": None, "source": "card goal", "by": "card", "origin": ""}
    return None


def decompose_origin(db, card_id):
    """The card whose decomposition created this card, from its own created event.

    The gateway's auto-decomposer records ``{"by": "auto-decomposer", "from_decompose_of": <card>}``
    and links the children to no parent at all, so the link is not in task_links: it is only in the
    event. Reading it here is what lets the card view put such a card where it belongs instead of
    dropping it (it has no single parent, so it is nobody's linked child)."""
    try:
        for (payload,) in q(db, "select payload from task_events where task_id = ? and kind = 'created' "
                                "order by created_at, id", (card_id,)):
            try:
                rec = json.loads(payload or "{}")
            except (TypeError, ValueError):
                continue
            src = rec.get("from_decompose_of")
            if src:
                return src
    except Exception:
        return None
    return None


def spawned_children(db, card_id, known=None):
    """Cards this card spawned by decomposition: their created event names it, and they carry no
    linked parent (or several), so ``linked_children`` cannot see them."""
    known = set(known or ())
    out = []
    try:
        rows = q(db, "select task_id from task_events where kind = 'created' "
                     "and payload like '%from_decompose_of%' order by task_id")
        for (cid,) in rows:
            if cid == card_id or cid in known:
                continue
            if decompose_origin(db, cid) == card_id:
                exists = qone(db, "select id from tasks where id = ?", (cid,))
                if exists:
                    out.append(cid)
    except Exception:
        return []
    return out


def closeout_cards(db, kids):
    """Cards whose parents are all among kids: the close-out of a parallel parent."""
    kset = set(kids)
    cand = set()
    for k in kids:
        for (c,) in q(db, "select child_id from task_links where parent_id = ?", (k,)):
            if c not in kset:
                cand.add(c)
    out = []
    for c in sorted(cand):
        ps = {r[0] for r in q(db, "select parent_id from task_links where child_id = ?", (c,))}
        if ps and ps <= kset:
            out.append(c)
    return out


class _Builder(object):
    """Collects nodes, edges and timeline events for one graph."""

    def __init__(self, steps_n):
        self.steps_n = steps_n
        self.nodes = []
        self.by_id = {}
        self.edges = []
        self.events = []
        self.used_sessions = set()
        self.db = kanban_db_path()

    # -- primitives
    def node(self, nid, kind, label, status, role, evidence, steps=None, **extra):
        if nid in self.by_id:
            return nid
        n = {
            "id": nid, "kind": kind, "label": str(label), "status": status, "role": role,
            "evidence": evidence or {}, "steps": steps or [],
            "tool_runs": [], "tool_run_total": 0, "tool_count": 0,
            "last_tool": None, "last_ts": None, "t0": None, "t1": None,
            "prompt": "", "live": {},
        }
        if steps:
            # What the run is doing right now, off its last step: the tool, its state, the last words
            # the session wrote and the last text its own output produced. One glance, always current.
            last = steps[-1]
            n["live"] = {"tool": last.get("tool"), "state": last.get("state"), "note": last.get("note"),
                         "out": last.get("out"), "say": last.get("say"), "ts": last.get("ts"),
                         "sec": last.get("sec")}
        n.update(extra)
        self.nodes.append(n)
        self.by_id[nid] = n
        return nid

    def edge(self, a, b):
        if not a or not b or a == b:
            return
        for e in self.edges:
            if e["from"] == a and e["to"] == b:
                return
        self.edges.append({"from": a, "to": b})

    def event(self, ts, kind, label, node, **extra):
        t = _num(ts)
        if t is None or not node:
            return
        ev = {"ts": t, "kind": kind, "label": str(label or kind)[:80], "node": node}
        ev.update(extra)
        self.events.append(ev)

    def tool_events(self, calls, nid):
        for c in calls[-MAX_TOOL_EVENTS:]:
            self.event(c.get("ts"), "tool", c.get("tool"), nid, state=c.get("state"))

    # -- sessions
    def find_session(self, card_row, run_row, card_session_id):
        # 0. exact: the worker recorded its own session on the card (task_events kind='session'), so a run
        #    is matched to the right session even when several crew sessions start in the same second.
        sid = exact_session_for_run(self.db, card_row[0] if card_row else None, run_row[0])
        if sid:
            prof, esdb, esrow = find_session_by_id(sid)
            if esrow and esrow[0] not in self.used_sessions:
                return prof, esdb, esrow
        prof, sdb, srow = find_worker_session(card_row, run_row, None)
        if not srow and card_session_id:
            prof, sdb, srow = find_worker_session(card_row, run_row, card_session_id)
        if not srow or srow[0] in self.used_sessions:
            return None
        self.used_sessions.add(srow[0])
        return prof, sdb, srow

    def session_tree(self, parent_nid, sess, role, run_id=None, text=None, run_status=None, card=None):
        prof, sdb, srow = sess
        sd = session_row_to_dict(srow)
        calls = load_tool_calls(sdb, sd["id"], sd["ended_at"])
        ev = {
            "session_id": sd["id"], "model": sd["model"], "source": sd["source"],
            "tool_call_count": sd["tool_call_count"], "input_tokens": sd["input_tokens"],
            "output_tokens": sd["output_tokens"], "message_count": sd["message_count"],
            "duration": fmt_dur(sd["started_at"], sd["ended_at"]), "title": sd["title"],
            "profile_name": sd["profile_name"], "run_id": run_id,
            # over EVERY call, not the kept tail: the panel's Failed count is the run's, not the page's
            "calls_failed": sum(1 for c in calls if c.get("state") == "err"),
        }
        steps = tail_steps(load_steps(sdb, sd["id"], sd["started_at"], sd["ended_at"]), self.steps_n)
        extra = tool_fields(calls, sd["tool_call_count"])
        extra.update(t0=sd["started_at"], t1=sd["ended_at"])
        nid = self.node("session:" + sd["id"], "session", sd["id"],
                        session_status(sd["ended_at"], run_status),
                        role, ev, steps, prompt=load_prompt(sdb, sd["id"]), run_id=run_id,
                        text=load_session_text(sdb, sd["id"]) if text is None else text, card=card, **extra)
        self.edge(parent_nid, nid)
        self.tool_events(calls, nid)
        tree = {"id": nid, "kids": []}
        for child in load_children(sdb, sd["id"]):
            cd = session_row_to_dict(child)
            ccalls = load_tool_calls(sdb, cd["id"], cd["ended_at"])
            cev = {
                "session_id": cd["id"], "model": cd["model"], "source": cd["source"],
                "tool_call_count": cd["tool_call_count"], "input_tokens": cd["input_tokens"],
                "output_tokens": cd["output_tokens"], "message_count": cd["message_count"],
                "duration": fmt_dur(cd["started_at"], cd["ended_at"]), "title": cd["title"],
                "calls_failed": sum(1 for c in ccalls if c.get("state") == "err"),
            }
            cextra = tool_fields(ccalls, cd["tool_call_count"])
            cextra.update(t0=cd["started_at"], t1=cd["ended_at"])
            cnid = self.node("subagent:" + cd["id"], "subagent", cd["id"],
                             session_status(cd["ended_at"]), role, cev,
                             tail_steps(load_steps(sdb, cd["id"], cd["started_at"], cd["ended_at"]), self.steps_n),
                             card=card, **cextra)
            self.edge(nid, cnid)
            self.tool_events(ccalls, cnid)
            tree["kids"].append({"id": cnid, "kids": []})
        return tree

    # -- one card: coordinator -> writer run(s) -> session -> verifier -> close
    def branch(self, card_id, child_trees=None):
        row = qone(self.db, "select id, title, status, assignee, result, model_override, "
                            "session_id, created_at, started_at, completed_at, block_kind, "
                            "body, skills, last_failure_error, provider_override from tasks "
                            "where id = ?", (card_id,))
        if not row:
            return None
        (cid, title, tstatus, assignee, result, model_override, card_session_id, created_at,
         started_at, completed_at, block_kind, body, skills, last_failure_error,
         provider_override) = row
        card_row = row[:11]
        runs = load_runs(self.db, cid)
        self.runs = runs
        writer_role = card_role(body, skills)
        cstatus = card_status(tstatus, [run_status(r[2], r[3]) for r in runs])
        card_ev = {
            "assignee": assignee, "result": result, "model_override": model_override,
            "provider_override": provider_override,
            "status": tstatus, "block_kind": block_kind, "created_at": created_at,
            "run_count": len(runs), "writer_role": writer_role,
            "coordinator": body_field(body, "Coordinator"),
            "verifier": body_field(body, "Verifier"),
            "done_when": body_field(body, "Done when"),
            "spent": load_ledger(cid)[0], "ceiling": load_ledger(cid)[1],
            "decisions": load_decisions(self.db, cid),
            "block_reason": load_block_reason(self.db, cid, runs, last_failure_error, tstatus)[0],
            "block_source": load_block_reason(self.db, cid, runs, last_failure_error, tstatus)[1],
        }
        closed = tstatus in ("done", "archived", "blocked")
        card_nid = self.node("card:" + cid, "card", cid, cstatus, "coordinator", card_ev,
                             title=title, t0=created_at,
                             t1=(completed_at or started_at or created_at) if closed else None,
                             last_ts=completed_at or started_at or created_at)

        run_node = {}
        writer_trees = []
        ver_runs = []
        last_writer = last_review = None
        prev_outcome = None
        single = card_session_id if len(runs) == 1 else None
        for r in runs:
            run_id, profile, rstatus, outcome, summary, error, rstart, rend, rhb = r
            is_ver = profile == "crew-verifier" or prev_outcome == "review_requested"
            prev_outcome = outcome
            sess = self.find_session(card_row, r, single)
            # The session's own words, read once and carried by both the run node and its session node: a
            # reader who clicks the worker gets the same live text as the flow box above it.
            rtext = load_session_text(sess[1], sess[2][0]) if sess else []
            if is_ver:
                ver_runs.append((r, sess))
                continue
            role = profile_role(profile, writer_role)
            rev = {
                "run_id": run_id, "profile": profile, "outcome": outcome, "summary": summary,
                "error": error, "last_heartbeat": rhb, "duration": fmt_dur(rstart, rend),
                "started_at": rstart, "ended_at": rend,
            }
            rnid = self.node("run:%s" % run_id, "run", run_id, run_status(rstatus, outcome), role,
                             rev, t0=rstart, t1=rend, last_ts=rend or rhb or rstart, text=rtext,
                             card=cid)
            run_node[run_id] = rnid
            self.edge(card_nid, rnid)
            tree = {"id": rnid, "kids": []}
            if sess:
                tree["kids"].append(self.session_tree(rnid, sess, role, run_id=run_id, text=rtext,
                                                      run_status=run_status(rstatus, outcome),
                                                      card=cid))
            writer_trees.append(tree)
            last_writer = rnid
            if outcome == "review_requested":
                last_review = rnid
        handoff = last_review or last_writer

        # one verifier node per card: the verdict record(s) plus every review run, folded
        verdicts = crew_card.all_verdicts(cid)
        board_events = load_task_events(self.db, cid)
        claims = [ts for kind, ts, _ in board_events if kind == "claimed"]
        vnid = None
        if verdicts or ver_runs or body_field(body, "Verifier"):
            # the chip is the line the close rule ends on: the newest verdict since the newest claim
            since = crew_card.verdict_lines(cid, max(claims) if claims else None, verdicts)
            last = since[-1] if since else None
            calls, steps, vruns, vprompt = [], [], [], ""
            t0s, t1s, alive = [], [], False
            for r, sess in ver_runs:
                run_id, profile, rstatus, outcome, summary, error, rstart, rend, rhb = r
                st = run_status(rstatus, outcome)
                alive = alive or st == "running"
                t0s.append(rstart)
                t1s.append(rend)
                item = {"run_id": run_id, "profile": profile, "outcome": outcome,
                        "duration": fmt_dur(rstart, rend), "summary": summary}
                if sess:
                    _, sdb, srow = sess
                    sd = session_row_to_dict(srow)
                    item["session_id"] = sd["id"]
                    calls += load_tool_calls(sdb, sd["id"], sd["ended_at"])
                    steps = tail_steps(load_steps(sdb, sd["id"], sd["started_at"], sd["ended_at"]), self.steps_n) or steps
                    vprompt = load_prompt(sdb, sd["id"])
                    for child in load_children(sdb, sd["id"]):
                        cd = session_row_to_dict(child)
                        calls += load_tool_calls(sdb, cd["id"], cd["ended_at"])
                vruns.append(item)
            for v in verdicts:
                t0s.append(v.get("ts"))
                t1s.append(v.get("ts"))
            calls.sort(key=lambda c: c.get("ts") or 0)
            vev = {
                "done_when": body_field(body, "Done when"),
                "command": (last or {}).get("command") or body_field(body, "proof command"),
                "rc": (last or {}).get("rc"),
                "verdict": (last or {}).get("verdict") or "unverified",
                "by": crew_card.verdict_by(last) if last else "",
                "output_head": (last or {}).get("output_head"),
                "ts": (last or {}).get("ts"),
                "duration_s": (last or {}).get("duration_s"),
                "verdict_count": len(verdicts),
                "file": last.get("_file") if last else None,
                "review_runs": vruns,
            }
            if alive:
                vstatus = "running"
            elif last:
                vstatus = "done" if (last.get("verdict") == "PASS" and last.get("rc") == 0) else "failed"
            else:
                vstatus = "pending"
            t0v = [t for t in (_num(x) for x in t0s) if t is not None]
            t0 = min(t0v) if t0v else None
            t1v = [t for t in (_num(x) for x in t1s) if t is not None]
            extra = tool_fields(calls, len(calls))
            if last and not calls:
                extra.update(tool_runs=[{"tool": "proof", "count": 1,
                                         "state": "ok" if vstatus == "done" else "err",
                                         "last_ts": last.get("ts")}],
                             tool_run_total=1, tool_count=1, last_tool="proof")
            extra.update(t0=t0, t1=None if alive else (max(t1v) if t1v else None),
                         last_ts=max(t1v) if t1v else extra.get("last_ts"))
            vnid = self.node("verify:" + cid, "verifier", cid, vstatus, "verifier", vev, steps,
                             prompt=vprompt, **extra)
            self.edge(handoff or card_nid, vnid)
            for r, _ in ver_runs:
                run_node[r[0]] = vnid
            self.tool_events(calls, vnid)
            for v in verdicts:
                self.event(v.get("ts"), "verdict", "%s rc=%s" % (v.get("verdict"), v.get("rc")), vnid)

        # the card goes back to the coordinator to close (done) or hand to a human (blocked)
        close_nid = None
        if closed:
            end_ts = None
            for kind, ts, _ in board_events:
                if kind in ("completed", "blocked"):
                    end_ts = ts
            end_ts = end_ts or completed_at
            close_nid = self.node("close:" + cid, "close", cid,
                                  "blocked" if tstatus == "blocked" else "done", "coordinator",
                                  {"status": tstatus, "result": result, "completed_at": completed_at},
                                  t0=end_ts, t1=end_ts, last_ts=end_ts)
            self.edge(vnid or handoff or card_nid, close_nid)

        for kind, ts, run_id in board_events:
            k = EVENT_KIND.get(kind)
            if not k:
                continue
            if k == "created":
                nid = card_nid
            elif k == "done":
                nid = close_nid or vnid or card_nid
            else:
                nid = run_node.get(run_id) or card_nid
            label = "%s %s" % (kind.replace("_", " "), cid)
            if run_id:
                label += " run %s" % run_id
            self.event(ts, k, label, nid)

        tree = {"id": card_nid, "kids": list(writer_trees) + list(child_trees or [])}
        chain = None
        if vnid:
            chain = {"id": vnid, "kids": [{"id": close_nid, "kids": []}] if close_nid else []}
        elif close_nid:
            chain = {"id": close_nid, "kids": []}
        if chain:
            chain["drop"] = 1 if writer_trees else 0
            tree["kids"].append(chain)
        return tree


def build_graph(card_ref, steps_n=DEFAULT_STEPS):
    """Return (graph, error). The graph is the process flow of one card, rooted at the
    coordinator; a parent card also carries its linked children and close-out as branches."""
    if card_ref == "latest":
        card_ref = latest_card_id()

    card_row, db = load_card(card_ref)
    if not card_row:
        return None, "card not found: %s" % card_ref
    card_id, title = card_row[0], card_row[1]

    kids = linked_children(db, card_id)
    # A card that has not run yet still gets a page: the card node alone, flagged pending, with
    # the missing run named as the reason. Only an unknown id is an error (404 upstream).
    pending = not load_runs(db, card_id) and not kids

    b = _Builder(steps_n)
    child_trees = []
    # where a card belongs in the tree: its linked children, the children it spawned by
    # decomposition, and the children it was the at-creation parent of (later links may have
    # turned those into many-parent cards, which the single-parent rule alone would drop)
    extra_kids = spawned_children(db, card_id, known=kids) + born_children(db, card_id, known=kids)
    kids = kids + [k for k in extra_kids if k not in kids]
    for k in kids + closeout_cards(db, kids):
        t = b.branch(k)
        if t:
            child_trees.append(t)
            b.edge("card:" + card_id, t["id"])
    card_tree = b.branch(card_id, child_trees)
    if not card_tree:
        return None, "card has no graph: %s" % card_id
    card_nid = card_tree["id"]
    # the owner's brief sits on top of the coordinator card, so the page tells the whole story
    # from the /crew invocation to the close-out; a card with no recorded brief keeps the
    # coordinator as its root
    brief = load_brief(db, card_id, body_of(db, card_id))
    root = card_nid
    if brief:
        bnid = b.node("brief:" + card_id, "brief", card_id, "done", "owner",
                      {"brief": brief, "text": brief.get("text"), "source": brief.get("source"),
                       "by": brief.get("by"), "origin": brief.get("origin")},
                      None, title="owner brief", brief=brief,
                      t0=brief.get("ts"), t1=brief.get("ts"), last_ts=brief.get("ts"))
        b.edge(bnid, card_nid)
        root = bnid
        card_tree = {"id": bnid, "kids": [card_tree]}
    tree = card_tree

    # the owner's brief, then the coordinator root, are drawn first
    nodes = [b.by_id[root]] + [n for n in b.nodes if n["id"] != root]
    edges = b.edges
    root_ev = b.by_id[card_nid]["evidence"]
    for rec in root_ev.get("decisions") or []:
        b.events.append({"ts": rec.get("ts") or 0, "kind": "decision", "label": decision_label(rec), "node": root})
    b.events.sort(key=lambda e: e.get("ts") or 0)
    for n in nodes:
        if n.get("last_ts") is None:
            n["last_ts"] = n.get("t1") or n.get("t0")
        n["role_color"] = ROLE_COLOURS.get(n["role"], ROLE_FALLBACK)
    layout_flow(tree, nodes)
    b.events.sort(key=lambda e: e["ts"])

    graph = {
        "generated_at": time.time(),
        "generated_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "card_id": card_id,
        "card_title": title,
        "card_status": card_row[2] if len(card_row) > 2 else "",
        # Read off the CARD node, never off the root: with a brief recorded the root is the brief.
        **card_box_fields(root_ev),
        "tokens": load_ledger_totals(card_id),
        "situation": build_situation(b.db, card_id, card_row, root_ev, b.runs),
        "report": load_done_report(b.db, card_id, card_row[2] if len(card_row) > 2 else ""),
        "root": root,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "layout": "flow-tree",
        "nodes": nodes,
        "edges": edges,
        "events": b.events,
        "roles": build_roles(nodes, load_roles()),
        "route": load_route(b.db, card_id),
    }
    if pending:
        not_run = "card %s has not run yet - no run rows; it waits for the dispatcher (status %s)" % (
            card_id, graph["card_status"] or "-")
        sit = graph["situation"]
        sit["pending"] = True
        if graph["card_status"] not in ("blocked", "triage"):
            sit["headline"] = "not run yet - waiting for dispatch"
        if not str(sit.get("reason") or "").strip():
            sit["reason"] = not_run
            sit["reason_source"] = "task"
            sit["reason_actor"] = "dispatcher"
        if not str(sit.get("why") or "").strip():
            sit["why"] = not_run
        graph["pending"] = True
        graph["pending_reason"] = not_run
        graph["runs"] = []
    return graph, None


def latest_card_id():
    db = kanban_db_path()
    if not db:
        return None
    row = qone(db, "select id from tasks where id in (select distinct task_id from task_runs) "
                   "order by created_at desc limit 1")
    if row:
        return row[0]
    row = qone(db, "select id from tasks order by created_at desc limit 1")
    return row[0] if row else None


def recent_cards(n):
    """Return the n most recent cards as dicts (id, status, title, run_count, assignee)."""
    db = kanban_db_path()
    if not db:
        return []
    rows = q(db, "select t.id, t.status, t.title, t.assignee, "
                 "(select count(*) from task_runs r where r.task_id = t.id) as rc "
                 "from tasks t order by t.created_at desc limit ?", (n,))
    out = []
    for r in rows:
        out.append({"id": r[0], "status": r[1], "title": r[2] or "", "assignee": r[3] or "", "runs": r[4]})
    return out


def list_recent(n):
    db = kanban_db_path()
    if not db:
        print("no kanban database found")
        return 0
    for c in recent_cards(n):
        print("%s  %-9s  runs=%-3s %s" % (c["id"], c["status"], c["runs"], c["title"][:60]))
    return 0


# ----------------------------------------------------------------- flow layout

def layout_flow(tree, nodes):
    """Tidy tree layout on the flow tree. Every subtree owns a disjoint column range, so two
    branches never share a column and nodes in one row never overlap. A node sits centred over
    its subtree; "drop" pushes a subtree down extra rows (the verifier chain sits one row below
    the writer run it follows). Sets n["layer"] (row) and n["x"] (column centre, may be .5)."""
    by_id = {n["id"]: n for n in nodes}
    placed = set()

    def place(t, layer, start):
        layer += t.get("drop", 0)
        x = start
        for k in t.get("kids") or []:
            if k and k.get("id") in by_id:
                x += place(k, layer + 1, x)
        width = max(1, x - start)
        n = by_id[t["id"]]
        n["layer"] = layer
        n["x"] = start + (width - 1) / 2.0
        placed.add(t["id"])
        return width

    width = place(tree, 0, 0) if tree and tree.get("id") in by_id else 0
    for n in nodes:
        if n["id"] not in placed:
            n["layer"] = 0
            n["x"] = float(width)
            width += 1


# ----------------------------------------------------------------- terminal render

def _box(title, lines):
    body = [title] + list(lines)
    width = max(len(l) for l in body) if body else 2
    width = min(max(width, 2), MAX_BOX_W)
    out = []
    top = "\u250c" + "\u2500" * (width + 2) + "\u2510"
    out.append(top)
    for l in body:
        l = l[:width]
        out.append("\u2502 " + l + " " * (width - len(l)) + " \u2502")
    out.append("\u2514" + "\u2500" * (width + 2) + "\u2518")
    return out


def _node_lines(node, steps_n):
    kind = node["kind"]
    ev = node["evidence"]
    status = node["status"]
    lines = []
    if kind == "brief":
        br = ev.get("brief") or {}
        lines.append("source=%s  at=%s" % (br.get("source") or "owner",
                                           fmt_ts(br.get("ts")) if br.get("ts") else "-"))
        for ln in wrap(br.get("text") or "", width=MAX_BOX_W - 4, maxlines=3):
            lines.append(ln)
        return lines
    if kind == "card":
        title = node.get("title") or ev.get("result") or ""
        lines.append("status=%s  role=coordinator  runs=%s" % (status, ev.get("run_count")))
        if ev.get("coordinator"):
            lines.append("opened by: %s" % ev["coordinator"])
        if ev.get("writer_role"):
            lines.append("last holder: %s" % ev["writer_role"])
        if ev.get("model_override"):
            lines.append("worker model: %s%s" % (ev["model_override"],
                                                (" via " + ev["provider_override"])
                                                if ev.get("provider_override") else ""))
        if ev.get("ceiling"):
            lines.append("tokens: %s of %s" % (format(ev.get("spent") or 0, ","),
                                               format(ev.get("ceiling"), ",")))
        if ev.get("block_reason"):
            wait = {"needs_input": "waiting for you", "capability": "waiting for a capability",
                    "transient": "transient failure", "dependency": "waiting for a parent card"}
            lines.append("why blocked: %s" % wait.get(ev.get("block_kind") or "", "blocked"))
            for ln in wrap(ev["block_reason"], width=MAX_BOX_W - 4, maxlines=3):
                lines.append(ln)
        for ln in wrap(node.get("title") or "", maxlines=2):
            lines.append(ln)
        if ev.get("result"):
            lines.append("result: " + (ev["result"] or "")[:MAX_BOX_W - 9])
    elif kind == "run":
        lines.append("status=%s  outcome=%s" % (status, ev.get("outcome") or "-"))
        lines.append("profile=%s  dur=%s" % (ev.get("profile") or "-", ev.get("duration")))
        if ev.get("last_heartbeat"):
            lines.append("heartbeat=%s" % fmt_ts(ev.get("last_heartbeat")))
        if ev.get("error"):
            lines.append("err: " + (ev["error"] or "")[:MAX_BOX_W - 6])
    elif kind == "verifier":
        lines.append("%s  rc=%s  dur=%ss  verdicts=%s  review runs=%s" % (
            ev.get("verdict") or "unverified", ev.get("rc"), ev.get("duration_s"),
            ev.get("verdict_count") or 0, len(ev.get("review_runs") or [])))
        for i, ln in enumerate(wrap("cmd: " + (ev.get("command") or "-"), width=MAX_BOX_W - 4, maxlines=2)):
            lines.append(ln)
        head = (ev.get("output_head") or "").strip().splitlines()
        if head:
            lines.append("out: " + head[0][:MAX_BOX_W - 9])
        if ev.get("done_when"):
            lines.append("done when: " + ev["done_when"][:MAX_BOX_W - 15])
    elif kind == "close":
        lines.append("status=%s  closed=%s" % (ev.get("status"), fmt_ts(node.get("t1"))))
    elif kind == "session" or kind == "subagent":
        lines.append("%s  model=%s" % (status, ev.get("model") or "-"))
        lines.append("tools=%s msgs=%s in=%s out=%s" % (
            ev.get("tool_call_count") or 0, ev.get("message_count") or 0,
            ev.get("input_tokens") or 0, ev.get("output_tokens") or 0))
        lines.append("dur=%s" % ev.get("duration"))
        for s in node["steps"][-steps_n:]:
            sec = ("t+%.1fs" % s["sec"]) if s.get("sec") is not None else "t+?"
            args = s["args"]
            line = "%s %s %s" % (sec, s["tool"], args)
            lines.append("  " + line[:MAX_BOX_W - 4])
    return lines


def _label_for(kind, label):
    if kind == "brief":
        return "OWNER BRIEF"
    if kind == "card":
        return "CARD " + str(label)
    if kind == "run":
        return "RUN #%s" % label
    if kind == "session":
        return "SESSION %s" % short_session_label(label)
    if kind == "subagent":
        return "SUBAGENT %s" % short_session_label(label)
    if kind == "verifier":
        return "VERIFY %s" % label
    if kind == "close":
        return "CLOSE %s" % label
    return "%s %s" % (kind.upper(), label)


def short_session_label(sid):
    sid = str(sid)
    return sid if len(sid) <= 16 else sid[:8] + ".." + sid[-6:]


def _band(items):
    # items: list of (box_lines, ansi_colour_or_empty)
    heights = [len(b) for b, _ in items]
    h = max(heights) if heights else 0
    rows = []
    for r in range(h):
        row = ""
        for i, (b, col) in enumerate(items):
            line = b[r] if r < len(b) else " " * len(b[0])
            if col:
                line = col + line + ANSI["reset"]
            row += line
            if i < len(items) - 1:
                row += " " * GAP
        rows.append(row.rstrip())
    return rows


def _col_centers(boxes):
    centers = []
    x = 0
    for b in boxes:
        w = len(b[0])
        centers.append(x + w // 2)
        x += w + GAP
    return centers


def _connector(prev_boxes, prev_ids, curr_boxes, curr_ids, edges):
    """Draw a 3-row orthogonal connector band between two consecutive layers."""
    child_to_parent = {}
    for e in edges:
        if e["to"] in curr_ids and e["from"] in prev_ids:
            child_to_parent[e["to"]] = e["from"]
    if not child_to_parent:
        return []
    pc = _col_centers(prev_boxes)
    cc = _col_centers(curr_boxes)
    width = max(pc + cc) + 1 if (pc or cc) else 0
    grid = [[" "] * width for _ in range(3)]
    parent_children = {}
    for ci, cid in enumerate(curr_ids):
        pid = child_to_parent.get(cid)
        if pid:
            parent_children.setdefault(pid, []).append(ci)
    for pi, pid in enumerate(prev_ids):
        if pid not in parent_children:
            continue
        child_idxs = parent_children[pid]
        child_cols = [cc[ci] for ci in child_idxs]
        lo = min([pc[pi]] + child_cols)
        hi = max([pc[pi]] + child_cols)
        for x in range(lo, hi + 1):
            if grid[1][x] == " ":
                grid[1][x] = "\u2500"
        left = any(c < pc[pi] for c in child_cols)
        right = any(c > pc[pi] for c in child_cols)
        if left and right:
            grid[1][pc[pi]] = "\u2534"
        elif right:
            grid[1][pc[pi]] = "\u2514"
        elif left:
            grid[1][pc[pi]] = "\u2518"
        else:
            grid[1][pc[pi]] = "\u2502"
        grid[0][pc[pi]] = "\u2502"
        for ci in child_idxs:
            ccol = cc[ci]
            if ccol == pc[pi]:
                grid[1][ccol] = "\u253c" if (left or right) else "\u2502"
            elif ccol > pc[pi]:
                grid[1][ccol] = "\u2510"
            else:
                grid[1][ccol] = "\u250c"
            grid[2][ccol] = "\u2502"
    return ["".join(r).rstrip() for r in grid]


def render_terminal(graph, colour, steps_n):
    layers = {}
    for n in graph["nodes"]:
        layers.setdefault(n["layer"], []).append(n)
    maxlayer = max(layers.keys()) if layers else 0

    out = []
    out.append("crew flow graph - card %s - %s" % (graph["card_id"], graph["card_title"][:70]))
    out.append("rendered %s - %d nodes, %d edges" % (
        time.strftime("%H:%M:%S"), graph["node_count"], graph["edge_count"]))
    sit = graph.get("situation") or {}
    if sit:
        c = sit.get("counts") or {}
        out.append("state: %s - %s (%d runs: %d done, %d blocked, %d failed, %d running)" % (
            graph.get("card_status") or "-", sit.get("headline") or "-", sit.get("runs") or 0,
            c.get("done", 0), c.get("blocked", 0), c.get("failed", 0), c.get("running", 0)))
        if sit.get("why"):
            out.append("why: %s" % sit["why"][:150])
        for d in (sit.get("done") or [])[:2]:
            out.append("done: %s" % d[:150])
        un = sit.get("units") or {}
        if un.get("total"):
            out.append("units: %d of %d passed" % (un.get("passed", 0), un["total"]))
        fp = sit.get("first_pass") or {}
        if fp.get("rounds"):
            out.append("verification: %s (%d fail(s) before first pass, %d rounds)" % (
                "passed first try" if fp.get("first_pass") else ("needed rework" if fp.get("passes") else "check failed"),
                fp.get("fails", 0), fp["rounds"]))
    roster = []
    for r in graph.get("roles") or []:
        roster.append("%s%s(%d: %s)" % (r["name"], "*" if r.get("active") else "",
                                        r.get("nodes", 0), r.get("last_action", "idle")))
    if roster:
        out.append("roles: " + "  ".join(roster))
    out.append("")

    prev = None
    for l in range(maxlayer + 1):
        lyr = sorted(layers.get(l, []), key=lambda n: n["x"])
        boxes = []
        ids = []
        for n in lyr:
            title = "[%s] %s" % (n.get("role", "?"), _label_for(n["kind"], n["label"]))
            lines = _node_lines(n, steps_n)
            boxes.append(_box(title, lines))
            ids.append(n["id"])
        if prev is not None:
            for r in _connector(prev["boxes"], prev["ids"], boxes, ids, graph["edges"]):
                out.append(r)
        items = []
        for i, n in enumerate(lyr):
            col = ANSI.get(n["status"], "") if colour else ""
            items.append((boxes[i], col))
        for r in _band(items):
            out.append(r)
        prev = {"boxes": boxes, "ids": ids}
        out.append("")

    legend = "  ".join("%s%s%s" % (ANSI[k] if colour else "", k, ANSI["reset"] if colour else "")
                       for k in ("running", "done", "failed"))
    out.append("legend: %s" % legend)
    out.append("status read from colour; --json / --html for machine + live views")
    return "\n".join(out)


# ----------------------------------------------------------------- json / html

def render_json(graph):
    return json.dumps(graph, indent=2, ensure_ascii=False)


def _js_safe(s):
    s = json.dumps(s, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _tok_fields(tok):
    """Exact figures for the rail token block: thousands separators, never k/M."""
    tok = tok or {}
    return {"tok_ceiling": format(int(tok.get("ceiling") or 0), ","),
            "tok_used": format(int(tok.get("used") or 0), ","),
            "tok_raw": format(int(tok.get("raw_total") or 0), ","),
            "tok_calls": format(int(tok.get("calls") or 0), ","),
            "tok_pct": "%.1f%%" % float(tok.get("pct") or 0.0)}


def _brief_fields(graph):
    """The brief block in the rail: the exact words the coordinator was given, never re-worded."""
    brief = None
    for n in graph.get("nodes") or []:
        if n.get("kind") == "brief":
            brief = n.get("brief") or {}
            break
    if not brief or not (brief.get("text") or "").strip():
        return {"brief_text": "", "brief_src": "", "brief_hidden": "hidden"}
    src = brief.get("source") or "owner"
    when = fmt_ts(brief.get("ts")) if brief.get("ts") else ""
    if src == "owner":
        label = "the owner's words when /crew was called"
    elif src == "card goal":
        label = "the card's own GOAL line - no brief was recorded"
    else:
        label = "source: %s" % src
    return {"brief_text": _html.escape(brief["text"].strip()),
            "brief_src": _html.escape("%s%s%s" % (label, " - " if when else "", when)),
            "brief_hidden": ""}


def render_html(graph, json_filename, nonce=None):
    # nonce: the serving process's per-response CSP nonce, set on every inline <script>; a standalone
    # --html file has no CSP and passes none.
    initial = _js_safe(graph)
    card_id = graph.get("card_id") or ""
    title = _html.escape("crew graph - " + card_id)

    css = dashboard_asset("tokens.css", "crew.css")
    js = dashboard_asset("lib.js", "card.js")

    html_doc = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{favicon}
<style>{css}</style>
</head>
<body class="page-card" data-card="%(card_id)s">
{brand}
<div id="event"></div>
<div id="main">
  <div id="toparea">
    <div class="tcell" id="topSit">
      <div class="tch">card</div>
      <div id="sit" class="sit"></div>
      <div id="sitfields" class="fields"></div>
    </div>
    <div class="tcell" id="topWhy">
      <div class="tch" id="whyHead">pending reason</div>
      <div class="tce" id="sitboxNone">nothing pending</div>
      <div id="sitbox" hidden>
        <div id="sitboxHead"><span class="sbl"></span><span class="sb"></span><button id="sitCopy" class="copy" type="button" title="copy the pending reason">copy</button></div>
        <div id="sitboxWhy"></div>
        <div id="sitboxMeta"></div>
      </div>
    </div>
    <div class="tcell" id="topSpin">
      <div class="tch">repeated stops</div>
      <div class="tce" id="spinboxNone">not spinning</div>
      <div id="spinbox" hidden>
        <div id="spinboxHead"><span id="spinboxCount"></span><span class="sbl">spinning</span><button id="spinCopy" class="copy" type="button" title="copy the repeated reason">copy</button></div>
        <div id="spinboxText"></div>
      </div>
    </div>
  </div>
  <!-- the role filters as one horizontal strip under the top boxes (owner, 2026-10-01): click a role to
       focus its nodes, "all roles" or esc for everything; each role carries its last message, which
       opens that lane's newest step -->
  <div id="rolestrip"><div id="roster"></div></div>
  <div id="row">
  <div id="rail">
    <div id="toksec">
      <div class="rh">tokens</div>
      <div class="tokrow" id="tokCeiling"><span class="tk">ceiling</span><span class="tv">{tok_ceiling}</span></div>
      <div class="tokrow" id="tokUsed"><span class="tk">used (billed)</span><span class="tv">{tok_used}</span></div>
      <div class="tokrow" id="tokRaw"><span class="tk">raw total</span><span class="tv">{tok_raw}</span></div>
      <div class="tokrow" id="tokCalls"><span class="tk">api calls</span><span class="tv">{tok_calls}</span></div>
      <div class="tokrow" id="tokPct"><span class="tk">of ceiling</span><span class="tv">{tok_pct}</span></div>
    </div>
    <div id="briefsec" {brief_hidden}>
      <div class="rh">brief</div>
      <div id="briefText">{brief_text}</div>
      <div id="briefSrc">{brief_src}</div>
    </div>
    <div class="rback"><a class="railbtn" href="/" title="back to the board">\u2039<span class="rbtnlabel"> board</span></a></div>
    <div class="rbot">
      <button class="railbtn tog" id="railBot" title="collapse the sidebar">\u2039</button>
    </div>
  </div>
  <div id="stage"><div id="world"><svg id="edges"></svg><div id="nodes"></div></div>
    <canvas id="minimap" width="200" height="130"></canvas><div id="zoomlbl"></div></div>
  <div id="panel"></div>
  </div>
</div>
<div id="scrubwrap"><div id="scrubber"></div></div>
<div id="statusbar">
  <span class="pill">crew</span>
  <span class="live" id="live">LIVE</span>
  <span class="cardtitle" id="cardtitle"></span>
  <span class="pill" id="ractive"></span>
  <span class="pill btn" id="followbtn">follow off</span>
  <span class="meta">
    <span id="counts"></span>
    <a href="/">overview</a>
    <span class="hints">space pause - r refresh - f or double-click fit - 0 zoom - F follow - ? help - o overview</span>
  </span>
</div>
<div id="help">
  <div class="h">keys</div>
  <div class="row"><kbd>space</kbd>pause / resume polling</div>
  <div class="row"><kbd>r</kbd>refresh once</div>
  <div class="row"><kbd>f</kbd>fit view</div>
  <div class="row"><kbd>0</kbd>reset zoom</div>
  <div class="row"><kbd>F</kbd>follow the newest active node</div>
  <div class="row"><kbd>wheel</kbd>zoom - <kbd>drag</kbd>pan - zoomed out, cards become status blocks</div>
  <div class="row"><kbd>?</kbd>toggle this help</div>
  <div class="row"><kbd>o</kbd>open overview</div>
  <div class="row"><kbd>esc</kbd>close help, clear role focus</div>
</div>
<script{nonce_attr}>
{js}
</script>
</body>
</html>
""".format(title=title, favicon=favicon_link(), brand=logo_link(), css=css, js=js,
               nonce_attr=(' nonce="%s"' % _html.escape(nonce, quote=True)) if nonce else "", **_tok_fields(graph.get("tokens")),
               **_brief_fields(graph))

    html_doc = html_doc.replace("%(card_id)s", _html.escape(card_id, quote=True))
    html_doc = html_doc.replace("%(json_name)s", _js_safe(json_filename))
    html_doc = html_doc.replace("%(initial)s", initial)
    html_doc = html_doc.replace("%(colours)s", json.dumps(HTML_COLOURS))
    return html_doc


# ----------------------------------------------------------------- main

def _default_path(outdir, card_id, ext):
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (card_id or "graph"))
    return os.path.join(outdir, safe + ext)


def resolve_card_ref(args):
    if args.recent:
        return "recent"
    if args.card:
        return args.card
    return "latest"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Live flow graph for a crew card.")
    ap.add_argument("--card", default=None, help="card id or 'latest'")
    ap.add_argument("--recent", type=int, default=None, help="list the N most recent cards")
    ap.add_argument("--watch", type=float, default=None, help="re-render in place every N seconds")
    ap.add_argument("--json", nargs="?", const="", default=None, metavar="PATH",
                    help="write machine JSON (PATH optional)")
    ap.add_argument("--html", nargs="?", const="", default=None, metavar="PATH",
                    help="write a self-contained HTML file (PATH optional)")
    ap.add_argument("--steps", type=int, default=DEFAULT_STEPS, help="steps per node (default %d)" % DEFAULT_STEPS)
    ap.add_argument("--outdir", default=None, help="output directory for default JSON/HTML paths")
    ap.add_argument("--color", dest="color", action="store_true", default=None)
    ap.add_argument("--no-color", dest="color", action="store_false")
    args = ap.parse_args(argv)

    colour = args.color if args.color is not None else bool(sys.stdout.isatty())

    if args.recent:
        return list_recent(args.recent)

    card_ref = resolve_card_ref(args)
    graph, err = build_graph(card_ref, args.steps)

    if err:
        print(err)
        return 0 if ("no runs yet" in (err or "") or "no kanban" in (err or "")) else 1

    if args.watch:
        return watch_loop(card_ref, args.watch, colour, args.steps)

    if args.json is not None:
        path = args.json or _default_path(args.outdir or os.getcwd(), graph["card_id"], ".graph.json")
        path = os.path.abspath(path)
        try:
            with open(path, "w") as fh:
                fh.write(render_json(graph))
        except Exception as exc:
            print("could not write JSON: %s" % exc)
            return 2
        print("JSON: %s" % path)
        print("nodes=%d edges=%d" % (graph["node_count"], graph["edge_count"]))
        return 0

    if args.html is not None:
        if args.html and (args.html != os.path.basename(args.html) or args.html in (".", "..")):
            print("--html takes a file name only; the directory is --outdir")
            return 2
        outdir = args.outdir or os.getcwd()
        html_path = (os.path.join(outdir, args.html) if args.html
                     else _default_path(outdir, graph["card_id"], ".graph.html"))
        html_path = os.path.abspath(html_path)
        json_path = os.path.splitext(html_path)[0] + ".json"
        json_name = os.path.basename(json_path)
        try:
            with open(json_path, "w") as fh:
                fh.write(render_json(graph))
            with open(html_path, "w") as fh:
                fh.write(render_html(graph, json_name))
        except Exception as exc:
            print("could not write HTML: %s" % exc)
            return 2
        print("HTML: %s" % html_path)
        print("JSON: %s" % json_path)
        print("nodes=%d edges=%d" % (graph["node_count"], graph["edge_count"]))
        return 0

    sys.stdout.write(render_terminal(graph, colour, args.steps))
    sys.stdout.write("\n")
    return 0


def watch_loop(card_ref, seconds, colour, steps_n):
    first = True
    while True:
        graph, err = build_graph(card_ref, steps_n)
        text = ""
        if err:
            text = err
        else:
            text = render_terminal(graph, colour, steps_n)
        if first:
            first = False
            sys.stdout.write("\x1b[2J\x1b[H")
        else:
            sys.stdout.write("\x1b[H")
        sys.stdout.write(text)
        sys.stdout.write("\x1b[J")
        sys.stdout.flush()
        try:
            time.sleep(seconds)
        except KeyboardInterrupt:
            sys.stdout.write("\n")
            return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:
        # Never traceback: report a clean message.
        print("crew_graph error: %s: %s" % (type(exc).__name__, exc))
        sys.exit(2)
