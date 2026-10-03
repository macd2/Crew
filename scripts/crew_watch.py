#!/usr/bin/env python3
"""In-session watcher: tells the session that opened a crew card when the card has something for the owner.

A /crew intake can run in a Hermes CLI session, where the card has no chat origin and crew_notify (which sends into a
chat with `hermes send`) has nowhere to report: the owner was never told (t_d3c396cd, 2026-10-03). Hermes reports its
own background work back into the SAME session with `terminal(background=true, notify_on_complete=true)`: when the
process exits, its output is delivered to the session and starts a new agent turn (tools/terminal_tool_background.py;
CLI: completion_queue, gateway: completion watcher). The intake starts this script that way right after the card
opens:

  python3 crew_card.py watch --card <id>        (crew_card.py only dispatches here: this module owns the loop)

It polls the board read-only every POLL_S (no model, no tokens) and exits only when crew_notify's own decision
(crew_notify.card_reports) has something for this card: the card done and audited, a new owner question, or an
abandon. A done card whose audit failed is followed into its follow-up card(s) and reported once, combined. The
summary goes to stdout (that is the message the session receives); before exiting, the message is recorded as sent in
crew_notify's state file under the same keys, so crew_notify never sends it again. crew_notify stays the fallback for
a session that is gone. It also exits, with one line, when the card is parked by the owner's /crew-stop ("stopped by you - /crew-unstuck <id>
to continue", said once, never by the notifier), stopped (archived) or gone, and after
MAX_LIFETIME_S with "still running".
"""
import argparse
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import crew_card  # noqa: E402
import crew_notify as N  # noqa: E402

POLL_S = int(os.environ.get("CREW_WATCH_POLL", "15"))
MAX_LIFETIME_S = int(os.environ.get("CREW_WATCH_LIFETIME", str(24 * 3600)))
MAX_CHAIN = 6                                     # follow-up hops followed (MAX_AUDIT_FOLLOWUPS is 2)


def _task(conn, tid):
    return conn.execute("select * from tasks where id=?", (tid,)).fetchone()


def follow(conn, db, tid, now):
    """(task, chain, final audit decision): the card whose ending counts for `tid`: itself, or, while its audit failed
    and a follow-up card carries the work on, that follow-up (chain = every card on the way)."""
    chain, cur = [tid], tid
    while True:
        task = _task(conn, cur)
        if not task or task["status"] != "done" or len(chain) > MAX_CHAIN:
            return task, chain, None
        ev = conn.execute("select id, created_at from task_events where task_id=? and kind='completed' "
                          "order by id desc limit 1", (cur,)).fetchone() or {"id": 0, "created_at": 0}
        state, dec, nxt = N.audit_outcome(conn, db, task, ev, now)
        if state != "followup" or nxt in chain:
            return task, chain, dec
        chain.append(nxt)
        cur = nxt


def _extra(conn, db, kind, chain, task, dec):
    """The lines above the card link: what was delivered where, how the proof ended, what is open."""
    first = _task(conn, chain[0])
    if kind == "needs":
        return "Reply here to answer, or /crew-unstuck %s to put it back in the queue." % task["id"]
    if kind != "done":
        return ""
    lines = []
    lands = crew_card.field(first["body"], "Lands at") if first else ""
    if lands:
        lines.append("Lands at: %s" % N.short(lands, 200))
    if len(chain) > 1:
        lines.append("Proof: the audit of %s failed; %s redid it%s" % (
            chain[0], " -> ".join(chain[1:]), ", audit passed" if (dec or {}).get("outcome") == "pass" else ""))
    elif dec and dec.get("decision") == "audit":
        lines.append("Proof: passed, re-run by the coordinator after completion")
    elif dec and dec.get("decision") == "owner_close":
        lines.append("Proof: closed by your override, no PASS line")
    for why in dict.fromkeys(w for cid in chain for w in crew_card.script_revisions(cid, db)):
        lines.append("proof script revised by the coordinator: %s" % N.short(why, 200))
    return "\n".join(lines)


def done_report(conn, db, tid, now):
    """The done report of card `tid` without header and link: what was delivered (the summary of the card, or of the
    follow-up that took over after a failed audit), where it lands, how the proof ended, what was revised. The one
    builder the card page reads (crew_graph) beside the message `check` sends (`_text` adds the header and link to
    the same two pieces). '' for a card that is not done."""
    task, chain, dec = follow(conn, db, tid, now)
    if not task or task["status"] != "done":
        return ""
    return "\n".join(x for x in (N.done_summary(conn, task), _extra(conn, db, "done", chain, task, dec)) if x)


def check(db, tid, state_path, now):
    """One poll: None while there is nothing to tell, else (text, [(card, key)] to record as sent)."""
    conn = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        if not _task(conn, tid):
            return "crew watch: card %s is not on the board any more." % tid, []
        task, chain, dec = follow(conn, db, tid, now)
        if not task:
            return "crew watch: follow-up card %s is not on the board any more." % chain[-1], []
        sent = N.sent_keys(state_path, task["id"])
        reports = N.card_reports(conn, db, task, 0, now)
        fresh = [r for r in reports if r[0] not in sent]
        if fresh:
            key, kind, question = fresh[-1]
            src = tid if task["id"] != tid else ""
            if src:             # a follow-up's ending is the original card's: its name, its title
                task = dict(task, title=_task(conn, tid)["title"])
            text = N._text(conn, task, kind, src, question, _extra(conn, db, kind, chain, task, dec))
            return text, [(task["id"], key)]
        if reports and reports[-1][1] in ("done", "abandoned"):
            return "crew watch: %s already reported to you in chat." % task["id"], []
        parked = crew_card.parked_by_owner(db, task["id"])
        if parked:              # the owner's own /crew-stop: said once here, never by the notifier
            return ("crew watch: card %s stopped by you - /crew-unstuck %s to continue." % (task["id"], task["id"]),
                    [(task["id"], "parked:%d" % parked)])
        if task["status"] == "archived":
            return "crew watch: card %s was stopped (archived); nothing more to report." % task["id"], []
        return None
    finally:
        conn.close()


def watch(db, tid, state_path, poll=POLL_S, lifetime=MAX_LIFETIME_S, sleep=time.sleep, now=time.time):
    """Poll until `check` has something, record it as sent, return the text; at `lifetime` return the 'still running'
    line (nothing recorded: crew_notify reports the ending when it comes)."""
    deadline = now() + lifetime
    while True:
        got = check(db, tid, state_path, now())
        if got:
            text, marks = got
            for card, key in marks:
                N.mark_sent(state_path, card, key, now())
            return text
        if now() >= deadline:
            return "crew watch: card %s is still running after %dh; check /crew-status." % (tid, lifetime // 3600)
        sleep(poll)


def main(argv=None):
    ap = argparse.ArgumentParser(description="wait for a crew card's ending or owner question, print it, exit")
    ap.add_argument("--card", required=True)
    ap.add_argument("--db", default=None, help="board kanban.db (default: the live board)")
    ap.add_argument("--state", default=None, help="notify state file (default: $HERMES_HOME/crew/notify-state.json)")
    ap.add_argument("--poll", type=int, default=POLL_S)
    ap.add_argument("--lifetime", type=int, default=MAX_LIFETIME_S, help="seconds before 'still running'")
    a = ap.parse_args(argv)
    db = a.db or crew_card.kanban_db()
    if not db or not os.path.exists(db):
        print("no board")
        return 2
    print(watch(db, a.card, a.state or N.state_file(os.environ.get("HERMES_KANBAN_BOARD")), a.poll, a.lifetime))
    return 0


if __name__ == "__main__":
    sys.exit(main())
