from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class OrderOut(BaseModel):
    order_id: str
    merchant_id: str
    amount: float
    currency: str
    status: str
    payment_method: str
    created_at: datetime
    class Config: from_attributes = True

class SettlementOut(BaseModel):
    settlement_id: str
    order_id: Optional[str]
    gross_amount: float
    fee: float
    net_amount: float
    utr: str
    status: str
    settled_at: datetime
    class Config: from_attributes = True

class ExceptionOut(BaseModel):
    exception_id: str
    order_id: Optional[str]
    exception_type: str
    severity: str
    amount_delta: Optional[float]
    status: str
    resolution: Optional[str]
    created_at: datetime
    class Config: from_attributes = True

class InvestigationOut(BaseModel):
    """
    Typed API view of a persisted AIInvestigation row.

    Step 8.2: the schema now surfaces the full 11-field investigation contract
    the plan requires — including provider / model / fallback_reason (added
    to the DB in Milestone D) and `investigated_at` (the persisted equivalent
    of the plan's `created_at`).

    All Milestone-D and pre-Milestone-D historical rows validate against this
    schema: fields absent on older rows come back as `None` because their
    columns are nullable.
    """
    root_cause: str
    classification: str
    confidence: float
    explanation: Optional[str] = None
    recommended_action: Optional[str] = None
    evidence: Optional[str] = None          # JSON string of Evidence[] (Step 3.1)
    tool_calls: Optional[str] = None        # JSON string of tool metadata (Step 5.3)
    risk_level: Optional[str] = None        # raw model risk — observability only (Step 3.2)
    auto_resolved: bool
    # ── Step 7.2 provenance (added in Milestone D; surfaced typed in Step 8.2) ──
    provider: Optional[str] = None          # "groq" | "fallback"
    model: Optional[str] = None             # e.g. "openai/gpt-oss-20b" | "fallback-rule-engine"
    fallback_reason: Optional[str] = None   # populated only when provider="fallback"
    # ── Timestamp (plan calls it created_at; column is investigated_at) ─────────
    investigated_at: Optional[datetime] = None
    class Config: from_attributes = True

class ReconciliationRunOut(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_records: int
    matched: int
    exceptions: int
    match_rate: Optional[float]
    amount_reconciled: float
    status: str
    class Config: from_attributes = True

class AuditLogOut(BaseModel):
    entity_type: str
    entity_id: str
    action: str
    actor: str
    detail: Optional[str]
    created_at: datetime
    class Config: from_attributes = True

class RunRequest(BaseModel):
    orders_csv: Optional[str] = None      # base64 or path — None = use generated data
    settlements_csv: Optional[str] = None
    bank_csv: Optional[str] = None

class ResolveRequest(BaseModel):
    resolution: str
    actor: str = "user"

class FlagRequest(BaseModel):
    reason: str = "Flagged for manual review"
    actor: str = "user"

class DashboardStats(BaseModel):
    total_records: int
    matched: int
    exceptions: int
    match_rate: float
    amount_reconciled: float
    auto_resolved: int
    pending_review: int
    exception_breakdown: dict
    severity_breakdown: dict
