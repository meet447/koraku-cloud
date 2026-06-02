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
      },
      fontFamily: {
        sans: ["var(--font-koraku)", "system-ui", "sans-serif"],
        helvetica: ['"Helvetica Regular"', "ui-sans-serif", "system-ui", "sans-serif"],
        "landing-sans": ["var(--font-inter)", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        "landing-display": ["var(--font-outfit)", "Outfit", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        "4xl": "2rem",
      },
    },
  },
  plugins: [],
} satisfies Config;
