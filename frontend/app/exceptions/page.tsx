"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import ExceptionTable from "@/components/dashboard/ExceptionTable";
import { getExceptions, Exception } from "@/lib/api";

export default function Exceptions() {
  const [excs, setExcs] = useState<Exception[]>([]);
  const load = async () => { const r = await getExceptions(); setExcs(r.data); };
  useEffect(() => { load(); }, []);

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
            Exception Queue
          </h1>
          <ExceptionTable exceptions={excs} onRefresh={load} />
        </main>
      </div>
    </div>
  );
}
