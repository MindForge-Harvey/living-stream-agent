import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/chat/',
  css: {
    modules: {
      localsConvention: 'camelCase',
    },
  },
  server: {
    proxy: {
      '/chat/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
})
