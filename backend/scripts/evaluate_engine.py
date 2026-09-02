"""
Step 10.2 — Evaluate the deterministic reconciliation engine against
ground_truth.csv.

Reproducible: pass `--seed N` to regenerate data with that seed first. Reads
ground truth AUTOMATICALLY — never manually enters expected values.

Usage:
    cd backend
    venv/Scripts/python.exe scripts/evaluate_engine.py --seed 42

Metrics reported:
    - dataset size
    - overall classification accuracy
    - overall precision / recall / F1 (binary: is-anomaly?)
    - false-positive / false-negative rate
    - per-anomaly-class precision / recall / F1 / support
    - confusion pairs where the engine disagreed with ground truth
"""
from __future__ import annotations
import argparse, csv, importlib.util, os, sys
from collections import Counter
from typing import Dict, List, Optional, Tuple

# Make the app package importable regardless of CWD
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _BACKEND)
os.chdir(_BACKEND)

from app.engine.normalizer import normalize_order, normalize_settlement, normalize_bank
from app.engine.matcher import reconcile
from app.eval.ground_truth import load_ground_truth, index_by_key, anomaly_counts


# ── Data helpers ──────────────────────────────────────────────────────────────
def read_csv(path: str) -> List[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def regenerate(seed: int, output_dir: str) -> None:
    """Regenerate CSVs deterministically using the project generator."""
    gen_path = os.path.join(_BACKEND, "data", "generate.py")
    spec = importlib.util.spec_from_file_location("_gen_for_eval", gen_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    mod.generate(records=100, seed=seed, output_dir=output_dir)


# ── Engine prediction extraction ──────────────────────────────────────────────
def engine_predictions(result: dict) -> Dict[str, str]:
    """
    Build a per-record engine prediction map:
      key = order_id (linked) or f'orphan:{settlement_id}' (Stage-2 orphan)
      value = 'clean' if matched, else exception_type

    When a record has both a matched row AND an exception row (e.g. duplicate
    case where the original matches and the duplicate is an orphan sharing
    the same order_id), the exception WINS — that's the semantic prediction
    for the underlying record.
    """
    pred: Dict[str, str] = {}
    for m in result["matched"]:
        oid = m.get("order_id")
        if oid:
            pred[oid] = "clean"
    for e in result["exceptions"]:
        oid = e.get("order_id")
        if oid:
            pred[oid] = e["exception_type"]
        elif e.get("settlement_id"):
            pred[f"orphan:{e['settlement_id']}"] = e["exception_type"]
    return pred


# ── Metric primitives ────────────────────────────────────────────────────────
def per_class_metrics(y_true: List[str], y_pred: List[str]) -> Dict[str, dict]:
    """Compute per-class precision/recall/F1/support treating each class as
    the positive class in a one-vs-rest scheme."""
    classes = sorted(set(y_true) | set(y_pred))
    out: Dict[str, dict] = {}
    for c in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == c and p == c)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != c and p == c)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == c and p != c)
        support = sum(1 for t in y_true if t == c)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec  = tp / (tp + fn) if (tp + fn) else 0.0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        out[c] = {"precision": prec, "recall": rec, "f1": f1,
                  "tp": tp, "fp": fp, "fn": fn, "support": support}
    return out


def binary_anomaly_metrics(y_true: List[str], y_pred: List[str]) -> dict:
    """Binary framing: is the record anomalous (anything ≠ 'clean')?"""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t != "clean" and p != "clean")
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == "clean" and p != "clean")
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == "clean" and p == "clean")
    fn = sum(1 for t, p in zip(y_true, y_pred) if t != "clean" and p == "clean")
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec  = tp / (tp + fn) if (tp + fn) else 0.0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    fpr  = fp / (fp + tn) if (fp + tn) else 0.0
    fnr  = fn / (fn + tp) if (fn + tp) else 0.0
    return {"precision": prec, "recall": rec, "f1": f1,
            "false_positive_rate": fpr, "false_negative_rate": fnr,
            "tp": tp, "fp": fp, "tn": tn, "fn": fn}


# ── Entry point ──────────────────────────────────────────────────────────────
def evaluate(seed: int = 42, data_dir: Optional[str] = None) -> dict:
    data_dir = data_dir or os.path.join(_BACKEND, "data", "generated")
    regenerate(seed=seed, output_dir=data_dir)

    orders = [normalize_order(r)      for r in read_csv(os.path.join(data_dir, "orders.csv"))]
    setts  = [normalize_settlement(r) for r in read_csv(os.path.join(data_dir, "settlements.csv"))]
    banks  = [normalize_bank(r)       for r in read_csv(os.path.join(data_dir, "bank_transactions.csv"))]
    gt     = load_ground_truth(os.path.join(data_dir, "ground_truth.csv"))

    result = reconcile(orders, setts, banks)
    pred   = engine_predictions(result)
    gt_idx = index_by_key(gt)

    # Align: iterate ground_truth (source of truth for record identity)
    y_true: List[str] = []
    y_pred: List[str] = []
    unaligned = 0
    confusions: List[Tuple[str, str, str]] = []  # (key, expected, actual)
    for key, r in gt_idx.items():
        exp = r.anomaly_type
        got = pred.get(key)
        if got is None:
            unaligned += 1
            continue
        y_true.append(exp)
        y_pred.append(got)
        if exp != got:
            confusions.append((key, exp, got))

    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    total   = len(y_true)
    accuracy = correct / total if total else 0.0

    per_class = per_class_metrics(y_true, y_pred)
    binary    = binary_anomaly_metrics(y_true, y_pred)

    # ── Report ────────────────────────────────────────────────────────────────
    print("=" * 72)
    print(f"STEP 10.2 — DETERMINISTIC ENGINE EVALUATION  (seed={seed})")
    print("=" * 72)
    print(f"dataset size (records in ground_truth.csv):  {len(gt)}")
    print(f"aligned records (with engine prediction):    {total}")
    print(f"unaligned (record in GT but no engine pred): {unaligned}")
    print()
    print("ground truth anomaly_type distribution:")
    for k, v in sorted(anomaly_counts(gt).items()):
        print(f"  {k:<24} {v:>4}")
    print()
    print("engine prediction distribution:")
    for k, v in sorted(Counter(y_pred).items()):
        print(f"  {k:<24} {v:>4}")

    print()
    print("--- OVERALL ---")
    print(f"classification accuracy:     {accuracy*100:6.2f}%  ({correct}/{total})")
    print()
    print("--- BINARY (is-anomaly?) ---")
    print(f"precision:                   {binary['precision']*100:6.2f}%")
    print(f"recall:                      {binary['recall']*100:6.2f}%")
    print(f"F1:                          {binary['f1']*100:6.2f}%")
    print(f"false_positive_rate:         {binary['false_positive_rate']*100:6.2f}%")
    print(f"false_negative_rate:         {binary['false_negative_rate']*100:6.2f}%")
    print(f"TP={binary['tp']}  FP={binary['fp']}  TN={binary['tn']}  FN={binary['fn']}")

    print()
    print("--- PER ANOMALY CLASS ---")
    print(f"{'class':<24}{'precision':>12}{'recall':>10}{'F1':>10}"
          f"{'TP':>6}{'FP':>6}{'FN':>6}{'support':>10}")
    for c, m in per_class.items():
        print(f"{c:<24}{m['precision']*100:>11.2f}%{m['recall']*100:>9.2f}%"
              f"{m['f1']*100:>9.2f}%{m['tp']:>6}{m['fp']:>6}{m['fn']:>6}{m['support']:>10}")

    print()
    print("--- CONFUSION PAIRS (record-level engine ≠ ground_truth) ---")
    conf_pairs = Counter((t[1], t[2]) for t in confusions)
    if not conf_pairs:
        print("  none")
    for (exp, got), n in sorted(conf_pairs.items(), key=lambda x: -x[1]):
        print(f"  expected={exp:<22} got={got:<22}  count={n}")

    print()
    return {
        "seed": seed,
        "dataset_size": len(gt),
        "aligned": total,
        "unaligned": unaligned,
        "accuracy": accuracy,
        "binary": binary,
        "per_class": per_class,
        "confusions": conf_pairs,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Evaluate deterministic engine vs ground_truth.csv")
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    evaluate(seed=a.seed)
