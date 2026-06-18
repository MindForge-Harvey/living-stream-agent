import { useState, useCallback, useEffect, useRef } from 'react'
import { callAgent, fetchForbiddenWords } from './api/index'
import Sidebar from './components/Sidebar/Sidebar'
import ChatHeader from './components/ChatHeader/ChatHeader'
import ChatArea from './components/ChatArea/ChatArea'
import InputArea from './components/InputArea/InputArea'
import MemoryDrawer from './components/MemoryDrawer/MemoryDrawer'
import Toast, { showToast } from './components/Toast/Toast'
import styles from './App.module.css'

const AGENT_INFO = {
  toolId: 'living-stream-agent',
  name: '直播话术生成智能体',
  desc: '生成、评估、优化直播脚本',
  icon: '🎙️',
  color: '#2563EB',
  suggestions: [
    '帮我生成一段护肤品的直播脚本',
    '对以下直播话术进行打分',
    '优化这段直播话术',
  ]
}

function getTime() {
  const d = new Date()
  return d.getHours().toString().padStart(2, '0') + ':' + d.getMinutes().toString().padStart(2, '0')
}

export default function App({ userInfo }) {
  const userId = userInfo?.platformUserId
  const [dialogs, setDialogs] = useState([])
  const [currentDialog, setCurrentDialog] = useState(null)
  const [messages, setMessages] = useState([])
  const [isTyping, setIsTyping] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState({ connected: false })
  const [loadingDialogs, setLoadingDialogs] = useState(false)
  const [memoryDrawerOpen, setMemoryDrawerOpen] = useState(false)
  const [forbiddenWords, setForbiddenWords] = useState([])
  const abortControllerRef = useRef(null)
  const messagesRef = useRef(messages)
  const dialogLoadSeqRef = useRef(0)

  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  useEffect(() => {
    const loadDialogs = async () => {
      try {
        setLoadingDialogs(true)
        const res = await fetch(`/chat/api/dialogs?userId=${userId}&pageSize=100`)
        if (res.ok) {
          const data = await res.json()
          setDialogs(data.items || data)
        }
      } catch (err) {
        console.error('加载对话列表失败:', err)
      } finally {
        setLoadingDialogs(false)
      }
    }
    if (userId) loadDialogs()
  }, [userId])

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/chat/api/health')
        const data = await res.json()
        setConnectionStatus({ connected: data.status === 'ok' })
      } catch {
        setConnectionStatus({ connected: false })
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const loadForbiddenWords = async () => {
      try {
        const words = await fetchForbiddenWords()
        setForbiddenWords(words || [])
      } catch (err) {
        console.error('加载违禁词失败:', err)
      }
    }
    loadForbiddenWords()
  }, [])

  const loadDialogMessages = async (dialogId) => {
    try {
      const res = await fetch(`/chat/api/dialogs/${dialogId}/messages`)
      if (res.ok) {
        const data = await res.json()
        return data.map(m => ({
          role: m.role,
          content: m.content,
          time: new Date(m.createdAt).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Shanghai' }),
        }))
      }
    } catch (err) {
      console.error('加载消息失败:', err)
    }
    return null
  }

  const selectDialog = useCallback(async (dialog) => {
    setCurrentDialog(dialog)
    setMessages([])

    const seq = ++dialogLoadSeqRef.current
    const msgs = await loadDialogMessages(dialog.id)
    if (seq === dialogLoadSeqRef.current && msgs) {
      setMessages(msgs)
    }
    setSidebarOpen(false)
  }, [])

  const createNewDialog = useCallback(async () => {
    const requestData = {
      userId: userId,
      toolId: AGENT_INFO.toolId,
      toolName: AGENT_INFO.name,
      title: '新对话',
      lanName: userInfo?.lanName || '',
      regionName: userInfo?.regionName || '',
      staffCode: userInfo?.staffCode || '',
      staffName: userInfo?.staffName || '',
      staffPosType: userInfo?.staffPosType || '',
    }
    if (!userId) {
      console.error('userId is empty')
      return
    }

    try {
      const res = await fetch('/chat/api/dialogs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
      })

      if (res.ok) {
        const dialog = await res.json()
        setDialogs(prev => [dialog, ...prev])
        setCurrentDialog(dialog)
        setMessages([{
          role: 'assistant',
          content: `已准备好，可以开始使用「${AGENT_INFO.name}」。`,
          time: getTime(),
        }])
        setSidebarOpen(false)
      } else {
        const error = await res.json()
        console.error('createDialog error', error)
        showToast(error.detail || '创建对话失败', 'error')
      }
    } catch (err) {
      console.error('创建对话失败:', err)
      showToast('创建对话失败: ' + err.message, 'error')
    }
  }, [userId, userInfo])

  const deleteDialog = useCallback(async (dialogId) => {
    if (!confirm('确定删除此对话？')) return
    try {
      const res = await fetch(`/chat/api/dialogs/${dialogId}?userId=${userId}`, { method: 'DELETE' })
      if (res.ok) {
        setDialogs(prev => prev.filter(d => d.id !== dialogId))
        if (currentDialog?.id === dialogId) {
          setCurrentDialog(null)
          setMessages([])
        }
        showToast('对话已删除', 'success')
      } else {
        const err = await res.json()
        showToast(err.detail || '删除失败', 'error')
      }
    } catch (err) {
      console.error('删除对话失败:', err)
      showToast('删除对话失败: ' + err.message, 'error')
    }
  }, [currentDialog, userId])

  const clearChat = useCallback(() => {
    if (!confirm('确定要清空当前对话的所有消息吗？')) return
    setMessages([{
      role: 'assistant',
      content: `已准备好，可以开始使用「${AGENT_INFO.name}」。`,
      time: getTime(),
    }])
  }, [])

  const sendMessage = useCallback(
    async (text, file) => {
      if (!currentDialog) return

      const userMsg = {
        role: 'user',
        content: text,
        fileName: file ? file.name : null,
        time: getTime(),
      }
      setMessages(prev => [...prev, userMsg])

      try {
        await fetch('/chat/api/dialogs/message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            dialogId: currentDialog.id,
            userId: userId,
            role: 'user',
            content: text,
          }),
        })
      } catch (err) {
        console.error('保存用户消息失败:', err)
      }

      setIsTyping(true)
      const placeholderMsg = { role: 'assistant', content: '', time: getTime() }
      setMessages(prev => [...prev, placeholderMsg])

      const controller = new AbortController()
      abortControllerRef.current = controller

      try {
        const result = await callAgent(currentDialog.id, text, file, (partialText) => {
          setMessages(prev => {
            const updated = [...prev]
            const lastIdx = updated.length - 1
            if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
              updated[lastIdx] = { ...updated[lastIdx], content: partialText }
            }
            return updated
          })
        }, controller.signal, userId)

        if (result) {
          try {
            await fetch('/chat/api/dialogs/message', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                dialogId: currentDialog.id,
                userId: userId,
                role: 'assistant',
                content: result,
              }),
            })
          } catch (err) {
            console.error('保存助手消息失败:', err)
          }
        }
      } catch (err) {
        if (err.name === 'AbortError') {
          setMessages(prev => {
            const updated = [...prev]
            const lastIdx = updated.length - 1
            if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
              updated[lastIdx] = {
                ...updated[lastIdx],
                content: updated[lastIdx].content + '\n\n[已中止]',
              }
            }
            return updated
          })
        } else {
          showToast(`请求出错：${err.message}`, 'error')
          setMessages(prev => {
            const updated = [...prev]
            const lastIdx = updated.length - 1
            if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
              updated[lastIdx] = {
                ...updated[lastIdx],
                content: `请求出错：${err.message}`,
              }
            }
            return updated
          })
        }
      } finally {
        setIsTyping(false)
        abortControllerRef.current = null
      }
    },
    [currentDialog, userId]
  )

  const handleAbort = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }, [])

  const retryLastMessage = useCallback(() => {
    if (isTyping) return
    const msgs = messagesRef.current
    if (msgs.length < 2) return

    let lastUserIdx = -1
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'user') {
        lastUserIdx = i
        break
      }
    }
    if (lastUserIdx < 0) return

    const lastUserMsg = msgs[lastUserIdx]
    setMessages(msgs.slice(0, lastUserIdx))
    setTimeout(() => sendMessage(lastUserMsg.content), 50)
  }, [isTyping, sendMessage])

  const showSuggestions = messages.length <= 1 && !isTyping

  return (
    <div className={styles.app}>
      <Toast />
      <Sidebar
        dialogs={dialogs}
        activeDialogId={currentDialog?.id}
        onSelectDialog={selectDialog}
        onNewChat={createNewDialog}
        onDeleteDialog={deleteDialog}
        open={sidebarOpen}
        connectionStatus={connectionStatus}
        userInfo={userInfo}
      />
      <main className={styles.main}>
        <ChatHeader
          tool={AGENT_INFO}
          onBack={() => setSidebarOpen((v) => !v)}
          onClear={clearChat}
          onMemory={() => setMemoryDrawerOpen(true)}
        />
        {currentDialog ? (
          <ChatArea
            messages={messages}
            tool={AGENT_INFO}
            isTyping={isTyping}
            showSuggestions={showSuggestions}
            onSuggestionClick={(text) => sendMessage(text)}
            userInfo={userInfo}
            onRetry={retryLastMessage}
            forbiddenWords={forbiddenWords}
          />
        ) : (
          <div className={styles.welcome}>
            <div className={styles.welcomeIcon}>🎙️</div>
            <h2>直播脚本生成智能体</h2>
            <p>点击"新建对话"开始使用</p>
            <button className={styles.startBtn} onClick={createNewDialog}>
              新建对话
            </button>
          </div>
        )}
        <InputArea 
          onSend={sendMessage} 
          onAbort={handleAbort} 
          showFileUpload={!!currentDialog} 
          isLoading={isTyping} 
          disabled={!currentDialog} 
          onDisabledClick={createNewDialog} 
        />
      </main>
      <MemoryDrawer
        open={memoryDrawerOpen}
        onClose={() => setMemoryDrawerOpen(false)}
        userId={userId}
      />
    </div>
  )
}
