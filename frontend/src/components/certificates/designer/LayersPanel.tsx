/**
 * LayersPanel — z-ordered element list (plan Task 7). Click to select,
 * up/down buttons to reorder (swaps z_index with the neighbor above/below
 * in paint order). Visibility toggling is explicitly out of scope per the
 * plan ("visibility not needed").
 */
import * as React from 'react'
import { ChevronUp, ChevronDown, Trash2 } from 'lucide-react'
import type { DesignerElement } from '@/lib/certificateDesignerTypes'

const TYPE_LABEL: Record<string, string> = {
  text: 'Text',
  student_name: 'Student Name',
  course_name: 'Course Name',
  completion_date: 'Completion Date',
  certificate_id: 'Certificate ID',
  instructor_name: 'Instructor Name',
  qr_code: 'QR Code',
  signature_image: 'Signature',
  image: 'Image',
  rect: 'Rectangle',
  line: 'Line',
}

function elementLabel(el: DesignerElement): string {
  const base = TYPE_LABEL[el.type] || el.type
  if (el.type === 'text' && el.content) {
    const trimmed = el.content.trim()
    if (trimmed) return trimmed.length > 24 ? `${trimmed.slice(0, 24)}…` : trimmed
  }
  return base
}

export interface LayersPanelProps {
  elements: DesignerElement[]
  selectedId: string | null
  onSelect: (id: string) => void
  onReorder: (elements: DesignerElement[]) => void
  onDelete: (id: string) => void
}

export const LayersPanel: React.FC<LayersPanelProps> = ({
  elements,
  selectedId,
  onSelect,
  onReorder,
  onDelete,
}) => {
  // Top of the list = highest z_index (painted last / on top), matching
  // how a designer visually thinks about layers.
  const ordered = [...elements].sort((a, b) => (b.z_index || 0) - (a.z_index || 0))

  const move = (index: number, direction: -1 | 1) => {
    const targetIndex = index + direction
    if (targetIndex < 0 || targetIndex >= ordered.length) return
    const a = ordered[index]
    const b = ordered[targetIndex]
    const nextElements = elements.map((el) => {
      if (el.id === a.id) return { ...el, z_index: b.z_index }
      if (el.id === b.id) return { ...el, z_index: a.z_index }
      return el
    })
    onReorder(nextElements)
  }

  if (elements.length === 0) {
    return (
      <div className="text-sm text-neutral-500 p-3 text-center">
        No elements yet. Add one from the toolbar.
      </div>
    )
  }

  return (
    <ul className="space-y-1" aria-label="Layers">
      {ordered.map((el, index) => (
        <li
          key={el.id}
          className={`flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm cursor-pointer border ${
            el.id === selectedId
              ? 'bg-primary-50 border-primary-300 text-primary-700'
              : 'border-transparent hover:bg-neutral-50 text-neutral-700'
          }`}
          onClick={() => onSelect(el.id)}
        >
          <span className="flex-1 truncate">{elementLabel(el)}</span>
          <button
            type="button"
            aria-label={`Move ${elementLabel(el)} up`}
            className="p-0.5 rounded hover:bg-neutral-200 disabled:opacity-30"
            disabled={index === 0}
            onClick={(e) => {
              e.stopPropagation()
              move(index, -1)
            }}
          >
            <ChevronUp size={14} />
          </button>
          <button
            type="button"
            aria-label={`Move ${elementLabel(el)} down`}
            className="p-0.5 rounded hover:bg-neutral-200 disabled:opacity-30"
            disabled={index === ordered.length - 1}
            onClick={(e) => {
              e.stopPropagation()
              move(index, 1)
            }}
          >
            <ChevronDown size={14} />
          </button>
          <button
            type="button"
            aria-label={`Delete ${elementLabel(el)}`}
            className="p-0.5 rounded hover:bg-danger-50 text-danger-600"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(el.id)
            }}
          >
            <Trash2 size={14} />
          </button>
        </li>
      ))}
    </ul>
  )
}

export default LayersPanel
