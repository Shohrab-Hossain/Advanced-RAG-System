const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,

  // A lint error must never stop the dev server. With the default (`true`), any
  // eslint error is emitted as a COMPILE error and the app refuses to render —
  // so a duplicate object key in one component takes the whole UI down while you
  // are working. Report them as warnings here; `npm run lint` and the production
  // build are where they are enforced.
  lintOnSave: 'warning',

  devServer: {
    port: 8080,
    proxy: {
      '/api': {
        // dev.py picks the backend port at launch and passes it in here.
        // The literal fallback keeps a bare `npm run serve` working on its own.
        target: process.env.DEV_API_TARGET || 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
