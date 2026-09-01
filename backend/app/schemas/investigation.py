"""
Pydantic schema for the AI investigator's output (Milestone B / Step 3.1).

REPLACES the pre-3.1 arbitrary-dict approach that used `json.loads` +
substring recovery with no validation.

Contract:
  Groq  →  raw JSON  →  _parse_investigation()  →  InvestigationResult
                                                          │
                                                          ▼
                                        controller.policy.evaluate_exception
                                                          │
                                                          ▼
                                                    PolicyDecision
                                                          │
                                                          ▼
                                              controller.resolver.apply

The AI investigator emits data only. Risk and auto-resolution are decided
by controller.policy (Step 2.2) — NOT by anything in this schema.
`risk_level` here is preserved as OBSERVABILITY only.
"""
from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ── Classification taxonomy ───────────────────────────────────────────────────
# Union of:
#   (a) the labels the current system prompt tells the model to emit,
#   (b) the labels _stub_investigation produces after Step 3.1 normalization,
#   (c) the deterministic engine exception_type set (so root-cause labels can
#       align with the type when appropriate).
#
# `pending_settlement` (used by the pre-3.1 stub) is intentionally NOT here;
# the stub is updated to emit `missing_settlement` instead.
Classification = Literal[
    "settlement_fee",
    "timing_difference",
    "data_entry_error",
    "potential_fraud",
    "duplicate",
    "partial_payment",
    "missing_bank_record",
    "missing_settlement",
    "unknown",
]


class Evidence(BaseModel):
    """One piece of evidence supporting an investigation conclusion.

    Strict shape (extra='forbid') so a model that emits `{"label": "x", ...}`
    (the pre-3.1 format) will fail validation and force a re-emit or fallback.
    """
    model_config = ConfigDict(extra="forbid")

    source: str = Field(..., min_length=1, description="Which record produced this fact (e.g. 'settlement').")
    field: str  = Field(..., min_length=1, description="Which column on that record (e.g. 'gross_amount').")
    value: Any                                             # concrete value (number, string, etc.)
    description: Optional[str] = Field(None, description="Optional human note.")


class InvestigationResult(BaseModel):
    """Validated output of a single AI investigation.

    NOTE: `risk_level` is present but is diagnostic/observability only.
    Deterministic backend policy (`controller.policy.evaluate_risk`) is the
    single source of truth for risk. Step 2.2 removed LLM authority.
    """
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    root_cause:         str            = Field(..., min_length=1)
    classification:     Classification
    confidence:         float          = Field(..., ge=0.0, le=1.0)
    explanation:        str            = Field(..., min_length=1)
    recommended_action: str            = Field(..., min_length=1)
    evidence:           List[Evidence] = Field(default_factory=list)

    # Optional short summary (NOT chain-of-thought).
    reasoning_summary:  Optional[str]  = None

    # Diagnostic / raw model-supplied risk. Observability ONLY — see class docstring.
    risk_level:         Optional[str]  = None

    # ── Provenance (Step 7.2) ────────────────────────────────────────────────
    # Filled to distinguish live Groq output from a fallback stub so no report
    # can ever call a fallback "AI success".
    provider:           Optional[str]  = None   # "groq" | "fallback"
    model:              Optional[str]  = None   # e.g. "llama-3.3-70b-versatile" | "fallback-rule-engine"
    fallback_reason:    Optional[str]  = None   # populated only when provider="fallback":
                                                # missing_api_key | authentication_error |
                                                # rate_limit_exhausted | timeout | network_error |
                                                # validation_failure | tool_budget_exhausted |
                                                # max_rounds_reached | unknown_error

    # Diagnostic list of tool invocations the agent made during this
    # investigation. Loose typing since it's audit-only; serialised as JSON
    # into ai_investigations.tool_calls by the reconciliation batch.
    tool_calls:         List[Dict[str, Any]] = Field(default_factory=list)
