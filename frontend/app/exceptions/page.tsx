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
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Topbar />
        <main className="flex-1 p-6">
          <h1 className="text-xl font-semibold mb-4">Exception Queue</h1>
          <ExceptionTable exceptions={excs} onRefresh={load} />
        </main>
      </div>
    </div>
  );
}
