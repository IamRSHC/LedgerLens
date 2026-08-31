"use client";
import { DashboardStats } from "@/lib/api";
import { excTypeLabel } from "@/lib/utils";
import { Sparkles } from "lucide-react";
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer,
} from "recharts";

const PIE_COLORS = ["#EF4444", "#F59E0B", "#3B82F6", "#10B981", "#94A3B8", "#14B8A6"];

function ChartCard({ title, children, delay = 0 }: { title: string; children: React.ReactNode; delay?: number }) {
  return (
    <div className="card animate-fade-in" style={{ padding: "20px", animationDelay: `${delay * 0.06}s` }}>
      <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: "var(--text-secondary)" }}>{title}</h3>
      {children}
    </div>
  );
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "var(--bg-card)", border: "1px solid var(--border-strong)",
      borderRadius: 8, padding: "8px 12px", fontSize: 12, color: "var(--text)",
      boxShadow: "var(--shadow-elevated)",
    }}>
      <p style={{ fontWeight: 600, marginBottom: 2 }}>{label || payload[0].name}</p>
      <p style={{ color: "var(--text-secondary)" }}>{payload[0].value}</p>
    </div>
  );
}

export default function Charts({ stats }: { stats: DashboardStats }) {
  const excData = Object.entries(stats.exception_breakdown).map(([k, v]) => ({
    name: excTypeLabel[k] ?? k, value: v,
  }));

  const sevData = [
    { name: "Critical", value: stats.severity_breakdown?.critical ?? 0, fill: "var(--danger)" },
    { name: "Warning",  value: stats.severity_breakdown?.warning  ?? 0, fill: "var(--warning)" },
    { name: "Low",      value: stats.severity_breakdown?.low      ?? 0, fill: "var(--info)" },
  ];

  const resData = [
    { name: "Matched",       value: stats.matched,        fill: "var(--success)" },
    { name: "Auto-Resolved", value: stats.auto_resolved,  fill: "var(--accent)" },
    { name: "Pending",       value: stats.pending_review, fill: "var(--warning)" },
  ];

  const axisStyle = { fill: "var(--text-muted)", fontSize: 11 };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
      <ChartCard title="Exception Types" delay={5}>
        {excData.length === 0 ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center",
            height: 160, color: "var(--text-muted)", fontSize: 13 }}>No exceptions</div>
        ) : (
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={excData} cx="50%" cy="50%" innerRadius={40} outerRadius={65}
                   dataKey="value" paddingAngle={3} stroke="none">
                {excData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
          {excData.map((d, i) => (
            <div key={d.name} style={{ display: "flex", justifyContent: "space-between",
              alignItems: "center", fontSize: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%",
                  background: PIE_COLORS[i % PIE_COLORS.length] }} />
                <span style={{ color: "var(--text-secondary)" }}>{d.name}</span>
              </div>
              <span className="font-mono" style={{ fontWeight: 600, fontSize: 12 }}>{d.value}</span>
            </div>
          ))}
        </div>
      </ChartCard>

      <ChartCard title="Severity" delay={6}>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={sevData} barSize={36}>
            <XAxis dataKey="name" tick={axisStyle} axisLine={false} tickLine={false} />
            <YAxis tick={axisStyle} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip />} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {sevData.map((d, i) => <Cell key={i} fill={d.fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
          {sevData.map(d => (
            <div key={d.name} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: d.fill }} />
              <span style={{ color: "var(--text-secondary)" }}>{d.name}</span>
              <span className="font-mono" style={{ fontWeight: 600, fontSize: 12 }}>{d.value}</span>
            </div>
          ))}
        </div>
      </ChartCard>

      <ChartCard title="Resolution" delay={7}>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={resData} barSize={36}>
            <XAxis dataKey="name" tick={axisStyle} axisLine={false} tickLine={false} />
            <YAxis tick={axisStyle} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip />} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {resData.map((d, i) => <Cell key={i} fill={d.fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div style={{
          marginTop: 12, padding: "10px 14px", borderRadius: 8,
          background: "var(--success-muted)", border: "1px solid rgba(16,185,129,0.2)",
          fontSize: 12, color: "var(--text-secondary)",
          display: "flex", alignItems: "center", gap: 6,
        }}>
          <Sparkles size={14} style={{ color: "var(--accent)" }} />
          <span>
            <span style={{ color: "var(--success)", fontWeight: 600 }}>
              {stats.auto_resolved} exceptions
            </span>
            {" "}auto-resolved by AI
          </span>
          <span style={{ color: "var(--text-muted)" }}>
            &middot; {stats.pending_review} need review
          </span>
        </div>
      </ChartCard>
    </div>
  );
}
