import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { exportScript } from '../../api/index'
import { showToast } from '../Toast/Toast'
import styles from './ChatHeader.module.css'

export default function ChatHeader({ tool, onBack, onClear, onMemory, onVersionHistory, onTemplateSelect, dialogId, userId }) {
  const navigate = useNavigate()
  const [exporting, setExporting] = useState(false)
  const [showExportMenu, setShowExportMenu] = useState(false)
  const [enteringAdmin, setEnteringAdmin] = useState(false)

  const handleExport = async (format) => {
    if (!dialogId) {
      showToast('请先选择一个对话', 'error')
      return
    }

    setExporting(true)
    setShowExportMenu(false)
    
    try {
      const blob = await exportScript(dialogId, format)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `直播脚本.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      showToast('导出成功', 'success')
    } catch (err) {
      showToast('导出失败: ' + err.message, 'error')
    } finally {
      setExporting(false)
    }
  }

  const handleAdminEntry = async () => {
    // 优先用 userId 免密登录
    if (userId) {
      setEnteringAdmin(true)
      try {
        const res = await fetch(`/chat/api/admin/auth-by-user?user_id=${encodeURIComponent(userId)}`)
        if (res.ok) {
          const data = await res.json()
          if (data.success && data.token) {
            localStorage.setItem('adminToken', data.token)
            navigate('/chat/config')
            return
          }
        }
      } catch {
        // 静默失败，走下面的正常登录流程
      } finally {
        setEnteringAdmin(false)
      }
    }
    // userId 未绑定或请求失败，跳登录页
    navigate('/chat/login')
  }

  return (
    <div className={styles.header}>
      <button className={styles.backBtn} onClick={onBack}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>
      <div className={styles.toolIcon}>🎙️</div>
      <div className={styles.titleArea}>
        <span className={styles.title}>{tool ? tool.name : '直播脚本生成智能体'}</span>
        {tool && <span className={styles.subtitle}>{tool.desc}</span>}
      </div>
      <div className={styles.actions}>
        {onTemplateSelect && (
          <button className={styles.templateBtn} onClick={onTemplateSelect} title="选择模板">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            模板
          </button>
        )}
        {onVersionHistory && dialogId && (
          <button className={styles.versionBtn} onClick={onVersionHistory} title="脚本版本历史">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            脚本版本历史
          </button>
        )}
        {dialogId && (
          <div className={styles.exportWrapper}>
            <button 
              className={styles.exportBtn} 
              onClick={() => setShowExportMenu(!showExportMenu)}
              disabled={exporting}
              title="导出脚本"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              {exporting ? '导出中...' : '导出'}
            </button>
            {showExportMenu && (
              <div className={styles.exportMenu}>
                <button onClick={() => handleExport('txt')}>导出为 TXT</button>
                <button onClick={() => handleExport('markdown')}>导出为 Markdown</button>
                <button onClick={() => handleExport('docx')}>导出为 Word</button>
              </div>
            )}
          </div>
        )}
        {onMemory && (
          <button className={styles.memoryBtn} onClick={onMemory} title="长期记忆">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a7 7 0 0 1 7 7c0 2.4-1.2 4.5-3 5.7V17a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.3C6.2 13.5 5 11.4 5 9a7 7 0 0 1 7-7z" />
              <line x1="9" y1="21" x2="15" y2="21" />
              <line x1="10" y1="24" x2="14" y2="24" />
            </svg>
            记忆
          </button>
        )}
        {tool && <button onClick={onClear}>清空</button>}
        <button className={styles.adminBtn} onClick={handleAdminEntry} title="后台管理" disabled={enteringAdmin}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </button>
      </div>
    </div>
  )
}
