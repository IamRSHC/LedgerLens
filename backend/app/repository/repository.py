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

def get_results(db: Session, run_id: str) -> List[ReconciliationResult]:
    return db.query(ReconciliationResult).filter(ReconciliationResult.run_id == run_id).all()


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

def resolve_exception(db: Session, exception_id: str, status: str, resolution: str, actor: str):
    db.query(Exc).filter(Exc.exception_id == exception_id).update({
        "status": status, "resolution": resolution, "resolved_at": datetime.utcnow()
    }); db.commit()


# ── AI investigations ──────────────────────────────────────────────────────────
def save_investigation(db: Session, inv: dict) -> AIInvestigation:
    obj = AIInvestigation(**inv); db.add(obj); db.commit(); db.refresh(obj); return obj

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
