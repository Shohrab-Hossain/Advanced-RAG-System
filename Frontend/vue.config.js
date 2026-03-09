const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,

  devServer: {
    port: 8080,
    // Proxy all /api/* requests to Flask during development
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        logLevel: 'debug',
      },
    },
  },
})
