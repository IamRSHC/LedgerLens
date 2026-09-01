"""
Controller package (Step 2.1).

    AI investigates.  POLICY decides.  RESOLVER executes.

- policy.py    — evaluate risk / auto-resolution eligibility (single source of truth).
- decisions.py — typed PolicyDecision returned by policy.
- resolver.py  — the ONLY application-layer component that runs a policy-approved
                 lifecycle transition. Wraps repository.transition_exception so
                 the AI can never mutate financial rows directly.

`app.engine.classifier` remains a thin compatibility shim that re-exports the
legacy names (`should_auto_resolve`, `risk_level`, HUMAN_REVIEW_TYPES,
AUTO_RESOLVE_TYPES) — it now delegates here. New code should import from
`app.controller.policy` / `app.controller.resolver` directly.
"""
