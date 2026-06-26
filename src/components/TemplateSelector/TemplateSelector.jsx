import { useState, useEffect } from 'react'
import { fetchTemplates, createTemplate, updateTemplate } from '../../api/index'
import { showToast } from '../Toast/Toast'
import styles from './TemplateSelector.module.css'

export default function TemplateSelector({ onSelect, onClose, userId }) {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedType, setSelectedType] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [view, setView] = useState('list') // list, detail, create, edit
  const [selectedTemplate, setSelectedTemplate] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    product_type: '',
    description: '',
    template_content: ''
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    try {
      setLoading(true)
      const data = await fetchTemplates()
      setTemplates(data || [])
    } catch (err) {
      console.error('加载模板失败:', err)
    } finally {
      setLoading(false)
    }
  }

  const productTypes = [...new Set(templates.map(t => t.product_type).filter(Boolean))]

  const filteredTemplates = templates.filter(t => {
    if (selectedType && t.product_type !== selectedType) return false
    if (searchTerm && !t.name.includes(searchTerm) && !t.description?.includes(searchTerm)) return false
    return true
  })

  const handleViewDetail = (template) => {
    setSelectedTemplate(template)
    setView('detail')
  }

  const handleCreate = () => {
    setFormData({
      name: '',
      product_type: '',
      description: '',
      template_content: ''
    })
    setView('create')
  }

  const handleEdit = (template) => {
    setFormData({
      name: template.name,
      product_type: template.product_type || '',
      description: template.description || '',
      template_content: template.template_content
    })
    setSelectedTemplate(template)
    setView('edit')
  }

  const handleSave = async () => {
    if (!formData.name.trim()) {
      showToast('请输入模板名称', 'error')
      return
    }
    if (!formData.template_content.trim()) {
      showToast('请输入模板内容', 'error')
      return
    }

    setSaving(true)
    try {
      if (view === 'create') {
        await createTemplate({
          ...formData,
          category: 'custom'
        })
        showToast('模板创建成功', 'success')
      } else {
        await updateTemplate(selectedTemplate.id, formData)
        showToast('模板更新成功', 'success')
      }
      await loadTemplates()
      setView('list')
    } catch (err) {
      showToast('保存失败: ' + err.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleUseTemplate = (template) => {
    onSelect(template)
    onClose()
  }

  const renderListView = () => (
    <>
      <div className={styles.filters}>
        <div className={styles.typeFilter}>
          <button
            className={`${styles.typeBtn} ${!selectedType ? styles.active : ''}`}
            onClick={() => setSelectedType(null)}
          >
            全部
          </button>
          {productTypes.map(type => (
            <button
              key={type}
              className={`${styles.typeBtn} ${selectedType === type ? styles.active : ''}`}
              onClick={() => setSelectedType(type)}
            >
              {type}
            </button>
          ))}
        </div>
        <div className={styles.filterActions}>
          <input
            className={styles.searchInput}
            type="text"
            placeholder="搜索模板..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />
          <button className={styles.createBtn} onClick={handleCreate}>
            + 新建模板
          </button>
        </div>
      </div>

      <div className={styles.content}>
        {loading ? (
          <div className={styles.loading}>加载中...</div>
        ) : filteredTemplates.length === 0 ? (
          <div className={styles.empty}>暂无模板</div>
        ) : (
          <div className={styles.grid}>
            {filteredTemplates.map(template => (
              <div
                key={template.id}
                className={styles.card}
              >
                <div className={styles.cardHeader}>
                  <span className={`${styles.badge} ${template.category === 'preset' ? styles.preset : styles.custom}`}>
                    {template.category === 'preset' ? '系统' : '自定义'}
                  </span>
                  {template.product_type && (
                    <span className={styles.typeTag}>{template.product_type}</span>
                  )}
                </div>
                <h4 className={styles.cardTitle}>{template.name}</h4>
                <p className={styles.cardDesc}>{template.description || '暂无描述'}</p>
                <div className={styles.cardActions}>
                  <button className={styles.detailBtn} onClick={() => handleViewDetail(template)}>
                    查看详情
                  </button>
                  <button className={styles.useBtn} onClick={() => handleUseTemplate(template)}>
                    使用
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )

  const renderDetailView = () => (
    <div className={styles.detailView}>
      <div className={styles.detailHeader}>
        <button className={styles.backBtn} onClick={() => setView('list')}>← 返回</button>
        <div className={styles.detailActions}>
          {selectedTemplate.category !== 'preset' && (
            <button className={styles.editBtn} onClick={() => handleEdit(selectedTemplate)}>
              编辑
            </button>
          )}
          <button className={styles.useBtn} onClick={() => handleUseTemplate(selectedTemplate)}>
            使用此模板
          </button>
        </div>
      </div>
      <div className={styles.detailContent}>
        <div className={styles.detailInfo}>
          <span className={`${styles.badge} ${selectedTemplate.category === 'preset' ? styles.preset : styles.custom}`}>
            {selectedTemplate.category === 'preset' ? '系统模板' : '自定义模板'}
          </span>
          {selectedTemplate.product_type && (
            <span className={styles.typeTag}>{selectedTemplate.product_type}</span>
          )}
        </div>
        <h3 className={styles.detailTitle}>{selectedTemplate.name}</h3>
        {selectedTemplate.description && (
          <p className={styles.detailDesc}>{selectedTemplate.description}</p>
        )}
        <div className={styles.detailTemplate}>
          <h4>模板内容</h4>
          <pre className={styles.templateContent}>{selectedTemplate.template_content}</pre>
        </div>
      </div>
    </div>
  )

  const renderFormView = () => (
    <div className={styles.formView}>
      <div className={styles.formHeader}>
        <button className={styles.backBtn} onClick={() => setView(view === 'create' ? 'list' : 'detail')}>
          ← 返回
        </button>
        <h3>{view === 'create' ? '新建模板' : '编辑模板'}</h3>
        <button 
          className={styles.saveBtn} 
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? '保存中...' : '保存'}
        </button>
      </div>
      <div className={styles.formContent}>
        <div className={styles.formGroup}>
          <label>模板名称 *</label>
          <input
            type="text"
            value={formData.name}
            onChange={e => setFormData({...formData, name: e.target.value})}
            placeholder="输入模板名称"
          />
        </div>
        <div className={styles.formGroup}>
          <label>产品类型</label>
          <input
            type="text"
            value={formData.product_type}
            onChange={e => setFormData({...formData, product_type: e.target.value})}
            placeholder="如：通信、数码、食品等"
          />
        </div>
        <div className={styles.formGroup}>
          <label>模板描述</label>
          <input
            type="text"
            value={formData.description}
            onChange={e => setFormData({...formData, description: e.target.value})}
            placeholder="简短描述模板用途"
          />
        </div>
        <div className={styles.formGroup}>
          <label>模板内容 *</label>
          <textarea
            value={formData.template_content}
            onChange={e => setFormData({...formData, template_content: e.target.value})}
            placeholder="输入模板内容，支持 Markdown 格式"
            rows={15}
          />
        </div>
      </div>
    </div>
  )

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <div className={styles.header}>
          <h3>
            {view === 'list' && '选择脚本模板'}
            {view === 'detail' && '模板详情'}
            {view === 'create' && '新建模板'}
            {view === 'edit' && '编辑模板'}
          </h3>
          <button className={styles.closeBtn} onClick={onClose}>×</button>
        </div>

        {view === 'list' && renderListView()}
        {view === 'detail' && renderDetailView()}
        {(view === 'create' || view === 'edit') && renderFormView()}
      </div>
    </div>
  )
}
