# LedgerLens — AI Finance Controller

> **Reconcile. Investigate. Resolve.**

Built for Razorpay AI Buildathon 2026 — Track 4: AI Finance Controller.

## Architecture

```
Synthetic Financial Data (3 sources)
         ↓
Deterministic Reconciliation Engine  (exact + fuzzy matching)
         ↓
    ┌────┴────┐
  MATCHED  EXCEPTIONS
              ↓
       AI Investigator (Groq LLaMA 3.3 70B + tool calling)
              ↓
       Evidence + Root Cause + Confidence
              ↓
       Risk Policy Engine
         ↙         ↘
  Auto-Resolve   Human Review
         ↘         ↙
          Audit Log
              ↓
         Dashboard
```

## Stack

| Layer    | Technology                        |
|----------|-----------------------------------|
| Frontend | Next.js 14 + TypeScript + Tailwind|
| Backend  | FastAPI + Python                  |
| Engine   | Pandas + custom matching pipeline |
| AI       | Groq API (Llama 3.3 70B) — free  |
| Database | SQLite (dev) → Supabase (prod)    |
| Deploy   | Vercel + Render                   |

## Quick Start

### Backend
```bash
cd backend
cp .env.example .env       # add your GROQ_API_KEY
pip install -r requirements.txt

# Generate synthetic data
python data/generate.py --records 100

# Start API
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

### Generate data at different scales
```bash
python data/generate.py --records 500
python data/generate.py --records 1000 --amount-mismatch 0.15
python data/generate.py --records 50   --duplicate 0.10
```

## Data Sources

| Source               | File                   | Records |
|----------------------|------------------------|---------|
| Merchant Orders      | orders.csv             | N       |
| Razorpay Settlements | settlements.csv        | N + dups|
| Bank Statement       | bank_transactions.csv  | N       |
| Ground Truth Labels  | ground_truth.csv       | N       |

## Anomaly Types

| Type                | Default % | Description                        |
|---------------------|-----------|------------------------------------|
| clean               | 70%       | Perfectly matched 3-way            |
| amount_mismatch     | 10%       | Settlement ≠ order amount          |
| duplicate           | 5%        | Same transaction settled twice     |
| missing_settlement  | 5%        | Order with no settlement           |
| date_mismatch       | 4%        | Settlement >10 days after order    |
| partial_settlement  | 3%        | Only 40–85% of amount settled      |
| unknown_transaction | 3%        | Settlement with no matching order  |

## API Endpoints

```
POST /api/reconciliation/run     — run full reconciliation on loaded data
GET  /api/reconciliation/runs    — list all runs
GET  /api/reconciliation/dashboard — KPIs for latest run
GET  /api/exceptions             — list exceptions (filter by run_id, status)
POST /api/exceptions/{id}/investigate — trigger AI investigation
POST /api/exceptions/{id}/resolve     — mark as resolved
GET  /api/audit                  — audit trail
GET  /api/transactions/orders    — raw order data
```

## Supabase Setup (Production)

1. Create project at supabase.com
2. Run `backend/schema.sql` in SQL Editor
3. Copy Project URL + service_role key from Settings → API
4. Set `DATABASE_URL=postgresql://...` in backend `.env`

## Groq Setup (Free)

1. Sign up at console.groq.com
2. Create API key
3. Set `GROQ_API_KEY=...` in backend `.env`
