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
        background: "#FEF3E2",       // Warm Cream (Band 1)
        surface: "#FFFFFF",          // Crisp white card on cream background
        "surface-card": "#FDF9F2",   // Subtle tinted warm card
        "surface-border": "#EBD8C1", // Warm border
        cream: {
          DEFAULT: "#FEF3E2",
          light: "#FFFBF5",
          dark: "#F4E4CE",
        },
        amber: {
          DEFAULT: "#F4AE52",        // Warm Golden Amber (Band 2)
          hover: "#E59E3F",
          light: "#FDEED9",
          dark: "#C78229",
        },
        terracotta: {
          DEFAULT: "#D4621A",        // Terracotta / Rust (Band 3)
          hover: "#B85012",
          light: "#FCEBDC",
          dark: "#993E0A",
        },
        espresso: {
          DEFAULT: "#2A1A0E",        // Deep Espresso (Band 4)
          muted: "#6B584B",
          light: "#948274",
        },
        primary: {
          DEFAULT: "#D4621A",        // Terracotta as primary button & accent
          hover: "#B85012",
          light: "#F4AE52",
          dark: "#2A1A0E",
        },
        income: {
          DEFAULT: "#588157",        // Sage Green for income
          hover: "#456944",
          light: "#355234",
          bg: "#E9F1E8",
        },
        expense: {
          DEFAULT: "#D4621A",        // Terracotta / Rust for expense
          hover: "#B85012",
          light: "#993E0A",
          bg: "#FCEBDC",
        },
        // Compatibility aliases for existing classes
        emerald: {
          DEFAULT: "#588157",
          hover: "#456944",
          300: "#588157",
          400: "#456944",
          500: "#355234",
          600: "#273D26",
        },
        danger: {
          DEFAULT: "#D4621A",
          hover: "#B85012",
        },
        red: {
          300: "#D4621A",
          400: "#B85012",
          500: "#993E0A",
          600: "#7A3108",
        },
        blue: {
          300: "#F4AE52",
          400: "#D4621A",
          500: "#B85012",
          600: "#993E0A",
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

