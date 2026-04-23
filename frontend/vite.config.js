import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  base: '/ui/',
  plugins: [vue()],
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    proxy: {
      '/v1': {
        target: 'http://localhost:8082',
        changeOrigin: true,
      },
      '/pulse': {
        target: 'http://localhost:8082',
        changeOrigin: true,
      }
    }
  }
})
