import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Le proxy renvoie tous les appels /api vers le backend Flask (port 5000),
// ce qui évite le CORS en développement.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:5000', changeOrigin: true },
      '/health': { target: 'http://localhost:5000', changeOrigin: true },
      '/socket.io': { target: 'http://localhost:5000', changeOrigin: true, ws: true },
    },
  },
})
