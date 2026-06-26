import { useState, useRef, useEffect } from 'react'
import { showToast } from '../Toast/Toast'
import styles from './InputArea.module.css'

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
const ALLOWED_FILE_TYPES = '.doc,.docx,.pdf,.txt,.xls,.xlsx'
const ALLOWED_FILE_EXTENSIONS = ['doc', 'docx', 'pdf', 'txt', 'xls', 'xlsx']

export default function InputArea({ onSend, onAbort, showFileUpload, isLoading, isCenter, initialValue }) {
  const [value, setValue] = useState('')
  const [file, setFile] = useState(null)
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (initialValue) {
      setValue(initialValue)
      // 调整textarea高度
      setTimeout(() => {
        const el = textareaRef.current
        if (el) {
          el.style.height = 'auto'
          el.style.height = Math.min(el.scrollHeight, 120) + 'px'
          el.focus()
        }
      }, 0)
    }
  }, [initialValue])

  const handleInput = (e) => {
    setValue(e.target.value)
    const el = textareaRef.current
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFileChange = (e) => {
    const selected = e.target.files[0]
    if (selected) {
      if (selected.size > MAX_FILE_SIZE) {
        showToast(`文件大小不能超过 ${MAX_FILE_SIZE / 1024 / 1024}MB`, 'warning')
        e.target.value = ''
        return
      }
      
      const ext = selected.name.split('.').pop().toLowerCase()
      if (!ALLOWED_FILE_EXTENSIONS.includes(ext)) {
        showToast(`不支持 .${ext} 格式，请上传 Word/PDF/TXT/Excel 文件`, 'warning')
        e.target.value = ''
        return
      }
      
      setFile(selected)
    }
  }

  const removeFile = () => {
    setFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleSend = () => {
    const text = value.trim()
    if (!text && !file) return
    onSend(text, file)
    setValue('')
    setFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    textareaRef.current.style.height = 'auto'
  }

  return (
    <div className={`${styles.inputArea} ${isCenter ? styles.center : ''}`}>
      {file && (
        <div className={styles.fileTag}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          <span className={styles.fileName}>{file.name}</span>
          <button className={styles.removeFile} onClick={removeFile}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      )}
      <div className={styles.wrapper}>
        {showFileUpload && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              className={styles.hiddenInput}
              onChange={handleFileChange}
              accept={ALLOWED_FILE_TYPES}
            />
            <button
              className={styles.uploadBtn}
              onClick={() => fileInputRef.current?.click()}
              title="上传文件 (支持 Word/PDF/TXT/Excel)"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
              </svg>
            </button>
          </>
        )}
        <textarea
          ref={textareaRef}
          className={styles.input}
          placeholder="输入内容开始对话..."
          rows={1}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
        />
        {isLoading ? (
          <button
            className={styles.abortBtn}
            onClick={onAbort}
            title="中止回复"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <rect x="4" y="4" width="16" height="16" rx="2" />
            </svg>
          </button>
        ) : (
          <button
            className={styles.sendBtn}
            onClick={handleSend}
            disabled={!value.trim() && !file}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        )}
      </div>
      {showFileUpload && !isCenter && (
        <div className={styles.fileHint}>
          支持 Word (.doc/.docx)、PDF、TXT、Excel (.xls/.xlsx)，最大 10MB
        </div>
      )}
    </div>
  )
}
