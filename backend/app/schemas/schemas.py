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
    root_cause: str
    classification: str
    confidence: float
    explanation: str
    recommended_action: str
    evidence: Optional[str]
    tool_calls: Optional[str]
    risk_level: str
    auto_resolved: bool
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
