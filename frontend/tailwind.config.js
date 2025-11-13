/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Charte graphique VyBuddy
        'vert-profond': {
          DEFAULT: '#002e33',
          light: '#1a464b',
          medium: '#356065',
          lighter: '#4d797e',
        },
        'indigo-tropical': {
          DEFAULT: '#7c7cff',
          light: '#a0a5ff',
          medium: '#adb1ff',
          lighter: '#c8c9ff',
        },
        'sable': {
          DEFAULT: '#eae0ce',
          light: '#f1eade',
          medium: '#f6f1e9',
          lighter: '#faf8f4',
        },
        'blanc': '#ffffff',
      },
    },
  },
  plugins: [],
}

