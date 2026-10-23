import React, { useState, useEffect, useRef } from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import App from './App'
import SessionGate from './components/SessionGate'
import AdminPage from './pages/Admin/AdminPage'
import SuperLoginPage from './pages/SuperAdmin/SuperLoginPage'
import SuperConfigPage from './pages/SuperAdmin/SuperConfigPage'
import { apiUrl, apiFetch } from './api/base'
import './styles/variables.css'

const LOGIN_ERROR_MESSAGES = {
  empty_user: '未获取到用户信息，请从平台进入',
  empty_ticket: '未获取到登录票据，请从平台进入',
  empty_staff_code_boss: '未获取到工号信息，无法完成校验',
  iam_check_failed: '身份校验服务异常，请稍后重试',
  iam_rejected_ticket: '登录票据校验未通过',
  staff_code_boss_mismatch: '身份信息与账号不匹配',
}

function loginErrorMessage(reason) {
  return LOGIN_ERROR_MESSAGES[reason] || ''
}

function ChatRoute() {
  const [userInfo, setUserInfo] = useState(null)
  const [waiting, setWaiting] = useState(true)
  const [loginRequired, setLoginRequired] = useState(false)
  const [loginError, setLoginError] = useState('')
  const authenticatingRef = useRef(false)

  useEffect(() => {
    const issueTestToken = async (info) => {
      const res = await apiFetch(apiUrl('/chat/api/auth/test-token'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: info.platformUserId,
          platformToken: info.platformToken || '',
          lanName: info.lanName || '',
          regionName: info.regionName || '',
          staffCode: info.staffCode || '',
          staffCodeBoss: info.staffCodeBoss || '',
          staffName: info.staffName || '',
          staffPosType: info.staffPosType || '',
        }),
      })
      if (!res.ok) {
        let reason = ''
        try {
          const errData = await res.json()
          reason = errData?.detail?.reason || errData?.reason || ''
        } catch {
          // 忽略解析失败
        }
        console.error('[login] test-token failed, status=', res.status, 'reason=', reason)
        const err = new Error('无法获取用户登录凭证')
        err.reason = reason
        throw err
      }
      const data = await res.json()
      if (!data.success || !data.token) {
        throw new Error(data.error || '无法获取用户登录凭证')
      }
      return {
        ...info,
        platformToken: data.token,
        lanName: data.lan_name || info.lanName || '',
        regionName: data.region_name || info.regionName || '',
        staffCode: data.staff_code || info.staffCode || '',
        staffName: data.staff_name || info.staffName || '',
        staffPosType: data.staff_pos_type || info.staffPosType || '',
      }
    }

    const showLoginRequired = () => {
      localStorage.removeItem('userInfo')
      console.error('[login] timeout => showLoginRequired (no PLATFORM_LOGIN received within 10s)')
      setLoginRequired(true)
      setWaiting(false)
    }
    let timeout = null

    const postToParent = (source, data) => {
      try {
        source?.postMessage(data, '*')
      } catch {
        // 忽略回传失败，不影响本系统自身登录状态
      }
    }

    const handleLogin = (event) => {
      const data = event.data || {}
      if (data.type === 'PLATFORM_LOGIN' && data.platformUserId) {
        console.log('[login] received PLATFORM_LOGIN, userId=', data.platformUserId)
        postToParent(event.source, { type: 'PLATFORM_LOGIN_RECEIVED' })
        if (authenticatingRef.current) {
          return
        }
        authenticatingRef.current = true
        if (timeout) {
          clearTimeout(timeout)
        }
        const info = {
          platformUserId: data.platformUserId,
          platformToken: data.platformToken || '',
          // 兼容蛇形和驼峰两种命名格式
          lanName: data.lanName || data.lan_name || '',
          regionName: data.regionName || data.region_name || '',
          staffCode: data.staffCode || data.staff_code || '',
          staffCodeBoss: data.staffCodeBoss || data.staff_code_boss || '',
          staffName: data.staffName || data.staff_name || '',
          staffPosType: data.staffPosType || data.staff_pos_type || '',
        }
        issueTestToken(info)
          .then((tokenInfo) => {
            setLoginError('')
            setUserInfo(tokenInfo)
            localStorage.setItem('userInfo', JSON.stringify(tokenInfo))
            postToParent(event.source, { type: 'PLATFORM_LOGIN_SUCCESS' })
            setWaiting(false)
            // 验证通过后刷新页面，重挂载后从 localStorage 进入对话界面
            window.location.reload()
          })
          .catch((err) => {
            localStorage.removeItem('userInfo')
            console.error('[login] issueTestToken catch, reason=', err?.reason)
            setLoginError(err?.reason || '')
            postToParent(event.source, { type: 'PLATFORM_LOGIN_FAILED', reason: err?.reason || '' })
            setLoginRequired(true)
            setWaiting(false)
          })
          .finally(() => {
            authenticatingRef.current = false
          })
      }
    }

    const handler = (event) => handleLogin(event)
    window.addEventListener('message', handler)

    // 退出登录后直接进入"请先从平台登录"页，不再发起自动握手/等待重登
    if (localStorage.getItem('logoutFlag')) {
      localStorage.removeItem('logoutFlag')
      localStorage.removeItem('userInfo')
      setLoginRequired(true)
      setWaiting(false)
      return () => {
        window.removeEventListener('message', handler)
      }
    }

    const savedUserInfo = localStorage.getItem('userInfo')
    if (savedUserInfo) {
      try {
        const parsed = JSON.parse(savedUserInfo)
        if (parsed.platformToken) {
          setUserInfo(parsed)
          setWaiting(false)
          return () => {
            window.removeEventListener('message', handler)
          }
        }
        localStorage.removeItem('userInfo')
      } catch (e) {
        localStorage.removeItem('userInfo')
      }
    }

    timeout = setTimeout(showLoginRequired, 10000)

    return () => {
      window.removeEventListener('message', handler)
      if (timeout) {
        clearTimeout(timeout)
      }
    }
  }, [])

  if (loginRequired) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f9fafb'
      }}>
        <div style={{
          background: '#fff',
          padding: '48px',
          borderRadius: '16px',
          textAlign: 'center',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
        }}>
          <h2 style={{ margin: 0, color: '#1f2937' }}>请先从平台登录</h2>
          {loginError && console.error('[login] rendering loginRequired, loginError=', loginError)}
          {loginErrorMessage(loginError) && (
            <p style={{ marginTop: '12px', color: '#dc2626', fontSize: '14px' }}>
              {loginErrorMessage(loginError)}
            </p>
          )}
        </div>
      </div>
    )
  }

  if (waiting) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f9fafb'
      }}>
        <div style={{
          background: '#fff',
          padding: '48px',
          borderRadius: '16px',
          textAlign: 'center',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
        }}>
          <h2 style={{ marginBottom: '12px', color: '#1f2937' }}>正在连接直播脚本生成智能体...</h2>
          <p style={{ color: '#6b7280', marginBottom: '24px' }}>请从直播脚本生成智能体点击"进入对话"按钮</p>
        </div>
      </div>
    )
  }

  return <App userInfo={userInfo} />
}

function AdminRoute({ children }) {
  const token = localStorage.getItem('adminToken')
  if (!token) {
    return <Navigate to="/" replace />
  }
  return children
}

function SuperAdminRoute({ children }) {
  const token = localStorage.getItem('superAdminToken')
  if (!token) {
    return <Navigate to="/superlogin" replace />
  }
  return children
}

function AppRoutes({ user }) {
  return (
      <Routes>
        <Route path="/" element={user ? <App userInfo={user} /> : <ChatRoute />} />
        <Route path="/config" element={<AdminRoute><AdminPage /></AdminRoute>} />
        <Route path="/superlogin" element={<SuperLoginPage />} />
        <Route path="/superconfig" element={<SuperAdminRoute><SuperConfigPage /></SuperAdminRoute>} />
      </Routes>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <HashRouter>
      <SessionGate platform={<AppRoutes />}>{user => <AppRoutes user={user} />}</SessionGate>
    </HashRouter>
  </React.StrictMode>
)
