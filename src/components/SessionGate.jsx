import { Fragment, useEffect, useState } from 'react'
import App from '../App'
import { apiUrl } from '../api/base'

export default function SessionGate({ platform, children }) {
  const [mode, setMode] = useState('loading')
  const [user, setUser] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let disposed = false
    let checking = false
    let identity = null
    try { identity = JSON.parse(localStorage.getItem('livingStreamPortalUser') || 'null')?.platformUserId } catch {}
    const controller = new AbortController()
    const check = async () => {
      if (checking || disposed) return
      checking = true
      try {
        // Do not send a cached uid here: this endpoint discovers account changes.
        const response = await fetch(apiUrl('/chat/api/auth/session'), { cache: 'no-store', signal: controller.signal })
        if (disposed) return
        if (response.status === 401) {
          localStorage.removeItem('livingStreamPortalUser')
          localStorage.removeItem('adminToken')
          localStorage.removeItem('superAdminToken')
          setUser(null)
          const returnTo = window.location.pathname + window.location.search
          window.location.assign('/api/auth/login?return_to=' + encodeURIComponent(returnTo))
          return
        }
        if (!response.ok) throw new Error('认证服务暂不可用，请稍后重试')
        const data = await response.json()
        if (data.mode === 'platform') {
          localStorage.removeItem('livingStreamPortalUser')
          setMode('platform')
          return
        }
        if (data.mode !== 'portal' || !data.authenticated || !data.userInfo?.platformUserId) throw new Error('无法确认当前登录身份')
        if (identity && identity !== data.userInfo.platformUserId) {
          localStorage.removeItem('adminToken')
          localStorage.removeItem('superAdminToken')
        }
        identity = data.userInfo.platformUserId
        localStorage.setItem('livingStreamPortalUser', JSON.stringify(data.userInfo))
        setUser(data.userInfo)
        setMode('portal')
        setError('')
      } catch (err) {
        if (!disposed) setError(err.message)
      } finally { checking = false }
    }
    const channel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('agent-showcase-auth') : null
    if (channel) channel.onmessage = check
    window.addEventListener('focus', check)
    window.addEventListener('living-stream-auth-check', check)
    const visible = () => { if (!document.hidden) check() }
    document.addEventListener('visibilitychange', visible)
    const interval = setInterval(check, 30000)
    check()
    return () => {
      disposed = true
      controller.abort()
      clearInterval(interval)
      channel?.close()
      window.removeEventListener('focus', check)
      window.removeEventListener('living-stream-auth-check', check)
      document.removeEventListener('visibilitychange', visible)
    }
  }, [])

  if (mode === 'platform') return platform
  return <>
    {error && <div role="alert" style={{ position: 'fixed', zIndex: 1000, top: 0, left: 0, right: 0, padding: 12, background: '#fef3c7', textAlign: 'center' }}>{error}</div>}
    {user ? <Fragment key={user.platformUserId}>{children ? children(user) : <App userInfo={user} />}</Fragment> : <div style={{ padding: 48, textAlign: 'center' }}>正在验证门户登录…</div>}
  </>
}
