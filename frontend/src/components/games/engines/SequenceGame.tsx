/** SequenceGame — drag items into the correct order (spec §1 row 5). Pure
 * props; scoring via engines/scoring.ts only. All config strings render as
 * React TEXT. Uses @dnd-kit/sortable's vertical list strategy (mirroring
 * edit-course.tsx's SortableSection/SortableLecture pattern). */
import * as React from 'react'
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical } from 'lucide-react'
import type { SequenceConfig } from '@/api/games'
import { GameShell } from '../GameShell'
import { capScore, deriveMaxScore, scoreSequenceSubmit } from './scoring'
import type { EngineProps } from './QuizRush'

interface SeqItem {
  id: string
  text: string
  correctIndex: number
}

function shuffled<T>(arr: T[]): T[] {
  const copy = [...arr]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

function isSameOrder(order: SeqItem[]): boolean {
  return order.every((item, i) => item.correctIndex === i)
}

function shuffleOrder(items: SeqItem[]): SeqItem[] {
  if (items.length <= 1) return [...items]
  let attempt = shuffled(items)
  // Re-shuffle if it happens to equal the correct order.
  let guard = 0
  while (isSameOrder(attempt) && guard < 10) {
    attempt = shuffled(items)
    guard += 1
  }
  return attempt
}

function SortableRow({ id, text, wrong }: { id: string; text: string; wrong: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }
  return (
    <div
      ref={setNodeRef}
      data-testid={`seq-row-${id}`}
      style={style}
      className={`flex items-center gap-2 px-3 py-2.5 rounded-xl border-2 bg-white ${
        wrong ? 'border-red-300 bg-red-50' : 'border-gray-200'
      }`}
    >
      <button
        type="button"
        {...attributes}
        {...listeners}
        aria-label="Drag to reorder"
        className="text-gray-400 hover:text-gray-600 cursor-grab active:cursor-grabbing"
        style={{ touchAction: 'none' }}
      >
        <GripVertical className="w-4 h-4" />
      </button>
      <span className="text-sm text-gray-900">{text}</span>
    </div>
  )
}

export const SequenceGame: React.FC<EngineProps<SequenceConfig>> = ({
  config, onComplete, title = '', bestScore = null, onReplay = () => window.location.reload(),
}) => {
  const maxScore = deriveMaxScore(config.items.length)
  const timeLimit = config.settings.time_limit_s

  const baseItems = React.useMemo<SeqItem[]>(
    () => config.items.map((item, i) => ({ id: `seq-${i}`, text: item.text, correctIndex: i })),
    [config]
  )

  const [order, setOrder] = React.useState<SeqItem[]>(() => shuffleOrder(baseItems))
  const [wrongIds, setWrongIds] = React.useState<Set<string>>(new Set())
  const [retryUsed, setRetryUsed] = React.useState(false)
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
  // closure was created. Applied for symmetry with MatchPairs/DragSort —
  // currently benign here since `score` is only ever set inside finish()
  // itself, but keeps the same safe pattern if that ever changes.
  const scoreRef = React.useRef(0)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    // Keyboard-only support (a11y): a focused drag handle can be lifted,
    // moved, and dropped with Space + arrow keys via dnd-kit's built-in
    // sortable keyboard coordinate getter.
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const finish = React.useCallback((finalScore: number) => {
    if (completedRef.current) return
    completedRef.current = true
    const capped = capScore(finalScore, maxScore)
    scoreRef.current = capped
    setScore(capped)
    setDone(true)
    onComplete({
      score: capped,
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

  const handleDragEnd = (event: DragEndEvent) => {
    if (paused || done) return
    const { active, over } = event
    if (!over || active.id === over.id) return
    setOrder((prev) => {
      const oldIndex = prev.findIndex((i) => i.id === active.id)
      const newIndex = prev.findIndex((i) => i.id === over.id)
      return arrayMove(prev, oldIndex, newIndex)
    })
    setWrongIds(new Set())
  }

  const submit = () => {
    if (paused || done) return
    const correctCount = order.filter((item, i) => item.correctIndex === i).length
    const allCorrect = correctCount === order.length

    if (allCorrect) {
      const points = scoreSequenceSubmit(correctCount, retryUsed)
      finish(capScore(score + points, maxScore))
      return
    }

    if (!retryUsed) {
      // First submit with wrong positions: highlight wrong items, allow ONE retry.
      const wrong = new Set(order.filter((item, i) => item.correctIndex !== i).map((i) => i.id))
      setWrongIds(wrong)
      setRetryUsed(true)
      return
    }

    // Second submit is final regardless of correctness.
    const points = scoreSequenceSubmit(correctCount, true)
    finish(capScore(score + points, maxScore))
  }

  return (
    <GameShell
      title={title}
      accentClass="text-rose-600"
      currentIndex={retryUsed ? 1 : 0}
      totalItems={2}
      score={score}
      maxScore={maxScore}
      timeRemainingS={timeRemaining}
      totalTimeS={timeLimit > 0 ? timeLimit : null}
      paused={paused}
      onPauseToggle={() => setPaused((p) => !p)}
      result={done ? { score, maxScore, bestScore } : null}
      onReplay={onReplay}
    >
      <div className="p-4 space-y-4">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={order.map((i) => i.id)} strategy={verticalListSortingStrategy}>
            <div className="space-y-2">
              {order.map((item) => (
                <SortableRow key={item.id} id={item.id} text={item.text} wrong={wrongIds.has(item.id)} />
              ))}
            </div>
          </SortableContext>
        </DndContext>
        {wrongIds.size > 0 && (
          <p className="text-sm text-red-600">Some items are out of order — you get one more try.</p>
        )}
        <button
          type="button"
          onClick={submit}
          className="px-4 py-2 rounded-lg bg-rose-600 text-white text-sm font-medium"
        >
          Submit
        </button>
      </div>
    </GameShell>
  )
}

export default SequenceGame
