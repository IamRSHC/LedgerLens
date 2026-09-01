"""
Reconciliation matching engine.

Stage 1 — Exact:  order_id + UTR chain
Stage 2 — Fuzzy:  scored matching on amount / date / reference
Stage 3 — Report: unmatched leftovers become exceptions
"""
from datetime import datetime
from typing import Optional
import math


# ── Scoring helpers ────────────────────────────────────────────────────────────

def amount_score(a: float, b: float) -> float:
    if a == 0 and b == 0: return 1.0
    if a == 0 or b == 0: return 0.0
    delta_pct = abs(a - b) / max(a, b)
    if delta_pct == 0:     return 1.0
    if delta_pct < 0.01:   return 0.90
    if delta_pct < 0.05:   return 0.70
    if delta_pct < 0.10:   return 0.50
    return 0.0

def date_score(d1: Optional[datetime], d2: Optional[datetime]) -> float:
    if not d1 or not d2: return 0.5  # neutral — can't penalise missing dates
    days = abs((d1 - d2).total_seconds()) / 86400
    if days <= 1:  return 1.0
    if days <= 3:  return 0.85
    if days <= 7:  return 0.60
    if days <= 30: return 0.30
    return 0.0

def ref_score(r1: str, r2: str) -> float:
    if not r1 or not r2: return 0.0
    if r1 == r2: return 1.0
    # simple character overlap
    s1, s2 = set(r1), set(r2)
    return len(s1 & s2) / len(s1 | s2) if s1 | s2 else 0.0

def match_score(order: dict, settlement: dict, bank: Optional[dict]) -> float:
    """
    Weights:
      50% — amount match (order vs settlement gross)
      25% — date proximity (order created_at vs settlement settled_at)
      15% — UTR / reference match
      10% — bank amount cross-check
    """
    amt  = amount_score(order["amount"], settlement["gross_amount"])
    dt   = date_score(order.get("created_at"), settlement.get("settled_at"))
    ref  = ref_score(order.get("reference_id",""), settlement.get("utr",""))
    bank_amt = amount_score(settlement["net_amount"], bank["credit_amount"]) if bank else 0.5
    return 0.50*amt + 0.25*dt + 0.15*ref + 0.10*bank_amt


# ── Main engine ────────────────────────────────────────────────────────────────

AUTO_MATCH_THRESHOLD  = 0.90
REVIEW_THRESHOLD      = 0.70

def reconcile(orders: list, settlements: list, bank_txns: list) -> dict:
    """
    Reconcile the three sources into two result-level buckets: MATCHED and EXCEPTION.

    Anything that fails the auto-match confidence threshold — including records
    that previously landed in a separate "review" bucket — becomes an exception
    so it enters the controller/AI workflow. Match metadata (score, type,
    date_delta_days) is preserved on the exception dict for downstream use.

    Args:
        orders:      list of normalized order dicts
        settlements: list of normalized settlement dicts
        bank_txns:   list of normalized bank_txn dicts

    Returns:
        {
          "matched":    [...],
          "exceptions": [...],
          "stats": {...},
        }
    """
    # Index by UTR for O(1) lookups
    settle_by_utr    = {s["utr"]: s for s in settlements if s.get("utr")}
    bank_by_utr      = {b["utr"]: b for b in bank_txns if b.get("utr")}

    # Step 1.4: when multiple settlements share the same order_id (the
    # duplicate-anomaly shape), prefer the EARLIEST-settled one as the
    # "original" that wins Stage 1. Duplicates (settled later) then fall
    # through to Stage 2 and are classified as `duplicate` explicitly.
    settle_by_oid: dict = {}
    for s in settlements:
        oid = s.get("order_id")
        if not oid:
            continue
        existing = settle_by_oid.get(oid)
        if existing is None:
            settle_by_oid[oid] = s
            continue
        s_dt = s.get("settled_at")
        e_dt = existing.get("settled_at")
        if s_dt and e_dt and s_dt < e_dt:
            settle_by_oid[oid] = s

    # Index orders for Stage 2 duplicate detection.
    orders_by_id = {o["order_id"]: o for o in orders}

    matched, exceptions = [], []
    used_settlements = set()
    used_banks       = set()

    # ── Stage 1: Exact match ───────────────────────────────────────────────────
    for order in orders:
        oid = order["order_id"]
        utr = order.get("reference_id", "")
        settlement = settle_by_oid.get(oid) or settle_by_utr.get(utr)
        if not settlement:
            exceptions.append(_exception(order, None, None, "missing_settlement"))
            continue

        bank = bank_by_utr.get(settlement["utr"])
        score = match_score(order, settlement, bank)

        used_settlements.add(settlement["settlement_id"])
        if bank: used_banks.add(bank["bank_txn_id"])

        record = _result(order, settlement, bank, score)

        if score >= AUTO_MATCH_THRESHOLD:
            record["match_type"] = "exact" if (oid == settlement.get("order_id")) else "fuzzy"
            matched.append(record)
        else:
            # Below auto-match confidence → exception so the controller can act.
            exc_type = _classify(order, settlement, bank, score)
            # Records in the old "review" band (REVIEW_THRESHOLD ≤ score < AUTO_MATCH_THRESHOLD)
            # that don't fit any specific classifier bucket are surfaced as low-confidence
            # matches rather than the generic "unclassified" label.
            if exc_type == "unclassified" and score >= REVIEW_THRESHOLD:
                exc_type = "low_confidence_match"
            exc = _exception(order, settlement, bank, exc_type)
            exc["match_score"]     = round(score, 4)
            exc["match_type"]      = "fuzzy"
            exc["date_delta_days"] = record.get("date_delta_days")
            exceptions.append(exc)

    # ── Stage 2: Orphan settlements ────────────────────────────────────────────
    # A settlement not consumed by Stage 1 is either:
    #   • duplicate           — its order_id references a real order (that order
    #                           was already reconciled via a different settlement);
    #   • unknown_transaction — no matching order at all.
    # This is deterministic: it uses only stable evidence already in the record
    # (order_id + orders_by_id membership). No LLM involved.
    orphan_settlements = 0
    for s in settlements:
        if s["settlement_id"] in used_settlements:
            continue
        orphan_settlements += 1
        bank = bank_by_utr.get(s.get("utr", ""))
        oid  = s.get("order_id")
        if oid and oid in orders_by_id:
            exceptions.append(_exception(orders_by_id[oid], s, bank, "duplicate"))
        else:
            exceptions.append(_exception(None, s, bank, "unknown_transaction"))

    # `total` now counts every distinct reconciliation-target entity:
    # each order + each orphan settlement (both duplicates and unknowns).
    # This makes matched + exceptions == total.
    total   = len(orders) + orphan_settlements
    n_match = len(matched)

    stats = {
        "total":      total,
        "matched":    n_match,
        "exceptions": len(exceptions),
        "match_rate": round(n_match / total * 100, 2) if total else 0,
        "amount_reconciled": round(sum(r.get("order_amount",0) for r in matched), 2),
    }
    return {"matched": matched, "exceptions": exceptions, "stats": stats}


def _result(order: dict, settlement: dict, bank: Optional[dict], score: float) -> dict:
    delta = round(order["amount"] - settlement["gross_amount"], 2) if settlement else None
    dt1 = order.get("created_at"); dt2 = settlement.get("settled_at") if settlement else None
    date_delta = abs((dt1-dt2).days) if dt1 and dt2 else None
    return {
        "order_id":      order["order_id"],
        "order_amount":  order["amount"],
        "settlement_id": settlement["settlement_id"] if settlement else None,
        "bank_txn_id":   bank["bank_txn_id"] if bank else None,
        "match_score":   round(score, 4),
        "match_type":    "fuzzy",
        "status":        "matched",
        "amount_delta":  delta,
        "date_delta_days": date_delta,
    }

def _classify(order, settlement, bank, score) -> str:
    if not settlement: return "missing_settlement"
    if not bank:       return "missing_bank_record"
    delta = abs(order["amount"] - settlement["gross_amount"])
    delta_pct = delta / max(order["amount"], 0.01)
    if delta_pct > 0.01: return "amount_mismatch"
    dt1 = order.get("created_at"); dt2 = settlement.get("settled_at")
    if dt1 and dt2 and abs((dt1-dt2).days) > 7: return "date_mismatch"
    if settlement["net_amount"] < order["amount"] * 0.90: return "partial_settlement"
    return "unclassified"

def _exception(order, settlement, bank, exc_type: str) -> dict:
    delta = None
    if order and settlement:
        delta = round(order["amount"] - settlement["gross_amount"], 2)
    severity = _severity(exc_type, delta)
    return {
        "order_id":      order["order_id"] if order else None,
        "settlement_id": settlement["settlement_id"] if settlement else None,
        "bank_txn_id":   bank["bank_txn_id"] if bank else None,
        "exception_type": exc_type,
        "severity":      severity,
        "amount_delta":  delta,
        "order_amount":  order["amount"] if order else None,
        "settlement_amount": settlement["gross_amount"] if settlement else None,
    }

def _severity(exc_type: str, delta: Optional[float]) -> str:
    if exc_type in ("unknown_transaction", "duplicate"): return "critical"
    if exc_type == "missing_settlement": return "warning"
    if exc_type == "amount_mismatch" and delta and abs(delta) > 5000: return "critical"
    if exc_type == "amount_mismatch": return "warning"
    return "low"
