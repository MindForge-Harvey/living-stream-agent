import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

function localLoginPlugin(env) {
  return {
    name: 'local-login',
    apply: 'serve',
    configureServer(server) {
      if (env.LOCAL_DEV_LOGIN !== 'true' || !env.PLATFORM_ENTRY_TOKEN) return
      server.middlewares.use(async (req, res, next) => {
        if (req.url !== '/__local/login') return next()
        const address = req.socket.remoteAddress
        const localHost = /^(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/.test(req.headers.host || '')
        if (req.method !== 'GET' ||
          !['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(address) ||
          !localHost) {
          res.statusCode = 403
          return res.end('Local access only')
        }
        res.setHeader('Cache-Control', 'no-store')
        res.setHeader('X-Frame-Options', 'DENY')
        try {
          const response = await fetch('http://127.0.0.1:3001/chat/api/auth/test-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              userId: 'local-harvey',
              platformToken: env.PLATFORM_ENTRY_TOKEN,
              staffName: '本地测试',
              staffCode: 'LOCAL001',
            }),
            signal: AbortSignal.timeout(10000),
          })
          const data = await response.json()
          if (!response.ok || !data.success || !data.token) throw new Error('Login failed')
          const info = JSON.stringify({
            platformUserId: data.userId,
            platformToken: data.token,
            staffName: data.staff_name,
            staffCode: data.staff_code,
          }).replace(/</g, '\\u003c')
          res.setHeader('Content-Type', 'text/html; charset=utf-8')
          res.end(`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>本地登录</title><body>正在进入直播话术智能体…<script>localStorage.removeItem('logoutFlag');localStorage.setItem('userInfo',JSON.stringify(${info}));location.replace('/chat/');</script></body></html>`)
        } catch {
          res.statusCode = 502
          res.end('本地登录失败，请确认后端已启动，并检查 .env 的 PLATFORM_ENTRY_TOKEN。')
        }
      })
    },
  }
}

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
        // API 必须保留完整前缀交给下面的 proxy，不能剥成 /api。
        if (url === '/chat/api' || url.startsWith('/chat/api/')) return next()
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

export default defineConfig(({ mode }) => ({
  plugins: [react(), localLoginPlugin(loadEnv(mode, process.cwd(), '')), chatPrefixPlugin()],
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
}))
