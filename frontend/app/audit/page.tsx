"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import { getAuditLogs, AuditLog } from "@/lib/api";
import { fmtDate } from "@/lib/utils";
import { Monitor, Sparkles, User, CheckCircle, AlertTriangle, Flag } from "lucide-react";

const actorIcon = (a: string) => {
  if (a === "system") return <Monitor size={13} />;
  if (a === "ai") return <Sparkles size={13} />;
  return <User size={13} />;
};

const actorColor = (a: string) =>
  a === "system" ? "var(--text-muted)" : a === "ai" ? "var(--accent)" : "var(--success)";

const actorBg = (a: string) =>
  a === "system" ? "rgba(100,116,139,0.08)" : a === "ai" ? "var(--accent-muted)" : "var(--success-muted)";

const actionIcon = (action: string) => {
  const a = action.toLowerCase();
  if (a.includes("resolve") || a.includes("match")) return <CheckCircle size={11} />;
  if (a.includes("flag") || a.includes("exception")) return <AlertTriangle size={11} />;
  if (a.includes("investigate")) return <Sparkles size={11} />;
  return <Flag size={11} />;
};

const dotColor = (actor: string) =>
  actor === "ai" ? "var(--accent)" : actor === "system" ? "var(--text-muted)" : "var(--success)";

export default function Audit() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  useEffect(() => { getAuditLogs().then(r => setLogs(r.data)); }, []);

  return (
    <div className="page-bg" style={{
      display: "flex", minHeight: "100vh",
      fontFamily: "var(--font-body)", color: "var(--text)",
    }}>
      <Sidebar />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Topbar />
        <main style={{ flex: 1, padding: 24 }}>
          <h1 style={{
            fontSize: 20, fontWeight: 600, marginBottom: 16,
            fontFamily: "var(--font-display)",
          }}>
            Audit Trail
          </h1>
          <div className="card" style={{ overflow: "hidden", padding: "16px 20px" }}>
            {/* Timeline feed */}
            <div style={{ maxHeight: "75vh", overflowY: "auto" }}>
              {logs.map((l, i) => (
                <div key={i} className="timeline-row" style={{
                  padding: "12px 0 12px 28px", fontSize: 13,
                  transition: "background 0.12s ease",
                }}>
                  {/* Timeline dot */}
                  <div className="timeline-dot" style={{ borderColor: dotColor(l.actor) }} />

                  {/* Content */}
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                    {/* Timestamp */}
                    <span style={{
                      color: "var(--text-muted)", fontSize: 11,
                      fontFamily: "var(--font-mono)",
                      minWidth: 110, flexShrink: 0, marginTop: 1,
                    }}>
                      {fmtDate(l.created_at)}
                    </span>

                    {/* Actor badge */}
                    <span style={{
                      display: "inline-flex", alignItems: "center", gap: 4,
                      color: actorColor(l.actor), fontWeight: 600, fontSize: 10,
                      padding: "2px 8px", borderRadius: 5,
                      background: actorBg(l.actor),
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      minWidth: 60, justifyContent: "center", flexShrink: 0,
                    }}>
                      {actorIcon(l.actor)}
                      {l.actor}
                    </span>

                    {/* Action content */}
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ color: actorColor(l.actor), opacity: 0.7 }}>
                          {actionIcon(l.action)}
                        </span>
                        <span style={{ fontWeight: 500 }}>{l.action}</span>
                        {l.entity_type && (
                          <span style={{
                            fontFamily: "var(--font-mono)", fontSize: 10,
                            color: "var(--text-muted)", padding: "1px 6px",
                            background: "var(--glass-surface)", borderRadius: 4,
                            border: "1px solid var(--glass-border)",
                          }}>
                            {l.entity_type}
                          </span>
                        )}
                      </div>
                      {l.detail && (
                        <p style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 3 }}>
                          {l.detail}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {logs.length === 0 && (
                <p style={{ padding: "40px 20px", textAlign: "center", color: "var(--text-muted)", fontSize: 14 }}>
                  No audit logs yet.
                </p>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
