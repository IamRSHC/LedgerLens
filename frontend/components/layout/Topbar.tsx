"use client";

interface Props {
  runId?: string;
  runDate?: string;
  onRun?: () => void;
  running?: boolean;
}

export default function Topbar({ runId, runDate, onRun, running }: Props) {
  const fmtDate = (s?: string) => s
    ? new Date(s).toLocaleString("en-IN", { day:"2-digit", month:"short", hour:"2-digit", minute:"2-digit" })
    : null;

  return (
    <header style={{ height: 56, display: "flex", alignItems: "center",
      justifyContent: "space-between", padding: "0 24px",
      borderBottom: "1px solid var(--line)",
      background: "var(--panel)" }}>

      <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 13 }}>
        {runId && (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 11,
            background: "var(--accent-muted)", border: "1px solid rgba(76,141,255,0.2)",
            color: "var(--accent)", padding: "3px 8px", borderRadius: 6 }}>
            {runId}
          </span>
        )}
        {runDate && (
          <span style={{ color: "var(--text-dim)", fontSize: 12 }}>
            Last run: {fmtDate(runDate)}
          </span>
        )}
      </div>

      <button onClick={onRun} disabled={running} style={{
        padding: "8px 18px", borderRadius: 8, fontWeight: 600, fontSize: 13,
        background: running ? "var(--accent-muted)" : "var(--accent)",
        color: running ? "var(--accent)" : "#fff", border: "none",
        cursor: running ? "not-allowed" : "pointer", transition: "opacity 0.15s",
      }}>
        {running ? "Running batch…" : "+ Run New Batch"}
      </button>
    </header>
  );
}
