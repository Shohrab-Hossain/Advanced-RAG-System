/**
 * tailwind.config.js — the Tailwind theme, READ from the design source
 * ────────────────────────────────────────────────────────────────────
 * This file no longer DEFINES design values. It reads design/theme/tokens.json, which is the single
 * source for the palette, type, elevation and motion.
 *
 * Why: a toolchain config holding design source is the split design/ exists to prevent — swap Tailwind
 * and the design system goes with it. Add a token to tokens.json, not here.
 *
 * The keyframes stay here on purpose: they are CSS structure the motion tokens drive, not design values.
 *
 * @type {import('tailwindcss').Config}
 */
const tokens = require('./design/theme/tokens.json')

module.exports = {
  content: [
    './public/index.html',
    './src/**/*.{vue,js,ts}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: tokens.font.sans,
        mono: tokens.font.mono,
      },
      colors: {
        warm: tokens.color.warm,
      },
      animation: tokens.motion.animation,
      keyframes: tokens.motion.keyframes,
      boxShadow: {
        'card':    tokens.elevation.card,
        'card-md': tokens.elevation['card-md'],
      },
    },
  },
  plugins: [],
}
