/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#FCFCFA",
        card: "#FFFFFF",
        border: "#E8E8E4",
        brandGreen: "#2E9D50",
        brandOrange: "#F59A23",
        brandRed: "#E53935",
        brandPurple: "#8064C8",
        brandBlue: "#2878D4",
      },
      fontFamily: {
        sans: ['"Times New Roman"', "Times", "serif"],
        serif: ['"Times New Roman"', "Times", "serif"],
        mono: ['"Times New Roman"', "Times", "serif"],
      },
    },
  },
  plugins: [],
};
