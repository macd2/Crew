#!/usr/bin/env python3
"""Comprehensive unit test suite for Crew structured contracts and role personas.

Tests:
- Domain model initialization and post-init coercion
- JSON serialization and deserialization
- Canonical Markdown rendering and round-trip parsing
- Tolerant Markdown parsing across diverse formatting variations (bold, italic, bullets, multiline)
- Zero-defect gap detection and canonical reporting order
- Token budget floor enforcement and verify mode auto-coercion
- Proof script collision detection
- Role specifications, system personas, and Zero-Checkout invariant enforcement
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path so contracts is directly importable
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts import (  # noqa: E402
    BUDGET_FLOOR,
    DEFAULT_BUDGET,
    INPUTS_MAX,
    ContractCard,
    ContractGaps,
    Role,
    get_role_specification,
    parse_markdown_card,
    prepare_contract_model,
    validate_contract,
)


class ContractCardModelTests(unittest.TestCase):
    """Tests for ContractCard dataclass and basic field normalization."""

    def test_default_initialization(self):
        c = ContractCard()
        self.assertEqual(c.role, "worker")
        self.assertEqual(c.verify, "proof")
        self.assertEqual(c.proof_mode, "safe")
        self.assertEqual(c.budget, DEFAULT_BUDGET)
        self.assertFalse(c.proof_approved)

    def test_budget_string_sanitization(self):
        c = ContractCard(budget="1,500,000 tokens")
        self.assertEqual(c.budget, 1500000)

        c2 = ContractCard(budget="2_000_000")
        self.assertEqual(c2.budget, 2000000)

    def test_verify_coercion_for_crew_script(self):
        c = ContractCard(
            verify="proof",
            proof_cmd='sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" .crew/20261018-test/verify.py'
        )
        self.assertEqual(c.verify, "independent")

    def test_to_dict_and_from_dict_roundtrip(self):
        c = ContractCard(
            title="Implement Feature",
            role="worker",
            goal="Add contract models",
            artifact="contracts.py",
            lands="O:/workspaces/oss/crew",
            audience="Developer",
            done_when="Tests pass",
            proof_cmd="pytest tests/test_role_contracts.py",
            verify="proof",
            proof_mode="safe",
            budget=800000,
            constraints="Zero-Checkout invariant",
            inputs="spec.md",
            units="unit1|unit2",
            route="auto",
        )
        d = c.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["title"], "Implement Feature")
        self.assertEqual(d["budget"], 800000)

        c_restored = ContractCard.from_dict(d)
        self.assertEqual(c, c_restored)

    def test_json_roundtrip(self):
        c = ContractCard(
            title="Deploy Service",
            role="content",
            goal="Publish report",
            artifact="report.pdf",
            lands="O:/reports",
            audience="Public",
            done_when="PDF is generated",
            proof_cmd="test -f O:/reports/report.pdf",
            verify="independent",
            budget=500000,
        )
        json_str = c.to_json(indent=2)
        self.assertIn('"artifact": "report.pdf"', json_str)
        c_restored = ContractCard.from_json(json_str)
        self.assertEqual(c, c_restored)

    def test_from_markdown_and_to_markdown(self):
        body = """Role: worker
GOAL: Write secure parser
Artifact: parser.py
Lands at: O:/workspaces
For: Commander
Done when: Tests pass
proof command: pytest tests
Proof mode: safe
"""
        card = ContractCard.from_markdown(body)
        self.assertEqual(card.role, "worker")
        self.assertEqual(card.goal, "Write secure parser")
        self.assertEqual(card.artifact, "parser.py")
        md = card.to_markdown()
        self.assertIn("Role: worker", md)
        self.assertIn("GOAL: Write secure parser", md)

    def test_contract_gaps_type(self):
        card = ContractCard()
        gaps = card.validate_gaps()
        self.assertIsInstance(gaps, ContractGaps)
        self.assertIsInstance(gaps, list)
        self.assertIn("GOAL", gaps)


class TolerantMarkdownParserTests(unittest.TestCase):
    """Tests verifying tolerant parsing of markdown formatting and multiline blocks."""

    def test_parses_clean_canonical_markdown(self):
        body = """Role: worker
Coordinator: default/sess-123
Verifier: crew-verifier
Verify: proof
Budget: 500000 tokens
Origin: telegram:12345
Route: auto

GOAL: Build secure auth module
Artifact: auth.py
Lands at: /src/auth
For: Core Team
Constraints: No external auth libraries

Done when: All JWT tests pass

proof command: pytest tests/test_auth.py
Proof mode: safe
Proof approved: yes
"""
        c = parse_markdown_card(body)
        self.assertEqual(c.role, "worker")
        self.assertEqual(c.coordinator, "default/sess-123")
        self.assertEqual(c.verifier, "crew-verifier")
        self.assertEqual(c.verify, "proof")
        self.assertEqual(c.budget, 500000)
        self.assertEqual(c.origin, "telegram:12345")
        self.assertEqual(c.route, "auto")
        self.assertEqual(c.goal, "Build secure auth module")
        self.assertEqual(c.artifact, "auth.py")
        self.assertEqual(c.lands, "/src/auth")
        self.assertEqual(c.audience, "Core Team")
        self.assertEqual(c.constraints, "No external auth libraries")
        self.assertEqual(c.done_when, "All JWT tests pass")
        self.assertEqual(c.proof_cmd, "pytest tests/test_auth.py")
        self.assertEqual(c.proof_mode, "safe")
        self.assertTrue(c.proof_approved)

    def test_parses_bold_and_markdown_decorated_headers(self):
        body = """**Role:** worker
**Coordinator:** default/sess-456
**Verify:** proof
**Budget:** 1,200,000 tokens
**Route:** cb-claude/custom

**GOAL:** Standardize card contracts
**Artifact:** contracts.py
**Lands at:** O:/workspaces/oss/crew
**For:** AI Agents Fleet
**Constraints:** Zero-Checkout invariant

**Done when:** Full test suite passes without errors
**proof command:** pytest tests/test_role_contracts.py
**Proof mode:** brave
"""
        c = parse_markdown_card(body)
        self.assertEqual(c.role, "worker")
        self.assertEqual(c.coordinator, "default/sess-456")
        self.assertEqual(c.verify, "proof")
        self.assertEqual(c.budget, 1200000)
        self.assertEqual(c.model, "cb-claude")
        self.assertEqual(c.provider, "custom")
        self.assertEqual(c.goal, "Standardize card contracts")
        self.assertEqual(c.artifact, "contracts.py")
        self.assertEqual(c.lands, "O:/workspaces/oss/crew")
        self.assertEqual(c.audience, "AI Agents Fleet")
        self.assertEqual(c.constraints, "Zero-Checkout invariant")
        self.assertEqual(c.done_when, "Full test suite passes without errors")
        self.assertEqual(c.proof_cmd, "pytest tests/test_role_contracts.py")
        self.assertEqual(c.proof_mode, "brave")

    def test_parses_multiline_done_when_and_constraints(self):
        body = """Role: worker
GOAL: Implement robust multiline parsing
Artifact: parser.py
Lands at: /lib
For: Developer
Done when:
- All unit tests pass with 100% coverage
- Performance benchmark finishes under 50ms
- No regex backtrack recursion detected
Constraints:
- Do not add external dependencies
- Preserve backwards compatibility with legacy cards
proof command: pytest tests/test_parser.py
"""
        c = parse_markdown_card(body)
        self.assertIn("All unit tests pass with 100% coverage", c.done_when)
        self.assertIn("No regex backtrack recursion detected", c.done_when)
        self.assertIn("Do not add external dependencies", c.constraints)
        self.assertIn("Preserve backwards compatibility", c.constraints)

    def test_parses_blockquoted_and_bullet_inputs(self):
        body = """Role: worker
GOAL: Process specifications
Artifact: output.json
Lands at: /out
For: QA
Inputs: /docs/specs.md, https://example.com/api
> Reference line 1: payload schema
> Reference line 2: auth headers
Done when: output.json generated
proof command: test -f /out/output.json
"""
        c = parse_markdown_card(body)
        self.assertIn("/docs/specs.md", c.inputs)
        self.assertIn("Reference line 1: payload schema", c.inputs)
        self.assertIn("Reference line 2: auth headers", c.inputs)

    def test_parses_units_bullet_list(self):
        body = """Role: worker
GOAL: Multi-step migration
Artifact: migrated.db
Lands at: /data
For: DBA
Units (progress items):
  - Step 1: Migrate schemas
  - Step 2: Ingest historical rows
  - Step 3: Verify foreign keys
Done when: Migration complete
proof command: test -f /data/migrated.db
"""
        c = parse_markdown_card(body)
        self.assertEqual(
            c.units,
            "Step 1: Migrate schemas|Step 2: Ingest historical rows|Step 3: Verify foreign keys"
        )


class ContractValidationAndGapsTests(unittest.TestCase):
    """Tests for zero-defect contract gap validation."""

    COMPLETE = {
        "role": "worker",
        "goal": "Build feature",
        "artifact": "feature.py",
        "lands": "/src",
        "audience": "Commander",
        "done_when": "All tests pass",
        "proof_cmd": "pytest tests/",
    }

    def test_complete_contract_has_no_gaps(self):
        gaps = validate_contract(self.COMPLETE)
        self.assertEqual(gaps, [])

    def test_missing_fields_reported_in_canonical_order(self):
        gaps = validate_contract({})
        expected = [
            "GOAL",
            "Artifact",
            "Lands at",
            "For",
            "Done when",
            "proof command",
            "role (worker, content, or verifier)",
        ]
        self.assertEqual(gaps, expected)

    def test_allow_no_proof_skips_only_proof_command(self):
        card = dict(self.COMPLETE, proof_cmd="")
        self.assertEqual(validate_contract(card), ["proof command"])
        self.assertEqual(validate_contract(card, allow_no_proof=True), [])

    def test_closeout_verify_mode_skips_proof_command(self):
        card = dict(self.COMPLETE, proof_cmd="", verify="closeout")
        self.assertEqual(validate_contract(card), [])

    def test_invalid_role_reported(self):
        card = dict(self.COMPLETE, role="invalid_actor")
        self.assertEqual(validate_contract(card), ["role (worker, content, or verifier)"])

    def test_accepted_roles_pass_validation(self):
        for role in ("worker", "content", "verifier", "reviewer", "coordinator", "diagnose"):
            with self.subTest(role=role):
                card = dict(self.COMPLETE, role=role)
                self.assertEqual(validate_contract(card), [])

    def test_invalid_verify_mode_reported(self):
        card = dict(self.COMPLETE, verify="magic")
        self.assertEqual(validate_contract(card), ["Verify (proof, independent, agent, or dual)"])

    def test_inputs_over_max_length_reported(self):
        card = dict(self.COMPLETE, inputs="A" * (INPUTS_MAX + 10))
        gaps = validate_contract(card)
        self.assertTrue(any("Inputs (pasted text over" in g for g in gaps))

    def test_script_taken_collision_reported(self):
        def mock_checker(cmd):
            return "t_existing123"

        gaps = validate_contract(self.COMPLETE, proof_taken_checker=mock_checker)
        self.assertTrue(any("already card t_existing123's" in g for g in gaps))


class PrepareContractModelTests(unittest.TestCase):
    """Tests for prepare_contract_model enforcement."""

    def test_raises_on_incomplete_contract(self):
        with self.assertRaises(ValueError) as ctx:
            prepare_contract_model({})
        self.assertIn("contract incomplete, missing: GOAL", str(ctx.exception))

    def test_raises_budget_to_floor(self):
        card = ContractCard(
            role="worker",
            goal="G",
            artifact="A",
            lands="L",
            audience="Audience",
            done_when="D",
            proof_cmd="P",
            budget=10000,
        )
        prepared = prepare_contract_model(card, budget_floor_val=BUDGET_FLOOR)
        self.assertEqual(prepared.budget, BUDGET_FLOOR)

    def test_auto_coerces_verify_mode_for_crew_script(self):
        card = ContractCard(
            role="worker",
            goal="G",
            artifact="A",
            lands="L",
            audience="Audience",
            done_when="D",
            proof_cmd='sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" /path/.crew/test/verify.py',
            verify="proof",
        )
        prepared = prepare_contract_model(card)
        self.assertEqual(prepared.verify, "independent")


class MarkdownRenderingRoundTripTests(unittest.TestCase):
    """Tests verifying canonical markdown rendering and round-trip fidelity."""

    def test_rendering_and_parsing_round_trip(self):
        original = ContractCard(
            title="Verify Roundtrip",
            role="worker",
            coordinator="default/sess-999",
            verifier="crew-verifier",
            verify="proof",
            budget=750000,
            origin="web:chat-1",
            route="auto",
            goal="Implement round trip rendering",
            artifact="renderer.py",
            lands="/src/render",
            audience="Architecture Team",
            constraints="Zero-Checkout invariant in effect",
            inputs="/specs/render.md\n> quoted sample 1\n> quoted sample 2",
            units="Phase 1|Phase 2|Phase 3",
            done_when="Renderer outputs canonical markdown and round trips cleanly",
            proof_cmd="pytest tests/test_role_contracts.py",
            proof_mode="safe",
            proof_approved=True,
        )
        rendered_md = original.render()
        parsed = parse_markdown_card(rendered_md)

        self.assertEqual(parsed.role, original.role)
        self.assertEqual(parsed.coordinator, original.coordinator)
        self.assertEqual(parsed.verifier, original.verifier)
        self.assertEqual(parsed.verify, original.verify)
        self.assertEqual(parsed.budget, original.budget)
        self.assertEqual(parsed.origin, original.origin)
        self.assertEqual(parsed.route, original.route)
        self.assertEqual(parsed.goal, original.goal)
        self.assertEqual(parsed.artifact, original.artifact)
        self.assertEqual(parsed.lands, original.lands)
        self.assertEqual(parsed.audience, original.audience)
        self.assertEqual(parsed.constraints, original.constraints)
        self.assertEqual(parsed.done_when, original.done_when)
        self.assertEqual(parsed.proof_cmd, original.proof_cmd)
        self.assertEqual(parsed.proof_mode, original.proof_mode)
        self.assertEqual(parsed.proof_approved, original.proof_approved)
        self.assertEqual(parsed.units, original.units)


class RoleSpecificationTests(unittest.TestCase):
    """Tests verifying role personas, prompt generation, and invariant enforcement."""

    def test_worker_specification_contains_zero_checkout_invariant(self):
        spec = get_role_specification("worker")
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.role, Role.WORKER)
        prompt = spec.render_system_prompt()
        self.assertIn("Zero-Checkout Invariant", prompt)
        self.assertIn("O:/workspaces/.worktrees/", prompt)
        self.assertIn("Single Writer", prompt)

    def test_verifier_specification_mandates_independent_evaluation(self):
        spec = get_role_specification("verifier")
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.role, Role.VERIFIER)
        prompt = spec.render_system_prompt()
        self.assertIn("Read-Only Verifier", prompt)
        self.assertIn("NEVER write, edit, or fix the artifact", prompt)
        self.assertIn("Zero-Checkout", prompt)

    def test_coordinator_specification_prohibits_chat_execution(self):
        spec = get_role_specification("coordinator")
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.role, Role.COORDINATOR)
        prompt = spec.render_system_prompt()
        self.assertIn("Zero Autonomous Chat Execution", prompt)
        self.assertIn("Turn-1 Dispatch", prompt)

    def test_diagnose_specification_is_pure_read_only(self):
        spec = get_role_specification("diagnose")
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.role, Role.DIAGNOSE)
        prompt = spec.render_system_prompt()
        self.assertIn("Pure Read-Only", prompt)
        self.assertIn("crew_diagnose.py", prompt)


if __name__ == "__main__":
    unittest.main()
