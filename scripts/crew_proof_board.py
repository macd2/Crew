#!/usr/bin/env python3
"""A scratch kanban board for a proof: the kernel's own schema in a file the proof owns.

A proof that seeds cards must never do it on the live board (a scheduled pass acts on them, a real agent
can claim them). Two homes for them: the kernel's own `crew-proofs` board (the nightly runner's, see
proofs_env) and a one-file scratch board a proof makes for itself (init_board). require_proof_board is the
guard every card-creating proof calls first: a DB pin that is the live default board exits 2. `init_board` asks the kernel itself to create the schema (hermes_cli.kanban_db.init_db in the
kernel's own interpreter), so the scratch board has every table and trigger the live one has. The kernel is
asked with HERMES_KANBAN_DB pinned to the scratch file and HERMES_HOME left on the real profile.

Never run the `hermes` CLI with a scratch HERMES_HOME: it bootstraps a runtime there and rewrites the
launcher under <hermes-agent>/.hermes/bin to point at it (it did, once). Proofs that need the CLI point
HERMES_BIN at a wrapper that resets HERMES_HOME, see crew_coordinator_proof.py.
"""
import atexit
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROOFS_BOARD = "crew-proofs"
AGENT = os.environ.get("HERMES_SRC") or os.path.expanduser("~/.hermes/hermes-agent")
VENV_PY = os.environ.get("HERMES_PY", os.path.join(AGENT, ".venv", "bin", "python"))


def init_board(db_path, real_home=None):
    """Create the kernel schema at db_path. Returns True when the file exists afterwards."""
    env = dict(os.environ, PYTHONPATH=AGENT, HERMES_KANBAN_DB=db_path,
               HERMES_HOME=real_home or os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes"))
    subprocess.run([VENV_PY, "-c", "from hermes_cli import kanban_db as kb; kb.init_db()"], env=env,
                   capture_output=True, text=True, timeout=180, cwd=AGENT)
    return os.path.exists(db_path)


def claim_review(db_path, card_id, real_home=None):
    """Claim a card that is in `review` as the reviewer would (the kernel's claim_review_task: the dispatcher's
    own call, which the CLI's `claim` does not offer). Returns True when the card is running afterwards."""
    env = dict(os.environ, PYTHONPATH=AGENT, HERMES_KANBAN_DB=db_path,
               HERMES_HOME=real_home or os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes"))
    code = ("from hermes_cli import kanban_db as kb, kanban_db_connect as kbc\n"
            "conn = kbc.connect()\n"
            "print(kb.claim_review_task(conn, %r, claimer='proof-reviewer') is not None)\n" % card_id)
    done = subprocess.run([VENV_PY, "-c", code], env=env, capture_output=True, text=True, timeout=180, cwd=AGENT)
    return (done.stdout or "").strip().endswith("True")


# ---------------------------------------------------------------------------------------------- proofs board


def _hermes_home():
    return os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")


def kanban_root():
    """The kernel's kanban home: HERMES_KANBAN_HOME, else the base home (a profile's home steps up to it)."""
    override = os.environ.get("HERMES_KANBAN_HOME", "").strip()
    if override:
        return os.path.expanduser(override)
    home = os.path.abspath(_hermes_home())
    if os.path.basename(os.path.dirname(home)) == "profiles":
        return os.path.dirname(os.path.dirname(home))
    return home


def default_db():
    """The live board's file: the kernel keeps the `default` board at <root>/kanban.db."""
    return os.path.join(kanban_root(), "kanban.db")


def proofs_dir():
    return os.path.join(kanban_root(), "kanban", "boards", PROOFS_BOARD)


def proofs_db():
    return os.path.join(proofs_dir(), "kanban.db")


def proofs_env():
    """The environment a proof runs in: every kernel and crew reader lands on the crew-proofs board.

    HERMES_KANBAN_DB pins the file for the kernel (CLI, tools, dispatcher), KANBAN_DB for the crew
    scripts, which read that name; the board slug and the two roots keep workspaces and attachments
    of a proof card out of the live board's folders as well."""
    db = proofs_db()
    return {"HERMES_KANBAN_BOARD": PROOFS_BOARD, "HERMES_KANBAN_DB": db, "KANBAN_DB": db,
            "HERMES_KANBAN_WORKSPACES_ROOT": os.path.join(proofs_dir(), "workspaces"),
            "HERMES_KANBAN_ATTACHMENTS_ROOT": os.path.join(proofs_dir(), "attachments")}


def ensure_proofs_board(hermes=None):
    """Create the crew-proofs board through the kernel's own verb (`kanban boards create`, which has
    mkdir -p semantics). Returns True when the board's file exists afterwards."""
    if not os.path.exists(proofs_db()):
        exe = hermes or os.environ.get("HERMES_BIN") or shutil.which("hermes") or "hermes"
        subprocess.run([exe, "kanban", "boards", "create", PROOFS_BOARD, "--name", "Crew proofs",
                        "--description", "Seed cards of the crew proof suite. Nothing here is real work."],
                       capture_output=True, text=True, timeout=240, stdin=subprocess.DEVNULL)
    return os.path.exists(proofs_db())


def _same_file(a, b):
    return os.path.realpath(os.path.expanduser(a)) == os.path.realpath(os.path.expanduser(b))


def pinned_dbs():
    """The kanban files this process is pinned to: [] when nothing pins it (then the kernel and every
    crew reader fall back to the live default board)."""
    return [v for v in (os.environ.get("HERMES_KANBAN_DB", "").strip(),
                        os.environ.get("KANBAN_DB", "").strip()) if v]


def live_pin(pins=None):
    """The reason this process would write to the live board, or "" when it is safe."""
    pins = pinned_dbs() if pins is None else pins
    if not pins:
        return "no kanban file is pinned (HERMES_KANBAN_DB / KANBAN_DB), so it would use the live board"
    live = {default_db(), os.path.expanduser("~/.hermes/kanban.db")}
    for pin in pins:
        if any(_same_file(pin, d) for d in live):
            return "the kanban file pinned is the live board (%s)" % pin
    return ""


def require_proof_board(name=None):
    """The guard: a proof that seeds cards calls this before it creates anything. Exit 2 when it would
    write to the live default board. Returns the file to seed (the pin the crew scripts read)."""
    why = live_pin()
    if why:
        sys.stderr.write("%s refused: %s.\nRun it through `crew_proofs.py --only <name>`, which pins the "
                         "crew-proofs board, or point KANBAN_DB and HERMES_KANBAN_DB at a scratch board.\n"
                         % (name or os.path.basename(sys.argv[0]), why))
        raise SystemExit(2)
    pin = os.environ.get("KANBAN_DB", "").strip() or os.environ["HERMES_KANBAN_DB"].strip()
    if not os.path.exists(pin):
        sys.stderr.write("%s refused: the pinned kanban file %s does not exist (a proof's seed would create "
                         "an empty one without the kernel's schema). `crew_proofs.py` creates the crew-proofs "
                         "board first.\n" % (name or os.path.basename(sys.argv[0]), pin))
        raise SystemExit(2)
    return pin


def proof_db(name=None):
    """The board file a proof seeds (guarded), for its `KANBAN_DB = ...` line."""
    return require_proof_board(name)


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


_SERVERS = []


def graph_base(timeout=30):
    """The served dashboard a proof reads over HTTP: CREW_GRAPH_BASE / CREW_GRAPH_URL when the caller
    names one, else a server of its own on a free port reading the proofs board (stopped at exit).
    Never the live server on :8799, which reads the live board and so can not see a proof's seed."""
    given = (os.environ.get("CREW_GRAPH_BASE") or os.environ.get("CREW_GRAPH_URL") or "").strip()
    if given:
        return given.rstrip("/")
    db = require_proof_board()
    port = _free_port()
    # the dashboard keeps the owner's cleared notifications in a file under the home: a proof that clears
    # rows must do it in a file of its own, never the owner's
    env = dict(os.environ, CREW_GRAPH_PORT=str(port), CREW_GRAPH_BIND="127.0.0.1",
               KANBAN_DB=db, HERMES_KANBAN_DB=db,
               CREW_ACK_FILE=os.environ.get("CREW_ACK_FILE") or os.path.join(
                   os.path.dirname(os.path.abspath(db)), "attention_acks.json"))
    proc = subprocess.Popen([sys.executable, os.path.join(HERE, "crew_graph_serve.py")], env=env,
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _SERVERS.append(proc)
    atexit.register(stop_servers)
    base = "http://127.0.0.1:%d" % port
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit("graph server for the proofs board exited %s" % proc.returncode)
        try:
            urllib.request.urlopen(base + "/", timeout=2).read(1)
            break
        except Exception:  # noqa: BLE001 - not listening yet
            time.sleep(0.2)
    else:
        stop_servers()
        raise SystemExit("graph server for the proofs board did not answer in %ss" % timeout)
    os.environ["CREW_GRAPH_BASE"] = os.environ["CREW_GRAPH_URL"] = base
    return base


def stop_servers():
    while _SERVERS:
        proc = _SERVERS.pop()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
