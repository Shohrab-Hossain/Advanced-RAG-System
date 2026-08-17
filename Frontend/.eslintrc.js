/**
 * .eslintrc.js — the config `npm run lint` needs to exist
 * ───────────────────────────────────────────────────────
 * The `lint` script has been in package.json since the project started, but neither the plugin nor a
 * config file was ever present, so the script could not run at all.
 *
 * Eslintrc (not flat `eslint.config.js`) because Vue CLI 5 ships ESLint 8, which reads this format.
 * Migrate to flat config only when the Vue CLI plugin does.
 *
 * The style rules below are DESCRIPTIVE — they were read off the existing source, not imposed on it.
 * The repo has no semicolons and uses single quotes; a config that disagreed with 60-odd files would
 * be disabled wholesale on first run, which is worse than no linter.
 *
 * Two rules were tuned after the first run, because they were flagging OUR opinion rather than a defect:
 *   · comma-dangle      → warn. The source is genuinely inconsistent here (5 sites), and a formatting
 *                         preference is not worth a red build.
 *   · no-constant-condition → checkLoops: false. `while (true)` with an internal `break` is the correct
 *                         shape for the SSE reader loop in services/ragApi.js, not a mistake.
 */
module.exports = {
  root: true,

  env: {
    node: true,
    browser: true,
    es2022: true,
  },

  extends: [
    'plugin:vue/vue3-essential',
    'eslint:recommended',
  ],

  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
  },

  rules: {
    // ── House style, read off the existing source ──────────────────────────
    semi: ['error', 'never'],
    quotes: ['error', 'single', { avoidEscape: true }],
    'comma-dangle': ['warn', 'always-multiline'],
    'no-constant-condition': ['error', { checkLoops: false }],

    // ── Kept as warnings — real signal, but not worth failing a build over ──
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'off',

    // Single-word component names are used deliberately for page views
    // (HomeView, ChatView); vue3-essential does not enforce this, but it is
    // listed so a later bump to vue3-recommended does not surprise anyone.
    'vue/multi-word-component-names': 'off',
  },
}
