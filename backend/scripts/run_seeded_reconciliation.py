"""
Drive a reconciliation batch against the CURRENT seed=42 generated dataset,
so the persisted `ai_investigations` rows share the same record identities
as `data/generated/ground_truth.csv`. Prints the created run_id.

Nothing about controller/agent/engine logic is changed — we only skip the
random-seed regeneration that /api/reconciliation/run performs before it
picks up the CSVs. All persistence, policy, resolver, audit paths are the
production ones.

Usage:
    cd backend
    venv/Scripts/python.exe scripts/run_seeded_reconciliation.py --seed 42
"""
from __future__ import annotations
import argparse, os, sys, importlib.util

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _BACKEND)
os.chdir(_BACKEND)


def main(seed: int = 42) -> None:
    # 1) Regenerate CSVs at the given seed (same call the eval script uses)
    gen_path = os.path.join(_BACKEND, "data", "generate.py")
    spec = importlib.util.spec_from_file_location("_gen_for_reco", gen_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    out_dir = os.path.join(_BACKEND, "data", "generated")
    mod.generate(records=100, seed=seed, output_dir=out_dir)
    print(f"regenerated CSVs into {out_dir} (seed={seed})")

    # 2) Monkey-patch the endpoint's own regenerate so it does NOT re-randomize
    from app.api import reconciliation as reco_api
    reco_api._regenerate_data = lambda: None

    # 3) Invoke the production handler in-process
    from app.database import SessionLocal
    from app.schemas.schemas import RunRequest
    db = SessionLocal()
    run = reco_api.run_reconciliation(RunRequest(), db)
    print(f"run_id: {run.run_id}   status: {run.status}   duration: {run.duration_ms}ms")
    print(f"stats:  {run.stats}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    main(seed=a.seed)
