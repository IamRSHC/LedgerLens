"""
Deterministic merchant profile lookup for `get_merchant_profile()` (Step 4.3).

Not a database — a small static configuration source keyed by the merchant
identifiers the synthetic generator emits (`MERCH-0001` … `MERCH-0005`).
Deterministic and traceable: same input → same output; auditable in one
place; no external service; no LLM-generated content.

If real merchant onboarding is added later (a `merchants` table or a
Supabase-backed config), swap this module's `PROFILES` for the actual data
source — the tool's public shape doesn't need to change.
"""
from __future__ import annotations
from typing import Dict, Any

# The five merchants the generator uses. Values chosen to line up with the
# Razorpay-style fee schedule the engine assumes elsewhere (2% standard,
# T+1..T+3 settlement, GST on fee at 18%).
PROFILES: Dict[str, Dict[str, Any]] = {
    "MERCH-0001": {"fee_rate": 0.02,  "settlement_lag_days": 2, "risk_tier": "standard"},
    "MERCH-0002": {"fee_rate": 0.02,  "settlement_lag_days": 2, "risk_tier": "standard"},
    "MERCH-0003": {"fee_rate": 0.02,  "settlement_lag_days": 2, "risk_tier": "standard"},
    # MERCH-0004: slightly elevated fee + longer settlement window → policy
    # should notice that "delta ≈ 2.5% of order" for this merchant is normal.
    "MERCH-0004": {"fee_rate": 0.025, "settlement_lag_days": 3, "risk_tier": "elevated"},
    "MERCH-0005": {"fee_rate": 0.02,  "settlement_lag_days": 2, "risk_tier": "standard"},
}
