/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'zeplin-main': '#f5f2ff',
        'zeplin-sidebar': '#20123a',
        'zeplin-accent': '#6c5ce7',
        'chat-bg': '#f5f2ff',
        'chat-surface': '#ffffff',
        'chat-primary': '#6c5ce7',
        'chat-secondary': '#ece6ff',
        'chat-accent': '#ff7eb6',
        'message-sent': '#6c5ce7',
        'message-received': '#ece6ff',
        'text-primary': '#20123a',
        'text-secondary': '#564d7a',
      },
      fontFamily: {
        'roboto': ['Roboto', 'sans-serif'],
        'inter': ['Inter', 'sans-serif'],
        'cccomicrazy': ['"CCComicrazy"', 'cursive'],
      },
    },
  },
  plugins: [],
}
