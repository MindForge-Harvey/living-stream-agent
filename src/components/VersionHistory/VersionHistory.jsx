import { useState, useEffect } from 'react'
import { fetchScriptVersions } from '../../api/index'
import styles from './VersionHistory.module.css'

export default function VersionHistory({ dialogId, onClose }) {
  const [versions, setVersions] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedVersion, setSelectedVersion] = useState(null)
  const [compareMode, setCompareMode] = useState(false)
  const [version1, setVersion1] = useState(null)
  const [version2, setVersion2] = useState(null)

  useEffect(() => {
    if (dialogId) {
      loadVersions()
    }
  }, [dialogId])

  const loadVersions = async () => {
    try {
      setLoading(true)
      const data = await fetchScriptVersions(dialogId)
      setVersions(data || [])
    } catch (err) {
      console.error('加载版本历史失败:', err)
    } finally {
      setLoading(false)
    }
  }

  const getVersionTypeLabel = (type) => {
    switch (type) {
      case 'generated': return '生成'
      case 'scored': return '打分'
      case 'revised': return '订正'
      case 'analyzed': return '分析'
      default: return type
    }
  }

  const getVersionTypeColor = (type) => {
    switch (type) {
      case 'generated': return '#2563eb'
      case 'scored': return '#f59e0b'
      case 'revised': return '#10b981'
      case 'analyzed': return '#8b5cf6'
      default: return '#6b7280'
    }
  }

  const handleVersionClick = (version) => {
    if (compareMode) {
      if (!version1) {
        setVersion1(version)
      } else if (!version2) {
        setVersion2(version)
      } else {
        setVersion1(version)
        setVersion2(null)
      }
    } else {
      setSelectedVersion(version)
    }
  }

  const renderDiff = (text1, text2) => {
    if (!text1 || !text2) return null

    const lines1 = text1.split('\n')
    const lines2 = text2.split('\n')
    const maxLen = Math.max(lines1.length, lines2.length)

    const diffLines = []
    for (let i = 0; i < maxLen; i++) {
      const line1 = lines1[i] || ''
      const line2 = lines2[i] || ''

      if (line1 === line2) {
        diffLines.push({ type: 'same', line1, line2 })
      } else {
        diffLines.push({ type: 'diff', line1, line2 })
      }
    }

    return diffLines
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <div className={styles.header}>
          <h3>脚本版本历史</h3>
          <div className={styles.headerActions}>
            <button
              className={`${styles.compareBtn} ${compareMode ? styles.active : ''}`}
              onClick={() => {
                setCompareMode(!compareMode)
                setVersion1(null)
                setVersion2(null)
              }}
            >
              {compareMode ? '取消对比' : '版本对比'}
            </button>
            <button className={styles.closeBtn} onClick={onClose}>×</button>
          </div>
        </div>

        <div className={styles.content}>
          <div className={styles.sidebar}>
            {loading ? (
              <div className={styles.loading}>加载中...</div>
            ) : versions.length === 0 ? (
              <div className={styles.empty}>暂无版本记录</div>
            ) : (
              <div className={styles.versionList}>
                {versions.map((version, index) => (
                  <div
                    key={version.id}
                    className={`${styles.versionItem} ${
                      selectedVersion?.id === version.id ? styles.selected : ''
                    } ${version1?.id === version.id || version2?.id === version.id ? styles.selected : ''}`}
                    onClick={() => handleVersionClick(version)}
                  >
                    <div className={styles.versionHeader}>
                      <span
                        className={styles.versionType}
                        style={{ background: getVersionTypeColor(version.version_type) }}
                      >
                        {getVersionTypeLabel(version.version_type)}
                      </span>
                      <span className={styles.versionIndex}>v{index + 1}</span>
                    </div>
                    <div className={styles.versionTime}>
                      {version.created_at}
                    </div>
                    {compareMode && (
                      <div className={styles.compareIndicator}>
                        {version1?.id === version.id && '版本 A'}
                        {version2?.id === version.id && '版本 B'}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className={styles.preview}>
            {compareMode ? (
              version1 && version2 ? (
                <div className={styles.diffView}>
                  <div className={styles.diffHeader}>
                    <div className={styles.diffTitle}>
                      <span className={styles.diffTagA}>版本 A</span>
                      <span className={styles.diffTime}>{version1.created_at}</span>
                    </div>
                    <div className={styles.diffTitle}>
                      <span className={styles.diffTagB}>版本 B</span>
                      <span className={styles.diffTime}>{version2.created_at}</span>
                    </div>
                  </div>
                  <div className={styles.diffContent}>
                    {renderDiff(version1.content, version2.content)?.map((line, i) => (
                      <div key={i} className={`${styles.diffLine} ${line.type === 'diff' ? styles.diffChanged : ''}`}>
                        <div className={styles.diffLineA}>
                          <span className={styles.lineNumber}>{i + 1}</span>
                          <span className={styles.lineContent}>{line.line1}</span>
                        </div>
                        <div className={styles.diffLineB}>
                          <span className={styles.lineNumber}>{i + 1}</span>
                          <span className={styles.lineContent}>{line.line2}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className={styles.selectHint}>
                  请选择两个版本进行对比
                </div>
              )
            ) : selectedVersion ? (
              <div className={styles.versionPreview}>
                <div className={styles.previewHeader}>
                  <span
                    className={styles.versionType}
                    style={{ background: getVersionTypeColor(selectedVersion.version_type) }}
                  >
                    {getVersionTypeLabel(selectedVersion.version_type)}
                  </span>
                  <span className={styles.previewTime}>{selectedVersion.created_at}</span>
                </div>
                <div className={styles.previewContent}>
                  <pre>{selectedVersion.content}</pre>
                </div>
              </div>
            ) : (
              <div className={styles.selectHint}>
                选择一个版本查看内容
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
