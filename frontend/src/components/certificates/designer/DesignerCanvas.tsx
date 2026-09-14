/**
 * DesignerCanvas — absolute-positioned certificate stage (plan Task 7).
 *
 * Renders every element in the template at its true certificate_width x
 * certificate_height, scaled visually by `zoom` (a CSS transform, so the
 * underlying element coordinates stay in the same px space the server's
 * certificate_html_renderer.py uses — WYSIWYG holds because both sides
 * position with `left/top/width/height` in px and rotate with
 * `transform: rotate(Ndeg)`, see _element_css there).
 *
 * Interactions: click to select, drag to move (pointer events, no new
 * deps), 8 resize handles, one rotate handle, snap-to-center guides while
 * dragging, Delete/Backspace removes the selected element, arrow keys nudge
 * it (Shift = 10px step).
 */
import * as React from 'react'
import { RotateCw } from 'lucide-react'
import type { DesignerElement } from '@/lib/certificateDesignerTypes'
import { snapToCenter, nudgeAmount, SNAP_THRESHOLD_PX } from '@/lib/designerSnap'
import { fontFamilyCss } from '@/lib/curatedFonts'
import { isSafeAssetSrc } from '@/lib/certificateAssetSrc'

export interface DesignerCanvasProps {
  elements: DesignerElement[]
  width: number
  height: number
  backgroundColor: string
  backgroundImage?: string
  zoom: number
  selectedId: string | null
  onSelect: (id: string | null) => void
  /** Called continuously while dragging/resizing/rotating (for live visual
   * feedback) — NOT a history checkpoint. */
  onLiveChange: (id: string, patch: Partial<DesignerElement>) => void
  /** Called once when a drag/resize/rotate/nudge/delete gesture completes —
   * the designer page pushes exactly one history snapshot here. */
  onCommit: (elements: DesignerElement[]) => void
  elementsRef: React.MutableRefObject<DesignerElement[]>
}

type ResizeHandle = 'nw' | 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w'

const RESIZE_HANDLES: ResizeHandle[] = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']

const MIN_SIZE = 12

function resolveText(el: DesignerElement): string {
  switch (el.type) {
    case 'student_name':
      return 'Jordan Alexis Rivera'
    case 'course_name':
      return 'Full-Stack Web Development Mastery'
    case 'completion_date':
      return 'September 2, 2026'
    case 'certificate_id':
      return 'PREVIEW-0000000000'
    case 'instructor_name':
      return 'Dr. Elena Whitfield'
    case 'text':
      return el.content || ''
    default:
      return ''
  }
}

function borderCss(border: DesignerElement['border']): string | undefined {
  if (!border) return undefined
  if (typeof border === 'string') return border
  return `${border.width}px ${border.style} ${border.color}`
}

export const DesignerCanvas: React.FC<DesignerCanvasProps> = ({
  elements,
  width,
  height,
  backgroundColor,
  backgroundImage,
  zoom,
  selectedId,
  onSelect,
  onLiveChange,
  onCommit,
  elementsRef,
}) => {
  const stageRef = React.useRef<HTMLDivElement>(null)
  const [guides, setGuides] = React.useState<{ v: boolean; h: boolean }>({ v: false, h: false })
  const dragState = React.useRef<{
    id: string
    mode: 'move' | 'resize' | 'rotate'
    handle?: ResizeHandle
    startClientX: number
    startClientY: number
    startEl: DesignerElement
    stageRect: DOMRect
  } | null>(null)

  const scale = zoom / 100

  const stopDrag = React.useCallback(() => {
    dragState.current = null
    setGuides({ v: false, h: false })
    onCommit(elementsRef.current)
  }, [onCommit, elementsRef])

  const handlePointerMove = React.useCallback(
    (e: PointerEvent) => {
      const drag = dragState.current
      if (!drag) return
      const dxScreen = e.clientX - drag.startClientX
      const dyScreen = e.clientY - drag.startClientY
      const dx = dxScreen / scale
      const dy = dyScreen / scale

      if (drag.mode === 'move') {
        const nextX = drag.startEl.x + dx
        const nextY = drag.startEl.y + dy
        const snapped = snapToCenter(nextX, nextY, drag.startEl.width, drag.startEl.height, width, height)
        setGuides({ v: snapped.snappedX, h: snapped.snappedY })
        onLiveChange(drag.id, { x: Math.round(snapped.x), y: Math.round(snapped.y) })
      } else if (drag.mode === 'resize' && drag.handle) {
        const patch = computeResize(drag.startEl, drag.handle, dx, dy)
        onLiveChange(drag.id, patch)
      } else if (drag.mode === 'rotate') {
        const cx = drag.stageRect.left + (drag.startEl.x + drag.startEl.width / 2) * scale
        const cy = drag.stageRect.top + (drag.startEl.y + drag.startEl.height / 2) * scale
        const angle = (Math.atan2(e.clientY - cy, e.clientX - cx) * 180) / Math.PI + 90
        onLiveChange(drag.id, { rotation: Math.round(angle) })
      }
    },
    [onLiveChange, scale, width, height]
  )

  React.useEffect(() => {
    const move = (e: PointerEvent) => handlePointerMove(e)
    const up = () => {
      if (dragState.current) stopDrag()
    }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
    return () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
    }
  }, [handlePointerMove, stopDrag])

  const beginDrag = (
    e: React.PointerEvent,
    el: DesignerElement,
    mode: 'move' | 'resize' | 'rotate',
    handle?: ResizeHandle
  ) => {
    e.stopPropagation()
    e.preventDefault()
    onSelect(el.id)
    const stageRect = stageRef.current?.getBoundingClientRect()
    if (!stageRect) return
    dragState.current = {
      id: el.id,
      mode,
      handle,
      startClientX: e.clientX,
      startClientY: e.clientY,
      startEl: { ...el },
      stageRect,
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!selectedId) return
    const el = elements.find((x) => x.id === selectedId)
    if (!el) return
    if (e.key === 'Delete' || e.key === 'Backspace') {
      e.preventDefault()
      const next = elements.filter((x) => x.id !== selectedId)
      onCommit(next)
      onSelect(null)
      return
    }
    const step = nudgeAmount(e.shiftKey)
    let dx = 0
    let dy = 0
    if (e.key === 'ArrowUp') dy = -step
    else if (e.key === 'ArrowDown') dy = step
    else if (e.key === 'ArrowLeft') dx = -step
    else if (e.key === 'ArrowRight') dx = step
    else return
    e.preventDefault()
    const next = elements.map((x) =>
      x.id === selectedId ? { ...x, x: x.x + dx, y: x.y + dy } : x
    )
    onCommit(next)
  }

  return (
    <div
      className="relative overflow-auto bg-neutral-100 rounded-lg border border-neutral-200 p-8"
      style={{ maxHeight: '75vh' }}
    >
      <div
        style={{
          width: width * scale,
          height: height * scale,
        }}
      >
        <div
          ref={stageRef}
          tabIndex={0}
          role="application"
          aria-label="Certificate design canvas"
          onKeyDown={handleKeyDown}
          onPointerDown={() => onSelect(null)}
          className="relative shadow-medium mx-auto outline-none"
          style={{
            width,
            height,
            transform: `scale(${scale})`,
            transformOrigin: 'top left',
            backgroundColor,
            backgroundImage:
              backgroundImage && isSafeAssetSrc(backgroundImage) ? `url(${backgroundImage})` : undefined,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          }}
        >
          {[...elements]
            .sort((a, b) => (a.z_index || 0) - (b.z_index || 0))
            .map((el) => (
              <ElementView
                key={el.id}
                el={el}
                selected={el.id === selectedId}
                onPointerDownMove={(e) => beginDrag(e, el, 'move')}
                onPointerDownResize={(e, handle) => beginDrag(e, el, 'resize', handle)}
                onPointerDownRotate={(e) => beginDrag(e, el, 'rotate')}
              />
            ))}

          {guides.v && (
            <div
              className="absolute top-0 bottom-0 pointer-events-none"
              style={{ left: width / 2, width: 1, background: '#3b82f6' }}
              data-testid="snap-guide-v"
            />
          )}
          {guides.h && (
            <div
              className="absolute left-0 right-0 pointer-events-none"
              style={{ top: height / 2, height: 1, background: '#3b82f6' }}
              data-testid="snap-guide-h"
            />
          )}
        </div>
      </div>
    </div>
  )
}

function computeResize(
  start: DesignerElement,
  handle: ResizeHandle,
  dx: number,
  dy: number
): Partial<DesignerElement> {
  let { x, y, width, height } = start

  if (handle.includes('e')) width = Math.max(MIN_SIZE, start.width + dx)
  if (handle.includes('s')) height = Math.max(MIN_SIZE, start.height + dy)
  if (handle.includes('w')) {
    const newWidth = Math.max(MIN_SIZE, start.width - dx)
    x = start.x + (start.width - newWidth)
    width = newWidth
  }
  if (handle.includes('n')) {
    const newHeight = Math.max(MIN_SIZE, start.height - dy)
    y = start.y + (start.height - newHeight)
    height = newHeight
  }

  return {
    x: Math.round(x),
    y: Math.round(y),
    width: Math.round(width),
    height: Math.round(height),
  }
}

const HANDLE_POSITION: Record<ResizeHandle, React.CSSProperties> = {
  nw: { top: -5, left: -5, cursor: 'nwse-resize' },
  n: { top: -5, left: '50%', marginLeft: -5, cursor: 'ns-resize' },
  ne: { top: -5, right: -5, cursor: 'nesw-resize' },
  e: { top: '50%', right: -5, marginTop: -5, cursor: 'ew-resize' },
  se: { bottom: -5, right: -5, cursor: 'nwse-resize' },
  s: { bottom: -5, left: '50%', marginLeft: -5, cursor: 'ns-resize' },
  sw: { bottom: -5, left: -5, cursor: 'nesw-resize' },
  w: { top: '50%', left: -5, marginTop: -5, cursor: 'ew-resize' },
}

interface ElementViewProps {
  el: DesignerElement
  selected: boolean
  onPointerDownMove: (e: React.PointerEvent) => void
  onPointerDownResize: (e: React.PointerEvent, handle: ResizeHandle) => void
  onPointerDownRotate: (e: React.PointerEvent) => void
}

const ElementView: React.FC<ElementViewProps> = ({
  el,
  selected,
  onPointerDownMove,
  onPointerDownResize,
  onPointerDownRotate,
}) => {
  const style: React.CSSProperties = {
    position: 'absolute',
    left: el.x,
    top: el.y,
    width: el.width,
    height: el.height,
    zIndex: el.z_index,
    transform: el.rotation ? `rotate(${el.rotation}deg)` : undefined,
    boxSizing: 'border-box',
    cursor: 'move',
  }

  let inner: React.ReactNode = null

  if (['text', 'student_name', 'course_name', 'completion_date', 'certificate_id', 'instructor_name'].includes(el.type)) {
    const justify = { left: 'flex-start', center: 'center', right: 'flex-end' }[el.text_align || 'left']
    inner = (
      <div
        className="w-full h-full flex items-center overflow-hidden whitespace-pre-wrap break-words"
        style={{
          justifyContent: justify,
          fontFamily: fontFamilyCss(el.font_family),
          fontSize: el.font_size ?? 24,
          color: el.font_color || '#000000',
          fontWeight: (el.font_weight as React.CSSProperties['fontWeight']) || 'normal',
          textAlign: el.text_align || 'left',
          letterSpacing: el.letter_spacing ? `${el.letter_spacing}px` : undefined,
          backgroundColor: el.background_color || undefined,
          border: borderCss(el.border),
        }}
      >
        {resolveText(el)}
      </div>
    )
  } else if (el.type === 'image' || el.type === 'signature_image') {
    const src = el.image_url || el.src
    inner =
      src && isSafeAssetSrc(src) ? (
        <img src={src} alt="" className="w-full h-full object-contain" draggable={false} />
      ) : (
        <div className="w-full h-full flex items-center justify-center bg-neutral-100 text-neutral-400 text-xs border border-dashed border-neutral-300">
          {el.type === 'signature_image' ? 'Signature' : 'Image'}
        </div>
      )
  } else if (el.type === 'rect') {
    inner = (
      <div
        className="w-full h-full"
        style={{
          backgroundColor: el.background_color || el.fill || 'transparent',
          border: borderCss(el.border),
          borderRadius: el.border_radius ?? 0,
        }}
      />
    )
  } else if (el.type === 'line') {
    inner = (
      <div
        className="w-full"
        style={{
          borderTop: `${el.line_thickness ?? 2}px solid ${el.line_color || el.font_color || '#000000'}`,
        }}
      />
    )
  } else if (el.type === 'qr_code') {
    inner = (
      <div className="w-full h-full flex items-center justify-center bg-white border border-neutral-300 text-neutral-400 text-[10px] text-center p-1">
        QR (server-rendered on preview/issue)
      </div>
    )
  }

  return (
    <div
      style={style}
      data-testid={`designer-element-${el.id}`}
      data-element-type={el.type}
      onPointerDown={onPointerDownMove}
    >
      {inner}
      {selected && (
        <>
          <div className="absolute inset-0 border-2 border-primary-500 pointer-events-none" />
          {RESIZE_HANDLES.map((h) => (
            <div
              key={h}
              className="absolute w-2.5 h-2.5 bg-white border border-primary-500 rounded-sm"
              style={HANDLE_POSITION[h]}
              onPointerDown={(e) => onPointerDownResize(e, h)}
              data-testid={`resize-handle-${h}`}
            />
          ))}
          <div
            className="absolute flex items-center justify-center w-5 h-5 bg-white border border-primary-500 rounded-full text-primary-600"
            style={{ top: -28, left: '50%', marginLeft: -10, cursor: 'grab' }}
            onPointerDown={onPointerDownRotate}
            data-testid="rotate-handle"
          >
            <RotateCw size={12} />
          </div>
        </>
      )}
    </div>
  )
}

export default DesignerCanvas
export { SNAP_THRESHOLD_PX }
