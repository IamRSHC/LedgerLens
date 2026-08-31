"use client";
import { useState } from "react";
import { Exception, Investigation, resolveException, flagException } from "@/lib/api";
import { excTypeLabel, fmtDate } from "@/lib/utils";
import { CheckCircle, Flag, X, Search, Sparkles, ChevronRight, Shield, AlertTriangle, Circle } from "lucide-react";

function SeverityBadge({ severity }: { severity: string }) {
  const cls = severity === "critical" ? "badge-danger"
    : severity === "warning" ? "badge-warning" : "badge-info";
  return (
    <span className={`badge ${cls}`}>
      <span style={{
        width: 5, height: 5, borderRadius: "50%", display: "inline-block",
        background: severity === "critical" ? "var(--danger)"
          : severity === "warning" ? "var(--warning)" : "var(--info)",
      }} />
      {severity}
    </span>
  );
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

function ToolCallRow({ tool, result, isLast }: { tool: string; result: any; isLast: boolean }) {
  const hasResult = result && typeof result === "object" && Object.keys(result).length > 0;
  const completed = hasResult || result !== undefined;

  const resultSummary = hasResult
    ? Object.entries(result).slice(0, 1).map(([k, v]) =>
        typeof v === "string" ? `${v.slice(0, 40)}${v.length > 40 ? "..." : ""}` : "Data retrieved"
      )[0]
    : "Completed";

  return (
    <div style={{
      fontSize: 12, display: "flex", alignItems: "flex-start", gap: 8,
      padding: "8px 10px",
      background: "var(--glass-surface)", borderRadius: 8,
      border: "1px solid var(--glass-border)",
      marginBottom: isLast ? 0 : 6,
    }}>
      {completed ? (
        <CheckCircle size={14} style={{ color: "var(--success)", marginTop: 1, flexShrink: 0 }} />
      ) : (
        <Circle size={14} className="tool-running" style={{ color: "var(--accent)", marginTop: 1, flexShrink: 0 }} />
      )}
      <div style={{ flex: 1 }}>
        <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--text)", fontSize: 12 }}>
          {tool}()
        </span>
        <p style={{ color: "var(--text-muted)", fontSize: 11, marginTop: 2 }}>
          {completed ? resultSummary : "Processing..."}
        </p>
      </div>
      {completed && (
        <span style={{ fontSize: 10, color: "var(--success)", fontWeight: 600, marginTop: 2, flexShrink: 0 }}>
          DONE
        </span>
      )}
    </div>
  );
}

function ResolutionPolicy({ inv }: { inv: Investigation }) {
  const confPct = (inv.confidence * 100).toFixed(0);
  const riskColor = inv.risk_level === "high" ? "var(--danger)"
    : inv.risk_level === "medium" ? "var(--warning)" : "var(--success)";
  const eligible = inv.confidence >= 0.8 && inv.risk_level !== "high";

  return (
    <div style={{
      padding: "14px 16px", borderRadius: 10,
      background: "var(--glass-surface)", border: "1px solid var(--glass-border)",
      boxShadow: "inset 0 1px 0 var(--glass-highlight)",
    }}>
      <p className="label-mono" style={{ marginBottom: 12, letterSpacing: "0.1em" }}>Resolution Policy</p>
      <div style={{ display: "flex", gap: 24, marginBottom: 12 }}>
        <div>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>AI confidence</span>
          <p style={{
            fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 18, marginTop: 2,
            color: inv.confidence >= 0.8 ? "var(--success)" : inv.confidence >= 0.5 ? "var(--warning)" : "var(--danger)",
          }}>
            {confPct}%
          </p>
        </div>
        <div>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Risk</span>
          <p style={{
            fontWeight: 700, fontSize: 18, marginTop: 2,
            textTransform: "capitalize", color: riskColor,
          }}>
            {inv.risk_level}
          </p>
        </div>
      </div>
      {/* Confidence bar */}
      <div style={{
        height: 4, borderRadius: 2, marginBottom: 12,
        background: "rgba(255,255,255,0.08)", overflow: "hidden",
      }}>
        <div style={{
          height: "100%", borderRadius: 2, width: `${inv.confidence * 100}%`,
          background: inv.confidence >= 0.8 ? "var(--success)" : inv.confidence >= 0.5 ? "var(--warning)" : "var(--danger)",
          transition: "width 0.5s ease",
        }} />
      </div>
      {/* Policy verdict */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "8px 12px", borderRadius: 7,
        background: eligible ? "var(--success-muted)" : "var(--warning-muted)",
        border: `1px solid ${eligible ? "rgba(16,185,129,0.20)" : "rgba(245,158,11,0.20)"}`,
        fontSize: 13, fontWeight: 600,
        color: eligible ? "var(--success)" : "var(--warning)",
      }}>
        {eligible ? (
          <><CheckCircle size={14} /> Eligible for auto-resolution</>
        ) : (
          <><AlertTriangle size={14} /> Human review required</>
        )}
      </div>
    </div>
  );
}

function Drawer({ exc, onClose, onResolved }: { exc: Exception; onClose: () => void; onResolved: () => void }) {
  const [resolving, setResolving] = useState(false);
  const [flagging, setFlagging] = useState(false);
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

  async function doFlag() {
    setFlagging(true);
    try { await flagException(exc.exception_id); onResolved(); }
    finally { setFlagging(false); }
  }

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 50, display: "flex", justifyContent: "flex-end",
      background: "rgba(0,0,0,0.50)", backdropFilter: "blur(6px)",
    }} onClick={onClose}>
      <div className="animate-slide-in" style={{
        width: 540,
        background: "var(--glass-surface-elevated)",
        backdropFilter: "blur(36px) saturate(170%)",
        WebkitBackdropFilter: "blur(36px) saturate(170%)",
        borderLeft: "1px solid var(--glass-border)",
        boxShadow: "inset 1px 0 0 var(--glass-highlight), -20px 0 60px rgba(0,0,0,0.30)",
        minHeight: "100vh", padding: 28, overflowY: "auto",
        display: "flex", flexDirection: "column", gap: 16,
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
              background: "var(--glass-surface)", border: "1px solid var(--glass-border)",
              borderRadius: 8, width: 32, height: 32,
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "var(--text-muted)", cursor: "pointer",
              boxShadow: "inset 0 1px 0 var(--glass-highlight)",
              transition: "all 0.15s ease",
            }}>
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Exception details */}
        <div style={{
          padding: 16, borderRadius: 10,
          background: "var(--glass-surface)",
          border: "1px solid var(--glass-border)",
          boxShadow: "inset 0 1px 0 var(--glass-highlight)",
        }}>
          <p className="label-mono" style={{ marginBottom: 12 }}>Exception Details</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            {([
              ["Order ID", exc.order_id ?? "—"],
              ["Type", excTypeLabel[exc.exception_type] ?? exc.exception_type],
              ["Amount Delta", exc.amount_delta != null ? `₹${Math.abs(exc.amount_delta).toFixed(2)}` : "—"],
              ["Status", exc.status.replace("_", " ")],
              ["Detected", fmtDate(exc.created_at)],
            ] as const).map(([k, v]) => (
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
            background: "var(--accent-muted)",
            border: "1px solid var(--accent-border)",
            borderRadius: 12, padding: 16, display: "flex", flexDirection: "column", gap: 14,
            boxShadow: "0 0 24px var(--glow-accent), inset 0 1px 0 rgba(20,184,166,0.08)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Sparkles size={14} style={{ color: "var(--accent)" }} />
                <p className="label-mono" style={{ color: "var(--accent)" }}>AI Investigation</p>
              </div>
              <div style={{
                display: "flex", alignItems: "center", gap: 6,
                fontSize: 12, fontWeight: 600,
                color: inv.confidence >= 0.8 ? "var(--success)" : inv.confidence >= 0.5 ? "var(--warning)" : "var(--danger)",
              }}>
                <Shield size={13} />
                {(inv.confidence * 100).toFixed(0)}%
              </div>
            </div>

            {/* Resolution Policy block */}
            <ResolutionPolicy inv={inv} />

            <div>
              <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{inv.root_cause}</p>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>{inv.explanation}</p>
            </div>

            {/* Tool calls with running/completed states */}
            {toolCalls.length > 0 && (
              <div>
                <p className="label-mono" style={{ marginBottom: 8 }}>Agent Tool Calls</p>
                {toolCalls.map((t, i) => (
                  <ToolCallRow key={i} tool={t.tool} result={t.result} isLast={i === toolCalls.length - 1} />
                ))}
              </div>
            )}

            {/* Evidence */}
            {evidence.length > 0 && (
              <div>
                <p className="label-mono" style={{ marginBottom: 8 }}>Evidence</p>
                {evidence.map((e, i) => (
                  <div key={i} style={{
                    display: "flex", justifyContent: "space-between",
                    padding: "8px 0",
                    borderBottom: i < evidence.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none",
                    fontSize: 13,
                  }}>
                    <span style={{ color: "var(--text-secondary)" }}>{e.label}</span>
                    <span className="font-mono" style={{ fontWeight: 600, fontSize: 12 }}>{e.value}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Recommended action */}
            <div style={{
              background: "var(--glass-surface)", borderRadius: 9, padding: "12px 14px",
              border: "1px solid var(--glass-border)",
              boxShadow: "inset 0 1px 0 var(--glass-highlight)",
            }}>
              <p className="label-mono" style={{ marginBottom: 4 }}>Recommended Action</p>
              <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)" }}>{inv.recommended_action}</p>
            </div>
          </div>
        ) : (
          <div style={{
            padding: 24, textAlign: "center", color: "var(--text-muted)", fontSize: 13,
            background: "var(--glass-surface)", borderRadius: 10,
            border: "1px solid var(--glass-border)",
          }}>
            No AI investigation yet.
          </div>
        )}

        {/* Actions — surface for exceptions still awaiting human action.
            Flag button hidden when already in manual_review (idempotent state). */}
        {(exc.status === "open" || exc.status === "manual_review") ? (
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={doResolve} disabled={resolving || flagging} className="btn-primary" style={{
              flex: 1, justifyContent: "center", padding: "12px 0",
              background: resolving
                ? "var(--success)"
                : "linear-gradient(135deg, var(--success), #059669)",
              opacity: resolving ? 0.5 : 1,
            }}>
              <CheckCircle size={16} />
              {resolving ? "Resolving..." : "Mark Resolved"}
            </button>
            {exc.status === "open" && (
              <button onClick={doFlag} disabled={resolving || flagging} className="btn-ghost" style={{
                padding: "12px 18px", color: "var(--danger)",
                opacity: flagging ? 0.5 : 1,
              }}>
                <Flag size={14} />
                {flagging ? "Flagging..." : "Flag for Review"}
              </button>
            )}
          </div>
        ) : (
          <div style={{
            padding: "12px", textAlign: "center", borderRadius: 9, fontSize: 14, fontWeight: 600,
            display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
            background: "var(--success-muted)", color: "var(--success)",
            border: "1px solid rgba(16,185,129,0.25)",
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
        padding: "14px 20px", borderBottom: "1px solid var(--glass-border)",
      }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, fontFamily: "var(--font-display)" }}>
          Reconciliation Results
        </h2>
        {/* Segmented glass control */}
        <div className="segment-control">
          {["all", "open", "manual_review", "auto_resolved", "resolved"].map(s => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`segment-item ${filter === s ? "segment-item-active" : ""}`}
            >
              {s === "auto_resolved" ? "Auto-Resolved"
                : s === "manual_review" ? "Manual Review"
                : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Column headers */}
      <div style={{
        display: "grid", gridTemplateColumns: gridCols, alignItems: "center",
        padding: "10px 20px", borderBottom: "1px solid var(--glass-border)",
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
          <div key={exc.exception_id} className="data-row" style={{
            display: "grid", gridTemplateColumns: gridCols, alignItems: "center",
            padding: "11px 20px", borderBottom: "1px solid rgba(255,255,255,0.03)",
            fontSize: 13, cursor: "pointer",
          }}
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
            <button onClick={e => { e.stopPropagation(); setSelected(exc); }}
              className={exc.status === "open" ? "btn-investigate" : "btn-ghost"}>
              {exc.status === "open"
                ? <><Search size={12} /> Investigate</>
                : <><ChevronRight size={12} /> View</>}
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
