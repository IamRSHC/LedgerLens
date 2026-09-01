# LedgerLens — AI Agent Hackathon-Ready Execution Plan

**Project:** LedgerLens — Reconcile. Investigate. Resolve.  
**Track:** Razorpay Buildathon — Track 4  
**Purpose:** Step-by-step implementation plan for making the existing LedgerLens AI Controller / Agent genuinely hackathon-ready.  
**Execution model:** The coding AI agent must execute **one step at a time**, verify the result, and produce a structured completion report after every step before proceeding.

---

# 0. EXECUTION CONTRACT

This document is intentionally written as an **execution plan**, not as a general architecture proposal.

The AI coding agent must follow these rules:

1. **Inspect before modifying.**
2. **Do not rewrite working systems unnecessarily.**
3. **Do not introduce large frameworks unless explicitly required by a step.**
4. **Do not replace deterministic financial logic with LLM logic.**
5. **The LLM investigates; deterministic code makes financial risk/resolution decisions.**
6. **Every step must end with verification.**
7. **Every step must produce a completion report.**
8. **Do not continue to the next step if the current step fails its acceptance criteria.**
9. **Preserve the existing GUI unless a step explicitly requires a backend-facing UI change.**
10. **Do not add RAG, vector databases, multi-agent systems, LangChain, Redis, Kafka, Celery, or similar infrastructure unless a later step explicitly proves it is necessary.**
11. **Do not send, expose, commit, or hard-code secrets.**
12. **Do not report stub/fallback behaviour as successful live AI behaviour.**
13. **Use the current repository as the source of truth for existing implementation.**
14. **At the end of every step, provide the report defined in Section 3.**
15. **Wait for the user to review/approve the report before moving to the next step unless the user explicitly asks for continuous execution.**

---

# 1. CURRENT BASELINE

The current repository has:

```text
frontend/
  Next.js 14.2.5
  App Router
  Dashboard / Transactions / Exceptions / Audit
  Recharts
  existing liquid-glass GUI system

backend/
  FastAPI
  SQLAlchemy
  SQLite
  reconciliation engine
  AI investigator
  repository layer
  synthetic data generator
  audit logging

backend/app/agent/
  investigator.py
  tools.py

backend/app/engine/
  normalizer.py
  matcher.py
  classifier.py

backend/app/repository/
  repository.py

backend/app/models/
  models.py

backend/app/schemas/
  schemas.py
```

Current AI architecture:

```text
Exception
   ↓
investigator.py
   ↓
Groq tool-calling loop
   ↓
5 read-only DB tools
   ↓
JSON response
   ↓
classifier.py
   ↓
auto-resolve / leave open
```

Important current limitations already identified:

- Groq live path has not been exercised because the API key is currently a placeholder.
- LLM output is parsed with `json.loads`; there is no Pydantic validation.
- The LLM can currently provide/override `risk_level`; risk must become fully deterministic.
- `review` is a separate reconciliation result state and is not properly integrated into the exception lifecycle.
- `manual_review` exists conceptually but is never actually written.
- Duplicate anomalies are generated but not correctly classified by the matcher.
- Missing bank records are not properly surfaced as their own exception type.
- `result_id` on exceptions is currently left `None`.
- The current `AUTO_RESOLVE_TYPES` definition is not actually used by the policy.
- The frontend and backend confidence thresholds differ (`0.80` vs `0.85`).
- AI tool calls are stored in `ai_investigations.tool_calls` but are not represented as audit events.
- The current agent has no dedicated `search_related_transactions()` tool.
- The current agent has no `get_merchant_profile()` tool.
- Ground truth exists, but there is no evaluation harness.
- Retry/rate-limit handling for Groq is minimal.
- AI investigation is synchronous inside `/api/reconciliation/run`.
- Real CSV upload fields exist in the request schema but are currently ignored.
- Supabase/PostgreSQL is declared but not currently wired into runtime.

These are the baseline problems this plan addresses.

---

# 2. TARGET ARCHITECTURE

The target architecture is:

```text
                 LEDGERLENS CONTROLLER
                         │
             ┌───────────┴───────────┐
             │                       │
      DETERMINISTIC LAYER       AI INVESTIGATION
             │                       │
      Normalize                Groq LLM
      Match                    Tool Calls
      Score                    Evidence
      Classify                 Root Cause
      Metrics                  Confidence
             │                       │
             └───────────┬───────────┘
                         ↓
                  PYDANTIC VALIDATION
                         ↓
                  DETERMINISTIC POLICY
                         ↓
              ┌──────────┴──────────┐
              ↓                     ↓
         AUTO-RESOLVE         MANUAL REVIEW
              └──────────┬──────────┘
                         ↓
                      AUDIT
```

The core principle is:

> **AI does not decide whether money is safe to resolve. The policy engine does.**

---

# 3. MANDATORY REPORT AFTER EVERY STEP

After completing **every step**, the AI coding agent must produce a report using this exact structure.

```text
# STEP X COMPLETION REPORT

## 1. Step
<step number + exact title>

## 2. Objective
<what this step was supposed to accomplish>

## 3. What Existed Before
<exact relevant implementation before changes>

## 4. Files Inspected
<list files inspected>

## 5. Files Created
<list files created, or "None">

## 6. Files Modified
<list files modified>

## 7. Files Deleted
<list files deleted, or "None">

## 8. What Changed
<detailed summary of implementation changes>

## 9. Architecture Impact
<how the system architecture changed, if at all>

## 10. API / Schema Impact
<new or modified endpoints, models, fields, or contracts>

## 11. AI-Agent Impact
<what changed in the AI agent/tool/prompt/policy behaviour>

## 12. Database Impact
<migrations, tables, fields, indexes, or "None">

## 13. Tests / Verification Performed
<commands and checks executed>

## 14. Test Results
<pass/fail results with useful output>

## 15. Known Limitations
<anything intentionally not solved>

## 16. Risks / Regressions
<any possible regressions or concerns>

## 17. Rollback Notes
<how the change can be reverted>

## 18. Acceptance Criteria
- [ ] criterion
- [ ] criterion

## 19. Final Status
PASS / PASS WITH NOTES / FAIL

## 20. Recommendation
<whether the next step is safe to begin>
```

### Additional rule

If the step is **FAIL**, do not start the next step.

---

# 4. PHASE 0 — BASELINE AND SAFETY

## STEP 0.1 — Create a Clean Baseline

### Objective

Create a reproducible baseline before changing the AI/controller implementation.

### Actions

1. Verify current git status.
2. Record current branch and commit.
3. Record Python version.
4. Record Node/npm version.
5. Install or verify backend dependencies.
6. Install or verify frontend dependencies.
7. Start backend.
8. Start frontend.
9. Verify:
   - `/`
   - `/health`
   - `/dashboard`
10. Run the current test/build commands if present.
11. Capture the current repository state.

### Required evidence

```text
git status
git rev-parse HEAD
python --version
node --version
npm --version
backend health response
frontend build/dev verification
```

### Acceptance criteria

- [ ] Repository state recorded.
- [ ] Backend starts.
- [ ] Frontend starts.
- [ ] `/health` returns success.
- [ ] Existing dashboard loads.
- [ ] No baseline build errors.

### Deliverable

**STEP 0.1 Completion Report**

---

# 5. PHASE 1 — REPAIR THE DETERMINISTIC CONTROLLER FOUNDATION

This phase must be completed before making the AI agent more sophisticated.

---

## STEP 1.1 — Unify Reconciliation Result Semantics

### Problem

Current engine produces:

```text
matched
review
exceptions
```

but `review` does not participate correctly in the AI/controller lifecycle.

### Target

Use:

```text
MATCHED
EXCEPTION
```

at the reconciliation-result level.

Then use the exception lifecycle for unresolved/processed states:

```text
OPEN
AI_INVESTIGATING
AUTO_RESOLVED
MANUAL_REVIEW
RESOLVED
```

### Actions

1. Inspect matcher output.
2. Identify all uses of `review`.
3. Replace ambiguous batch-level `review` semantics without destroying useful score information.
4. Preserve:
   - match score
   - match type
   - amount delta
   - date delta
5. Ensure exceptions enter the controller workflow.
6. Update response schemas.
7. Update repository persistence.
8. Update frontend types only where required to maintain compatibility.

### Acceptance criteria

- [ ] No exception disappears into a non-controller `review` bucket.
- [ ] Match metadata is preserved.
- [ ] Every unresolved anomaly becomes an `exception`.
- [ ] Existing matched transactions remain matched.
- [ ] Dashboard counts remain internally consistent.

### Deliverable

**STEP 1.1 Completion Report**

---

## STEP 1.2 — Implement Correct Exception Lifecycle

### Target lifecycle

```text
OPEN
  ↓
AI_INVESTIGATING
  ↓
┌──────────────────────┐
│                      │
AUTO_RESOLVED      MANUAL_REVIEW
│                      │
└──────────┬───────────┘
           ↓
        RESOLVED
```

### Actions

1. Add actual support for `manual_review`.
2. Create explicit transitions.
3. Prevent `Flag for Review` from setting `resolved`.
4. Ensure `Mark Resolved` works from manual review.
5. Decide safe idempotency rules:
   - resolving an already resolved exception
   - flagging an already manual-review exception
   - investigating an already resolved exception
6. Update audit entries for each transition.

### Acceptance criteria

- [ ] `manual_review` can actually be written.
- [ ] Flagging for review no longer means resolved.
- [ ] Resolve transitions are explicit.
- [ ] Invalid transitions are rejected or safely ignored.
- [ ] Every state change creates an audit entry.

---

## STEP 1.3 — Link Results to Exceptions

### Problem

`Exception.result_id` is currently left `None`.

### Actions

1. Inspect result insertion order.
2. Ensure result IDs are available before creating exceptions.
3. Link each exception to its corresponding reconciliation result.
4. Update repository methods if necessary.
5. Verify API responses expose the relationship where useful.

### Acceptance criteria

- [ ] Every exception references the correct result.
- [ ] Result → exception navigation is possible in backend data.
- [ ] No orphaned exception records are created by normal reconciliation.

---

## STEP 1.4 — Fix Duplicate Detection

### Problem

The generator creates duplicates, but the matcher does not properly emit `duplicate`.

### Actions

Implement deterministic duplicate detection using stable evidence such as:

- same order/UTR relationship
- repeated settlement records
- same financial identity
- duplicate settlement within the anomaly rules

Do not use the LLM for duplicate detection.

### Acceptance criteria

- [ ] Generator-created duplicates are classified as `duplicate`.
- [ ] They no longer become generic `unknown_transaction`.
- [ ] Severity rules work with actual `duplicate` exceptions.
- [ ] Ground-truth anomaly type matches engine output.

---

## STEP 1.5 — Fix Missing Bank Record Detection

### Problem

`missing_bank_record` exists conceptually but is not reliably emitted.

### Actions

Ensure the deterministic engine distinguishes:

```text
settlement exists
+
bank record absent
```

from other mismatch types.

### Acceptance criteria

- [ ] Missing bank records are explicitly classified.
- [ ] They are not silently treated as successful matches.
- [ ] Severity is deterministic.
- [ ] Ground truth can evaluate this case.

---

## STEP 1.6 — Make Match Types Honest

### Problem

Current `match_type` semantics can call a result "exact" simply because `order_id` matched, even though the full result still passed through scoring.

### Target

Use clear semantics such as:

```text
exact
fuzzy
```

or another small set only if justified.

### Actions

Document and implement precise match-type meaning.

Do not over-engineer this.

### Acceptance criteria

- [ ] `exact` means what its name says.
- [ ] `fuzzy` means scoring/secondary evidence was required.
- [ ] Frontend labels remain understandable.

---

## STEP 1.7 — Centralize Policy Thresholds

### Problem

Frontend uses `0.80`; backend uses `0.85`.

### Actions

Create a single backend policy configuration.

Example:

```text
AUTO_RESOLVE_CONFIDENCE = 0.85
```

Frontend should consume the backend's actual decision rather than independently recreating the rule.

### Acceptance criteria

- [ ] One authoritative threshold exists.
- [ ] Frontend no longer contradicts backend policy.
- [ ] Threshold is configurable.
- [ ] Tests cover boundary conditions.

---

# 6. PHASE 2 — BUILD THE REAL CONTROLLER POLICY

---

## STEP 2.1 — Create Dedicated Policy Module

Create:

```text
backend/app/controller/
├── __init__.py
├── policy.py
├── decisions.py
└── resolver.py
```

### Separation

`policy.py`:

> Should this exception be eligible for automatic resolution?

`decisions.py`:

> What decision did the policy make and why?

`resolver.py`:

> Execute the approved application-level resolution.

### Important

The policy module must not call the LLM.

### Acceptance criteria

- [ ] Controller policy is independent of investigator.py.
- [ ] Unit-testable functions exist.
- [ ] Policy reasons are explicit.

---

## STEP 2.2 — Implement Deterministic Risk Policy

Use deterministic rules.

Example:

### HIGH RISK

```text
unknown_transaction
duplicate
missing_settlement
potential_fraud
large financial delta
insufficient evidence
```

### MEDIUM RISK

```text
amount mismatch above configured low-risk threshold
unusual timing
partial settlement requiring verification
```

### LOW RISK

```text
known benign fee difference
known timing difference
small validated discrepancy
```

### Critical rule

A high LLM confidence score must NOT downgrade a structurally high-risk exception.

Example:

```text
₹82,000 mismatch
AI confidence = 0.99
→ HUMAN REVIEW
```

### Acceptance criteria

- [ ] Risk comes from backend policy.
- [ ] LLM cannot override risk.
- [ ] Large-value exceptions remain protected.
- [ ] High-risk categories remain protected.

---

## STEP 2.3 — Define Auto-Resolution Allowlist

Use explicit policy rather than only:

```text
not human review
+
confidence >= 0.85
```

Example concept:

```text
AUTO_RESOLVABLE_TYPES = {
    settlement_fee,
    known_timing_difference,
    validated_partial_settlement
}
```

with additional conditions.

### Requirements

Automatic resolution should require:

```text
allowed exception type
+
sufficient evidence
+
confidence >= threshold
+
risk not high
+
delta within safe bounds
```

### Acceptance criteria

- [ ] Explicit allowlist exists.
- [ ] High-risk exception can never auto-resolve.
- [ ] Allowed exception types require evidence.
- [ ] Monetary limits are enforced.

---

## STEP 2.4 — Make Resolution Execution Deterministic

The LLM should recommend.

Application code executes.

Flow:

```text
AI recommendation
      ↓
Policy validation
      ↓
Resolution command
      ↓
Database mutation
      ↓
Audit entry
```

The agent must not directly mutate the database.

### Acceptance criteria

- [ ] No AI tool directly modifies financial records.
- [ ] Application-level resolver performs mutations.
- [ ] Resolution is auditable.

---

# 7. PHASE 3 — MAKE THE AI OUTPUT SAFE

---

## STEP 3.1 — Define `InvestigationResult`

Create a strict Pydantic schema.

Suggested fields:

```text
root_cause
classification
confidence
explanation
recommended_action
evidence
```

Optional metadata:

```text
reasoning_summary
```

Do not expose private model chain-of-thought.

### Classification should be constrained

Example:

```text
settlement_fee
timing_difference
data_entry_error
potential_fraud
duplicate
partial_payment
missing_bank_record
missing_settlement
unknown
```

### Evidence object

Use something like:

```text
source
field
value
description
```

### Acceptance criteria

- [ ] LLM response is validated through Pydantic.
- [ ] Confidence is constrained to 0–1.
- [ ] Classification is constrained.
- [ ] Evidence has a stable shape.
- [ ] Invalid output is rejected safely.

---

## STEP 3.2 — Remove LLM-Controlled Risk

The LLM must stop deciding `risk_level`.

### Before

```text
LLM output
   ↓
risk_level
```

### After

```text
LLM output
   ↓
controller.policy.risk_level(...)
```

If keeping the model field temporarily for compatibility, ignore it for actual policy.

### Acceptance criteria

- [ ] Model-provided risk is never authoritative.
- [ ] Backend policy is authoritative.
- [ ] Tests prove this.

---

## STEP 3.3 — Improve the Investigation Context Packet

Current prompt includes only basic exception fields.

Create a structured context packet.

Example:

```text
EXCEPTION
type: amount_mismatch
severity: warning
order_id: ORD-1828
settlement_id: SET-9912
delta: ₹50

AVAILABLE SOURCES
transaction
settlement
bank
fee rules
previous exceptions
related transactions
merchant profile
```

Do not dump the full database into the model.

### Acceptance criteria

- [ ] Context is explicit.
- [ ] Only relevant exception data is included.
- [ ] Sensitive/unrelated data is not dumped.
- [ ] Prompt construction is centralized.

---

# 8. PHASE 4 — STRENGTHEN THE AGENT TOOLS

---

## STEP 4.1 — Audit and Harden Existing Tools

Current tools:

```text
get_transaction()
get_settlement()
get_bank_record()
get_fee_rules()
get_previous_exceptions()
```

For each tool:

1. Validate arguments.
2. Return predictable JSON-serializable output.
3. Avoid leaking internal objects.
4. Handle missing records cleanly.
5. Keep all financial reads deterministic.
6. Keep tools read-only.

### Acceptance criteria

- [ ] All tools return predictable structures.
- [ ] Missing records produce explicit not-found responses.
- [ ] No tool can mutate data.
- [ ] No tool accepts arbitrary SQL.

---

## STEP 4.2 — Add `search_related_transactions()`

Purpose:

Allow evidence-based pattern comparison.

It should support controlled filters such as:

```text
merchant_id
order_id
utr
amount range
date range
exception type
```

Do not allow unrestricted queries.

### Example use

```text
Current mismatch = ₹50

Related records:
TXN012 → ₹50 difference
TXN023 → ₹50 difference
TXN031 → ₹50 difference

Conclusion:
consistent fee pattern
```

### Acceptance criteria

- [ ] Tool is read-only.
- [ ] Tool has bounded query parameters.
- [ ] Results are concise.
- [ ] Results can be cited as evidence.

---

## STEP 4.3 — Add `get_merchant_profile()`

Return controlled merchant metadata.

Example:

```json
{
  "merchant_id": "MERCH-0003",
  "fee_rate": 0.02,
  "settlement_lag_days": 2,
  "risk_tier": "standard"
}
```

Do not invent merchant profile values dynamically.

### Acceptance criteria

- [ ] Profile is deterministic.
- [ ] Tool is read-only.
- [ ] Data can be traced to configured application data.

---

# 9. PHASE 5 — BUILD A ROBUST AGENT LOOP

---

## STEP 5.1 — Formalize Agent States

Use a conceptual state machine:

```text
START
  ↓
UNDERSTAND
  ↓
INVESTIGATE
  ↓
TOOL_CALL
  ↓
OBSERVE
  ↓
NEED_MORE_EVIDENCE?
  ├── YES → INVESTIGATE
  └── NO
        ↓
STRUCTURED_RESULT
        ↓
VALIDATE
        ↓
POLICY
        ↓
RESOLVE / REVIEW
```

Do not implement a giant agent framework.

A simple Python loop is enough.

---

## STEP 5.2 — Prevent Tool Loops

Current agent can theoretically call the same tools repeatedly.

Add guardrails such as:

```text
max rounds
max repeated tool call
max total tool calls
```

Example:

```text
max_rounds = 5
max_total_tools = 8
same_tool_same_args_limit = 2
```

### Acceptance criteria

- [ ] Agent cannot loop indefinitely.
- [ ] Repeated identical calls are controlled.
- [ ] Tool budget is enforced.

---

## STEP 5.3 — Add Tool Execution Metadata

Every call should record:

```text
tool
arguments
result_summary
started_at
duration_ms
status
```

Example:

```json
{
  "tool": "get_settlement",
  "arguments": {
    "settlement_id": "SET-8821"
  },
  "result_summary": "Settlement found",
  "duration_ms": 124,
  "status": "success"
}
```

Do not store unnecessary raw database dumps.

---

# 10. PHASE 6 — GROQ LIVE PATH

---

## STEP 6.1 — Configure Groq Safely

Use environment variables.

Required:

```text
GROQ_API_KEY
```

Optional configuration:

```text
GROQ_MODEL
GROQ_MAX_ROUNDS
GROQ_MAX_TOKENS
```

Never hard-code the key.

### Verification

Perform one minimal live request.

### Acceptance criteria

- [ ] API key is loaded from environment.
- [ ] Key is not committed.
- [ ] Groq client initializes.
- [ ] One live request succeeds.
- [ ] The model name is configurable.

---

## STEP 6.2 — Verify One Real Tool Call

Use one known exception.

Target:

```text
Exception
   ↓
Groq
   ↓
get_settlement()
   ↓
tool result
   ↓
Groq final result
```

Do not move forward until this works.

### Required evidence

The completion report must include:

```text
tool selected
tool executed
tool result summary
final structured output
```

Do not expose secrets.

---

## STEP 6.3 — Verify Multi-Tool Investigation

Test an exception where the agent needs at least two tools.

Example:

```text
get_settlement()
+
get_fee_rules()
```

Expected:

```text
evidence
→ settlement fee
→ confidence
→ recommendation
```

### Acceptance criteria

- [ ] Multiple tools can be called in one investigation.
- [ ] Tool results are passed back correctly.
- [ ] Final output remains schema-valid.

---

# 11. PHASE 7 — RESILIENCE AND FALLBACK

---

## STEP 7.1 — Add Retry / Rate-Limit Handling

Do not catch all errors and immediately hide them.

Distinguish:

```text
authentication failure
rate limit
timeout
temporary network failure
invalid model response
tool failure
```

Recommended behaviour:

```text
temporary failure
   ↓
limited retry with backoff
   ↓
if still failing
   ↓
safe fallback / manual review
```

### Acceptance criteria

- [ ] Temporary errors can retry.
- [ ] Authentication errors are visible.
- [ ] Rate limits do not silently masquerade as successful AI.
- [ ] Retries are bounded.

---

## STEP 7.2 — Make Fallback Explicit

Existing `_stub_investigation()` may remain.

But output must identify provider:

```text
provider = groq
```

or:

```text
provider = fallback
```

Also include:

```text
fallback_reason
```

where appropriate.

### Acceptance criteria

- [ ] Fallback results are distinguishable.
- [ ] UI/API can tell whether Groq actually ran.
- [ ] Reports never call fallback "AI success."

---

# 12. PHASE 8 — AGENT AUDITABILITY

---

## STEP 8.1 — Audit Investigation Lifecycle

Add audit events:

```text
investigation_started
tool_called
tool_completed
investigation_completed
investigation_failed
policy_evaluated
auto_resolved
manual_review_required
resolved
```

### Important

Do not dump raw model prompts or private chain-of-thought into public audit logs.

Store:

- event
- actor
- summary
- relevant IDs
- outcome
- confidence
- policy decision

---

## STEP 8.2 — Improve Investigation Persistence

Ensure `ai_investigations` contains:

```text
provider
model
confidence
classification
root_cause
recommended_action
evidence
tool_calls
risk_level
auto_resolved
created_at
```

Add fields only when useful.

Avoid unnecessary schema expansion.

---

# 13. PHASE 9 — MANUAL REVIEW WORKFLOW

---

## STEP 9.1 — Implement Manual Review End-to-End

Flow:

```text
AI investigation
      ↓
Policy says human review
      ↓
status = manual_review
      ↓
user sees queue
      ↓
user investigates
      ↓
user resolves
      ↓
audit log
```

Optional metadata:

```text
reviewer
review_note
reviewed_at
```

Only add these if they materially improve the workflow.

### Acceptance criteria

- [ ] Manual review is a real persisted state.
- [ ] Manual-review exceptions appear in the correct UI filter.
- [ ] Resolve action works.
- [ ] Audit records the review.

---

## STEP 9.2 — Fix `Flag for Review`

The frontend action must call a dedicated semantic backend operation or a resolve endpoint with an explicit transition.

It must NOT be:

```text
resolve(status="resolved")
resolution="Flagged for manual review"
```

### Acceptance criteria

- [ ] Flag action sets `manual_review`.
- [ ] Audit action is `flagged_for_manual_review`.
- [ ] User can later resolve it.

---

# 14. PHASE 10 — GROUND-TRUTH EVALUATION

This phase is essential for the hackathon.

---

## STEP 10.1 — Build Ground-Truth Loader

Read:

```text
ground_truth.csv
```

Map:

```text
record identity
→ expected anomaly type
→ expected match outcome
```

Do not manually enter results.

---

## STEP 10.2 — Evaluate Deterministic Engine

Create:

```text
backend/scripts/evaluate_engine.py
```

Measure:

```text
precision
recall
F1
classification accuracy
false-positive rate
false-negative rate
```

Evaluate anomaly classes separately.

### Acceptance criteria

- [ ] Ground truth is automatically loaded.
- [ ] Results are reproducible.
- [ ] Metrics are machine-generated.

---

## STEP 10.3 — Evaluate Controller Decisions

Create:

```text
backend/scripts/evaluate_agent.py
```

Measure at least:

```text
classification accuracy
root-cause accuracy
auto-resolution precision
manual-review recall
```

### Priority metric

**Auto-resolution precision**

Reason:

A controller that incorrectly auto-resolves a financial exception is more dangerous than one that sends a safe case to manual review.

### Example report

```text
Exceptions evaluated:      50
Correct classifications:   47
Classification accuracy:   94.0%

Auto-resolve candidates:   18
Correct auto-resolutions:  17
Auto-resolution precision: 94.4%

Human-review cases:        32
Correctly routed:           31
Review recall:             96.9%
```

Do not invent these numbers. The script must calculate them.

---

# 15. PHASE 11 — FAILURE-MODE TESTING

Create explicit tests for:

## Case A — Tool failure

```text
get_settlement()
→ database error
```

Expected:

```text
investigation failure
→ safe fallback or manual review
```

---

## Case B — Missing evidence

```text
bank record missing
```

Expected:

```text
insufficient evidence
→ manual review
```

---

## Case C — Invalid LLM JSON

Expected:

```text
schema validation failure
→ retry/fallback
```

---

## Case D — Hallucinated fee

The model claims:

```text
₹50 standard fee
```

but fee rules do not support it.

Expected:

```text
evidence mismatch
→ cannot auto-resolve
```

---

## Case E — High-value discrepancy

```text
₹82,000 delta
AI confidence = 0.99
```

Expected:

```text
HIGH RISK
→ MANUAL REVIEW
```

---

## Case F — Repeated tool call

Expected:

```text
tool budget stops loop
```

---

## Case G — Groq authentication failure

Expected:

```text
provider failure
→ fallback/manual review
```

and the system must identify the provider failure honestly.

---

# 16. PHASE 12 — API CONTRACTS

Once backend semantics are correct, review every API.

Required core flow:

```text
POST /api/reconciliation/run

GET /api/reconciliation/dashboard

GET /api/exceptions

GET /api/exceptions/{id}

POST /api/exceptions/{id}/investigate

POST /api/exceptions/{id}/resolve

GET /api/audit
```

Consider adding a dedicated transition endpoint only if the existing API becomes semantically confusing.

The API should expose enough information for the frontend to display:

```text
status
exception type
severity
investigation
provider
confidence
evidence
risk
policy decision
resolution
tool calls
```

Do not expose secrets.

---

# 17. PHASE 13 — SYNCHRONOUS VS BACKGROUND EXECUTION

Do NOT add Redis/Celery/etc. immediately.

First measure the real latency.

Test:

```text
50 records
100 records
500 records
1000 records
```

Record:

```text
total batch time
average investigation time
LLM calls
tool calls
```

Only introduce a background worker if the synchronous request becomes demonstrably unsuitable.

For the hackathon, a simple controlled implementation is preferable to unnecessary infrastructure.

---

# 18. PHASE 14 — CSV UPLOAD

Only after the demo data flow is stable.

Current request fields:

```text
orders_csv
settlements_csv
bank_csv
```

are currently ignored.

### Implement:

```text
Upload
 ↓
Validate
 ↓
Normalize
 ↓
Reconcile
 ↓
Investigate
 ↓
Policy
 ↓
Audit
```

Validation should include:

- required columns
- amount parsing
- date parsing
- duplicate identifiers
- missing identifiers
- unsupported formats

### Important

Keep Demo Mode fully functional.

Upload must be an additional path, not a replacement for the controlled demo.

---

# 19. PHASE 15 — GUI INTEGRATION

Only after backend behaviour is correct.

The current GUI should become a truthful visualization layer.

Dashboard must show:

```text
Total records
Matched
Exceptions
Match rate
Amount reconciled
```

and these must come from the same authoritative backend values.

Exception drawer must show:

```text
AI Investigation
Provider
Model
Confidence
Root cause
Evidence
Tool calls
Risk
Resolution policy
Current status
```

---

## GUI-specific integration requirements

### Tool calls

Show:

```text
✓ get_transaction()
✓ get_settlement()
✓ get_fee_rules()
```

and optionally:

```text
◌ running...
```

if live progress is later implemented.

---

### Risk policy

Show:

```text
MODEL CONFIDENCE
94%

POLICY RISK
Low

DECISION
Eligible for auto-resolution
```

or:

```text
MODEL CONFIDENCE
71%

POLICY RISK
High

DECISION
Human review required
```

Remember:

**Model confidence ≠ policy decision.**

---

### Manual review

The UI must distinguish:

```text
OPEN
MANUAL REVIEW
AUTO-RESOLVED
RESOLVED
```

---

# 20. PHASE 16 — PERFORMANCE TESTING

Run controlled batches.

Minimum:

```text
50
100
500
1000
```

Record:

```text
batch size
processing time
number of exceptions
number of AI investigations
number of tools calls
auto-resolved count
manual-review count
```

Calculate:

```text
records/sec
average investigation latency
```

Do not claim throughput that was not measured.

---

# 21. PHASE 17 — FINAL HACKATHON DEMO DATASET

Create one deterministic demo seed.

Example concept:

```text
demo seed
=
stable known anomaly distribution
```

The demo should always generate the same story.

For example:

```text
100 records

known clean transactions
amount mismatches
missing settlements
duplicates
date mismatches
partial settlements
unknown transactions
```

The exact metrics must come from the actual run.

### Why

You do not want your recorded pitch to change every time the demo is run.

---

# 22. PHASE 18 — FINAL DEMO SCENARIO

The complete five-minute flow should eventually be:

```text
LANDING
  ↓
Try Demo
  ↓
100-record batch
  ↓
Dashboard
  ↓
Show match rate
  ↓
Show exceptions
  ↓
Open amount mismatch
  ↓
AI investigation
  ↓
Watch tool calls
  ↓
Evidence appears
  ↓
Root cause
  ↓
Policy evaluates risk
  ↓
Auto-resolve or manual-review decision
  ↓
Audit Trail
  ↓
Show exact sequence of events
  ↓
Show controller evaluation metrics
```

The demo should communicate one story:

> **LedgerLens doesn't ask an LLM to reconcile money. It uses deterministic reconciliation to find exceptions, an AI agent to investigate them, a policy engine to control resolution risk, and an audit trail to record every decision.**

---

# 23. PHASE 19 — FINAL SECURITY CHECK

Before submission:

### Secrets

- [ ] No API keys committed.
- [ ] `.env` excluded by `.gitignore`.
- [ ] `.env.example` contains placeholders only.

### AI safety

- [ ] Agent has no unrestricted SQL tool.
- [ ] Agent has no direct destructive DB tool.
- [ ] Write actions happen through deterministic application logic.
- [ ] High-risk cases require review.

### Data integrity

- [ ] Financial amounts remain deterministic.
- [ ] Ground truth remains separate from production decision logic.
- [ ] Audit records cannot be silently bypassed.

---

# 24. PHASE 20 — FINAL README / ARCHITECTURE EVIDENCE

Update README only after implementation stabilizes.

README should clearly explain:

## What LedgerLens is

```text
AI Finance Controller
```

## Why deterministic first

```text
financial correctness
```

## AI role

```text
exception investigation
```

## Policy role

```text
risk-controlled resolution
```

## Evaluation

```text
ground truth
+
precision
+
recall
+
F1
+
auto-resolution precision
```

## Architecture

```text
data
→ reconciliation
→ AI investigation
→ policy
→ resolution
→ audit
```

Do not claim features that are not implemented.

---

# 25. PHASE 21 — FINAL FULL-SYSTEM TEST

Run from clean startup.

Test exactly:

```text
1. Start backend
2. Start frontend
3. Try Demo
4. Run 100-record batch
5. Dashboard loads
6. Exceptions are accurate
7. Open exception
8. Investigate
9. Groq runs
10. Tools execute
11. Structured output validates
12. Policy evaluates
13. Auto-resolve or manual review occurs
14. Audit records everything
15. Dashboard refreshes accurately
16. Transactions page works
17. Exceptions page works
18. Audit page works
19. Theme switching still works
20. Sidebar still works
```

No UI redesign should be performed during this phase unless a real functional integration bug is discovered.

---

# 26. FINAL ACCEPTANCE CRITERIA

LedgerLens is considered **hackathon-ready** only when all of the following are true.

## Deterministic Engine

- [ ] 50+ records process successfully.
- [ ] Exact matching works.
- [ ] Fuzzy matching works.
- [ ] Duplicate detection works.
- [ ] Missing settlement detection works.
- [ ] Missing bank detection works.
- [ ] Amount mismatch detection works.
- [ ] Date mismatch detection works.
- [ ] Partial settlement detection works.
- [ ] Unknown transaction detection works.
- [ ] Match metrics are reproducible.

## AI Investigator

- [ ] Real Groq path works.
- [ ] Tool calling works.
- [ ] Multiple tools can be used.
- [ ] Tool calls are bounded.
- [ ] Tool results are deterministic.
- [ ] Structured output is Pydantic-validated.
- [ ] Invalid model output is handled safely.
- [ ] Groq failure is distinguishable from fallback.
- [ ] Evidence is stored.
- [ ] Provider/model metadata is stored.

## Controller Policy

- [ ] LLM cannot override risk.
- [ ] Risk policy is deterministic.
- [ ] Auto-resolution requires explicit eligibility.
- [ ] High-risk cases cannot auto-resolve.
- [ ] Monetary thresholds are enforced.
- [ ] Policy decision is auditable.

## Resolution Workflow

- [ ] Auto-resolve works.
- [ ] Manual review works.
- [ ] Flag for review does not resolve the exception.
- [ ] Human resolution works.
- [ ] State transitions are explicit.

## Audit

- [ ] Investigation starts are logged.
- [ ] Tool calls are recorded.
- [ ] Investigation completion is logged.
- [ ] Policy decision is logged.
- [ ] Resolution is logged.
- [ ] Audit entries are readable.

## Evaluation

- [ ] Ground truth is machine-read.
- [ ] Engine precision/recall/F1 are computed.
- [ ] AI classification metrics are computed.
- [ ] Auto-resolution precision is computed.
- [ ] Human-review recall is computed.
- [ ] Failure-mode tests exist.

## Product

- [ ] Demo Mode works.
- [ ] Dashboard values are internally consistent.
- [ ] Exceptions page works.
- [ ] Transactions page works.
- [ ] Audit page works.
- [ ] Existing GUI remains functional.
- [ ] No major regression introduced.

---

# 27. RECOMMENDED EXECUTION ORDER

The coding AI must execute in this order:

```text
STEP 0.1
Clean baseline
    ↓
STEP 1.1
Unify result semantics
    ↓
STEP 1.2
Exception lifecycle
    ↓
STEP 1.3
Result → exception linkage
    ↓
STEP 1.4
Duplicate detection
    ↓
STEP 1.5
Missing bank detection
    ↓
STEP 1.6
Match-type semantics
    ↓
STEP 1.7
Centralize thresholds
    ↓
STEP 2.1
Dedicated controller policy
    ↓
STEP 2.2
Deterministic risk
    ↓
STEP 2.3
Auto-resolution allowlist
    ↓
STEP 2.4
Deterministic resolver
    ↓
STEP 3.1
Pydantic investigation result
    ↓
STEP 3.2
Remove LLM risk authority
    ↓
STEP 3.3
Evidence context packet
    ↓
STEP 4.1
Harden existing tools
    ↓
STEP 4.2
Related transactions
    ↓
STEP 4.3
Merchant profile
    ↓
STEP 5.1
Agent states
    ↓
STEP 5.2
Tool loop guardrails
    ↓
STEP 5.3
Tool metadata
    ↓
STEP 6.1
Configure Groq
    ↓
STEP 6.2
One real tool call
    ↓
STEP 6.3
Multi-tool investigation
    ↓
STEP 7.1
Retry/rate-limit handling
    ↓
STEP 7.2
Explicit fallback
    ↓
STEP 8.1
Agent audit lifecycle
    ↓
STEP 8.2
Investigation persistence
    ↓
STEP 9.1
Manual review workflow
    ↓
STEP 9.2
Fix Flag for Review
    ↓
STEP 10.x
Ground-truth evaluation
    ↓
STEP 11.x
Failure testing
    ↓
STEP 12
API contract verification
    ↓
STEP 13
Latency/performance decision
    ↓
STEP 14
CSV upload
    ↓
STEP 15
GUI integration
    ↓
STEP 16
Performance testing
    ↓
STEP 17
Stable demo dataset
    ↓
STEP 18
Final demo flow
    ↓
STEP 19
Security review
    ↓
STEP 20
README/architecture evidence
    ↓
STEP 21
Full-system test
    ↓
HACKATHON READY
```

---

# 28. WHAT NOT TO BUILD

Unless an actual measured requirement appears, do not add:

```text
❌ RAG
❌ Vector database
❌ LangChain
❌ Multi-agent architecture
❌ Autonomous SQL
❌ Fine-tuning
❌ Persistent conversational memory
❌ Kafka
❌ Redis
❌ Celery
❌ Complex distributed workers
❌ Ten financial workflows
❌ Full accounting platform
```

The project is already sufficiently sophisticated.

The strength is the separation:

```text
deterministic financial correctness
+
AI investigation
+
deterministic risk policy
+
auditable resolution
```

---

# 29. FINAL ARCHITECTURE

The final system should look like:

```text
                           LEDGERLENS
                               │
                  ┌────────────┴────────────┐
                  │                         │
             INPUT LAYER              EVALUATION
                  │                         │
        ┌─────────┴─────────┐        Ground Truth
        │                   │             │
     Demo Data           CSV Upload       │
        │                   │             │
        └─────────┬─────────┘             │
                  ↓                       │
             Normalization                │
                  ↓                       │
          Reconciliation Engine           │
          ┌───────┴────────┐              │
          │                │              │
       MATCHED         EXCEPTION          │
          │                │              │
          │          AI INVESTIGATOR      │
          │          ┌─────────────┐      │
          │          │ Groq LLM    │      │
          │          │ Tool Calls  │      │
          │          └──────┬──────┘      │
          │                 │             │
          │             Evidence          │
          │                 │             │
          │          Pydantic Validation  │
          │                 │             │
          └────────────┬────┴──────────────┘
                       ↓
                 POLICY ENGINE
                       ↓
              ┌────────┴────────┐
              ↓                 ↓
         AUTO-RESOLVE      MANUAL REVIEW
              └────────┬────────┘
                       ↓
                    AUDIT
                       ↓
                   DASHBOARD
                       │
                       └──────────────→ Metrics
```

---

# 30. FINAL DEFINITION OF "HACKATHON READY"

LedgerLens is ready to submit when a judge can observe this complete chain:

```text
100 financial records
        ↓
deterministic reconciliation
        ↓
exceptions found
        ↓
AI investigates one
        ↓
AI calls real tools
        ↓
evidence is shown
        ↓
structured result is validated
        ↓
deterministic policy evaluates risk
        ↓
safe case auto-resolves
        ↓
unsafe case goes to human review
        ↓
every step appears in audit trail
        ↓
evaluation metrics prove performance
```

The final pitch should not be:

> "We built an AI that reconciles payments."

It should be:

> **"LedgerLens is an AI Finance Controller that uses deterministic reconciliation to detect exceptions, an agentic AI investigator to gather evidence and identify root causes, and a deterministic risk policy to decide whether an exception can be safely auto-resolved or requires human review — with every decision auditable and measurable against ground truth."**

That is the implementation target for this document.

---

# 31. EXECUTION RULE FOR THE CODING AI

**Start with STEP 0.1 only.**

After completing Step 0.1:

1. Stop.
2. Do not start Step 1.1 automatically.
3. Produce the mandatory completion report from Section 3.
4. Clearly state PASS / PASS WITH NOTES / FAIL.
5. Wait for the next instruction unless continuous execution was explicitly requested.
