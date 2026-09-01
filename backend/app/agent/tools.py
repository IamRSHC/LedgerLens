"""
AI Investigator tools (Milestone C — Steps 4.1, 4.2, 4.3).

Every tool:
  - is READ-ONLY (no db.commit(), no repo mutation function, no external write);
  - validates its arguments;
  - returns a JSON-serialisable dict — never a SQLAlchemy row;
  - uses the same success/miss shape:
        success  → {"found": true,  ...fields...}
        miss     → {"found": false, "error": "<code>", ...}
  - does not accept a free-form query string or SQL fragment;
  - has a matching OpenAI/Groq tool schema in `TOOL_DEFINITIONS`.

TOOL_REGISTRY is the whitelist consulted by `agent/investigator.py`. Only
functions listed there can be invoked by the model.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.models import Order, Settlement, BankTransaction, Exception as Exc
from app.agent.merchant_profiles import PROFILES as MERCHANT_PROFILES


# ── Argument validation helpers ───────────────────────────────────────────────
def _err(code: str, **extra) -> Dict[str, Any]:
    """Uniform miss/error envelope."""
    d: Dict[str, Any] = {"found": False, "error": code}
    d.update(extra)
    return d


def _require_str(v: Any, name: str) -> Optional[Dict[str, Any]]:
    if not isinstance(v, str) or not v.strip():
        return _err("invalid_argument", argument=name, message=f"{name} must be a non-empty string")
    return None


def _optional_num(v: Any, name: str) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    raise ValueError(f"{name} must be a number or omitted")


def _parse_iso_date(v: Any, name: str) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v)
        except ValueError:
            pass
    raise ValueError(f"{name} must be ISO-8601 date/datetime or omitted")


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if isinstance(dt, datetime) else None


# ── Step 4.1: hardened existing tools ────────────────────────────────────────
def get_transaction(db: Session, order_id: str) -> Dict[str, Any]:
    err = _require_str(order_id, "order_id")
    if err: return err
    o = db.query(Order).filter(Order.order_id == order_id).first()
    if not o:
        return _err("transaction_not_found", order_id=order_id)
    return {
        "found":          True,
        "order_id":       o.order_id,
        "merchant_id":    o.merchant_id,
        "amount":         o.amount,
        "currency":       o.currency,
        "status":         o.status,
        "payment_method": o.payment_method,
        "created_at":     _iso(o.created_at),
        "reference_id":   o.reference_id,   # UTR
    }


def get_settlement(db: Session, settlement_id: str) -> Dict[str, Any]:
    err = _require_str(settlement_id, "settlement_id")
    if err: return err
    s = db.query(Settlement).filter(Settlement.settlement_id == settlement_id).first()
    if not s:
        return _err("settlement_not_found", settlement_id=settlement_id)
    return {
        "found":         True,
        "settlement_id": s.settlement_id,
        "order_id":      s.order_id,
        "merchant_id":   s.merchant_id,
        "gross_amount":  s.gross_amount,
        "fee":           s.fee,
        "net_amount":    s.net_amount,
        "utr":           s.utr,
        "status":        s.status,
        "settled_at":    _iso(s.settled_at),
    }


def get_bank_record(db: Session, utr: str) -> Dict[str, Any]:
    err = _require_str(utr, "utr")
    if err: return err
    b = db.query(BankTransaction).filter(BankTransaction.utr == utr).first()
    if not b:
        return _err("bank_record_not_found", utr=utr)
    return {
        "found":            True,
        "bank_txn_id":      b.bank_txn_id,
        "utr":              b.utr,
        "credit_amount":    b.credit_amount,
        "debit_amount":     b.debit_amount,
        "narration":        b.narration,
        "transaction_date": _iso(b.transaction_date),
        "value_date":       _iso(b.value_date),
        "bank":             b.bank,
    }


def get_fee_rules() -> Dict[str, Any]:
    """Static Razorpay-style fee schedule. Deterministic and traceable."""
    return {
        "found":            True,
        "standard_rate":    "2% of transaction amount",
        "standard_rate_pct": 0.02,
        "gst_on_fee_pct":   0.18,
        "max_fee_inr":      1500.0,
        "settlement_lag":   "1-3 business days",
        "formula":          "net = gross - fee - (fee * 0.18)",
    }


def get_previous_exceptions(db: Session, order_id: str) -> Dict[str, Any]:
    err = _require_str(order_id, "order_id")
    if err: return err
    rows = db.query(Exc).filter(Exc.order_id == order_id).order_by(Exc.created_at.desc()).all()
    return {
        "found": True,
        "count": len(rows),
        "exceptions": [
            {
                "exception_id":   e.exception_id,
                "run_id":         e.run_id,
                "exception_type": e.exception_type,
                "severity":       e.severity,
                "status":         e.status,
                "amount_delta":   e.amount_delta,
                "created_at":     _iso(e.created_at),
            }
            for e in rows
        ],
    }


# ── Step 4.2: new search_related_transactions ────────────────────────────────
_SEARCH_LIMIT_DEFAULT = 10
_SEARCH_LIMIT_MAX     = 25


def search_related_transactions(
    db: Session,
    merchant_id:    Optional[str] = None,
    order_id:       Optional[str] = None,
    utr:            Optional[str] = None,
    amount_min:     Optional[float] = None,
    amount_max:     Optional[float] = None,
    date_from:      Optional[str] = None,
    date_to:        Optional[str] = None,
    exception_type: Optional[str] = None,
    limit:          Optional[int] = None,
) -> Dict[str, Any]:
    """
    Return exceptions matching a bounded set of filters. Read-only. No free-form
    SQL/text queries — every input is a typed, optional filter that maps to a
    single WHERE clause. Result set is capped.

    At least one filter must be supplied — a bare call would otherwise scan the
    whole exceptions table.
    """
    # Validate types where supplied
    for pair in (("merchant_id", merchant_id), ("order_id", order_id),
                 ("utr", utr), ("exception_type", exception_type)):
        n, v = pair
        if v is not None:
            e = _require_str(v, n)
            if e: return e
    try:
        amt_min = _optional_num(amount_min, "amount_min")
        amt_max = _optional_num(amount_max, "amount_max")
        dt_from = _parse_iso_date(date_from, "date_from")
        dt_to   = _parse_iso_date(date_to,   "date_to")
    except ValueError as e:
        return _err("invalid_argument", message=str(e))

    if limit is None:
        capped_limit = _SEARCH_LIMIT_DEFAULT
    else:
        if not isinstance(limit, int) or limit < 1:
            return _err("invalid_argument", argument="limit", message="limit must be a positive integer")
        capped_limit = min(limit, _SEARCH_LIMIT_MAX)

    supplied = [x for x in (merchant_id, order_id, utr, amt_min, amt_max,
                             dt_from, dt_to, exception_type) if x is not None]
    if not supplied:
        return _err("invalid_argument", message="at least one filter must be supplied")

    q = db.query(Exc)
    # merchant_id and utr require joining Order (Exc doesn't carry them directly)
    if merchant_id or utr:
        q = q.join(Order, Order.order_id == Exc.order_id)
        if merchant_id: q = q.filter(Order.merchant_id == merchant_id)
        if utr:         q = q.filter(Order.reference_id == utr)
    if order_id:       q = q.filter(Exc.order_id == order_id)
    if exception_type: q = q.filter(Exc.exception_type == exception_type)
    if amt_min is not None: q = q.filter(Exc.amount_delta >= amt_min)
    if amt_max is not None: q = q.filter(Exc.amount_delta <= amt_max)
    if dt_from is not None: q = q.filter(Exc.created_at >= dt_from)
    if dt_to   is not None: q = q.filter(Exc.created_at <= dt_to)

    rows = q.order_by(Exc.created_at.desc()).limit(capped_limit).all()
    return {
        "found": True,
        "count": len(rows),
        "limit_used": capped_limit,
        "matches": [
            {
                "exception_id":   e.exception_id,
                "order_id":       e.order_id,
                "exception_type": e.exception_type,
                "amount_delta":   e.amount_delta,
                "severity":       e.severity,
                "status":         e.status,
                "created_at":     _iso(e.created_at),
            }
            for e in rows
        ],
    }


# ── Step 4.3: get_merchant_profile ───────────────────────────────────────────
def get_merchant_profile(merchant_id: str) -> Dict[str, Any]:
    """
    Return controlled merchant configuration from a deterministic in-app source.
    """
    err = _require_str(merchant_id, "merchant_id")
    if err: return err
    prof = MERCHANT_PROFILES.get(merchant_id)
    if not prof:
        return _err("merchant_not_found", merchant_id=merchant_id)
    return {
        "found":              True,
        "merchant_id":        merchant_id,
        "fee_rate":           prof["fee_rate"],
        "settlement_lag_days": prof["settlement_lag_days"],
        "risk_tier":          prof["risk_tier"],
    }


# ── OpenAI/Groq tool schemas ─────────────────────────────────────────────────
TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "get_transaction",
        "description": (
            "Fetch a single order (transaction) by order_id. Returns the order's "
            "amount, status, payment method, reference UTR, and merchant. "
            "Use this to confirm what the merchant billed the customer. "
            "Returns {found: false, error: 'transaction_not_found'} if the order does not exist."
        ),
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "string", "description": "The order identifier (e.g. 'ORD-…')."},
        }, "required": ["order_id"]},
    }},
    {"type": "function", "function": {
        "name": "get_settlement",
        "description": (
            "Fetch a single Razorpay settlement by settlement_id. Returns gross/fee/net "
            "amounts, the UTR the money settled under, and the settlement date. "
            "Use this to verify what actually settled and when. "
            "Returns {found: false, error: 'settlement_not_found'} if the settlement does not exist."
        ),
        "parameters": {"type": "object", "properties": {
            "settlement_id": {"type": "string", "description": "The settlement identifier (e.g. 'SET-…')."},
        }, "required": ["settlement_id"]},
    }},
    {"type": "function", "function": {
        "name": "get_bank_record",
        "description": (
            "Fetch the bank transaction credited for a given UTR. Returns credit_amount, "
            "narration, transaction_date, and bank name. Use this to verify the money leg — "
            "does the bank actually show a credit for this settlement's UTR? "
            "Returns {found: false, error: 'bank_record_not_found'} when no bank row exists."
        ),
        "parameters": {"type": "object", "properties": {
            "utr": {"type": "string", "description": "The 12-digit UTR from the settlement or order.reference_id."},
        }, "required": ["utr"]},
    }},
    {"type": "function", "function": {
        "name": "get_fee_rules",
        "description": (
            "Return the deterministic Razorpay fee schedule the engine assumes: standard "
            "2% rate, 18% GST on the fee, ₹1500 cap, T+1..T+3 settlement window. "
            "Use this to check whether an amount discrepancy is consistent with the fee formula."
        ),
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_previous_exceptions",
        "description": (
            "List every prior exception logged against a given order_id, most recent first. "
            "Use this to check whether the current exception is part of a repeating problem "
            "for the same order. Returns {found: true, count: N, exceptions: [...]}."
        ),
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "string", "description": "The order identifier to check."},
        }, "required": ["order_id"]},
    }},
    {"type": "function", "function": {
        "name": "search_related_transactions",
        "description": (
            "Search prior exceptions with bounded, typed filters. Useful for pattern-finding: "
            "'have other exceptions for this merchant shown the same delta?', "
            "'has this UTR appeared in past exceptions?'. Only exceptions are searched — not "
            "raw orders — because exceptions are the units of interest. At least one filter "
            "must be supplied. Results are capped at 25. Returns {found, count, matches: [...]}."
        ),
        "parameters": {"type": "object", "properties": {
            "merchant_id":    {"type": "string", "description": "Filter to this merchant (joins Order)."},
            "order_id":       {"type": "string", "description": "Filter to this order_id."},
            "utr":            {"type": "string", "description": "Filter to this UTR (matches Order.reference_id)."},
            "amount_min":     {"type": "number", "description": "Only include exceptions where amount_delta >= this."},
            "amount_max":     {"type": "number", "description": "Only include exceptions where amount_delta <= this."},
            "date_from":      {"type": "string", "description": "ISO date; created_at >= this."},
            "date_to":        {"type": "string", "description": "ISO date; created_at <= this."},
            "exception_type": {"type": "string", "description": "Filter to a specific exception_type."},
            "limit":          {"type": "integer", "description": "Result cap (default 10, max 25)."},
        }},
    }},
    {"type": "function", "function": {
        "name": "get_merchant_profile",
        "description": (
            "Return the merchant's configured fee_rate, expected settlement_lag_days, and "
            "risk_tier (standard | elevated). Use this to check whether an anomaly is "
            "consistent with what's normal for this specific merchant. "
            "Returns {found: false, error: 'merchant_not_found'} for unknown IDs."
        ),
        "parameters": {"type": "object", "properties": {
            "merchant_id": {"type": "string", "description": "The merchant identifier (e.g. 'MERCH-0003')."},
        }, "required": ["merchant_id"]},
    }},
]


TOOL_REGISTRY = {
    "get_transaction":             get_transaction,
    "get_settlement":              get_settlement,
    "get_bank_record":             get_bank_record,
    "get_fee_rules":               get_fee_rules,
    "get_previous_exceptions":     get_previous_exceptions,
    "search_related_transactions": search_related_transactions,
    "get_merchant_profile":        get_merchant_profile,
}
