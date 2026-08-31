"use client";
import { useTheme } from "next-themes";
import { Sun, Moon, Play } from "lucide-react";
import { useEffect, useState } from "react";

interface Props {
  runId?: string;
  runDate?: string;
  onRun?: () => void;
  running?: boolean;
}

export default function Topbar({ runId, runDate, onRun, running }: Props) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const fmtDate = (s?: string) => s
    ? new Date(s).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <header style={{
      height: 56, display: "flex", alignItems: "center",
      justifyContent: "space-between", padding: "0 24px",
      background: "var(--glass-surface-floating)",
      backdropFilter: "blur(28px) saturate(160%)",
      WebkitBackdropFilter: "blur(28px) saturate(160%)",
      borderBottom: "1px solid var(--glass-border)",
      boxShadow: "inset 0 -1px 0 var(--glass-highlight), 0 4px 20px rgba(0,0,0,0.10)",
      position: "sticky", top: 0, zIndex: 10,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 13 }}>
        {runId && (
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600,
            padding: "4px 10px", borderRadius: 7,
            background: "var(--accent-muted)", color: "var(--accent)",
            border: "1px solid var(--accent-border)",
          }}>
            {runId}
          </span>
        )}
        {runDate && (
          <span style={{ color: "var(--text-muted)", fontSize: 12 }}>
            Last run: {fmtDate(runDate)}
          </span>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {mounted && (
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label="Toggle theme"
            style={{
              width: 36, height: 36, borderRadius: 9,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "var(--glass-surface)", border: "1px solid var(--glass-border)",
              color: "var(--text-secondary)", cursor: "pointer",
              transition: "all 0.18s ease",
              boxShadow: "inset 0 1px 0 var(--glass-highlight)",
            }}
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        )}

        {onRun && (
          <button onClick={onRun} disabled={running} className="btn-primary">
            <Play size={14} />
            {running ? "Running..." : "Run Batch"}
          </button>
        )}
      </div>
    </header>
  );
}
