import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class", "[data-theme='dark']"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        "surface-3": "var(--surface-3)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        text: "var(--text)",
        "text-dim": "var(--text-dim)",
        "text-mute": "var(--text-mute)",
        accent: "var(--accent)",
        "accent-soft": "var(--accent-soft)",
        "accent-ring": "var(--accent-ring)",
        blue: "var(--blue)",
        violet: "var(--violet)",
        amber: "var(--amber)",
        red: "var(--red)",
      },
      fontFamily: {
        sans: "var(--font-sans)",
        mono: "var(--font-mono)",
      },
      fontSize: {
        h1: ["22px", { lineHeight: "1.2", letterSpacing: "-0.4px", fontWeight: "600" }],
        h2: ["15px", { lineHeight: "1.3", fontWeight: "600" }],
        body: ["13px", { lineHeight: "1.5" }],
        "body-sm": ["12px", { lineHeight: "1.5" }],
        mono: ["12px", { lineHeight: "1.5" }],
        "mono-sm": ["11px", { lineHeight: "1.4" }],
        label: ["10.5px", { lineHeight: "1.2", letterSpacing: "0.4px", fontWeight: "500" }],
        kpi: ["28px", { lineHeight: "1.2", letterSpacing: "-0.6px", fontWeight: "500" }],
      },
      borderRadius: {
        xs: "3px",
        sm: "4px",
        md: "5px",
        lg: "6px",
        xl: "8px",
      },
      spacing: {
        "s-1": "4px",
        "s-2": "8px",
        "s-3": "10px",
        "s-4": "12px",
        "s-5": "14px",
        "s-6": "18px",
        "s-7": "20px",
        "s-8": "28px",
        "s-9": "40px",
      },
      boxShadow: {
        sm: "0 1px 2px rgba(0,0,0,0.04)",
        md: "0 4px 16px rgba(0,0,0,0.06)",
        lg: "0 12px 48px rgba(0,0,0,0.18)",
        popup: "0 8px 24px rgba(0,0,0,0.10)",
      },
      keyframes: {
        vaPulse: {
          "0%": { boxShadow: "0 0 0 0 var(--accent-ring)" },
          "70%": { boxShadow: "0 0 0 8px rgba(16,185,129,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(16,185,129,0)" },
        },
        vaPop: { "0%": { transform: "scale(0.96)", opacity: "0" }, "100%": { transform: "scale(1)", opacity: "1" } },
        vaSlide: { "0%": { transform: "translateX(360px)", opacity: "0" }, "100%": { transform: "translateX(0)", opacity: "1" } },
        vaFade: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
      },
      animation: {
        vaPulse: "vaPulse 1.6s infinite",
        vaPop: "vaPop 160ms cubic-bezier(.2,.8,.3,1)",
        vaSlide: "vaSlide 180ms cubic-bezier(.2,.8,.3,1)",
        vaFade: "vaFade 140ms ease-out",
      },
    },
  },
  plugins: [],
};
export default config;
