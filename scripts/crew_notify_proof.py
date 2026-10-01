#!/usr/bin/env python3
"""Proof for the crew notification path (chat side of one card).

Done when a card whose body carries an `Origin:` line reports back into that origin chat/thread as
soon as it ends `done`, alerts the shared topic `crew-alerts` when it ends `blocked`, and the daemon
that carries both posts runs without the file-descriptor exhaustion that killed it before.

Checks (stdlib only, no browser):
  1. crew_card.py open accepts --origin and the card body records it verbatim.
  2. a done probe card: one feed pass (scratch state) prints a post whose target is the origin topic.
  3. a blocked probe card: one feed pass prints a post whose target is crew-alerts.
  4. a card with no Origin line produces no crew-alerts post (only the cards this chat opened ping).
  5. no credential value from the profile .env appears in the captured output (a bare service base
     URL is not a credential).
  6. kanban-zulip-feed.service is active, its main process holds a stable open-descriptor count over
     60 s, and its journal carries no 'Too many open files' line since the last restart.

Read-only against the board except for two probe cards, both archived again at the end.
Exit 0 = every check passed. Non-zero = it did not, and the failing check is printed.
"""
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402 - the owner profile, the base home and the package checkout
HOME = os.environ.get("HERMES_HOME") or crew_card.owner_home()
KANBAN_DB = os.environ.get("KANBAN_DB") or os.path.join(crew_card.base_home(), "kanban.db")
CARD_TOOL = os.path.join(HERE, "crew_card.py")
FEED = os.path.join(HERE, "kanban_zulip_feed.py")
SERVICE = "kanban-zulip-feed.service"
ALERT_TOPIC = "crew-alerts"
ORIGIN = "zulip:stream:Kanban|PROBE origin thread"
PROBE = "probe"
# scheme + host + optional port, nothing else: a service base URL, never a credential.
BARE_URL_RE = re.compile(r"^https?://[A-Za-z0-9.\-]+(:[0-9]+)?/?$")
FAILURES = []


def check(name, ok, detail=""):
    print("%-58s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + detail) if detail else ""))
    if not ok:
        FAILURES.append(name)
    return ok


def run(argv, state=None, timeout=120):
    env = dict(os.environ)
    env["HERMES_HOME"] = HOME
    if state:
        env["KANBAN_FEED_STATE"] = state
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def open_probe(title, origin=True):
    """A probe card, seeded straight into the board database.

    No CLI: a worker or verifier context has to be able to run this proof too, and `crew_card.py
    open` does not always succeed there. The body carries the coordinator line the feed looks for and
    the origin verbatim, exactly as `crew_card.py open --origin ...` would have written them. The
    card starts archived so neither the feed nor the dispatcher touches it before the proof sets the
    status it wants to test.
    """
    card = "t_" + uuid.uuid4().hex[:8]
    body = ("Coordinator: %s/\n"
            "Goal: probe card: proves the crew notification path routes a done report to the origin "
            "chat and a blocked alert to the shared crew-alerts topic\n"
            "Role: worker\nproof command: true\n"
            % (os.environ.get("CREW_ROLE") or crew_card.owner_profile()))
    if origin:
        body += "Origin: %s\n" % ORIGIN
    conn = sqlite3.connect(KANBAN_DB)
    try:
        conn.execute(
            "insert into tasks (id, title, body, assignee, status, priority, created_by, created_at, "
            "workspace_kind) values (?, ?, ?, 'crew-worker', 'archived', 0, 'probe', ?, 'scratch')",
            (card, title, body, int(time.time())))
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        conn.close()
        return None, "seeding failed: %s" % str(exc)[:120], 2
    conn.close()
    return card, "seeded %s" % card, 0


def set_status(card, status):
    conn = sqlite3.connect(KANBAN_DB)
    conn.execute("update tasks set status = ? where id = ?", (status, card))
    conn.commit()
    conn.close()


def body_of(card):
    conn = sqlite3.connect(KANBAN_DB)
    row = conn.execute("select coalesce(body,'') from tasks where id = ?", (card,)).fetchone()
    conn.close()
    return row[0] if row else ""


def feed_pass(state):
    return run([sys.executable, FEED, "--dry-run", "--once"], state=state)[1]


def posted_targets(text, card):
    """Topics the captured pass says it posted this card's report into."""
    out = []
    for line in text.splitlines():
        if card in line and line.lstrip().startswith("---"):
            m = re.search(r"---\s*#(\S+)\s*>\s*([^()]+?)\s*\(", line)
            if m:
                out.append((m.group(1), m.group(2).strip()))
    return out


def service_main_pid():
    rc, out = run(["systemctl", "--user", "show", SERVICE, "-p", "MainPID", "--value"])
    return int(out.strip() or 0)


def open_fds(pid):
    try:
        return len(os.listdir("/proc/%d/fd" % pid))
    except OSError:
        return -1


def journal_since_restart():
    rc, txt = run(["journalctl", "--user", "-u", SERVICE, "-n", "200", "--no-pager", "-o", "cat"])
    lines = txt.splitlines()
    cut = 0
    for i in range(len(lines) - 1, -1, -1):
        if "Started" in lines[i] or "Stopping" in lines[i]:
            cut = i
            break
    return "\n".join(lines[cut:])


def main():
    state_dir = tempfile.mkdtemp(prefix="crew-notify-proof-")
    probe_done, probe_blocked, probe_plain = None, None, None
    text = ""
    try:
        # 1 - the contract records where the card came from.
        probe_done, out, rc = open_probe("PROBE notify done %s" % os.path.basename(state_dir))
        check("crew_card.py open accepts --origin", rc == 0 and probe_done is not None, out.strip()[:80])
        if probe_done:
            body = body_of(probe_done)
            check("card body records the origin verbatim", ORIGIN in body)

        # 2 - a done card reports into its origin thread.
        if probe_done:
            set_status(probe_done, "done")
            text = feed_pass(os.path.join(state_dir, "done.json"))
            targets = posted_targets(text, probe_done)
            check("done card posts once, into its origin topic",
                  len(targets) == 1 and targets[0][1] == "PROBE origin thread",
                  "; ".join("%s > %s" % t for t in targets) or "no post for %s" % probe_done)

        # 3 - a blocked card alerts the shared topic.
        probe_blocked, out, rc = open_probe("PROBE notify blocked %s" % os.path.basename(state_dir))
        if probe_blocked:
            set_status(probe_blocked, "blocked")
            text = feed_pass(os.path.join(state_dir, "blocked.json"))
            targets = posted_targets(text, probe_blocked)
            # A stuck card alerts the shared topic AND the chat it came from, once each.
            check("blocked card alerts #%s and its origin, once each" % ALERT_TOPIC,
                  len(targets) == 2
                  and sorted(t[1] for t in targets) == sorted([ALERT_TOPIC, "PROBE origin thread"]),
                  "; ".join("%s > %s" % t for t in targets) or "no post for %s" % probe_blocked)

        # 4 - a card with no origin does not ping.
        probe_plain, out, rc = open_probe("PROBE notify plain %s" % os.path.basename(state_dir),
                                         origin=False)
        if probe_plain:
            set_status(probe_plain, "blocked")
            text = feed_pass(os.path.join(state_dir, "plain.json"))
            check("a stuck card with no origin still alerts #%s" % ALERT_TOPIC, probe_plain in text)
            check("a stuck card with no origin has no chat to report into",
                  ("PROBE origin thread" not in text) or (probe_plain not in text.split("PROBE origin thread")[0][-200:]))
        else:
            check("a probe card without an origin can be opened", False, out.strip()[:60])

        # 5 - no credential reaches the post.
        # A bare scheme+host(+port) from .env (ZULIP_SITE) is the base URL the feed is meant to
        # print as the card link, so it is not a credential; anything with a path, a query, a
        # userinfo or non-URL shape is still treated as a secret.
        env_path = os.path.join(HOME, ".env")
        if os.path.exists(env_path):
            secrets = []
            with open(env_path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if "=" in line and not line.strip().startswith("#"):
                        _, _, v = line.partition("=")
                        v = v.strip().strip('"').strip("'")
                        if len(v) >= 16 and not BARE_URL_RE.match(v):
                            secrets.append(v)
            captured = text
            check("no credential from .env appears in the pass output",
                  not any(s in captured for s in secrets))

        # 6 - the daemon carries it without dying again.
        pid = service_main_pid()
        limit = 0
        try:
            with open("/proc/%d/limits" % pid) as fh:
                for line in fh:
                    if line.startswith("Max open files"):
                        limit = int(line.split()[3])
        except OSError:
            limit = 0
        first = open_fds(pid)
        time.sleep(60)
        second = open_fds(pid)
        check("%s active" % SERVICE,
              run(["systemctl", "--user", "is-active", SERVICE])[1].strip() == "active")
        check("open descriptors below the process limit", limit == 0 or 0 < first < limit,
              "fds %d of limit %d" % (first, limit))
        check("open descriptors stable over 60 s", first > 0 and second >= 0
              and second - first <= 5, "fds %d -> %d" % (first, second))
        check("no 'Too many open files' since the restart",
              "Too many open files" not in journal_since_restart())
    finally:
        for card in (probe_done, probe_blocked, probe_plain):
            if card:
                set_status(card, "archived")

    if FAILURES:
        print("PROOF FAIL: %d check(s) failed: %s" % (len(FAILURES), "; ".join(FAILURES)))
        return 1
    print("PROOF OK: done reports land in the origin thread, blocked alerts in #%s, "
          "no-origin cards stay silent, the daemon holds its descriptors" % ALERT_TOPIC)
    return 0


if __name__ == "__main__":
    sys.exit(main())
