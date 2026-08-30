"""
Tool definitions for the AI Investigator.
Each tool fetches context from the DB and returns a dict the LLM can reason over.
"""
import json
from sqlalchemy.orm import Session
from app.models.models import Order, Settlement, BankTransaction, Exception as Exc
import app.repository.repository as repo


def get_transaction(db: Session, order_id: str) -> dict:
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order: return {"error": f"Order {order_id} not found"}
    return {"order_id": order.order_id, "amount": order.amount, "status": order.status,
            "payment_method": order.payment_method, "created_at": str(order.created_at),
            "reference_id": order.reference_id}

def get_settlement(db: Session, settlement_id: str) -> dict:
    s = db.query(Settlement).filter(Settlement.settlement_id == settlement_id).first()
    if not s: return {"error": f"Settlement {settlement_id} not found"}
    return {"settlement_id": s.settlement_id, "gross_amount": s.gross_amount,
            "fee": s.fee, "net_amount": s.net_amount, "utr": s.utr,
            "settled_at": str(s.settled_at), "status": s.status}

def get_bank_record(db: Session, utr: str) -> dict:
    b = db.query(BankTransaction).filter(BankTransaction.utr == utr).first()
    if not b: return {"error": f"Bank record for UTR {utr} not found"}
    return {"bank_txn_id": b.bank_txn_id, "utr": b.utr,
            "credit_amount": b.credit_amount, "narration": b.narration,
            "transaction_date": str(b.transaction_date), "bank": b.bank}

def get_fee_rules() -> dict:
    return {
        "standard_rate": "2% of transaction amount",
        "gst_on_fee": "18%",
        "max_fee": 1500.0,
        "settlement_lag": "1-3 business days",
        "note": "Net = gross - fee - (fee * 0.18)"
    }

def get_previous_exceptions(db: Session, order_id: str) -> list:
    excs = db.query(Exc).filter(Exc.order_id == order_id).all()
    return [{"exception_id": e.exception_id, "type": e.exception_type,
             "status": e.status, "created_at": str(e.created_at)} for e in excs]


TOOL_DEFINITIONS = [
    {"type": "function", "function": {
        "name": "get_transaction",
        "description": "Retrieve full order/transaction details by order_id",
        "parameters": {"type":"object","properties":{"order_id":{"type":"string"}},"required":["order_id"]}
    }},
    {"type": "function", "function": {
        "name": "get_settlement",
        "description": "Retrieve Razorpay settlement details by settlement_id",
        "parameters": {"type":"object","properties":{"settlement_id":{"type":"string"}},"required":["settlement_id"]}
    }},
    {"type": "function", "function": {
        "name": "get_bank_record",
        "description": "Retrieve bank transaction by UTR number",
        "parameters": {"type":"object","properties":{"utr":{"type":"string"}},"required":["utr"]}
    }},
    {"type": "function", "function": {
        "name": "get_fee_rules",
        "description": "Get Razorpay fee schedule and settlement rules",
        "parameters": {"type":"object","properties":{}}
    }},
    {"type": "function", "function": {
        "name": "get_previous_exceptions",
        "description": "Get history of exceptions for this order",
        "parameters": {"type":"object","properties":{"order_id":{"type":"string"}},"required":["order_id"]}
    }},
]

TOOL_REGISTRY = {
    "get_transaction": get_transaction,
    "get_settlement": get_settlement,
    "get_bank_record": get_bank_record,
    "get_fee_rules": get_fee_rules,
    "get_previous_exceptions": get_previous_exceptions,
}
