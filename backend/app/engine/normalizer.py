"""
Normalizes raw CSV rows into uniform dicts before matching.
"""
from datetime import datetime
from typing import Optional


def _parse_dt(val) -> Optional[datetime]:
    if not val: return None
    if isinstance(val, datetime): return val
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try: return datetime.strptime(str(val).split(".")[0], fmt)
        except ValueError: pass
    return None

def _f(val) -> float:
    try: return float(val) if val not in (None, "", "None") else 0.0
    except: return 0.0


def normalize_order(row: dict) -> dict:
    return {
        "order_id":       str(row.get("order_id", "")),
        "merchant_id":    str(row.get("merchant_id", "")),
        "customer_id":    str(row.get("customer_id", "")),
        "amount":         _f(row.get("amount")),
        "currency":       str(row.get("currency", "INR")),
        "status":         str(row.get("status", "")),
        "payment_method": str(row.get("payment_method", "")),
        "created_at":     _parse_dt(row.get("created_at")),
        "reference_id":   str(row.get("reference_id", "")),  # UTR
    }

def normalize_settlement(row: dict) -> dict:
    return {
        "settlement_id": str(row.get("settlement_id", "")),
        "order_id":      str(row.get("order_id", "")) or None,
        "merchant_id":   str(row.get("merchant_id", "")),
        "gross_amount":  _f(row.get("gross_amount")),
        "fee":           _f(row.get("fee")),
        "net_amount":    _f(row.get("net_amount")),
        "utr":           str(row.get("utr", "")),
        "status":        str(row.get("status", "")),
        "settled_at":    _parse_dt(row.get("settled_at")),
    }

def normalize_bank(row: dict) -> dict:
    return {
        "bank_txn_id":      str(row.get("bank_txn_id", "")),
        "utr":              str(row.get("utr", "")),
        "credit_amount":    _f(row.get("credit_amount")),
        "debit_amount":     _f(row.get("debit_amount")),
        "narration":        str(row.get("narration", "")),
        "transaction_date": _parse_dt(row.get("transaction_date")),
        "value_date":       _parse_dt(row.get("value_date")),
        "bank":             str(row.get("bank", "")),
    }
