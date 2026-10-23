import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiUrl } from '../../api/base'
import styles from './SuperAdmin.module.css'

export default function SuperConfigPage() {
  const [activeTab, setActiveTab] = useState('admins')
  const [admins, setAdmins] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [stats, setStats] = useState({ overview: null, users: [] })
  const [statsFilter, setStatsFilter] = useState({ keyword: '', lanName: '', regionName: '', staffPosType: '' })
  const [statsSort, setStatsSort] = useState({ sortBy: 'dialogCount', sortOrder: 'desc' })
  const [statsPage, setStatsPage] = useState(1)
  const [statsPagination, setStatsPagination] = useState({ total: 0, totalPages: 0 })
  const [filterOptions, setFilterOptions] = useState({ lanNames: [], regionNames: [], staffPosTypes: [] })
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showBindModal, setShowBindModal] = useState(false)
  const [selectedAdmin, setSelectedAdmin] = useState(null)
  const [createKeyword, setCreateKeyword] = useState('')
  const [createResults, setCreateResults] = useState([])
  const [createSearching, setCreateSearching] = useState(false)
  const [selectedCreateUser, setSelectedCreateUser] = useState(null)
  const [bindKeyword, setBindKeyword] = useState('')
  const [bindResults, setBindResults] = useState([])
  const [bindSearching, setBindSearching] = useState(false)
  const [selectedBindUser, setSelectedBindUser] = useState(null)
  const navigate = useNavigate()
  const pageSize = 10
  const debounceTimerRef = useRef(null)

  const token = localStorage.getItem('superAdminToken')

  useEffect(() => {
    if (!token) {
      navigate('/superlogin')
      return
    }
    fetchAdmins()
    loadStats()
    loadFilterOptions()

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [token, navigate])

  useEffect(() => {
    if (!showCreateModal || !createKeyword.trim()) {
      setCreateResults([])
      setCreateSearching(false)
      return
    }

    const timer = setTimeout(() => {
      searchPlatformUsers(createKeyword, setCreateResults, setCreateSearching)
    }, 300)

    return () => clearTimeout(timer)
  }, [showCreateModal, createKeyword])

  useEffect(() => {
    if (!showBindModal || !bindKeyword.trim()) {
      setBindResults([])
      setBindSearching(false)
      return
    }

    const timer = setTimeout(() => {
      searchPlatformUsers(bindKeyword, setBindResults, setBindSearching)
    }, 300)

    return () => clearTimeout(timer)
  }, [showBindModal, bindKeyword])

  const searchPlatformUsers = async (keyword, setResults, setSearching) => {
    setSearching(true)
    try {
      const res = await fetch(apiUrl(`/api/super-admin/platform-users/search?q=${encodeURIComponent(keyword.trim())}`), {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const data = await res.json()

      if (res.ok) {
        setResults(data)
      } else {
        setError(data.detail || '搜索用户失败')
        setResults([])
      }
    } catch (err) {
      setError('网络错误: ' + err.message)
      setResults([])
    } finally {
      setSearching(false)
    }
  }

  const fetchAdmins = async () => {
    try {
      const res = await fetch(apiUrl('/api/super-admin/admins'), {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (res.status === 401) {
        localStorage.removeItem('superAdminToken')
        navigate('/superlogin')
        return
      }

      const data = await res.json()
      if (res.ok) {
        setAdmins(data)
      } else {
        setError(data.detail || '获取管理员列表失败')
      }
    } catch (err) {
      setError('网络错误: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const buildStatsParams = (filters, sort, page = null) => {
    const params = new URLSearchParams()
    if (filters.keyword) params.set('keyword', filters.keyword)
    if (filters.lanName) params.set('lanName', filters.lanName)
    if (filters.regionName) params.set('regionName', filters.regionName)
    if (filters.staffPosType) params.set('staffPosType', filters.staffPosType)
    params.set('sortBy', sort.sortBy)
    params.set('sortOrder', sort.sortOrder)
    if (page !== null) {
      params.set('page', page)
      params.set('pageSize', pageSize)
    }
    return params
  }

  const handleUnauthorized = (res) => {
    if (res.status !== 401) return false
    localStorage.removeItem('superAdminToken')
    navigate('/superlogin')
    return true
  }

  const loadStats = async (filters = statsFilter, sort = statsSort, page = statsPage) => {
    try {
      const headers = { 'Authorization': `Bearer ${token}` }
      const params = buildStatsParams(filters, sort, page)
      const [overviewRes, usersRes] = await Promise.all([
        fetch(apiUrl('/api/super-admin/conversations/stats/overview'), { headers }),
        fetch(apiUrl(`/api/super-admin/conversations/stats/users?${params}`), { headers }),
      ])

      if (handleUnauthorized(overviewRes) || handleUnauthorized(usersRes)) return

      const overview = overviewRes.ok ? await overviewRes.json() : null
      const usersData = usersRes.ok ? await usersRes.json() : { items: [], total: 0, totalPages: 0 }
      if (!overviewRes.ok || !usersRes.ok) {
        setError('加载使用统计失败')
      }

      setStats({ overview, users: usersData.items || [] })
      setStatsPagination({ total: usersData.total || 0, totalPages: usersData.totalPages || 0 })
    } catch (err) {
      setError('网络错误: ' + err.message)
    }
  }

  const loadFilterOptions = async () => {
    try {
      const res = await fetch(apiUrl('/api/super-admin/conversations/stats/filters'), {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (handleUnauthorized(res)) return
      if (res.ok) {
        const data = await res.json()
        setFilterOptions(data)
      }
    } catch (err) {
      setError('网络错误: ' + err.message)
    }
  }

  const handleStatsFilterChange = (key, value) => {
    const nextFilter = { ...statsFilter, [key]: value }
    setStatsFilter(nextFilter)
    setStatsPage(1)

    if (key === 'keyword') {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
      debounceTimerRef.current = setTimeout(() => {
        loadStats(nextFilter, statsSort, 1)
      }, 300)
      return
    }

    loadStats(nextFilter, statsSort, 1)
  }

  const handleStatsSort = (field) => {
    const nextSort = statsSort.sortBy === field
      ? { ...statsSort, sortOrder: statsSort.sortOrder === 'desc' ? 'asc' : 'desc' }
      : { sortBy: field, sortOrder: 'desc' }
    setStatsSort(nextSort)
    setStatsPage(1)
    loadStats(statsFilter, nextSort, 1)
  }

  const handleStatsPageChange = (page) => {
    setStatsPage(page)
    loadStats(statsFilter, statsSort, page)
  }

  const handleExportUsers = async () => {
    try {
      const params = buildStatsParams(statsFilter, statsSort)
      const res = await fetch(apiUrl(`/api/super-admin/conversations/stats/users/export?${params}`), {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (handleUnauthorized(res)) return
      if (!res.ok) {
        setError('导出失败')
        return
      }

      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `用户使用统计_${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setError('导出失败: ' + err.message)
    }
  }

  const renderSortIcon = (field) => {
    if (statsSort.sortBy !== field) return <span className={styles.sortIcon}>↕</span>
    return <span className={styles.sortIcon}>{statsSort.sortOrder === 'desc' ? '↓' : '↑'}</span>
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!selectedCreateUser) {
      setError('请先从搜索结果中选择一个已有平台用户')
      return
    }

    try {
      const res = await fetch(apiUrl('/api/super-admin/admins'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ bound_user_id: selectedCreateUser.platform_user_id })
      })

      const data = await res.json()
      if (res.ok) {
        closeCreateModal()
        fetchAdmins()
      } else {
        setError(data.detail || '创建管理员失败')
      }
    } catch (err) {
      setError('网络错误: ' + err.message)
    }
  }

  const handleDelete = async (adminId) => {
    if (!confirm('确定要删除此管理员吗？')) return

    try {
      const res = await fetch(apiUrl(`/api/super-admin/admins/${adminId}`), {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (res.ok) {
        fetchAdmins()
      } else {
        const data = await res.json()
        setError(data.detail || '删除管理员失败')
      }
    } catch (err) {
      setError('网络错误: ' + err.message)
    }
  }

  const handleToggleActive = async (adminId, currentStatus) => {
    try {
      const res = await fetch(apiUrl(`/api/super-admin/admins/${adminId}`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ is_active: !currentStatus })
      })

      if (res.ok) {
        fetchAdmins()
      } else {
        const data = await res.json()
        setError(data.detail || '更新管理员状态失败')
      }
    } catch (err) {
      setError('网络错误: ' + err.message)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('superAdminToken')
    navigate('/superlogin')
  }

  const openCreateModal = () => {
    setError('')
    setCreateKeyword('')
    setCreateResults([])
    setSelectedCreateUser(null)
    setShowCreateModal(true)
  }

  const closeCreateModal = () => {
    setShowCreateModal(false)
    setCreateKeyword('')
    setCreateResults([])
    setSelectedCreateUser(null)
  }

  const openBindModal = (admin) => {
    setError('')
    setSelectedAdmin(admin)
    setSelectedBindUser(admin.bound_user || null)
    setBindKeyword('')
    setBindResults([])
    setShowBindModal(true)
  }

  const closeBindModal = () => {
    setShowBindModal(false)
    setSelectedAdmin(null)
    setSelectedBindUser(null)
    setBindKeyword('')
    setBindResults([])
  }

  const handleBindUser = async (e) => {
    e.preventDefault()
    if (!selectedAdmin) return

    const boundUserId = selectedBindUser?.platform_user_id || null

    try {
      const res = await fetch(apiUrl(`/api/super-admin/admins/${selectedAdmin.id}/bind-user`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ bound_user_id: boundUserId })
      })

      const data = await res.json()
      if (res.ok) {
        closeBindModal()
        setError('')
        fetchAdmins()
      } else {
        setError(data.detail || '绑定失败')
      }
    } catch (err) {
      setError('网络错误: ' + err.message)
    }
  }

  const renderUserSummary = (user, fallbackUserId) => {
    if (user) {
      return (
        <div className={styles.userSummary}>
          <div className={styles.userName}>{user.staff_name || '未填写姓名'}</div>
          <div className={styles.userMeta}>用户ID：{user.platform_user_id}</div>
          <div className={styles.userMeta}>工号：{user.staff_code || '未填写'} · 岗位：{user.staff_pos_type || '未填写'}</div>
          <div className={styles.userMeta}>地市：{user.lan_name || '未填写'} · 区县：{user.region_name || '未填写'}</div>
        </div>
      )
    }

    if (fallbackUserId) {
      return (
        <div className={styles.userSummary}>
          <span className={styles.boundUser}>{fallbackUserId}</span>
          <div className={styles.userMeta}>平台用户信息不存在或已删除</div>
        </div>
      )
    }

    return <span className={styles.unbound}>未绑定</span>
  }

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>加载中...</div>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <div className={styles.headerBar}>
        <h1 className={styles.pageTitle}>超级管理员控制台</h1>
        <button className={styles.logoutBtn} onClick={handleLogout}>退出登录</button>
      </div>

      {error && <div className={styles.errorBar}>{error}<button onClick={() => setError('')}>×</button></div>}

      <div className={styles.content}>
        <div className={styles.tabs}>
          <button
            className={`${styles.tabBtn} ${activeTab === 'admins' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('admins')}
          >
            管理员管理
          </button>
          <button
            className={`${styles.tabBtn} ${activeTab === 'statistics' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('statistics')}
          >
            使用统计
          </button>
        </div>

        {activeTab === 'admins' && (
          <>
            <div className={styles.toolbar}>
              <h2 className={styles.sectionTitle}>管理员列表</h2>
              <button className={styles.createBtn} onClick={openCreateModal}>
                + 新增管理员
              </button>
            </div>

            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>管理员标识</th>
                    <th>状态</th>
                    <th>类型</th>
                    <th>绑定用户信息</th>
                    <th>创建时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {admins.map(admin => (
                    <tr key={admin.id}>
                      <td>{admin.id}</td>
                      <td>{admin.username}</td>
                      <td>
                        <span className={`${styles.badge} ${admin.is_active ? styles.badgeActive : styles.badgeInactive}`}>
                          {admin.is_active ? '启用' : '禁用'}
                        </span>
                      </td>
                      <td>
                        <span className={`${styles.badge} ${admin.is_superadmin ? styles.badgeSuper : styles.badgeNormal}`}>
                          {admin.is_superadmin ? '超级管理员' : '普通管理员'}
                        </span>
                      </td>
                      <td>{renderUserSummary(admin.bound_user, admin.bound_user_id)}</td>
                      <td>{admin.created_at}</td>
                      <td>
                        {!admin.is_superadmin && (
                          <div className={styles.actions}>
                            <button
                              className={styles.actionBtn}
                              onClick={() => handleToggleActive(admin.id, admin.is_active)}
                            >
                              {admin.is_active ? '禁用' : '启用'}
                            </button>
                            <button
                              className={styles.actionBtn}
                              onClick={() => openBindModal(admin)}
                            >
                              {admin.bound_user_id ? '修改绑定' : '绑定用户'}
                            </button>
                            <button
                              className={`${styles.actionBtn} ${styles.deleteBtn}`}
                              onClick={() => handleDelete(admin.id)}
                            >
                              删除
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {activeTab === 'statistics' && (
          <div className={styles.statsContainer}>
            <div className={styles.statsOverview}>
              <div className={styles.statCard}>
                <div className={styles.statValue}>{stats.overview?.totalUsers || 0}</div>
                <div className={styles.statLabel}>用户数</div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statValue}>{stats.overview?.totalDialogs || 0}</div>
                <div className={styles.statLabel}>对话数</div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statValue}>{stats.overview?.totalRequests ?? stats.overview?.totalMessages ?? 0}</div>
                <div className={styles.statLabel}>请求数</div>
              </div>
            </div>

            <div className={styles.statsSection}>
              <div className={styles.statsSectionHeader}>
                <h2 className={styles.sectionTitle}>用户使用明细</h2>
                <button className={styles.exportBtn} onClick={handleExportUsers}>导出CSV</button>
              </div>

              <div className={styles.statsFilterBar}>
                <input
                  className={styles.filterInput}
                  type="text"
                  placeholder="搜索姓名/工号/用户ID..."
                  value={statsFilter.keyword}
                  onChange={(e) => handleStatsFilterChange('keyword', e.target.value)}
                />
                <select
                  className={styles.filterSelect}
                  value={statsFilter.lanName}
                  onChange={(e) => handleStatsFilterChange('lanName', e.target.value)}
                >
                  <option value="">全部地市</option>
                  {filterOptions.lanNames.map(name => <option key={name} value={name}>{name}</option>)}
                </select>
                <select
                  className={styles.filterSelect}
                  value={statsFilter.regionName}
                  onChange={(e) => handleStatsFilterChange('regionName', e.target.value)}
                >
                  <option value="">全部区县</option>
                  {filterOptions.regionNames.map(name => <option key={name} value={name}>{name}</option>)}
                </select>
                <select
                  className={styles.filterSelect}
                  value={statsFilter.staffPosType}
                  onChange={(e) => handleStatsFilterChange('staffPosType', e.target.value)}
                >
                  <option value="">全部岗位</option>
                  {filterOptions.staffPosTypes.map(name => <option key={name} value={name}>{name}</option>)}
                </select>
              </div>

              <div className={styles.tableWrapper}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>用户ID</th>
                      <th className={styles.sortableTh} onClick={() => handleStatsSort('staffName')}>姓名 {renderSortIcon('staffName')}</th>
                      <th>工号</th>
                      <th>岗位</th>
                      <th className={styles.sortableTh} onClick={() => handleStatsSort('lanName')}>地市 {renderSortIcon('lanName')}</th>
                      <th className={styles.sortableTh} onClick={() => handleStatsSort('regionName')}>区县 {renderSortIcon('regionName')}</th>
                      <th className={styles.sortableTh} onClick={() => handleStatsSort('dialogCount')}>对话数 {renderSortIcon('dialogCount')}</th>
                      <th className={styles.sortableTh} onClick={() => handleStatsSort('totalRequests')}>请求数 {renderSortIcon('totalRequests')}</th>
                      <th className={styles.sortableTh} onClick={() => handleStatsSort('firstUsed')}>首次使用 {renderSortIcon('firstUsed')}</th>
                      <th className={styles.sortableTh} onClick={() => handleStatsSort('lastUsed')}>最近使用 {renderSortIcon('lastUsed')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.users.length === 0 ? (
                      <tr>
                        <td colSpan="10" className={styles.emptyCell}>暂无数据</td>
                      </tr>
                    ) : (
                      stats.users.map(user => (
                        <tr key={user.userId}>
                          <td className={styles.monospace}>{user.userId}</td>
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
                    共 {statsPagination.total} 条，共 {statsPagination.totalPages} 页，当前第 {statsPage} 页
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
      </div>

      {showCreateModal && (
        <div className={styles.modal}>
          <div className={styles.modalContent}>
            <h3 className={styles.modalTitle}>新增管理员</h3>
            <form onSubmit={handleCreate}>
              <div className={styles.field}>
                <label className={styles.label}>搜索平台用户</label>
                <UserSearchBox
                  keyword={createKeyword}
                  setKeyword={setCreateKeyword}
                  results={createResults}
                  searching={createSearching}
                  selectedUser={selectedCreateUser}
                  onSelect={setSelectedCreateUser}
                  placeholder="输入用户ID、工号或姓名搜索"
                />
                <p className={styles.fieldHint}>该用户进入对话页后会自动显示后台入口，无需管理员用户名和密码。</p>
              </div>
              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelBtn} onClick={closeCreateModal}>取消</button>
                <button type="submit" className={styles.confirmBtn} disabled={!selectedCreateUser}>创建</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showBindModal && selectedAdmin && (
        <div className={styles.modal}>
          <div className={styles.modalContent}>
            <h3 className={styles.modalTitle}>绑定用户身份 - {selectedAdmin.username}</h3>
            <form onSubmit={handleBindUser}>
              <div className={styles.field}>
                <label className={styles.label}>搜索平台用户</label>
                <UserSearchBox
                  keyword={bindKeyword}
                  setKeyword={setBindKeyword}
                  results={bindResults}
                  searching={bindSearching}
                  selectedUser={selectedBindUser}
                  onSelect={setSelectedBindUser}
                  placeholder="输入用户ID、工号或姓名搜索"
                />
                <p className={styles.fieldHint}>绑定后，该用户在对话界面点击「后台管理」可直接进入管理后台，无需登录</p>
              </div>
              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelBtn} onClick={closeBindModal}>取消</button>
                <button type="button" className={styles.cancelBtn} onClick={() => setSelectedBindUser(null)}>解绑</button>
                <button type="submit" className={styles.confirmBtn}>{selectedBindUser ? '确认绑定' : '确认解绑'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function UserSearchBox({ keyword, setKeyword, results, searching, selectedUser, onSelect, placeholder }) {
  return (
    <div className={styles.userSearch}>
      <input
        className={styles.input}
        type="text"
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        placeholder={placeholder}
      />

      {selectedUser && (
        <div className={styles.selectedHint}>
          已选择：{selectedUser.staff_name || selectedUser.platform_user_id}
        </div>
      )}

      {selectedUser && results.length === 0 && !keyword.trim() && (
        <button
          type="button"
          className={`${styles.userCard} ${styles.userCardSelected}`}
          onClick={() => onSelect(selectedUser)}
        >
          <div className={styles.userCardHeader}>
            <strong>{selectedUser.staff_name || '未填写姓名'}</strong>
            <span>{selectedUser.platform_user_id}</span>
          </div>
          <div className={styles.userCardMeta}>工号：{selectedUser.staff_code || '未填写'} · 岗位：{selectedUser.staff_pos_type || '未填写'}</div>
          <div className={styles.userCardMeta}>地市：{selectedUser.lan_name || '未填写'} · 区县：{selectedUser.region_name || '未填写'}</div>
        </button>
      )}

      {searching && <div className={styles.searchStatus}>搜索中...</div>}

      {!searching && keyword.trim() && results.length === 0 && (
        <div className={styles.searchStatus}>未找到匹配的平台用户</div>
      )}

      {results.length > 0 && (
        <div className={styles.userCardList}>
          {results.map(user => (
            <button
              type="button"
              key={user.platform_user_id}
              className={`${styles.userCard} ${selectedUser?.platform_user_id === user.platform_user_id ? styles.userCardSelected : ''}`}
              onClick={() => onSelect(user)}
            >
              <div className={styles.userCardHeader}>
                <strong>{user.staff_name || '未填写姓名'}</strong>
                <span>{user.platform_user_id}</span>
              </div>
              <div className={styles.userCardMeta}>工号：{user.staff_code || '未填写'} · 岗位：{user.staff_pos_type || '未填写'}</div>
              <div className={styles.userCardMeta}>地市：{user.lan_name || '未填写'} · 区县：{user.region_name || '未填写'}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
