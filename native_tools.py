"""Native Hermes tools for the Crew plugin.

Provides first-class Hermes tool definitions (JSON Schemas) and handlers
for card creation, status inspection, diagnosis, and verdict recording,
registered via `ctx.register_tool()`.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import types
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(HERE, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def _card_tool():
    """Load scripts/crew_card.py."""
    try:
        import crew_card  # type: ignore[import-not-found]
        return crew_card
    except Exception:
        return None


def _diagnose_tool():
    """Load scripts/crew_diagnose.py."""
    try:
        import crew_diagnose  # type: ignore[import-not-found]
        return crew_diagnose
    except Exception:
        return None


# ---------------------------------------------------------------- schemas

CREW_CARD_CREATE_SCHEMA = {
    "name": "crew_card_create",
    "description": (
        "Create a contract-guarded Crew Kanban card without spawning external shell processes. "
        "Enforces role verification, token budget floors, and proof contract requirements."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short title for the card (max 120 characters)."
            },
            "role": {
                "type": "string",
                "enum": ["worker", "content", "verifier", "reviewer"],
                "description": "The assigned Crew role for the card (worker, content, verifier, reviewer)."
            },
            "goal": {
                "type": "string",
                "description": "Full goal/objective description. Defaults to title if omitted."
            },
            "artifact": {
                "type": "string",
                "description": "Primary artifact produced or modified (file path, repo, PR)."
            },
            "lands": {
                "type": "string",
                "description": "Target workspace directory or destination for artifact. Defaults to '.' if omitted."
            },
            "audience": {
                "type": "string",
                "description": "Target audience (e.g. 'commander', 'team', 'users'). Defaults to 'commander' if omitted."
            },
            "done_when": {
                "type": "string",
                "description": "Acceptance criteria / Definition of Done. Defaults to 'proof command passes' if omitted."
            },
            "proof_cmd": {
                "type": "string",
                "description": "Deterministic shell/python command to verify completion."
            },
            "budget": {
                "type": "integer",
                "description": "Token budget for the card. Defaults to role default or minimum budget floor."
            },
            "verify": {
                "type": "string",
                "enum": ["proof", "independent", "agent", "dual"],
                "description": "Verification mode for the card. Defaults to 'proof'."
            },
            "parents": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of parent task IDs."
            },
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional additional skills to force-load on the worker."
            },
            "dry_run": {
                "type": "boolean",
                "description": "If true, validate contract and return card preview without writing to Kanban database."
            },
            "allow_no_proof": {
                "type": "boolean",
                "description": "If true, allow creating the card without an automated proof command."
            },
            "initial_status": {
                "type": "string",
                "description": "Initial Kanban status (e.g., 'todo', 'triage')."
            }
        },
        "required": ["title", "role"]
    }
}

CREW_DIAGNOSE_SCHEMA = {
    "name": "crew_diagnose",
    "description": (
        "Inspect and diagnose cards sitting in a given Kanban board state or lookup a specific card by ID. Read-only."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "state": {
                "type": "string",
                "enum": ["blocked", "triage", "todo", "ready", "running", "done", "archived"],
                "description": "Filter cards by state. Defaults to 'blocked'."
            },
            "card_id": {
                "type": "string",
                "description": "Specific card ID to diagnose (e.g. 't_ab12cd34'). Overrides state filter."
            },
            "format": {
                "type": "string",
                "enum": ["text", "json"],
                "description": "Output format: 'text' (human-readable summary) or 'json' (structured data). Defaults to 'text'."
            }
        }
    }
}

CREW_VERDICT_SCHEMA = {
    "name": "crew_verdict",
    "description": (
        "Run and record the owner-confirmed verification proof command for a card, "
        "enforcing safety preflights and automatic rework limits."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "card_id": {
                "type": "string",
                "description": "The target card ID (e.g., 't_1234abcd')."
            },
            "command": {
                "type": "string",
                "description": "Optional command override. Must match the owner-confirmed proof command; unconfirmed commands will be refused."
            },
            "timeout": {
                "type": "integer",
                "description": "Execution timeout in seconds. Defaults to 60."
            },
            "by": {
                "type": "string",
                "description": "Identifier of the reviewing agent/profile. Defaults to current profile or 'crew-verifier'."
            },
            "no_hand_back": {
                "type": "boolean",
                "description": "If true, do not automatically request changes or hand back on 2nd failure."
            }
        },
        "required": ["card_id"]
    }
}

CREW_STATUS_SCHEMA = {
    "name": "crew_status",
    "description": (
        "View in-flight Crew cards, their current status, latest coordinator decisions, and any questions waiting on the owner."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum number of in-flight cards to display. Defaults to 8."
            },
            "format": {
                "type": "string",
                "enum": ["text", "json"],
                "description": "Output format: 'text' (formatted summary) or 'json' (structured card list). Defaults to 'text'."
            }
        }
    }
}

CREW_EVENT_SUBSCRIBE_SCHEMA = {
    "name": "crew_event_subscribe",
    "description": (
        "Subscribe an HTTP/REST webhook URL to receive real-time Crew card lifecycle events "
        "(card_created, card_claimed, card_blocked, card_review, card_completed), or manage existing subscriptions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["subscribe", "unsubscribe", "list", "clear"],
                "description": "Subscription action: 'subscribe' (default), 'unsubscribe', 'list', or 'clear'."
            },
            "url": {
                "type": "string",
                "description": "Webhook endpoint URL (required for subscribe and unsubscribe)."
            },
            "events": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Event kinds to subscribe to (e.g. ['card_created', 'card_completed'], or ['*'] for all). Defaults to ['*']."
            },
            "headers": {
                "type": "object",
                "description": "Optional HTTP headers to include with webhook POST requests (e.g. auth tokens)."
            },
            "format": {
                "type": "string",
                "enum": ["text", "json"],
                "description": "Output format: 'text' or 'json'. Defaults to 'text'."
            }
        }
    }
}


# ---------------------------------------------------------------- handlers


def handle_crew_card_create(args: dict, **kwargs: Any) -> dict[str, Any]:
    """Handler for crew_card_create."""
    if not isinstance(args, dict):
        return {"status": "error", "error": "arguments must be a JSON object"}
    title = str(args.get("title") or "").strip()
    role = str(args.get("role") or "").strip().lower()
    if not title:
        return {"status": "error", "error": "title is required"}
    if not role:
        return {"status": "error", "error": "role is required"}

    c: dict[str, Any] = {
        "title": title,
        "role": role,
        "goal": str(args.get("goal") or title).strip(),
        "artifact": str(args.get("artifact") or "workspace changes").strip(),
        "lands": str(args.get("lands") or ".").strip(),
        "audience": str(args.get("audience") or "commander").strip(),
        "done_when": str(args.get("done_when") or "proof command passes").strip(),
        "proof_cmd": str(args.get("proof_cmd") or "").strip(),
        "verify": str(args.get("verify") or "proof").strip(),
    }
    if args.get("budget"):
        try:
            c["budget"] = int(args["budget"])
        except (ValueError, TypeError):
            pass
    if args.get("proof_mode"):
        c["proof_mode"] = str(args["proof_mode"]).strip().lower()
    if args.get("proof_approved"):
        c["proof_approved"] = bool(args["proof_approved"])
    if args.get("units"):
        c["units"] = args["units"]
    if args.get("inputs"):
        c["inputs"] = str(args["inputs"])

    dry_run = bool(args.get("dry_run", False))
    allow_no_proof = bool(args.get("allow_no_proof", False))
    parents = tuple(args.get("parents") or ())
    initial_status = args.get("initial_status")

    if not c["proof_cmd"] and not allow_no_proof:
        return {"status": "error", "error": "proof_cmd is required unless allow_no_proof is True"}

    try:
        mod = _card_tool()
        if mod is None:
            return {"status": "error", "error": "crew_card module could not be loaded"}
        res = mod.open_card(
            c,
            dry_run=dry_run,
            allow_no_proof=allow_no_proof,
            parents=parents,
            initial_status=initial_status,
        )
        if isinstance(res, dict) and not dry_run:
            cid = res.get("id") or res.get("task_id")
            if cid:
                try:
                    try:
                        from .runtime_events import emit_card_event, CARD_CREATED
                    except ImportError:
                        from runtime_events import emit_card_event, CARD_CREATED
                    emit_card_event(
                        CARD_CREATED,
                        card_id=cid,
                        status=str(initial_status or "running"),
                        title=title,
                        role=role,
                    )
                except Exception:
                    pass
        return {"status": "ok", "card": res}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def handle_crew_diagnose(args: dict, **kwargs: Any) -> Any:
    """Handler for crew_diagnose."""
    if not isinstance(args, dict):
        args = {}
    state = str(args.get("state") or "blocked").strip().lower()
    card_id = (args.get("card_id") or "").strip() or None
    fmt = str(args.get("format") or "text").strip().lower()

    diag_mod = _diagnose_tool()
    if diag_mod is None:
        err = "crew_diagnose module could not be loaded"
        return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"

    if not card_id and state not in diag_mod.STATES:
        err = f"unknown state {state!r}: must be one of {', '.join(diag_mod.STATES)}"
        return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"

    try:
        rows = diag_mod.board_rows(None if card_id else state, card_id)
        if rows is None:
            err = "no board to read: kanban database missing"
            return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"

        cards = diag_mod.cards_from_rows(rows)
        if fmt == "json":
            return {
                "status": "ok",
                "state": state if not card_id else None,
                "card_id": card_id,
                "count": len(cards),
                "cards": cards,
            }
        return diag_mod.render(cards, state, card_id)
    except Exception as exc:
        err = str(exc)
        return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"


def handle_crew_verdict(args: dict, **kwargs: Any) -> dict[str, Any]:
    """Handler for crew_verdict."""
    if not isinstance(args, dict):
        return {"status": "error", "error": "arguments must be a JSON object"}
    card_id = str(args.get("card_id") or "").strip()
    if not card_id:
        return {"status": "error", "error": "card_id is required"}

    command = args.get("command")
    if command is not None:
        command = str(command).strip()

    timeout = 60
    if args.get("timeout"):
        try:
            timeout = int(args["timeout"])
        except (ValueError, TypeError):
            pass

    card_mod = _card_tool()
    if card_mod is None:
        return {"status": "error", "error": "crew_card module could not be loaded"}

    by = args.get("by") or card_mod.current_profile() or "crew-verifier"
    no_hand_back = bool(args.get("no_hand_back", False))

    verdict_args = types.SimpleNamespace(
        card=card_id,
        command=command,
        timeout=timeout,
        by=by,
        no_hand_back=no_hand_back,
        for_event=None,
    )

    stdout_buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buf):
            rc = card_mod.cmd_verdict(verdict_args)
        captured = stdout_buf.getvalue()
        verdict_str = "PASS" if rc == 0 else "FAIL"
        try:
            try:
                from .runtime_events import emit_card_event, CARD_UPDATED
            except ImportError:
                from runtime_events import emit_card_event, CARD_UPDATED
            emit_card_event(
                CARD_UPDATED,
                card_id=card_id,
                status="verified" if rc == 0 else "verification_failed",
                verdict=verdict_str,
                exit_code=rc,
                by=by,
            )
        except Exception:
            pass
        return {
            "status": "ok",
            "verdict": verdict_str,
            "card_id": card_id,
            "exit_code": rc,
            "output": captured.strip(),
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "output": stdout_buf.getvalue().strip(),
        }


def handle_crew_status(args: dict, **kwargs: Any) -> Any:
    """Handler for crew_status."""
    if not isinstance(args, dict):
        args = {}
    limit = 8
    if args.get("limit"):
        try:
            limit = int(args["limit"])
        except (ValueError, TypeError):
            pass
    fmt = str(args.get("format") or "text").strip().lower()

    card_mod = _card_tool()
    if card_mod is None:
        err = "crew_card module could not be loaded"
        return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"

    try:
        if fmt == "json":
            got = card_mod.status_cards(limit=limit)
            if got is None:
                return {"status": "error", "error": "No kanban database found"}
            cards, total = got
            return {
                "status": "ok",
                "total": total,
                "count": len(cards),
                "cards": cards,
            }
        return card_mod.status_text(limit=limit)
    except Exception as exc:
        err = str(exc)
        return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"


def handle_crew_event_subscribe(args: dict, **kwargs: Any) -> Any:
    """Handler for crew_event_subscribe."""
    if not isinstance(args, dict):
        args = {}
    action = str(args.get("action") or "subscribe").strip().lower()
    fmt = str(args.get("format") or "text").strip().lower()
    url = str(args.get("url") or "").strip()
    events = args.get("events")
    headers = args.get("headers")

    try:
        try:
            from .runtime_events import get_webhook_manager
        except ImportError:
            from runtime_events import get_webhook_manager

        mgr = get_webhook_manager()

        if action == "subscribe":
            if not url:
                err = "url is required for action='subscribe'"
                return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"

            res = mgr.register(url=url, events=events, headers=headers)
            if fmt == "json":
                return res
            ev_str = ", ".join(res["events"])
            return f"Subscribed {url} to events: [{ev_str}] (active webhooks: {res['active_webhooks']})"

        elif action == "unsubscribe":
            if not url:
                err = "url is required for action='unsubscribe'"
                return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"
            ok = mgr.unregister(url)
            if fmt == "json":
                return {"status": "ok" if ok else "not_found", "unregistered": ok, "url": url}
            return f"Unsubscribed {url}" if ok else f"Webhook {url} not found"

        elif action == "list":
            items = mgr.list_all()
            if fmt == "json":
                return {"status": "ok", "count": len(items), "webhooks": items}
            if not items:
                return "No active webhook subscriptions"
            lines = [f"Active webhooks ({len(items)}):"]
            for item in items:
                lines.append(f"  - {item['url']} -> {item['events']}")
            return "\n".join(lines)

        elif action == "clear":
            cleared = mgr.clear()
            if fmt == "json":
                return {"status": "ok", "cleared": cleared}
            return f"Cleared {cleared} webhook subscription(s)"

        else:
            err = f"unknown action {action!r}"
            return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"

    except Exception as exc:
        err = str(exc)
        return {"status": "error", "error": err} if fmt == "json" else f"error: {err}"


# ---------------------------------------------------------------- registration


CREW_NATIVE_TOOLS = [
    ("crew_card_create", CREW_CARD_CREATE_SCHEMA, handle_crew_card_create),
    ("crew_diagnose", CREW_DIAGNOSE_SCHEMA, handle_crew_diagnose),
    ("crew_verdict", CREW_VERDICT_SCHEMA, handle_crew_verdict),
    ("crew_status", CREW_STATUS_SCHEMA, handle_crew_status),
    ("crew_event_subscribe", CREW_EVENT_SUBSCRIBE_SCHEMA, handle_crew_event_subscribe),
]


def _string_response_adapter(fn: Any) -> Any:
    """Adapts tool handler output to guarantee Hermes str result contract."""
    import json
    def wrapped(*args: Any, **kwargs: Any) -> str:
        res = fn(*args, **kwargs)
        if isinstance(res, str):
            return res
        return json.dumps(res, indent=2, ensure_ascii=False)
    return wrapped


def register_native_tools(ctx: Any) -> None:
    """Register Crew native tools with Hermes plugin context."""
    for name, schema, handler in CREW_NATIVE_TOOLS:
        try:
            ctx.register_tool(
                name=name,
                toolset="crew",
                schema=schema,
                handler=_string_response_adapter(handler),
                description=schema.get("description", ""),
            )
        except Exception:
            # Registration failure of an individual tool must not crash plugin init
            pass
