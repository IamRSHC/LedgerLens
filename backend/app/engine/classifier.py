"""
Compatibility shim (Step 2.1).

The authoritative implementation of risk evaluation and auto-resolution
eligibility now lives in `app.controller.policy`. This module re-exports the
legacy names so existing importers keep working without modification:

  - `app.agent.investigator`   still imports `risk_level`, `should_auto_resolve`
                               from here (unchanged in Step 2.1).
  - `app.api.reconciliation`   was migrated to use the controller directly
                               in Step 2.1, but this shim remains for any
                               external caller or future re-import.

New code MUST import from `app.controller.policy` / `app.controller.resolver`.
"""
from app.controller.policy import (
    AUTO_RESOLVE_TYPES,
    HUMAN_REVIEW_TYPES,
    evaluate_risk as risk_level,
    evaluate_auto_resolution as should_auto_resolve,
)

__all__ = [
    "AUTO_RESOLVE_TYPES",
    "HUMAN_REVIEW_TYPES",
    "risk_level",
    "should_auto_resolve",
]
