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
    <aside className="glass" style={{
      width: 232, minHeight: "100vh", display: "flex", flexDirection: "column",
      padding: "20px 12px", borderRight: "1px solid var(--border)",
      position: "sticky", top: 0, zIndex: 20,
    }}>
      <Link href="/" style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "0 10px", marginBottom: 32, textDecoration: "none", color: "inherit",
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: "var(--accent-muted)", border: "1px solid var(--accent-border)",
          display: "flex", alignItems: "center", justifyContent: "center",
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
              textDecoration: "none", transition: "all 0.15s ease",
              background: active ? "var(--accent-muted)" : "transparent",
              color: active ? "var(--accent)" : "var(--text-secondary)",
              borderLeft: active ? "3px solid var(--accent)" : "3px solid transparent",
            }}>
              <Icon size={18} strokeWidth={active ? 2.2 : 1.8} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div style={{
        padding: "14px 12px", borderTop: "1px solid var(--border)",
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
