import React, { useState, useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate, useSearchParams } from 'react-router-dom'
import App from './App'
import LoginPage from './pages/Login/LoginPage'
import AdminPage from './pages/Admin/AdminPage'
import TestLoginPage from './pages/TestLogin/TestLoginPage'
import './styles/variables.css'

function ChatRoute() {
  const [userInfo, setUserInfo] = useState(null)
  const [waiting, setWaiting] = useState(true)
  const [searchParams] = useSearchParams()

  useEffect(() => {
    // 检查 URL 参数中是否有用户信息
    const userIdFromUrl = searchParams.get('userId')
    const staffNameFromUrl = searchParams.get('staffName')
    
    if (userIdFromUrl) {
      // 从 URL 参数直接登录
      setUserInfo({
        platformUserId: userIdFromUrl,
        platformToken: 'url-token',
        lanName: '',
        regionName: '',
        staffCode: '',
        staffName: staffNameFromUrl || userIdFromUrl,
        staffPosType: '',
      })
      setWaiting(false)
      return
    }

    const redirectToLogin = async () => {
      try {
        const res = await fetch('/chat/api/config')
        const config = await res.json()
        window.location.href = config.redirectUrl || '/chat/test/login'
      } catch {
        window.location.href = '/chat/test/login'
      }
    }

    const timeout = setTimeout(redirectToLogin, 5000)

    const handler = (event) => {
      if (event.data?.type === 'PLATFORM_LOGIN' && event.data.platformUserId) {
        clearTimeout(timeout)
        setUserInfo({
          platformUserId: event.data.platformUserId,
          platformToken: event.data.platformToken,
          lanName: event.data.lan_name || '',
          regionName: event.data.region_name || '',
          staffCode: event.data.staff_code || '',
          staffName: event.data.staff_name || '',
          staffPosType: event.data.staff_pos_type || '',
        })
        setWaiting(false)
      }
    }
    window.addEventListener('message', handler)
    return () => {
      window.removeEventListener('message', handler)
      clearTimeout(timeout)
    }
  }, [searchParams])

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
          <a href="/chat/test/login" style={{ color: '#2563eb', textDecoration: 'underline' }}>手动登录</a>
        </div>
      </div>
    )
  }
  
  return <App userInfo={userInfo} />
}

function AdminRoute({ children }) {
  const token = localStorage.getItem('adminToken')
  if (!token) {
    return <Navigate to="/chat/login" replace />
  }
  return children
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/chat" element={<Navigate to="/chat/" replace />} />
        <Route path="/chat/" element={<ChatRoute />} />
        <Route path="/chat/login" element={<LoginPage />} />
        <Route path="/chat/config" element={<AdminRoute><AdminPage /></AdminRoute>} />
        <Route path="/chat/test" element={<Navigate to="/chat/test/login" replace />} />
        <Route path="/chat/test/login" element={<TestLoginPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
