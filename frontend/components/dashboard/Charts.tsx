"use client";
import { DashboardStats } from "@/lib/api";
import { excTypeLabel } from "@/lib/utils";
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";

const COLORS = ["#EF4444","#F5A524","#4C8DFF","#2FB380","#8792A8","#F5A524"];

const ttStyle = {
  background: "#182238", border: "1px solid #24304A",
  borderRadius: 8, fontSize: 12, color: "#E7ECF5",
};

const card = (extra?: object): React.CSSProperties => ({
  background: "var(--panel)",
  border: "1px solid var(--line)", borderRadius: 12,
  padding: "18px 20px", ...extra,
});

export default function Charts({ stats }: { stats: DashboardStats }) {
  const excData = Object.entries(stats.exception_breakdown).map(([k, v]) => ({
    name: excTypeLabel[k] ?? k, value: v,
  }));

  const sevData = [
    { name: "Critical", value: stats.severity_breakdown?.critical ?? 0, fill: "#EF4444" },
    { name: "Warning",  value: stats.severity_breakdown?.warning  ?? 0, fill: "#F5A524" },
    { name: "Low",      value: stats.severity_breakdown?.low      ?? 0, fill: "#4C8DFF" },
  ];

  const resData = [
    { name: "Matched",       value: stats.matched,        fill: "#2FB380" },
    { name: "Auto-Resolved", value: stats.auto_resolved,  fill: "#4C8DFF" },
    { name: "Pending",       value: stats.pending_review, fill: "#F5A524" },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>

      {/* Exception type breakdown */}
      <div style={card()}>
        <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: "#8792A8" }}>Exception Types</h3>
        {excData.length === 0 ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center",
            height: 160, color: "#5C6883", fontSize: 13 }}>No exceptions — all clear 🎉</div>
        ) : (
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={excData} cx="50%" cy="50%" innerRadius={40} outerRadius={65}
                   dataKey="value" paddingAngle={3}>
                {excData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={ttStyle} />
            </PieChart>
          </ResponsiveContainer>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
          {excData.map((d, i) => (
            <div key={d.name} style={{ display: "flex", justifyContent: "space-between",
              alignItems: "center", fontSize: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%",
                  background: COLORS[i % COLORS.length] }} />
                <span style={{ color: "#8792A8" }}>{d.name}</span>
              </div>
              <span style={{ fontWeight: 600 }}>{d.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Severity distribution */}
      <div style={card()}>
        <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: "#8792A8" }}>Severity</h3>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={sevData} barSize={36}>
            <XAxis dataKey="name" tick={{ fill: "#5C6883", fontSize: 11 }}
                   axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#5C6883", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={ttStyle} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {sevData.map((d, i) => <Cell key={i} fill={d.fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
          {sevData.map(d => (
            <div key={d.name} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: d.fill }} />
              <span style={{ color: "#8792A8" }}>{d.name}</span>
              <span style={{ fontWeight: 600 }}>{d.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Resolution summary */}
      <div style={card()}>
        <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: "#8792A8" }}>Resolution</h3>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={resData} barSize={36}>
            <XAxis dataKey="name" tick={{ fill: "#5C6883", fontSize: 11 }}
                   axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#5C6883", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={ttStyle} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {resData.map((d, i) => <Cell key={i} fill={d.fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div style={{ marginTop: 12, padding: "10px 14px", borderRadius: 8,
          background: "rgba(47,179,128,0.08)", border: "1px solid rgba(47,179,128,0.2)",
          fontSize: 12, color: "#8792A8" }}>
          <span style={{ color: "#2FB380", fontWeight: 600 }}>
            {stats.auto_resolved} exceptions
          </span>
          {" "}auto-resolved by AI · {stats.pending_review} need your review
        </div>
      </div>
    </div>
  );
}
