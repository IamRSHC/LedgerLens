"use client";
import { useEffect, useState, useCallback } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import KPICards from "@/components/dashboard/KPICards";
import Charts from "@/components/dashboard/Charts";
import ExceptionTable from "@/components/dashboard/ExceptionTable";
import { getDashboard, getExceptions, getRuns, DashboardStats, Exception, Run } from "@/lib/api";

function BackendOffline() {
  return (
    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "var(--panel)", border: "1px solid var(--line)",
        borderRadius: 16, padding: "40px 48px", textAlign: "center", maxWidth: 440 }}>
        <div style={{ fontSize: 40, marginBottom: 16 }}>🔌</div>
        <h2 style={{ fontWeight: 600, marginBottom: 8, fontSize: 18 }}>Backend not running</h2>
        <p style={{ color: "#8792A8", fontSize: 14, lineHeight: 1.7, marginBottom: 24 }}>
          The FastAPI server at <code style={{ color: "#4C8DFF", background: "rgba(76,141,255,0.1)",
          padding: "1px 6px", borderRadius: 4 }}>localhost:8000</code> isn't reachable.
        </p>
        <div style={{ background: "rgba(0,0,0,0.3)", borderRadius: 10, padding: "14px 18px",
          textAlign: "left", fontFamily: "monospace", fontSize: 12, color: "#8792A8", lineHeight: 2 }}>
          <div style={{ color: "#5C6883" }}># In your backend folder:</div>
          <div>pip install -r requirements.txt</div>
          <div>python data/generate.py</div>
          <div>uvicorn app.main:app --reload</div>
        </div>
        <p style={{ marginTop: 16, fontSize: 12, color: "#5C6883" }}>
          Then refresh this page or click "Run New Batch" in the top bar.
        </p>
      </div>
    </div>
  );
}

function NoData({ onRun }: { onRun: () => void }) {
  return (
    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "var(--panel)", border: "1px solid var(--line)",
        borderRadius: 16, padding: "40px 48px", textAlign: "center" }}>
        <div style={{ fontSize: 40, marginBottom: 16 }}>📊</div>
        <h2 style={{ fontWeight: 600, marginBottom: 8 }}>No batches yet</h2>
        <p style={{ color: "#8792A8", fontSize: 14, marginBottom: 24 }}>
          Run your first reconciliation to see the dashboard populate.
        </p>
        <button onClick={onRun} style={{ padding: "11px 24px", borderRadius: 10, fontWeight: 600,
          fontSize: 14, background: "#4C8DFF", color: "#fff",
          border: "none", cursor: "pointer" }}>
          Run New Batch →
        </button>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats]     = useState<DashboardStats | null>(null);
  const [excs, setExcs]       = useState<Exception[]>([]);
  const [run, setRun]         = useState<Run | null>(null);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setOffline(false);
    try {
      const [statsRes, excsRes, runsRes] = await Promise.all([
        getDashboard(), getExceptions(), getRuns(),
      ]);
      setStats(statsRes.data as DashboardStats);
      setExcs(excsRes.data as Exception[]);
      setRun((runsRes.data as Run[])?.[0] ?? null);
    } catch (e: any) {
      if (!e?.response) setOffline(true); // network error = backend down
    } finally {
      setLoading(false);
    }
  }, []);

  const runBatch = useCallback(async () => {
    const { runReconciliation } = await import("@/lib/api");
    setRunning(true);
    try { await runReconciliation(); await load(); }
    catch { setOffline(true); }
    finally { setRunning(false); }
  }, [load]);

  useEffect(() => { load(); }, [load]);

  const healthLabel = !stats ? null
    : stats.match_rate >= 90 ? { text: "All Clear",    color: "#2FB380", icon: "✓" }
    : stats.match_rate >= 75 ? { text: "Needs Review", color: "#F5A524", icon: "⚠" }
    : { text: "Critical",    color: "#EF4444", icon: "✕" };

  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "var(--font-body)",
      background: "var(--ink)", color: "var(--text)" }}>
      <Sidebar />
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <Topbar runId={run?.run_id} runDate={run?.started_at} onRun={runBatch} running={running} />

        <main style={{ flex: 1, padding: 24, display: "flex", flexDirection: "column",
          gap: 16, overflow: "auto" }}>

          {loading ? (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ color: "#5C6883", fontSize: 14 }}>Loading…</div>
            </div>
          ) : offline ? (
            <BackendOffline />
          ) : !stats ? (
            <NoData onRun={runBatch} />
          ) : (
            <>
              {/* Health banner */}
              {healthLabel && (
                <div style={{ background: `${healthLabel.color}0f`,
                  border: `1px solid ${healthLabel.color}30`, borderRadius: 12,
                  padding: "12px 20px", display: "flex", alignItems: "center",
                  justifyContent: "space-between" }}>
                  <p style={{ fontSize: 14, color: "#8792A8" }}>
                    <span style={{ fontWeight: 600, color: healthLabel.color }}>
                      {healthLabel.icon} {healthLabel.text}
                    </span>
                    {" — "}
                    {run?.run_id} · {stats.total_records} records ·{" "}
                    {stats.exceptions > 0
                      ? `${stats.exceptions} exceptions require attention`
                      : "All records reconciled cleanly 🎉"}
                  </p>
                  <span style={{ fontSize: 12, padding: "3px 10px", borderRadius: 100,
                    color: healthLabel.color, border: `1px solid ${healthLabel.color}40`,
                    background: `${healthLabel.color}12`, fontWeight: 500 }}>
                    {healthLabel.text}
                  </span>
                </div>
              )}

              <KPICards stats={stats} />
              <Charts stats={stats} />
              <ExceptionTable exceptions={excs} onRefresh={load} />
            </>
          )}
        </main>
      </div>
    </div>
  );
}
