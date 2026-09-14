import React from 'react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical } from 'lucide-react'

interface SortableLectureProps {
  id: string
  children: React.ReactNode
}

export function SortableLecture({ id, children }: SortableLectureProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    zIndex: isDragging ? 999 : 'auto',
  }
  return (
    <div ref={setNodeRef} style={style as React.CSSProperties} className="relative">
      <div
        {...attributes}
        {...listeners}
        className="absolute left-1 top-4 cursor-grab active:cursor-grabbing text-gray-400 hover:text-orange-500 z-10"
        style={{ touchAction: 'none' }}
      >
        <GripVertical className="h-4 w-4" />
      </div>
      <div className="pl-6">{children}</div>
    </div>
  )
}
