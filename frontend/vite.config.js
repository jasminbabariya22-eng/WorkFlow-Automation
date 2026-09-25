import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

// Load SSL certificates generated in backend/certs
const certPath = path.resolve(__dirname, '../backend/certs/fullchain.pem')
const keyPath = path.resolve(__dirname, '../backend/certs/privkey.pem')

const hasCerts = fs.existsSync(certPath) && fs.existsSync(keyPath)

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    https: hasCerts ? {
      key: fs.readFileSync(keyPath),
      cert: fs.readFileSync(certPath)
    } : false,
    proxy: {
      '/workflow-studio': {
        target: 'https://127.0.0.1:8000',
        changeOrigin: true,
        secure: false
      },
      '/workflows': {
        target: 'https://127.0.0.1:8000',
        changeOrigin: true,
        secure: false
      },
      '/workflow': {
        target: 'https://127.0.0.1:8000',
        changeOrigin: true,
        secure: false
      },
      '/client': {
        target: 'https://127.0.0.1:8000',
        changeOrigin: true,
        secure: false
      },
      '/api': {
        target: 'https://127.0.0.1:8000',
        changeOrigin: true,
        secure: false
      },
      '/health': {
        target: 'https://127.0.0.1:8000',
        changeOrigin: true,
        secure: false
      },
      '/ws': {
        target: 'wss://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
        secure: false
      }
    }
  }
})
