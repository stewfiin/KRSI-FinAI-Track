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
        background: "#F8F9FD",       // Clean Ice Snow (Airy, Modern Canvas)
        surface: "#FFFFFF",          // Crisp White Floating Surface
        "surface-card": "#F1F4FA",   // Subtle Tech Surface
        "surface-border": "#E5E8F0", // Ultra-fine Modern Border
        volt: {
          DEFAULT: "#C8F526",        // Signature Electric Volt Lime (Neo-Fintech)
          hover: "#B6DF1E",
          light: "#F5FDE0",
          dark: "#9EBE12",
          text: "#0D0F17",
        },
        onyx: {
          DEFAULT: "#0D0F17",        // Deep Obsidian Black
          50: "#F8F9FD",
          100: "#F1F4FA",
          200: "#E2E8F0",
          800: "#1A1D27",
          900: "#0D0F17",
        },
        cream: {
          DEFAULT: "#F8F9FD",
          light: "#FFFFFF",
          dark: "#E8ECF5",
        },
        amber: {
          DEFAULT: "#C8F526",        // Electric Volt Accent
          hover: "#B6DF1E",
          light: "#F5FDE0",
          dark: "#9EBE12",
        },
        terracotta: {
          DEFAULT: "#0D0F17",        // Deep Obsidian as Primary Contrast
          hover: "#1F2432",
          light: "#F1F4FA",
          dark: "#05070A",
        },
        espresso: {
          DEFAULT: "#0F1117",        // Deep Graphite Text
          muted: "#64748B",          // Cool Slate Muted
          light: "#94A3B8",
        },
        primary: {
          DEFAULT: "#0D0F17",        // Obsidian Primary CTA
          hover: "#1F2432",
          light: "#C8F526",
          dark: "#05070A",
        },
        income: {
          DEFAULT: "#10B981",        // Vivid Emerald Mint
          hover: "#059669",
          light: "#047857",
          bg: "#ECFDF5",
        },
        expense: {
          DEFAULT: "#F43F5E",        // Coral Crimson
          hover: "#E11D48",
          light: "#BE123C",
          bg: "#FFF1F2",
        },
        // Compatibility aliases for existing classes
        emerald: {
          DEFAULT: "#10B981",
          hover: "#059669",
          100: "#D1FAE5",
          300: "#6EE7B7",
          400: "#34D399",
          500: "#10B981",
          600: "#059669",
          700: "#047857",
          800: "#065F46",
          900: "#064E3B",
        },
        danger: {
          DEFAULT: "#F43F5E",
          hover: "#E11D48",
        },
        red: {
          300: "#FDA4AF",
          400: "#FB7185",
          500: "#F43F5E",
          600: "#E11D48",
        },
        blue: {
          100: "#DBEAFE",
          200: "#BFDBFE",
          300: "#93C5FD",
          400: "#60A5FA",
          500: "#3B82F6",
          600: "#2563EB",
          800: "#1E40AF",
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"SF Pro Text"',
          '"SF Pro Display"',
          '"SF Pro"',
          "Inter",
          "system-ui",
          "sans-serif",
        ],
        mono: [
          '"SF Mono"',
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};
export default config;

