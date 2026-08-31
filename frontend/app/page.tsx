"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { runReconciliation } from "@/lib/api";
import {
  Hexagon, Play, ArrowRight,
  Sun, Moon, CheckCircle, Clock, AlertTriangle, Shield,
} from "lucide-react";

const STATS = [
  { value: "94.7%", label: "Auto match rate", Icon: CheckCircle },
  { value: "~2s",   label: "Per 1,000 records", Icon: Clock },
  { value: "7",     label: "Exception types", Icon: AlertTriangle },
  { value: "100%",  label: "Auditable", Icon: Shield },
];

export default function Landing() {
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  async function startDemo() {
    setLoading(true); setError("");
    try {
      await runReconciliation();
      router.push("/dashboard");
    } catch {
      setError("Backend not reachable — start the FastAPI server first.");
      setLoading(false);
    }
  }

  return (
    <main className="page-bg" style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", padding: "24px",
      fontFamily: "var(--font-body)", color: "var(--text)",
      position: "relative",
    }}>
      {/* Theme toggle */}
      {mounted && (
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label="Toggle theme"
          style={{
            position: "absolute", top: 20, right: 24,
            width: 40, height: 40, borderRadius: 10,
            display: "flex", alignItems: "center", justifyContent: "center",
            background: "var(--glass-surface)", border: "1px solid var(--glass-border)",
            color: "var(--text-secondary)", cursor: "pointer",
            transition: "all 0.18s ease",
            boxShadow: "inset 0 1px 0 var(--glass-highlight)",
            backdropFilter: "var(--glass-blur)",
            WebkitBackdropFilter: "var(--glass-blur)",
          }}
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      )}

      {/* Buildathon badge */}
      <div className="badge badge-accent" style={{
        marginBottom: 28, padding: "6px 16px", fontSize: 12,
        fontFamily: "var(--font-mono)",
      }}>
        <span style={{
          width: 6, height: 6, borderRadius: "50%", background: "var(--accent)",
          display: "inline-block",
        }} />
        Razorpay AI Buildathon 2026 — Track 4
      </div>

      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 36 }}>
        <div style={{
          width: 52, height: 52, borderRadius: 14,
          display: "flex", alignItems: "center", justifyContent: "center",
          background: "var(--accent-muted)", border: "1px solid var(--accent-border)",
          boxShadow: "0 0 24px var(--glow-accent), inset 0 1px 0 rgba(255,255,255,0.06)",
        }}>
          <Hexagon size={24} style={{ color: "var(--accent)" }} />
        </div>
        <span style={{
          fontSize: 30, fontWeight: 700, letterSpacing: "-0.5px",
          fontFamily: "var(--font-display)",
        }}>
          LedgerLens
        </span>
      </div>

      {/* Headline */}
      <h1 style={{
        fontSize: 52, fontWeight: 700, textAlign: "center", lineHeight: 1.1,
        marginBottom: 16, letterSpacing: "-1.5px", maxWidth: 600,
        fontFamily: "var(--font-display)",
      }}>
        AI Finance Controller
      </h1>
      <p style={{
        fontSize: 18, textAlign: "center", marginBottom: 8,
        color: "var(--text-secondary)", fontWeight: 400,
      }}>
        Reconcile. Investigate. Resolve.
      </p>
      <p style={{
        fontSize: 14, textAlign: "center", maxWidth: 480,
        color: "var(--text-muted)", lineHeight: 1.7, marginBottom: 48,
      }}>
        Deterministic reconciliation engine paired with Groq LLaMA AI investigation.
        Every exception investigated, every decision audited.
      </p>

      {/* Stat strip — glass surface */}
      <div style={{
        display: "flex", gap: 0, marginBottom: 48, flexWrap: "wrap", justifyContent: "center",
        background: "var(--glass-surface)",
        backdropFilter: "var(--glass-blur)",
        WebkitBackdropFilter: "var(--glass-blur)",
        border: "1px solid var(--glass-border)",
        borderRadius: 14, overflow: "hidden",
        boxShadow: "inset 0 1px 0 var(--glass-highlight), var(--glass-shadow)",
      }}>
        {STATS.map(({ value, label, Icon }, i) => (
          <div key={label} style={{
            padding: "20px 30px", textAlign: "center", position: "relative",
            borderRight: i < STATS.length - 1 ? "1px solid var(--glass-border)" : "none",
          }}>
            <div style={{
              fontSize: 24, fontWeight: 700, color: "var(--accent)",
              fontFamily: "var(--font-mono)", fontVariantNumeric: "tabular-nums",
              marginBottom: 4,
            }}>
              {value}
            </div>
            <div style={{
              fontSize: 11, color: "var(--text-muted)",
              display: "flex", alignItems: "center", gap: 4, justifyContent: "center",
            }}>
              <Icon size={11} />
              {label}
            </div>
          </div>
        ))}
      </div>

      {/* CTAs */}
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <button onClick={startDemo} disabled={loading} className="btn-primary" style={{
          padding: "14px 28px", fontSize: 15,
          opacity: loading ? 0.6 : 1,
        }}>
          <Play size={16} />
          {loading ? "Starting..." : "Try Demo"}
        </button>
        <button onClick={() => router.push("/dashboard")} className="btn-secondary" style={{
          padding: "14px 28px", fontSize: 15,
        }}>
          Open Dashboard
          <ArrowRight size={16} />
        </button>
      </div>

      {error && (
        <div style={{
          marginTop: 8, background: "var(--danger-muted)",
          border: "1px solid rgba(239,68,68,0.25)",
          borderRadius: 8, padding: "10px 18px", fontSize: 13,
          color: "var(--danger)", maxWidth: 460, textAlign: "center",
          display: "flex", alignItems: "center", gap: 8, justifyContent: "center",
        }}>
          <AlertTriangle size={14} />
          {error}
        </div>
      )}
    </main>
  );
}
