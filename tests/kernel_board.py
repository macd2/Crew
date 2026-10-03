"""A throwaway kanban board made by Hermes's own code (hermes_cli.kanban_db_connect creates the schema,
hermes_cli.kanban_db moves the cards), so a test sees the kernel's real states, events and counters and not a
hand-made table. Needs hermes_cli, i.e. the Hermes venv python."""
import os
import sys
from pathlib import Path

ROOT = os.environ.get("HERMES_AGENT_DIR") or os.path.expanduser("~/.hermes/hermes-agent")
if ROOT not in sys.path:
    sys.path.append(ROOT)       # hermes_cli's own root modules (hermes_yaml, utils) live there

from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc

BODY = "Role: worker\nCoordinator: owner/s\nBudget: 200000 tokens\n\nGOAL: g\nDone when: d\n\nproof command: true\n"


def open_board(directory):
    """(kb, conn, path) for a fresh board file in `directory`; HERMES_KANBAN_DB points at it."""
    path = os.path.join(directory, "kanban.db")
    os.environ["HERMES_KANBAN_DB"] = path
    return kb, kbc.connect(Path(path)), path


def add_card(conn, status="ready", body=BODY, title="t", assignee="crew-worker", parents=()):
    """A card in `status`: ready/todo through create_task, blocked by the kernel's block_task, triage the way the
    kernel reaches it (a second same-kind block: BLOCK_RECURRENCE_LIMIT)."""
    if status == "triage":
        cid = kb.create_task(conn, title=title, body=body, assignee=assignee, parents=parents)
        for _ in range(kb.BLOCK_RECURRENCE_LIMIT):
            kb.block_task(conn, cid, reason="stuck", kind="needs_input")
            if kb.get_task(conn, cid).status == "blocked" and kb.get_task(conn, cid).block_recurrences < kb.BLOCK_RECURRENCE_LIMIT:
                kb.unblock_task(conn, cid)
        return cid
    cid = kb.create_task(conn, title=title, body=body, assignee=assignee, parents=parents)
    if status == "blocked":
        kb.block_task(conn, cid, reason="stuck", kind="needs_input")
    return cid


def events(conn, cid):
    return [r[0] for r in conn.execute("select kind from task_events where task_id = ? order by id", (cid,))]


def kernel_cli(path):
    """A stand-in for `subprocess.run([hermes, "kanban", ...])` that runs the same hermes_cli.kanban_db call the
    command runs (unblock, edit --body, set-model, block, schedule, archive) on the board at `path`, and records argv."""
    from types import SimpleNamespace
    calls = []

    def run(argv, **_kw):
        args = list(argv)
        calls.append(args)
        rest = args[args.index("kanban") + 1:] if "kanban" in args else args
        verb, cid = rest[0], rest[1]
        with kbc.connect_closing(Path(path)) as conn:
            if verb == "unblock":
                ok = kb.unblock_task(conn, cid)
            elif verb == "edit":
                ok = kb.edit_task(conn, cid, body=rest[rest.index("--body") + 1])
            elif verb == "set-model":
                model = rest[2] if len(rest) > 2 else None
                provider = rest[rest.index("--provider") + 1] if "--provider" in rest else None
                ok = kb.set_model_override(conn, cid, model, provider=provider)
            elif verb == "block":
                kind = rest[rest.index("--kind") + 1] if "--kind" in rest else None
                words = [w for i, w in enumerate(rest[2:], 2) if w != "--kind" and rest[i - 1] != "--kind"]
                ok = kb.block_task(conn, cid, reason=" ".join(words), kind=kind)
            elif verb == "schedule":
                ok = kb.schedule_task(conn, cid, reason=" ".join(rest[2:]))
            elif verb == "archive":
                ok = kb.archive_task(conn, cid)
            else:
                raise AssertionError("kernel_cli has no stand-in for %r" % verb)
        return SimpleNamespace(returncode=0 if ok else 1, stdout="ok" if ok else "", stderr="" if ok else "refused")

    run.calls = calls
    return run
