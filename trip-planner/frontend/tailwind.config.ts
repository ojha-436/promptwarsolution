import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // WCAG-compliant pairs (≥ 4.5:1 against background)
        ink: "#0f172a",
        accent: "#1d4ed8",
        accentHover: "#1e40af",
        muted: "#475569",
        success: "#15803d",
        danger: "#b91c1c",
        warn: "#a16207",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
