import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#2E86AB',
          600: '#1a6d91',
          700: '#0f3460',
          800: '#1a1a2e',
          900: '#16213e',
        },
        accent: '#e94560',
      },
      keyframes: {
        slideIn: {
          from: { transform: 'translateX(100%)', opacity: '0' },
          to: { transform: 'translateX(0)', opacity: '1' },
        },
        slideOut: {
          from: { transform: 'translateX(0)', opacity: '1' },
          to: { transform: 'translateX(100%)', opacity: '0' },
        },
      },
      animation: {
        slideIn: 'slideIn 0.2s ease-out',
        slideOut: 'slideOut 0.2s ease-in',
      },
    },
  },
  plugins: [],
}
export default config
