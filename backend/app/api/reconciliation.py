import csv, io, uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.schemas import ReconciliationRunOut, RunRequest, DashboardStats
from app.engine.normalizer import normalize_order, normalize_settlement, normalize_bank
from app.engine.matcher import reconcile
from app.agent.investigator import investigate
# Step 2.1: policy + resolver replace the direct `should_auto_resolve` +
# inline transition_exception calls. AI investigates, POLICY decides, RESOLVER executes.
from app.controller.policy import evaluate_exception
from app.controller.resolver import apply as apply_resolution
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

    # Persist results (Step 1.1: only MATCHED result rows; former "review" items
    # now flow through result["exceptions"] and are persisted below as exception rows.)
    result_rows = []
    for m in result["matched"]:
        result_rows.append({
            "run_id": run_id, "order_id": m.get("order_id"),
            "settlement_id": m.get("settlement_id"), "bank_txn_id": m.get("bank_txn_id"),
            "match_type": m.get("match_type"), "match_score": m.get("match_score"),
            "status": "matched",
            "amount_delta": m.get("amount_delta"), "date_delta_days": m.get("date_delta_days"),
        })
    repo.bulk_insert_results(db, result_rows)

    # Create exceptions + run AI investigation (Step 1.2 lifecycle:
    # open → ai_investigating → auto_resolved OR manual_review).
    # Step 1.3: every exception is now linked to its own ReconciliationResult
    # row (status="exception"), so result → exception navigation is possible
    # from either direction.
    for exc in result["exceptions"]:
        exc_result = repo.insert_result(db, {
            "run_id": run_id,
            "order_id":        exc.get("order_id"),
            "settlement_id":   exc.get("settlement_id"),
            "bank_txn_id":     exc.get("bank_txn_id"),
            "match_type":      exc.get("match_type") or "unmatched",
            "match_score":     exc.get("match_score"),
            "status":          "exception",
            "amount_delta":    exc.get("amount_delta"),
            "date_delta_days": exc.get("date_delta_days"),
        })

        exc_id = f"EX-{uuid.uuid4().hex[:8].upper()}"
        repo.create_exception(db, {
            "exception_id": exc_id, "run_id": run_id, "order_id": exc.get("order_id"),
            "exception_type": exc["exception_type"], "severity": exc["severity"],
            "amount_delta": exc.get("amount_delta"), "status": repo.STATUS_OPEN,
            "result_id": exc_result.id,
        })
        repo.log_action(db, run_id, "exception", exc_id, f"flagged:{exc['exception_type']}")

        # open → ai_investigating (audit action="started_investigation" preserved
        # for backwards compat with earlier steps' consumers).
        repo.transition_exception(
            db, exc_id, repo.STATUS_AI_INVESTIGATING,
            actor="system", action="started_investigation",
        )

        # ── Step 8.1 audit: investigation_started ─────────────────────────────
        # Plan-named event. Detail carries the identifiers a reviewer needs to
        # correlate this investigation with the underlying exception — no
        # prompts, no chain-of-thought.
        repo.log_action(
            db, run_id, "exception", exc_id, "investigation_started",
            actor="ai",
            detail=f"type={exc['exception_type']} severity={exc['severity']} "
                   f"order_id={exc.get('order_id')} amount_delta={exc.get('amount_delta')}",
        )

        inv      = investigate(exc, db)

        # ── Step 8.1 audit: tool_called + tool_completed per tool invocation ──
        # Emitted from the reconciliation loop (NOT the agent) so the agent
        # keeps its read-only stance. Uses only the Step-5.3 metadata already
        # sanitised by the dispatcher (no raw payloads, no chain-of-thought).
        import json
        for tc in inv.get("tool_calls", []) or []:
            args_str = json.dumps(tc.get("arguments", {}), default=str)[:120]
            repo.log_action(
                db, run_id, "exception", exc_id, "tool_called",
                actor="ai",
                detail=f"tool={tc.get('tool')} args={args_str}",
            )
            repo.log_action(
                db, run_id, "exception", exc_id, "tool_completed",
                actor="ai",
                detail=f"tool={tc.get('tool')} status={tc.get('status')} "
                       f"duration_ms={tc.get('duration_ms')} "
                       f"summary={(tc.get('result_summary') or '')[:100]}",
            )

        # ── Step 8.1 audit: investigation_completed / investigation_failed ────
        # "completed" means a live-provider investigation returned a validated
        # InvestigationResult with no fallback_reason. Anything else (any
        # fallback path) is "failed" and carries the exact fallback_reason —
        # never a prompt or a raw provider error string.
        _provider = inv.get("provider") or "unknown"
        _model    = inv.get("model") or "unknown"
        _cls      = inv.get("classification") or "unknown"
        _conf     = inv.get("confidence") if inv.get("confidence") is not None else 0.0
        _fb       = inv.get("fallback_reason")
        if _provider == "groq" and _fb is None:
            repo.log_action(
                db, run_id, "exception", exc_id, "investigation_completed",
                actor="ai",
                detail=f"provider=groq model={_model} classification={_cls} "
                       f"confidence={_conf} tool_calls={len(inv.get('tool_calls', []) or [])}",
            )
        else:
            repo.log_action(
                db, run_id, "exception", exc_id, "investigation_failed",
                actor="ai",
                detail=f"provider={_provider} model={_model} "
                       f"fallback_reason={_fb} classification={_cls} confidence={_conf}",
            )

        decision = evaluate_exception(exc, inv)

        # ── Step 8.1 audit: policy_evaluated ──────────────────────────────────
        # Records the deterministic policy verdict. Blockers list is truncated
        # to keep audit rows bounded; full blockers persist on ai_investigations
        # via the resolver's own audit `detail`.
        _blockers = "; ".join(decision.blockers) if decision.blockers else "none"
        repo.log_action(
            db, run_id, "exception", exc_id, "policy_evaluated",
            actor="system",
            detail=f"decision={decision.decision} policy_risk={decision.risk_level} "
                   f"model_risk={decision.model_risk or 'unknown'} "
                   f"eligible={decision.eligible_for_auto_resolution} "
                   f"blockers={_blockers[:200]}",
        )

        repo.save_investigation(db, {
            "exception_id": exc_id, "root_cause": inv.get("root_cause",""),
            "classification": inv.get("classification",""), "confidence": inv.get("confidence",0),
            "explanation": inv.get("explanation",""), "recommended_action": inv.get("recommended_action",""),
            "evidence": json.dumps(inv.get("evidence", [])),
            # Post-Step-3.1: InvestigationResult.tool_calls is a list; serialise to JSON here.
            "tool_calls": json.dumps(inv.get("tool_calls", [])),
            # Model-supplied risk_level (observability only — Step 3.2).
            "risk_level": inv.get("risk_level") or "unknown",
            "auto_resolved": decision.eligible_for_auto_resolution,
            # Step 7.2 provenance columns — new for Milestone D.
            "provider":        inv.get("provider"),
            "model":           inv.get("model"),
            "fallback_reason": inv.get("fallback_reason"),
        })

        # ai_investigating → auto_resolved OR manual_review, executed by the resolver.
        # The resolver emits the transition-level audit ("auto_resolved" or
        # "policy_manual_review") via transition_exception — those rows are
        # preserved. The plan additionally names "manual_review_required" as
        # the semantic event for the manual-review branch, so we emit it here
        # so consumers can filter on either name.
        apply_resolution(db, exc_id, decision, inv)
        if decision.decision == "manual_review":
            repo.log_action(
                db, run_id, "exception", exc_id, "manual_review_required",
                actor="system",
                detail=f"policy_risk={decision.risk_level} confidence={_conf} "
                       f"blockers={_blockers[:200]}",
            )

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
    # Pick the latest COMPLETE run. Killed/incomplete "pending" batches — e.g.
    # from a mid-flight timeout — would otherwise become the "latest run" and
    # the dashboard would report zero counts while the exception table shows
    # real rows. Scan a small window so a couple of pending runs at the top
    # don't hide a good result underneath.
    runs = repo.get_runs(db, limit=10)
    if not runs:
        return {"message": "No runs yet — POST /api/reconciliation/run to start"}
    run = next((r for r in runs if r.status == "complete"), None)
    if run is None:
        # There are runs but none complete yet — surface that instead of zeros.
        latest = runs[0]
        return {
            "message": f"Latest run {latest.run_id} is still {latest.status}; "
                       "no complete run to summarise yet.",
            "run_id": latest.run_id,
            "run_status": latest.status,
        }
    excs = repo.get_exceptions(db, run_id=run.run_id)
    exc_breakdown = {}; sev_breakdown = {"low":0,"warning":0,"critical":0}
    auto_resolved = 0; manual_review = 0; pending = 0
    for e in excs:
        exc_breakdown[e.exception_type] = exc_breakdown.get(e.exception_type, 0) + 1
        sev_breakdown[e.severity] = sev_breakdown.get(e.severity, 0) + 1
        if e.status == repo.STATUS_AUTO_RESOLVED: auto_resolved += 1
        if e.status == repo.STATUS_MANUAL_REVIEW: manual_review += 1
        # Anything not yet in a terminal state counts as pending human attention.
        if e.status in (repo.STATUS_OPEN, repo.STATUS_AI_INVESTIGATING, repo.STATUS_MANUAL_REVIEW):
            pending += 1
    return {
        "total_records": run.total_records, "matched": run.matched,
        "exceptions": run.exceptions, "match_rate": run.match_rate or 0,
        "amount_reconciled": run.amount_reconciled or 0,
        "auto_resolved": auto_resolved, "manual_review": manual_review,
        "pending_review": pending,
        "exception_breakdown": exc_breakdown, "severity_breakdown": sev_breakdown,
        # The run these KPIs describe. Frontend uses this to filter the
        # exception table so table and KPIs always show the same batch.
        "run_id":         run.run_id,
        "run_started_at": run.started_at.isoformat() if run.started_at else None,
        "run_status":     run.status,
    }
