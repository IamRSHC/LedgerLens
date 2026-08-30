"use client";
import { DashboardStats } from "@/lib/api";
import { fmtINR, fmtPct } from "@/lib/utils";

interface CardProps {
  label: string; value: string; sub?: string;
  color?: string; glow?: string; icon?: string;
}

function KPICard({ label, value, sub, color = "var(--text)", icon }: CardProps) {
  return (
    <div style={{
      background: "var(--panel)",
      border: `1px solid var(--line)`,
      borderTop: `2px solid ${color}`,
      borderRadius: 12, padding: "18px 20px",
      display: "flex", flexDirection: "column", gap: 6,
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <p className="stat-label">{label}</p>
        {icon && <span style={{ fontSize: 16, opacity: 0.7 }}>{icon}</span>}
      </div>
      <p className="stat-value" style={{ fontSize: 28, color }}>{value}</p>
      {sub && <p style={{ fontSize: 12, color: "var(--text-dim)" }}>{sub}</p>}
    </div>
  );
}

export default function KPICards({ stats }: { stats: DashboardStats }) {
  const rateColor = stats.match_rate >= 90 ? "var(--green)" : stats.match_rate >= 75 ? "var(--amber)" : "var(--red)";
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14 }}>
      <KPICard label="Total Records"     value={stats.total_records.toLocaleString("en-IN")}
               sub="in current batch"    color="var(--text)" icon="📄" />
      <KPICard label="Matched"           value={stats.matched.toLocaleString("en-IN")}
               sub={`${stats.auto_resolved} auto-resolved`}
               color="var(--green)" icon="✓" />
      <KPICard label="Exceptions"        value={stats.exceptions.toLocaleString("en-IN")}
               sub={`${stats.pending_review} pending review`}
               color={stats.exceptions > 10 ? "var(--red)" : "var(--amber)"} icon="⚠" />
      <KPICard label="Match Rate"        value={fmtPct(stats.match_rate)}
               color={rateColor} icon="%" />
      <KPICard label="Amount Reconciled" value={fmtINR(stats.amount_reconciled)}
               sub="successfully matched" color="var(--accent)" icon="₹" />
    </div>
  );
}
