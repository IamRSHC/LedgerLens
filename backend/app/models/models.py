from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True, nullable=False)
    merchant_id = Column(String, index=True)
    customer_id = Column(String)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    status = Column(String)
    payment_method = Column(String)
    created_at = Column(DateTime)
    reference_id = Column(String, index=True)
    reconciliation_results = relationship("ReconciliationResult", back_populates="order")

class Settlement(Base):
    __tablename__ = "settlements"
    id = Column(Integer, primary_key=True, index=True)
    settlement_id = Column(String, unique=True, index=True, nullable=False)
    order_id = Column(String, nullable=True, index=True)
    merchant_id = Column(String, index=True)
    gross_amount = Column(Float)
    fee = Column(Float)
    net_amount = Column(Float)
    utr = Column(String, index=True)
    status = Column(String)
    settled_at = Column(DateTime)

class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    id = Column(Integer, primary_key=True, index=True)
    bank_txn_id = Column(String, unique=True, index=True, nullable=False)
    utr = Column(String, index=True)
    credit_amount = Column(Float)
    debit_amount = Column(Float)
    narration = Column(String)
    transaction_date = Column(DateTime)
    value_date = Column(DateTime)
    bank = Column(String)

class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, unique=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_records = Column(Integer, default=0)
    matched = Column(Integer, default=0)
    exceptions = Column(Integer, default=0)
    match_rate = Column(Float, nullable=True)
    amount_reconciled = Column(Float, default=0.0)
    status = Column(String, default="pending")
    results = relationship("ReconciliationResult", back_populates="run")

class ReconciliationResult(Base):
    __tablename__ = "reconciliation_results"
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, ForeignKey("reconciliation_runs.run_id"), index=True)
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=True, index=True)
    settlement_id = Column(String, nullable=True)
    bank_txn_id = Column(String, nullable=True)
    match_type = Column(String)    # exact / fuzzy / unmatched
    match_score = Column(Float, nullable=True)
    status = Column(String)        # matched / exception  (Step 1.1: "review" retired)
    amount_delta = Column(Float, nullable=True)
    date_delta_days = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    run = relationship("ReconciliationRun", back_populates="results")
    order = relationship("Order", back_populates="reconciliation_results")
    exception = relationship("Exception", back_populates="result", uselist=False)

class Exception(Base):
    __tablename__ = "exceptions"
    id = Column(Integer, primary_key=True, index=True)
    exception_id = Column(String, unique=True, index=True)
    result_id = Column(Integer, ForeignKey("reconciliation_results.id"), unique=True)
    run_id = Column(String, index=True)
    order_id = Column(String, nullable=True, index=True)
    exception_type = Column(String)   # amount_mismatch / missing_settlement / etc.
    severity = Column(String)          # low / warning / critical
    amount_delta = Column(Float, nullable=True)
    status = Column(String, default="open")  # open / auto_resolved / manual_review / resolved
    resolution = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    result = relationship("ReconciliationResult", back_populates="exception")
    investigation = relationship("AIInvestigation", back_populates="exception", uselist=False)

class AIInvestigation(Base):
    __tablename__ = "ai_investigations"
    id = Column(Integer, primary_key=True, index=True)
    exception_id = Column(String, ForeignKey("exceptions.exception_id"), unique=True)
    root_cause = Column(String)
    classification = Column(String)
    confidence = Column(Float)
    explanation = Column(Text)
    recommended_action = Column(Text)
    evidence = Column(Text)      # JSON
    tool_calls = Column(Text)    # JSON
    risk_level = Column(String)  # low / medium / high (raw model view, observability only)
    auto_resolved = Column(Boolean, default=False)
    # Step 7.2: provenance columns. Nullable so historical rows survive.
    provider = Column(String, nullable=True)          # "groq" | "fallback"
    model = Column(String, nullable=True)             # e.g. "llama-3.3-70b-versatile"
    fallback_reason = Column(String, nullable=True)   # populated only when provider="fallback"
    investigated_at = Column(DateTime, default=datetime.utcnow)
    exception = relationship("Exception", back_populates="investigation")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, nullable=True, index=True)
    entity_type = Column(String)
    entity_id = Column(String)
    action = Column(String)
    actor = Column(String, default="system")
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
