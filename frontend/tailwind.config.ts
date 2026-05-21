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
          500: '#2E86AB',
          600: '#1a6d91',
          700: '#0f3460',
          800: '#1a1a2e',
          900: '#16213e',
        },
        accent: '#e94560',
      },
    },
  },
  plugins: [],
}
export default config