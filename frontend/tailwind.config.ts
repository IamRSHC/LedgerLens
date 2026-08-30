import type { Config } from "tailwindcss";
const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}","./components/**/*.{ts,tsx}","./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          green:  "#2FB380",
          amber:  "#F5A524",
          red:    "#EF4444",
          accent: "#4C8DFF",
        },
        ink:          "#0B1220",
        panel:        "#131B2C",
        panelRaised:  "#182238",
        line:         "#24304A",
      },
      fontFamily: {
        sans:    ["Inter","ui-sans-serif","system-ui"],
        display: ["Space Grotesk","Inter","sans-serif"],
        mono:    ["JetBrains Mono","ui-monospace","monospace"],
      },
      animation: {
        "fade-in":    "fadeIn 0.4s ease-out",
        "slide-in":   "slideIn 0.35s ease-out",
        "pulse-slow": "pulse 3s ease-in-out infinite",
      },
      keyframes: {
        fadeIn:  { "0%": {opacity:"0",transform:"translateY(8px)"}, "100%": {opacity:"1",transform:"translateY(0)"} },
        slideIn: { "0%": {opacity:"0",transform:"translateX(16px)"}, "100%": {opacity:"1",transform:"translateX(0)"} },
      },
    },
  },
  plugins: [],
};
export default config;
