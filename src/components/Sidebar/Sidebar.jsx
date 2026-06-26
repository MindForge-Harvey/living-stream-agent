import styles from './Sidebar.module.css'

export default function Sidebar({ dialogs, activeDialogId, onSelectDialog, onNewChat, onDeleteDialog, open, connectionStatus, userInfo }) {
  const userId = userInfo?.platformUserId
  const staffName = userInfo?.staffName
  const handleLogout = () => {
    localStorage.removeItem('userInfo')
    window.location.reload()
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return ''
    
    const now = new Date()
    const diff = now - date
    
    if (diff < 60000) return '刚刚'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
    
    const shanghaiDate = new Date(date.toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }))
    const month = (shanghaiDate.getMonth() + 1).toString().padStart(2, '0')
    const day = shanghaiDate.getDate().toString().padStart(2, '0')
    return `${month}-${day}`
  }

  const groupDialogsByDate = (dialogs) => {
    const groups = {}
    const now = new Date()
    const today = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }))
    const todayDate = new Date(today.getFullYear(), today.getMonth(), today.getDate())
    const yesterdayDate = new Date(todayDate.getTime() - 86400000)
    
    dialogs.forEach(dialog => {
      const date = new Date(dialog.updatedAt)
      const shanghaiDate = new Date(date.toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }))
      const dialogDate = new Date(shanghaiDate.getFullYear(), shanghaiDate.getMonth(), shanghaiDate.getDate())
      
      let label
      if (dialogDate.getTime() === todayDate.getTime()) {
        label = '今天'
      } else if (dialogDate.getTime() === yesterdayDate.getTime()) {
        label = '昨天'
      } else {
        label = `${(shanghaiDate.getMonth() + 1).toString().padStart(2, '0')}-${shanghaiDate.getDate().toString().padStart(2, '0')}`
      }
      
      if (!groups[label]) groups[label] = []
      groups[label].push(dialog)
    })
    
    return Object.entries(groups)
  }

  const groupedDialogs = groupDialogsByDate(dialogs)

  return (
    <aside className={`${styles.sidebar} ${open ? styles.open : ''}`}>
      <div className={styles.header}>
        <div className={styles.logo}>
          <div className={styles.logoIcon}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
          </div>
          <div>
            <div className={styles.logoText}>直播脚本生成智能体</div>
          </div>
        </div>
        <button className={styles.newChatBtn} onClick={onNewChat}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          新建对话
        </button>
      </div>

      <div className={styles.dialogList}>
        {dialogs.length === 0 ? (
          <div className={styles.emptyTip}>
            <p>暂无对话记录</p>
            <p className={styles.emptySubTip}>点击"新建对话"开始</p>
          </div>
        ) : (
          groupedDialogs.map(([label, groupDialogs]) => (
            <div key={label} className={styles.dialogGroup}>
              <div className={styles.groupLabel}>{label}</div>
              {groupDialogs.map(dialog => (
                <div
                  key={dialog.id}
                  className={`${styles.dialogItem} ${activeDialogId === dialog.id ? styles.dialogActive : ''}`}
                  onClick={() => onSelectDialog(dialog)}
                >
                  <div className={styles.dialogIcon}>🎙️</div>
                  <div className={styles.dialogInfo}>
                    <div className={styles.dialogTitle}>{dialog.title}</div>
                    <div className={styles.dialogMeta}>
                      <span className={styles.toolName}>{dialog.toolName}</span>
                      <span className={styles.dialogTime}>{formatDate(dialog.updatedAt)}</span>
                    </div>
                  </div>
                  <button 
                    className={styles.deleteBtn}
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteDialog(dialog.id)
                    }}
                    title="删除对话"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          ))
        )}
      </div>

      <div className={styles.footer}>
        <div className={styles.statusIndicator}>
          <div className={`${styles.statusDot} ${connectionStatus?.connected ? styles.connected : styles.disconnected}`} />
          <span className={styles.statusText}>{connectionStatus?.connected ? '已连接' : '未连接'}</span>
        </div>
        <div className={styles.userInfo}>
          <div className={styles.userAvatar}>{staffName?.charAt(0)?.toUpperCase() || userId?.charAt(0)?.toUpperCase()}</div>
          <span className={styles.userId}>{staffName || userId}</span>
        </div>
        <button className={styles.logoutBtn} onClick={handleLogout} title="退出登录">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </button>
      </div>
    </aside>
  )
}
