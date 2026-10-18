#!/usr/bin/env python3
"""Standardized Crew Role Contracts and System Personas.

Provides strongly-typed domain models, tolerant Markdown card parsing,
canonical Markdown/JSON serialization, zero-defect contract gap validation,
and formal role persona prompt specifications for the Crew multi-agent orchestration engine.

Deterministic, Python standard library only.
"""

from __future__ import annotations

import dataclasses
from enum import Enum
import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class Role(str, Enum):
    """Crew participant roles."""
    WORKER = "worker"
    CONTENT = "content"
    VERIFIER = "verifier"
    REVIEWER = "reviewer"
    COORDINATOR = "coordinator"
    DIAGNOSE = "diagnose"

    @classmethod
    def from_str(cls, val: Optional[str]) -> Optional[Role]:
        if not val:
            return None
        cleaned = str(val).strip().lower()
        # Common aliases
        if cleaned in ("coder", "engineer", "dev"):
            return cls.WORKER
        if cleaned in ("designer", "writer", "copywriter"):
            return cls.CONTENT
        if cleaned in ("qa", "auditor", "tester"):
            return cls.VERIFIER
        if cleaned in ("leader", "pm", "intake"):
            return cls.COORDINATOR
        for item in cls:
            if item.value == cleaned:
                return item
        return None

    @classmethod
    def is_writer(cls, val: str) -> bool:
        r = cls.from_str(val)
        return r in (cls.WORKER, cls.CONTENT)

    @classmethod
    def accepted_roles(cls) -> Tuple[str, ...]:
        return tuple(r.value for r in cls)


class VerifyMode(str, Enum):
    """Card verification taxonomy modes."""
    PROOF = "proof"
    INDEPENDENT = "independent"
    AGENT = "agent"
    DUAL = "dual"
    CLOSEOUT = "closeout"

    @classmethod
    def from_str(cls, val: Optional[str]) -> Optional[VerifyMode]:
        if not val:
            return None
        cleaned = str(val).strip().lower()
        for item in cls:
            if item.value == cleaned:
                return item
        return None

    @classmethod
    def accepted_modes(cls) -> Tuple[str, ...]:
        return tuple(m.value for m in cls)


class ContractGaps(list):
    """Structured collection of detected contract validation gaps."""
    pass


class ProofMode(str, Enum):
    """Unattended proof execution safety mode."""
    SAFE = "safe"
    BRAVE = "brave"

    @classmethod
    def from_str(cls, val: Optional[str]) -> ProofMode:
        if not val:
            return cls.SAFE
        cleaned = str(val).strip().lower()
        return cls.BRAVE if cleaned == "brave" else cls.SAFE


# -----------------------------------------------------------------------------
# Constants & Contract Schema Rules
# -----------------------------------------------------------------------------

DEFAULT_BUDGET = 1_000_000
BUDGET_FLOOR = 120_000
INPUTS_MAX = 2000
DEFAULT_RUNTIME = "60m"

REQUIRED_FIELDS = [
    ("goal", "GOAL"),
    ("artifact", "Artifact"),
    ("lands", "Lands at"),
    ("audience", "For"),
    ("done_when", "Done when"),
    ("proof_cmd", "proof command"),
]

PROOF_SCRIPT_RX = re.compile(r"(?:^|[\s'\"=/])\.crew/")
NO_PROOF_RX = re.compile(r"^\s*\(\s*none\b", re.I)

# Tolerant contract header line regex
# Matches plain 'Key:', decorated '**Key:**', markdown bullet '- **Key:**', header '### Key:'
CONTRACT_FIELD_LINE_RX = re.compile(
    r"^\s*(?:[-*]\s+)?(?:\#{1,6}\s+)?(?:\*\*|\*|__|_)?\s*"
    r"(Role|Coordinator|Verifier|Verify|Budget|Origin|Route|GOAL|Artifact|Lands at|For|Constraints|Inputs|Units|"
    r"Done when|proof command|Proof mode|Proof approved|Proof script)\s*"
    r"(?:\*\*|\*|__|_)?\s*:\s*(?:\*\*|\*|__|_)?\s*(.*?)(?:\*\*|\*|__|_)?\s*$",
    re.I
)

# Canonical field key normalization map
KEY_NORM_MAP: Dict[str, str] = {
    "role": "role",
    "coordinator": "coordinator",
    "verifier": "verifier",
    "verify": "verify",
    "budget": "budget",
    "origin": "origin",
    "route": "route",
    "goal": "goal",
    "artifact": "artifact",
    "lands at": "lands",
    "lands": "lands",
    "for": "audience",
    "audience": "audience",
    "constraints": "constraints",
    "inputs": "inputs",
    "units": "units",
    "done when": "done_when",
    "proof command": "proof_cmd",
    "proof_cmd": "proof_cmd",
    "proof mode": "proof_mode",
    "proof approved": "proof_approved",
    "proof script": "proof_script",
}


def is_proof_script_cmd(cmd: Optional[str]) -> bool:
    """True when the proof command invokes a script under a .crew/ directory."""
    return bool(PROOF_SCRIPT_RX.search(str(cmd or "")))


def coerce_verify_mode(mode: str, proof_command: str) -> str:
    """Coerces 'proof' to 'independent' if the command runs a .crew/ script."""
    m = (mode or "").strip().lower()
    if m == VerifyMode.PROOF.value and is_proof_script_cmd(proof_command):
        return VerifyMode.INDEPENDENT.value
    return m or VerifyMode.PROOF.value


# -----------------------------------------------------------------------------
# Structured Contract Data Model
# -----------------------------------------------------------------------------

@dataclasses.dataclass
class ContractCard:
    """Structured model for a Crew contract card."""
    title: str = ""
    role: str = "worker"
    goal: str = ""
    artifact: str = ""
    lands: str = ""
    audience: str = ""
    done_when: str = ""
    proof_cmd: str = ""
    verify: str = "proof"
    proof_mode: str = "safe"
    proof_approved: bool = False
    budget: Optional[Union[int, str]] = DEFAULT_BUDGET
    constraints: str = ""
    inputs: str = ""
    units: str = ""
    route: str = ""
    model: str = ""
    provider: str = ""
    coordinator: str = ""
    verifier: str = ""
    origin: str = ""
    unparsed_notes: str = ""

    def __post_init__(self):
        self.role = (self.role or "").strip().lower()
        self.verify = (self.verify or "").strip().lower()
        self.proof_mode = (self.proof_mode or "safe").strip().lower()
        if self.budget is not None:
            if isinstance(self.budget, str):
                digits = re.sub(r"\D", "", self.budget)
                self.budget = int(digits) if digits else None
            elif not self.budget:
                self.budget = None

        # Auto coerce verify mode if proof runs .crew/
        if self.proof_cmd and is_proof_script_cmd(self.proof_cmd) and self.verify == "proof":
            self.verify = "independent"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-compatible dictionary."""
        return {
            "title": self.title,
            "role": self.role,
            "goal": self.goal,
            "artifact": self.artifact,
            "lands": self.lands,
            "audience": self.audience,
            "done_when": self.done_when,
            "proof_cmd": self.proof_cmd,
            "verify": self.verify,
            "proof_mode": self.proof_mode,
            "proof_approved": self.proof_approved,
            "budget": self.budget,
            "constraints": self.constraints,
            "inputs": self.inputs,
            "units": self.units,
            "route": self.route,
            "model": self.model,
            "provider": self.provider,
            "coordinator": self.coordinator,
            "verifier": self.verifier,
            "origin": self.origin,
            "unparsed_notes": self.unparsed_notes,
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ContractCard:
        """Instantiate from dictionary."""
        valid_keys = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_keys and v is not None}
        return cls(**filtered)

    @classmethod
    def from_json(cls, json_str: str) -> ContractCard:
        """Instantiate from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_markdown(cls, body: str) -> ContractCard:
        """Parse a Markdown card body string into a ContractCard instance."""
        return parse_markdown_card(body)

    def to_markdown(self, python_exec: str = "python3", script_path: str = "crew_card.py") -> str:
        """Alias for render() maintaining API symmetry with to_dict and to_json."""
        return self.render(python_exec=python_exec, script_path=script_path)

    def validate_gaps(
        self,
        allow_no_proof: bool = False,
        proof_taken_checker: Optional[Callable[[str], str]] = None,
    ) -> ContractGaps:
        """Run zero-defect gap validation."""
        return validate_contract(self.to_dict(), allow_no_proof=allow_no_proof, proof_taken_checker=proof_taken_checker)

    def is_valid(self, allow_no_proof: bool = False) -> bool:
        """Check if contract has zero gaps."""
        return len(self.validate_gaps(allow_no_proof=allow_no_proof)) == 0

    def render(self, python_exec: str = "python3", script_path: str = "crew_card.py") -> str:
        """Render to canonical Markdown card body."""
        return render_contract_body(self.to_dict(), python_exec=python_exec, script_path=script_path)


# -----------------------------------------------------------------------------
# Tolerant Markdown Parser
# -----------------------------------------------------------------------------

def parse_markdown_card(body: str) -> ContractCard:
    """Tolerantly parses a card body Markdown string into a ContractCard.

    Handles:
    - Markdown key decorations (**Role:**, *Role:*, __Role:__, `Role:`, etc.)
    - Bullet point headers (- **GOAL:** ...)
    - Indented continuation lines and bullet lists for multiline fields (Done when, Constraints, Inputs, GOAL)
    - Blockquoted inputs (> line)
    - Digits extraction from budget (e.g. '1,500,000 tokens' -> 1500000)
    - Route parsing (auto, model/provider, none)
    - Units list extraction
    """
    raw_lines = (body or "").splitlines()
    field_map: Dict[str, List[str]] = {}
    current_key: Optional[str] = None
    unparsed: List[str] = []

    # Units special header detection (Units (...):)
    inside_units_block = False
    units_list: List[str] = []

    for line in raw_lines:
        trimmed = line.strip()

        # Check for Units header block: Units (...):
        if re.match(r"^Units\s*\(.*?\)\s*:\s*$", trimmed, re.I):
            inside_units_block = True
            current_key = None
            continue
        elif inside_units_block:
            if trimmed.startswith("-"):
                unit_val = trimmed.lstrip("-").strip()
                if unit_val and not unit_val.startswith("Mark a unit:"):
                    units_list.append(unit_val)
                continue
            elif trimmed and not trimmed.startswith("Mark a unit:"):
                # Non-bullet non-empty line ends units block unless it's empty
                if not CONTRACT_FIELD_LINE_RX.match(line):
                    pass
            elif not trimmed:
                continue

        m = CONTRACT_FIELD_LINE_RX.match(line)
        if m:
            inside_units_block = False
            raw_key = m.group(1).strip().lower()
            val = m.group(2).strip()
            norm_key = KEY_NORM_MAP.get(raw_key, raw_key)
            current_key = norm_key
            if norm_key not in field_map:
                field_map[norm_key] = []
            if val:
                field_map[norm_key].append(val)
        else:
            if current_key in ("done_when", "constraints", "inputs", "goal", "artifact", "lands", "audience"):
                # Check if this line is continuation
                if trimmed.startswith(">"):
                    field_map[current_key].append(trimmed[1:].strip())
                elif trimmed.startswith("- ") or trimmed.startswith("* "):
                    field_map[current_key].append(trimmed)
                elif line.startswith("  ") or line.startswith("\t"):
                    field_map[current_key].append(trimmed)
                elif trimmed and not trimmed.startswith("Contract:") and not trimmed.startswith("Finish:"):
                    # Only append if not beginning another standard section
                    field_map[current_key].append(trimmed)
                elif not trimmed:
                    # preserve blank line if needed or skip
                    pass
            else:
                if trimmed and not trimmed.startswith("Contract:") and not trimmed.startswith("Finish:") and not trimmed.startswith("Verifier, finish"):
                    unparsed.append(trimmed)

    # Reconstruct text fields
    def get_text(k: str) -> str:
        lines = field_map.get(k, [])
        return "\n".join(lines).strip()

    # Role
    role_raw = get_text("role").lower()
    role_obj = Role.from_str(role_raw)
    role_val = role_obj.value if role_obj else role_raw

    # Budget
    budget_raw = get_text("budget")
    budget_digits = re.search(r"\d[\d_,]*", budget_raw)
    budget_val = int(re.sub(r"\D", "", budget_digits.group(0))) if budget_digits else None

    # Route
    route_raw = get_text("route")
    route_class = ""
    model = ""
    provider = ""
    if route_raw:
        if route_raw.lower() == "auto":
            route_class = "auto"
        elif "/" in route_raw:
            model_part, _, provider_part = route_raw.rpartition("/")
            model = model_part.strip()
            provider = provider_part.strip()

    # Proof approved
    proof_approved_raw = get_text("proof_approved").lower()
    proof_approved = proof_approved_raw in ("yes", "true", "1")

    # Proof cmd
    raw_proof_cmd = get_text("proof_cmd")
    if NO_PROOF_RX.match(raw_proof_cmd):
        raw_proof_cmd = ""

    # Verify
    verify_raw = get_text("verify").lower()

    # Units
    units_raw = get_text("units")
    if units_list:
        units_val = "|".join(units_list)
    elif units_raw:
        units_val = "|".join([u.strip() for u in units_raw.split("|") if u.strip()])
    else:
        units_val = ""

    return ContractCard(
        role=role_val,
        coordinator=get_text("coordinator"),
        verifier=get_text("verifier"),
        verify=verify_raw,
        budget=budget_val,
        origin=get_text("origin"),
        route=route_class,
        model=model,
        provider=provider,
        goal=get_text("goal"),
        artifact=get_text("artifact"),
        lands=get_text("lands"),
        audience=get_text("audience"),
        constraints=get_text("constraints"),
        inputs=get_text("inputs"),
        done_when=get_text("done_when"),
        proof_cmd=raw_proof_cmd,
        proof_mode=get_text("proof_mode") or "safe",
        proof_approved=proof_approved,
        units=units_val,
        unparsed_notes="\n".join(unparsed).strip(),
    )


# -----------------------------------------------------------------------------
# Zero-Defect Contract Validation & Gaps Engine
# -----------------------------------------------------------------------------

def validate_contract(
    c: Union[ContractCard, Dict[str, Any]],
    allow_no_proof: bool = False,
    proof_taken_checker: Optional[Callable[[str], str]] = None,
) -> ContractGaps:
    """Evaluates contract gaps in exact canonical order."""
    if isinstance(c, ContractCard):
        data = c.to_dict()
    else:
        data = dict(c)

    gaps: List[str] = []
    proof_command = str(data.get("proof_cmd") or "").strip()

    # 1. Script collision check
    if proof_taken_checker and proof_command:
        taken = proof_taken_checker(proof_command)
        if taken:
            gaps.append(
                "proof command (its .crew/ script is already card %s's: give this card its own folder, "
                "<landing folder>/.crew/<YYYYMMDD-HHMMSS>-<slug>/verify.py)" % taken
            )

    # 2. Required fields check in canonical contract order:
    # GOAL, Artifact, Lands at, For, Done when, proof command
    for key, label in REQUIRED_FIELDS:
        if key == "proof_cmd" and (allow_no_proof or data.get("verify") == VerifyMode.CLOSEOUT.value):
            continue
        val = str(data.get(key) or "").strip()
        if not val:
            gaps.append(label)

    # 3. Role check
    role = str(data.get("role") or "").strip().lower()
    valid_roles = Role.accepted_roles()
    if role not in valid_roles:
        gaps.append("role (worker, content, or verifier)")

    # 4. Verify mode check
    verify_mode = str(data.get("verify") or "").strip().lower()
    valid_verify_modes = ("",) + VerifyMode.accepted_modes()
    if verify_mode not in valid_verify_modes:
        gaps.append("Verify (proof, independent, agent, or dual)")

    # 5. Inputs size limit check
    inputs_val = str(data.get("inputs") or "")
    if len(inputs_val) > INPUTS_MAX:
        gaps.append("Inputs (pasted text over %d characters: ask the owner for a file path instead)" % INPUTS_MAX)

    return ContractGaps(gaps)


def prepare_contract_model(
    c: Union[ContractCard, Dict[str, Any]],
    allow_no_proof: bool = False,
    budget_floor_val: int = BUDGET_FLOOR,
    proof_taken_checker: Optional[Callable[[str], str]] = None,
) -> ContractCard:
    """Validates contract completeness and enforces budget floor & mode coercions."""
    card = c if isinstance(c, ContractCard) else ContractCard.from_dict(c)
    gaps = validate_contract(card, allow_no_proof=allow_no_proof, proof_taken_checker=proof_taken_checker)
    if gaps:
        raise ValueError("contract incomplete, missing: " + ", ".join(gaps))

    # Budget floor enforcement
    budget_int = int(card.budget) if card.budget is not None else 0
    if budget_int < budget_floor_val:
        card.budget = budget_floor_val

    # Coerce verify mode if proof command runs a .crew/ script
    if card.proof_cmd and is_proof_script_cmd(card.proof_cmd) and card.verify == "proof":
        card.verify = "independent"

    return card


# -----------------------------------------------------------------------------
# Canonical Markdown Renderer
# -----------------------------------------------------------------------------

def render_inputs_lines(inputs_text: str) -> List[str]:
    """Renders inputs text as canonical Markdown lines with > quoting."""
    lines = [ln.strip() for ln in str(inputs_text or "").splitlines() if ln.strip()]
    if not lines:
        return []
    head = "" if lines[0].startswith(">") else lines.pop(0)
    res = ["Inputs: %s" % head if head else "Inputs:"]
    for ln in lines:
        res.append(ln if ln.startswith(">") else "> " + ln)
    return res


def render_contract_body(
    c: Union[ContractCard, Dict[str, Any]],
    python_exec: str = "python3",
    script_path: str = "crew_card.py",
) -> str:
    """Renders a contract to the canonical Kanban card body Markdown format."""
    d = c.to_dict() if isinstance(c, ContractCard) else dict(c)

    role = str(d.get("role") or "worker").strip().lower()
    coordinator = str(d.get("coordinator") or "default/no-session")
    verifier = str(d.get("verifier") or "crew-verifier")
    verify_mode = str(d.get("verify") or "proof").strip().lower()
    budget = int(d.get("budget") or DEFAULT_BUDGET)

    lines = [
        "Role: %s" % role,
        "Coordinator: %s" % coordinator,
        "Verifier: %s" % verifier,
        "Verify: %s" % verify_mode,
        "Budget: %d tokens" % budget,
    ]

    origin = str(d.get("origin") or "").strip()
    if origin:
        lines.append("Origin: %s" % origin)

    route = str(d.get("route") or "").strip()
    model = str(d.get("model") or "").strip()
    provider = str(d.get("provider") or "").strip()
    if route:
        lines.append("Route: %s" % route)
    elif model and provider:
        lines.append("Route: %s/%s" % (model, provider))

    lines += [
        "",
        "GOAL: %s" % str(d.get("goal") or "").strip(),
        "Artifact: %s" % str(d.get("artifact") or "").strip(),
        "Lands at: %s" % str(d.get("lands") or "").strip(),
        "For: %s" % str(d.get("audience") or "").strip(),
    ]

    constraints = str(d.get("constraints") or "").strip()
    if constraints:
        lines.append("Constraints: %s" % constraints)

    # Inputs
    inputs_lines = render_inputs_lines(str(d.get("inputs") or ""))
    if inputs_lines:
        lines += inputs_lines

    # Units
    units_raw = str(d.get("units") or "").strip()
    if units_raw:
        units = [u.strip() for u in units_raw.split("|") if u.strip()]
        if units:
            lines += ["", "Units (one entry each in $HERMES_HOME/crew/progress/<card>.json):"]
            for u in units:
                lines.append("  - %s" % u)
            lines.append(
                'Mark a unit: %s %s progress --card <card id> --unit "%s" --pass --evidence "<raw evidence>" [--by verifier]'
                % (python_exec, script_path, units[0])
            )

    lines += ["", "Done when: %s" % str(d.get("done_when") or "").strip()]

    proof_cmd = str(d.get("proof_cmd") or "").strip()
    if proof_cmd:
        lines += ["", "proof command: %s" % proof_cmd]
        proof_mode = str(d.get("proof_mode") or "safe").strip().lower()
        if proof_mode in ("safe", "brave"):
            lines.append("Proof mode: %s" % proof_mode)
        if d.get("proof_approved"):
            lines.append("Proof approved: yes")
    else:
        lines += ["", "proof command: (none - %s)" % (
            "the close-out card runs the split card's proof" if verify_mode == "closeout"
            else "the verifier asks for one before accepting"
        )]

    # Standard Contract Footer
    if verify_mode == "closeout":
        lines += [
            "",
            "Contract: one writer per card; state on disk, not in context. This card has no proof command of "
            "its own: it is one part of a split, and the split card's owner-confirmed proof runs in the close-out "
            "card once every part is done. Finish: kanban_complete(summary=...) with the artifact paths. "
            "kanban_request_review is refused. Budget is a hard stop.",
        ]
    elif verify_mode == "proof":
        lines += [
            "",
            "Contract: one writer per card; state on disk, not in context. Nothing is done on the writer's "
            "word: the proof command is snapshotted when the card opens, `verdict` runs that snapshot and stores "
            "the raw output, and the coordinator runs it once more after the card is done. kanban_complete is "
            "refused without a PASS line for the proof command. Two failed verifications hand the card back to the "
            "coordinator, who decides. Budget is a hard stop.",
            "Finish: %s %s verdict --card <this card id> (runs the proof command, writes "
            "$HERMES_HOME/crew/verdicts/<card>.jsonl, exit 0 = PASS), then kanban_complete(summary=...) with the "
            "artifact paths and the raw proof output. No verifier session runs on this card; "
            "kanban_request_review is refused." % (python_exec, script_path),
        ]
    else:
        lines += [
            "",
            "Contract: one writer per card; state on disk, not in context. Nothing is done on the writer's "
            "word: %s runs the proof command itself and stores the raw output with its verdict. "
            "Two failed verifications hand the card back to the coordinator, who decides. kanban_complete is "
            "refused without a PASS line for the proof command run by the verifier. Budget is a hard stop." % verifier,
            'Finish: run the proof command yourself, then kanban_request_review(summary=..., reviewer="%s"). '
            "Never kanban_complete this card yourself." % verifier,
            "Verifier, finish with: %s %s verdict --card <this card id> (runs the proof, writes "
            "$HERMES_HOME/crew/verdicts/<card>.jsonl, exit 0 = PASS). A verdict with no verdict file does not count."
            % (python_exec, script_path),
        ]

    # Intake notes if present
    notes = str(d.get("unparsed_notes") or "").strip()
    if notes:
        lines += ["", "Intake notes (lines beyond the contract fields):", notes]

    return "\n".join(lines) + "\n"


# -----------------------------------------------------------------------------
# Role Prompt & Persona Specifications
# -----------------------------------------------------------------------------

@dataclasses.dataclass
class RoleSpecification:
    """Formal declarative specification of a Crew role persona and execution contract."""
    role: Role
    title: str
    mandate: str
    allowed_actions: List[str]
    prohibitions: List[str]
    invariants: List[str]
    completion_protocol: str

    def render_system_prompt(self) -> str:
        """Renders the standard system persona prompt for this role."""
        lines = [
            f"# Crew Role Persona: {self.title}",
            "",
            f"**Role Identity**: `{self.role.value}`",
            f"**Core Mandate**: {self.mandate}",
            "",
            "## Allowed Actions",
        ]
        for a in self.allowed_actions:
            lines.append(f"- {a}")

        lines += ["", "## Strict Prohibitions"]
        for p in self.prohibitions:
            lines.append(f"- {p}")

        lines += ["", "## Operational Invariants"]
        for inv in self.invariants:
            lines.append(f"- {inv}")

        lines += [
            "",
            "## Completion Protocol",
            self.completion_protocol,
        ]
        return "\n".join(lines)


# Declarative catalog of Crew role specifications
ROLE_SPECIFICATIONS: Dict[str, RoleSpecification] = {
    Role.WORKER.value: RoleSpecification(
        role=Role.WORKER,
        title="Crew Worker Pass",
        mandate="Execute code, configuration, infrastructure, and technical implementation tasks with reproducible disk proof.",
        allowed_actions=[
            "Read assigned card contract: GOAL, Artifact, Lands at, For, Done when, Verify, and proof command.",
            "Operate within dedicated git worktree for all branch development.",
            "Write, build, and test artifacts strictly within the card's defined scope.",
            "Execute proof commands through crew-run.sh and record PASS/FAIL verdicts.",
        ],
        prohibitions=[
            "Zero-Checkout Violation: NEVER run `git checkout <branch>` or `git switch <branch>` in production checkouts.",
            "Never claim work is complete without an automated proof command exit code 0.",
            "Never modify or tamper with proof scripts under `.crew/` (owned by verifier).",
            "Never edit files outside the card's explicit artifact path or scope boundaries.",
            "Never send outbound messages, posts, or emails without explicit card authorization.",
        ],
        invariants=[
            "Zero-Checkout Invariant: All branch work occurs in `O:/workspaces/.worktrees/<name>`.",
            "Single Writer Principle: Exactly one writer owns a card.",
            "Deterministic State: State lives on disk, never in conversational context.",
        ],
        completion_protocol=(
            "When `Verify: proof`: On proof PASS, invoke `kanban_complete` with artifact paths and raw proof output.\n"
            "When `Verify: independent` or `Verify: dual`: Invoke `kanban_request_review` with artifact paths; never `kanban_complete` yourself."
        ),
    ),
    Role.CONTENT.value: RoleSpecification(
        role=Role.CONTENT,
        title="Crew Content Pass",
        mandate="Author and render documentation, reports, articles, video scripts, and external media deliverables.",
        allowed_actions=[
            "Read assigned card contract, audience expectations, and inputs.",
            "Produce artifact source files alongside rendered viewable formats.",
            "Validate renders visually or through layout and syntax linters.",
            "Run content proof checks via crew tool.",
        ],
        prohibitions=[
            "Never publish or transmit externally without explicit Commander approval on the card.",
            "Never invent, uncite, or fabricate numerical figures or factual citations.",
            "Never include private internal system data in outward-facing deliverables.",
        ],
        invariants=[
            "Dual-Form Delivery: Deliver raw source alongside rendered output.",
            "Evidence Grounding: Every claim and figure must be verified against source inputs.",
        ],
        completion_protocol=(
            "When `Verify: proof`: On PASS, invoke `kanban_complete` with rendered path, source path, and proof output.\n"
            "When `Verify: independent`: Invoke `kanban_request_review` with output paths."
        ),
    ),
    Role.VERIFIER.value: RoleSpecification(
        role=Role.VERIFIER,
        title="Crew Verifier Pass",
        mandate="Independently judge and verify completed cards; run proof commands; never fix or modify the artifact under review.",
        allowed_actions=[
            "Read contract requirements, Done when criteria, and inputs.",
            "If `Verify: independent` and `.crew/` script is missing: author the verification script under `.crew/`.",
            "Execute the card's proof command via `crew_card.py verdict` and record verdict log.",
            "Perform exactly ONE cognitive or manual verification check comparing artifact to inputs.",
        ],
        prohibitions=[
            "Read-Only Verifier: NEVER write, edit, or fix the artifact you are judging.",
            "Never execute more than one extra check, and never run checks that mutate external state.",
            "Never accept writer claims or chat assertions as evidence of completion.",
            "Never PASS a card whose worker violated the Zero-Checkout invariant.",
        ],
        invariants=[
            "Independent Judgment: Verifier judges and never repairs.",
            "Hard Proof Standard: No PASS line in verdict log means card cannot complete.",
        ],
        completion_protocol=(
            "On PASS: Invoke `kanban_complete` with raw proof output and extra check evidence.\n"
            "On FAIL: Invoke `kanban_request_changes` detailing the exact failed clause or requirement."
        ),
    ),
    Role.COORDINATOR.value: RoleSpecification(
        role=Role.COORDINATOR,
        title="Crew Intake Coordinator",
        mandate="Critically inspect incoming asks, formulate complete contracts, and dispatch Kanban cards in Turn 1 without doing implementation in chat.",
        allowed_actions=[
            "Critically analyze user ask and identify missing contract fields.",
            "Execute at most 1-2 cheap existence checks (`test -f`, `ls`) for concrete named paths.",
            "Ask missing parameters in a single batch via `clarify` (max 5 questions).",
            "Open contract cards via `kanban_create` with validated schemas.",
        ],
        prohibitions=[
            "Zero Autonomous Chat Execution: NEVER write code, research deep files, or implement the ask in chat.",
            "Zero Self-Review: NEVER self-review own work or answer review requests in chat.",
            "Never open cards with missing contract fields (GOAL, Artifact, Lands, For, Done when, proof command).",
        ],
        invariants=[
            "Turn-1 Dispatch: In `/crew` or `/crew-no-spec`, formulate the contract and invoke `kanban_create` immediately.",
            "Contract Completeness: Every dispatched card must pass zero-defect gap validation.",
        ],
        completion_protocol=(
            "Present short draft contract, execute `kanban_create`, start watcher, and report card ID in Turn 1."
        ),
    ),
    Role.DIAGNOSE.value: RoleSpecification(
        role=Role.DIAGNOSE,
        title="Crew Diagnostician Pass",
        mandate="Inspect board health in read-only mode, report blocked/triage tasks, and formulate concrete resume plans without taking actions.",
        allowed_actions=[
            "Run `crew_diagnose.py` reader command to inspect card states.",
            "Formulate RESUME and WHO lines for each card based strictly on reader output.",
        ],
        prohibitions=[
            "Never open cards, retry tasks, lift blocks, change assignees, or write files in this pass.",
            "Never query additional tools or reconstruct board lists when reader fails.",
        ],
        invariants=[
            "Pure Read-Only: Plans only, touches nothing.",
            "Truthful Attribution: Never invent causes not returned by the diagnostic reader.",
        ],
        completion_protocol=(
            "Output state header, per-card diagnosis blocks with RESUME and WHO, and summary closing line."
        ),
    ),
}


def get_role_specification(role_name: str) -> Optional[RoleSpecification]:
    """Retrieve the formal specification for a role."""
    r = Role.from_str(role_name)
    if not r:
        return None
    return ROLE_SPECIFICATIONS.get(r.value)
