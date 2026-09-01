"use client";
import { useEffect, useState, useCallback } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import KPICards from "@/components/dashboard/KPICards";
import Charts from "@/components/dashboard/Charts";
import ExceptionTable from "@/components/dashboard/ExceptionTable";
import { getDashboard, getExceptions, getRuns, DashboardStats, Exception, Run } from "@/lib/api";
import { AlertTriangle, CheckCircle, XCircle, WifiOff, Play } from "lucide-react";

function BackendOffline() {
  return (
    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="glass-elevated" style={{ padding: "40px 48px", textAlign: "center", maxWidth: 440 }}>
        <div style={{
          width: 48, height: 48, borderRadius: 12, margin: "0 auto 16px",
          display: "flex", alignItems: "center", justifyContent: "center",
          background: "var(--danger-muted)", color: "var(--danger)",
          border: "1px solid rgba(239,68,68,0.2)",
        }}>
          <WifiOff size={24} />
        </div>
        <h2 style={{ fontWeight: 600, marginBottom: 8, fontSize: 18, fontFamily: "var(--font-display)" }}>
          Backend not running
        </h2>
        <p style={{ color: "var(--text-secondary)", fontSize: 14, lineHeight: 1.7, marginBottom: 24 }}>
          The FastAPI server at{" "}
          <code style={{
            color: "var(--accent)", background: "var(--accent-muted)",
            padding: "1px 6px", borderRadius: 4, fontFamily: "var(--font-mono)", fontSize: 12,
          }}>localhost:8000</code>{" "}
          isn't reachable.
        </p>
        <div style={{
          background: "var(--glass-surface)", borderRadius: 10, padding: "14px 18px",
          textAlign: "left", fontFamily: "var(--font-mono)", fontSize: 12,
          color: "var(--text-secondary)", lineHeight: 2,
          border: "1px solid var(--glass-border)",
          boxShadow: "inset 0 1px 0 var(--glass-highlight)",
        }}>
          <div style={{ color: "var(--text-muted)" }}># In your backend folder:</div>
          <div>pip install -r requirements.txt</div>
          <div>python data/generate.py</div>
          <div>uvicorn app.main:app --reload</div>
        </div>
        <p style={{ marginTop: 16, fontSize: 12, color: "var(--text-muted)" }}>
          Then refresh this page or click "Run Batch" in the top bar.
        </p>
      </div>
    </div>
  );
}

function NoData({ onRun }: { onRun: () => void }) {
  return (
    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="glass-elevated" style={{ padding: "40px 48px", textAlign: "center" }}>
        <div style={{
          width: 48, height: 48, borderRadius: 12, margin: "0 auto 16px",
          display: "flex", alignItems: "center", justifyContent: "center",
          background: "var(--accent-muted)", color: "var(--accent)",
          border: "1px solid var(--accent-border)",
          boxShadow: "0 0 16px var(--glow-accent)",
        }}>
          <Play size={24} />
        </div>
        <h2 style={{ fontWeight: 600, marginBottom: 8, fontFamily: "var(--font-display)" }}>No batches yet</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 24 }}>
          Run your first reconciliation to see the dashboard.
        </p>
        <button onClick={onRun} className="btn-primary" style={{ padding: "12px 24px", fontSize: 14 }}>
          <Play size={16} />
          Run First Batch
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
      const s   = statsRes.data as DashboardStats;
      const all = excsRes.data as Exception[];
      const rs  = runsRes.data as Run[];
      setStats(s);
      // Filter the exception table to the same run the KPIs describe so the
      // two panes never disagree. When the backend didn't return a run_id
      // (no complete run yet), fall through to the unfiltered list — the
      // banner then already tells the user the situation.
      setExcs(s?.run_id ? all.filter(e => e.run_id === s.run_id) : all);
      // Prefer the run the dashboard actually summarised over the newest run
      // (which may be an incomplete/killed batch we deliberately skipped).
      const summarised = s?.run_id ? rs.find(r => r.run_id === s.run_id) : null;
      setRun(summarised ?? rs?.[0] ?? null);
    } catch (e: any) {
      if (!e?.response) setOffline(true);
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
    : stats.match_rate >= 90 ? { text: "All Clear",    color: "var(--success)", Icon: CheckCircle }
    : stats.match_rate >= 75 ? { text: "Needs Review", color: "var(--warning)", Icon: AlertTriangle }
    : { text: "Critical",    color: "var(--danger)",  Icon: XCircle };

  return (
    <div className="page-bg" style={{
      display: "flex", minHeight: "100vh",
      fontFamily: "var(--font-body)", color: "var(--text)",
    }}>
      <Sidebar />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Topbar runId={run?.run_id} runDate={run?.started_at} onRun={runBatch} running={running} />

        <main style={{ flex: 1, padding: 24, display: "flex", flexDirection: "column", gap: 16, overflow: "auto", position: "relative" }}>
          {/* Ambient glow blobs — localized light sources behind major surfaces */}
          <div className="glow-blob glow-blob-teal" style={{
            width: 400, height: 400, top: 60, left: "10%",
          }} />
          <div className="glow-blob glow-blob-indigo" style={{
            width: 300, height: 300, top: 200, right: "5%",
          }} />
          <div className="glow-blob glow-blob-teal" style={{
            width: 350, height: 350, bottom: 100, left: "40%",
          }} />

          {loading ? (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", position: "relative", zIndex: 1 }}>
              <div style={{ color: "var(--text-muted)", fontSize: 14 }}>Loading...</div>
            </div>
          ) : offline ? (
            <BackendOffline />
          ) : !stats ? (
            <NoData onRun={runBatch} />
          ) : (
            <>
              {/* Health banner — glass alert surface */}
              {healthLabel && (
                <div className="animate-fade-in" style={{
                  background: "var(--glass-surface)",
                  backdropFilter: "var(--glass-blur)",
                  WebkitBackdropFilter: "var(--glass-blur)",
                  border: `1px solid color-mix(in srgb, ${healthLabel.color} 20%, var(--glass-border))`,
                  borderRadius: 12, padding: "14px 20px",
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  boxShadow: `inset 0 1px 0 var(--glass-highlight), 0 0 24px color-mix(in srgb, ${healthLabel.color} 8%, transparent)`,
                  position: "relative", overflow: "hidden",
                }}>
                  {/* Left accent edge */}
                  <div style={{
                    position: "absolute", left: 0, top: 0, bottom: 0, width: 3,
                    background: healthLabel.color, borderRadius: "12px 0 0 12px",
                  }} />
                  <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 14, paddingLeft: 8 }}>
                    <healthLabel.Icon size={16} style={{ color: healthLabel.color }} />
                    <span>
                      <span style={{ fontWeight: 600, color: healthLabel.color }}>{healthLabel.text}</span>
                      <span style={{ color: "var(--text-secondary)" }}>
                        {" — "}{run?.run_id} &middot; {stats.total_records} records &middot;{" "}
                        {stats.exceptions > 0
                          ? `${stats.exceptions} exceptions require attention`
                          : "All records reconciled"}
                      </span>
                    </span>
                  </div>
                  <span className="badge" style={{
                    color: healthLabel.color,
                    borderColor: `color-mix(in srgb, ${healthLabel.color} 30%, transparent)`,
                    background: `color-mix(in srgb, ${healthLabel.color} 10%, transparent)`,
                  }}>
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
