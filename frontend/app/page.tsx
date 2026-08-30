"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { runReconciliation } from "@/lib/api";

export default function Landing() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function startDemo() {
    setLoading(true); setError("");
    try {
      await runReconciliation();
      router.push("/dashboard");
    } catch {
      setError("Backend not reachable at localhost:8000 — start the FastAPI server first, then try again.");
      setLoading(false);
    }
  }

  return (
    <main style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", padding: "24px",
      background: "var(--ink)",
      fontFamily: "var(--font-body)", color: "var(--text)",
    }}>

      {/* Badge */}
      <div style={{ marginBottom: 24, display: "flex", alignItems: "center", gap: 8,
        background: "var(--accent-muted)", border: "1px solid rgba(76,141,255,0.25)",
        borderRadius: 100, padding: "5px 14px", fontSize: 12, color: "var(--accent)",
        fontFamily: "var(--font-mono)" }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent)",
          display: "inline-block" }} />
        Razorpay AI Buildathon 2026 — Track 4
      </div>

      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 32 }}>
        <div style={{ width: 44, height: 44, borderRadius: 10, display: "flex",
          alignItems: "center", justifyContent: "center", fontSize: 20,
          background: "var(--panel)", border: "1px solid var(--accent)", color: "var(--accent)" }}>⬡</div>
        <span style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-0.4px", fontFamily: "var(--font-display)" }}>LedgerLens</span>
      </div>

      {/* Headline */}
      <h1 style={{ fontSize: 52, fontWeight: 700, textAlign: "center", lineHeight: 1.12,
        marginBottom: 20, letterSpacing: "-1px", maxWidth: 720,
        fontFamily: "var(--font-display)", color: "var(--text)" }}>
        AI Finance Controller
      </h1>
      <p style={{ fontSize: 18, textAlign: "center", marginBottom: 8, color: "var(--text-muted)", fontWeight: 400 }}>
        Reconcile. Investigate. Resolve.
      </p>
      <p style={{ fontSize: 14, textAlign: "center", maxWidth: 500, color: "var(--text-dim)",
        lineHeight: 1.7, marginBottom: 48 }}>
        Deterministic reconciliation engine + Groq LLaMA AI investigation.
        Every exception investigated, every decision audited.
      </p>

      {/* Stat pills */}
      <div style={{ display: "flex", gap: 12, marginBottom: 48, flexWrap: "wrap", justifyContent: "center" }}>
        {[
          ["94.7%", "Auto match rate"],
          ["~2s", "Per 1,000 records"],
          ["7", "Exception types detected"],
          ["100%", "Auditable decisions"],
        ].map(([v, l]) => (
          <div key={l} style={{ background: "var(--panel)", border: "1px solid var(--line)",
            borderRadius: 10, padding: "12px 20px", textAlign: "center" }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: "var(--accent)", fontFamily: "var(--font-mono)" }}>{v}</div>
            <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 2 }}>{l}</div>
          </div>
        ))}
      </div>

      {/* CTAs */}
      <div style={{ display: "flex", gap: 12 }}>
        <button onClick={startDemo} disabled={loading} style={{
          padding: "13px 28px", borderRadius: 8, fontWeight: 600, fontSize: 14,
          background: "var(--accent)", color: "#fff",
          border: "none", cursor: loading ? "not-allowed" : "pointer",
          opacity: loading ? 0.7 : 1,
          transition: "opacity 0.15s",
        }}>
          {loading ? "Starting demo…" : "▶  Try Demo"}
        </button>
        <button onClick={() => router.push("/dashboard")} style={{
          padding: "13px 28px", borderRadius: 8, fontWeight: 600, fontSize: 14,
          background: "var(--panel)", color: "var(--text)",
          border: "1px solid var(--line)", cursor: "pointer",
          transition: "border-color 0.15s",
        }}>
          Open Dashboard
        </button>
      </div>

      {error && (
        <div style={{ marginTop: 20, background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
          borderRadius: 8, padding: "10px 18px", fontSize: 13, color: "#fca5a5", maxWidth: 460, textAlign: "center" }}>
          ⚠ {error}
        </div>
      )}

      {/* Architecture diagram preview */}
      <div style={{ marginTop: 72, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
        <p style={{ fontSize: 12, color: "var(--text-dim)", marginBottom: 16, textTransform: "uppercase",
          letterSpacing: "0.1em", fontFamily: "var(--font-mono)" }}>How it works</p>
        <div style={{ display: "flex", alignItems: "center", gap: 0, flexWrap: "wrap", justifyContent: "center" }}>
          {[
            { label: "Financial Data", sub: "Orders · Settlements · Bank", color: "var(--accent)" },
            null,
            { label: "Recon Engine", sub: "Exact + fuzzy matching", color: "var(--green)" },
            null,
            { label: "AI Investigator", sub: "Groq + tool calling", color: "var(--amber)" },
            null,
            { label: "Audit Trail", sub: "Every decision logged", color: "var(--accent)" },
          ].map((item, i) =>
            item === null ? (
              <div key={i} style={{ color: "var(--text-dim)", fontSize: 18, padding: "0 4px" }}>→</div>
            ) : (
              <div key={i} style={{ background: "var(--panel)", border: `1px solid var(--line)`,
                borderRadius: 8, padding: "10px 16px", textAlign: "center",
                borderTop: `2px solid ${item.color}` }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: item.color }}>{item.label}</div>
                <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 2 }}>{item.sub}</div>
              </div>
            )
          )}
        </div>
      </div>

      <p style={{ marginTop: 64, fontSize: 11, color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>
        FastAPI · Next.js · Groq LLaMA 3.3 70B · SQLite → Supabase PostgreSQL
      </p>
    </main>
  );
}
