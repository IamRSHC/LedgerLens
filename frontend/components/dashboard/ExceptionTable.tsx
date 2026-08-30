"use client";
import { useState } from "react";
import { Exception, Investigation, resolveException } from "@/lib/api";
import { excTypeLabel, fmtDate } from "@/lib/utils";

const sevStyle = (s: string): React.CSSProperties => ({
  fontSize: 11, padding: "2px 9px", borderRadius: 100, fontWeight: 600,
  ...(s === "critical" ? { color: "#EF4444", background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)" }
    : s === "warning"  ? { color: "#F5A524", background: "rgba(245,165,36,0.12)", border: "1px solid rgba(245,165,36,0.25)" }
    : { color: "#4C8DFF", background: "rgba(76,141,255,0.12)", border: "1px solid rgba(76,141,255,0.25)" }),
});

const statusStyle = (s: string): React.CSSProperties => ({
  fontWeight: 600, fontSize: 12,
  color: s === "matched" || s === "auto_resolved" || s === "resolved" ? "#2FB380"
       : s === "open" ? "#F5A524" : "#8792A8",
});

function Drawer({ exc, onClose, onResolved }: { exc: Exception; onClose: () => void; onResolved: () => void }) {
  const [resolving, setResolving] = useState(false);
  const inv: Investigation | undefined = exc.investigation;
  let evidence: { label: string; value: string }[] = [];
  try { evidence = inv?.evidence ? JSON.parse(inv.evidence) : []; } catch {}
  let toolCalls: { tool: string; args: object; result: object }[] = [];
  try { toolCalls = inv?.tool_calls ? JSON.parse(inv.tool_calls) : []; } catch {}

  async function doResolve() {
    setResolving(true);
    try { await resolveException(exc.exception_id, inv?.recommended_action ?? "Manually reviewed"); onResolved(); }
    finally { setResolving(false); }
  }

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex", justifyContent: "flex-end" }}
         onClick={onClose}>
      <div style={{ width: 500, background: "#131B2C", borderLeft: "1px solid var(--line)",
        minHeight: "100vh", padding: 28, overflowY: "auto", display: "flex", flexDirection: "column", gap: 16 }}
           onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <p style={{ fontSize: 11, color: "#5C6883", fontFamily: "var(--font-mono)", marginBottom: 4 }}>
              {exc.exception_id}
            </p>
            <h2 style={{ fontSize: 18, fontWeight: 700 }}>
              {excTypeLabel[exc.exception_type] ?? exc.exception_type}
            </h2>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={sevStyle(exc.severity)}>{exc.severity.toUpperCase()}</span>
            <button onClick={onClose} style={{ background: "none", border: "none", color: "#5C6883",
              cursor: "pointer", fontSize: 18, padding: 4 }}>✕</button>
          </div>
        </div>

        {/* Raw data */}
        <div style={{ background: "var(--panel)", border: "1px solid var(--line)",
          borderRadius: 12, padding: 16 }}>
          <p style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em",
            color: "#5C6883", marginBottom: 12 }}>Raw Data</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {[
              ["Order ID", exc.order_id ?? "—"],
              ["Exception Type", excTypeLabel[exc.exception_type] ?? exc.exception_type],
              ["Amount Delta", exc.amount_delta != null ? `₹${Math.abs(exc.amount_delta).toFixed(2)}` : "—"],
              ["Status", exc.status.replace("_", " ")],
              ["Detected", fmtDate(exc.created_at)],
            ].map(([k, v]) => (
              <div key={k}>
                <p style={{ fontSize: 11, color: "#5C6883", marginBottom: 2 }}>{k}</p>
                <p style={{ fontSize: 13, fontWeight: 500, fontFamily: k === "Order ID" ? "monospace" : undefined }}>{v}</p>
              </div>
            ))}
          </div>
        </div>

        {/* AI Investigation */}
        {inv ? (
          <div style={{ background: "rgba(76,141,255,0.06)", border: "1px solid rgba(76,141,255,0.2)",
            borderRadius: 12, padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <p style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase",
                letterSpacing: "0.08em", color: "#4C8DFF" }}>🤖 AI Investigation</p>
              <span style={{ fontSize: 12, color: "#2FB380", fontWeight: 600 }}>
                {(inv.confidence * 100).toFixed(0)}% confidence
              </span>
            </div>

            <div>
              <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{inv.root_cause}</p>
              <p style={{ fontSize: 13, color: "#8792A8", lineHeight: 1.7 }}>{inv.explanation}</p>
            </div>

            {/* Tool calls (the "audit trail" of AI reasoning) */}
            {toolCalls.length > 0 && (
              <div>
                <p style={{ fontSize: 11, color: "#5C6883", marginBottom: 8,
                  textTransform: "uppercase", letterSpacing: "0.08em" }}>Tools Used</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {toolCalls.map((t, i) => (
                    <div key={i} style={{ fontSize: 12, color: "#4C8DFF", display: "flex",
                      alignItems: "center", gap: 6 }}>
                      <span style={{ color: "#2FB380" }}>✓</span> {t.tool}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Evidence */}
            {evidence.length > 0 && (
              <div>
                <p style={{ fontSize: 11, color: "#5C6883", marginBottom: 8,
                  textTransform: "uppercase", letterSpacing: "0.08em" }}>Evidence</p>
                {evidence.map((e, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between",
                    padding: "7px 0", borderBottom: "1px solid var(--panel-raised)",
                    fontSize: 13 }}>
                    <span style={{ color: "#8792A8" }}>{e.label}</span>
                    <span style={{ fontWeight: 600 }}>{e.value}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Recommendation */}
            <div style={{ background: "var(--panel-raised)", borderRadius: 10, padding: "12px 14px" }}>
              <p style={{ fontSize: 11, color: "#5C6883", marginBottom: 4 }}>Recommended Action</p>
              <p style={{ fontSize: 13, lineHeight: 1.6 }}>{inv.recommended_action}</p>
            </div>
          </div>
        ) : (
          <div style={{ background: "var(--panel)", border: "1px solid var(--line)",
            borderRadius: 12, padding: 20, textAlign: "center", color: "#5C6883", fontSize: 13 }}>
            No AI investigation yet.
          </div>
        )}

        {/* Actions */}
        {exc.status === "open" ? (
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={doResolve} disabled={resolving} style={{
              flex: 1, padding: "11px 0", borderRadius: 10, fontWeight: 600, fontSize: 14,
              background: "#2FB380", color: "#000", border: "none",
              cursor: resolving ? "not-allowed" : "pointer", opacity: resolving ? 0.7 : 1,
            }}>
              {resolving ? "Resolving…" : "✓ Mark Resolved"}
            </button>
            <button style={{ padding: "11px 18px", borderRadius: 10, fontWeight: 600, fontSize: 14,
              background: "rgba(239,68,68,0.1)", color: "#EF4444",
              border: "1px solid rgba(239,68,68,0.2)", cursor: "pointer" }}>
              🚩 Flag Review
            </button>
          </div>
        ) : (
          <div style={{ padding: "11px", textAlign: "center", borderRadius: 10,
            background: "rgba(47,179,128,0.06)", border: "1px solid rgba(47,179,128,0.2)",
            color: "#2FB380", fontSize: 14, fontWeight: 600 }}>
            ✓ {exc.status.replace("_", " ")}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ExceptionTable({ exceptions, onRefresh }: { exceptions: Exception[]; onRefresh: () => void }) {
  const [selected, setSelected] = useState<Exception | null>(null);
  const [filter, setFilter]     = useState("all");

  const filtered = filter === "all" ? exceptions : exceptions.filter(e => e.status === filter);

  const col: React.CSSProperties = { display: "grid",
    gridTemplateColumns: "120px 2fr 1.5fr 100px 90px 100px",
    alignItems: "center", padding: "0 20px" };

  return (
    <div style={{ background: "var(--panel)", border: "1px solid var(--line)",
      borderRadius: 14, overflow: "hidden" }}>

      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "14px 20px", borderBottom: "1px solid var(--line)" }}>
        <h2 style={{ fontSize: 14, fontWeight: 600 }}>Reconciliation Results</h2>
        <div style={{ display: "flex", gap: 6 }}>
          {["all", "open", "auto_resolved", "resolved"].map(s => (
            <button key={s} onClick={() => setFilter(s)} style={{
              fontSize: 12, padding: "4px 12px", borderRadius: 100,
              border: "1px solid", cursor: "pointer", transition: "all 0.15s",
              fontWeight: filter === s ? 600 : 400,
              background: filter === s ? "rgba(76,141,255,0.15)" : "transparent",
              color: filter === s ? "#4C8DFF" : "#5C6883",
              borderColor: filter === s ? "rgba(76,141,255,0.3)" : "var(--line)",
            }}>
              {s.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Column labels */}
      <div style={{ ...col, padding: "10px 20px",
        borderBottom: "1px solid var(--line)", fontSize: 11,
        textTransform: "uppercase", letterSpacing: "0.07em", color: "#5C6883", fontWeight: 600 }}>
        <span>Status</span><span>Type</span><span>Order ID</span>
        <span>Delta</span><span>Severity</span><span>Action</span>
      </div>

      {/* Rows */}
      <div style={{ maxHeight: 420, overflowY: "auto" }}>
        {filtered.length === 0 && (
          <div style={{ padding: "40px 20px", textAlign: "center", color: "#5C6883", fontSize: 14 }}>
            No records in this filter.
          </div>
        )}
        {filtered.map(exc => (
          <div key={exc.exception_id} style={{ ...col, padding: "11px 20px",
            borderBottom: "1px solid var(--panel-raised)", fontSize: 13,
            cursor: "pointer", transition: "background 0.1s" }}
            onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.02)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
            <span style={statusStyle(exc.status)}>
              {exc.status === "matched" || exc.status === "auto_resolved" || exc.status === "resolved" ? "✓" : "⚠"}{" "}
              {exc.status.replace("_", " ")}
            </span>
            <span style={{ fontWeight: 500 }}>{excTypeLabel[exc.exception_type] ?? exc.exception_type}</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "#5C6883" }}>
              {exc.order_id ? `…${exc.order_id.slice(-10)}` : "—"}
            </span>
            <span style={{ color: exc.amount_delta && Math.abs(exc.amount_delta) > 0 ? "#EF4444" : "#8792A8",
              fontWeight: exc.amount_delta ? 600 : 400 }}>
              {exc.amount_delta != null ? `₹${Math.abs(exc.amount_delta).toFixed(0)}` : "—"}
            </span>
            <span style={sevStyle(exc.severity)}>{exc.severity}</span>
            <button onClick={() => setSelected(exc)} style={{
              fontSize: 12, padding: "5px 12px", borderRadius: 8, cursor: "pointer",
              fontWeight: 600, border: "1px solid",
              ...(exc.status === "open"
                ? { background: "rgba(76,141,255,0.12)", color: "#4C8DFF", borderColor: "rgba(76,141,255,0.25)" }
                : { background: "transparent", color: "#5C6883", borderColor: "var(--line)" }),
            }}>
              {exc.status === "open" ? "Investigate" : "View"}
            </button>
          </div>
        ))}
      </div>

      {selected && (
        <Drawer exc={selected} onClose={() => setSelected(null)}
                onResolved={() => { setSelected(null); onRefresh(); }} />
      )}
    </div>
  );
}
