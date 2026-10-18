#!/usr/bin/env python3
"""Tests for native Hermes tools registered by the Crew plugin.

Verifies:
1. Tool JSON Schemas and definitions.
2. Tool registration via register_native_tools(ctx) and plugin register(ctx).
3. Handler logic and error handling for:
   - crew_card_create
   - crew_diagnose
   - crew_verdict
   - crew_status
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

import native_tools  # noqa: E402
from native_tools import (  # noqa: E402
    CREW_CARD_CREATE_SCHEMA,
    CREW_DIAGNOSE_SCHEMA,
    CREW_NATIVE_TOOLS,
    CREW_STATUS_SCHEMA,
    CREW_VERDICT_SCHEMA,
    handle_crew_card_create,
    handle_crew_diagnose,
    handle_crew_status,
    handle_crew_verdict,
    register_native_tools,
)


class MockPluginContext:
    def __init__(self):
        self.tools = []
        self.commands = []
        self.skills = []
        self.hooks = []

    def register_tool(self, name, toolset, schema, handler, description="", **kwargs):
        self.tools.append({
            "name": name,
            "toolset": toolset,
            "schema": schema,
            "handler": handler,
            "description": description,
            "kwargs": kwargs,
        })

    def register_command(self, name, handler, description="", args_hint=""):
        self.commands.append({
            "name": name,
            "handler": handler,
            "description": description,
            "args_hint": args_hint,
        })

    def register_skill(self, name, path, description="", frontmatter=None):
        self.skills.append({
            "name": name,
            "path": path,
            "description": description,
            "frontmatter": frontmatter,
        })

    def register_hook(self, name, hook_fn):
        self.hooks.append({"name": name, "hook_fn": hook_fn})


class ToolSchemasTests(unittest.TestCase):
    def test_schema_names_and_structure(self):
        expected_names = {"crew_card_create", "crew_diagnose", "crew_verdict", "crew_status", "crew_event_subscribe"}
        registered_names = {name for name, _, _ in CREW_NATIVE_TOOLS}
        self.assertEqual(expected_names, registered_names)

        for name, schema, handler in CREW_NATIVE_TOOLS:
            self.assertEqual(name, schema["name"])
            self.assertTrue(len(schema["description"]) > 10)
            self.assertEqual("object", schema["parameters"]["type"])
            self.assertIn("properties", schema["parameters"])
            self.assertTrue(callable(handler))

    def test_card_create_schema_required_fields(self):
        params = CREW_CARD_CREATE_SCHEMA["parameters"]
        self.assertEqual(["title", "role"], params["required"])
        self.assertIn("proof_cmd", params["properties"])
        self.assertIn("budget", params["properties"])
        self.assertIn("verify", params["properties"])

    def test_diagnose_schema_fields(self):
        props = CREW_DIAGNOSE_SCHEMA["parameters"]["properties"]
        self.assertIn("state", props)
        self.assertIn("card_id", props)
        self.assertIn("format", props)
        self.assertEqual(["blocked", "triage", "todo", "ready", "running", "done", "archived"],
                         props["state"]["enum"])

    def test_verdict_schema_fields(self):
        params = CREW_VERDICT_SCHEMA["parameters"]
        self.assertEqual(["card_id"], params["required"])
        props = params["properties"]
        self.assertIn("command", props)
        self.assertIn("timeout", props)
        self.assertIn("by", props)

    def test_status_schema_fields(self):
        props = CREW_STATUS_SCHEMA["parameters"]["properties"]
        self.assertIn("limit", props)
        self.assertIn("format", props)

    def test_event_subscribe_schema_fields(self):
        props = native_tools.CREW_EVENT_SUBSCRIBE_SCHEMA["parameters"]["properties"]
        self.assertIn("action", props)
        self.assertIn("url", props)
        self.assertIn("events", props)
        self.assertIn("headers", props)
        self.assertIn("format", props)
        self.assertEqual(["subscribe", "unsubscribe", "list", "clear"], props["action"]["enum"])


class ToolRegistrationTests(unittest.TestCase):
    def test_register_native_tools(self):
        ctx = MockPluginContext()
        register_native_tools(ctx)
        self.assertEqual(5, len(ctx.tools))
        names = {t["name"] for t in ctx.tools}
        self.assertEqual({"crew_card_create", "crew_diagnose", "crew_verdict", "crew_status", "crew_event_subscribe"}, names)
        for t in ctx.tools:
            self.assertEqual("crew", t["toolset"])
            self.assertTrue(callable(t["handler"]))

    def test_plugin_init_registers_tools(self):
        import importlib.util
        init_path = REPO / "__init__.py"
        spec = importlib.util.spec_from_file_location("crew_plugin", str(init_path))
        assert spec is not None and spec.loader is not None
        crew_init = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(crew_init)
        ctx = MockPluginContext()
        crew_init.register(ctx)
        tool_names = {t["name"] for t in ctx.tools}
        self.assertIn("crew_card_create", tool_names)
        self.assertIn("crew_diagnose", tool_names)
        self.assertIn("crew_verdict", tool_names)
        self.assertIn("crew_status", tool_names)
        self.assertIn("crew_event_subscribe", tool_names)
        self.assertTrue(len(ctx.commands) >= 5)
        self.assertTrue(len(ctx.hooks) >= 8)

    def test_registered_handlers_satisfy_hermes_string_contract(self):
        ctx = MockPluginContext()
        register_native_tools(ctx)
        for t in ctx.tools:
            out = t["handler"]({"title": "Test", "role": "worker", "dry_run": True, "allow_no_proof": True})
            self.assertIsInstance(out, str, f"Tool {t['name']} handler must return str")


class CrewCardCreateHandlerTests(unittest.TestCase):
    def test_invalid_args(self):
        res = handle_crew_card_create("not-a-dict")  # type: ignore[arg-type]
        self.assertEqual("error", res["status"])
        self.assertIn("arguments must be a JSON object", res["error"])

    def test_missing_title_or_role(self):
        res = handle_crew_card_create({"role": "worker"})
        self.assertEqual("error", res["status"])
        self.assertIn("title is required", res["error"])

        res = handle_crew_card_create({"title": "Test Title"})
        self.assertEqual("error", res["status"])
        self.assertIn("role is required", res["error"])

    def test_missing_proof_cmd_without_allow(self):
        res = handle_crew_card_create({"title": "Test", "role": "worker"})
        self.assertEqual("error", res["status"])
        self.assertIn("proof_cmd is required unless allow_no_proof is True", res["error"])

    def test_dry_run_creation(self):
        res = handle_crew_card_create({
            "title": "Dry run card",
            "role": "worker",
            "goal": "Test goal execution",
            "proof_cmd": "python -V",
            "dry_run": True,
        })
        self.assertEqual("ok", res["status"])
        card = res["card"]
        self.assertTrue(card.get("dry_run"))
        self.assertIn("argv", card)
        self.assertIn("Role: worker", card.get("body", ""))

    def test_allow_no_proof_dry_run(self):
        res = handle_crew_card_create({
            "title": "No proof card",
            "role": "worker",
            "goal": "Planning pass",
            "allow_no_proof": True,
            "dry_run": True,
        })
        self.assertEqual("ok", res["status"])
        self.assertTrue(res["card"].get("dry_run"))


class CrewDiagnoseHandlerTests(unittest.TestCase):
    def test_unknown_state(self):
        res = handle_crew_diagnose({"state": "invalid_state", "format": "json"})
        self.assertEqual("error", res["status"])
        self.assertIn("unknown state 'invalid_state'", res["error"])

    @mock.patch("native_tools._diagnose_tool")
    def test_diagnose_json_output(self, mock_diag):
        mock_mod = mock.MagicMock()
        mock_mod.STATES = ("blocked", "triage", "todo", "ready", "running", "done", "archived")
        mock_mod.board_rows.return_value = [("row1",)]
        mock_mod.cards_from_rows.return_value = [{"id": "t_01", "state": "blocked", "title": "Blocked Card"}]
        mock_diag.return_value = mock_mod

        res = handle_crew_diagnose({"state": "blocked", "format": "json"})
        self.assertEqual("ok", res["status"])
        self.assertEqual(1, res["count"])
        self.assertEqual("t_01", res["cards"][0]["id"])

    @mock.patch("native_tools._diagnose_tool")
    def test_diagnose_text_output(self, mock_diag):
        mock_mod = mock.MagicMock()
        mock_mod.STATES = ("blocked", "triage", "todo", "ready", "running", "done", "archived")
        mock_mod.board_rows.return_value = [("row1",)]
        mock_mod.cards_from_rows.return_value = [{"id": "t_01"}]
        mock_mod.render.return_value = "diagnose: 1 card(s) in state blocked"
        mock_diag.return_value = mock_mod

        res = handle_crew_diagnose({"state": "blocked", "format": "text"})
        self.assertIn("diagnose: 1 card(s)", res)

    @mock.patch("native_tools._diagnose_tool")
    def test_diagnose_no_board(self, mock_diag):
        mock_mod = mock.MagicMock()
        mock_mod.STATES = ("blocked", "triage", "todo", "ready", "running", "done", "archived")
        mock_mod.board_rows.return_value = None
        mock_diag.return_value = mock_mod

        res = handle_crew_diagnose({"format": "json"})
        self.assertEqual("error", res["status"])
        self.assertIn("kanban database missing", res["error"])


class CrewVerdictHandlerTests(unittest.TestCase):
    def test_missing_card_id(self):
        res = handle_crew_verdict({})
        self.assertEqual("error", res["status"])
        self.assertIn("card_id is required", res["error"])

    @mock.patch("native_tools._card_tool")
    def test_verdict_pass(self, mock_card):
        mock_mod = mock.MagicMock()
        mock_mod.cmd_verdict.return_value = 0
        mock_mod.current_profile.return_value = "reviewer"
        mock_card.return_value = mock_mod

        res = handle_crew_verdict({"card_id": "t_pass"})
        self.assertEqual("ok", res["status"])
        self.assertEqual("PASS", res["verdict"])
        self.assertEqual(0, res["exit_code"])
        self.assertEqual("t_pass", res["card_id"])

    @mock.patch("native_tools._card_tool")
    def test_verdict_fail(self, mock_card):
        mock_mod = mock.MagicMock()
        mock_mod.cmd_verdict.return_value = 1
        mock_mod.current_profile.return_value = "reviewer"
        mock_card.return_value = mock_mod

        res = handle_crew_verdict({"card_id": "t_fail"})
        self.assertEqual("ok", res["status"])
        self.assertEqual("FAIL", res["verdict"])
        self.assertEqual(1, res["exit_code"])

    @mock.patch("native_tools._card_tool")
    def test_verdict_exception_handling(self, mock_card):
        mock_mod = mock.MagicMock()
        mock_mod.cmd_verdict.side_effect = RuntimeError("verdict crash")
        mock_mod.current_profile.return_value = "reviewer"
        mock_card.return_value = mock_mod

        res = handle_crew_verdict({"card_id": "t_crash"})
        self.assertEqual("error", res["status"])
        self.assertIn("verdict crash", res["error"])


class CrewStatusHandlerTests(unittest.TestCase):
    @mock.patch("native_tools._card_tool")
    def test_status_json(self, mock_card):
        mock_mod = mock.MagicMock()
        mock_mod.status_cards.return_value = ([{"id": "t_10", "status": "running"}], 1)
        mock_card.return_value = mock_mod

        res = handle_crew_status({"format": "json"})
        self.assertEqual("ok", res["status"])
        self.assertEqual(1, res["total"])
        self.assertEqual(1, res["count"])
        self.assertEqual("t_10", res["cards"][0]["id"])

    @mock.patch("native_tools._card_tool")
    def test_status_text(self, mock_card):
        mock_mod = mock.MagicMock()
        mock_mod.status_text.return_value = "open cards: 1\n\nTitle: Card"
        mock_card.return_value = mock_mod

        res = handle_crew_status({"format": "text"})
        self.assertIn("open cards: 1", res)

    @mock.patch("native_tools._card_tool")
    def test_status_no_board(self, mock_card):
        mock_mod = mock.MagicMock()
        mock_mod.status_cards.return_value = None
        mock_card.return_value = mock_mod

        res = handle_crew_status({"format": "json"})
        self.assertEqual("error", res["status"])
        self.assertIn("No kanban database found", res["error"])


class CrewEventSubscribeHandlerTests(unittest.TestCase):
    def setUp(self):
        try:
            from runtime_events import get_webhook_manager
            get_webhook_manager().clear()
        except ImportError:
            pass

    def tearDown(self):
        try:
            from runtime_events import get_webhook_manager
            get_webhook_manager().clear()
        except ImportError:
            pass

    def test_event_subscribe_requires_url(self):
        res = native_tools.handle_crew_event_subscribe({"action": "subscribe", "format": "json"})
        self.assertEqual("error", res["status"])
        self.assertIn("url is required", res["error"])

    def test_event_subscribe_and_list(self):
        res = native_tools.handle_crew_event_subscribe({
            "action": "subscribe",
            "url": "http://127.0.0.1:9999/webhook",
            "events": ["card_created", "card_completed"],
            "format": "json",
        })
        self.assertEqual("ok", res["status"])
        self.assertEqual("http://127.0.0.1:9999/webhook", res["url"])
        self.assertEqual(["card_created", "card_completed"], res["events"])

        lst = native_tools.handle_crew_event_subscribe({"action": "list", "format": "json"})
        self.assertEqual("ok", lst["status"])
        self.assertEqual(1, lst["count"])
        self.assertEqual("http://127.0.0.1:9999/webhook", lst["webhooks"][0]["url"])

    def test_event_subscribe_and_unsubscribe(self):
        native_tools.handle_crew_event_subscribe({
            "action": "subscribe",
            "url": "http://127.0.0.1:9999/webhook",
            "format": "json",
        })
        unsub = native_tools.handle_crew_event_subscribe({
            "action": "unsubscribe",
            "url": "http://127.0.0.1:9999/webhook",
            "format": "json",
        })
        self.assertEqual("ok", unsub["status"])
        self.assertTrue(unsub["unregistered"])

        lst = native_tools.handle_crew_event_subscribe({"action": "list", "format": "json"})
        self.assertEqual(0, lst["count"])

    def test_event_subscribe_clear(self):
        native_tools.handle_crew_event_subscribe({
            "action": "subscribe",
            "url": "http://127.0.0.1:9999/webhook1",
            "format": "json",
        })
        native_tools.handle_crew_event_subscribe({
            "action": "subscribe",
            "url": "http://127.0.0.1:9999/webhook2",
            "format": "json",
        })
        clr = native_tools.handle_crew_event_subscribe({"action": "clear", "format": "json"})
        self.assertEqual("ok", clr["status"])
        self.assertEqual(2, clr["cleared"])


if __name__ == "__main__":
    unittest.main()
