"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/dashboard",    icon: "▦",  label: "Dashboard"   },
  { href: "/transactions", icon: "⇄",  label: "Transactions" },
  { href: "/exceptions",   icon: "⚠",  label: "Exceptions"  },
  { href: "/audit",        icon: "≡",  label: "Audit Trail" },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside style={{ width: 220, minHeight: "100vh", display: "flex", flexDirection: "column",
      padding: "24px 12px", borderRight: "1px solid var(--line)",
      background: "var(--panel)" }}>

      {/* Logo */}
      <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10,
        padding: "0 10px", marginBottom: 32, textDecoration: "none", color: "inherit" }}>
        <div style={{ width: 30, height: 30, borderRadius: 8,
          background: "var(--panel-raised)", border: "1px solid var(--accent)", color: "var(--accent)",
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>⬡</div>
        <span style={{ fontWeight: 700, fontSize: 15, letterSpacing: "-0.3px", fontFamily: "var(--font-display)" }}>LedgerLens</span>
      </Link>

      {/* Label */}
      <p style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", color: "var(--text-dim)",
        textTransform: "uppercase", padding: "0 10px", marginBottom: 6, fontFamily: "var(--font-mono)" }}>Navigation</p>

      {/* Nav items */}
      <nav style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
        {NAV.map(({ href, icon, label }) => {
          const active = path.startsWith(href);
          return (
            <Link key={href} href={href} style={{
              display: "flex", alignItems: "center", gap: 10, padding: "9px 12px",
              borderRadius: 8, fontSize: 14, fontWeight: active ? 600 : 400,
              textDecoration: "none", transition: "all 0.15s",
              background: active ? "var(--accent-muted)" : "transparent",
              color: active ? "var(--accent)" : "var(--text-muted)",
              border: active ? "1px solid rgba(76,141,255,0.25)" : "1px solid transparent",
            }}>
              <span style={{ fontSize: 15, width: 18, textAlign: "center" }}>{icon}</span>
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div style={{ padding: "12px 10px", borderTop: "1px solid var(--line)",
        fontSize: 11, color: "var(--text-dim)" }}>
        <p style={{ fontWeight: 600, color: "var(--text-muted)" }}>LedgerLens v1.0</p>
        <p style={{ marginTop: 2 }}>Razorpay Buildathon · Track 4</p>
      </div>
    </aside>
  );
}
