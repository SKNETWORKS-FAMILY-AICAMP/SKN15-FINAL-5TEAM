/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'zeplin-main': '#F9FAFB',
        'zeplin-sidebar': '#1F2937',
        'zeplin-accent': '#8B5CF6',
        'chat-bg': '#fef7ff',
        'chat-surface': '#ffffff',
        'chat-primary': '#625b71',
        'chat-secondary': '#ece6f0',
        'chat-accent': '#e8def8',
        'message-sent': '#625b71',
        'message-received': '#ece6f0',
        'text-primary': '#1d1b20',
        'text-secondary': '#49454f',
      },
      fontFamily: {
        'roboto': ['Roboto', 'sans-serif'],
        'inter': ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
