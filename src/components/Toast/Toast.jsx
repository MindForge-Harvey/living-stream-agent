import { useState, useEffect, useCallback } from 'react'
import styles from './Toast.module.css'

let toastId = 0
const listeners = new Set()

export function showToast(message, type = 'error', duration = 3000) {
  const id = ++toastId
  listeners.forEach(listener => listener({ id, message, type, duration }))
  return id
}

export default function Toast() {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((toast) => {
    setToasts(prev => [...prev, toast])
    
    if (toast.duration > 0) {
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== toast.id))
      }, toast.duration)
    }
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  useEffect(() => {
    listeners.add(addToast)
    return () => listeners.delete(addToast)
  }, [addToast])

  if (toasts.length === 0) return null

  return (
    <div className={styles.container}>
      {toasts.map(toast => (
        <div
          key={toast.id}
          className={`${styles.toast} ${styles[toast.type]}`}
          onClick={() => removeToast(toast.id)}
        >
          <div className={styles.icon}>
            {toast.type === 'error' && '✕'}
            {toast.type === 'success' && '✓'}
            {toast.type === 'warning' && '!'}
            {toast.type === 'info' && 'i'}
          </div>
          <div className={styles.message}>{toast.message}</div>
          <button className={styles.close} onClick={() => removeToast(toast.id)}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      ))}
    </div>
  )
}
