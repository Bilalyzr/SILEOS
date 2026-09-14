/**
 * DesignerToolbar — add-element menu, zoom, undo/redo, size presets,
 * Save, Preview (plan Task 7).
 */
import * as React from 'react'
import {
  Type, User, BookOpen, Calendar, Hash, UserSquare2, QrCode, PenTool,
  Image as ImageIcon, Square, Minus, Undo2, Redo2, ZoomIn, ZoomOut, Eye, Save,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ElementType } from '@/lib/certificateDesignerTypes'
import { SIZE_PRESETS, ZOOM_MAX, ZOOM_MIN } from '@/lib/certificateDesignerTypes'
import { clampZoom } from '@/lib/designerSnap'

const ADD_MENU: { type: ElementType; label: string; icon: React.ElementType }[] = [
  { type: 'text', label: 'Text', icon: Type },
  { type: 'student_name', label: 'Student Name', icon: User },
  { type: 'course_name', label: 'Course Name', icon: BookOpen },
  { type: 'completion_date', label: 'Completion Date', icon: Calendar },
  { type: 'certificate_id', label: 'Certificate ID', icon: Hash },
  { type: 'instructor_name', label: 'Instructor Name', icon: UserSquare2 },
  { type: 'qr_code', label: 'QR Code', icon: QrCode },
  { type: 'signature_image', label: 'Signature', icon: PenTool },
  { type: 'image', label: 'Image', icon: ImageIcon },
  { type: 'rect', label: 'Rectangle', icon: Square },
  { type: 'line', label: 'Line', icon: Minus },
]

export interface DesignerToolbarProps {
  onAddElement: (type: ElementType) => void
  zoom: number
  onZoomChange: (zoom: number) => void
  canUndo: boolean
  canRedo: boolean
  onUndo: () => void
  onRedo: () => void
  onApplyPreset: (preset: keyof typeof SIZE_PRESETS) => void
  onSave: () => void
  saving?: boolean
  onPreview: () => void
  previewing?: boolean
  disabled?: boolean
}

export const DesignerToolbar: React.FC<DesignerToolbarProps> = ({
  onAddElement,
  zoom,
  onZoomChange,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onApplyPreset,
  onSave,
  saving,
  onPreview,
  previewing,
  disabled,
}) => {
  const [menuOpen, setMenuOpen] = React.useState(false)

  return (
    <div className="flex flex-wrap items-center gap-2 p-3 bg-white border border-neutral-200 rounded-lg">
      <div className="relative">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={disabled}
          onClick={() => setMenuOpen((v) => !v)}
        >
          + Add element
        </Button>
        {menuOpen && (
          <div
            className="absolute z-20 mt-1 w-56 bg-white border border-neutral-200 rounded-lg shadow-medium py-1 max-h-80 overflow-auto"
            onMouseLeave={() => setMenuOpen(false)}
          >
            {ADD_MENU.map(({ type, label, icon: Icon }) => (
              <button
                key={type}
                type="button"
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-50"
                onClick={() => {
                  onAddElement(type)
                  setMenuOpen(false)
                }}
              >
                <Icon size={15} />
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="h-6 w-px bg-neutral-200" />

      <Button type="button" variant="ghost" size="icon" disabled={!canUndo || disabled} onClick={onUndo} aria-label="Undo">
        <Undo2 size={16} />
      </Button>
      <Button type="button" variant="ghost" size="icon" disabled={!canRedo || disabled} onClick={onRedo} aria-label="Redo">
        <Redo2 size={16} />
      </Button>

      <div className="h-6 w-px bg-neutral-200" />

      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Zoom out"
        onClick={() => onZoomChange(clampZoom(zoom - 10, ZOOM_MIN, ZOOM_MAX))}
      >
        <ZoomOut size={16} />
      </Button>
      <span className="text-sm text-neutral-600 w-12 text-center" data-testid="zoom-value">
        {zoom}%
      </span>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Zoom in"
        onClick={() => onZoomChange(clampZoom(zoom + 10, ZOOM_MIN, ZOOM_MAX))}
      >
        <ZoomIn size={16} />
      </Button>

      <div className="h-6 w-px bg-neutral-200" />

      <select
        className="input text-sm w-40"
        disabled={disabled}
        defaultValue=""
        onChange={(e) => {
          if (e.target.value) onApplyPreset(e.target.value as keyof typeof SIZE_PRESETS)
          e.target.value = ''
        }}
        aria-label="Apply size preset"
      >
        <option value="" disabled>
          Size preset…
        </option>
        {Object.entries(SIZE_PRESETS).map(([key, preset]) => (
          <option key={key} value={key}>
            {preset.label} ({preset.width}×{preset.height})
          </option>
        ))}
      </select>

      <div className="flex-1" />

      <Button type="button" variant="outline" size="sm" disabled={previewing} onClick={onPreview}>
        <Eye size={15} className="mr-1.5" />
        {previewing ? 'Rendering…' : 'Preview'}
      </Button>
      <Button type="button" size="sm" disabled={saving || disabled} onClick={onSave}>
        <Save size={15} className="mr-1.5" />
        {saving ? 'Saving…' : 'Save'}
      </Button>
    </div>
  )
}

export default DesignerToolbar
