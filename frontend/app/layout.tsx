import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LedgerLens — AI Finance Controller",
  description: "Reconcile. Investigate. Resolve.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  );
}
