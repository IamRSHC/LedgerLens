"""
AI Investigator (Milestone B + C).

Contract (Milestone B):
  INVESTIGATOR ONLY — never mutates DB, never calls resolver, never decides
  risk or auto-resolution. Emits a validated `InvestigationResult`.

Milestone C additions:
  Step 5.1 — Explicit agent-phase names (see PHASES) for testable execution:
             START → UNDERSTAND_EXCEPTION → INVESTIGATE → TOOL_CALL → OBSERVE
             → (NEED_MORE_EVIDENCE? loops) → VALIDATE_RESULT → RETURN
  Step 5.2 — Per-run tool budgets:
                MAX_ROUNDS               (LLM round cap, was already present)
                MAX_TOTAL_TOOL_CALLS     (per-investigation ceiling)
                MAX_IDENTICAL_TOOL_CALLS (max calls with the same tool+args)
             Hitting any budget produces a "blocked" tool response so the
             model can conclude with what it has; exhaustion falls back to
             a schema-valid stub (`fallback_reason="tool_budget_exhausted"`
             or `"max_rounds_reached"`).
  Step 5.3 — Every tool call records structured metadata:
                {tool, arguments, status, result_summary, started_at, duration_ms}
             Persisted on InvestigationResult.tool_calls; the raw tool result
             is sent to the model but NOT stored (no giant DB payloads).
"""
from __future__ import annotations
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.agent.tools import TOOL_DEFINITIONS, TOOL_REGISTRY
from app.schemas.investigation import InvestigationResult, Evidence


# ── Model configuration ───────────────────────────────────────────────────────
MODEL      = "llama-3.3-70b-versatile"
MAX_TOKENS = 1000


# ── Step 5.1: agent-phase names (conceptual state flow) ──────────────────────
PHASE_START               = "START"
PHASE_UNDERSTAND          = "UNDERSTAND_EXCEPTION"
PHASE_INVESTIGATE         = "INVESTIGATE"
PHASE_TOOL_CALL           = "TOOL_CALL"
PHASE_OBSERVE             = "OBSERVE"
PHASE_VALIDATE_RESULT     = "VALIDATE_RESULT"
PHASE_RETURN              = "RETURN"

PHASES: Tuple[str, ...] = (
    PHASE_START, PHASE_UNDERSTAND, PHASE_INVESTIGATE,
    PHASE_TOOL_CALL, PHASE_OBSERVE,
    PHASE_VALIDATE_RESULT, PHASE_RETURN,
)


# ── Step 5.2: loop guardrails ────────────────────────────────────────────────
MAX_ROUNDS               = 5   # LLM turns per investigation
MAX_TOTAL_TOOL_CALLS     = 8   # per-investigation cap across all tools
MAX_IDENTICAL_TOOL_CALLS = 2   # max invocations with the SAME tool+arguments


# ── System prompt (Step 3.3 + tools introduced by Step 4.2/4.3) ──────────────
SYSTEM_PROMPT = """You are LedgerLens AI Investigator — a financial reconciliation agent.

YOUR JOB
Investigate a single financial exception detected by the deterministic
reconciliation engine. Gather evidence with the provided tools. Explain
what happened. Recommend an action.

YOU DO NOT DECIDE:
  - risk level
  - whether the exception may be auto-resolved
Those are decided by a deterministic backend policy engine AFTER you finish.
Any `risk_level` value you emit is observability only; the backend will
ignore it for policy purposes.

RULES
  1. Use tools to fetch actual data before making claims. Do NOT invent
     amounts, dates, UTRs, fee rules, or merchant profiles.
  2. A tool returning {found: false, ...} is EVIDENCE OF ABSENCE only
     within that tool's scope — do not extrapolate.
  3. Evidence entries must be grounded in tool output. Never fabricate.
  4. Confidence must reflect evidence quality. Do not claim >= 0.85 without
     concrete tool-derived evidence supporting the root cause.
  5. Do NOT output chain-of-thought. `reasoning_summary` is at most one short
     sentence — no step-by-step reasoning.
  6. `recommended_action` is advice for a human reviewer. It is not a command.
  7. Tool budgets are enforced. If the runtime returns a "blocked" tool
     response, do NOT retry — conclude with the evidence gathered so far.

OUTPUT FORMAT
Return ONE JSON object matching exactly this schema (no markdown fences,
no preamble, no trailing prose):

{
  "root_cause": "one short phrase",
  "classification": "settlement_fee | timing_difference | data_entry_error | potential_fraud | duplicate | partial_payment | missing_bank_record | missing_settlement | unknown",
  "confidence": 0.0,
  "explanation": "2-3 sentences citing tool-derived numbers",
  "recommended_action": "one clear action for a human reviewer",
  "evidence": [
    {"source": "settlement", "field": "gross_amount", "value": 12345.67, "description": "from get_settlement()"}
  ],
  "reasoning_summary": "optional single-sentence summary",
  "risk_level": "low | medium | high"
}

Evidence entries MUST use keys {source, field, value, description}. Do not
use {label, ...}.
"""


# ── Context packet (Step 3.3, extended with Milestone-C tools) ───────────────
def _context_packet(exception: Dict[str, Any]) -> str:
    def _fmt(v: Any) -> str:
        return "N/A" if v is None else str(v)

    lines = [
        "EXCEPTION",
        "---------",
        f"exception_id:     {_fmt(exception.get('exception_id'))}",
        f"type:             {_fmt(exception.get('exception_type'))}",
        f"severity:         {_fmt(exception.get('severity'))}",
        f"order_id:         {_fmt(exception.get('order_id'))}",
        f"settlement_id:    {_fmt(exception.get('settlement_id'))}",
        f"bank_txn_id:      {_fmt(exception.get('bank_txn_id'))}",
        f"amount_delta:     {_fmt(exception.get('amount_delta'))}",
        f"order_amount:     {_fmt(exception.get('order_amount'))}",
        f"settlement_amount:{_fmt(exception.get('settlement_amount'))}",
        f"match_type:       {_fmt(exception.get('match_type'))}",
        f"match_score:      {_fmt(exception.get('match_score'))}",
        f"date_delta_days:  {_fmt(exception.get('date_delta_days'))}",
        "",
        "AVAILABLE EVIDENCE SOURCES (call the tool to fetch)",
        "---------------------------------------------------",
        "  get_transaction(order_id)                  full order record",
        "  get_settlement(settlement_id)              settlement (gross/fee/net/UTR/settled_at)",
        "  get_bank_record(utr)                       bank transaction credit for a UTR",
        "  get_fee_rules()                            Razorpay fee schedule + settlement lag",
        "  get_previous_exceptions(order_id)          prior exceptions for this order",
        "  search_related_transactions(...filters)    bounded search over prior exceptions "
        "(merchant_id, order_id, utr, amount_min/max, date_from/to, exception_type, limit)",
        "  get_merchant_profile(merchant_id)          merchant fee_rate, settlement_lag_days, risk_tier",
        "",
        f"Runtime budgets: MAX_ROUNDS={MAX_ROUNDS}, MAX_TOTAL_TOOL_CALLS={MAX_TOTAL_TOOL_CALLS}, "
        f"MAX_IDENTICAL_TOOL_CALLS={MAX_IDENTICAL_TOOL_CALLS}.",
        "Fetch every piece of evidence you cite. Do not invent facts.",
    ]
    return "\n".join(lines)


# ── Response parsing (Step 3.1) ───────────────────────────────────────────────
def _extract_json_object(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl >= 0:
            text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    if text.lower().startswith("json"):
        text = text[4:].lstrip()
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start >= 0 and end > start:
        return text[start:end]
    return text


def _parse_investigation(raw: str) -> InvestigationResult:
    payload = _extract_json_object(raw)
    data    = json.loads(payload)
    return InvestigationResult.model_validate(data)


# ── Step 5.3: tool-call metadata helpers ─────────────────────────────────────
_SUMMARY_MAX = 160


def _summarize(result: Any) -> str:
    if not isinstance(result, dict):
        return str(result)[:_SUMMARY_MAX]
    if result.get("found") is False:
        code = result.get("error", "unknown_error")
        return f"not_found: {code}"[:_SUMMARY_MAX]
    if result.get("found") is True:
        # Prefer a concise key list rather than dumping large payloads.
        drop = {"found", "matches", "exceptions"}
        pairs = [(k, v) for k, v in result.items() if k not in drop][:4]
        pretty = ", ".join(f"{k}={v}" for k, v in pairs)
        if "count" in result:
            pretty = f"count={result['count']}" + (f"; {pretty}" if pretty else "")
        return (pretty or "success")[:_SUMMARY_MAX]
    return str(result)[:_SUMMARY_MAX]


def _status_for(result: Any) -> str:
    if isinstance(result, dict):
        if result.get("found") is False:
            return "not_found"
        if result.get("found") is True:
            return "success"
    return "success"


def _args_key(args: Dict[str, Any]) -> str:
    """Canonical string form of an argument dict, for identical-call detection."""
    try:
        return json.dumps(args, sort_keys=True, default=str)
    except Exception:
        return repr(sorted(args.items()))


# ── Fallback stub (Step 3.1) — schema-valid ──────────────────────────────────
_STUB_TABLE = {
    "amount_mismatch":      ("Settlement fee deduction",         "settlement_fee",       0.88),
    "missing_settlement":   ("Settlement not yet processed",     "missing_settlement",   0.72),
    "duplicate":            ("Duplicate settlement detected",    "duplicate",            0.95),
    "date_mismatch":        ("Settlement timing delay",          "timing_difference",    0.80),
    "partial_settlement":   ("Partial payment processed",        "partial_payment",      0.85),
    "unknown_transaction":  ("No matching order found",          "unknown",              0.60),
    "missing_bank_record":  ("Bank record not observed",         "missing_bank_record",  0.65),
    "low_confidence_match": ("Low-confidence match",             "unknown",              0.60),
    "unclassified":         ("Unclassified engine exception",    "unknown",              0.55),
}


def _stub_investigation(
    exception: Dict[str, Any],
    *,
    fallback_reason: Optional[str] = None,
) -> InvestigationResult:
    exc_type = exception.get("exception_type", "unknown")
    delta    = abs(exception.get("amount_delta") or 0)
    root_cause, classification, confidence = _STUB_TABLE.get(
        exc_type, ("Unknown issue", "unknown", 0.50)
    )
    tail = f" (fallback: {fallback_reason})" if fallback_reason else ""
    return InvestigationResult(
        root_cause=root_cause,
        classification=classification,
        confidence=confidence,
        explanation=(
            f"Rule-based stub for {exc_type}, absolute delta ~₹{delta:.2f}. "
            f"Fallback used because live investigator was unavailable.{tail}"
        ),
        recommended_action="Manual review — confirm with finance team.",
        evidence=[
            Evidence(source="exception", field="exception_type", value=exc_type,
                     description="Deterministic classification from reconciliation engine"),
            Evidence(source="exception", field="amount_delta",   value=f"₹{delta:.2f}",
                     description="Absolute order↔settlement gross discrepancy"),
        ],
        risk_level=None,
        provider="fallback",
        tool_calls=[],
    )


# ── Bounded tool dispatcher (Step 5.2 + 5.3) ─────────────────────────────────
def _dispatch_tool(
    db: Session, name: str, args: Dict[str, Any],
    identical_counts: Dict[str, int], total_tool_calls_ref: List[int],
) -> Tuple[Any, Dict[str, Any]]:
    """
    Invoke one tool with all guards + metadata. Returns (result_for_model,
    metadata_for_log).

    - Increments the total-call counter (passed as a single-element list so
      callers can share the mutation).
    - Enforces MAX_TOTAL_TOOL_CALLS and MAX_IDENTICAL_TOOL_CALLS.
    - Builds a Step-5.3 metadata dict for every call, including blocked ones.
    """
    total_tool_calls_ref[0] += 1
    total_now = total_tool_calls_ref[0]

    key = f"{name}::{_args_key(args)}"
    identical_counts[key] = identical_counts.get(key, 0) + 1
    same_now = identical_counts[key]

    started = datetime.utcnow()
    t0 = time.monotonic()

    # ── Guard: total budget ──────────────────────────────────────────────────
    if total_now > MAX_TOTAL_TOOL_CALLS:
        result = {"found": False, "error": "tool_budget_exceeded",
                  "message": f"MAX_TOTAL_TOOL_CALLS={MAX_TOTAL_TOOL_CALLS} reached; "
                             "produce a final answer with the evidence you have."}
        meta = {"tool": name, "arguments": args, "status": "blocked",
                "result_summary": "blocked: total tool budget exhausted",
                "started_at": started.isoformat(), "duration_ms": 0}
        return result, meta

    # ── Guard: identical-call budget ─────────────────────────────────────────
    if same_now > MAX_IDENTICAL_TOOL_CALLS:
        result = {"found": False, "error": "identical_tool_call_limit",
                  "tool": name, "arguments": args,
                  "message": f"Same tool+arguments already invoked {MAX_IDENTICAL_TOOL_CALLS} times; "
                             "do not repeat — use a different tool or conclude."}
        meta = {"tool": name, "arguments": args, "status": "blocked",
                "result_summary": f"blocked: identical call #{same_now}",
                "started_at": started.isoformat(), "duration_ms": 0}
        return result, meta

    # ── Dispatch ─────────────────────────────────────────────────────────────
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        result = {"found": False, "error": "unknown_tool", "tool": name}
        duration_ms = int((time.monotonic() - t0) * 1000)
        meta = {"tool": name, "arguments": args, "status": "error",
                "result_summary": f"unknown_tool: {name}",
                "started_at": started.isoformat(), "duration_ms": duration_ms}
        return result, meta

    needs_db = "db" in fn.__code__.co_varnames
    try:
        result = fn(db, **args) if needs_db else fn(**args)
        status = _status_for(result)
    except TypeError as e:
        result = {"found": False, "error": "invalid_argument", "detail": str(e)[:120]}
        status = "error"
    except Exception as e:
        result = {"found": False, "error": "tool_execution_failed", "detail": str(e)[:120]}
        status = "error"

    duration_ms = int((time.monotonic() - t0) * 1000)
    meta = {
        "tool": name, "arguments": args, "status": status,
        "result_summary": _summarize(result),
        "started_at": started.isoformat(), "duration_ms": duration_ms,
    }
    return result, meta


# ── Live Groq loop ───────────────────────────────────────────────────────────
def _run_agent(client, exception: Dict[str, Any], db: Session) -> InvestigationResult:
    """
    Bounded agent loop, phase-labelled per PHASES.
    """
    # ── PHASE_START ──────────────────────────────────────────────────────────
    # ── PHASE_UNDERSTAND ────────────────────────────────────────────────────
    messages: List[Dict[str, Any]] = [
        {"role": "user", "content": _context_packet(exception)},
    ]
    tool_calls_log:    List[Dict[str, Any]] = []
    identical_counts:  Dict[str, int]       = {}
    total_tool_calls_ref: List[int]         = [0]

    # ── PHASE_INVESTIGATE (rounds loop) ──────────────────────────────────────
    for _round in range(MAX_ROUNDS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            max_tokens=MAX_TOKENS,
        )
        msg = response.choices[0].message

        if msg.tool_calls:
            # ── PHASE_TOOL_CALL / PHASE_OBSERVE ─────────────────────────────
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name,
                                  "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result, meta = _dispatch_tool(
                    db, name, args, identical_counts, total_tool_calls_ref
                )
                tool_calls_log.append(meta)
                # Full result goes back to the model; metadata-only is what we persist.
                messages.append({"role": "tool",
                                 "content": json.dumps(result, default=str),
                                 "tool_call_id": tc.id})
            continue

        # ── PHASE_VALIDATE_RESULT ────────────────────────────────────────────
        raw = msg.content or ""
        try:
            result = _parse_investigation(raw)
        except Exception as ve:
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": (
                    f"Your previous response failed schema validation ({ve!s}). "
                    "Re-emit ONE JSON object matching the schema exactly. "
                    "Every evidence entry must use keys {source, field, value, description}. "
                    "Confidence must be a number between 0 and 1. "
                    "Classification must be one of the allowed values."
                ),
            })
            continue

        # ── PHASE_RETURN ─────────────────────────────────────────────────────
        result.provider = "groq"
        result.tool_calls = tool_calls_log
        return result

    # Rounds exhausted. If the tool budget ran out we say so; otherwise it's max rounds.
    reason = ("tool_budget_exhausted"
              if total_tool_calls_ref[0] > MAX_TOTAL_TOOL_CALLS
              else "max_rounds_reached")
    stub = _stub_investigation(exception, fallback_reason=reason)
    # Preserve the tool-call metadata we collected, so the audit trail keeps
    # everything we tried before giving up.
    stub.tool_calls = tool_calls_log
    return stub


# ── Public API ────────────────────────────────────────────────────────────────
def investigate(exception: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    Investigate an exception. Returns a validated InvestigationResult as a
    dict (model_dump). Never raises — every failure route funnels to a
    schema-valid fallback stub tagged `provider="fallback"`.
    """
    if not settings.groq_api_key:
        return _stub_investigation(exception, fallback_reason="no_api_key").model_dump()

    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        result = _run_agent(client, exception, db)
    except Exception as e:
        result = _stub_investigation(
            exception, fallback_reason=f"provider_error:{e!s}"[:200]
        )

    return result.model_dump()
