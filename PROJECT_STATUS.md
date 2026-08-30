# LedgerLens — Project Status Report

**Last updated:** 2026-08-31
**Purpose of this doc:** a complete technical snapshot of the project as of this session — what it is, what was broken, what was fixed, what the current design looks like, and every "gotcha" worth remembering before the next work session or a future chat with an AI assistant that has no memory of this one.

---

## 1. What this project is

LedgerLens is an AI Finance Controller built for **Razorpay AI Buildathon 2026 — Track 4**. It reconciles three synthetic financial data sources (merchant orders, Razorpay settlements, bank statement), flags mismatches as "exceptions," and uses an LLM (Groq Llama 3.3 70B) with tool calling to investigate and explain each exception before either auto-resolving it or routing it to human review.

**Stack:**
| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind |
| Backend | FastAPI + Python |
| Engine | Pure Python matching pipeline (no pandas yet) |
| AI | Groq API (Llama 3.3 70B), tool-calling |
| Database | SQLite (dev) |
| Data | Synthetic generator (`backend/data/generate.py`), stdlib only |

**Repo layout:**
```
LedgerLens/
├── backend/          FastAPI app, SQLite DB, data generator
│   ├── app/
│   │   ├── api/          reconciliation, exceptions, transactions, audit routers
│   │   ├── agent/        investigator.py (Groq calls), tools.py
│   │   ├── engine/       matcher.py, normalizer.py, classifier.py
│   │   ├── models/       SQLAlchemy models
│   │   ├── repository/   DB access layer
│   │   └── schemas/      Pydantic schemas
│   ├── data/
│   │   ├── generate.py   synthetic data generator
│   │   └── generated/    orders.csv, settlements.csv, bank_transactions.csv, ground_truth.csv
│   └── venv/             (gitignored)
└── frontend/
    ├── app/              page.tsx (landing), dashboard/, transactions/, exceptions/, audit/
    ├── components/       layout/ (Sidebar, Topbar), dashboard/ (KPICards, Charts, ExceptionTable)
    └── lib/              api.ts (axios client), utils.ts
```

---

## 2. ⚠️ Not under version control

**There is no git repository in this project (`git status` → "not a git repository").** Every fix in this session exists only on disk. If the buildathon submission requires a GitHub repo, or if you want any safety net against a bad edit, **run `git init` and make a first commit before doing anything else.** This is the single highest-priority action item.

---

## 3. Environment quirks specific to this machine

- **Python 3.14.4** is the only Python installed (checked via `py -0p` — no 3.11/3.12/3.13 available). This matters because Python 3.14 is very new (released Oct 2025) and plenty of PyPI packages hadn't shipped prebuilt Windows wheels for it as of the original pins in this repo.
- **No Rust/MSVC toolchain** capable of building `pydantic-core` from source is set up — `link.exe` fails during the build. This is what caused the original "backend won't start" symptom. **Do not re-pin `pydantic`, `fastapi`, `sqlalchemy`, etc. to old versions** — always check `pip index versions <pkg>` and confirm a `cp314-*-win_amd64.whl` exists before pinning.
- **Windows console codepage is cp1252**, not UTF-8. Any bare `print()` containing a Unicode character (✓, ₹ used mid-string in a print, etc.) will crash with `UnicodeEncodeError` the moment that code path runs under a plain `uvicorn`/`python` invocation in this terminal. Two files already had this bug and were fixed (see §4). **If you add new `print()` debug statements, keep them ASCII-only**, or the process will crash on startup with no useful traceback pointing at the real issue.

---

## 4. Bugs found and fixed this session

### 4.1 Backend wouldn't start — dependency pins predated Python 3.14
**File:** [backend/requirements.txt](backend/requirements.txt)
`pydantic==2.7.1` (and fastapi/uvicorn/sqlalchemy/etc. pinned alongside it) had no Windows wheel for `cp314`, so `pip install` tried to compile `pydantic-core` from Rust source and failed at the linker step.
**Fix:** bumped every pin to a version with a prebuilt `cp314-win_amd64` wheel:
`fastapi 0.111.0→0.141.1`, `uvicorn 0.29.0→0.52.4`, `pydantic 2.7.1→2.13.5`, `pydantic-settings 2.2.1→2.15.0`, `sqlalchemy 2.0.30→2.0.52`, `python-multipart 0.0.9→0.0.32`, `httpx 0.27.0→0.28.1`, `python-dotenv 1.0.1→1.2.3`, `rapidfuzz 3.9.3→3.14.5`, `groq 0.9.0→1.7.0`, `faker 24.11.0→40.37.0`.
**Watch for:** `groq` went from `0.9.x` to `1.7.0` — a major version bump. The current usage (`Groq(api_key=...)`, `.chat.completions.create(...)`) is the stable OpenAI-compatible surface and still works, but if you add new Groq SDK features, check the 1.x changelog first.

### 4.2 Startup crash — Unicode checkmark on a cp1252 console
**File:** [backend/app/main.py](backend/app/main.py)
`print("✓  LedgerLens API running")` in the `@app.on_event("startup")` handler crashed with `UnicodeEncodeError` before the server ever bound to a port.
**Fix:** replaced with `print("[ok] LedgerLens API running")`.

### 4.3 Every reconciliation run silently processed 0 records
**File:** [backend/app/api/reconciliation.py](backend/app/api/reconciliation.py)
`_load_generated_data()` built its path as `os.path.dirname(__file__)/../../../data/generated` — **one `..` too many** — which resolved to a nonexistent folder one level above the `backend/` directory instead of `backend/data/generated`. The endpoint returned `200 OK` with `total_records: 0` every time — no error, just silently wrong.
**Fix:** corrected to `../../data/generated` (2 levels up from `app/api/`, not 3).

### 4.4 Every run *after* the first one crashed with a UNIQUE constraint error
**Files:** [backend/app/repository/repository.py](backend/app/repository/repository.py), [backend/app/api/reconciliation.py](backend/app/api/reconciliation.py)
`orders.order_id`, `settlements.settlement_id`, and `bank_transactions.bank_txn_id` all have `unique=True` constraints. `run_reconciliation()` re-inserted the same generated CSV rows on every call without ever clearing the old ones — so the *first* run ever succeeded, and *every run after that* threw `sqlite3.IntegrityError: UNIQUE constraint failed` mid-transaction, leaving that run stuck in DB status `"pending"` with 0 records forever. This is what caused the "Backend not reachable" banner and the "0 records / Needs Review" dashboard state the user saw — the backend was actually up and reachable, it was just crashing on every reconciliation call after the first.
**Fix:** added `clear_orders()`, `clear_settlements()`, `clear_bank_txns()` to `repository.py`, called at the top of `run_reconciliation()` before the reseed. Runs are now safely repeatable.

### 4.5 Two `uvicorn` processes silently double-bound to port 8000
Not a code bug — an operational trap. Windows allowed **two separate `uvicorn` processes to both report `LISTENING` on `127.0.0.1:8000` simultaneously** (one from an earlier session-managed background process, one from the user's own terminal following setup instructions). Requests were routed unpredictably between the stale process (pre-fix code) and the fresh one, which looked exactly like flaky/random bugs — a request would succeed, then an identical request moments later would 500.
**Lesson:** if backend behavior seems inconsistent between identical requests, **check `netstat -ano | grep :8000` for more than one LISTENING PID** before debugging application logic. Always fully stop one instance (kill both the reloader parent and its worker child on Windows — killing just the parent PID can leave the child bound) before starting another.

### 4.6 "Try Demo" and "Open Dashboard" appearing to do "nothing"
Not a bug — by design there is only one dashboard route (`/dashboard`); both buttons land there. "Try Demo" (`app/page.tsx`) POSTs `/api/reconciliation/run` first, then navigates. "Open Dashboard" just navigates directly and the dashboard's own `load()` fetches whichever run is already latest. This looked especially like a bug because the generated data was **fully deterministic** (fixed `seed=42`) at the time, so even a genuinely fresh run produced numerically identical results to the last one. See §4.7 for the fix that makes runs visibly differ now.

### 4.7 Demo data was deterministic — now regenerates randomly per run
**Files:** [backend/data/generate.py](backend/data/generate.py), [backend/app/api/reconciliation.py](backend/app/api/reconciliation.py)
`generate()` defaulted to `seed=42`, so every reconciliation run reused the exact same transactions. Changed the function default to `seed=None` (only seeds the RNG when a caller explicitly passes one — the CLI's own `--seed` flag still defaults to `42`, so `python data/generate.py` stays reproducible for manual testing). Added `_regenerate_data()` in `reconciliation.py`, called at the top of `run_reconciliation()`, which loads `generate.py` via `importlib` and calls `generate(seed=None)` before every run. Also had to apply the same Unicode-print fix from §4.2 to `generate.py`'s own status prints (`✓` → `[ok]`), since this script now executes in-process inside the FastAPI worker instead of only running standalone from the CLI.

> **⚠️ Special condition to remember:** the anomaly-type **ratios** in `generate()` are fixed percentages (10% amount-mismatch, 5% duplicate, 5% missing-settlement, 4% date-mismatch, 3% partial, 3% unknown), and with `records=100` these are computed as **deterministic integer counts** (`int(records * ratio)`) regardless of random seed. Randomizing the seed changes *which* transactions get which anomaly and their specific amounts/dates/order IDs — it does **not** meaningfully change the *category counts*. So don't be surprised if "Total Records," "Matched," and "Exceptions" land in a similar range run after run (e.g. 76–78 matched, 16–18 exceptions) even with true randomization — that's expected, not a sign the fix didn't work. What **does** visibly change every run: `amount_reconciled`, every order ID, every specific exception's numbers. Verified across three consecutive runs after the fix: **78/18/₹20.5L → 77/16/₹18.9L → 76/17/₹19.4L** (matched/exceptions/amount reconciled).
> If you want total record/exception *counts* to visibly vary too, the next step would be randomizing `records` itself (e.g. `random.randint(80, 150)`) inside `generate()` — not done yet, flagged here as a possible future enhancement, not a bug.

---

## 5. Frontend: visual redesign (partial — "immediate" pass, not the full revamp)

The user described the original UI as "generic purple AI SaaS" (blue→purple gradients, glass/blur cards, neon glow shadows) and wants a full GUI overhaul on a **dedicated day before the deadline**. In the meantime, a scoped token-level pass was done to kill the worst offenders immediately.

### Design reference audit
Three of the user's own past projects were inspected for style direction:
- **`F:\NTT\NTT-Website`** — soft glassmorphism, violet/cyan (`#7C6EFF`/`#38C2FF`), light/dark theme via CSS vars. **Not used** — too close to the "consumer social app" register the user was rejecting.
- **`D:\Desktop\pathfinder-tsp-main`** — a "cyber" terminal theme: near-black bg, JetBrains Mono + Rajdhani, semantic 5-color system (cyan/amber/green/red/purple), uppercase tracked `.stat-label`/`.stat-value` classes, thin bordered cards, no shadows. Partial inspiration (mono-for-data pattern).
- **`D:\Desktop\Smart-Care---Community-Connect-main`** — an ops/monitoring dashboard: `--ink #0B1220` / `--panel #131B2C` / `--panel-raised #182238` / `--line #24304A` surfaces, **Space Grotesk** (display) + **Inter** (body) + **JetBrains Mono** (data/labels), semantic `--accent #4C8DFF` (blue, no purple) / `--green #2FB380` / `--amber #F5A524` / `--red #EF4444`. **This is the one actually adopted** — closest register to a finance/audit tool.

### What changed
| File | Change |
|---|---|
| [frontend/app/globals.css](frontend/app/globals.css) | New CSS variable system (ink/panel/line/text/accent/green/amber/red), Google Fonts import (Space Grotesk + Inter + JetBrains Mono), `.stat-label`/`.stat-value` utility classes, `.glass` redefined as a flat bordered panel (no more `backdrop-filter: blur`) |
| [frontend/tailwind.config.ts](frontend/tailwind.config.ts) | `brand.*` colors updated to the new palette, `purple` token removed entirely, `fontFamily.display`/`fontFamily.mono` added |
| [frontend/app/page.tsx](frontend/app/page.tsx) | Landing hero — removed every gradient (logo box, headline text-fill, CTA button), flat panels, mono stat pills |
| [frontend/app/dashboard/page.tsx](frontend/app/dashboard/page.tsx) | Same palette swap, removed duplicate Google Fonts `<link>` tag (now centralized in globals.css) |
| [frontend/components/layout/Sidebar.tsx](frontend/components/layout/Sidebar.tsx), [Topbar.tsx](frontend/components/layout/Topbar.tsx) | Solid accent blue instead of blue→purple gradients |
| [frontend/components/dashboard/KPICards.tsx](frontend/components/dashboard/KPICards.tsx) | Mono values via `.stat-value`, dropped glow box-shadows, "Amount Reconciled" purple → accent blue |
| [frontend/components/dashboard/Charts.tsx](frontend/components/dashboard/Charts.tsx) | Chart color arrays swapped to the new palette, "Auto-Resolved" bar purple → accent blue |
| [frontend/components/dashboard/ExceptionTable.tsx](frontend/components/dashboard/ExceptionTable.tsx) | Severity badge colors, AI Investigation panel purple accent → blue accent, drawer background flattened |
| [frontend/app/audit/page.tsx](frontend/app/audit/page.tsx) | `actorColor()` map: Tailwind default `purple-400` (for the "ai" actor) → `#4C8DFF` |

### ⚠️ Explicitly NOT touched yet (deferred to the dedicated GUI day)
- **Layout/structure** of any page — only colors, fonts, and surface treatment changed. Grid layouts, card arrangement, table density are all untouched.
- **`frontend/app/transactions/page.tsx`** and **`frontend/app/exceptions/page.tsx`** — these use Tailwind utility classes + `var(--border)`/`var(--muted)` CSS vars (not hardcoded hex), so they inherited the new palette automatically for free, but their layout/content was not reviewed.
- **Light theme** (`.light` class in globals.css) — token values were updated for consistency but the light/dark toggle itself isn't wired up anywhere in the app; untested.
- Pathfinder's grid-line background texture and "cyber" glow accents were considered but not applied — flagged as a possible extra touch for the full revamp, not done.

---

## 6. Current verified state (as of end of this session)

- Backend starts cleanly: `cd backend && venv\Scripts\activate && uvicorn app.main:app --reload` → binds `http://127.0.0.1:8000`, `/health` → `{"status":"ok"}`, `/docs` loads.
- `POST /api/reconciliation/run` is now **safely repeatable** and produces fresh randomized data each call (see §4.7 for what does/doesn't vary).
- Frontend (`npm run dev` → `http://localhost:3000`) landing page, dashboard, and exception drawer all render with the new palette; both "Try Demo" and "Run New Batch" trigger real new runs end-to-end with no console errors.
- **`GROQ_API_KEY` in `backend/.env` is still the placeholder value** (`your_groq_api_key_here`). The AI investigator ([backend/app/agent/investigator.py](backend/app/agent/investigator.py)) catches the resulting `401 Invalid API Key` error and falls back to a rule-based stub — this is why every exception's investigation currently reads something like *"Rule-based stub: ... AI error: Error code: 401 ..."* embedded directly in the `explanation` field. **This is expected fallback behavior, not a bug** — but it also means the actual Groq tool-calling investigation flow (the core "AI Investigator" feature of this whole project) has never been exercised end-to-end yet. Add a real key to `backend/.env` and re-run to test it for the first time.

---

## 7. Known open items / suggested next steps

1. **`git init` this repo** — currently zero version control (see §2). Do this before any further large edits.
2. **Add a real `GROQ_API_KEY`** and verify the actual LLM tool-calling investigation path works (never yet tested with a live key — everything so far has exercised the fallback stub only).
3. Full GUI revamp (structure, not just tokens) — user's own dedicated day, planned but not scheduled yet.
4. Consider randomizing `records` count in `generate()` if visibly-varying total counts (not just amounts) matters for the demo (§4.7).
5. `transactions/` and `exceptions/` pages haven't had a content/layout review, only inherited the palette automatically.
6. Confirm only **one** `uvicorn` process is ever running on port 8000 at a time going forward (§4.5) — check `netstat -ano | grep :8000` if behavior ever seems inconsistent between identical requests.
7. Frontend `.env.local` → `NEXT_PUBLIC_API_URL=http://localhost:8000` — correct for local dev, will need updating for any deployed environment (README mentions Vercel + Render for prod).

---

## 8. Quick reference — how to run everything

```bash
# Backend
cd backend
venv\Scripts\activate          # Windows cmd.exe — use venv\Scripts\Activate.ps1 for PowerShell
uvicorn app.main:app --reload  # → http://localhost:8000, docs at /docs

# Frontend (separate terminal)
cd frontend
npm run dev                    # → http://localhost:3000
```

No manual data generation step needed — `POST /api/reconciliation/run` regenerates fresh data automatically now (§4.7). The old README instruction to run `python data/generate.py` manually first is no longer required for the demo flow, though it still works standalone for anyone who wants a fixed, reproducible dataset (uses `seed=42` by default via the CLI).
