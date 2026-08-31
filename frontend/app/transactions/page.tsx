"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import { getOrders } from "@/lib/api";
import { fmtDate } from "@/lib/utils";

export default function Transactions() {
  const [orders, setOrders] = useState<any[]>([]);
  useEffect(() => { getOrders().then(r => setOrders(r.data)); }, []);

  const gridCols = "2fr 1fr 1fr 1fr 1fr";

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
            Transactions
          </h1>
          <div className="card" style={{ overflow: "hidden" }}>
            <div style={{
              display: "grid", gridTemplateColumns: gridCols, alignItems: "center",
              padding: "10px 20px", borderBottom: "1px solid var(--border)",
            }}>
              {["Order ID", "Amount", "Method", "Status", "Date"].map(h => (
                <span key={h} className="label-mono">{h}</span>
              ))}
            </div>
            <div style={{ maxHeight: "75vh", overflowY: "auto" }}>
              {orders.map((o, i) => (
                <div key={i} style={{
                  display: "grid", gridTemplateColumns: gridCols, alignItems: "center",
                  padding: "10px 20px", fontSize: 13,
                  borderBottom: "1px solid var(--border)",
                  transition: "background 0.1s ease",
                }}
                  onMouseEnter={e => (e.currentTarget.style.background = "var(--row-hover)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-secondary)" }}>
                    {o.order_id}
                  </span>
                  <span className="font-mono" style={{ fontWeight: 600, fontSize: 13 }}>
                    ₹{o.amount?.toLocaleString("en-IN")}
                  </span>
                  <span style={{ color: "var(--text-muted)", fontSize: 12 }}>{o.payment_method}</span>
                  <span className="badge badge-success" style={{ justifySelf: "start" }}>{o.status}</span>
                  <span style={{ color: "var(--text-muted)", fontSize: 12, fontFamily: "var(--font-mono)" }}>
                    {o.created_at?.slice(0, 10)}
                  </span>
                </div>
              ))}
              {orders.length === 0 && (
                <p style={{ padding: "40px 20px", textAlign: "center", color: "var(--text-muted)", fontSize: 14 }}>
                  No transactions yet. Run a batch first.
                </p>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
