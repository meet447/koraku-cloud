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
          panel: "#f7f7f5",
          surface: "#fafaf8",
          accent: "#0f766e",
          accentsoft: "#ccfbf1",
        },
      },
      fontFamily: {
        sans: ["var(--font-koraku)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        "4xl": "2rem",
      },
    },
  },
  plugins: [],
} satisfies Config;
