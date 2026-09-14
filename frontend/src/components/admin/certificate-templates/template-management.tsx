import React, { useCallback, useState, useEffect } from 'react'
import {
  Plus,
  Upload,
  Edit,
  Trash2,
  Eye,
  FileImage,
  Settings,
  X,
  Check,
  Loader2
} from 'lucide-react'
import {
  getCertificateTemplates,
  createCertificateTemplate,
  updateCertificateTemplate,
  deleteCertificateTemplate,
  previewCertificateTemplate,
  CertificateTemplate,
  CertificateTemplateCreate,
  TemplateBackground
} from '@/api/admin'
import TemplateBuilder from './template-builder'
import TemplateUploader from './template-uploader'

interface TemplateManagementProps {
  onClose?: () => void
}

const TemplateManagement: React.FC<TemplateManagementProps> = ({ onClose }) => {
  const [templates, setTemplates] = useState<CertificateTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'list' | 'create' | 'upload'>('list')
  const [editingTemplate, setEditingTemplate] = useState<CertificateTemplate | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // New template state for builder
  const [newTemplate, setNewTemplate] = useState<CertificateTemplateCreate>({
    name: '',
    description: '',
    template_type: 'builder',
    background: { type: 'color', value: '#ffffff' },
    dimensions: { width: 1123, height: 794 },
    elements: [],
    orientation: 'landscape',
    is_default: false
  })

  const loadTemplates = useCallback(async () => {
    try {
      setLoading(true)
      const data = await getCertificateTemplates()
      setTemplates(data)
    } catch (error) {
      console.error('Failed to load templates:', error)
      showMessage('error', 'Failed to load templates')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTemplates()
  }, [loadTemplates])

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 5000)
  }

  const handleCreateTemplate = async () => {
    if (!newTemplate.name.trim()) {
      showMessage('error', 'Please enter a template name')
      return
    }

    setSaving(true)
    try {
      await createCertificateTemplate(newTemplate)
      showMessage('success', 'Template created successfully')
      await loadTemplates()
      setActiveTab('list')
      resetNewTemplate()
    } catch (error) {
      console.error('Failed to create template:', error)
      showMessage('error', 'Failed to create template')
    } finally {
      setSaving(false)
    }
  }

  const handleUpdateTemplate = async () => {
    if (!editingTemplate) return

    setSaving(true)
    try {
      await updateCertificateTemplate(editingTemplate.id, editingTemplate)
      showMessage('success', 'Template updated successfully')
      await loadTemplates()
      setEditingTemplate(null)
    } catch (error) {
      console.error('Failed to update template:', error)
      showMessage('error', 'Failed to update template')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteTemplate = async (templateId: number) => {
    if (!confirm('Are you sure you want to delete this template?')) return

    try {
      await deleteCertificateTemplate(templateId)
      showMessage('success', 'Template deleted successfully')
      await loadTemplates()
    } catch (error) {
      console.error('Failed to delete template:', error)
      showMessage('error', error instanceof Error ? error.message : 'Failed to delete template')
    }
  }

  const handlePreview = async (template: CertificateTemplate) => {
    try {
      const result = await previewCertificateTemplate(template.id)
      // Open preview in new tab. Uploaded templates are images; builder/legacy
      // templates come back as a rendered PDF.
      const win = window.open()
      if (win) {
        const viewer = result.preview_type === 'image'
          ? `<img src="${result.preview_url}" alt="${template.name}" style="max-width:100%;height:auto;box-shadow:0 2px 12px rgba(0,0,0,.15);background:#fff;" />`
          : `<embed src="${result.preview_url}" width="100%" style="min-height:90vh;border:none;" type="application/pdf">`
        win.document.write(`
          <html>
            <head><title>Preview: ${template.name}</title></head>
            <body style="margin:0;padding:20px;background:#f0f0f0;display:flex;justify-content:center;align-items:flex-start;">
              ${viewer}
            </body>
          </html>
        `)
      }
    } catch (error) {
      console.error('Failed to generate preview:', error)
      showMessage('error', 'Failed to generate preview')
    }
  }

  const handleEditTemplate = (template: CertificateTemplate) => {
    setEditingTemplate(template)
    setActiveTab('create')
  }

  const resetNewTemplate = () => {
    setNewTemplate({
      name: '',
      description: '',
      template_type: 'builder',
      background: { type: 'color', value: '#ffffff' },
      dimensions: { width: 1123, height: 794 },
      elements: [],
      orientation: 'landscape',
      is_default: false
    })
  }

  const handleUploadComplete = () => {
    showMessage('success', 'Template uploaded successfully')
    loadTemplates()
    setActiveTab('list')
  }

  if (loading && activeTab === 'list') {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Certificate Templates</h2>
          <p className="text-gray-600 mt-1">Manage and customize certificate templates</p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={24} />
          </button>
        )}
      </div>

      {/* Message */}
      {message && (
        <div className={`flex items-center gap-2 p-4 rounded-lg ${
          message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {message.type === 'success' ? <Check size={18} /> : <X size={18} />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6">
          <button
            onClick={() => {
              setActiveTab('list')
              setEditingTemplate(null)
              resetNewTemplate()
            }}
            className={`pb-4 px-1 font-medium transition-colors ${
              activeTab === 'list'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Templates ({templates.length})
          </button>
          <button
            onClick={() => {
              setActiveTab('create')
              setEditingTemplate(null)
              resetNewTemplate()
            }}
            className={`pb-4 px-1 font-medium transition-colors flex items-center gap-2 ${
              activeTab === 'create'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Settings size={18} />
            {editingTemplate ? 'Edit Template' : 'Build Template'}
          </button>
          <button
            onClick={() => setActiveTab('upload')}
            className={`pb-4 px-1 font-medium transition-colors flex items-center gap-2 ${
              activeTab === 'upload'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Upload size={18} />
            Upload Template
          </button>
        </nav>
      </div>

      {/* Content */}
      {activeTab === 'list' && (
        <div>
          <div className="flex justify-end mb-4">
            <button
              onClick={() => setActiveTab('create')}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus size={18} />
              New Template
            </button>
          </div>

          {templates.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-gray-300">
              <FileImage size={48} className="mx-auto text-gray-400 mb-3" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No templates yet</h3>
              <p className="text-gray-500 mb-4">
                Create your first certificate template or upload an existing one
              </p>
              <div className="flex justify-center gap-3">
                <button
                  onClick={() => setActiveTab('create')}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <Settings size={18} />
                  Build Template
                </button>
                <button
                  onClick={() => setActiveTab('upload')}
                  className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <Upload size={18} />
                  Upload Template
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {templates.map((template) => (
                <div
                  key={template.id}
                  className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
                >
                  {/* Preview */}
                  <div className="aspect-video bg-gray-100 relative">
                    {template.preview_url ? (
                      <img
                        src={template.preview_url}
                        alt={template.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <FileImage size={48} className="text-gray-400" />
                      </div>
                    )}
                    <div className="absolute top-2 right-2 flex gap-1">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${
                        template.template_type === 'upload'
                          ? 'bg-purple-100 text-purple-700'
                          : template.template_type === 'builder'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}>
                        {template.template_type}
                      </span>
                    </div>
                  </div>

                  {/* Info */}
                  <div className="p-4">
                    <h3 className="font-semibold text-gray-900 truncate">{template.name}</h3>
                    <p className="text-sm text-gray-500 truncate mt-1">
                      {template.description || 'No description'}
                    </p>
                    <div className="flex items-center justify-between mt-3">
                      <span className="text-xs text-gray-500">
                        {template.usage_count} uses
                      </span>
                      <div className="flex gap-1">
                        <button
                          onClick={() => handlePreview(template)}
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                          title="Preview"
                        >
                          <Eye size={16} />
                        </button>
                        {template.template_type === 'builder' && (
                          <button
                            onClick={() => handleEditTemplate(template)}
                            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            title="Edit"
                          >
                            <Edit size={16} />
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteTemplate(template.id)}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'create' && (
        <div className="space-y-6">
          {/* Template Info */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Template Name *
                </label>
                <input
                  type="text"
                  value={editingTemplate ? editingTemplate.name : newTemplate.name}
                  onChange={(e) => {
                    const val = e.target.value
                    if (editingTemplate) {
                      setEditingTemplate({ ...editingTemplate, name: val })
                    } else {
                      setNewTemplate({ ...newTemplate, name: val })
                    }
                  }}
                  placeholder="Professional Certificate"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Orientation
                </label>
                <select
                  value={editingTemplate ? editingTemplate.orientation : newTemplate.orientation}
                  onChange={(e) => {
                    const val = e.target.value as 'landscape' | 'portrait'
                    if (editingTemplate) {
                      setEditingTemplate({ ...editingTemplate, orientation: val })
                    } else {
                      setNewTemplate({ ...newTemplate, orientation: val })
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="landscape">Landscape</option>
                  <option value="portrait">Portrait</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Background Color
                </label>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={
                      editingTemplate
                        ? editingTemplate.background.value || '#ffffff'
                        : newTemplate.background.value || '#ffffff'
                    }
                    onChange={(e) => {
                      const bg = { type: 'color', value: e.target.value } as TemplateBackground
                      if (editingTemplate) {
                        setEditingTemplate({ ...editingTemplate, background: bg })
                      } else {
                        setNewTemplate({ ...newTemplate, background: bg })
                      }
                    }}
                    className="w-12 h-10 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={
                      editingTemplate
                        ? editingTemplate.background.value || '#ffffff'
                        : newTemplate.background.value || '#ffffff'
                    }
                    onChange={(e) => {
                      const bg = { type: 'color', value: e.target.value } as TemplateBackground
                      if (editingTemplate) {
                        setEditingTemplate({ ...editingTemplate, background: bg })
                      } else {
                        setNewTemplate({ ...newTemplate, background: bg })
                      }
                    }}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
              </div>
            </div>
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={editingTemplate ? editingTemplate.description : newTemplate.description}
                onChange={(e) => {
                  const val = e.target.value
                  if (editingTemplate) {
                    setEditingTemplate({ ...editingTemplate, description: val })
                  } else {
                    setNewTemplate({ ...newTemplate, description: val })
                  }
                }}
                placeholder="Optional description..."
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none"
              />
            </div>
          </div>

          {/* Builder */}
          <TemplateBuilder
            name={editingTemplate ? editingTemplate.name : newTemplate.name}
            description={editingTemplate ? editingTemplate.description ?? '' : newTemplate.description ?? ''}
            background={editingTemplate ? editingTemplate.background : newTemplate.background}
            dimensions={editingTemplate ? editingTemplate.dimensions : newTemplate.dimensions}
            elements={editingTemplate ? editingTemplate.elements : newTemplate.elements}
            orientation={editingTemplate ? editingTemplate.orientation : newTemplate.orientation || 'landscape'}
            onChange={(data) => {
              if (editingTemplate) {
                setEditingTemplate({
                  ...editingTemplate,
                  ...data
                })
              } else {
                setNewTemplate(data)
              }
            }}
          />

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <button
              onClick={() => {
                setActiveTab('list')
                setEditingTemplate(null)
                resetNewTemplate()
              }}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={editingTemplate ? handleUpdateTemplate : handleCreateTemplate}
              disabled={saving || !(editingTemplate?.name || newTemplate.name)?.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Check size={18} />
                  {editingTemplate ? 'Update Template' : 'Create Template'}
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {activeTab === 'upload' && (
        <TemplateUploader
          onUploadComplete={handleUploadComplete}
          onCancel={() => setActiveTab('list')}
        />
      )}
    </div>
  )
}

export default TemplateManagement
