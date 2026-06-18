import { useEffect, useRef } from 'react'
import Message from '../Message/Message'
import TypingIndicator from '../TypingIndicator/TypingIndicator'
import styles from './ChatArea.module.css'

export default function ChatArea({ messages, tool, isTyping, showSuggestions, onSuggestionClick, userInfo, onRetry, forbiddenWords }) {
  const areaRef = useRef(null)

  useEffect(() => {
    const el = areaRef.current
    let timer
    if (el) {
      timer = setTimeout(() => (el.scrollTop = el.scrollHeight), 50)
    }
    return () => clearTimeout(timer)
  }, [messages, isTyping])

  return (
    <div className={styles.area} ref={areaRef}>
      <div className={styles.messages}>
        {messages.map((msg, i) => (
          <Message
            key={msg.id || `${msg.role}-${i}`}
            role={msg.role}
            content={msg.content}
            fileName={msg.fileName}
            time={msg.time}
            tool={tool}
            userInfo={userInfo}
            isLast={i === messages.length - 1 && msg.role === 'assistant' && !isTyping}
            onRetry={onRetry}
            forbiddenWords={forbiddenWords}
          />
        ))}
        {isTyping && <TypingIndicator tool={tool} />}
        {showSuggestions && tool?.suggestions?.length > 0 && (
          <div className={styles.suggestions}>
            {tool.suggestions.map((s) => (
              <button
                key={s}
                className={styles.chip}
                onClick={() => onSuggestionClick(s)}
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
