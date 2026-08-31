import type { Config } from "tailwindcss";
const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}","./components/**/*.{ts,tsx}","./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        slate: {
          950: "#020617",
          900: "#0F172A",
          800: "#1E293B",
          700: "#334155",
          600: "#475569",
          500: "#64748B",
          400: "#94A3B8",
          300: "#CBD5E1",
          200: "#E2E8F0",
          100: "#F1F5F9",
          50:  "#F8FAFC",
        },
        teal: {
          700: "#0F766E",
          600: "#0D9488",
          500: "#14B8A6",
          400: "#2DD4BF",
        },
        emerald: { 500: "#10B981", 600: "#059669" },
        amber:   { 500: "#F59E0B", 600: "#D97706" },
        red:     { 500: "#EF4444", 600: "#DC2626" },
        blue:    { 500: "#3B82F6", 600: "#2563EB" },
      },
      fontFamily: {
        sans:    ["Inter","ui-sans-serif","system-ui"],
        display: ["Space Grotesk","Inter","sans-serif"],
        mono:    ["JetBrains Mono","ui-monospace","monospace"],
      },
      animation: {
        "fade-in":    "fadeInUp 0.4s ease-out both",
        "slide-in":   "slideInRight 0.25s ease-out both",
      },
    },
  },
  plugins: [],
};
export default config;
