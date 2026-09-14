/** DragSort — drag items into category buckets (spec §1 row 3). Pure props;
 * scoring via engines/scoring.ts only. All config strings render as React
 * TEXT. Uses @dnd-kit/core's DndContext + useDraggable/useDroppable for
 * touch-capable drag (PointerSensor with an activation distance, mirroring
 * edit-course.tsx's lectureDragSensors). */
import * as React from 'react'
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  useDraggable,
  useDroppable,
  type DragEndEvent,
} from '@dnd-kit/core'
import type { DragSortConfig } from '@/api/games'
import { GameShell } from '../GameShell'
import { capScore, deriveMaxScore, scoreDragSortItem } from './scoring'
import type { EngineProps } from './QuizRush'

/**
 * dnd-kit's default KeyboardSensor coordinate getter is built for sortable
 * lists (relative reordering) — drag_sort instead needs to move a draggable
 * onto one of several fixed drop zones. There is no built-in coordinate
 * getter for "free" drop-zone targeting, so keyboard support here is
 * implemented as an explicit Enter/Space-to-cycle activation on each
 * draggable item's category buttons instead of arrow-key dragging (see
 * onKeyboardPlace below) — dnd-kit's KeyboardSensor is still registered so a
 * future coordinate getter can be swapped in, and so keyboard focus still
 * participates in the same DndContext for consistency.
 */
function DraggableItem({
  id, text, onKeyboardPlace, categories,
}: {
  id: string
  text: string
  onKeyboardPlace: (categoryIndex: number) => void
  categories: { name: string }[]
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id })
  const style: React.CSSProperties = {
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    opacity: isDragging ? 0.5 : 1,
    touchAction: 'none',
  }
  const [menuOpen, setMenuOpen] = React.useState(false)
  return (
    <div className="relative inline-block">
      <button
        ref={setNodeRef}
        type="button"
        {...attributes}
        {...listeners}
        tabIndex={0}
        role="button"
        aria-label={`${text}. Press Enter to choose a category.`}
        style={style}
        onKeyDown={(e) => {
          // Keyboard-only path: Enter/Space opens a category picker menu
          // (arrow-key + Enter selects) instead of relying on pointer drag.
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setMenuOpen((v) => !v)
          }
        }}
        className="px-4 py-3 rounded-xl border-2 border-gray-200 bg-white text-sm cursor-grab active:cursor-grabbing"
      >
        {text}
      </button>
      {menuOpen && (
        <div role="menu" aria-label={`Place "${text}" into category`}
          className="absolute z-20 mt-1 min-w-max rounded-lg border border-gray-200 bg-white shadow-lg py-1">
          {categories.map((category, ci) => (
            <button
              key={ci}
              type="button"
              role="menuitem"
              onClick={() => { setMenuOpen(false); onKeyboardPlace(ci) }}
              className="block w-full px-3 py-1.5 text-left text-sm hover:bg-amber-50"
            >
              {category.name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function DropZone({ id, name, children }: { id: string; name: string; children: React.ReactNode }) {
  const { setNodeRef, isOver } = useDroppable({ id })
  return (
    <div
      ref={setNodeRef}
      className={`min-h-24 rounded-xl border-2 border-dashed p-3 space-y-2 transition ${
        isOver ? 'border-amber-400 bg-amber-50' : 'border-gray-200'
      }`}
    >
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{name}</p>
      {children}
    </div>
  )
}

export const DragSort: React.FC<EngineProps<DragSortConfig>> = ({
  config, onComplete, title = '', bestScore = null, onReplay = () => window.location.reload(),
}) => {
  const maxScore = deriveMaxScore(config.items.length)
  const timeLimit = config.settings.time_limit_s

  const [placed, setPlaced] = React.useState<Record<number, number>>({}) // itemIndex -> categoryIndex
  const [wrongAttemptsByItem, setWrongAttemptsByItem] = React.useState<Record<number, number>>({})
  const [bounce, setBounce] = React.useState<number | null>(null)
  const [score, setScore] = React.useState(0)
  const [timeRemaining, setTimeRemaining] = React.useState<number | null>(
    timeLimit > 0 ? timeLimit : null
  )
  const [paused, setPaused] = React.useState(false)
  const [done, setDone] = React.useState(false)
  const startedAtRef = React.useRef(Date.now())
  const completedRef = React.useRef(false)
  // Mirrors `score` so the countdown interval (mounted once, deps exclude
  // score to avoid re-ticking the timer) always reads the LATEST banked
  // score on expiry instead of the value captured when the effect's
  // closure was created.
  const scoreRef = React.useRef(0)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    // Keyboard-only support (a11y): registered so keyboard focus
    // participates in the same DndContext; actual keyboard placement is
    // driven by DraggableItem's Enter/Space category-picker menu (see its
    // header comment) rather than arrow-key coordinate dragging, since
    // drag_sort's targets are fixed zones, not a reorderable list.
    useSensor(KeyboardSensor)
  )

  const finish = React.useCallback((finalScore: number) => {
    if (completedRef.current) return
    completedRef.current = true
    setDone(true)
    onComplete({
      score: capScore(finalScore, maxScore),
      maxScore,
      durationS: Math.round((Date.now() - startedAtRef.current) / 1000),
    })
  }, [maxScore, onComplete])

  React.useEffect(() => {
    if (paused || done || timeRemaining === null) return
    const t = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev === null) return prev
        if (prev <= 1) {
          finish(scoreRef.current)
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paused, done, timeRemaining === null, finish])

  // Shared placement logic used by both pointer drag-end and the keyboard
  // category-picker menu, so both input paths score/finish identically.
  const attemptPlace = React.useCallback((itemIndex: number, categoryIndex: number) => {
    if (paused || done) return
    if (placed[itemIndex] !== undefined) return

    const item = config.items[itemIndex]
    if (categoryIndex === item.category_index) {
      const wrongAttempts = wrongAttemptsByItem[itemIndex] ?? 0
      const points = scoreDragSortItem(wrongAttempts)
      setScore((prev) => {
        const next = capScore(prev + points, maxScore)
        scoreRef.current = next
        setPlaced((prevPlaced) => {
          const nextPlaced = { ...prevPlaced, [itemIndex]: categoryIndex }
          if (Object.keys(nextPlaced).length >= config.items.length) {
            finish(next)
          }
          return nextPlaced
        })
        return next
      })
    } else {
      setWrongAttemptsByItem((prev) => ({ ...prev, [itemIndex]: (prev[itemIndex] ?? 0) + 1 }))
      setBounce(itemIndex)
      window.setTimeout(() => setBounce(null), 400)
    }
  }, [paused, done, placed, config.items, wrongAttemptsByItem, maxScore, finish])

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over) return
    const itemIndex = Number(String(active.id).replace('item-', ''))
    const categoryIndex = Number(String(over.id).replace('zone-', ''))
    attemptPlace(itemIndex, categoryIndex)
  }

  const unplacedItems = config.items
    .map((item, i) => ({ item, i }))
    .filter(({ i }) => placed[i] === undefined)

  return (
    <GameShell
      title={title}
      accentClass="text-amber-600"
      currentIndex={Object.keys(placed).length}
      totalItems={config.items.length}
      score={score}
      maxScore={maxScore}
      timeRemainingS={timeRemaining}
      totalTimeS={timeLimit > 0 ? timeLimit : null}
      paused={paused}
      onPauseToggle={() => setPaused((p) => !p)}
      result={done ? { score, maxScore, bestScore } : null}
      onReplay={onReplay}
    >
      <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
        <div className="p-4 space-y-4">
          <div className="flex flex-wrap gap-2">
            {unplacedItems.map(({ item, i }) => (
              <div key={i} className={bounce === i ? 'animate-bounce' : ''}>
                <DraggableItem
                  id={`item-${i}`}
                  text={item.text}
                  categories={config.categories}
                  onKeyboardPlace={(categoryIndex) => attemptPlace(i, categoryIndex)}
                />
              </div>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {config.categories.map((category, ci) => (
              <DropZone key={ci} id={`zone-${ci}`} name={category.name}>
                <div className="flex flex-wrap gap-2">
                  {config.items
                    .map((item, ii) => ({ item, ii }))
                    .filter(({ ii }) => placed[ii] === ci)
                    .map(({ item, ii }) => (
                      <span key={ii} className="px-3 py-1.5 rounded-lg bg-amber-100 text-amber-800 text-sm">
                        {item.text}
                      </span>
                    ))}
                </div>
              </DropZone>
            ))}
          </div>
        </div>
      </DndContext>
    </GameShell>
  )
}

export default DragSort
