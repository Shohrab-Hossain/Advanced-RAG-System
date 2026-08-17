/**
 * tailwind.config.js — the Tailwind theme
 * ───────────────────────────────────────
 * The live design system is src/assets/main.css: its @layer components classes (.card, .btn-primary,
 * .section-label-*, .prose-rag) and its @layer utilities animations. This file holds only what has to
 * be expressed as Tailwind theme config rather than CSS — today that is the two font families.
 *
 * Why nothing is read from design/ any more: design/theme-lab/ is a THROWAWAY, git-ignored scratch
 * space for trying a new theme out. It holds no live data and may be deleted at any time. Adopting a
 * theme means writing the values into src/ (and here), not pointing the build at the lab.
 *
 * The families must stay in step with the Google Fonts <link> in public/index.html — renaming one here
 * without changing that fetches nothing and silently falls back.
 *
 * @type {import('tailwindcss').Config}
 */
module.exports = {
  content: [
    './public/index.html',
    './src/**/*.{vue,js,ts}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
