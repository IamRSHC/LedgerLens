"""
Typed representation of what the policy decided and why (Step 2.1).

Deliberately small: five fields, one dataclass. This is a data record, not a
framework — the reasoning still lives in policy.py; this just names what the
policy produced so downstream code (resolver, API responses, audit trail)
never has to re-derive it.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Literal, Optional

DecisionAction = Literal["auto_resolve", "manual_review"]


@dataclass
class PolicyDecision:
    # Deterministic risk classification from the policy engine.
    # AUTHORITATIVE — this is what gates auto-resolution (Step 2.2).
    # Values: "low" | "medium" | "high".
    risk_level: str

    # Whether the exception passes ALL current auto-resolution rules.
    # Set by policy.evaluate_auto_resolution().
    eligible_for_auto_resolution: bool

    # Terminal-of-this-batch action the resolver will execute.
    decision: DecisionAction

    # Short human-readable explanation. If eligible, this is "eligible";
    # otherwise it summarises the blockers.
    reason: str

    # Structured list of the specific rules that blocked auto-resolution
    # (empty when eligible). Useful for audit detail and future UI.
    blockers: List[str] = field(default_factory=list)

    # Step 2.2: the model's OWN risk_level as supplied by the investigation
    # (LLM or stub). Preserved for observability + audit only — never used
    # to decide anything. Compare with `risk_level` to spot LLM/policy drift.
    model_risk: Optional[str] = None
