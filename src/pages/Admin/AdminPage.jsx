import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import styles from './Admin.module.css'

function MarkdownContent({ content }) {
  const html = useMemo(() => {
    const processed = (content || '').replace(/\\n/g, '\n')
    const result = marked.parse(processed.replace(/<br\s*\/?>/g, '  \n'), {
      breaks: true,
      gfm: true
    })
    return typeof result === 'string' ? result : ''
  }, [content])

  return (
    <div 
      className={styles.markdownContent} 
      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }} 
    />
  )
}

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState(() => {
    return localStorage.getItem('adminActiveTab') || 'statistics'
  })
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false)
  const [passwordData, setPasswordData] = useState({ oldPassword: '', newPassword: '', confirmPassword: '' })
  const [stats, setStats] = useState({ overview: null, users: [], tools: [] })
  const [userDetailOpen, setUserDetailOpen] = useState(false)
  const [selectedUserId, setSelectedUserId] = useState(null)
  const [selectedUser, setSelectedUser] = useState(null)
  const [userDialogs, setUserDialogs] = useState([])
  const [selectedDialog, setSelectedDialog] = useState(null)
  const [dialogMessages, setDialogMessages] = useState([])
  const [loadingDialogs, setLoadingDialogs] = useState(false)
  const [loadingMessages, setLoadingMessages] = useState(false)

  const [statsFilter, setStatsFilter] = useState({ keyword: '', lanName: '', regionName: '', staffPosType: '' })
  const [statsSort, setStatsSort] = useState({ sortBy: 'dialogCount', sortOrder: 'desc' })
  const [statsPage, setStatsPage] = useState(1)
  const [statsPagination, setStatsPagination] = useState({ total: 0, totalPages: 0 })
  const [filterOptions, setFilterOptions] = useState({ lanNames: [], regionNames: [], staffPosTypes: [] })
  const navigate = useNavigate()
  const pageSize = 10

  const [forbiddenWords, setForbiddenWords] = useState([])
  const [forbiddenWordDialogOpen, setForbiddenWordDialogOpen] = useState(false)
  const [forbiddenWordEditItem, setForbiddenWordEditItem] = useState(null)
  const [forbiddenWordFormData, setForbiddenWordFormData] = useState({ word: '', replacement: '***', level: '' })
  const [forbiddenWordSearchTerm, setForbiddenWordSearchTerm] = useState('')
  const [forbiddenWordCurrentPage, setForbiddenWordCurrentPage] = useState(1)
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('adminToken')
    if (!token) {
      navigate('/chat/login')
      return
    }
    loadStats()
    loadFilterOptions()
    loadForbiddenWords()
  }, [navigate])

  const loadForbiddenWords = async () => {
    try {
      const token = localStorage.getItem('adminToken')
      const res = await fetch('/chat/api/forbidden-words', {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
      const data = await res.json()
      setForbiddenWords(data)
    } catch (err) {
      console.error('加载违禁词失败:', err)
    }
  }

  const loadStats = async (filters = statsFilter, sort = statsSort, page = statsPage) => {
    try {
      const token = localStorage.getItem('adminToken')
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {}

      const params = new URLSearchParams()
      if (filters.keyword) params.set('keyword', filters.keyword)
      if (filters.lanName) params.set('lanName', filters.lanName)
      if (filters.regionName) params.set('regionName', filters.regionName)
      if (filters.staffPosType) params.set('staffPosType', filters.staffPosType)
      params.set('sortBy', sort.sortBy)
      params.set('sortOrder', sort.sortOrder)
      params.set('page', page)
      params.set('pageSize', pageSize)

      const [overviewRes, usersRes] = await Promise.all([
        fetch('/chat/api/dialogs/stats/overview', { headers }),
        fetch(`/chat/api/dialogs/stats/users?${params}`, { headers }),
      ])

      const overview = overviewRes.ok ? await overviewRes.json() : null
      const usersData = usersRes.ok ? await usersRes.json() : { items: [], total: 0, totalPages: 0 }

      setStats({ overview, users: usersData.items || usersData, tools: [] })
      setStatsPagination({ total: usersData.total || 0, totalPages: usersData.totalPages || 0 })
    } catch (err) {
      console.error('加载统计数据失败:', err)
    }
  }

  const loadFilterOptions = async () => {
    try {
      const token = localStorage.getItem('adminToken')
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {}
      const res = await fetch('/chat/api/dialogs/stats/filters', { headers })
      if (res.ok) {
        const data = await res.json()
        setFilterOptions(data)
      }
    } catch (err) {
      console.error('加载筛选选项失败:', err)
    }
  }

  const handleStatsFilterChange = (key, value) => {
    const newFilter = { ...statsFilter, [key]: value }
    setStatsFilter(newFilter)
    setStatsPage(1)
    loadStats(newFilter, statsSort, 1)
  }

  const handleStatsSort = (field) => {
    const newSort = statsSort.sortBy === field
      ? { ...statsSort, sortOrder: statsSort.sortOrder === 'desc' ? 'asc' : 'desc' }
      : { sortBy: field, sortOrder: 'desc' }
    setStatsSort(newSort)
    setStatsPage(1)
    loadStats(statsFilter, newSort, 1)
  }

  const handleStatsPageChange = (newPage) => {
    setStatsPage(newPage)
    loadStats(statsFilter, statsSort, newPage)
  }

  const handleExportUsers = async () => {
    try {
      const token = localStorage.getItem('adminToken')
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {}
      const params = new URLSearchParams()
      if (statsFilter.keyword) params.set('keyword', statsFilter.keyword)
      if (statsFilter.lanName) params.set('lanName', statsFilter.lanName)
      if (statsFilter.regionName) params.set('regionName', statsFilter.regionName)
      if (statsFilter.staffPosType) params.set('staffPosType', statsFilter.staffPosType)
      params.set('sortBy', statsSort.sortBy)
      params.set('sortOrder', statsSort.sortOrder)

      const res = await fetch(`/chat/api/dialogs/stats/users/export?${params}`, { headers })
      if (res.ok) {
        const blob = await res.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `用户使用统计_${new Date().toISOString().slice(0, 10)}.csv`
        a.click()
        window.URL.revokeObjectURL(url)
      } else {
        alert('导出失败')
      }
    } catch (err) {
      alert('导出失败: ' + err.message)
    }
  }

  const renderSortIcon = (field) => {
    if (statsSort.sortBy !== field) return <span className={styles.sortIcon}>↕</span>
    return <span className={styles.sortIcon}>{statsSort.sortOrder === 'desc' ? '↓' : '↑'}</span>
  }

  const handleUserClick = async (userId) => {
    setSelectedUserId(userId)
    const user = stats.users.find(u => u.userId === userId)
    setSelectedUser(user || null)
    setUserDetailOpen(true)
    setSelectedDialog(null)
    setDialogMessages([])
    setLoadingDialogs(true)
    
    try {
      const res = await fetch(`/chat/api/dialogs?userId=${userId}`)
      if (res.ok) {
        const data = await res.json()
        setUserDialogs(data.items || data)
      } else {
        setUserDialogs([])
      }
    } catch (err) {
      console.error('获取用户对话失败:', err)
      setUserDialogs([])
    } finally {
      setLoadingDialogs(false)
    }
  }

  const handleDialogClick = async (dialog) => {
    setSelectedDialog(dialog)
    setLoadingMessages(true)
    
    try {
      const res = await fetch(`/chat/api/dialogs/${dialog.id}/messages`)
      if (res.ok) {
        const data = await res.json()
        setDialogMessages(data)
      } else {
        setDialogMessages([])
      }
    } catch (err) {
      console.error('获取对话消息失败:', err)
      setDialogMessages([])
    } finally {
      setLoadingMessages(false)
    }
  }

  const handleBackToDialogs = () => {
    setSelectedDialog(null)
    setDialogMessages([])
  }

  const handleCloseUserDetail = () => {
    setUserDetailOpen(false)
    setSelectedUserId(null)
    setSelectedUser(null)
    setUserDialogs([])
    setSelectedDialog(null)
    setDialogMessages([])
  }

  const handleLogout = () => {
    localStorage.removeItem('adminToken')
    navigate('/chat/')
  }

  const handleAddForbiddenWord = () => {
    setForbiddenWordEditItem(null)
    setForbiddenWordFormData({ word: '', replacement: '***', level: '' })
    setForbiddenWordDialogOpen(true)
  }

  const handleEditForbiddenWord = (item) => {
    setForbiddenWordEditItem(item)
    setForbiddenWordFormData({ id: item.id, word: item.word, replacement: item.replacement, level: item.level || '' })
    setForbiddenWordDialogOpen(true)
  }

  const handleDeleteForbiddenWord = async (id) => {
    if (!confirm('确定删除此违禁词？')) return
    try {
      const token = localStorage.getItem('adminToken')
      const res = await fetch(`/chat/api/forbidden-words/${id}`, { 
        method: 'DELETE',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
      if (res.ok) {
        await loadForbiddenWords()
      } else {
        const err = await res.json()
        alert(err.error || '删除失败')
      }
    } catch (err) {
      alert('删除失败: ' + err.message)
    }
  }

  const handleSaveForbiddenWord = async (e) => {
    e.preventDefault()
    if (!forbiddenWordFormData.word.trim()) {
      alert('请输入违禁词')
      return
    }

    try {
      const token = localStorage.getItem('adminToken')
      const url = forbiddenWordEditItem 
        ? `/chat/api/forbidden-words/${forbiddenWordEditItem.id}` 
        : '/chat/api/forbidden-words'
      const method = forbiddenWordEditItem ? 'PUT' : 'POST'

      const res = await fetch(url, {
        method,
        headers: { 
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify(forbiddenWordFormData)
      })

      if (res.ok) {
        await loadForbiddenWords()
        setForbiddenWordDialogOpen(false)
        setForbiddenWordEditItem(null)
      } else {
        const err = await res.json()
        alert(err.detail || '保存失败')
      }
    } catch (err) {
      alert('保存失败: ' + err.message)
    }
  }

  const handleImportForbiddenWords = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    setImporting(true)
    try {
      const token = localStorage.getItem('adminToken')
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch('/chat/api/forbidden-words/import', {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        body: formData
      })

      if (res.ok) {
        const data = await res.json()
        alert(`导入成功！新增 ${data.imported} 个，跳过 ${data.skipped} 个重复词`)
        await loadForbiddenWords()
      } else {
        const err = await res.json()
        alert(err.detail || '导入失败')
      }
    } catch (err) {
      alert('导入失败: ' + err.message)
    } finally {
      setImporting(false)
      e.target.value = ''
    }
  }

  const handleDeleteAllForbiddenWords = async () => {
    if (!confirm('确定清空所有违禁词？此操作不可恢复！')) return
    try {
      const token = localStorage.getItem('adminToken')
      const res = await fetch('/chat/api/forbidden-words/batch/all', { 
        method: 'DELETE',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
      if (res.ok) {
        await loadForbiddenWords()
        alert('已清空所有违禁词')
      } else {
        const err = await res.json()
        alert(err.error || '清空失败')
      }
    } catch (err) {
      alert('清空失败: ' + err.message)
    }
  }

  const handleChangePassword = async (e) => {
    e.preventDefault()
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      alert('两次输入的密码不一致')
      return
    }
    if (passwordData.newPassword.length < 6) {
      alert('新密码长度不能少于6位')
      return
    }

    try {
      const token = localStorage.getItem('adminToken')
      const res = await fetch('/chat/api/admin/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          old_password: passwordData.oldPassword,
          new_password: passwordData.newPassword
        })
      })

      const data = await res.json()
      if (res.ok) {
        alert('密码修改成功')
        setPasswordDialogOpen(false)
        setPasswordData({ oldPassword: '', newPassword: '', confirmPassword: '' })
      } else {
        alert(data.detail || '修改失败')
      }
    } catch (err) {
      alert('修改失败: ' + err.message)
    }
  }

  const tabs = [
    { key: 'statistics', label: '用户使用统计', icon: '📊' },
    { key: 'forbidden', label: '违禁词配置', icon: '🚫' }
  ]

  const handleTabChange = (tabKey) => {
    setActiveTab(tabKey)
    localStorage.setItem('adminActiveTab', tabKey)
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.logoIcon}>🎙️</span>
          <h1 className={styles.title}>后台管理</h1>
        </div>
        <div className={styles.headerRight}>
          <button className={styles.homeBtn} onClick={() => navigate('/chat/')}>返回首页</button>
          <button className={styles.passwordBtn} onClick={() => setPasswordDialogOpen(true)}>修改密码</button>
          <button className={styles.logoutBtn} onClick={handleLogout}>退出登录</button>
        </div>
      </header>

      <div className={styles.layout}>
        <aside className={styles.sidebar}>
          <nav className={styles.tabNav}>
            {tabs.map(tab => (
              <button
                key={tab.key}
                className={`${styles.tabBtn} ${activeTab === tab.key ? styles.tabActive : ''}`}
                onClick={() => handleTabChange(tab.key)}
              >
                <span className={styles.tabIcon}>{tab.icon}</span>
                <span className={styles.tabLabel}>{tab.label}</span>
              </button>
            ))}
          </nav>
        </aside>

        <main className={styles.main}>
          {activeTab === 'forbidden' && (
            <>
              <div className={styles.toolbar}>
                <div className={styles.searchBox}>
                  <svg className={styles.searchIcon} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                  <input
                    className={styles.searchInput}
                    type="text"
                    placeholder="搜索违禁词..."
                    value={forbiddenWordSearchTerm}
                    onChange={(e) => { setForbiddenWordSearchTerm(e.target.value); setForbiddenWordCurrentPage(1) }}
                  />
                  {forbiddenWordSearchTerm && (
                    <button className={styles.clearBtn} onClick={() => { setForbiddenWordSearchTerm(''); setForbiddenWordCurrentPage(1) }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  )}
                </div>
                <div className={styles.toolbarActions}>
                  <label className={styles.importBtn}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="17 8 12 3 7 8" />
                      <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                    {importing ? '导入中...' : '导入Excel'}
                    <input
                      type="file"
                      accept=".xlsx,.xls"
                      onChange={handleImportForbiddenWords}
                      style={{ display: 'none' }}
                      disabled={importing}
                    />
                  </label>
                  <button className={styles.addBtn} onClick={handleAddForbiddenWord}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="12" y1="5" x2="12" y2="19" />
                      <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                    新增违禁词
                  </button>
                  {forbiddenWords.length > 0 && (
                    <button className={styles.clearAllBtn} onClick={handleDeleteAllForbiddenWords}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                      清空全部
                    </button>
                  )}
                </div>
              </div>

                <div className={styles.importHint}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
                Excel格式：第一列为违禁词，第二列为替换词（可选，默认***），第三列为级别（single/multi，可选，自动判断）
              </div>

              <div className={styles.tableWrapper}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>违禁词</th>
                      <th>替换词</th>
                      <th>级别</th>
                      <th>创建时间</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(() => {
                      const filtered = forbiddenWords.filter(item => 
                        !forbiddenWordSearchTerm || item.word.includes(forbiddenWordSearchTerm)
                      )
                      const totalPages = Math.ceil(filtered.length / pageSize)
                      const paginated = filtered.slice(
                        (forbiddenWordCurrentPage - 1) * pageSize,
                        forbiddenWordCurrentPage * pageSize
                      )
                      
                      if (paginated.length === 0) {
                        return (
                          <tr>
                            <td colSpan="5" className={styles.empty}>
                              {forbiddenWordSearchTerm ? '没有找到匹配的违禁词' : '暂无违禁词，点击上方按钮添加或导入'}
                            </td>
                          </tr>
                        )
                      }
                      
                      return paginated.map((item) => (
                        <tr key={item.id}>
                          <td className={styles.wordCell}>{item.word}</td>
                          <td>{item.replacement}</td>
                          <td>{item.level === 'single' ? '单字' : '多字'}</td>
                          <td>{new Date(item.createdAt).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}</td>
                          <td className={styles.actions}>
                            <button className={styles.editBtn} onClick={() => handleEditForbiddenWord(item)}>编辑</button>
                            <button className={styles.deleteBtn} onClick={() => handleDeleteForbiddenWord(item.id)}>删除</button>
                          </td>
                        </tr>
                      ))
                    })()}
                  </tbody>
                </table>
              </div>

              {(() => {
                const filtered = forbiddenWords.filter(item => 
                  !forbiddenWordSearchTerm || item.word.includes(forbiddenWordSearchTerm)
                )
                const totalPages = Math.ceil(filtered.length / pageSize)
                
                if (totalPages <= 1) return null
                
                return (
                  <div className={styles.pagination}>
                    <div className={styles.pageInfo}>
                      共 <span className={styles.pageHighlight}>{filtered.length}</span> 条，
                      共 <span className={styles.pageHighlight}>{totalPages}</span> 页，
                      当前第 <span className={styles.pageHighlight}>{forbiddenWordCurrentPage}</span> 页
                    </div>
                    <div className={styles.pageButtons}>
                      <button
                        className={styles.pageBtn}
                        disabled={forbiddenWordCurrentPage === 1}
                        onClick={() => setForbiddenWordCurrentPage(prev => prev - 1)}
                      >
                        上一页
                      </button>
                      <button
                        className={styles.pageBtn}
                        disabled={forbiddenWordCurrentPage === totalPages}
                        onClick={() => setForbiddenWordCurrentPage(prev => prev + 1)}
                      >
                        下一页
                      </button>
                    </div>
                  </div>
                )
              })()}
            </>
          )}

          {activeTab === 'statistics' && (
            <div className={styles.statsContainer}>
              <div className={styles.statsOverview}>
                <div className={styles.statCard}>
                  <div className={styles.statIcon}>👥</div>
                  <div className={styles.statInfo}>
                    <div className={styles.statValue}>{stats.overview?.totalUsers || 0}</div>
                    <div className={styles.statLabel}>用户数</div>
                  </div>
                </div>
                <div className={styles.statCard}>
                  <div className={styles.statIcon}>💬</div>
                  <div className={styles.statInfo}>
                    <div className={styles.statValue}>{stats.overview?.totalDialogs || 0}</div>
                    <div className={styles.statLabel}>对话数</div>
                  </div>
                </div>
                <div className={styles.statCard}>
                  <div className={styles.statIcon}>📨</div>
                  <div className={styles.statInfo}>
                    <div className={styles.statValue}>{stats.overview?.totalMessages || 0}</div>
                    <div className={styles.statLabel}>消息数</div>
                  </div>
                </div>
              </div>

              <div className={styles.statsSection}>
                <div className={styles.statsSectionHeader}>
                  <h3 className={styles.sectionTitle}>用户使用明细</h3>
                  <button className={styles.exportBtn} onClick={handleExportUsers}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                    导出CSV
                  </button>
                </div>

                <div className={styles.statsFilterBar}>
                  <div className={styles.filterSearchBox}>
                    <svg className={styles.filterSearchIcon} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="11" cy="11" r="8" />
                      <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                      className={styles.filterInput}
                      type="text"
                      placeholder="搜索姓名/工号/用户ID..."
                      value={statsFilter.keyword}
                      onChange={(e) => handleStatsFilterChange('keyword', e.target.value)}
                    />
                    {statsFilter.keyword && (
                      <button className={styles.clearBtn} onClick={() => handleStatsFilterChange('keyword', '')}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <line x1="18" y1="6" x2="6" y2="18" />
                          <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                      </button>
                    )}
                  </div>
                  <select
                    className={styles.filterSelect}
                    value={statsFilter.lanName}
                    onChange={(e) => handleStatsFilterChange('lanName', e.target.value)}
                  >
                    <option value="">全部地市</option>
                    {filterOptions.lanNames.map(name => (
                      <option key={name} value={name}>{name}</option>
                    ))}
                  </select>
                  <select
                    className={styles.filterSelect}
                    value={statsFilter.regionName}
                    onChange={(e) => handleStatsFilterChange('regionName', e.target.value)}
                  >
                    <option value="">全部区县</option>
                    {filterOptions.regionNames.map(name => (
                      <option key={name} value={name}>{name}</option>
                    ))}
                  </select>
                  <select
                    className={styles.filterSelect}
                    value={statsFilter.staffPosType}
                    onChange={(e) => handleStatsFilterChange('staffPosType', e.target.value)}
                  >
                    <option value="">全部岗位</option>
                    {filterOptions.staffPosTypes.map(name => (
                      <option key={name} value={name}>{name}</option>
                    ))}
                  </select>
                </div>

                <div className={styles.tableWrapper}>
                  <table className={styles.statsTable}>
                    <thead>
                      <tr>
                        <th>用户ID</th>
                        <th className={styles.sortableTh} onClick={() => handleStatsSort('staffName')}>姓名 {renderSortIcon('staffName')}</th>
                        <th>工号</th>
                        <th>岗位</th>
                        <th className={styles.sortableTh} onClick={() => handleStatsSort('lanName')}>地市 {renderSortIcon('lanName')}</th>
                        <th className={styles.sortableTh} onClick={() => handleStatsSort('regionName')}>区县 {renderSortIcon('regionName')}</th>
                        <th className={styles.sortableTh} onClick={() => handleStatsSort('dialogCount')}>对话数 {renderSortIcon('dialogCount')}</th>
                        <th className={styles.sortableTh} onClick={() => handleStatsSort('totalRequests')}>消息数 {renderSortIcon('totalRequests')}</th>
                        <th className={styles.sortableTh} onClick={() => handleStatsSort('firstUsed')}>首次使用 {renderSortIcon('firstUsed')}</th>
                        <th className={styles.sortableTh} onClick={() => handleStatsSort('lastUsed')}>最近使用 {renderSortIcon('lastUsed')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.users.length === 0 ? (
                        <tr>
                          <td colSpan="10" className={styles.statsEmpty}>暂无数据</td>
                        </tr>
                      ) : (
                        stats.users.map((user) => (
                          <tr key={user.userId}>
                            <td>
                              <button
                                className={styles.userIdBtn}
                                onClick={() => handleUserClick(user.userId)}
                              >
                                {user.userId}
                              </button>
                            </td>
                            <td>{user.staffName || '-'}</td>
                            <td>{user.staffCode || '-'}</td>
                            <td>{user.staffPosType || '-'}</td>
                            <td>{user.lanName || '-'}</td>
                            <td>{user.regionName || '-'}</td>
                            <td>{user.dialogCount}</td>
                            <td>{user.totalRequests}</td>
                            <td>{user.firstUsed ? new Date(user.firstUsed).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '-'}</td>
                            <td>{user.lastUsed ? new Date(user.lastUsed).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '-'}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>

                {statsPagination.totalPages > 1 && (
                  <div className={styles.pagination}>
                    <div className={styles.pageInfo}>
                      共 <span className={styles.pageHighlight}>{statsPagination.total}</span> 条，
                      共 <span className={styles.pageHighlight}>{statsPagination.totalPages}</span> 页，
                      当前第 <span className={styles.pageHighlight}>{statsPage}</span> 页
                    </div>
                    <div className={styles.pageButtons}>
                      <button
                        className={styles.pageBtn}
                        disabled={statsPage === 1}
                        onClick={() => handleStatsPageChange(statsPage - 1)}
                      >
                        上一页
                      </button>
                      <button
                        className={styles.pageBtn}
                        disabled={statsPage === statsPagination.totalPages}
                        onClick={() => handleStatsPageChange(statsPage + 1)}
                      >
                        下一页
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </main>
      </div>

      {passwordDialogOpen && (
        <div className={styles.overlay} onClick={() => setPasswordDialogOpen(false)}>
          <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
            <div className={styles.dialogHeader}>
              <h3>修改密码</h3>
              <button className={styles.closeBtn} onClick={() => setPasswordDialogOpen(false)}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <form className={styles.form} onSubmit={handleChangePassword}>
              <div className={styles.field}>
                <label className={styles.label}>原密码</label>
                <input
                  className={styles.input}
                  type="password"
                  value={passwordData.oldPassword}
                  onChange={(e) => setPasswordData(prev => ({ ...prev, oldPassword: e.target.value }))}
                  placeholder="请输入原密码"
                />
              </div>

              <div className={styles.field}>
                <label className={styles.label}>新密码</label>
                <input
                  className={styles.input}
                  type="password"
                  value={passwordData.newPassword}
                  onChange={(e) => setPasswordData(prev => ({ ...prev, newPassword: e.target.value }))}
                  placeholder="请输入新密码（至少6位）"
                />
              </div>

              <div className={styles.field}>
                <label className={styles.label}>确认新密码</label>
                <input
                  className={styles.input}
                  type="password"
                  value={passwordData.confirmPassword}
                  onChange={(e) => setPasswordData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                  placeholder="请再次输入新密码"
                />
              </div>

              <div className={styles.dialogActions}>
                <button type="button" className={styles.cancelBtn} onClick={() => setPasswordDialogOpen(false)}>取消</button>
                <button type="submit" className={styles.saveBtn}>确认修改</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {forbiddenWordDialogOpen && (
        <div className={styles.overlay} onClick={() => setForbiddenWordDialogOpen(false)}>
          <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
            <div className={styles.dialogHeader}>
              <h3>{forbiddenWordEditItem ? '编辑违禁词' : '新增违禁词'}</h3>
              <button className={styles.closeBtn} onClick={() => setForbiddenWordDialogOpen(false)}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <form className={styles.form} onSubmit={handleSaveForbiddenWord}>
              <div className={styles.field}>
                <label className={styles.label}>违禁词 <span className={styles.required}>*</span></label>
                <input
                  className={styles.input}
                  value={forbiddenWordFormData.word}
                  onChange={(e) => setForbiddenWordFormData(prev => ({ ...prev, word: e.target.value }))}
                  placeholder="输入违禁词"
                />
              </div>

              <div className={styles.field}>
                <label className={styles.label}>替换词</label>
                <input
                  className={styles.input}
                  value={forbiddenWordFormData.replacement}
                  onChange={(e) => setForbiddenWordFormData(prev => ({ ...prev, replacement: e.target.value }))}
                  placeholder="输入替换词（默认为***）"
                />
                <div className={styles.hint}>检测到违禁词时将替换为此词</div>
              </div>

              <div className={styles.field}>
                <label className={styles.label}>级别</label>
                <select
                  className={styles.input}
                  value={forbiddenWordFormData.level}
                  onChange={(e) => setForbiddenWordFormData(prev => ({ ...prev, level: e.target.value }))}
                >
                  <option value="">自动判断（按字数）</option>
                  <option value="single">单字（仅提示 LLM，不做规则替换）</option>
                  <option value="multi">多字（LLM 提示 + 规则替换）</option>
                </select>
                <div className={styles.hint}>单字如"最"，只在 prompt 中提示 LLM；多字会额外做规则替换</div>
              </div>

              <div className={styles.dialogActions}>
                <button type="button" className={styles.cancelBtn} onClick={() => setForbiddenWordDialogOpen(false)}>取消</button>
                <button type="submit" className={styles.saveBtn}>保存</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {userDetailOpen && (
        <div className={styles.overlay} onClick={handleCloseUserDetail}>
          <div className={styles.userDetailDialog} onClick={(e) => e.stopPropagation()}>
            <div className={styles.dialogHeader}>
              <h3>
                {selectedDialog ? (
                  <span>
                    <button className={styles.backBtn} onClick={handleBackToDialogs}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="15 18 9 12 15 6" />
                      </svg>
                      返回
                    </button>
                    对话详情
                  </span>
                ) : (
                  <span>
                    {selectedUser?.staffName ? `${selectedUser.staffName} 的对话列表` : `用户 ${selectedUserId} 的对话列表`}
                  </span>
                )}
              </h3>
              <button className={styles.closeBtn} onClick={handleCloseUserDetail}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className={styles.userDetailContent}>
              {!selectedDialog ? (
                loadingDialogs ? (
                  <div className={styles.loading}>加载中...</div>
                ) : (
                  <>
                    {selectedUser && (selectedUser.staffName || selectedUser.staffCode || selectedUser.lanName) && (
                      <div className={styles.userInfoCard}>
                        {selectedUser.staffName && <span>姓名: {selectedUser.staffName}</span>}
                        {selectedUser.staffCode && <span>工号: {selectedUser.staffCode}</span>}
                        {selectedUser.staffPosType && <span>岗位: {selectedUser.staffPosType}</span>}
                        {selectedUser.lanName && <span>地市: {selectedUser.lanName}</span>}
                        {selectedUser.regionName && <span>区县: {selectedUser.regionName}</span>}
                      </div>
                    )}
                    {userDialogs.length === 0 ? (
                      <div className={styles.emptyState}>该用户暂无对话记录</div>
                    ) : (
                      <div className={styles.dialogList}>
                        {userDialogs.map((dialog) => (
                          <div 
                            key={dialog.id} 
                            className={styles.dialogItem}
                            onClick={() => handleDialogClick(dialog)}
                          >
                            <div className={styles.dialogItemHeader}>
                              <span className={styles.dialogTitle}>{dialog.title}</span>
                              <span className={styles.dialogTime}>
                                {new Date(dialog.updatedAt).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}
                              </span>
                            </div>
                            <div className={styles.dialogItemMeta}>
                              <span className={styles.dialogTool}>工具: {dialog.toolName}</span>
                              <span className={styles.dialogCount}>消息数: {dialog.requestCount}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )
              ) : (
                loadingMessages ? (
                  <div className={styles.loading}>加载中...</div>
                ) : dialogMessages.length === 0 ? (
                  <div className={styles.emptyState}>该对话暂无消息</div>
                ) : (
                  <div className={styles.messageList}>
                    <div className={styles.dialogInfo}>
                      <h4>{selectedDialog.title}</h4>
                      <span>工具: {selectedDialog.toolName}</span>
                    </div>
                    {dialogMessages.map((msg) => (
                      <div 
                        key={msg.id} 
                        className={`${styles.messageItem} ${msg.role === 'user' ? styles.userMessage : styles.assistantMessage}`}
                      >
                        <div className={styles.messageRole}>
                          {msg.role === 'user' ? '用户' : '助手'}
                        </div>
                        <div className={styles.messageContent}>
                          {msg.role === 'user' ? msg.content : <MarkdownContent content={msg.content} />}
                        </div>
                        <div className={styles.messageTime}>
                          {new Date(msg.createdAt).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}
                        </div>
                      </div>
                    ))}
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
