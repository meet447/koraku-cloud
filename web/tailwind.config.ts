import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        koraku: {
          ink: "#0a0a0a",
          muted: "#737373",
          line: "#e5e5e5",
          panel: "#f7f7f7",
          surface: "#fafafa",
          surfaceWarm: "#f7f7f7",
          accent: "#0f766e",
          accentsoft: "#ccfbf1",
        },
        landing: {
          stone: "#f7f4ef",
          shell: "#faf9f7",
          card: "#ffffff",
          ink: "#1c1917",
          muted: "#57534e",
          soft: "#78716c",
          accent: "#ea580c",
          accentText: "#c2410c",
          accentSoft: "#fff7ed",
          body: "#2d3148",
        },
      },
      fontFamily: {
        sans: ["var(--font-koraku)", "system-ui", "sans-serif"],
        "landing-sans": ["var(--font-inter)", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        "landing-display": ["var(--font-outfit)", "Outfit", "ui-sans-serif", "system-ui", "sans-serif"],
        "landing-body": ["var(--font-dm-sans)", "DM Sans", "ui-sans-serif", "system-ui", "sans-serif"],
        "landing-hand": ["var(--font-caveat)", "Caveat", "cursive"],
        "landing-serif": ["var(--font-cormorant)", "Cormorant Garamond", "Georgia", "serif"],
        "landing-pixel": ["var(--font-pixelify)", "Pixelify Sans", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        "4xl": "2rem",
      },
      keyframes: {
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
      },
      animation: {
        marquee: "marquee 45s linear infinite",
      },
      boxShadow: {
        "landing-hero": "0 40px 100px -28px rgba(0,0,0,0.08)",
        "landing-nav": "0 12px 40px rgba(0,0,0,0.08)",
        "landing-card": "0 1px 3px rgba(0,0,0,0.05), 0 18px 40px -28px rgba(0,0,0,0.18)",
        "landing-soft": "0 4px 20px rgba(0,0,0,0.04)",
      },
    },
  },
  plugins: [],
} satisfies Config;
