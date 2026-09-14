/**
 * TemplateGallery — grid of own + global certificate templates (plan
 * Task 7). A template row MAY carry a real Chrome-rendered `thumbnail` PNG
 * URL (Task 8 fix round D-8, populated by seed_designer_templates.py when
 * Chrome is available) — the card renders that image when present, and
 * falls back to a lightweight scaled-down CSS swatch of the template's
 * background/orientation as a placeholder otherwise (e.g. Chrome absent at
 * seed time, or an instructor's freshly-created draft with no render yet).
 */
import * as React from 'react'
import { confirmDialog } from '@/components/ui/confirm'
import { Plus, Copy, Trash2, Pencil, Globe2, Lock } from 'lucide-react'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import type { DesignerTemplate } from '@/lib/certificateDesignerTypes'
import {
  deleteDesignerTemplate,
  duplicateDesignerTemplate,
  errorDetail,
  isDeleteConflict,
} from '@/api/certificateDesigner'

export interface TemplateGalleryProps {
  templates: DesignerTemplate[]
  loading: boolean
  onCreateNew: () => void
  onEdit: (template: DesignerTemplate) => void
  onChanged: () => void
  isAdmin?: boolean
}

const CARD_PREVIEW_HEIGHT = 110

export const TemplateGallery: React.FC<TemplateGalleryProps> = ({
  templates,
  loading,
  onCreateNew,
  onEdit,
  onChanged,
  isAdmin,
}) => {
  const [busyId, setBusyId] = React.useState<number | null>(null)

  const handleDuplicate = async (template: DesignerTemplate) => {
    setBusyId(template.id)
    try {
      await duplicateDesignerTemplate(template.id)
      toast.success(`Duplicated "${template.name}"`)
      onChanged()
    } catch (err) {
      toast.error(errorDetail(err, 'Failed to duplicate template'))
    } finally {
      setBusyId(null)
    }
  }

  const handleDelete = async (template: DesignerTemplate) => {
    if (!await confirmDialog(`Delete "${template.name}"? This cannot be undone.`)) return
    setBusyId(template.id)
    try {
      await deleteDesignerTemplate(template.id)
      toast.success(`Deleted "${template.name}"`)
      onChanged()
    } catch (err) {
      if (isDeleteConflict(err)) {
        toast.error(
          errorDetail(err, 'Template is in use (assigned to a course or has issued certificates) and cannot be deleted')
        )
      } else {
        toast.error(errorDetail(err, 'Failed to delete template'))
      }
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-neutral-900">Certificate templates</h2>
        <Button type="button" size="sm" onClick={onCreateNew}>
          <Plus size={15} className="mr-1.5" />
          New template
        </Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="h-48 dash-skeleton" />
          ))}
        </div>
      ) : templates.length === 0 ? (
        <Card className="p-10 text-center">
          <p className="text-neutral-600 mb-3">No certificate templates yet.</p>
          <Button type="button" onClick={onCreateNew}>
            <Plus size={15} className="mr-1.5" />
            Create your first template
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map((template) => {
            const aspect = template.certificate_width / template.certificate_height
            const canEdit = isAdmin || template.is_own
            return (
              <Card key={template.id} className="overflow-hidden flex flex-col" data-testid={`template-card-${template.id}`}>
                <div
                  className="bg-neutral-100 flex items-center justify-center relative"
                  style={{ height: CARD_PREVIEW_HEIGHT }}
                >
                  {template.thumbnail ? (
                    // Real Chrome-rendered preview (Task 8 fix round D-8) —
                    // takes priority over the CSS swatch below when present.
                    <img
                      src={template.thumbnail}
                      alt={`${template.name} preview`}
                      className="border border-neutral-300 shadow-sm object-cover"
                      style={{
                        height: CARD_PREVIEW_HEIGHT - 24,
                        width: (CARD_PREVIEW_HEIGHT - 24) * aspect,
                        maxWidth: '90%',
                      }}
                    />
                  ) : (
                    <div
                      className="border border-neutral-300 shadow-sm"
                      style={{
                        height: CARD_PREVIEW_HEIGHT - 24,
                        width: (CARD_PREVIEW_HEIGHT - 24) * aspect,
                        maxWidth: '90%',
                        backgroundColor: template.background_color || '#ffffff',
                        backgroundImage: template.background_image ? `url(${template.background_image})` : undefined,
                        backgroundSize: 'cover',
                        backgroundPosition: 'center',
                      }}
                    />
                  )}
                  {template.is_global && (
                    <span className="absolute top-2 right-2 inline-flex items-center gap-1 bg-white/90 text-[11px] font-medium text-neutral-600 px-1.5 py-0.5 rounded">
                      <Globe2 size={11} /> Global
                    </span>
                  )}
                  {!canEdit && (
                    <span className="absolute top-2 left-2 inline-flex items-center gap-1 bg-white/90 text-[11px] font-medium text-neutral-500 px-1.5 py-0.5 rounded">
                      <Lock size={11} /> Read-only
                    </span>
                  )}
                </div>
                <div className="p-3 flex-1 flex flex-col">
                  <p className="font-medium text-neutral-900 truncate" title={template.name}>
                    {template.name}
                  </p>
                  <p className="text-xs text-neutral-500 mb-3">
                    {template.orientation} &middot; {template.certificate_width}×{template.certificate_height}
                  </p>
                  <div className="mt-auto flex items-center gap-1.5">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => onEdit(template)}
                    >
                      <Pencil size={13} className="mr-1" />
                      {canEdit ? 'Edit' : 'View'}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={`Duplicate ${template.name}`}
                      disabled={busyId === template.id}
                      onClick={() => handleDuplicate(template)}
                    >
                      <Copy size={14} />
                    </Button>
                    {canEdit && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label={`Delete ${template.name}`}
                        disabled={busyId === template.id}
                        onClick={() => handleDelete(template)}
                      >
                        <Trash2 size={14} className="text-danger-600" />
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default TemplateGallery
