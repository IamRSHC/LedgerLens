"""
Controller resolver — the single application-layer component that executes a
policy-approved lifecycle transition (Step 2.1).

Wraps `repository.transition_exception` so the AI investigator has no direct
path to mutate financial state. The AI's role is to produce an investigation
dict; the policy decides what to do; this module does it.

Step 2.4 will formalise this further (a resolution command object). For 2.1
the surface is a single `apply()` function.
"""
from __future__ import annotations
from typing import Dict, Any

from sqlalchemy.orm import Session

import app.repository.repository as repo
from app.controller.decisions import PolicyDecision


def apply(
    db: Session,
    exception_id: str,
    decision: PolicyDecision,
    investigation: Dict[str, Any],
):
    """
    Execute the transition dictated by a PolicyDecision.

      eligible_for_auto_resolution=True  → STATUS_AUTO_RESOLVED (actor="ai")
      eligible_for_auto_resolution=False → STATUS_MANUAL_REVIEW (actor="system")

    Returns the updated Exception row. Raises repo.InvalidTransition when the
    requested transition is not permitted from the current lifecycle state.
    """
    conf = investigation.get("confidence")

    if decision.eligible_for_auto_resolution:
        return repo.transition_exception(
            db, exception_id, repo.STATUS_AUTO_RESOLVED,
            actor="ai",
            resolution=investigation.get("recommended_action"),
            action="auto_resolved",
            detail=f"confidence={conf} policy_risk={decision.risk_level} model_risk={decision.model_risk}",
        )

    blockers_str = ",".join(decision.blockers) if decision.blockers else "none"
    return repo.transition_exception(
        db, exception_id, repo.STATUS_MANUAL_REVIEW,
        actor="system",
        resolution="Requires manual review — policy did not auto-resolve",
        action="policy_manual_review",
        detail=f"confidence={conf} policy_risk={decision.risk_level} model_risk={decision.model_risk} blockers={blockers_str}",
    )
