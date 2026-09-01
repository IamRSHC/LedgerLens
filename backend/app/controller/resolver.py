"""
Controller resolver — the single application-layer component that executes a
policy-approved lifecycle transition (Step 2.1, hardened in Step 2.4).

Contract:
  AI INVESTIGATES  →  POLICY DECIDES  →  RESOLVER EXECUTES  →  REPO PERSISTS  →  AUDIT

  This module is the ONLY controller-side path from a PolicyDecision to a
  lifecycle-state change. It:
    - executes ONLY the decision it receives (no policy re-derivation);
    - validates that the decision is internally consistent BEFORE touching
      the database — an inconsistent decision raises InconsistentDecision
      and no DB mutation / no audit row is produced;
    - verifies the target exception exists BEFORE any mutation;
    - relies on `repo.transition_exception` for atomic status + audit and
      for idempotency (same-state → no-op, no duplicate audit row);
    - never reads `investigation.risk_level` for policy purposes — the
      authoritative risk is on `decision.risk_level` (Step 2.2), and the
      raw model value is recorded via `decision.model_risk` for audit only.

Human-driven finalization (`POST /api/exceptions/{id}/resolve` and `.../flag`)
is a SEPARATE surface implemented in `api/exceptions.py`; it is NOT a
controller resolution and does not flow through this module.
"""
from __future__ import annotations
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

import app.repository.repository as repo
from app.controller.decisions import PolicyDecision


class InconsistentDecision(ValueError):
    """
    Raised when a PolicyDecision's fields disagree with each other, e.g.
        decision.decision == "auto_resolve"  but  eligible_for_auto_resolution=False
    The resolver refuses to execute — no DB mutation, no audit row.
    """


def _validate(decision: PolicyDecision) -> None:
    if decision.decision not in ("auto_resolve", "manual_review"):
        raise InconsistentDecision(
            f"unknown decision={decision.decision!r} "
            f"(allowed: 'auto_resolve', 'manual_review')"
        )
    if decision.decision == "auto_resolve" and not decision.eligible_for_auto_resolution:
        raise InconsistentDecision(
            "decision='auto_resolve' but eligible_for_auto_resolution=False — "
            "policy result is contradictory; refusing to auto-resolve"
        )
    if decision.decision == "manual_review" and decision.eligible_for_auto_resolution:
        raise InconsistentDecision(
            "decision='manual_review' but eligible_for_auto_resolution=True — "
            "policy result is contradictory; refusing to route to manual review "
            "without an explicit blocker"
        )


def apply(
    db: Session,
    exception_id: str,
    decision: PolicyDecision,
    investigation: Dict[str, Any],
):
    """
    Execute the lifecycle transition dictated by a PolicyDecision.

      decision.decision == "auto_resolve"   → STATUS_AUTO_RESOLVED   actor="ai"
      decision.decision == "manual_review"  → STATUS_MANUAL_REVIEW   actor="system"

    Ordering (all pre-mutation):
      1. Validate decision internal consistency        → InconsistentDecision
      2. Look up the exception                         → ValueError if missing
      3. Delegate to repo.transition_exception         → InvalidTransition on illegal move
         which handles idempotency (same-state → no-op, no duplicate audit).

    On success returns the updated Exception row (unchanged on an idempotent
    no-op). Raises rather than silently mutating or writing a misleading
    audit row.
    """
    _validate(decision)

    exc = repo.get_exception(db, exception_id)
    if exc is None:
        # No mutation. No audit. Caller sees a clean ValueError.
        raise ValueError(f"Exception {exception_id!r} not found; resolver refused to execute")

    conf = investigation.get("confidence")
    blockers_str = ",".join(decision.blockers) if decision.blockers else "none"

    if decision.decision == "auto_resolve":
        return repo.transition_exception(
            db, exception_id, repo.STATUS_AUTO_RESOLVED,
            actor="ai",
            resolution=investigation.get("recommended_action"),
            action="auto_resolved",
            detail=(f"confidence={conf} policy_risk={decision.risk_level} "
                    f"model_risk={decision.model_risk}"),
        )

    # decision == "manual_review"
    return repo.transition_exception(
        db, exception_id, repo.STATUS_MANUAL_REVIEW,
        actor="system",
        resolution="Requires manual review — policy did not auto-resolve",
        action="policy_manual_review",
        detail=(f"confidence={conf} policy_risk={decision.risk_level} "
                f"model_risk={decision.model_risk} blockers={blockers_str}"),
    )
