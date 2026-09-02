"""
Step 10.3 — Evaluate the controller/agent decision layer.

Scores the persisted `ai_investigations` + `exceptions` rows for the most
recent COMPLETE run against ground_truth.csv. Never manually enters expected
values.

Priority metric per plan: **auto-resolution precision**. An unsafe
auto-resolution is worse than sending a safe case to manual review, so this
metric is reported first.

Also reports:
  - classification accuracy (AI's own classification label vs ground-truth
    anomaly_type family — see MAP_TO_GT for the alignment)
  - manual-review recall  (fraction of should-be-reviewed records that ended
    up in manual_review or resolved-after-manual)
  - provider counts       (groq vs fallback — fallback is NOT counted as
    "live AI success")
  - fallback_reason distribution

Usage:
    cd backend
    venv/Scripts/python.exe scripts/evaluate_agent.py [--run RUN-XXXX]
"""
from __future__ import annotations
import argparse, os, sys
from collections import Counter
from typing import Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _BACKEND)
os.chdir(_BACKEND)

from app.database import SessionLocal
from app.models.models import Exception as Exc, AIInvestigation
import app.repository.repository as repo
from app.eval.ground_truth import load_ground_truth, index_by_key


# ── AI classification → ground_truth anomaly family mapping ──────────────────
# The AI emits classification enums from schemas/investigation.py. Ground truth
# uses the engine-side taxonomy. This map answers: "if the AI said X, which
# ground-truth anomaly type(s) is that consistent with?"
# It is used ONLY for scoring — NOT for any decision or state change.
MAP_TO_GT: Dict[str, set] = {
    "settlement_fee":       {"amount_mismatch"},              # fee-shaped delta
    "timing_difference":    {"date_mismatch"},
    "data_entry_error":     {"amount_mismatch"},
    "potential_fraud":      {"unknown_transaction", "duplicate"},
    "duplicate":            {"duplicate"},
    "partial_payment":      {"partial_settlement", "amount_mismatch"},
    "missing_bank_record":  {"missing_bank_record"},          # engine may or may not emit this
    "missing_settlement":   {"missing_settlement"},
    "unknown":              set(),                             # non-committal
}

# Ground-truth anomaly types that should NEVER auto-resolve. Aligns with the
# controller's HUMAN_REVIEW_TYPES + high-value protection.
UNSAFE_TO_AUTORESOLVE = {"duplicate", "unknown_transaction", "missing_settlement"}


def latest_complete_run(db) -> Optional[str]:
    runs = repo.get_runs(db, limit=10)
    for r in runs:
        if r.status == "complete":
            return r.run_id
    return None


def evaluate(run_id: Optional[str] = None) -> dict:
    db = SessionLocal()

    if run_id is None:
        run_id = latest_complete_run(db)
    if not run_id:
        print("no complete run found — nothing to evaluate.")
        return {}

    print("=" * 72)
    print(f"STEP 10.3 — CONTROLLER / AGENT EVALUATION  (run={run_id})")
    print("=" * 72)

    # Load ground truth (from the same generated dataset the run scored against)
    gt = load_ground_truth(os.path.join(_BACKEND, "data", "generated", "ground_truth.csv"))
    gt_idx = index_by_key(gt)

    # Pull every exception + its investigation for this run
    excs = db.query(Exc).filter(Exc.run_id == run_id).all()
    print(f"exceptions persisted for this run: {len(excs)}")

    # Helper: Exception has order_id; settlement_id lives on the linked
    # ReconciliationResult. Build a stable ground-truth key per exception.
    def _gt_key(e) -> Optional[str]:
        if e.order_id:
            return e.order_id
        sid = getattr(e.result, "settlement_id", None) if e.result else None
        return f"orphan:{sid}" if sid else None

    # ── Provider distribution ────────────────────────────────────────────────
    inv_rows = [e.investigation for e in excs if e.investigation]
    prov_dist   = Counter((i.provider or "unknown") for i in inv_rows)
    fb_dist     = Counter((i.fallback_reason or "n/a") for i in inv_rows if i.provider == "fallback")
    model_dist  = Counter((i.model or "unknown") for i in inv_rows)
    print()
    print("--- provider distribution (live-Groq vs fallback) ---")
    for k, v in sorted(prov_dist.items()):
        print(f"  provider={k:<12} {v:>3}")
    print(f"  live-Groq investigations:     {prov_dist.get('groq', 0)}")
    print(f"  fallback investigations:      {prov_dist.get('fallback', 0)}")
    print("  fallback_reason breakdown:")
    for k, v in sorted(fb_dist.items(), key=lambda x: -x[1]):
        print(f"    {k:<28} {v}")
    print("  model distribution:")
    for k, v in sorted(model_dist.items(), key=lambda x: -x[1]):
        print(f"    {k:<32} {v}")

    # ── Classification accuracy (against ground truth) ───────────────────────
    n_cls_correct = 0
    n_cls_total   = 0
    n_cls_undetermined = 0
    for e in excs:
        # engine key
        key = _gt_key(e)
        if key is None: continue
        gt_row = gt_idx.get(key)
        if not gt_row:
            continue
        inv = e.investigation
        cls = (inv.classification if inv else None) or "unknown"
        expected_gt = gt_row.anomaly_type
        n_cls_total += 1
        allowed = MAP_TO_GT.get(cls, set())
        if not allowed:
            # AI classification carries no ground-truth mapping (e.g. "unknown")
            n_cls_undetermined += 1
            continue
        if expected_gt in allowed:
            n_cls_correct += 1

    cls_scored = n_cls_total - n_cls_undetermined
    cls_acc    = (n_cls_correct / cls_scored) if cls_scored else 0.0
    print()
    print("--- classification accuracy (AI classification vs ground truth) ---")
    print(f"  scorable investigations:      {cls_scored}  "
          f"(excluding {n_cls_undetermined} 'unknown'/unmapped)")
    print(f"  correct:                      {n_cls_correct}")
    print(f"  accuracy:                     {cls_acc*100:6.2f}%")

    # ── Auto-resolution precision ────────────────────────────────────────────
    # An auto-resolved case is CORRECT if the ground-truth anomaly is NOT
    # unsafe-to-autoresolve (i.e., safe to have closed without human review).
    ar = [e for e in excs if e.status == repo.STATUS_AUTO_RESOLVED]
    correct_ar = 0
    unsafe_ar  = 0
    for e in ar:
        key = _gt_key(e)
        if key is None: continue
        gt_row = gt_idx.get(key)
        if not gt_row: continue
        if gt_row.anomaly_type in UNSAFE_TO_AUTORESOLVE:
            unsafe_ar += 1
        else:
            correct_ar += 1
    ar_total = len(ar)
    ar_prec  = (correct_ar / ar_total) if ar_total else None
    print()
    print("--- auto-resolution precision (PRIORITY METRIC) ---")
    print(f"  auto-resolved rows:           {ar_total}")
    print(f"  safely auto-resolved:         {correct_ar}")
    print(f"  UNSAFE auto-resolutions:      {unsafe_ar}   (must be 0 for safety)")
    if ar_prec is None:
        print(f"  precision:                    N/A (no auto-resolutions in this run)")
    else:
        print(f"  precision:                    {ar_prec*100:6.2f}%")

    # ── Manual-review recall ─────────────────────────────────────────────────
    # Denominator: ground-truth records that SHOULD be reviewed (HRT + any
    # non-clean anomaly with high delta).
    # Numerator: how many of those are in manual_review OR resolved-after-review.
    should_review_types = set(UNSAFE_TO_AUTORESOLVE) | {"amount_mismatch",
                                                        "date_mismatch",
                                                        "partial_settlement"}
    # Build per-record ground-truth expectation
    should_review = 0
    routed_ok    = 0
    for e in excs:
        key = _gt_key(e)
        if key is None: continue
        gt_row = gt_idx.get(key)
        if not gt_row or gt_row.anomaly_type == "clean":
            continue
        should_review += 1
        if e.status in (repo.STATUS_MANUAL_REVIEW, repo.STATUS_RESOLVED):
            routed_ok += 1
    mr_recall = (routed_ok / should_review) if should_review else 0.0
    print()
    print("--- manual-review recall ---")
    print(f"  ground-truth cases requiring review:  {should_review}")
    print(f"  correctly routed to manual_review or resolved: {routed_ok}")
    print(f"  recall:                                 {mr_recall*100:6.2f}%")

    # ── Runtime / observability totals ───────────────────────────────────────
    import json
    n_tool_calls_per_inv: List[int] = []
    for i in inv_rows:
        try:
            calls = json.loads(i.tool_calls or "[]")
        except Exception:
            calls = []
        n_tool_calls_per_inv.append(len(calls))
    llm_calls_estimate = sum(1 for i in inv_rows if i.provider == "groq")
    print()
    print("--- runtime / observability ---")
    print(f"  investigations total:              {len(inv_rows)}")
    print(f"  live-Groq investigations:          {prov_dist.get('groq', 0)}")
    print(f"  fallback investigations:           {prov_dist.get('fallback', 0)}")
    print(f"  investigations with any tool call: {sum(1 for n in n_tool_calls_per_inv if n>0)}")
    print(f"  total recorded tool calls:         {sum(n_tool_calls_per_inv)}")
    if n_tool_calls_per_inv:
        print(f"  avg tool calls / investigation:    {sum(n_tool_calls_per_inv)/len(n_tool_calls_per_inv):.2f}")
        print(f"  max tool calls in one investigation:{max(n_tool_calls_per_inv)}")

    db.close()
    return {
        "run_id": run_id,
        "provider_distribution": dict(prov_dist),
        "fallback_reasons": dict(fb_dist),
        "classification_accuracy": cls_acc,
        "auto_resolution_precision": ar_prec,
        "auto_resolved_total": ar_total,
        "unsafe_auto_resolutions": unsafe_ar,
        "manual_review_recall": mr_recall,
        "manual_review_denominator": should_review,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Evaluate controller / AI decisions vs ground_truth.csv")
    p.add_argument("--run", type=str, default=None, help="run_id (default: latest complete)")
    a = p.parse_args()
    evaluate(run_id=a.run)
