"""
Ground-truth loader (Step 10.1).

Reads `data/generated/ground_truth.csv` (produced by the synthetic generator)
into typed records. This module NEVER manually enters expected values — every
field comes from the CSV. It is not imported by any production module; only
by evaluation scripts under `backend/scripts/`.
"""
from __future__ import annotations
import csv
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class GroundTruthRecord:
    """One row of ground_truth.csv."""
    order_id:       Optional[str]
    settlement_id:  Optional[str]
    bank_txn_id:    Optional[str]
    anomaly_type:   str      # 'clean' | 'amount_mismatch' | 'missing_settlement' |
                             # 'duplicate' | 'date_mismatch' | 'partial_settlement' |
                             # 'unknown_transaction'
    expected_match: bool
    notes:          str


def _clean(v: Optional[str]) -> Optional[str]:
    """CSVReader represents empty cells as '' and JSON-nulls as 'None'."""
    if v is None or v == "" or v == "None":
        return None
    return v


def load_ground_truth(path: str) -> List[GroundTruthRecord]:
    """Load ground_truth.csv → list of typed records."""
    rows: List[GroundTruthRecord] = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append(GroundTruthRecord(
                order_id=      _clean(r.get("order_id")),
                settlement_id= _clean(r.get("settlement_id")),
                bank_txn_id=   _clean(r.get("bank_txn_id")),
                anomaly_type=  (r.get("anomaly_type") or "").strip(),
                expected_match=(r.get("expected_match", "") or "").strip().lower() == "true",
                notes=         (r.get("notes") or "").strip(),
            ))
    return rows


def index_by_key(records: List[GroundTruthRecord]) -> Dict[str, GroundTruthRecord]:
    """
    Build a stable lookup key per record so engine predictions can be compared
    against ground truth:
      - linked anomaly (has order_id) → key = order_id
      - orphan anomaly  (no order_id, has settlement_id) → key = f'orphan:{settlement_id}'

    This matches the key scheme used by the evaluation scripts.
    """
    out: Dict[str, GroundTruthRecord] = {}
    for r in records:
        if r.order_id:
            out[r.order_id] = r
        elif r.settlement_id:
            out[f"orphan:{r.settlement_id}"] = r
    return out


def anomaly_counts(records: List[GroundTruthRecord]) -> Dict[str, int]:
    """Distribution of anomaly_type across the loaded records."""
    out: Dict[str, int] = {}
    for r in records:
        out[r.anomaly_type] = out.get(r.anomaly_type, 0) + 1
    return out
