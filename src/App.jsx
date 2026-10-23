import { useState, useCallback, useEffect, useMemo, useRef } from 'react'
import { authHeaders, callAgent, fetchForbiddenWords, fetchSuggestedQuestions } from './api/index'
import { apiUrl } from './api/base'
import Sidebar from './components/Sidebar/Sidebar'
import ChatHeader from './components/ChatHeader/ChatHeader'
import ChatArea from './components/ChatArea/ChatArea'
import InputArea from './components/InputArea/InputArea'
import MemoryDrawer from './components/MemoryDrawer/MemoryDrawer'
import TemplateSelector from './components/TemplateSelector/TemplateSelector'
import VersionHistory from './components/VersionHistory/VersionHistory'
import Toast, { showToast } from './components/Toast/Toast'
import styles from './App.module.css'

const AGENT_INFO = {
  toolId: 'living-stream-agent',
  name: '直播话术生成智能体',
  desc: '生成、评估、优化直播脚本',
  icon: '🎙️',
  color: '#2563EB',
}

function getTime() {
  const d = new Date()
  return d.getHours().toString().padStart(2, '0') + ':' + d.getMinutes().toString().padStart(2, '0')
}

export default function App({ userInfo }) {
  const userId = userInfo?.platformUserId
  const authHeader = useMemo(() => authHeaders(userInfo?.platformToken), [userInfo?.platformToken])
  const [dialogs, setDialogs] = useState([])
  const [currentDialog, setCurrentDialog] = useState(null)
  const [messages, setMessages] = useState([])
  const [isTyping, setIsTyping] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState({ connected: false })
  const [loadingDialogs, setLoadingDialogs] = useState(false)
  const [memoryDrawerOpen, setMemoryDrawerOpen] = useState(false)
  const [forbiddenWords, setForbiddenWords] = useState([])
  const [templateSelectorOpen, setTemplateSelectorOpen] = useState(false)
  const [versionHistoryOpen, setVersionHistoryOpen] = useState(false)
  const [inputText, setInputText] = useState('')
  const [isAdminUser, setIsAdminUser] = useState(false)
  const [suggestedQuestions, setSuggestedQuestions] = useState([])
  const abortControllerRef = useRef(null)
  const messagesRef = useRef(messages)
  const dialogLoadSeqRef = useRef(0)
  const currentDialogRef = useRef(currentDialog)

  // 保持 currentDialogRef 与 currentDialog 同步
  useEffect(() => {
    currentDialogRef.current = currentDialog
  }, [currentDialog])

  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  useEffect(() => {
    const loadDialogs = async () => {
      try {
        setLoadingDialogs(true)
        const res = await fetch(apiUrl('/chat/api/conversations?pageSize=100'), {
          headers: authHeader,
        })
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
  }, [userId, userInfo?.platformToken])

  useEffect(() => {
    const checkAdminIdentity = async () => {
      if (!userId || !userInfo?.platformToken) {
        setIsAdminUser(false)
        return
      }
      try {
        const res = await fetch(apiUrl('/chat/api/admin/me-by-user'), {
          headers: authHeader,
        })
        if (!res.ok) {
          setIsAdminUser(false)
          return
        }
        const data = await res.json()
        setIsAdminUser(Boolean(data.isAdmin))
      } catch {
        setIsAdminUser(false)
      }
    }
    checkAdminIdentity()
  }, [authHeader, userId, userInfo?.platformToken])

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(apiUrl('/chat/api/health'))
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

  useEffect(() => {
    const loadSuggestedQuestions = async () => {
      try {
        const data = await fetchSuggestedQuestions()
        setSuggestedQuestions((data || []).map(item => item.content).filter(Boolean).slice(0, 3))
      } catch (err) {
        console.error('加载推荐问题失败:', err)
        setSuggestedQuestions([])
      }
    }
    loadSuggestedQuestions()
  }, [])

  const loadDialogMessages = useCallback(async (dialogId) => {
    try {
      const res = await fetch(apiUrl(`/chat/api/conversations/${dialogId}/messages`), {
        headers: authHeader,
      })
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
  }, [userInfo?.platformToken])

  const selectDialog = useCallback(async (dialog) => {
    setCurrentDialog(dialog)
    setMessages([])

    const seq = ++dialogLoadSeqRef.current
    const msgs = await loadDialogMessages(dialog.id)
    if (seq === dialogLoadSeqRef.current && msgs) {
      setMessages(msgs)
    }
    setSidebarOpen(false)
  }, [loadDialogMessages])

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
      const res = await fetch(apiUrl('/chat/api/conversations'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader },
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
  }, [authHeader, userId, userInfo])

  const deleteDialog = useCallback(async (dialogId) => {
    if (!confirm('确定删除此对话？')) return
    try {
      const res = await fetch(apiUrl(`/chat/api/conversations/${dialogId}`), {
        method: 'DELETE',
        headers: authHeader,
      })
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
  }, [authHeader, currentDialog])

  const clearChat = useCallback(() => {
    if (!currentDialog) return
    deleteDialog(currentDialog.id)
  }, [currentDialog, deleteDialog])

  // 创建对话并发送消息
  const createDialogAndSend = useCallback(async (text, file) => {
    const requestData = {
      userId: userId,
      toolId: AGENT_INFO.toolId,
      toolName: AGENT_INFO.name,
      title: text.slice(0, 20) + (text.length > 20 ? '...' : ''),
      lanName: userInfo?.lanName || '',
      regionName: userInfo?.regionName || '',
      staffCode: userInfo?.staffCode || '',
      staffName: userInfo?.staffName || '',
      staffPosType: userInfo?.staffPosType || '',
    }

    try {
      const res = await fetch(apiUrl('/chat/api/conversations'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader },
        body: JSON.stringify(requestData),
      })

      if (res.ok) {
        const dialog = await res.json()
        setDialogs(prev => [dialog, ...prev])
        setCurrentDialog(dialog)
        setSidebarOpen(false)
        // 等待状态更新后再发送消息
        return dialog
      } else {
        const error = await res.json()
        showToast(error.detail || '创建对话失败', 'error')
        return null
      }
    } catch (err) {
      showToast('创建对话失败: ' + err.message, 'error')
      return null
    }
  }, [authHeader, userId, userInfo])

  const sendMessage = useCallback(
    async (text, file) => {
      // 如果没有当前对话，先创建对话
      let dialog = currentDialogRef.current
      if (!dialog) {
        dialog = await createDialogAndSend(text, file)
        if (!dialog) return
      }

      const userMsg = {
        role: 'user',
        content: text,
        fileName: file ? file.name : null,
        time: getTime(),
      }
      setMessages(prev => [...prev, userMsg])

      setIsTyping(true)
      const placeholderMsg = { role: 'assistant', content: '', time: getTime() }
      setMessages(prev => [...prev, placeholderMsg])

      const controller = new AbortController()
      abortControllerRef.current = controller

      try {
        await callAgent(dialog.id, text, file, (partialText) => {
          setMessages(prev => {
            const updated = [...prev]
            const lastIdx = updated.length - 1
            if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
              updated[lastIdx] = { ...updated[lastIdx], content: partialText }
            }
            return updated
          })
        }, controller.signal)
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
    [authHeader, userId, createDialogAndSend]
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
    // 截取消息到最后一条用户消息之前
    const newMessages = msgs.slice(0, lastUserIdx)
    setMessages(newMessages)
    
    // 使用 requestAnimationFrame 确保状态更新后再发送
    requestAnimationFrame(() => {
      const dialog = currentDialogRef.current
      if (dialog) {
        sendMessage(lastUserMsg.content)
      }
    })
  }, [isTyping, sendMessage])

  const handleTemplateSelect = useCallback((template) => {
    const message = `请使用以下模板生成直播脚本：

模板名称：${template.name}
模板类型：${template.product_type || '通用'}

${template.template_content}

请根据这个模板结构，生成一个完整的直播脚本。`
    
    // 将模板内容设置到输入框，让用户可以修改后再发送
    setInputText(message)
  }, [])

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
        onClose={() => setSidebarOpen(false)}
        open={sidebarOpen}
        connectionStatus={connectionStatus}
        userInfo={userInfo}
      />
      {sidebarOpen && (
        <button
          type="button"
          className={styles.sidebarOverlay}
          aria-label="关闭对话列表"
          onClick={() => setSidebarOpen(false)}
          onTouchStart={() => setSidebarOpen(false)}
        />
      )}
      <main className={styles.main}>
        <ChatHeader
          tool={AGENT_INFO}
          onBack={() => setSidebarOpen((v) => !v)}
          onClear={clearChat}
          onMemory={() => setMemoryDrawerOpen(true)}
          onVersionHistory={() => setVersionHistoryOpen(true)}
          onTemplateSelect={() => setTemplateSelectorOpen(true)}
          dialogId={currentDialog?.id}
          userId={userId}
          isAdminUser={isAdminUser}
        />
        {currentDialog ? (
          <>
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
            <InputArea 
              onSend={(text, file) => {
                sendMessage(text, file)
                setInputText('')
              }} 
              onAbort={handleAbort} 
              showFileUpload={true}
              isLoading={isTyping}
              initialValue={inputText}
            />
          </>
        ) : (
          <div className={styles.welcome}>
            <div className={styles.welcomeContent}>
              <div className={styles.welcomeIcon}>🎙️</div>
              <h2>直播脚本生成智能体</h2>
              <div className={styles.welcomeInputWrapper}>
                <InputArea 
                  onSend={(text, file) => {
                    sendMessage(text, file)
                    setInputText('')
                  }} 
                  onAbort={handleAbort} 
                  showFileUpload={true}
                  isLoading={isTyping}
                  isCenter={true}
                  initialValue={inputText}
                />
              </div>
              {suggestedQuestions.length > 0 && (
                <div className={styles.suggestions}>
                  {suggestedQuestions.map((text, i) => (
                    <button
                      key={`${text}-${i}`}
                      className={styles.suggestionBtn}
                      onClick={() => sendMessage(text)}
                    >
                      {text}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
      <MemoryDrawer
        open={memoryDrawerOpen}
        onClose={() => setMemoryDrawerOpen(false)}
        userId={userId}
      />
      {templateSelectorOpen && (
        <TemplateSelector
          onSelect={handleTemplateSelect}
          onClose={() => setTemplateSelectorOpen(false)}
          userId={userId}
        />
      )}
      {versionHistoryOpen && currentDialog && (
        <VersionHistory
          dialogId={currentDialog.id}
          onClose={() => setVersionHistoryOpen(false)}
        />
      )}
    </div>
  )
}
