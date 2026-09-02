# LedgerLens — AI Finance Controller

> **Reconcile. Investigate. Resolve.** Safely.

Built for Razorpay AI Buildathon 2026 — Track 4: AI Finance Controller.

LedgerLens reconciles orders ↔ settlements ↔ bank transactions, uses an LLM to
**investigate** the exceptions it can't auto-close, and then routes each one
through a **deterministic policy** that decides whether it's safe to
auto-resolve or must go to a human. The LLM never decides what happens to
money.

---

## What LedgerLens is

An AI Finance Controller. It does four things:

1. **Reconciles** three data sources (orders, settlements, bank transactions) with a deterministic weighted matcher.
2. **Investigates** every unmatched or mismatched record with an LLM agent that can call read-only tools (`get_transaction`, `get_settlement`, `get_bank_record`, `get_merchant_profile`, `search_related_transactions`, `get_fee_rules`, `check_duplicate`).
3. **Governs** every proposed resolution with a deterministic policy: risk is computed from `amount_delta` + high-risk-transaction protection, and auto-resolution requires the exception type to sit in a small allowlist AND the model's confidence to clear an authoritative threshold.
4. **Audits** everything — investigation start/complete/failed, every tool call, every policy verdict, every state transition.

Everything the LLM produces is validated against a strict Pydantic schema. If validation, the tool budget, or the round budget is exceeded, the system falls back to a rule-engine stub and records `provider="fallback"` with the exact `fallback_reason` — never presented as a live-AI success.

---

## Architecture

```
Synthetic financial data  (3 CSV sources + ground_truth.csv)
        │
        ▼
Deterministic reconciliation engine   ─── exact + weighted-fuzzy matching
        │
   ┌────┴─────┐
 matched   exceptions
              │
              ▼
     AI investigator  (Groq, 7 read-only tools, hard tool + round budgets)
              │
              ▼
     Pydantic InvestigationResult   (validated shape, provenance recorded)
              │
              ▼
     Deterministic policy   (risk + allowlist + confidence gate)
        ↙          ↘
   Resolver     Human review
        ↘          ↙
         Audit log (lifecycle events)
              │
              ▼
         Dashboard + Exception drawer
```

### Component responsibilities

| Layer | Role | Authority |
|---|---|---|
| **Engine** ([backend/app/engine/matcher.py](backend/app/engine/matcher.py)) | Weighted matcher (50% amount, 25% date, 15% ref, 10% bank); classifies unmatched into `amount_mismatch`, `missing_settlement`, `duplicate`, `date_mismatch`, `partial_settlement`, `unknown_transaction`, `missing_bank_record` | deterministic |
| **AI investigator** ([backend/app/agent/investigator.py](backend/app/agent/investigator.py)) | Groq LLM + tool-calling loop; produces evidence, root cause, classification, confidence | **data only** — no decision authority |
| **Investigation schema** ([backend/app/schemas/investigation.py](backend/app/schemas/investigation.py)) | Strict Pydantic validation of every LLM output; extra fields forbidden on evidence | rejects malformed output → retry / fallback |
| **Policy** ([backend/app/controller/policy.py](backend/app/controller/policy.py)) | `evaluate_risk`, `evaluate_auto_resolution`, `evaluate_exception → PolicyDecision`; `AUTO_RESOLVE_TYPES = {partial_settlement, date_mismatch}`; HRT protection; `amount_delta > 10000 → high` | **sole authority on risk** |
| **Resolver** ([backend/app/controller/resolver.py](backend/app/controller/resolver.py)) | Validates the PolicyDecision then executes the state transition | rejects `InconsistentDecision` before mutating |
| **Repository** ([backend/app/repository/repository.py](backend/app/repository/repository.py)) | `transition_exception` with `ALLOWED_TRANSITIONS` enforcement; `_AI_INV_WRITABLE_COLS` allowlist on investigation writes | idempotent, allowlisted |
| **Audit** — emitted from the reconciliation loop, NOT the agent | `investigation_started`, `tool_called`, `tool_completed`, `investigation_completed`, `investigation_failed`, `policy_evaluated`, `auto_resolved`, `manual_review_required`, `resolved` | agent stays read-only |

### Safety limits (do not change without re-evaluation)

- `AUTO_MATCH_THRESHOLD = 0.90`, `REVIEW_THRESHOLD = 0.70`
- `AUTO_RESOLVE_CONFIDENCE = 0.85` (env-overridable)
- `MAX_ROUNDS = 5`, `MAX_TOTAL_TOOL_CALLS = 8`, `MAX_IDENTICAL_TOOL_CALLS = 2`
- Retry taxonomy: `authentication_error = 0 retries`, `rate_limit/timeout/network = 2 retries`, `unknown = 1 retry`
- `AUTO_RESOLVE_TYPES = {partial_settlement, date_mismatch}` (allowlist)
- `HUMAN_REVIEW_TYPES = {unknown_transaction, duplicate, missing_settlement}` (always manual)

---

## Stack

| Layer    | Technology |
|----------|---|
| Frontend | Next.js 14 + TypeScript |
| Backend  | FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| Engine   | Custom weighted-score matcher (no pandas needed at runtime) |
| AI       | Groq — configurable model via `GROQ_MODEL` (verified with `openai/gpt-oss-20b` and `llama-3.3-70b-versatile`) |
| Database | SQLite for local dev (`backend/ledgerlens.db`) |

**Not integrated at runtime** (but referenced for future work):
- Supabase Postgres — the code path uses SQLAlchemy so a swap is straightforward, but no Supabase client is wired in.
- CSV upload / file-based ingestion — the demo uses the synthetic generator.

---

## Quick Start

### Backend
```bash
cd backend
cp .env.example .env       # add your GROQ_API_KEY
pip install -r requirements.txt

# (optional) generate a deterministic dataset — the API also does this per run
python data/generate.py --seed 42 --records 100

uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Reproducible seeded demo (for judging or CI)
```bash
cd backend
venv/Scripts/python.exe scripts/run_seeded_reconciliation.py --seed 42
venv/Scripts/python.exe scripts/evaluate_engine.py --seed 42
venv/Scripts/python.exe scripts/evaluate_agent.py
venv/Scripts/python.exe scripts/test_failure_modes.py
```
Every metric this project reports is generated by one of these scripts.

---

## Data sources

| Source               | File                   | Records |
|----------------------|------------------------|---------|
| Merchant orders      | orders.csv             | N       |
| Razorpay settlements | settlements.csv        | N + dups|
| Bank statement       | bank_transactions.csv  | N       |
| Ground truth labels  | ground_truth.csv       | N       |

`ground_truth.csv` is used **only** by evaluation scripts under `backend/scripts/` and `backend/app/eval/`. It is **never** imported by controller, policy, resolver, repository, or the agent.

## Anomaly types (default distribution, seed=42)

| Type                | % | Description |
|---|---:|---|
| clean               | 70 | perfectly matched 3-way |
| amount_mismatch     | 10 | settlement ≠ order amount |
| duplicate           |  5 | same transaction settled twice |
| missing_settlement  |  5 | order with no settlement |
| date_mismatch       |  4 | settlement >10 days after order |
| partial_settlement  |  3 | only 40–85% of amount settled |
| unknown_transaction |  3 | settlement with no matching order |

---

## API endpoints

```
POST /api/reconciliation/run             — full reconciliation on generated data
GET  /api/reconciliation/runs            — list runs
GET  /api/reconciliation/runs/{run_id}   — one run
GET  /api/reconciliation/dashboard       — KPIs for the LATEST COMPLETE run
GET  /api/exceptions                     — list (filter by run_id, status)
GET  /api/exceptions/{id}                — one exception with nested investigation
POST /api/exceptions/{id}/investigate    — re-run the investigator (terminal is idempotent)
POST /api/exceptions/{id}/resolve        — mark resolved
POST /api/exceptions/{id}/flag           — flag for manual review
GET  /api/audit                          — audit trail
GET  /api/transactions/orders            — raw orders
GET  /api/transactions/settlements       — raw settlements
GET  /api/transactions/bank              — raw bank txns
```

Every investigation returned in `/api/exceptions*` carries provenance so the UI can distinguish live from fallback:

```json
{
  "provider":        "groq" | "fallback",
  "model":           "openai/gpt-oss-20b" | "fallback-rule-engine",
  "fallback_reason": null | "rate_limit_exhausted" | "authentication_error" |
                     "timeout" | "network_error" | "validation_failure" |
                     "tool_budget_exhausted" | "max_rounds_reached" |
                     "missing_api_key" | "unknown_error"
}
```

---

## Evaluation (real, machine-generated — Milestone 6)

### Deterministic engine — `scripts/evaluate_engine.py --seed 42`

| Metric | Value |
|---|---:|
| Classification accuracy | **93.00 %** (93/100) |
| Binary (is-anomaly?) precision | **100.00 %** |
| Binary (is-anomaly?) recall | **86.67 %** |
| Binary F1 | **92.86 %** |
| False-positive rate | **0.00 %** |

Per-class F1: `date_mismatch`, `duplicate`, `missing_settlement`, `unknown_transaction` all **100 %**; `amount_mismatch` **63.16 %**; `partial_settlement` **0 %** (mis-labelled as `amount_mismatch` at the engine layer — see limitations).

### Controller / agent — `scripts/evaluate_agent.py` (against `run_seeded_reconciliation.py --seed 42`)

- **Auto-resolution precision (priority metric):** N/A in the last measured run — 0 auto-resolutions.
- **Unsafe auto-resolutions:** **0.** Never observed in any measured run.
- **Manual-review recall:** **100 %.** Every non-clean anomaly was correctly routed to manual review or resolved-after-review.
- **Provider distribution in the last measured run:** 0 groq / 22 fallback — all `rate_limit_exhausted` (Groq account daily quota exhausted). This is the honest picture; see §Live AI notes below.
- **Prior live-Groq evidence (Milestone D):** RUN-D5BF2CF7 recorded one live-Groq investigation using `openai/gpt-oss-20b` with 3 tool calls (`get_transaction → get_settlement → get_merchant_profile`), demonstrating the end-to-end live path works when quota is available.

### Failure modes — `scripts/test_failure_modes.py`

**22/22 assertions pass**, covering:

| Case | What it verifies |
|---|---|
| A | Tool failure → safe error metadata, no fabricated evidence |
| B | Missing evidence → `manual_review`, blocked by allowlist |
| C | Invalid LLM JSON → validation raises → fallback with explicit reason |
| D | Hallucinated fee → allowlist blocks auto-resolution |
| E | ₹82,000 delta + AI conf 0.99 low-risk → `policy_risk=high` overrides → `manual_review` |
| F | Repeated tool call → 3rd identical blocked; total budget ceiling enforced |
| G | Groq auth failure → no retry, `authentication_error` fallback, model provenance clean |
| Safety | Zero DB-mutation code paths in `investigator.py` or `tools.py` (grep-verified) |

---

## Live AI notes

The demo may run in **live-Groq** or **fallback** mode depending on quota. The UI truthfully labels every investigation:
- `live · groq` chip — real LLM call with tool activity
- `fallback · rule engine` chip + `fallback-rule-engine` model tag + `reason: <code>` — LLM was unavailable, deterministic stub filled in

Fallback is **never** counted as an AI success in metrics or the drawer. Manual-review recall is 100% in fallback mode by design — nothing is auto-resolved when the LLM cannot judge.

---

## Known limitations (honest)

- **`partial_settlement` mis-labelled as `amount_mismatch` at the engine layer.** The engine has no payments-plan feed, so a partial payment looks identical to a wrong amount. The AI layer's `partial_payment` classification catches this at investigation time.
- **Small-delta `amount_mismatch` cases fall inside the matcher's tolerance band** and are labelled `clean` (4/10 in the seed=42 dataset).
- **Groq daily quota** on the demo account is often exhausted, so the current run is likely to be 100 % fallback. Prior verified live-Groq runs are documented in the evaluation section above.
- **Synchronous reconciliation.** A fresh 100-record batch takes ~30–90 s live, ~50 s in full-fallback (rate-limit retries dominate). Frontend axios timeout on `runReconciliation` is 10 minutes to cover the worst case; other endpoints keep the default. No Redis / Celery / background worker is used; the hackathon-scale batch is well within a sync request.
- **SQLite** for local dev — production would swap the SQLAlchemy URL to Postgres/Supabase but the code path isn't wired to a Supabase client today.

---

## Security posture

- `backend/.env` is git-ignored via `backend/.gitignore` **and** the root `.gitignore` (defense in depth). Only `backend/.env.example` (placeholders) is tracked.
- `git grep` for `gsk_[a-z0-9]{20,}` / `sk-[a-z0-9]{20,}` / `AIzaSy` across every tracked file returns **zero** matches.
- Agent has **no** DB write tools, **no** SQL tool, **no** resolver import, **no** repository import — grep-verified as a test assertion in `test_failure_modes.py`.
- Deterministic policy is the sole authority on risk; the LLM's `risk_level` field is stored for observability only.
- Ground truth is read only by evaluation scripts — never by any decision path.

---

## Repository layout

```
backend/
  app/
    api/            reconciliation, exceptions, audit, transactions
    agent/          investigator + read-only tools
    controller/     policy, decisions, resolver
    engine/         normalizer + weighted matcher
    eval/           ground_truth loader (evaluation-only, NOT imported by prod)
    models/         SQLAlchemy models
    repository/     transitions + investigation persistence
    schemas/        Pydantic wire schemas + InvestigationResult
  data/
    generate.py     deterministic synthetic generator (--seed 42)
    generated/      (git-ignored) generated CSVs + ground_truth.csv
  scripts/
    evaluate_engine.py
    evaluate_agent.py
    run_seeded_reconciliation.py
    test_failure_modes.py
  .env.example      placeholders only
  .env              LOCAL — git-ignored
frontend/
  app/dashboard/    dashboard page + drawer
  components/       KPI cards, charts, exception table + drawer
  lib/api.ts        typed API client
```
