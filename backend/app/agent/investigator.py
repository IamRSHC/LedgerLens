"""
AI Investigator — Day 3 implementation.
Uses Groq (Llama 3.3 70B) with tool calling to investigate exceptions.
"""
import json
from typing import Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.agent.tools import TOOL_DEFINITIONS, TOOL_REGISTRY
from app.engine.classifier import risk_level, should_auto_resolve


SYSTEM_PROMPT = """You are LedgerLens AI Investigator — a financial reconciliation agent.

Your job: investigate a financial exception detected by the reconciliation engine.
Use the provided tools to gather evidence, then return a structured JSON analysis.

Rules:
1. Use tools to fetch actual data — never guess amounts or dates.
2. Be specific: cite actual numbers in your explanation.
3. Confidence must reflect evidence quality — don't claim 0.95 without strong evidence.
4. Risk level: "low" = routine fee/timing; "medium" = unusual but explainable; "high" = unexplained large gap or fraud risk.

Return ONLY this JSON (no markdown, no preamble):
{
  "root_cause": "one short phrase",
  "classification": "settlement_fee | timing_difference | data_entry_error | potential_fraud | duplicate | partial_payment | unknown",
  "confidence": 0.00,
  "explanation": "2-3 sentences citing evidence",
  "recommended_action": "one clear action",
  "risk_level": "low | medium | high",
  "evidence": [{"label": "...", "value": "..."}]
}"""


def investigate(exception: dict, db: Session) -> dict:
    """
    Investigate an exception using the Groq LLM with tool calling.
    Returns a structured investigation result dict.
    """
    if not settings.groq_api_key:
        return _stub_investigation(exception)

    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        return _run_agent(client, exception, db)
    except Exception as e:
        return _stub_investigation(exception, error=str(e))


def _run_agent(client, exception: dict, db: Session) -> dict:
    user_msg = f"""Exception to investigate:
Order ID:          {exception.get('order_id', 'N/A')}
Settlement ID:     {exception.get('settlement_id', 'N/A')}
Exception Type:    {exception['exception_type']}
Severity:          {exception['severity']}
Amount Delta:      ₹{exception.get('amount_delta', 'N/A')}
Order Amount:      ₹{exception.get('order_amount', 'N/A')}
Settlement Amount: ₹{exception.get('settlement_amount', 'N/A')}

Use the tools to investigate and return your JSON analysis."""

    messages = [{"role": "user", "content": user_msg}]
    tool_calls_log = []
    max_rounds = 5

    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            max_tokens=1000,
        )
        msg = response.choices[0].message

        if msg.tool_calls:
            messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]})
            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)
                fn   = TOOL_REGISTRY.get(name)
                if fn:
                    needs_db = "db" in fn.__code__.co_varnames
                    result   = fn(db, **args) if needs_db else fn(**args)
                else:
                    result = {"error": f"Unknown tool: {name}"}
                tool_calls_log.append({"tool": name, "args": args, "result": result})
                messages.append({"role": "tool", "content": json.dumps(result), "tool_call_id": tc.id})
        else:
            raw = (msg.content or "{}").strip()
            try:
                analysis = json.loads(raw)
            except json.JSONDecodeError:
                start = raw.find("{"); end = raw.rfind("}") + 1
                analysis = json.loads(raw[start:end]) if start >= 0 else {}

            analysis["tool_calls"] = json.dumps(tool_calls_log)
            analysis["risk_level"] = analysis.get("risk_level", risk_level(exception, analysis))
            analysis["auto_resolved"] = should_auto_resolve(exception, analysis)
            return analysis

    return _stub_investigation(exception, error="Max rounds reached")


def _stub_investigation(exception: dict, error: Optional[str] = None) -> dict:
    """Fallback when Groq is unavailable — rule-based stub."""
    exc_type = exception.get("exception_type", "unknown")
    delta    = abs(exception.get("amount_delta") or 0)

    stubs = {
        "amount_mismatch":      ("Settlement fee deduction",   "settlement_fee",      0.88, "medium"),
        "missing_settlement":   ("Settlement not yet processed","pending_settlement",  0.72, "warning"),
        "duplicate":            ("Duplicate settlement detected","duplicate",          0.95, "high"),
        "date_mismatch":        ("Settlement timing delay",     "timing_difference",   0.80, "low"),
        "partial_settlement":   ("Partial payment processed",   "partial_payment",     0.85, "medium"),
        "unknown_transaction":  ("No matching order found",     "unknown",             0.60, "high"),
    }
    root_cause, classification, confidence, rl = stubs.get(exc_type, ("Unknown issue","unknown",0.50,"high"))

    return {
        "root_cause":         root_cause,
        "classification":     classification,
        "confidence":         confidence,
        "explanation":        f"Rule-based stub: {exc_type} detected with delta ₹{delta:.2f}." +
                              (f" AI error: {error}" if error else " Enable GROQ_API_KEY for full investigation."),
        "recommended_action": "Review manually and confirm with finance team.",
        "risk_level":         rl,
        "evidence":           [{"label": "Exception Type", "value": exc_type},
                               {"label": "Amount Delta",   "value": f"₹{delta:.2f}"}],
        "tool_calls":         "[]",
        "auto_resolved":      False,
    }
