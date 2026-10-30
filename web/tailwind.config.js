/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#090d16',
        surface: '#0f172a',
        border: '#1e293b',
        muted: '#94a3b8',
      },
    },
  },
  plugins: [],
}
