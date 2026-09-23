/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FAFAF8",
        panel: "#F2F0EA",
        ink: "#141210",
        muted: "#6B655D",
        rule: "#DAD5CB",
        signal: "#B4361E",   // severity / failure / the one loud colour
        kraft: "#8A6A1F",    // medium severity only
        moss: "#3F5B43",     // pass / healthy
      },
      fontFamily: {
        display: ['"General Sans"', '"Inter Tight"', "system-ui", "sans-serif"],
        sans: ['"Inter Tight"', "system-ui", "sans-serif"],
      },
      letterSpacing: { tightest: "-0.04em" },
      maxWidth: { measure: "62ch" },
    },
  },
  plugins: [],
};
