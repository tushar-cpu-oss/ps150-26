/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg0: '#070A0F', bg1: '#0B1017', bg2: '#0E141C',
        panel: '#111821', panel2: '#151D27',
        ice: { DEFAULT: '#7CD4F7', dim: '#4A9CC0', soft: 'rgba(124,212,247,0.12)' },
        cool: '#E6EEF5',
        amber: { DEFAULT: '#F2B34A' },
        crit: '#F0616D',
        ok: '#5FD6A4',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};
