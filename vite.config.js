import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * 模拟 C 服务器：让 dev server 在 /chat 前缀下也能工作。
 * C 服务器把 /chat 转发到 B，地址栏可见路径为 /chat/...。
 * 本插件剥离前缀后交给 vite 处理静态资源与 SPA 回退，模拟生产 nginx 的行为。
 */
function chatPrefixPlugin() {
  return {
    name: 'chat-prefix',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url || '/'
        // 只处理 /chat 开头的请求（静态资源、SPA 路由、favicon）
        if (url === '/chat' || url.startsWith('/chat/')) {
          // 剥掉 /chat 前缀后转给 vite 内部 handler
          const stripped = url === '/chat' ? '/' : url.slice('/chat'.length)
          req.url = stripped
          server.middlewares.handle(req, res, () => {})
          return
        }
        next()
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), chatPrefixPlugin()],
  base: './',
  css: {
    modules: {
      localsConvention: 'camelCase',
    },
  },
  server: {
    host: true,
    allowedHosts: ['host.docker.internal'],
    proxy: {
      // C 会把 /chat/api 改写为 /chat 转发到 B（后端实际前缀）。
      // dev 下后端监听 3001，直接代理，无需前缀。
      '/chat/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
})
