import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // Resolve certificate paths using modern import.meta.dirname
  const certPath = path.resolve(import.meta.dirname, '../backend/certs/fullchain.pem')
  const keyPath = path.resolve(import.meta.dirname, '../backend/certs/privkey.pem')

  // Enable SSL only if certificates exist AND VITE_USE_SSL is not explicitly set to 'false'
  const certsExist = fs.existsSync(certPath) && fs.existsSync(keyPath)
  const useSSL = env.VITE_USE_SSL !== 'false' && certsExist

  // Dynamic backend URLs based on SSL state
  // Backend on port 8000 runs HTTPS whenever certs exist; decouple from frontend UI SSL toggle
  const backendProtocol = env.VITE_BACKEND_PROTOCOL || (certsExist ? 'https' : 'http')
  const wsProtocol = backendProtocol === 'https' ? 'wss' : 'ws'
  const backendHost = env.VITE_BACKEND_HOST || '127.0.0.1:8000'
  const backendTarget = `${backendProtocol}://${backendHost}`
  const wsTarget = `${wsProtocol}://${backendHost}`

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      https: useSSL ? {
        key: fs.readFileSync(keyPath),
        cert: fs.readFileSync(certPath)
      } : false,
      proxy: {
        '/workflow-studio': {
          target: backendTarget,
          changeOrigin: true,
          secure: false
        },
        '/workflows': {
          target: backendTarget,
          changeOrigin: true,
          secure: false
        },
        '/workflow': {
          target: backendTarget,
          changeOrigin: true,
          secure: false
        },
        '/client': {
          target: backendTarget,
          changeOrigin: true,
          secure: false
        },
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          secure: false
        },
        '/health': {
          target: backendTarget,
          changeOrigin: true,
          secure: false
        },
        '/ws': {
          target: wsTarget,
          ws: true,
          changeOrigin: true,
          secure: false
        }
      }
    }
  }
})
