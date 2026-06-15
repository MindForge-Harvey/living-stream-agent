import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import styles from './Login.module.css'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = await fetch('/chat/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })

      const data = await res.json()

      if (res.ok && data.success) {
        localStorage.setItem('adminToken', data.token)
        navigate('/chat/config')
      } else {
        setError(data.error || '登录失败')
      }
    } catch (err) {
      setError('网络错误: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.header}>
          <div className={styles.logo}>🎙️</div>
          <h1 className={styles.title}>后台管理</h1>
          <p className={styles.subtitle}>请登录以继续</p>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label className={styles.label}>用户名</label>
            <input
              className={styles.input}
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入用户名"
              autoFocus
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>密码</label>
            <input
              className={styles.input}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
            />
          </div>

          {error && <div className={styles.error}>{error}</div>}

          <button className={styles.submitBtn} type="submit" disabled={loading}>
            {loading ? '登录中...' : '登录'}
          </button>
        </form>

        <button className={styles.backBtn} onClick={() => navigate('/chat/')}>
          返回首页
        </button>
      </div>
    </div>
  )
}
