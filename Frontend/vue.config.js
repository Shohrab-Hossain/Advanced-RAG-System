const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,

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
