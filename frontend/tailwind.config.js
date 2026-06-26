/** @type {import('tailwindcss').Config} */
const ch = (v) => `rgb(var(${v}) / <alpha-value>)`;

export default {
  darkMode: 'class',
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['"Space Grotesk"', 'Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Semantic tokens — driven by CSS variables so light/dark share one set
        // of components. (Channel triplets keep `/opacity` modifiers working.)
        paper:        ch('--paper'),
        card:         ch('--card'),
        ink:          ch('--ink'),
        'ink-soft':   ch('--ink-soft'),
        'ink-faint':  ch('--ink-faint'),
        line:         ch('--line'),
        'line-strong':ch('--line-strong'),
        clay:         ch('--clay'),
        'clay-dark':  ch('--clay-dark'),
        'clay-wash':  ch('--clay-wash'),
        // Mood colours — data accents, constant across themes.
        happy:     '#C98A12',
        energetic: '#D6294B',
        angry:     '#7E3CC0',
        sad:       '#2563EB',
        relaxed:   '#0E8C63',
      },
      boxShadow: {
        card: '0 1px 2px rgb(0 0 0 / 0.04), 0 1px 3px rgb(0 0 0 / 0.06)',
        lift: '0 4px 6px rgb(0 0 0 / 0.05), 0 10px 20px rgb(0 0 0 / 0.07)',
        pop:  '0 8px 16px rgb(0 0 0 / 0.10), 0 20px 40px rgb(0 0 0 / 0.16)',
      },
      borderRadius: {
        xl2: '14px',
      },
    },
  },
  plugins: [],
}
