import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0B0F19",
        surface: "#111827",
        "surface-card": "#1E293B",
        "surface-border": "#334155",
        primary: {
          DEFAULT: "#3B82F6",
          hover: "#2563EB",
          light: "#60A5FA",
        },
        emerald: {
          DEFAULT: "#10B981",
          hover: "#059669",
        },
        danger: {
          DEFAULT: "#EF4444",
          hover: "#DC2626",
        },
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;

