import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        /* Brand palette */
        brand: {
          purple: "#5523b2",
          "purple-bright": "#7e3cf3",
          "purple-dark": "#2b0c6e",
          "purple-mid": "#5523b2",
          green: "#9dee92",
          lavender: "#e5e5ea",
          "lavender-1": "#eae6ff",
          white: "#ffffff",
          black: "#111111",
        },
        emerald: {
          400: "#34d399",
          500: "#10b981",
        },
        rose: {
          400: "#fb7185",
          500: "#f43f5e",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xl: "calc(var(--radius) + 4px)",
        "2xl": "calc(var(--radius) + 8px)",
      },
      fontFamily: {
        mono: ["var(--font-mono)", "monospace"],
        sans: ["var(--font-sans)", "sans-serif"],
        heading: ["var(--font-heading)", "Plus Jakarta Sans", "sans-serif"],
      },
      fontSize: {
        display: ["88px", { lineHeight: "1.1", fontWeight: "700" }],
        title: ["64px", { lineHeight: "1.1", fontWeight: "700" }],
        "h1": ["48px", { lineHeight: "1.1", fontWeight: "600" }],
        "h2": ["36px", { lineHeight: "1.2", fontWeight: "600" }],
        "h3": ["24px", { lineHeight: "1.3", fontWeight: "600" }],
      },
      animation: {
        "ticker-slide": "ticker-slide 40s linear infinite",
        "fade-in": "fade-in 0.5s ease forwards",
        "slide-up": "slide-up 0.4s ease forwards",
      },
      keyframes: {
        "ticker-slide": {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
