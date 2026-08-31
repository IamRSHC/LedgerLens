import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }

export const fmtINR = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

export const fmtPct = (n: number) => `${n.toFixed(1)}%`;

export const fmtDate = (s: string) =>
  new Date(s).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

export const excTypeLabel: Record<string, string> = {
  amount_mismatch:     "Amount Mismatch",
  missing_settlement:  "Missing Settlement",
  duplicate:           "Duplicate",
  date_mismatch:       "Date Mismatch",
  partial_settlement:  "Partial Settlement",
  unknown_transaction: "Unknown Transaction",
};
