import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }

export const fmtINR = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

export const fmtPct = (n: number) => `${n.toFixed(1)}%`;

export const fmtDate = (s: string) =>
  new Date(s).toLocaleString("en-IN", { day:"2-digit", month:"short", hour:"2-digit", minute:"2-digit" });

export const severityColor = (s: string) => ({
  low:      "text-brand-green border-brand-green/30 bg-brand-green/10",
  warning:  "text-brand-amber border-brand-amber/30 bg-brand-amber/10",
  critical: "text-brand-red   border-brand-red/30   bg-brand-red/10",
}[s] ?? "text-zinc-400 border-zinc-700 bg-zinc-800");

export const statusIcon = (s: string) => ({
  matched:       "✓",
  auto_resolved: "⚡",
  resolved:      "✓",
  open:          "⚠",
  manual_review: "🚩",
}[s] ?? "·");

export const excTypeLabel: Record<string,string> = {
  amount_mismatch:    "Amount Mismatch",
  missing_settlement: "Missing Settlement",
  duplicate:          "Duplicate",
  date_mismatch:      "Date Mismatch",
  partial_settlement: "Partial Settlement",
  unknown_transaction:"Unknown Transaction",
};
