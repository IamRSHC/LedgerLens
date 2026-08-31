"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, ArrowLeftRight, AlertTriangle, ScrollText,
  Hexagon, PanelLeftClose, PanelLeft,
} from "lucide-react";

const NAV = [
  { href: "/dashboard",    icon: LayoutDashboard, label: "Dashboard" },
  { href: "/transactions", icon: ArrowLeftRight,   label: "Transactions" },
  { href: "/exceptions",   icon: AlertTriangle,    label: "Exceptions" },
  { href: "/audit",        icon: ScrollText,       label: "Audit Trail" },
];

const STORAGE_KEY = "ledgerlens-sidebar-collapsed";
const WIDTH_EXPANDED = 232;
const WIDTH_COLLAPSED = 68;

function NavTooltip({ label, show }: { label: string; show: boolean }) {
  if (!show) return null;
  return (
    <span style={{
      position: "absolute",
      left: "calc(100% + 10px)", top: "50%", transform: "translateY(-50%)",
      padding: "5px 12px", borderRadius: 8, fontSize: 12, fontWeight: 600,
      whiteSpace: "nowrap", zIndex: 100, pointerEvents: "none",
      background: "var(--glass-surface-elevated)",
      backdropFilter: "blur(24px) saturate(150%)",
      WebkitBackdropFilter: "blur(24px) saturate(150%)",
      border: "1px solid var(--glass-border)",
      boxShadow: "inset 0 1px 0 var(--glass-highlight), 0 8px 24px rgba(0,0,0,0.25)",
      color: "var(--text)",
    }}>
      {label}
    </span>
  );
}

export default function Sidebar() {
  const path = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [hoveredNav, setHoveredNav] = useState<string | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "true") setCollapsed(true);
    } catch {}
    setMounted(true);
  }, []);

  function toggle() {
    const next = !collapsed;
    setCollapsed(next);
    try { localStorage.setItem(STORAGE_KEY, String(next)); } catch {}
  }

  const width = mounted ? (collapsed ? WIDTH_COLLAPSED : WIDTH_EXPANDED) : WIDTH_EXPANDED;

  return (
    <aside style={{
      width, minWidth: width, minHeight: "100vh",
      display: "flex", flexDirection: "column",
      padding: collapsed ? "20px 8px" : "20px 12px",
      background: "var(--glass-surface-floating)",
      backdropFilter: "blur(28px) saturate(160%)",
      WebkitBackdropFilter: "blur(28px) saturate(160%)",
      borderRight: "1px solid var(--glass-border)",
      boxShadow: "inset -1px 0 0 var(--glass-highlight)",
      position: "sticky", top: 0, zIndex: 20,
      transition: "width 200ms ease-out, min-width 200ms ease-out, padding 200ms ease-out",
      overflow: "visible",
    }}>
      {/* Logo row + toggle */}
      <div style={{
        display: "flex", alignItems: "center",
        justifyContent: collapsed ? "center" : "space-between",
        padding: collapsed ? "0" : "0 10px",
        marginBottom: 32,
        minHeight: 34,
        transition: "padding 200ms ease-out",
      }}>
        <Link href="/" style={{
          display: "flex", alignItems: "center", gap: 10,
          textDecoration: "none", color: "inherit",
          overflow: "hidden",
        }}>
          <div style={{
            width: 34, height: 34, minWidth: 34, borderRadius: 10,
            background: "var(--accent-muted)",
            border: "1px solid var(--accent-border)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 0 16px rgba(20,184,166,0.12), inset 0 1px 0 rgba(255,255,255,0.06)",
          }}>
            <Hexagon size={16} style={{ color: "var(--accent)" }} />
          </div>
          {!collapsed && (
            <span style={{
              fontWeight: 700, fontSize: 16, letterSpacing: "-0.3px",
              fontFamily: "var(--font-display)", color: "var(--text)",
              whiteSpace: "nowrap",
            }}>
              LedgerLens
            </span>
          )}
        </Link>

        {!collapsed && (
          <button
            onClick={toggle}
            aria-label="Collapse sidebar"
            aria-expanded="true"
            style={{
              width: 34, height: 34, borderRadius: 9,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "var(--glass-surface)", border: "1px solid var(--glass-border)",
              color: "var(--text-muted)", cursor: "pointer",
              boxShadow: "inset 0 1px 0 var(--glass-highlight)",
              transition: "all 0.18s ease",
              flexShrink: 0,
            }}
          >
            <PanelLeftClose size={15} />
          </button>
        )}
      </div>

      {/* Expand button when collapsed — sits below the logo */}
      {collapsed && (
        <button
          onClick={toggle}
          aria-label="Expand sidebar"
          aria-expanded="false"
          style={{
            width: 36, height: 36, borderRadius: 9,
            display: "flex", alignItems: "center", justifyContent: "center",
            background: "var(--glass-surface)", border: "1px solid var(--glass-border)",
            color: "var(--text-muted)", cursor: "pointer",
            boxShadow: "inset 0 1px 0 var(--glass-highlight)",
            transition: "all 0.18s ease",
            margin: "0 auto 16px",
          }}
        >
          <PanelLeft size={15} />
        </button>
      )}

      {/* Navigation label */}
      {!collapsed && (
        <p className="label-mono" style={{
          padding: "0 12px", marginBottom: 8,
          transition: "opacity 200ms ease-out",
        }}>
          Navigation
        </p>
      )}

      {/* Nav items */}
      <nav style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              onMouseEnter={() => setHoveredNav(href)}
              onMouseLeave={() => setHoveredNav(null)}
              style={{
                display: "flex", alignItems: "center",
                gap: 10,
                padding: collapsed ? "10px 0" : "10px 12px",
                justifyContent: collapsed ? "center" : "flex-start",
                borderRadius: 8, fontSize: 14, fontWeight: active ? 600 : 400,
                textDecoration: "none", transition: "all 0.18s ease",
                background: active ? "var(--accent-muted)" : "transparent",
                color: active ? "var(--accent)" : "var(--text-secondary)",
                borderLeft: collapsed ? "none" : (active ? "2px solid var(--accent)" : "2px solid transparent"),
                boxShadow: active ? "0 0 12px var(--glow-accent), inset 0 1px 0 rgba(20,184,166,0.06)" : "none",
                position: "relative",
                overflow: "visible",
              }}
            >
              <Icon size={18} strokeWidth={active ? 2.2 : 1.8} style={{ flexShrink: 0 }} />
              {!collapsed && <span style={{ whiteSpace: "nowrap" }}>{label}</span>}
              {collapsed && <NavTooltip label={label} show={hoveredNav === href} />}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div style={{
        padding: collapsed ? "14px 4px" : "14px 12px",
        borderTop: "1px solid var(--glass-border)",
        fontSize: 11, color: "var(--text-muted)",
        textAlign: collapsed ? "center" : "left",
        transition: "padding 200ms ease-out",
      }}>
        {collapsed ? (
          <p style={{ fontWeight: 600, color: "var(--text-secondary)" }}>v1.0</p>
        ) : (
          <>
            <p style={{ fontWeight: 600, color: "var(--text-secondary)", marginBottom: 2 }}>
              LedgerLens v1.0
            </p>
            <p>Razorpay Buildathon 2026</p>
          </>
        )}
      </div>
    </aside>
  );
}
