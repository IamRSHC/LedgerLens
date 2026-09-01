"""
Controller policy — single authoritative implementation of risk evaluation
and auto-resolution eligibility (Step 2.1).

Preserves the exact behaviour that lived in `engine/classifier.py` before this
step. Steps 2.2 (deterministic risk override) and 2.3 (explicit allowlist)
will build on this without touching callers.

Rules (post-Step-2.2):
  - HUMAN_REVIEW_TYPES exceptions can never auto-resolve.
  - Risk is DETERMINISTIC (backend `evaluate_risk`) — the LLM's
    `investigation.risk_level` is preserved for observability but has NO
    authority over the eligibility decision.
  - `policy_risk == "high"` blocks auto-resolution.
  - confidence must meet `settings.auto_resolve_confidence` (default 0.85).
"""
from __future__ import annotations
from typing import Dict, Any

from app.config import settings
from app.controller.decisions import PolicyDecision


AUTO_RESOLVE_TYPES = {"partial_settlement", "date_mismatch"}
HUMAN_REVIEW_TYPES = {"unknown_transaction", "duplicate", "missing_settlement"}


# ── Risk ──────────────────────────────────────────────────────────────────────
def evaluate_risk(exception: Dict[str, Any], investigation: Dict[str, Any] | None = None) -> str:
    """
    Deterministic policy risk. Reads only from the exception fields; the
    `investigation` argument is accepted for signature parity with the legacy
    `classifier.risk_level(exc, inv)` shape but is ignored today. Step 2.2 may
    tighten this further.
    """
    exc_type = exception.get("exception_type", "")
    if exc_type in HUMAN_REVIEW_TYPES: return "high"
    delta = abs(exception.get("amount_delta") or 0)
    if delta > 10000: return "high"
    if delta > 1000:  return "medium"
    return "low"


# ── Auto-resolution eligibility ───────────────────────────────────────────────
def evaluate_auto_resolution(exception: Dict[str, Any], investigation: Dict[str, Any]) -> bool:
    """
    True iff the exception passes every current auto-resolution rule.

    Step 2.2: risk comes from the deterministic backend policy
    (`evaluate_risk`) — the LLM-provided `investigation.risk_level` is
    IGNORED for the gate. A high-confidence LLM verdict on a structurally
    high-risk exception (large delta, HUMAN_REVIEW_TYPE, etc.) still routes
    to manual review.
    """
    exc_type   = exception.get("exception_type", "")
    confidence = investigation.get("confidence", 0.0)
    policy_risk = evaluate_risk(exception, investigation)
    if exc_type in HUMAN_REVIEW_TYPES: return False
    if policy_risk == "high":          return False
    if confidence < settings.auto_resolve_confidence: return False
    return True


# ── Combined evaluation → PolicyDecision ──────────────────────────────────────
def evaluate_exception(exception: Dict[str, Any], investigation: Dict[str, Any]) -> PolicyDecision:
    """
    Run the full policy against an exception + its investigation and return a
    typed PolicyDecision. The resolver uses this to execute the transition.

    `PolicyDecision.risk_level` is the AUTHORITATIVE policy risk.
    `PolicyDecision.model_risk` is the raw model-provided value, kept for
    observability only and never consulted for decisions.
    """
    exc_type   = exception.get("exception_type", "")
    confidence = investigation.get("confidence", 0.0)
    model_risk = investigation.get("risk_level")   # may be None
    policy_risk = evaluate_risk(exception, investigation)

    eligible = evaluate_auto_resolution(exception, investigation)

    blockers = []
    if exc_type in HUMAN_REVIEW_TYPES:
        blockers.append(f"exception_type={exc_type} in HUMAN_REVIEW_TYPES")
    if policy_risk == "high":
        blockers.append("policy_risk=high")
    if confidence < settings.auto_resolve_confidence:
        blockers.append(f"confidence={confidence} < {settings.auto_resolve_confidence}")

    reason = "eligible" if eligible else "; ".join(blockers) or "policy_declined"
    action = "auto_resolve" if eligible else "manual_review"

    return PolicyDecision(
        risk_level=policy_risk,
        eligible_for_auto_resolution=eligible,
        decision=action,
        reason=reason,
        blockers=blockers,
        model_risk=model_risk,
    )
