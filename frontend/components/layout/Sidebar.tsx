"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, ArrowLeftRight, AlertTriangle, ScrollText, Hexagon } from "lucide-react";

const NAV = [
  { href: "/dashboard",    icon: LayoutDashboard, label: "Dashboard" },
  { href: "/transactions", icon: ArrowLeftRight,   label: "Transactions" },
  { href: "/exceptions",   icon: AlertTriangle,    label: "Exceptions" },
  { href: "/audit",        icon: ScrollText,       label: "Audit Trail" },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside style={{
      width: 232, minHeight: "100vh", display: "flex", flexDirection: "column",
      padding: "20px 12px",
      background: "var(--glass-surface-floating)",
      backdropFilter: "blur(28px) saturate(160%)",
      WebkitBackdropFilter: "blur(28px) saturate(160%)",
      borderRight: "1px solid var(--glass-border)",
      boxShadow: "inset -1px 0 0 var(--glass-highlight)",
      position: "sticky", top: 0, zIndex: 20,
    }}>
      <Link href="/" style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "0 10px", marginBottom: 32, textDecoration: "none", color: "inherit",
      }}>
        <div style={{
          width: 34, height: 34, borderRadius: 10,
          background: "var(--accent-muted)",
          border: "1px solid var(--accent-border)",
          display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: "0 0 16px rgba(20,184,166,0.12), inset 0 1px 0 rgba(255,255,255,0.06)",
        }}>
          <Hexagon size={16} style={{ color: "var(--accent)" }} />
        </div>
        <span style={{
          fontWeight: 700, fontSize: 16, letterSpacing: "-0.3px",
          fontFamily: "var(--font-display)", color: "var(--text)",
        }}>
          LedgerLens
        </span>
      </Link>

      <p className="label-mono" style={{ padding: "0 12px", marginBottom: 8 }}>
        Navigation
      </p>

      <nav style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = path.startsWith(href);
          return (
            <Link key={href} href={href} style={{
              display: "flex", alignItems: "center", gap: 10, padding: "10px 12px",
              borderRadius: 8, fontSize: 14, fontWeight: active ? 600 : 400,
              textDecoration: "none", transition: "all 0.18s ease",
              background: active ? "var(--accent-muted)" : "transparent",
              color: active ? "var(--accent)" : "var(--text-secondary)",
              borderLeft: active ? "2px solid var(--accent)" : "2px solid transparent",
              boxShadow: active ? "0 0 12px var(--glow-accent), inset 0 1px 0 rgba(20,184,166,0.06)" : "none",
            }}>
              <Icon size={18} strokeWidth={active ? 2.2 : 1.8} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div style={{
        padding: "14px 12px", borderTop: "1px solid var(--glass-border)",
        fontSize: 11, color: "var(--text-muted)",
      }}>
        <p style={{ fontWeight: 600, color: "var(--text-secondary)", marginBottom: 2 }}>
          LedgerLens v1.0
        </p>
        <p>Razorpay Buildathon 2026</p>
      </div>
    </aside>
  );
}
