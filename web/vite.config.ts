import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import path from 'node:path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: {
    port: 5173,
    // UWC_API_PORT lets an isolated API (own runtime dir) back a second dev server during development
    proxy: { '/api': { target: `http://127.0.0.1:${process.env.UWC_API_PORT ?? 8765}`, changeOrigin: true } },
  },
})
