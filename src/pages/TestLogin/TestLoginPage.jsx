import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import styles from './TestLogin.module.css'

export default function TestLoginPage() {
  const [userId, setUserId] = useState('')
  const [staffName, setStaffName] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()

  const TEST_PASSWORD = '123456'

  const checkPassword = () => {
    if (password !== TEST_PASSWORD) {
      alert('密码错误')
      return false
    }
    return true
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!userId.trim()) {
      alert('请输入用户ID')
      return
    }
    if (!checkPassword()) return

    // 模拟平台登录，发送 postMessage
    const userInfo = {
      platformUserId: userId.trim(),
      platformToken: 'test-token',
      lanName: '',
      regionName: '',
      staffCode: '',
      staffName: staffName.trim() || userId.trim(),
      staffPosType: '',
    }

    // 打开新窗口并发送登录信息
    const chatWindow = window.open('/chat/', '_blank')
    
    // 等待页面加载后发送消息
    setTimeout(() => {
      chatWindow.postMessage({
        type: 'PLATFORM_LOGIN',
        ...userInfo
      }, window.location.origin)
    }, 1000)

    // 也可以直接跳转
    // navigate('/chat/')
  }

  const handleDirectLogin = () => {
    if (!userId.trim()) {
      alert('请输入用户ID')
      return
    }
    if (!checkPassword()) return

    // 直接跳转并传递参数
    const params = new URLSearchParams({
      userId: userId.trim(),
      staffName: staffName.trim() || userId.trim()
    })
    navigate(`/chat/?${params.toString()}`)
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.header}>
          <div className={styles.logo}>🎙️</div>
          <h1 className={styles.title}>测试登录</h1>
          <p className={styles.subtitle}>输入用户信息进入直播脚本生成智能体</p>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label className={styles.label}>用户ID <span className={styles.required}>*</span></label>
            <input
              className={styles.input}
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="请输入用户ID（如：test001）"
              autoFocus
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>姓名（可选）</label>
            <input
              className={styles.input}
              type="text"
              value={staffName}
              onChange={(e) => setStaffName(e.target.value)}
              placeholder="请输入姓名"
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>密码 <span className={styles.required}>*</span></label>
            <input
              className={styles.input}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入访问密码"
            />
          </div>

          <div className={styles.actions}>
            <button className={styles.submitBtn} type="submit">
              新窗口打开
            </button>
            <button 
              className={styles.directBtn} 
              type="button"
              onClick={handleDirectLogin}
            >
              直接进入
            </button>
          </div>
        </form>

        <div className={styles.hint}>
          <p>说明：</p>
          <ul>
            <li>新窗口打开：会在新窗口中打开对话页面</li>
            <li>直接进入：在当前窗口直接进入</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
