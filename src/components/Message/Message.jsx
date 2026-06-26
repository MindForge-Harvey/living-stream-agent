import React, { useMemo, useState, useCallback } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import styles from './Message.module.css'

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function highlightForbiddenWordsInHtml(html, forbiddenWords) {
  if (!forbiddenWords || forbiddenWords.length === 0 || !html) return html

  let result = html
  for (const wordObj of forbiddenWords) {
    const word = wordObj.word || wordObj
    if (!word) continue
    
    const escapedWord = escapeRegExp(word)
    const regex = new RegExp(`(?<!<mark[^>]*>)${escapedWord}(?![^<]*</mark>)`, 'g')
    result = result.replace(regex, `<mark class="${styles.forbiddenWord}">${word}</mark>`)
  }
  return result
}

export default function Message({ role, content, fileName, time, tool, userInfo, isLast, onRetry, forbiddenWords }) {
  const isUser = role === 'user'
  const userId = userInfo?.platformUserId
  const staffName = userInfo?.staffName

  const safeContent = typeof content === 'string' ? content : String(content || '')
  const [copied, setCopied] = useState(false)

  const html = useMemo(() => {
    const result = marked.parse(safeContent, { gfm: true })
    const raw = typeof result === 'string' ? result : ''
    const sanitized = DOMPurify.sanitize(raw, { ADD_TAGS: ['mark'], ADD_ATTR: ['class'] })
    
    // 在 HTML 层面进行违禁词高亮
    if (forbiddenWords && forbiddenWords.length > 0) {
      return highlightForbiddenWordsInHtml(sanitized, forbiddenWords)
    }
    return sanitized
  }, [safeContent, forbiddenWords])

  const wordCount = useMemo(() => {
    if (!safeContent) return 0
    const text = safeContent.replace(/[#*\-\n\r]/g, '').trim()
    return text.length
  }, [safeContent])

  const avatarText = staffName ? staffName.charAt(0).toUpperCase() : (userId ? userId.charAt(0).toUpperCase() : '用')

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(safeContent)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = safeContent
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }, [safeContent])

  const handleCopyMarkdown = useCallback(async () => {
    try {
      const tempDiv = document.createElement('div')
      tempDiv.innerHTML = html
      const plainText = tempDiv.textContent || tempDiv.innerText || ''
      await navigator.clipboard.writeText(plainText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }, [html])

  return (
    <div className={`${styles.message} ${isUser ? styles.user : styles.ai}`}>
      <div className={styles.avatar}>
        {isUser ? (
          <span className={styles.avatarText}>{avatarText}</span>
        ) : (
          <span className={styles.avatarIcon}>🎙️</span>
        )}
      </div>
      <div className={styles.content}>
        <div className={styles.bubble}>
          {isUser ? (
            <div className={styles.userMessageWrapper}>
              {safeContent && <div className={styles.userText}>{safeContent}</div>}
              {fileName && (
                <div className={styles.attachment}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
                  </svg>
                  <span>{fileName}</span>
                </div>
              )}
            </div>
          ) : (
            <div 
              className={styles.markdown} 
              dangerouslySetInnerHTML={{ __html: html }} 
            />
          )}
        </div>
        <div className={styles.meta}>
          <span className={styles.time}>{time}</span>
          {wordCount > 0 && <span className={styles.wordCount}>{wordCount} 字</span>}
          <div className={styles.actions}>
            <button
              className={`${styles.actionBtn} ${copied ? styles.copied : ''}`}
              onClick={handleCopy}
              title="复制内容"
            >
              {copied ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              )}
            </button>
            {!isUser && isLast && onRetry && (
              <button
                className={styles.actionBtn}
                onClick={onRetry}
                title="重新生成"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="23 4 23 10 17 10" />
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
