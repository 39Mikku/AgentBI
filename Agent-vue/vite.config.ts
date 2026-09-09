import { fileURLToPath, URL } from 'node:url'
import { createHash } from 'node:crypto'
import { realpathSync } from 'node:fs'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

const repoRoot = realpathSync(fileURLToPath(new URL('..', import.meta.url))).replace(/\\/g, '/').replace(/\/$/, '')
const normalizedRoot = process.platform === 'win32' ? repoRoot.toLowerCase() : repoRoot
const instanceId = `sha256:${createHash('sha256').update(normalizedRoot, 'utf8').digest('hex')}`

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), ...(process.env.AGENTBI_DEVTOOLS === 'true' ? [vueDevTools()] : []), {
    name: 'agentbi-instance',
    configureServer(server) {
      server.middlewares.use('/__agentbi', (_request, response) => {
        response.setHeader('Content-Type', 'application/json')
        response.end(JSON.stringify({ instance: instanceId }))
      })
    },
  }],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    open: false,
    proxy: {
      // 代理前端 /api 请求到 FastAPI 后端，剥离 /api 前缀，规避开发期 CORS
      '/api': {
        target: process.env.AGENTBI_BACKEND_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})
