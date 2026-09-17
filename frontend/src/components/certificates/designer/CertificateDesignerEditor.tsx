/**
 * CertificateDesignerEditor — wires DesignerCanvas + DesignerToolbar +
 * LayersPanel + ElementProperties into the full editor screen (plan
 * Task 7). Shared between the instructor page and the admin certificates
 * tab; `isAdmin` unlocks the is_global toggle.
 *
 * Owns: undo/redo history (useReducer over designerHistoryReducer), zoom,
 * selection, localStorage draft autosave + restore-on-open prompt, Save
 * (create or update), Preview (calls the server preview endpoint and shows
 * the result in a modal).
 */
import * as React from 'react'
import toast from 'react-hot-toast'
import { X, Globe2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { DesignerCanvas } from './DesignerCanvas'
import { DesignerToolbar } from './DesignerToolbar'
import { LayersPanel } from './LayersPanel'
import { ElementProperties } from './ElementProperties'
import {
  createDesignerTemplate,
  updateDesignerTemplate,
  previewDesignerTemplate,
  errorDetail,
} from '@/api/certificateDesigner'
import type { DesignerElement, DesignerTemplate, ElementType, Orientation } from '@/lib/certificateDesignerTypes'
import { SIZE_PRESETS, ZOOM_DEFAULT, MAX_ELEMENTS, makeElementId } from '@/lib/certificateDesignerTypes'
import { designerHistoryReducer, createHistory, canUndo, canRedo } from '@/lib/designerHistory'
import { saveDraft, loadDraft, clearDraft } from '@/lib/designerDraftStorage'

export interface CertificateDesignerEditorProps {
  /** null = creating a brand-new template */
  template: DesignerTemplate | null
  isAdmin?: boolean
  onSaved: (template: DesignerTemplate) => void
  onCancel: () => void
}

function newElement(type: ElementType, existingCount: number): DesignerElement {
  const base: DesignerElement = {
    id: makeElementId(),
    type,
    x: 100,
    y: 100,
    width: 300,
    height: 60,
    rotation: 0,
    z_index: existingCount,
  }
  if (type === 'text') base.content = 'Sample text'
  if (['text', 'student_name', 'course_name', 'completion_date', 'certificate_id', 'instructor_name'].includes(type)) {
    base.font_size = 24
    base.font_color = '#1a1a1a'
    base.font_weight = 'normal'
    base.text_align = 'center'
  }
  if (type === 'qr_code') {
    base.width = 120
    base.height = 120
  }
  if (type === 'image' || type === 'signature_image') {
    base.width = 200
    base.height = 100
  }
  if (type === 'rect') {
    base.width = 200
    base.height = 100
    base.background_color = '#f3f4f6'
  }
  if (type === 'line') {
    base.width = 200
    base.height = 2
    base.line_color = '#000000'
    base.line_thickness = 2
  }
  return base
}

export const CertificateDesignerEditor: React.FC<CertificateDesignerEditorProps> = ({
  template,
  isAdmin,
  onSaved,
  onCancel,
}) => {
  const draftKeyId = template?.id ?? 'new'
  const readOnly = !!template && !isAdmin && !template.is_own

  const [name, setName] = React.useState(template?.name || 'Untitled certificate')
  const [description, setDescription] = React.useState(template?.description || '')
  const [orientation, setOrientation] = React.useState<Orientation>(template?.orientation || 'landscape')
  const [width, setWidth] = React.useState(template?.certificate_width || SIZE_PRESETS.a4_landscape.width)
  const [height, setHeight] = React.useState(template?.certificate_height || SIZE_PRESETS.a4_landscape.height)
  const [backgroundColor, setBackgroundColor] = React.useState(template?.background_color || '#ffffff')
  const [backgroundImage, setBackgroundImage] = React.useState(template?.background_image || '')
  const [isGlobal, setIsGlobal] = React.useState(!!template?.is_global)

  const [history, dispatch] = React.useReducer(
    designerHistoryReducer,
    createHistory(template?.elements_config || [])
  )
  const historyElements = history.present
  // Live drag/resize/rotate frames update this ref + a cheap render tick
  // WITHOUT pushing a history entry (history.present stays the pre-drag
  // snapshot until onCommit fires on pointerup) — a drag gesture must not
  // blow through the bounded 50-entry undo stack one frame at a time.
  const elementsRef = React.useRef(historyElements)
  // Bumped by handleLiveChange to force a re-render mid-drag; the number
  // itself is never read, only used as a React state identity change so
  // `elements` below re-derives from the mutated ref on every drag frame.
  const [, forceLiveRender] = React.useState(0)
  React.useEffect(() => {
    elementsRef.current = historyElements
  }, [historyElements])
  const elements = elementsRef.current

  const [selectedId, setSelectedId] = React.useState<string | null>(null)
  const [zoom, setZoom] = React.useState(ZOOM_DEFAULT)
  const [saving, setSaving] = React.useState(false)
  const [previewing, setPreviewing] = React.useState(false)
  const [previewUrl, setPreviewUrl] = React.useState<string | null>(null)
  const [draftPromptShown, setDraftPromptShown] = React.useState(false)
  const [pendingDraft, setPendingDraft] = React.useState<ReturnType<typeof loadDraft>>(null)

  // Restore-draft prompt on open (plan Task 7 binding).
  React.useEffect(() => {
    const draft = loadDraft(draftKeyId)
    if (draft && draft.elements.length > 0) {
      setPendingDraft(draft)
      setDraftPromptShown(true)
    }
     
  }, [draftKeyId])

  // Autosave draft on every committed change.
  React.useEffect(() => {
    if (readOnly) return
    saveDraft(draftKeyId, {
      elements,
      background_color: backgroundColor,
      background_image: backgroundImage,
      orientation,
      certificate_width: width,
      certificate_height: height,
    })
  }, [draftKeyId, elements, backgroundColor, backgroundImage, orientation, width, height, readOnly])

  const commit = (next: DesignerElement[]) => {
    dispatch({ type: 'PUSH', elements: next })
  }

  const handleLiveChange = (id: string, patch: Partial<DesignerElement>) => {
    elementsRef.current = elementsRef.current.map((el) => (el.id === id ? { ...el, ...patch } : el))
    // Cheap render tick so the canvas reflects the in-progress drag/resize/
    // rotate — no history push here (history.present is untouched until
    // onCommit fires on pointerup, so a whole gesture is exactly ONE undo
    // step, not one per mousemove frame).
    forceLiveRender((t) => t + 1)
  }

  const handleAddElement = (type: ElementType) => {
    if (elements.length >= MAX_ELEMENTS) {
      toast.error(`Maximum of ${MAX_ELEMENTS} elements reached`)
      return
    }
    const el = newElement(type, elements.length)
    commit([...elements, el])
    setSelectedId(el.id)
  }

  const handlePropertyChange = (patch: Partial<DesignerElement>) => {
    if (!selectedId) return
    commit(elements.map((el) => (el.id === selectedId ? { ...el, ...patch } : el)))
  }

  const handleApplyPreset = (key: keyof typeof SIZE_PRESETS) => {
    const preset = SIZE_PRESETS[key]
    setWidth(preset.width)
    setHeight(preset.height)
    setOrientation(preset.orientation)
  }

  const handleRestoreDraft = () => {
    if (pendingDraft) {
      dispatch({ type: 'RESET', elements: pendingDraft.elements })
      setBackgroundColor(pendingDraft.background_color)
      setBackgroundImage(pendingDraft.background_image)
      setOrientation(pendingDraft.orientation)
      setWidth(pendingDraft.certificate_width)
      setHeight(pendingDraft.certificate_height)
    }
    setDraftPromptShown(false)
  }

  const handleDiscardDraft = () => {
    clearDraft(draftKeyId)
    setDraftPromptShown(false)
  }

  const handleSave = async () => {
    if (readOnly) return
    if (!name.trim()) {
      toast.error('Please give the template a name')
      return
    }
    setSaving(true)
    try {
      const payload = {
        name: name.trim(),
        description,
        orientation,
        certificate_width: width,
        certificate_height: height,
        background_color: backgroundColor,
        background_image: backgroundImage,
        elements_config: elements,
        ...(isAdmin ? { is_global: isGlobal } : {}),
      }
      const saved = template
        ? await updateDesignerTemplate(template.id, payload)
        : await createDesignerTemplate(payload)
      clearDraft(draftKeyId)
      toast.success('Template saved')
      onSaved(saved)
    } catch (err) {
      toast.error(errorDetail(err, 'Failed to save template'))
    } finally {
      setSaving(false)
    }
  }

  const handlePreview = async () => {
    if (!template) {
      toast.error('Save the template first to generate a live preview')
      return
    }
    setPreviewing(true)
    try {
      const res = await previewDesignerTemplate(template.id)
      setPreviewUrl(res.preview_url)
    } catch (err) {
      toast.error(errorDetail(err, 'Failed to generate preview'))
    } finally {
      setPreviewing(false)
    }
  }

  const selectedElement = elements.find((el) => el.id === selectedId) || null

  return (
    <div className="space-y-4">
      {draftPromptShown && (
        <Card className="p-4 bg-warning-50 border-warning-200 flex items-center justify-between gap-4">
          <p className="text-sm text-warning-800">
            A locally-saved draft of this template was found. Restore it, or discard and start
            from the saved version?
          </p>
          <div className="flex gap-2 shrink-0">
            <Button type="button" size="sm" variant="outline" onClick={handleDiscardDraft}>
              Discard
            </Button>
            <Button type="button" size="sm" onClick={handleRestoreDraft}>
              Restore draft
            </Button>
          </div>
        </Card>
      )}

      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex-1 min-w-[240px]">
          <input
            className="text-lg font-semibold border-none bg-transparent focus:outline-none focus:ring-0 w-full"
            value={name}
            disabled={readOnly}
            onChange={(e) => setName(e.target.value)}
            placeholder="Template name"
            aria-label="Template name"
          />
          <input
            className="text-sm text-neutral-500 border-none bg-transparent focus:outline-none focus:ring-0 w-full"
            value={description}
            disabled={readOnly}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description (optional)"
            aria-label="Template description"
          />
        </div>
        <div className="flex items-center gap-3">
          {isAdmin && (
            <label className="flex items-center gap-1.5 text-sm text-neutral-700">
              <input
                type="checkbox"
                checked={isGlobal}
                onChange={(e) => setIsGlobal(e.target.checked)}
              />
              <Globe2 size={14} />
              Global (visible to all instructors)
            </label>
          )}
          <Button type="button" variant="ghost" onClick={onCancel} aria-label="Close editor">
            <X size={18} />
          </Button>
        </div>
      </div>

      <DesignerToolbar
        onAddElement={handleAddElement}
        zoom={zoom}
        onZoomChange={setZoom}
        canUndo={canUndo(history)}
        canRedo={canRedo(history)}
        onUndo={() => dispatch({ type: 'UNDO' })}
        onRedo={() => dispatch({ type: 'REDO' })}
        onApplyPreset={handleApplyPreset}
        onSave={handleSave}
        saving={saving}
        onPreview={handlePreview}
        previewing={previewing}
        disabled={readOnly}
      />

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_260px_280px] gap-4">
        <DesignerCanvas
          elements={elements}
          width={width}
          height={height}
          backgroundColor={backgroundColor}
          backgroundImage={backgroundImage}
          zoom={zoom}
          selectedId={readOnly ? null : selectedId}
          onSelect={setSelectedId}
          onLiveChange={readOnly ? () => {} : handleLiveChange}
          onCommit={readOnly ? () => {} : commit}
          elementsRef={elementsRef}
        />

        <Card className="p-3">
          <h3 className="text-sm font-semibold text-neutral-700 mb-2">Layers</h3>
          <LayersPanel
            elements={elements}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onReorder={readOnly ? () => {} : commit}
            onDelete={(id) => {
              if (readOnly) return
              commit(elements.filter((el) => el.id !== id))
              if (selectedId === id) setSelectedId(null)
            }}
          />

          <div className="mt-4 pt-4 border-t border-neutral-200 space-y-2">
            <h3 className="text-sm font-semibold text-neutral-700">Background</h3>
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1">Color</label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={/^#[0-9a-fA-F]{3,8}$/.test(backgroundColor) ? backgroundColor : '#ffffff'}
                  disabled={readOnly}
                  onChange={(e) => setBackgroundColor(e.target.value)}
                  className="w-9 h-9 rounded border border-neutral-300 cursor-pointer p-0.5"
                />
                <input
                  type="text"
                  className="input flex-1 text-sm"
                  value={backgroundColor}
                  disabled={readOnly}
                  onChange={(e) => setBackgroundColor(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1">Background image URL</label>
              <input
                type="text"
                className="input w-full text-sm"
                value={backgroundImage}
                disabled={readOnly}
                onChange={(e) => setBackgroundImage(e.target.value)}
                placeholder="/uploads/..."
              />
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <h3 className="text-sm font-semibold text-neutral-700 mb-2">Properties</h3>
          <ElementProperties element={selectedElement} onChange={handlePropertyChange} disabled={readOnly} />
        </Card>
      </div>

      {previewUrl && (
        <div
          className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-6"
          onClick={() => setPreviewUrl(null)}
          role="dialog"
          aria-modal="true"
          aria-label="Certificate preview"
        >
          <div
            className="bg-white rounded-lg overflow-hidden max-w-4xl w-full max-h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-3 border-b border-neutral-200">
              <span className="font-medium text-sm">Preview</span>
              <Button type="button" variant="ghost" size="icon" onClick={() => setPreviewUrl(null)} aria-label="Close preview">
                <X size={16} />
              </Button>
            </div>
            <div className="flex-1 overflow-auto p-3">
              <iframe
                title="Certificate preview"
                src={previewUrl}
                className="w-full h-[70vh] border-0"
                sandbox="allow-same-origin"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default CertificateDesignerEditor
