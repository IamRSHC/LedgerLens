"use client";
import { DashboardStats } from "@/lib/api";
import { fmtINR, fmtPct } from "@/lib/utils";
import { FileText, CheckCircle2, AlertTriangle, Percent, IndianRupee } from "lucide-react";

interface CardProps {
  label: string;
  value: string;
  sub?: string;
  color: string;
  icon: React.ReactNode;
  delay: number;
}

function KPICard({ label, value, sub, color, icon, delay }: CardProps) {
  return (
    <div className="card card-hover animate-fade-in" style={{
      padding: "20px", borderTop: `2px solid ${color}`,
      animationDelay: `${delay * 0.06}s`,
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <p className="label-mono">{label}</p>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          display: "flex", alignItems: "center", justifyContent: "center",
          background: `color-mix(in srgb, ${color} 12%, transparent)`,
          color: color,
        }}>
          {icon}
        </div>
      </div>
      <p className="stat-value" style={{ fontSize: 28, color, marginBottom: sub ? 4 : 0 }}>{value}</p>
      {sub && <p style={{ fontSize: 12, color: "var(--text-muted)" }}>{sub}</p>}
    </div>
  );
}

export default function KPICards({ stats }: { stats: DashboardStats }) {
  const rateColor = stats.match_rate >= 90 ? "var(--success)"
    : stats.match_rate >= 75 ? "var(--warning)" : "var(--danger)";

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 16 }}>
      <KPICard label="Total Records" value={stats.total_records.toLocaleString("en-IN")}
               sub="in current batch" color="var(--text-secondary)"
               icon={<FileText size={16} />} delay={0} />
      <KPICard label="Matched" value={stats.matched.toLocaleString("en-IN")}
               sub={`${stats.auto_resolved} auto-resolved`}
               color="var(--success)" icon={<CheckCircle2 size={16} />} delay={1} />
      <KPICard label="Exceptions" value={stats.exceptions.toLocaleString("en-IN")}
               sub={`${stats.pending_review} pending review`}
               color={stats.exceptions > 10 ? "var(--danger)" : "var(--warning)"}
               icon={<AlertTriangle size={16} />} delay={2} />
      <KPICard label="Match Rate" value={fmtPct(stats.match_rate)}
               color={rateColor} icon={<Percent size={16} />} delay={3} />
      <KPICard label="Amount Reconciled" value={fmtINR(stats.amount_reconciled)}
               sub="successfully matched" color="var(--accent)"
               icon={<IndianRupee size={16} />} delay={4} />
    </div>
  );
}
