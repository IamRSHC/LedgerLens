"""
Data access layer — all DB queries live here.
Business logic never imports sqlalchemy directly.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.models import (
    Order, Settlement, BankTransaction,
    ReconciliationRun, ReconciliationResult,
    Exception as Exc, AIInvestigation, AuditLog,
)


# ── Exception lifecycle (Step 1.2) ─────────────────────────────────────────────
# Single source of truth for exception status values and the transitions between
# them. Callers (API + reconciliation) must go through transition_exception()
# so every state change is validated and audited in one place.

STATUS_OPEN             = "open"
STATUS_AI_INVESTIGATING = "ai_investigating"
STATUS_AUTO_RESOLVED    = "auto_resolved"
STATUS_MANUAL_REVIEW    = "manual_review"
STATUS_RESOLVED         = "resolved"

TERMINAL_STATUSES = {STATUS_AUTO_RESOLVED, STATUS_RESOLVED}

ALLOWED_TRANSITIONS = {
    STATUS_OPEN:              {STATUS_AI_INVESTIGATING, STATUS_MANUAL_REVIEW, STATUS_RESOLVED},
    STATUS_AI_INVESTIGATING:  {STATUS_AUTO_RESOLVED, STATUS_MANUAL_REVIEW, STATUS_OPEN},
    STATUS_MANUAL_REVIEW:     {STATUS_RESOLVED},
    STATUS_AUTO_RESOLVED:     set(),  # terminal
    STATUS_RESOLVED:          set(),  # terminal
}


class InvalidTransition(Exception):
    def __init__(self, exception_id: str, from_status: str, to_status: str):
        self.exception_id = exception_id
        self.from_status  = from_status
        self.to_status    = to_status
        super().__init__(
            f"Invalid lifecycle transition for {exception_id}: "
            f"{from_status!r} → {to_status!r}"
        )


def transition_exception(
    db: Session,
    exception_id: str,
    to_status: str,
    actor: str = "system",
    resolution: Optional[str] = None,
    detail: Optional[str] = None,
    action: Optional[str] = None,
) -> Exc:
    """
    Move an exception through its lifecycle atomically:
      - validate the from→to transition against ALLOWED_TRANSITIONS
      - update status / resolution / resolved_at
      - emit one audit_log entry describing the transition

    Idempotent when to_status == current status (returns the row unchanged, no
    duplicate audit entry). Raises InvalidTransition for disallowed moves so the
    caller can choose how to surface the error.
    """
    exc = db.query(Exc).filter(Exc.exception_id == exception_id).first()
    if not exc:
        return None
    from_status = exc.status
    if from_status == to_status:
        return exc  # idempotent no-op
    allowed = ALLOWED_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise InvalidTransition(exception_id, from_status, to_status)

    updates = {"status": to_status}
    if resolution is not None:
        updates["resolution"] = resolution
    if to_status in TERMINAL_STATUSES:
        updates["resolved_at"] = datetime.utcnow()
    db.query(Exc).filter(Exc.exception_id == exception_id).update(updates)
    db.commit()

    log_action(
        db, exc.run_id, "exception", exception_id,
        action or f"transition:{from_status}->{to_status}",
        actor=actor, detail=detail,
    )
    db.refresh(exc)
    return exc


# ── Orders ─────────────────────────────────────────────────────────────────────
def get_orders(db: Session, skip=0, limit=100) -> List[Order]:
    return db.query(Order).offset(skip).limit(limit).all()

def get_order(db: Session, order_id: str) -> Optional[Order]:
    return db.query(Order).filter(Order.order_id == order_id).first()

def bulk_insert_orders(db: Session, rows: list):
    objs = [Order(**{k: v for k, v in r.items() if v is not None and k != "id"}) for r in rows]
    db.bulk_save_objects(objs); db.commit()

def clear_orders(db: Session):
    db.query(Order).delete(); db.commit()


# ── Settlements ────────────────────────────────────────────────────────────────
def get_settlements(db: Session, skip=0, limit=100) -> List[Settlement]:
    return db.query(Settlement).offset(skip).limit(limit).all()

def get_settlement_by_utr(db: Session, utr: str) -> Optional[Settlement]:
    return db.query(Settlement).filter(Settlement.utr == utr).first()

def bulk_insert_settlements(db: Session, rows: list):
    objs = [Settlement(**{k: v for k, v in r.items() if k != "id"}) for r in rows]
    db.bulk_save_objects(objs); db.commit()

def clear_settlements(db: Session):
    db.query(Settlement).delete(); db.commit()


# ── Bank transactions ──────────────────────────────────────────────────────────
def get_bank_txns(db: Session, skip=0, limit=100) -> List[BankTransaction]:
    return db.query(BankTransaction).offset(skip).limit(limit).all()

def get_bank_txn_by_utr(db: Session, utr: str) -> Optional[BankTransaction]:
    return db.query(BankTransaction).filter(BankTransaction.utr == utr).first()

def bulk_insert_bank_txns(db: Session, rows: list):
    objs = [BankTransaction(**{k: v for k, v in r.items() if k != "id"}) for r in rows]
    db.bulk_save_objects(objs); db.commit()

def clear_bank_txns(db: Session):
    db.query(BankTransaction).delete(); db.commit()


# ── Reconciliation runs ────────────────────────────────────────────────────────
def create_run(db: Session, run_id: str) -> ReconciliationRun:
    run = ReconciliationRun(run_id=run_id)
    db.add(run); db.commit(); db.refresh(run); return run

def get_run(db: Session, run_id: str) -> Optional[ReconciliationRun]:
    return db.query(ReconciliationRun).filter(ReconciliationRun.run_id == run_id).first()

def get_runs(db: Session, skip=0, limit=20) -> List[ReconciliationRun]:
    return db.query(ReconciliationRun).order_by(ReconciliationRun.started_at.desc()).offset(skip).limit(limit).all()

def update_run(db: Session, run_id: str, **kwargs):
    db.query(ReconciliationRun).filter(ReconciliationRun.run_id == run_id).update(kwargs)
    db.commit()


# ── Results ────────────────────────────────────────────────────────────────────
def bulk_insert_results(db: Session, results: list):
    objs = [ReconciliationResult(**r) for r in results]
    db.bulk_save_objects(objs); db.commit()

def insert_result(db: Session, r: dict) -> ReconciliationResult:
    """
    Insert a single ReconciliationResult row and return it with .id populated.

    Used by the reconciliation batch loop when it needs the freshly-assigned
    primary key so an Exception can be linked via result_id in the same
    transaction. bulk_save_objects() does not populate defaults; this is the
    single-row helper that does.
    """
    obj = ReconciliationResult(**r)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

def get_results(db: Session, run_id: str) -> List[ReconciliationResult]:
    return db.query(ReconciliationResult).filter(ReconciliationResult.run_id == run_id).all()

def get_result(db: Session, result_id: int) -> Optional[ReconciliationResult]:
    return db.query(ReconciliationResult).filter(ReconciliationResult.id == result_id).first()


# ── Exceptions ─────────────────────────────────────────────────────────────────
def create_exception(db: Session, exc: dict) -> Exc:
    obj = Exc(**exc); db.add(obj); db.commit(); db.refresh(obj); return obj

def get_exceptions(db: Session, run_id: Optional[str]=None, status: Optional[str]=None, skip=0, limit=100):
    q = db.query(Exc)
    if run_id:  q = q.filter(Exc.run_id == run_id)
    if status:  q = q.filter(Exc.status == status)
    return q.order_by(Exc.created_at.desc()).offset(skip).limit(limit).all()

def get_exception(db: Session, exception_id: str) -> Optional[Exc]:
    return db.query(Exc).filter(Exc.exception_id == exception_id).first()


# ── AI investigations ──────────────────────────────────────────────────────────

# Step 8.2: the exact set of columns callers may write. Anything else in the
# input dict is silently dropped rather than raising a TypeError that would
# otherwise abort the whole batch. Kept as a module-level constant so it's
# grep-able and stays in lockstep with the model.
_AI_INV_WRITABLE_COLS = {
    "exception_id",
    "root_cause",
    "classification",
    "confidence",
    "explanation",
    "recommended_action",
    "evidence",
    "tool_calls",
    "risk_level",
    "auto_resolved",
    "provider",
    "model",
    "fallback_reason",
}


def save_investigation(db: Session, inv: dict) -> AIInvestigation:
    """
    Persist one AIInvestigation row.

    Step 8.2 hardening: the input dict is filtered against `_AI_INV_WRITABLE_COLS`
    before construction. Unknown keys are silently dropped instead of raising
    TypeError — a defensive posture so a future caller passing an extra field
    doesn't crash a whole reconciliation batch. `id` and `investigated_at`
    are populated by the DB (autoincrement + DateTime default) and must not
    appear in `inv`.
    """
    clean = {k: v for k, v in inv.items() if k in _AI_INV_WRITABLE_COLS}
    obj = AIInvestigation(**clean); db.add(obj); db.commit(); db.refresh(obj); return obj

def get_investigation(db: Session, exception_id: str) -> Optional[AIInvestigation]:
    return db.query(AIInvestigation).filter(AIInvestigation.exception_id == exception_id).first()


# ── Audit ──────────────────────────────────────────────────────────────────────
def log_action(db: Session, run_id: Optional[str], entity_type: str, entity_id: str,
               action: str, actor: str = "system", detail: Optional[str] = None):
    entry = AuditLog(run_id=run_id, entity_type=entity_type, entity_id=entity_id,
                     action=action, actor=actor, detail=detail)
    db.add(entry); db.commit()

def get_audit_logs(db: Session, run_id: Optional[str]=None, skip=0, limit=200):
    q = db.query(AuditLog)
    if run_id: q = q.filter(AuditLog.run_id == run_id)
    return q.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
