import csv, io, uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.schemas import ReconciliationRunOut, RunRequest, DashboardStats
from app.engine.normalizer import normalize_order, normalize_settlement, normalize_bank
from app.engine.matcher import reconcile
from app.agent.investigator import investigate
from app.engine.classifier import should_auto_resolve
import app.repository.repository as repo

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])


def _data_dir():
    import os
    return os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _regenerate_data():
    """Regenerate the synthetic CSVs with a fresh random seed, so every
    demo run produces different transactions instead of the same fixed batch."""
    import importlib.util, os
    data_dir = _data_dir()
    spec = importlib.util.spec_from_file_location("ledgerlens_datagen", os.path.join(data_dir, "generate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.generate(output_dir=os.path.join(data_dir, "generated"), seed=None)


def _load_generated_data():
    """Load the synthetic generated CSVs as fallback for demo mode."""
    import os
    base = os.path.join(_data_dir(), "generated")
    def read(name):
        path = os.path.join(base, name)
        if not os.path.exists(path): return []
        with open(path, encoding="utf-8") as f:
            return list(csv.DictReader(f))
    return read("orders.csv"), read("settlements.csv"), read("bank_transactions.csv")


@router.post("/run", response_model=ReconciliationRunOut)
def run_reconciliation(req: RunRequest, db: Session = Depends(get_db)):
    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
    run = repo.create_run(db, run_id)
    repo.log_action(db, run_id, "run", run_id, "started")

    # Fresh random data per run, then load it
    _regenerate_data()
    orders_raw, settle_raw, bank_raw = _load_generated_data()

    orders      = [normalize_order(r)      for r in orders_raw]
    settlements = [normalize_settlement(r) for r in settle_raw]
    banks       = [normalize_bank(r)       for r in bank_raw]

    # Seed DB (reset + reseed so re-running the demo doesn't collide on unique IDs)
    repo.clear_orders(db)
    repo.clear_settlements(db)
    repo.clear_bank_txns(db)
    repo.bulk_insert_orders(db, orders)
    repo.bulk_insert_settlements(db, settlements)
    repo.bulk_insert_bank_txns(db, banks)

    # Run engine
    result = reconcile(orders, settlements, banks)
    stats  = result["stats"]

    # Persist results
    result_rows = []
    for m in result["matched"] + result["review"]:
        result_rows.append({
            "run_id": run_id, "order_id": m.get("order_id"),
            "settlement_id": m.get("settlement_id"), "bank_txn_id": m.get("bank_txn_id"),
            "match_type": m.get("match_type"), "match_score": m.get("match_score"),
            "status": "matched" if m in result["matched"] else "review",
            "amount_delta": m.get("amount_delta"), "date_delta_days": m.get("date_delta_days"),
        })
    repo.bulk_insert_results(db, result_rows)

    # Create exceptions + run AI investigation
    for exc in result["exceptions"]:
        exc_id = f"EX-{uuid.uuid4().hex[:8].upper()}"
        exc_obj = repo.create_exception(db, {
            "exception_id": exc_id, "run_id": run_id, "order_id": exc.get("order_id"),
            "exception_type": exc["exception_type"], "severity": exc["severity"],
            "amount_delta": exc.get("amount_delta"), "status": "open",
            "result_id": None,
        })
        repo.log_action(db, run_id, "exception", exc_id, f"flagged:{exc['exception_type']}")

        # Investigate
        inv = investigate(exc, db)
        auto = should_auto_resolve(exc, inv)
        import json
        repo.save_investigation(db, {
            "exception_id": exc_id, "root_cause": inv.get("root_cause",""),
            "classification": inv.get("classification",""), "confidence": inv.get("confidence",0),
            "explanation": inv.get("explanation",""), "recommended_action": inv.get("recommended_action",""),
            "evidence": json.dumps(inv.get("evidence",[])), "tool_calls": inv.get("tool_calls","[]"),
            "risk_level": inv.get("risk_level","high"), "auto_resolved": auto,
        })
        if auto:
            repo.resolve_exception(db, exc_id, "auto_resolved", inv["recommended_action"], "ai")
            repo.log_action(db, run_id, "exception", exc_id, "auto_resolved", actor="ai")

    # Finalize run
    repo.update_run(db, run_id,
        completed_at=datetime.utcnow(), total_records=stats["total"],
        matched=stats["matched"], exceptions=stats["exceptions"],
        match_rate=stats["match_rate"], amount_reconciled=stats["amount_reconciled"],
        status="complete")
    repo.log_action(db, run_id, "run", run_id, "complete",
                    detail=f"matched={stats['matched']} exceptions={stats['exceptions']}")

    return repo.get_run(db, run_id)


@router.get("/runs", response_model=list[ReconciliationRunOut])
def list_runs(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return repo.get_runs(db, skip, limit)


@router.get("/runs/{run_id}", response_model=ReconciliationRunOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = repo.get_run(db, run_id)
    if not run: raise HTTPException(404, "Run not found")
    return run


@router.get("/dashboard")
def dashboard_stats(db: Session = Depends(get_db)):
    runs = repo.get_runs(db, limit=1)
    if not runs:
        return {"message": "No runs yet — POST /api/reconciliation/run to start"}
    run = runs[0]
    excs = repo.get_exceptions(db, run_id=run.run_id)
    exc_breakdown = {}; sev_breakdown = {"low":0,"warning":0,"critical":0}
    auto_resolved = 0; pending = 0
    for e in excs:
        exc_breakdown[e.exception_type] = exc_breakdown.get(e.exception_type, 0) + 1
        sev_breakdown[e.severity] = sev_breakdown.get(e.severity, 0) + 1
        if e.status == "auto_resolved": auto_resolved += 1
        if e.status == "open":          pending += 1
    return {
        "total_records": run.total_records, "matched": run.matched,
        "exceptions": run.exceptions, "match_rate": run.match_rate or 0,
        "amount_reconciled": run.amount_reconciled or 0,
        "auto_resolved": auto_resolved, "pending_review": pending,
        "exception_breakdown": exc_breakdown, "severity_breakdown": sev_breakdown,
    }
