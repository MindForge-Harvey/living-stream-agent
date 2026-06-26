/**
 * 调用直播话术生成智能体API
 * @param {string} dialogId - 对话ID
 * @param {string} message - 用户消息
 * @param {File|null} file - 上传的文件
 * @param {function} onChunk - 流式数据回调
 * @param {AbortSignal} signal - 中止信号
 * @returns {Promise<string>} 完整的响应文本
 */
export async function callAgent(dialogId, message, file = null, onChunk = null, signal = null, userId = null) {
  const formData = new FormData()
  formData.append('message', message)
  if (dialogId) {
    formData.append('dialogId', dialogId)
  }
  if (userId) {
    formData.append('userId', userId)
  }
  if (file) {
    formData.append('file', file)
  }

  const res = await fetch('/chat/api/agent', {
    method: 'POST',
    body: formData,
    signal,
  })

  if (!res.ok) {
    const errText = await res.text()
    let errMsg
    try {
      const errJson = JSON.parse(errText)
      errMsg = errJson.detail || errJson.message || errText
    } catch {
      errMsg = errText || `请求失败: ${res.status}`
    }
    throw new Error(errMsg)
  }

  const contentType = res.headers.get('content-type') || ''
  let finalContent = ''

  if (contentType.includes('text/event-stream')) {
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      buffer += chunk

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const cleanLine = line.replace(/\r$/, '')
        if (!cleanLine || !cleanLine.startsWith('data:')) continue

        const jsonStr = cleanLine.substring(5).trim()
        if (!jsonStr) continue

        try {
          const data = JSON.parse(jsonStr)
          if (data.content !== undefined) {
            finalContent += data.content
            if (onChunk) onChunk(finalContent)
          }
        } catch (e) {
          console.warn('SSE JSON parse error:', jsonStr)
        }
      }
    }

    if (buffer) {
      const cleanLine = buffer.replace(/\r$/, '')
      if (cleanLine && cleanLine.startsWith('data:')) {
        const jsonStr = cleanLine.substring(5).trim()
        if (jsonStr) {
          try {
            const data = JSON.parse(jsonStr)
            if (data.content !== undefined) {
              finalContent += data.content
              if (onChunk) onChunk(finalContent)
            }
          } catch (e) {
            console.warn('SSE JSON parse error:', jsonStr)
          }
        }
      }
    }
  } else {
    finalContent = await res.text()
    if (onChunk) onChunk(finalContent)
  }

  return finalContent
}

// 用户记忆相关 API
export async function fetchMemories(userId) {
  const res = await fetch(`/chat/api/memories?user_id=${encodeURIComponent(userId)}`)
  if (!res.ok) throw new Error('获取记忆失败')
  return res.json()
}

export async function createMemory(userId, content) {
  const res = await fetch('/chat/api/memories', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, content }),
  })
  if (!res.ok) throw new Error('创建记忆失败')
  return res.json()
}

export async function updateMemory(memoryId, content) {
  const res = await fetch(`/chat/api/memories/${memoryId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
  if (!res.ok) throw new Error('更新记忆失败')
  return res.json()
}

export async function deleteMemory(memoryId, userId) {
  const params = userId ? `?user_id=${encodeURIComponent(userId)}` : ''
  const res = await fetch(`/chat/api/memories/${memoryId}${params}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('删除记忆失败')
  // 安全解析 JSON，防止空响应导致解析错误
  const text = await res.text()
  return text ? JSON.parse(text) : { success: true }
}

// 违禁词相关 API
export async function fetchForbiddenWords() {
  const res = await fetch('/chat/api/forbidden-words/public')
  if (!res.ok) throw new Error('获取违禁词失败')
  return res.json()
}

// 脚本模板相关 API
export async function fetchTemplates(category = null, productType = null) {
  let url = '/chat/api/templates/public'
  const params = new URLSearchParams()
  if (category) params.append('category', category)
  if (productType) params.append('product_type', productType)
  if (params.toString()) url += '?' + params.toString()
  
  const res = await fetch(url)
  if (!res.ok) throw new Error('获取模板失败')
  return res.json()
}

export async function fetchTemplateById(templateId) {
  const res = await fetch(`/chat/api/templates/${templateId}`)
  if (!res.ok) throw new Error('获取模板详情失败')
  return res.json()
}

export async function createTemplate(data) {
  const token = localStorage.getItem('adminToken')
  const res = await fetch('/chat/api/templates', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data)
  })
  if (!res.ok) throw new Error('创建模板失败')
  return res.json()
}

export async function updateTemplate(templateId, data) {
  const token = localStorage.getItem('adminToken')
  const res = await fetch(`/chat/api/templates/${templateId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data)
  })
  if (!res.ok) throw new Error('更新模板失败')
  return res.json()
}

// 脚本版本相关 API
export async function fetchScriptVersions(dialogId) {
  const res = await fetch(`/chat/api/agent/versions/${dialogId}`)
  if (!res.ok) throw new Error('获取版本历史失败')
  return res.json()
}

// 导出功能 API
export async function exportScript(dialogId, format = 'txt') {
  const res = await fetch('/chat/api/export', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ dialog_id: dialogId, format })
  })
  
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}))
    throw new Error(errData.detail || '导出失败')
  }
  
  return res.blob()
}
