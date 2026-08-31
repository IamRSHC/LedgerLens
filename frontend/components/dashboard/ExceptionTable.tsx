"use client";
import { useState } from "react";
import { Exception, Investigation, resolveException } from "@/lib/api";
import { excTypeLabel, fmtDate } from "@/lib/utils";
import { CheckCircle, Flag, X, Search, Sparkles, ChevronRight, Shield } from "lucide-react";

function SeverityBadge({ severity }: { severity: string }) {
  const cls = severity === "critical" ? "badge-danger"
    : severity === "warning" ? "badge-warning" : "badge-info";
  return <span className={`badge ${cls}`}>{severity}</span>;
}

function StatusIndicator({ status }: { status: string }) {
  const resolved = status === "matched" || status === "auto_resolved" || status === "resolved";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      fontWeight: 600, fontSize: 12,
      color: resolved ? "var(--success)" : status === "open" ? "var(--warning)" : "var(--text-muted)",
    }}>
      {resolved
        ? <CheckCircle size={13} />
        : <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--warning)", display: "inline-block" }} />}
      {status.replace("_", " ")}
    </span>
  );
}

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
    <div style={{
      position: "fixed", inset: 0, zIndex: 50, display: "flex", justifyContent: "flex-end",
      background: "rgba(0,0,0,0.4)", backdropFilter: "blur(4px)",
    }} onClick={onClose}>
      <div className="animate-slide-in" style={{
        width: 520, background: "var(--bg-card)", borderLeft: "1px solid var(--border)",
        minHeight: "100vh", padding: 28, overflowY: "auto",
        display: "flex", flexDirection: "column", gap: 16,
        boxShadow: "var(--shadow-elevated)",
      }} onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <p className="label-mono" style={{ marginBottom: 6 }}>{exc.exception_id}</p>
            <h2 style={{ fontSize: 18, fontWeight: 700, fontFamily: "var(--font-display)" }}>
              {excTypeLabel[exc.exception_type] ?? exc.exception_type}
            </h2>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <SeverityBadge severity={exc.severity} />
            <button onClick={onClose} style={{
              background: "var(--bg-elevated)", border: "1px solid var(--border)",
              borderRadius: 6, width: 32, height: 32,
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "var(--text-muted)", cursor: "pointer",
            }}>
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Raw data */}
        <div className="card" style={{ padding: 16 }}>
          <p className="label-mono" style={{ marginBottom: 12 }}>Exception Details</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            {[
              ["Order ID", exc.order_id ?? "—"],
              ["Type", excTypeLabel[exc.exception_type] ?? exc.exception_type],
              ["Amount Delta", exc.amount_delta != null ? `₹${Math.abs(exc.amount_delta).toFixed(2)}` : "—"],
              ["Status", exc.status.replace("_", " ")],
              ["Detected", fmtDate(exc.created_at)],
            ].map(([k, v]) => (
              <div key={k}>
                <p style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 3 }}>{k}</p>
                <p style={{
                  fontSize: 13, fontWeight: 500,
                  fontFamily: k === "Order ID" || k === "Amount Delta" ? "var(--font-mono)" : undefined,
                }}>{v}</p>
              </div>
            ))}
          </div>
        </div>

        {/* AI Investigation */}
        {inv ? (
          <div style={{
            background: "var(--accent-muted)", border: "1px solid var(--accent-border)",
            borderRadius: 12, padding: 16, display: "flex", flexDirection: "column", gap: 14,
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Sparkles size={14} style={{ color: "var(--accent)" }} />
                <p className="label-mono" style={{ color: "var(--accent)" }}>AI Investigation</p>
              </div>
              <div style={{
                display: "flex", alignItems: "center", gap: 6,
                fontSize: 12, fontWeight: 600, color: "var(--success)",
              }}>
                <Shield size={13} />
                {(inv.confidence * 100).toFixed(0)}% confidence
              </div>
            </div>

            {/* Confidence bar */}
            <div style={{ height: 4, borderRadius: 2, background: "var(--border)", overflow: "hidden" }}>
              <div style={{
                height: "100%", borderRadius: 2, width: `${inv.confidence * 100}%`,
                background: inv.confidence >= 0.8 ? "var(--success)"
                  : inv.confidence >= 0.5 ? "var(--warning)" : "var(--danger)",
                transition: "width 0.5s ease",
              }} />
            </div>

            <div>
              <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{inv.root_cause}</p>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>{inv.explanation}</p>
            </div>

            {toolCalls.length > 0 && (
              <div>
                <p className="label-mono" style={{ marginBottom: 8 }}>Tools Used</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {toolCalls.map((t, i) => (
                    <div key={i} style={{
                      fontSize: 12, display: "flex", alignItems: "center", gap: 6,
                      color: "var(--text-secondary)",
                    }}>
                      <CheckCircle size={12} style={{ color: "var(--success)" }} />
                      <span style={{ fontFamily: "var(--font-mono)" }}>{t.tool}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {evidence.length > 0 && (
              <div>
                <p className="label-mono" style={{ marginBottom: 8 }}>Evidence</p>
                {evidence.map((e, i) => (
                  <div key={i} style={{
                    display: "flex", justifyContent: "space-between",
                    padding: "8px 0", borderBottom: "1px solid var(--border)",
                    fontSize: 13,
                  }}>
                    <span style={{ color: "var(--text-secondary)" }}>{e.label}</span>
                    <span className="font-mono" style={{ fontWeight: 600, fontSize: 12 }}>{e.value}</span>
                  </div>
                ))}
              </div>
            )}

            <div style={{
              background: "var(--bg-elevated)", borderRadius: 8, padding: "12px 14px",
              border: "1px solid var(--border)",
            }}>
              <p className="label-mono" style={{ marginBottom: 4 }}>Recommended Action</p>
              <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)" }}>{inv.recommended_action}</p>
            </div>
          </div>
        ) : (
          <div className="card" style={{
            padding: 24, textAlign: "center", color: "var(--text-muted)", fontSize: 13,
          }}>
            No AI investigation yet.
          </div>
        )}

        {/* Actions */}
        {exc.status === "open" ? (
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={doResolve} disabled={resolving} className="btn-primary" style={{
              flex: 1, justifyContent: "center", padding: "12px 0",
              background: "var(--success)", opacity: resolving ? 0.6 : 1,
            }}>
              <CheckCircle size={16} />
              {resolving ? "Resolving..." : "Mark Resolved"}
            </button>
            <button className="btn-secondary" style={{ padding: "12px 18px" }}>
              <Flag size={14} style={{ color: "var(--danger)" }} />
              <span style={{ color: "var(--danger)" }}>Flag</span>
            </button>
          </div>
        ) : (
          <div className="badge-success" style={{
            padding: "12px", textAlign: "center", borderRadius: 8,
            fontSize: 14, fontWeight: 600, display: "flex", alignItems: "center",
            justifyContent: "center", gap: 6,
          }}>
            <CheckCircle size={16} />
            {exc.status.replace("_", " ")}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ExceptionTable({ exceptions, onRefresh }: { exceptions: Exception[]; onRefresh: () => void }) {
  const [selected, setSelected] = useState<Exception | null>(null);
  const [filter, setFilter] = useState("all");

  const filtered = filter === "all" ? exceptions : exceptions.filter(e => e.status === filter);

  const gridCols = "120px 2fr 1.5fr 100px 90px 100px";

  return (
    <>
    <div className="card animate-fade-in" style={{ overflow: "hidden", animationDelay: "0.3s" }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "14px 20px", borderBottom: "1px solid var(--border)",
      }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, fontFamily: "var(--font-display)" }}>
          Reconciliation Results
        </h2>
        <div style={{ display: "flex", gap: 6 }}>
          {["all", "open", "auto_resolved", "resolved"].map(s => (
            <button key={s} onClick={() => setFilter(s)} style={{
              fontSize: 12, padding: "4px 12px", borderRadius: 9999, cursor: "pointer",
              transition: "all 0.15s ease", fontWeight: filter === s ? 600 : 400,
              background: filter === s ? "var(--accent-muted)" : "transparent",
              color: filter === s ? "var(--accent)" : "var(--text-muted)",
              border: `1px solid ${filter === s ? "var(--accent-border)" : "var(--border)"}`,
            }}>
              {s.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Column headers */}
      <div style={{
        display: "grid", gridTemplateColumns: gridCols, alignItems: "center",
        padding: "10px 20px", borderBottom: "1px solid var(--border)",
      }}>
        {["Status", "Type", "Order ID", "Delta", "Severity", "Action"].map(h => (
          <span key={h} className="label-mono">{h}</span>
        ))}
      </div>

      {/* Rows */}
      <div style={{ maxHeight: 420, overflowY: "auto" }}>
        {filtered.length === 0 && (
          <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--text-muted)", fontSize: 14 }}>
            No records in this filter.
          </div>
        )}
        {filtered.map(exc => (
          <div key={exc.exception_id} style={{
            display: "grid", gridTemplateColumns: gridCols, alignItems: "center",
            padding: "11px 20px", borderBottom: "1px solid var(--border)",
            fontSize: 13, cursor: "pointer", transition: "background 0.1s ease",
          }}
            onMouseEnter={e => (e.currentTarget.style.background = "var(--row-hover)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            onClick={() => setSelected(exc)}>
            <StatusIndicator status={exc.status} />
            <span style={{ fontWeight: 500 }}>{excTypeLabel[exc.exception_type] ?? exc.exception_type}</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)" }}>
              {exc.order_id ? `...${exc.order_id.slice(-10)}` : "—"}
            </span>
            <span className="font-mono" style={{
              fontSize: 12,
              color: exc.amount_delta && Math.abs(exc.amount_delta) > 0 ? "var(--danger)" : "var(--text-muted)",
              fontWeight: exc.amount_delta ? 600 : 400,
            }}>
              {exc.amount_delta != null ? `₹${Math.abs(exc.amount_delta).toFixed(0)}` : "—"}
            </span>
            <SeverityBadge severity={exc.severity} />
            <button onClick={e => { e.stopPropagation(); setSelected(exc); }} style={{
              fontSize: 12, padding: "5px 12px", borderRadius: 8, cursor: "pointer",
              fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 4,
              transition: "all 0.15s ease",
              ...(exc.status === "open"
                ? { background: "var(--accent-muted)", color: "var(--accent)", border: "1px solid var(--accent-border)" }
                : { background: "transparent", color: "var(--text-muted)", border: "1px solid var(--border)" }),
            }}>
              {exc.status === "open" ? <><Search size={12} /> Investigate</> : <><ChevronRight size={12} /> View</>}
            </button>
          </div>
        ))}
      </div>

    </div>

    {selected && (
      <Drawer exc={selected} onClose={() => setSelected(null)}
              onResolved={() => { setSelected(null); onRefresh(); }} />
    )}
    </>
  );
}
