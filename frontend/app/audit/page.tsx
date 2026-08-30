"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import { getAuditLogs, AuditLog } from "@/lib/api";
import { fmtDate } from "@/lib/utils";

const actorColor = (a: string) => ({ system:"text-[#8792A8]", ai:"text-[#4C8DFF]", user:"text-[#2FB380]" }[a] ?? "text-[#8792A8]");

export default function Audit() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  useEffect(() => { getAuditLogs().then(r => setLogs(r.data)); }, []);
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Topbar />
        <main className="flex-1 p-6">
          <h1 className="text-xl font-semibold mb-4">Audit Trail</h1>
          <div className="glass">
            <div className="grid text-xs font-medium uppercase tracking-widest px-4 py-2.5 border-b"
                 style={{ gridTemplateColumns:"160px 80px 120px 1fr", borderColor:"var(--border)", color:"var(--muted)" }}>
              <span>Time</span><span>Actor</span><span>Entity</span><span>Action</span>
            </div>
            <div className="divide-y max-h-[75vh] overflow-y-auto" style={{ divideColor:"var(--border)" }}>
              {logs.map((l, i) => (
                <div key={i} className="grid items-center px-4 py-2.5 text-xs hover:bg-white/[0.02]"
                     style={{ gridTemplateColumns:"160px 80px 120px 1fr" }}>
                  <span style={{ color:"var(--muted)" }}>{fmtDate(l.created_at)}</span>
                  <span className={actorColor(l.actor)}>{l.actor}</span>
                  <span className="font-mono" style={{ color:"var(--muted)" }}>{l.entity_type}</span>
                  <span>{l.action}{l.detail ? <span style={{color:"var(--muted)"}}> — {l.detail}</span> : null}</span>
                </div>
              ))}
              {logs.length === 0 && <p className="text-center py-8 text-sm" style={{color:"var(--muted)"}}>No audit logs yet.</p>}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
