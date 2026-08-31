"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import { getAuditLogs, AuditLog } from "@/lib/api";
import { fmtDate } from "@/lib/utils";
import { Monitor, Sparkles, User } from "lucide-react";

const actorIcon = (a: string) => {
  if (a === "system") return <Monitor size={13} />;
  if (a === "ai") return <Sparkles size={13} />;
  return <User size={13} />;
};

const actorColor = (a: string) =>
  a === "system" ? "var(--text-muted)" : a === "ai" ? "var(--accent)" : "var(--success)";

export default function Audit() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  useEffect(() => { getAuditLogs().then(r => setLogs(r.data)); }, []);

  const gridCols = "160px 100px 120px 1fr";

  return (
    <div style={{
      display: "flex", minHeight: "100vh",
      fontFamily: "var(--font-body)", background: "var(--bg)", color: "var(--text)",
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
          <div className="card" style={{ overflow: "hidden" }}>
            <div style={{
              display: "grid", gridTemplateColumns: gridCols, alignItems: "center",
              padding: "10px 20px", borderBottom: "1px solid var(--border)",
            }}>
              {["Time", "Actor", "Entity", "Action"].map(h => (
                <span key={h} className="label-mono">{h}</span>
              ))}
            </div>
            <div style={{ maxHeight: "75vh", overflowY: "auto" }}>
              {logs.map((l, i) => (
                <div key={i} style={{
                  display: "grid", gridTemplateColumns: gridCols, alignItems: "center",
                  padding: "10px 20px", fontSize: 13,
                  borderBottom: "1px solid var(--border)",
                  transition: "background 0.1s ease",
                }}
                  onMouseEnter={e => (e.currentTarget.style.background = "var(--row-hover)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                  <span style={{
                    color: "var(--text-muted)", fontSize: 12,
                    fontFamily: "var(--font-mono)",
                  }}>
                    {fmtDate(l.created_at)}
                  </span>
                  <span style={{
                    display: "inline-flex", alignItems: "center", gap: 5,
                    color: actorColor(l.actor), fontWeight: 500, fontSize: 12,
                  }}>
                    {actorIcon(l.actor)}
                    {l.actor}
                  </span>
                  <span style={{
                    fontFamily: "var(--font-mono)", fontSize: 11,
                    color: "var(--text-muted)",
                  }}>
                    {l.entity_type}
                  </span>
                  <span>
                    {l.action}
                    {l.detail && (
                      <span style={{ color: "var(--text-muted)" }}> — {l.detail}</span>
                    )}
                  </span>
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
