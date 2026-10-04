import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const backend = 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  // in dev, Vite serves the app and hands the API{{#auth}} and the sign-in{{/auth}} to the backend
  server: { proxy: { '/api': backend{{#auth}}, '/auth': backend{{/auth}} } },
})
