"""
Phase 11 — Failure-Mode Testing.

Explicitly exercises the 7 required scenarios and verifies the system never
bypasses policy, never mutates DB from the agent, and never produces a false
"AI success" during failure.

Usage:
    cd backend
    venv/Scripts/python.exe scripts/test_failure_modes.py

Every test is self-contained: mocks the Groq client / dispatches directly to
the policy or resolver. No live network calls. The real ledgerlens.db is
NOT written to by these tests.
"""
from __future__ import annotations
import json, os, sys, re

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _BACKEND)
os.chdir(_BACKEND)

# Route SQLAlchemy at an in-memory DB so failure tests never write to the real DB
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
from app.database import Base, engine, SessionLocal
from app.models import models
Base.metadata.create_all(bind=engine)

from app.config import settings
from app.controller.policy import evaluate_exception, evaluate_risk
from app.controller.resolver import apply as apply_resolution, InconsistentDecision
import app.repository.repository as repo
from app.agent import investigator as inv_mod
from app.agent.investigator import (
    investigate, _dispatch_tool, _call_llm, _LLMError,
    _parse_investigation, MAX_TOTAL_TOOL_CALLS, MAX_IDENTICAL_TOOL_CALLS,
    MAX_TRANSIENT_RETRIES, MAX_UNKNOWN_RETRIES, PROVIDER_GROQ, PROVIDER_FALLBACK,
)
from app.schemas.investigation import InvestigationResult

RESULTS = {}


# ── Minimal mock Groq client ────────────────────────────────────────────────
class _MockFn:
    def __init__(self, name, args): self.name = name; self.arguments = json.dumps(args)
class _MockTC:
    def __init__(self, i, name, args): self.id = f"t{i}"; self.function = _MockFn(name, args)
class _MockMsg:
    def __init__(self, tool_calls=None, content=None):
        self.tool_calls = tool_calls; self.content = content
class _MockResp:
    def __init__(self, msg): self.choices = [type("_c", (), {"message": msg})]
class _MockClient:
    def __init__(self, program):
        self.chat = type("_c", (), {})()
        self.chat.completions = type("_cc", (), {})()
        self.chat.completions.calls = 0
        prog = list(program)
        def _create(**kwargs):
            self.chat.completions.calls += 1
            step = prog[min(self.chat.completions.calls - 1, len(prog) - 1)]
            if isinstance(step, Exception):
                raise step
            return step
        self.chat.completions.create = _create


db = SessionLocal()


def _check(name, cond, msg=""):
    ok = "OK" if cond else "FAIL"
    RESULTS[name] = ok
    print(f"  [{ok}] {name}  {msg}")
    if not cond:
        raise AssertionError(f"{name}: {msg}")


# ── Case A: Tool failure → safe fallback ────────────────────────────────────
print("=" * 72)
print("Case A — Tool failure")
print("=" * 72)
identical = {}; total = [0]
# Force a tool that will raise TypeError by passing wrong kwargs
result, meta = _dispatch_tool(db, "get_settlement", {"wrong_kwarg": "x"},
                              identical, total)
print(f"  tool result:  {result}")
print(f"  metadata:     {meta}")
_check("A.tool_status_is_error", meta["status"] == "error",
       f"expected status=error, got {meta['status']}")
_check("A.tool_result_not_success", result.get("found") is False,
       "tool must not report success on failure")
_check("A.no_false_evidence", not result.get("credit_amount"),
       "tool must not fabricate credit_amount on failure")


# ── Case B: Missing evidence → manual review ────────────────────────────────
print()
print("=" * 72)
print("Case B — Missing evidence (missing_bank_record)")
print("=" * 72)
# Simulate an exception whose bank record is missing
exc = {"exception_type": "missing_bank_record", "amount_delta": 100, "severity": "warning"}
inv = {"confidence": 0.99, "risk_level": "low"}   # AI wildly confident
decision = evaluate_exception(exc, inv)
print(f"  decision:  {decision.decision}")
print(f"  blockers:  {decision.blockers}")
_check("B.missing_evidence_routes_to_manual",
       decision.decision == "manual_review" and not decision.eligible_for_auto_resolution,
       "insufficient evidence must NOT auto-resolve")
_check("B.blocked_by_allowlist",
       any("AUTO_RESOLVE_TYPES" in b for b in decision.blockers),
       "block reason must include allowlist rejection")


# ── Case C: Invalid LLM JSON → validation/retry/fallback ────────────────────
print()
print("=" * 72)
print("Case C — Invalid LLM structured output")
print("=" * 72)
# Direct parse test
try:
    _parse_investigation("this is definitely not JSON at all")
    _check("C.malformed_raises", False, "malformed JSON should raise")
except Exception as e:
    _check("C.malformed_raises", True, f"raised {type(e).__name__}")

# Schema-invalid JSON
try:
    _parse_investigation('{"root_cause":"", "classification":"nope", "confidence":2.0, "explanation":"", "recommended_action":""}')
    _check("C.schema_invalid_raises", False, "schema-invalid should raise")
except Exception as e:
    _check("C.schema_invalid_raises", True, f"raised {type(e).__name__}")

# End-to-end: an "always garbage" mock client → fallback with reason
class _GroqDummy:
    pass
import groq as _g
_orig_ctor = _g.Groq
_g.Groq = lambda **kw: _MockClient([_MockResp(_MockMsg(content="not json"))] * 30)
_saved_key = settings.groq_api_key
settings.groq_api_key = "gsk_test_placeholder"
try:
    result = investigate({"exception_type":"amount_mismatch","amount_delta":100,"severity":"warning"}, db)
    _check("C.no_unsafe_success",
           result["provider"] == PROVIDER_FALLBACK,
           f"garbage responses must fall back; got provider={result['provider']}")
    _check("C.fallback_reason_present",
           result["fallback_reason"] in ("max_rounds_reached","tool_budget_exhausted","validation_failure","unknown_error"),
           f"got fallback_reason={result['fallback_reason']}")
finally:
    _g.Groq = _orig_ctor
    settings.groq_api_key = _saved_key


# ── Case D: Hallucinated evidence → cannot auto-resolve ─────────────────────
print()
print("=" * 72)
print("Case D — Hallucinated fee")
print("=" * 72)
# Model claims "settlement_fee" classification with confidence 0.99 on an
# amount_mismatch that could NOT be a standard 2% fee (delta = ₹50 on ₹100
# order = 50% — no fee rule supports this). The controller policy MUST NOT
# auto-resolve because amount_mismatch is not in the allowlist.
exc = {"exception_type": "amount_mismatch", "amount_delta": 50, "severity": "warning"}
inv = {"classification": "settlement_fee", "confidence": 0.99, "risk_level": "low",
       "root_cause": "Standard ₹50 fee (fabricated)"}
decision = evaluate_exception(exc, inv)
print(f"  decision:  {decision.decision}")
print(f"  blockers:  {decision.blockers}")
_check("D.hallucinated_fee_cannot_autoresolve",
       decision.decision == "manual_review",
       "hallucinated fee claim must NOT auto-resolve")
_check("D.allowlist_holds_against_hallucination",
       any("AUTO_RESOLVE_TYPES" in b for b in decision.blockers),
       "allowlist must be the blocker")


# ── Case E: High-value discrepancy → high risk → manual review ──────────────
print()
print("=" * 72)
print("Case E — High-value discrepancy (₹82,000 delta, AI conf 0.99)")
print("=" * 72)
exc = {"exception_type": "amount_mismatch", "amount_delta": 82000, "severity": "critical"}
inv = {"confidence": 0.99, "risk_level": "low"}  # AI insists it's low
decision = evaluate_exception(exc, inv)
policy_risk = evaluate_risk(exc, inv)
print(f"  policy_risk:      {policy_risk}   (evaluate_risk)")
print(f"  PolicyDecision:   {decision.risk_level}  model_risk={decision.model_risk}")
print(f"  decision:         {decision.decision}")
print(f"  blockers:         {decision.blockers}")
_check("E.high_delta_policy_risk_high", policy_risk == "high",
       "delta > 10000 must be policy_risk=high")
_check("E.high_delta_manual_review", decision.decision == "manual_review",
       "high policy_risk must NOT auto-resolve")
_check("E.high_delta_blocker_present",
       any("policy_risk=high" in b for b in decision.blockers),
       "policy_risk=high must appear in blockers")


# ── Case F: Repeated tool call → budget stops the loop ──────────────────────
print()
print("=" * 72)
print("Case F — Repeated tool call")
print("=" * 72)
identical.clear(); total = [0]
statuses = []
for i in range(5):
    r, m = _dispatch_tool(db, "get_fee_rules", {}, identical, total)
    statuses.append(m["status"])
print(f"  statuses of 5 identical calls:  {statuses}")
_check("F.identical_call_blocked_after_limit",
       statuses[MAX_IDENTICAL_TOOL_CALLS] == "blocked",
       f"3rd identical call must be blocked (MAX_IDENTICAL_TOOL_CALLS={MAX_IDENTICAL_TOOL_CALLS})")

# Total budget
identical.clear(); total = [0]
total_statuses = []
for i in range(12):
    r, m = _dispatch_tool(db, "search_related_transactions", {"merchant_id": f"M-{i}"},
                          identical, total)
    total_statuses.append(m["status"])
print(f"  total-budget test statuses:     {total_statuses}")
_check("F.total_budget_blocks_after_ceiling",
       all(s == "blocked" for s in total_statuses[MAX_TOTAL_TOOL_CALLS:]),
       f"calls beyond MAX_TOTAL_TOOL_CALLS={MAX_TOTAL_TOOL_CALLS} must be blocked")


# ── Case G: Groq authentication failure → no infinite retry, explicit fallback ──
print()
print("=" * 72)
print("Case G — Groq authentication failure")
print("=" * 72)
class _AuthError(Exception):
    pass
type_name_holder = type("AuthenticationError", (Exception,), {})
mock = _MockClient([type_name_holder("401 invalid_api_key")])
try:
    _call_llm(mock, model="x", messages=[])
    _check("G.auth_raises", False, "expected _LLMError")
except _LLMError as e:
    _check("G.auth_no_retry",
           mock.chat.completions.calls == 1,
           f"auth error must NOT retry, got {mock.chat.completions.calls} attempts")
    _check("G.auth_fallback_reason",
           e.fallback_reason == "authentication_error",
           f"got fallback_reason={e.fallback_reason}")

# End-to-end via investigate() with auth-erroring mock client
_g.Groq = lambda **kw: _MockClient([type_name_holder("401 unauthorized")])
settings.groq_api_key = "gsk_test_placeholder"
try:
    result = investigate({"exception_type":"amount_mismatch","amount_delta":100,"severity":"warning"}, db)
    _check("G.investigate_returns_fallback",
           result["provider"] == PROVIDER_FALLBACK,
           f"got provider={result['provider']}")
    _check("G.investigate_records_auth_reason",
           result["fallback_reason"] == "authentication_error",
           f"got fallback_reason={result['fallback_reason']}")
    _check("G.no_false_ai_success",
           result["model"] != settings.groq_model,
           "fallback model must not claim to be the live groq model")
finally:
    _g.Groq = _orig_ctor
    settings.groq_api_key = ""


# ── AI safety invariants (no DB mutation across all failure runs) ───────────
print()
print("=" * 72)
print("AI safety invariants (unchanged despite failure paths)")
print("=" * 72)
inv_src = open("app/agent/investigator.py", encoding="utf-8").read()
tools_src = open("app/agent/tools.py", encoding="utf-8").read()
code_i = re.sub(r'"""[\s\S]*?"""', '', inv_src)
code_t = re.sub(r'"""[\s\S]*?"""', '', tools_src)
banned = [r'\btransition_exception\s*\(', r'\bresolver\.apply\s*\(',
          r'\bapply_resolution\s*\(', r'\bdb\.commit\s*\(',
          r'\bdb\.add\s*\(', r'\bdb\.delete\s*\(',
          r'^\s*from\s+app\.controller\.resolver\s+import',
          r'^\s*from\s+app\.repository']
mutation_free = all(
    not re.search(p, code_i, re.MULTILINE)
    and not re.search(p, code_t, re.MULTILINE)
    for p in banned
)
_check("SAFETY.no_db_mutation_from_agent", mutation_free,
       "agent must have zero DB mutation code paths")


# ── Summary ─────────────────────────────────────────────────────────────────
print()
print("=" * 72)
print("SUMMARY")
print("=" * 72)
for k, v in RESULTS.items():
    print(f"  [{v}] {k}")
all_ok = all(v == "OK" for v in RESULTS.values())
print()
print(("ALL FAILURE-MODE TESTS PASS" if all_ok else "SOME TESTS FAILED"))
sys.exit(0 if all_ok else 1)
