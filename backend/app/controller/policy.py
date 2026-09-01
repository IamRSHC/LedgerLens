"""
Controller policy — single authoritative implementation of risk evaluation
and auto-resolution eligibility (Step 2.1).

Preserves the exact behaviour that lived in `engine/classifier.py` before this
step. Steps 2.2 (deterministic risk override) and 2.3 (explicit allowlist)
will build on this without touching callers.

Rules (post-Step-2.3):
  Auto-resolution requires ALL of the following. Missing any one → manual_review.

    1. exception_type ∉ HUMAN_REVIEW_TYPES              (structural blacklist)
    2. exception_type ∈ AUTO_RESOLVE_TYPES              (positive allowlist)
    3. policy_risk != "high"                            (deterministic risk gate)
    4. confidence >= settings.auto_resolve_confidence   (evidence quality gate)

  Risk is DETERMINISTIC (backend `evaluate_risk`) — the LLM's
  `investigation.risk_level` is preserved for observability but has NO
  authority over the eligibility decision (Step 2.2).

  The positive allowlist means anything NOT explicitly enumerated defaults to
  manual review, regardless of confidence. This is the conservative posture
  called out by Section 2.3 of the plan.
"""
from __future__ import annotations
from typing import Dict, Any

from app.config import settings
from app.controller.decisions import PolicyDecision


# Step 2.3: positive allowlist. An exception may only auto-resolve if its
# type is in this set AND every other rule in `evaluate_auto_resolution` also
# passes (policy_risk != "high", confidence >= threshold).
#
# Why each of these is on the allowlist:
#   - date_mismatch      : underlying money moved (bank cross-check clean); only
#                          the settlement timing drifted. amount_delta is
#                          typically 0 so policy_risk stays low. Safe when
#                          confidence is high.
#   - partial_settlement : common when fees/refunds are netted off the gross;
#                          large deltas are still caught by the deterministic
#                          policy_risk gate (|delta| > 10_000 → high → blocked),
#                          so only small, high-confidence partials get through.
#
# Everything not listed here defaults to manual review — including
# amount_mismatch, missing_bank_record, low_confidence_match, and unclassified.
AUTO_RESOLVE_TYPES = {"partial_settlement", "date_mismatch"}

# Step 1.2 / 2.1: hard structural blacklist. These types can never
# auto-resolve because the underlying situation always requires a human
# to inspect actual money movement:
#   - unknown_transaction : settlement with no matching order — potential fraud
#   - duplicate           : same order settled twice — potential double-payment
#   - missing_settlement  : order billed but no settlement seen — potential loss
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

    Post-Step-2.3 gate order:
      1. HUMAN_REVIEW_TYPES (structural blacklist)  → block
      2. AUTO_RESOLVE_TYPES (positive allowlist)    → block if type NOT listed
      3. policy_risk (deterministic)                → block if "high"
      4. confidence                                 → block if < threshold

    Step 2.2 rule preserved: risk comes from `evaluate_risk`, NOT from
    `investigation.risk_level`.
    """
    exc_type   = exception.get("exception_type", "")
    confidence = investigation.get("confidence", 0.0)
    policy_risk = evaluate_risk(exception, investigation)
    if exc_type in HUMAN_REVIEW_TYPES:      return False
    if exc_type not in AUTO_RESOLVE_TYPES:  return False   # Step 2.3
    if policy_risk == "high":               return False
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
    if exc_type not in AUTO_RESOLVE_TYPES:
        blockers.append(f"exception_type={exc_type} not in AUTO_RESOLVE_TYPES (allowlist)")
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
