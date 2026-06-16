import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Any request starting with /api gets forwarded to FastAPI
      '/api': {
        target: 'http://localhost:10000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
        // /api/predict → http://localhost:8000/predict
      }
    }
  }
})
