import styles from './TypingIndicator.module.css'

export default function TypingIndicator({ tool }) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.spinner} />
      <span className={styles.text}>正在处理...</span>
    </div>
  )
}
