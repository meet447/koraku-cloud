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
          shell: "#f9fafb",
          card: "#f4f8f9",
          footer: "#f0f1f5",
          ink: "#1c1917",
          muted: "#57534e",
          soft: "#78716c",
          navy: "#0a1b33",
          deep: "#0a152d",
          blue: "#1e4fc0",
          body: "#2d3148",
        },
      },
      fontFamily: {
        sans: ["var(--font-koraku)", "system-ui", "sans-serif"],
        "landing-sans": ["var(--font-inter)", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        "landing-display": ["var(--font-outfit)", "Outfit", "ui-sans-serif", "system-ui", "sans-serif"],
        "landing-body": ["var(--font-dm-sans)", "DM Sans", "ui-sans-serif", "system-ui", "sans-serif"],
        "landing-hand": ["var(--font-caveat)", "Caveat", "cursive"],
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
      backgroundImage: {
        "landing-badge":
          "linear-gradient(90deg, #F5C344, #F28482, #B567C2)",
        "landing-highlight":
          "linear-gradient(90deg, #FFB347, #E5A1F5)",
        "landing-card-1":
          "radial-gradient(circle at 50% 0%, #FFB347 0%, #F9ED96 30%, #F4F8F9 60%, #F4F8F9 100%)",
        "landing-card-2":
          "radial-gradient(circle at 50% 0%, #E5A1F5 0%, #F8ACA0 30%, #F4F8F9 60%, #F4F8F9 100%)",
        "landing-card-3":
          "radial-gradient(circle at 50% 0%, #F9ED96 0%, #E5A1F5 30%, #F4F8F9 60%, #F4F8F9 100%)",
        "landing-lucky-cube":
          "linear-gradient(135deg, #5b9ffb 0%, #1e5dd7 55%, #1448be 100%)",
      },
      boxShadow: {
        "landing-hero": "0 40px 100px -20px rgba(0,0,0,0.03)",
        "landing-nav": "0 12px 40px rgba(0,0,0,0.08)",
        "landing-card": "0 10px 30px -10px rgba(0,0,0,0.1)",
        "landing-footer-left": "0 12px 40px rgba(21, 76, 189, 0.25)",
        "landing-footer-right": "0 4px 20px rgba(0,0,0,0.04)",
        "landing-lucky-cube":
          "inset 3px 3px 8px rgba(255,255,255,0.35), inset -3px -3px 12px rgba(0,0,0,0.18), 8px 14px 28px rgba(20,72,200,0.35)",
        "landing-social":
          "0 6px 18px rgba(0,0,0,0.35), 0 2px 6px rgba(0,0,0,0.2)",
        "landing-social-hover":
          "0 10px 24px rgba(0,0,0,0.4), 0 4px 10px rgba(0,0,0,0.25)",
        "landing-subscribe":
          "0 6px 20px rgba(0,0,0,0.28), 0 2px 8px rgba(0,0,0,0.15)",
        "landing-subscribe-hover":
          "0 8px 24px rgba(0,0,0,0.32), 0 4px 12px rgba(0,0,0,0.18)",
      },
    },
  },
  plugins: [],
} satisfies Config;
