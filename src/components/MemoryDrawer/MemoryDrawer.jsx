import { useState, useEffect, useCallback } from 'react'
import { fetchMemories, createMemory, updateMemory, deleteMemory } from '../../api/index'
import { showToast } from '../Toast/Toast'
import styles from './MemoryDrawer.module.css'

export default function MemoryDrawer({ open, onClose, userId }) {
  const [memories, setMemories] = useState([])
  const [loading, setLoading] = useState(false)
  const [newContent, setNewContent] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editContent, setEditContent] = useState('')

  const loadMemories = useCallback(async () => {
    if (!userId) return
    try {
      setLoading(true)
      const data = await fetchMemories(userId)
      setMemories(data)
    } catch (err) {
      showToast('加载记忆失败', 'error')
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    if (open && userId) {
      loadMemories()
    }
  }, [open, userId, loadMemories])

  const handleAdd = async () => {
    const content = newContent.trim()
    if (!content) return
    try {
      const mem = await createMemory(userId, content)
      setMemories(prev => [mem, ...prev])
      setNewContent('')
      showToast('记忆已添加', 'success')
    } catch (err) {
      showToast('添加失败', 'error')
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('确定删除这条记忆？')) return
    try {
      await deleteMemory(id)
      setMemories(prev => prev.filter(m => m.id !== id))
      showToast('已删除', 'success')
    } catch (err) {
      showToast('删除失败', 'error')
    }
  }

  const handleStartEdit = (mem) => {
    setEditingId(mem.id)
    setEditContent(mem.content)
  }

  const handleSaveEdit = async (id) => {
    const content = editContent.trim()
    if (!content) return
    try {
      const updated = await updateMemory(id, content)
      setMemories(prev => prev.map(m => m.id === id ? updated : m))
      setEditingId(null)
      showToast('已更新', 'success')
    } catch (err) {
      showToast('更新失败', 'error')
    }
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setEditContent('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleAdd()
    }
  }

  const formatTime = (dateStr) => {
    const d = new Date(dateStr)
    return d.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Shanghai',
    })
  }

  return (
    <>
      <div
        className={`${styles.overlay} ${open ? styles.overlayOpen : ''}`}
        onClick={onClose}
      />
      <div className={`${styles.drawer} ${open ? styles.drawerOpen : ''}`}>
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <span className={styles.headerIcon}>🧠</span>
            <span className={styles.headerTitle}>长期记忆</span>
            {memories.length > 0 && (
              <span className={styles.headerCount}>{memories.length}</span>
            )}
          </div>
          <button className={styles.closeBtn} onClick={onClose}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className={styles.addSection}>
          <div className={styles.addInputWrap}>
            <textarea
              className={styles.addInput}
              placeholder="输入要记住的内容..."
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />
            <button
              className={styles.addBtn}
              onClick={handleAdd}
              disabled={!newContent.trim()}
            >
              添加
            </button>
          </div>
        </div>

        <div className={styles.list}>
          {loading ? (
            <div className={styles.empty}>加载中...</div>
          ) : memories.length === 0 ? (
            <div className={styles.empty}>
              <div className={styles.emptyIcon}>🧠</div>
              <div className={styles.emptyText}>
                暂无记忆<br />
                对话中说「请记住：xxx」或在此手动添加
              </div>
            </div>
          ) : (
            memories.map(mem => (
              <div key={mem.id} className={styles.memoryItem}>
                {editingId === mem.id ? (
                  <>
                    <textarea
                      className={styles.memoryEditInput}
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      autoFocus
                    />
                    <div className={styles.memoryFooter}>
                      <span className={styles.memoryTime}>{formatTime(mem.createdAt)}</span>
                      <div className={styles.memoryActions}>
                        <button onClick={handleCancelEdit}>取消</button>
                        <button className={styles.saveBtn} onClick={() => handleSaveEdit(mem.id)}>保存</button>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div className={styles.memoryContent}>{mem.content}</div>
                    <div className={styles.memoryFooter}>
                      <span className={styles.memoryTime}>{formatTime(mem.createdAt)}</span>
                      <div className={styles.memoryActions}>
                        <button onClick={() => handleStartEdit(mem)}>编辑</button>
                        <button className={styles.deleteBtn} onClick={() => handleDelete(mem.id)}>删除</button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </>
  )
}
