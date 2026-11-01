/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // ── GraphMind Design System ──────────────────────────────────────
        bg: {
          base:    "#0f1117",   // deep charcoal — main background
          surface: "#1a1d27",   // slightly lighter — panels
          card:    "#222535",   // cards
          hover:   "#2a2e42",   // hover state
        },
        border: {
          DEFAULT: "#2d3148",
          subtle:  "#232639",
          strong:  "#3d4266",
        },
        accent: {
          DEFAULT: "#4f7ef8",   // muted blue — primary
          dim:     "#3d62c4",   // hover
          bright:  "#6b9aff",   // emphasis
          muted:   "#2a3f7a",   // very muted
        },
        text: {
          primary:   "#e8eaf0",
          secondary: "#9399b2",
          muted:     "#5c6289",
          inverse:   "#0f1117",
        },
        node: {
          repository: "#4f7ef8",
          file:       "#60a5fa",
          class:      "#a78bfa",
          function:   "#4caf7d",
          method:     "#34d399",
          import:     "#e8a44a",
          variable:   "#9399b2",
          directory:  "#5c6289",
        },
        status: {
          success: "#4caf7d",
          warning: "#e8a44a",
          error:   "#e05c5c",
          info:    "#4f7ef8",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
      animation: {
        "fade-in":   "fadeIn 0.15s ease-out",
        "slide-in":  "slideIn 0.2s ease-out",
        "pulse-dot": "pulseDot 2s ease-in-out infinite",
        "spin-slow": "spin 3s linear infinite",
      },
      keyframes: {
        fadeIn:   { from: { opacity: "0" }, to: { opacity: "1" } },
        slideIn:  { from: { transform: "translateY(-4px)", opacity: "0" }, to: { transform: "translateY(0)", opacity: "1" } },
        pulseDot: { "0%, 100%": { opacity: "1" }, "50%": { opacity: "0.4" } },
      },
      boxShadow: {
        panel:  "0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)",
        card:   "0 4px 12px rgba(0,0,0,0.3)",
        accent: "0 0 0 2px rgba(79,126,248,0.3)",
      },
    },
  },
  plugins: [],
};
