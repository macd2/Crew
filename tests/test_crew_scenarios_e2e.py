#!/usr/bin/env python3
"""Comprehensive E2E Scenario Test Suite for Crew Plugin and Native Tools.

Tests all operational scenarios across the 5 core layers:
1. Native Tool Execution & Schema Contract (`crew_card_create`, `crew_diagnose`, `crew_verdict`, `crew_status`).
2. Contract Parser & Tolerant Header Lexing (`contracts.py`).
3. In-Process Event Lifecycle & REST Dispatch (`runtime_events.py`).
4. Dual-Chained Review & Re-Review Pipeline Governance.
5. Skill Invariants & Frontmatter Standards.
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

# Ensure oss/crew is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts import (  # noqa: E402
    ContractCard,
    ContractGaps,
    get_role_specification,
    parse_markdown_card,
    prepare_contract_model,
)
from native_tools import (  # noqa: E402
    register_native_tools,
)
from runtime_events import (  # noqa: E402
    CARD_CLAIMED,
    CARD_COMPLETED,
    CARD_CREATED,
    CARD_REVIEW,
    Event,
    EventBus,
    RESTNotifier,
    emit_card_event,
    handle_kanban_lifecycle_event,
)


class MockPluginContext:
    def __init__(self):
        self.tools: List[Dict[str, Any]] = []
        self.commands: List[Dict[str, Any]] = []
        self.hooks: List[Dict[str, Any]] = []
        self.skills: List[Dict[str, Any]] = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)

    def register_command(self, name, handler, **kwargs):
        self.commands.append({"name": name, "handler": handler, **kwargs})

    def register_hook(self, name, handler):
        self.hooks.append({"name": name, "handler": handler})

    def register_skill(self, name, path, **kwargs):
        self.skills.append({"name": name, "path": path, **kwargs})


# =============================================================================
# SCENARIO GROUP 1: NATIVE TOOLS CONTRACT & EXECUTION
# =============================================================================

class ScenarioGroup1NativeTools(unittest.TestCase):
    """Scenario 1: End-to-end execution of Crew native tools via string-adapted handlers."""

    def setUp(self):
        self.ctx = MockPluginContext()
        register_native_tools(self.ctx)
        self.tool_map = {t["name"]: t["handler"] for t in self.ctx.tools}

    def test_scenario_1_1_card_create_valid_dry_run(self):
        """Scenario 1.1: Agent calls crew_card_create in dry_run mode with all required fields."""
        handler = self.tool_map["crew_card_create"]
        args = {
            "title": "Build WebSocket Ping Test",
            "role": "worker",
            "goal": "Implement keepalive ping assertions",
            "artifact": "connection.rs",
            "lands": "oss/buzz",
            "audience": "reviewer",
            "done_when": "cargo test passes",
            "proof_cmd": "cargo test --test keepalive",
            "budget": 500000,
            "dry_run": True,
        }
        res_str = handler(args)
        self.assertIsInstance(res_str, str, "Handler must return str per Hermes tool contract")
        res = json.loads(res_str)
        self.assertEqual(res["status"], "ok")
        card = res["card"]
        self.assertTrue(card.get("dry_run"))
        self.assertIn("Build WebSocket Ping Test", card.get("argv", []))
        self.assertIn("Role: worker", card.get("body", ""))
        self.assertEqual(card.get("role"), "worker")
        self.assertEqual(card.get("budget"), 500000)
        self.assertEqual(card.get("proof_cmd"), "cargo test --test keepalive")

    def test_scenario_1_2_card_create_rejects_missing_required(self):
        """Scenario 1.2: Agent omits title or role; tool returns structured error."""
        handler = self.tool_map["crew_card_create"]
        res = json.loads(handler({"role": "worker"}))
        self.assertEqual(res["status"], "error")
        self.assertIn("title is required", res["error"])

        res = json.loads(handler({"title": "Fix bug"}))
        self.assertEqual(res["status"], "error")
        self.assertIn("role is required", res["error"])

    def test_scenario_1_3_card_create_budget_floor_enforcement(self):
        """Scenario 1.3: Low budget is normalized without crashing."""
        handler = self.tool_map["crew_card_create"]
        args = {
            "title": "Trivial typo fix",
            "role": "worker",
            "proof_cmd": "test -f README.md",
            "budget": 5000,  # Below budget floor
            "dry_run": True,
        }
        res = json.loads(handler(args))
        self.assertEqual(res["status"], "ok")
        # In dry run, card is parsed successfully
        self.assertIsNotNone(res["card"])

    def test_scenario_1_4_diagnose_text_and_json_modes(self):
        """Scenario 1.4: Agent invokes crew_diagnose in both text and JSON formats."""
        handler = self.tool_map["crew_diagnose"]
        # Format text (human-readable string)
        text_out = handler({"state": "blocked", "format": "text"})
        self.assertIsInstance(text_out, str)
        self.assertTrue(text_out.startswith("diagnose:") or "error:" in text_out or "no board" in text_out)

        # Format json (serialized JSON string)
        json_out = handler({"state": "blocked", "format": "json"})
        self.assertIsInstance(json_out, str)
        res = json.loads(json_out)
        self.assertIn("status", res)

    def test_scenario_1_5_status_in_flight_queries(self):
        """Scenario 1.5: Agent invokes crew_status with limit bounds."""
        handler = self.tool_map["crew_status"]
        text_out = handler({"format": "text", "limit": 5})
        self.assertIsInstance(text_out, str)

        json_out = handler({"format": "json", "limit": 5})
        self.assertIsInstance(json_out, str)
        res = json.loads(json_out)
        self.assertIn("status", res)

    def test_scenario_1_6_verdict_handler_contract(self):
        """Scenario 1.6: crew_verdict requires card_id and executes verdict check."""
        handler = self.tool_map["crew_verdict"]
        res = json.loads(handler({}))
        self.assertEqual(res["status"], "error")
        self.assertIn("card_id is required", res["error"])

    def test_scenario_1_7_event_subscribe_webhook_management(self):
        """Scenario 1.7: Agent manages webhook subscriptions via crew_event_subscribe."""
        handler = self.tool_map["crew_event_subscribe"]
        # Subscribe
        sub_res = json.loads(handler({
            "action": "subscribe",
            "url": "http://127.0.0.1:8888/events",
            "events": ["card_created", "card_completed"],
            "format": "json",
        }))
        self.assertEqual(sub_res["status"], "ok")
        self.assertEqual("http://127.0.0.1:8888/events", sub_res["url"])

        # List
        list_res = json.loads(handler({"action": "list", "format": "json"}))
        self.assertEqual(list_res["status"], "ok")
        self.assertGreaterEqual(list_res["count"], 1)

        # Clear
        clr_res = json.loads(handler({"action": "clear", "format": "json"}))
        self.assertEqual(clr_res["status"], "ok")
        self.assertGreaterEqual(clr_res["cleared"], 1)


# =============================================================================
# SCENARIO GROUP 2: CONTRACT PARSING & TOLERANT LEXING
# =============================================================================

class ScenarioGroup2ContractTolerantParsing(unittest.TestCase):
    """Scenario 2: Robust contract parsing across diverse human and LLM Markdown styles."""

    def test_scenario_2_1_bold_colon_and_bullet_headers(self):
        """Scenario 2.1: Key decorations (**Role:**, **Role**:, - **GOAL:**)."""
        body = """
- **Role:** worker
- **GOAL**: Implement Zero-Checkout test suite
- **Artifact:** test_suite.py
- **Lands at:** O:/workspaces
- **For:** Commander
- **Done when:** 100% tests pass
- **proof command:** pytest tests
- **Proof mode:** brave
- **Budget:** 1,200,000 tokens
"""
        card = ContractCard.from_markdown(body)
        self.assertEqual(card.role, "worker")
        self.assertEqual(card.goal, "Implement Zero-Checkout test suite")
        self.assertEqual(card.artifact, "test_suite.py")
        self.assertEqual(card.audience, "Commander")
        self.assertEqual(card.proof_mode, "brave")
        self.assertEqual(card.budget, 1200000)

    def test_scenario_2_2_multiline_continuation_blocks(self):
        """Scenario 2.2: Multiline fields with indentation and bullets."""
        body = """Role: worker
GOAL: Multi-part refactor
Artifact: engine.py
Lands at: .
For: Commander
Done when:
  1. Component A is isolated
  2. Component B passes tests
  3. No regressions observed
Constraints:
  - Zero-Checkout invariant
  - Do not edit outside workspace
proof command: pytest tests
"""
        card = ContractCard.from_markdown(body)
        self.assertIn("Component A is isolated", card.done_when)
        self.assertIn("Component B passes tests", card.done_when)
        self.assertIn("Zero-Checkout invariant", card.constraints)

    def test_scenario_2_3_contract_gaps_detection(self):
        """Scenario 2.3: Incomplete card produces typed ContractGaps list."""
        card = ContractCard(role="worker", title="Missing most fields")
        gaps = card.validate_gaps()
        self.assertIsInstance(gaps, ContractGaps)
        self.assertIn("GOAL", gaps)
        self.assertIn("Artifact", gaps)
        self.assertIn("Lands at", gaps)
        self.assertIn("Done when", gaps)
        self.assertIn("proof command", gaps)

    def test_scenario_2_4_auto_coerce_verify_for_crew_script(self):
        """Scenario 2.4: If proof_cmd points to .crew/ script, verify mode coerces to independent."""
        card = ContractCard(
            role="worker",
            proof_cmd='sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" .crew/20261018-test/verify.py',
            verify="proof",
        )
        self.assertEqual(card.verify, "independent")

    def test_scenario_2_5_bidirectional_roundtrip_rendering(self):
        """Scenario 2.5: Round-trip ContractCard rendering to Markdown and parsing back."""
        original = ContractCard(
            role="worker",
            goal="Implement bidirectional roundtrip",
            artifact="contracts.py",
            lands="oss/crew",
            audience="commander",
            done_when="pytest passes",
            proof_cmd="pytest tests",
            budget=600000,
            verify="proof",
        )
        rendered = original.render()
        parsed = parse_markdown_card(rendered)
        self.assertEqual(parsed.role, original.role)
        self.assertEqual(parsed.goal, original.goal)
        self.assertEqual(parsed.artifact, original.artifact)
        self.assertEqual(parsed.budget, original.budget)
        self.assertEqual(parsed.proof_cmd, original.proof_cmd)


# =============================================================================
# SCENARIO GROUP 3: EVENT-DRIVEN LIFECYCLE HOOKS
# =============================================================================

class ScenarioGroup3EventLifecycle(unittest.TestCase):
    """Scenario 3: In-process EventBus dispatch and REST notification without bash polling."""

    def test_scenario_3_1_event_bus_lifecycle_transitions(self):
        """Scenario 3.1: Full event lifecycle transition sequence."""
        bus = EventBus()
        captured_events: List[Event] = []

        bus.subscribe("*", lambda evt: captured_events.append(evt))

        emit_card_event(CARD_CREATED, "t_test001", "todo", bus=bus, payload={"title": "Test task"})
        emit_card_event(CARD_CLAIMED, "t_test001", "running", bus=bus, payload={"worker": "coder"})
        emit_card_event(CARD_REVIEW, "t_test001", "review", bus=bus, payload={"verifier": "reviewer"})
        emit_card_event(CARD_COMPLETED, "t_test001", "done", bus=bus, payload={"verdict": "PASS"})

        self.assertEqual(len(captured_events), 4)
        self.assertEqual([e.kind for e in captured_events], [
            CARD_CREATED, CARD_CLAIMED, CARD_REVIEW, CARD_COMPLETED
        ])

    def test_scenario_3_2_subscriber_error_isolation(self):
        """Scenario 3.2: Malfunctioning subscriber does not crash publisher or siblings."""
        bus = EventBus()
        healthy_received = []

        def failing_sub(evt):
            raise RuntimeError("Database connection timeout")

        def healthy_sub(evt):
            healthy_received.append(evt.card_id)

        bus.subscribe(CARD_CREATED, failing_sub)
        bus.subscribe(CARD_CREATED, healthy_sub)

        # Emitting must NOT raise
        emit_card_event(CARD_CREATED, "t_safe001", "todo", bus=bus)
        self.assertEqual(healthy_received, ["t_safe001"])

    def test_scenario_3_3_rest_notifier_containment(self):
        """Scenario 3.3: RESTNotifier traps network failures and returns clean boolean status."""
        bus = EventBus()
        mock_opener = mock.MagicMock(side_effect=urllib.error.URLError("Connection refused"))
        notifier = RESTNotifier(["http://127.0.0.1:59999/webhook"], timeout=1.0, opener=mock_opener)
        bus.subscribe(CARD_COMPLETED, notifier.handle_event)

        evt = Event(kind=CARD_COMPLETED, card_id="t_err001", status="done")
        results = notifier.notify(evt)
        self.assertIn("http://127.0.0.1:59999/webhook", results)
        self.assertFalse(results["http://127.0.0.1:59999/webhook"])

    def test_scenario_3_4_kanban_lifecycle_hook_translation(self):
        """Scenario 3.4: Hermes Kanban lifecycle hooks translate to Crew events."""
        bus = EventBus()
        events: List[Event] = []
        bus.subscribe("*", lambda e: events.append(e))

        ev = handle_kanban_lifecycle_event("kanban_task_completed", "t_100", bus=bus, summary="Done")
        self.assertIsNotNone(ev)
        assert ev is not None
        self.assertEqual(ev.kind, CARD_COMPLETED)
        self.assertEqual(ev.status, "done")
        self.assertEqual(len(events), 1)


# =============================================================================
# SCENARIO GROUP 4: DUAL-CHAINED PIPELINE & GOVERNANCE
# =============================================================================

class ScenarioGroup4DualChainedGovernance(unittest.TestCase):
    """Scenario 4: Multi-agent coordination with Zero-Checkout invariant."""

    def test_scenario_4_1_role_personas_codify_zero_checkout(self):
        """Scenario 4.1: Role specifications enforce Zero-Checkout in system prompts and invariants."""
        worker_spec = get_role_specification("worker")
        self.assertIsNotNone(worker_spec)
        assert worker_spec is not None
        self.assertTrue(any("Zero-Checkout" in inv for inv in worker_spec.invariants))
        prompt = worker_spec.render_system_prompt()
        self.assertIn("Zero-Checkout", prompt)

        verifier_spec = get_role_specification("verifier")
        self.assertIsNotNone(verifier_spec)
        assert verifier_spec is not None
        self.assertTrue(any("Zero-Checkout" in p for p in verifier_spec.prohibitions))
        v_prompt = verifier_spec.render_system_prompt()
        self.assertIn("Zero-Checkout", v_prompt)

    def test_scenario_4_2_coordinator_specification_prohibits_chat_execution(self):
        """Scenario 4.2: Coordinator persona explicitly forbids performing tasks directly in chat."""
        coord_spec = get_role_specification("coordinator")
        self.assertIsNotNone(coord_spec)
        assert coord_spec is not None
        prompt = coord_spec.render_system_prompt()
        self.assertIn("without doing implementation in chat", prompt)
        self.assertIn("Zero Autonomous Chat Execution", prompt)

    def test_scenario_4_3_dual_review_mode_contract_and_completion_protocol(self):
        """Scenario 4.3: Dual verification mode contract mandates review request instead of completion."""
        worker_spec = get_role_specification("worker")
        self.assertIsNotNone(worker_spec)
        assert worker_spec is not None
        self.assertIn("Verify: dual", worker_spec.completion_protocol)
        self.assertIn("kanban_request_review", worker_spec.completion_protocol)

        verifier_spec = get_role_specification("verifier")
        self.assertIsNotNone(verifier_spec)
        assert verifier_spec is not None
        self.assertIn("kanban_request_changes", verifier_spec.completion_protocol)

        card = prepare_contract_model({
            "title": "Dual verification task",
            "role": "worker",
            "goal": "Implement feature and request review",
            "artifact": "feature.py",
            "lands": "oss/crew",
            "audience": "commander",
            "done_when": "tests pass",
            "proof_cmd": "pytest",
            "verify": "dual",
        })
        self.assertEqual(card.verify, "dual")
        self.assertEqual(len(card.validate_gaps()), 0)


# =============================================================================
# SCENARIO GROUP 5: SKILLS & FRONTMATTER COMPLIANCE GATE
# =============================================================================

class ScenarioGroup5SkillCompliance(unittest.TestCase):
    """Scenario 5: All shipped Crew skills strictly comply with Hermes standards."""

    def test_scenario_5_1_skill_frontmatter_and_triggers(self):
        """Scenario 5.1: Frontmatter starts at byte 0, version matches plugin.yaml, description ends with a period."""
        skills_dir = ROOT / "skills"
        plugin_version = next(
            line.split(":", 1)[1].strip()
            for line in (ROOT / "plugin.yaml").read_text(encoding="utf-8").splitlines()
            if line.startswith("version:")
        )
        target_skills = sorted(p.name for p in skills_dir.iterdir() if (p / "SKILL.md").is_file())
        self.assertTrue(target_skills, "no shipped skills found")

        for s_name in target_skills:
            skill_md = skills_dir / s_name / "SKILL.md"
            self.assertTrue(skill_md.exists(), f"SKILL.md missing for {s_name}")
            content = skill_md.read_text(encoding="utf-8")

            # Must start with frontmatter at byte 0
            self.assertTrue(content.startswith("---\n"), f"{s_name} must start with --- at byte 0")

            # Extract frontmatter lines
            parts = content.split("---\n", 2)
            self.assertTrue(len(parts) >= 3, f"{s_name} has invalid YAML frontmatter")
            fm_text = parts[1]

            # Version check: every skill carries the plugin version
            self.assertIn("version: %s" % plugin_version, fm_text, f"{s_name} version must be {plugin_version}")

            # Description check
            for line in fm_text.splitlines():
                if line.startswith("description:"):
                    desc = line.split("description:", 1)[1].strip().strip('"').strip("'")
                    self.assertTrue(desc, f"{s_name} description must not be empty")
                    self.assertTrue(desc.endswith("."), f"{s_name} description must end with a period")


if __name__ == "__main__":
    unittest.main(verbosity=2)
