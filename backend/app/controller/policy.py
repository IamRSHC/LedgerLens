"""
Controller policy — single authoritative implementation of risk evaluation
and auto-resolution eligibility (Step 2.1).

Preserves the exact behaviour that lived in `engine/classifier.py` before this
step. Steps 2.2 (deterministic risk override) and 2.3 (explicit allowlist)
will build on this without touching callers.

Rules kept unchanged in Step 2.1:
  - HUMAN_REVIEW_TYPES exceptions can never auto-resolve.
  - risk_level == "high" blocks auto-resolution.
  - confidence must meet settings.auto_resolve_confidence (default 0.85).
  - risk_level as seen by the eligibility check is whatever the investigation
    provides — the LLM's authority over risk is intentionally left in place
    here and will be removed in Step 3.2.
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
    True iff the exception passes every current auto-resolution rule. Identical
    behaviour to the pre-2.1 `classifier.should_auto_resolve`.
    """
    exc_type   = exception.get("exception_type", "")
    confidence = investigation.get("confidence", 0.0)
    risk       = investigation.get("risk_level", "high")
    if exc_type in HUMAN_REVIEW_TYPES: return False
    if risk == "high":                 return False
    if confidence < settings.auto_resolve_confidence: return False
    return True


# ── Combined evaluation → PolicyDecision ──────────────────────────────────────
def evaluate_exception(exception: Dict[str, Any], investigation: Dict[str, Any]) -> PolicyDecision:
    """
    Run the full policy against an exception + its investigation and return a
    typed PolicyDecision. The resolver uses this to execute the transition.
    """
    exc_type = exception.get("exception_type", "")
    confidence = investigation.get("confidence", 0.0)
    inv_risk = investigation.get("risk_level", "high")

    # Deterministic (policy-computed) risk. Not authoritative for eligibility
    # yet — Step 2.2 will make it so. Surfaced here for the audit trail and
    # any consumer that wants policy's own view.
    policy_risk = evaluate_risk(exception, investigation)

    eligible = evaluate_auto_resolution(exception, investigation)

    blockers = []
    if exc_type in HUMAN_REVIEW_TYPES:
        blockers.append(f"exception_type={exc_type} in HUMAN_REVIEW_TYPES")
    if inv_risk == "high":
        blockers.append("investigation.risk_level=high")
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
    )
