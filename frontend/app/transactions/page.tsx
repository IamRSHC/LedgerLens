"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import { getOrders } from "@/lib/api";

export default function Transactions() {
  const [orders, setOrders] = useState<any[]>([]);
  useEffect(() => { getOrders().then(r => setOrders(r.data)); }, []);
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Topbar />
        <main className="flex-1 p-6">
          <h1 className="text-xl font-semibold mb-4">Transactions</h1>
          <div className="glass">
            <div className="grid text-xs font-medium uppercase tracking-widest px-4 py-2.5 border-b"
                 style={{ gridTemplateColumns:"2fr 1fr 1fr 1fr 1fr", borderColor:"var(--border)", color:"var(--muted)" }}>
              <span>Order ID</span><span>Amount</span><span>Method</span><span>Status</span><span>Date</span>
            </div>
            <div className="divide-y max-h-[75vh] overflow-y-auto" style={{ divideColor:"var(--border)" }}>
              {orders.map((o, i) => (
                <div key={i} className="grid items-center px-4 py-2.5 text-sm hover:bg-white/[0.02]"
                     style={{ gridTemplateColumns:"2fr 1fr 1fr 1fr 1fr" }}>
                  <span className="font-mono text-xs">{o.order_id}</span>
                  <span className="font-medium">₹{o.amount?.toLocaleString("en-IN")}</span>
                  <span className="text-xs" style={{color:"var(--muted)"}}>{o.payment_method}</span>
                  <span className="text-xs text-green-400">{o.status}</span>
                  <span className="text-xs" style={{color:"var(--muted)"}}>{o.created_at?.slice(0,10)}</span>
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
