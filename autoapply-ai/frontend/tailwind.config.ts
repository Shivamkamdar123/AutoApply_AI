import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        base: "#08090C",
        surface: {
          DEFAULT: "#0F1115",
          2: "#16181D",
          3: "#1D2027",
        },
        border: {
          DEFAULT: "#24272E",
          strong: "#34383F",
        },
        text: {
          primary: "#F2F2F5",
          secondary: "#A5A8B0",
          tertiary: "#6B6E76",
        },
        accent: {
          DEFAULT: "#8B7CF7",
          strong: "#6E56CF",
          glow: "rgba(139, 124, 247, 0.25)",
        },
        semantic: {
          amber: "#F5A623",
          "amber-dim": "rgba(245, 166, 35, 0.12)",
          green: "#34D399",
          "green-dim": "rgba(52, 211, 153, 0.12)",
          red: "#F0596B",
          "red-dim": "rgba(240, 89, 107, 0.12)",
        },
      },
      fontFamily: {
        display: ["var(--font-space-grotesk)", "sans-serif"],
        sans: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-plex-mono)", "monospace"],
      },
      backgroundImage: {
        "gradient-signature":
          "linear-gradient(135deg, #7C5CFF 0%, #B15CFF 50%, #E44FD6 100%)",
        "radial-glow":
          "radial-gradient(circle at 50% 0%, rgba(124, 92, 255, 0.15) 0%, transparent 70%)",
      },
      boxShadow: {
        glow: "0 0 35px -5px rgba(124, 92, 255, 0.3)",
      },
    },
  },
  plugins: [],
};

export default config;
