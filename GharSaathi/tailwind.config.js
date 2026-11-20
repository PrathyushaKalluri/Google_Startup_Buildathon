/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        haldi: { DEFAULT: '#FFC83D', soft: '#FFE9A8', deep: '#E8A80F' },
        mirchi: { DEFAULT: '#F46D54', soft: '#FDDCD4', deep: '#C94A33' },
        peacock: { DEFAULT: '#157A78', soft: '#D3ECEA', deep: '#0E5957' },
        leaf: { DEFAULT: '#70A95A', soft: '#E1EFD9', deep: '#4E7F3C' },
        cream: '#FFF8EB',
        ink: { DEFAULT: '#302820', soft: '#6B5D4F' },
        sand: { DEFAULT: '#EDE1CD', deep: '#D9C7A8' },
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        pop: '4px 4px 0 0 #302820',
        soft: '0 10px 30px -12px rgba(48,40,32,0.25)',
      },
    },
  },
  plugins: [],
};
