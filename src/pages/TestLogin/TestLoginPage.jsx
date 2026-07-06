import { useState } from 'react'
import styles from './TestLogin.module.css'

const PLATFORM_ENTRY_TOKEN = '5s9D2g7F0k3j6P1r8T4b7N2m5Z9x0C3v7B1n4A6q8w2E5r7t9y1u3i5o7p0a2s4d6f8g'

export default function TestLoginPage() {
  const [userId, setUserId] = useState('')
  const [staffName, setStaffName] = useState('')
  const [password, setPassword] = useState('')

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
      platformToken: PLATFORM_ENTRY_TOKEN,
      lanName: '',
      regionName: '',
      staffCode: '',
      staffName: staffName.trim() || userId.trim(),
      staffPosType: '',
    }

    const iframe = document.createElement('iframe')
    iframe.src = '/chat/'
    iframe.style.display = 'none'
    iframe.setAttribute('aria-hidden', 'true')
    document.body.appendChild(iframe)

    let attempts = 0
    const timer = setInterval(() => {
      attempts += 1
      iframe.contentWindow?.postMessage({
        type: 'PLATFORM_LOGIN',
        ...userInfo
      }, window.location.origin)
      if (attempts >= 30) {
        clearInterval(timer)
      }
    }, 300)

    setTimeout(() => {
      window.open('/chat/', '_blank')
    }, 2500)
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
              打开聊天页面
            </button>
          </div>
        </form>

        <div className={styles.hint}>
          <p>说明：</p>
          <ul>
            <li>登录成功后会打开新的对话页面</li>
            <li>登录信息通过 postMessage 发送给 /chat 页面</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
