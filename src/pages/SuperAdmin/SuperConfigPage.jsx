import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import styles from './SuperAdmin.module.css'

export default function SuperConfigPage() {
  const [admins, setAdmins] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showBindModal, setShowBindModal] = useState(false)
  const [selectedAdmin, setSelectedAdmin] = useState(null)
  const [newBoundUserId, setNewBoundUserId] = useState('')
  const [bindUserId, setBindUserId] = useState('')
  const navigate = useNavigate()

  const token = localStorage.getItem('superAdminToken')

  useEffect(() => {
    if (!token) {
      navigate('/superlogin')
      return
    }
    fetchAdmins()
  }, [token, navigate])

  const fetchAdmins = async () => {
    try {
      const res = await fetch('/api/super-admin/admins', {
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

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      const res = await fetch('/api/super-admin/admins', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ bound_user_id: newBoundUserId.trim() })
      })

      const data = await res.json()
      if (res.ok) {
        setShowCreateModal(false)
        setNewBoundUserId('')
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
      const res = await fetch(`/api/super-admin/admins/${adminId}`, {
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
      const res = await fetch(`/api/super-admin/admins/${adminId}`, {
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

  const handleBindUser = async (e) => {
    e.preventDefault()
    if (!selectedAdmin) return

    try {
      const res = await fetch(`/api/super-admin/admins/${selectedAdmin.id}/bind-user`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ bound_user_id: bindUserId.trim() || null })
      })

      const data = await res.json()
      if (res.ok) {
        setShowBindModal(false)
        setSelectedAdmin(null)
        setBindUserId('')
        setError('')
        fetchAdmins()
      } else {
        setError(data.detail || '绑定失败')
      }
    } catch (err) {
      setError('网络错误: ' + err.message)
    }
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
        <div className={styles.toolbar}>
          <h2 className={styles.sectionTitle}>管理员列表</h2>
          <button className={styles.createBtn} onClick={() => setShowCreateModal(true)}>
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
                <th>绑定用户ID</th>
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
                  <td>
                    {admin.bound_user_id ? (
                      <span className={styles.boundUser}>{admin.bound_user_id}</span>
                    ) : (
                      <span className={styles.unbound}>未绑定</span>
                    )}
                  </td>
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
                          onClick={() => {
                            setSelectedAdmin(admin)
                            setBindUserId(admin.bound_user_id || '')
                            setShowBindModal(true)
                          }}
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
      </div>

      {showCreateModal && (
        <div className={styles.modal}>
          <div className={styles.modalContent}>
            <h3 className={styles.modalTitle}>新增管理员</h3>
            <form onSubmit={handleCreate}>
              <div className={styles.field}>
                <label className={styles.label}>平台用户ID（userId）</label>
                <input
                  className={styles.input}
                  type="text"
                  value={newBoundUserId}
                  onChange={(e) => setNewBoundUserId(e.target.value)}
                  placeholder="请输入要授权为管理员的平台用户ID"
                  required
                />
                <p className={styles.fieldHint}>该用户进入对话页后会自动显示后台入口，无需管理员用户名和密码。</p>
              </div>
              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelBtn} onClick={() => setShowCreateModal(false)}>取消</button>
                <button type="submit" className={styles.confirmBtn}>创建</button>
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
                <label className={styles.label}>平台用户ID（userId）</label>
                <input
                  className={styles.input}
                  type="text"
                  value={bindUserId}
                  onChange={(e) => setBindUserId(e.target.value)}
                  placeholder="输入要绑定的平台用户ID，留空则解绑"
                />
                <p className={styles.fieldHint}>绑定后，该用户在对话界面点击「后台管理」可直接进入管理后台，无需登录</p>
              </div>
              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelBtn} onClick={() => setShowBindModal(false)}>取消</button>
                <button type="submit" className={styles.confirmBtn}>确认绑定</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
