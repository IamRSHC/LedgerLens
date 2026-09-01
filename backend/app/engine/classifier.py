"""
Classify and score exceptions for risk-based routing.
Low risk  → auto-resolve candidate
High risk → human review required
"""
from app.config import settings

AUTO_RESOLVE_TYPES = {"partial_settlement", "date_mismatch"}
HUMAN_REVIEW_TYPES = {"unknown_transaction", "duplicate", "missing_settlement"}

def should_auto_resolve(exception: dict, investigation: dict) -> bool:
    """
    Authoritative auto-resolution gate. Threshold comes from
    `settings.auto_resolve_confidence` (Step 1.7) so backend and frontend can
    never diverge again. Frontend consumes the resulting boolean via
    `investigation.auto_resolved`; it must NOT re-derive eligibility itself.
    """
    exc_type   = exception.get("exception_type", "")
    confidence = investigation.get("confidence", 0.0)
    risk       = investigation.get("risk_level", "high")
    if exc_type in HUMAN_REVIEW_TYPES: return False
    if risk == "high":                 return False
    if confidence < settings.auto_resolve_confidence: return False
    return True

def risk_level(exception: dict, investigation: dict) -> str:
    exc_type = exception.get("exception_type", "")
    if exc_type in HUMAN_REVIEW_TYPES: return "high"
    delta = abs(exception.get("amount_delta") or 0)
    if delta > 10000: return "high"
    if delta > 1000:  return "medium"
    return "low"
