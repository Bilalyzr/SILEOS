/**
 * ScorableItemsPanel — student side of "the quiz as a container" (v2.0 §5).
 * Lists the quiz's scorable items and plays each inline with the existing
 * players (GamePlayer / H5PLesson / VirtualLabPlayer); every player already
 * records its own advisory result, which the cumulative grade reads back.
 * Practice-only items are labelled so learners know they are not graded.
 */
import * as React from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { ScorableItem } from '@/api/scorable'
import { GamePlayer } from '@/components/games/GamePlayer'
import { H5PLesson } from '@/components/h5p/H5PLesson'
import { VirtualLabPlayer } from '@/components/labs/VirtualLabPlayer'
import { ThreeDTaskPlayer } from '@/components/three-d/tasks/ThreeDTaskPlayer'

const KIND_ICON: Record<string, string> = { h5p: '🧩', game: '🎮', lab: '🔬', three_d_task: '🧊' }

function ItemPlayer({ item }: { item: ScorableItem }) {
  if (item.kind === 'game') return <GamePlayer gameId={Number(item.id)} previewOnly={false} className="min-h-[50vh]" />
  if (item.kind === 'h5p' && item.public_id) return <H5PLesson contentId={item.public_id} title={item.title} />
  if (item.kind === 'lab') return <VirtualLabPlayer slug={String(item.id)} title={item.title} height={480} />
  if (item.kind === 'three_d_task') return <ThreeDTaskPlayer taskId={Number(item.id)} />
  return <p className="text-sm text-neutral-500">This item type is not playable in this app version.</p>
}

export const ScorableItemsPanel: React.FC<{ items: ScorableItem[] }> = ({ items }) => {
  const [open, setOpen] = React.useState<string | null>(null)
  if (!items || items.length === 0) return null
  const graded = items.filter((i) => !i.practice_only).length
  return (
    <div className="bg-white rounded-xl shadow-soft p-6 mb-6">
      <h2 className="font-semibold text-neutral-900">Scored items in this quiz</h2>
      <p className="text-xs text-neutral-500 mb-3">
        {graded} graded · {items.length - graded} practice. Play each one; your best score counts.
      </p>
      <ul className="space-y-2">
        {items.map((it) => {
          const k = `${it.kind}:${it.id}`
          const isOpen = open === k
          return (
            <li key={k} className="border border-neutral-200 rounded-lg">
              <button
                type="button"
                onClick={() => setOpen(isOpen ? null : k)}
                aria-expanded={isOpen}
                className="w-full flex items-center gap-2 px-3 py-2 text-left text-sm"
              >
                <span>{KIND_ICON[it.kind]}</span>
                <span className="font-medium text-neutral-900 flex-1">{it.title}</span>
                <span className="text-xs text-neutral-500">{it.max_score} pts</span>
                {it.practice_only ? (
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-600">practice</span>
                ) : (
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">graded · weight {it.weight}</span>
                )}
                {it.attempts_allowed > 0 && <span className="text-[11px] text-neutral-400">{it.attempts_allowed} attempts</span>}
                {isOpen ? <ChevronUp className="w-4 h-4 text-neutral-400" /> : <ChevronDown className="w-4 h-4 text-neutral-400" />}
              </button>
              {isOpen && (
                <div className="border-t border-neutral-100 p-3 bg-neutral-50">
                  <ItemPlayer item={it} />
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export default ScorableItemsPanel
