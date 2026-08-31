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
      padding: "20px",
      animationDelay: `${delay * 0.06}s`,
      position: "relative",
      overflow: "hidden",
    }}>
      {/* accent gradient top edge */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, ${color}, transparent)`,
        opacity: 0.6,
      }} />

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <p className="label-mono">{label}</p>
        <div style={{
          width: 36, height: 36, borderRadius: 11,
          display: "flex", alignItems: "center", justifyContent: "center",
          background: `color-mix(in srgb, ${color} 10%, transparent)`,
          border: `1px solid color-mix(in srgb, ${color} 18%, transparent)`,
          color: color,
          boxShadow: `inset 0 1px 0 rgba(255,255,255,0.04), 0 0 12px color-mix(in srgb, ${color} 8%, transparent)`,
        }}>
          {icon}
        </div>
      </div>
      <p className="stat-value" style={{ fontSize: 30, color, marginBottom: sub ? 4 : 0 }}>{value}</p>
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
