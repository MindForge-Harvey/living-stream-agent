import React, { useState, useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import App from './App'
import AdminPage from './pages/Admin/AdminPage'
import TestLoginPage from './pages/TestLogin/TestLoginPage'
import SuperLoginPage from './pages/SuperAdmin/SuperLoginPage'
import SuperConfigPage from './pages/SuperAdmin/SuperConfigPage'
import './styles/variables.css'

const PLATFORM_ENTRY_TOKEN = '5s9D2g7F0k3j6P1r8T4b7N2m5Z9x0C3v7B1n4A6q8w2E5r7t9y1u3i5o7p0a2s4d6f8g'

function ChatRoute() {
  const [userInfo, setUserInfo] = useState(null)
  const [waiting, setWaiting] = useState(true)
  const [loginRequired, setLoginRequired] = useState(false)

  useEffect(() => {
    const issueTestToken = async (info) => {
      const res = await fetch('/chat/api/auth/test-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: info.platformUserId,
          platformToken: PLATFORM_ENTRY_TOKEN,
          lanName: info.lanName || '',
          regionName: info.regionName || '',
          staffCode: info.staffCode || '',
          staffName: info.staffName || '',
          staffPosType: info.staffPosType || '',
        }),
      })
      if (!res.ok) {
        throw new Error('无法获取用户登录凭证')
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

    const savedUserInfo = localStorage.getItem('userInfo')
    if (savedUserInfo) {
      try {
        const parsed = JSON.parse(savedUserInfo)
        if (parsed.platformToken) {
          setUserInfo(parsed)
          setWaiting(false)
          return
        }
        localStorage.removeItem('userInfo')
      } catch (e) {
        localStorage.removeItem('userInfo')
      }
    }

    const showLoginRequired = () => {
      localStorage.removeItem('userInfo')
      setLoginRequired(true)
      setWaiting(false)
    }

    const timeout = setTimeout(showLoginRequired, 10000)

    const handler = (event) => {
      if (event.data?.type === 'PLATFORM_LOGIN' && event.data.platformUserId) {
        clearTimeout(timeout)
        if (event.data.platformToken !== PLATFORM_ENTRY_TOKEN) {
          localStorage.removeItem('userInfo')
          setLoginRequired(true)
          setWaiting(false)
          return
        }
        const info = {
          platformUserId: event.data.platformUserId,
          platformToken: '',
          // 兼容蛇形和驼峰两种命名格式
          lanName: event.data.lanName || event.data.lan_name || '',
          regionName: event.data.regionName || event.data.region_name || '',
          staffCode: event.data.staffCode || event.data.staff_code || '',
          staffName: event.data.staffName || event.data.staff_name || '',
          staffPosType: event.data.staffPosType || event.data.staff_pos_type || '',
        }
        issueTestToken(info)
          .then((tokenInfo) => {
            setUserInfo(tokenInfo)
            localStorage.setItem('userInfo', JSON.stringify(tokenInfo))
            setWaiting(false)
          })
          .catch(() => {
            localStorage.removeItem('userInfo')
            setLoginRequired(true)
            setWaiting(false)
          })
      }
    }
    window.addEventListener('message', handler)
    return () => {
      window.removeEventListener('message', handler)
      clearTimeout(timeout)
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
          <a href="/test/login" style={{ color: '#2563eb', textDecoration: 'underline' }}>手动登录</a>
        </div>
      </div>
    )
  }

  return <App userInfo={userInfo} />
}

function AdminRoute({ children }) {
  const token = localStorage.getItem('adminToken')
  if (!token) {
    return <Navigate to="/chat/" replace />
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

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/chat" element={<Navigate to="/chat/" replace />} />
        <Route path="/chat/" element={<ChatRoute />} />
        <Route path="/chat/config" element={<AdminRoute><AdminPage /></AdminRoute>} />
        <Route path="/test" element={<Navigate to="/test/login" replace />} />
        <Route path="/test/login" element={<TestLoginPage />} />
        <Route path="/superlogin" element={<SuperLoginPage />} />
        <Route path="/superconfig" element={<SuperAdminRoute><SuperConfigPage /></SuperAdminRoute>} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
