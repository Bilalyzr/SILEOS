/**
 * Identify Lab engine — "find the named structure" on a labelled diagram.
 * The diagram is a built-in SVG (cell, skeleton) or an https image; hotspots
 * are percent coordinates on that box. Each prompt names ONE structure; the
 * student clicks a target dot. Parameter-based grading: hotspot id equality,
 * 10 points per structure, one attempt each (a wrong click reveals the
 * answer and moves on). Keyboard operable: every target is a real button.
 * All strings come from config and render as React text only.
 */
import * as React from 'react'
import type { Hotspot, IdentifyLabConfig } from '@/api/labs'
import { CellDiagram } from '../diagrams/CellDiagram'
import { SkeletonDiagram } from '../diagrams/SkeletonDiagram'

interface Props {
  config: IdentifyLabConfig
  onFinish: (score: number, maxScore: number) => void
  finished?: boolean
}

function shuffle<T>(arr: T[]): T[] {
  const a = arr.slice()
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

function Diagram({ diagram }: { diagram: string }) {
  if (diagram === 'cell') return <CellDiagram className="w-full h-full" />
  if (diagram === 'skeleton') return <SkeletonDiagram className="w-full h-full" />
  return <img src={diagram} alt="Lab diagram" className="w-full h-full object-contain select-none" draggable={false} />
}

export function IdentifyLab({ config, onFinish, finished = false }: Props) {
  const hotspots = config.hotspots
  const maxScore = hotspots.length * 10
  const [order] = React.useState<Hotspot[]>(() => shuffle(hotspots))
  const [index, setIndex] = React.useState(0)
  const [results, setResults] = React.useState<Record<string, 'correct' | 'wrong'>>({})
  const [lastMessage, setLastMessage] = React.useState<string>('')
  const [revealId, setRevealId] = React.useState<string | null>(null)

  const done = index >= order.length
  const target = done ? null : order[index]
  const score = Object.values(results).filter((r) => r === 'correct').length * 10

  const pick = (h: Hotspot) => {
    if (!target || finished || done) return
    const correct = h.id === target.id
    setResults((prev) => ({ ...prev, [target.id]: correct ? 'correct' : 'wrong' }))
    setRevealId(target.id)
    setLastMessage(
      correct
        ? `Correct — ${target.label}. ${target.description || ''}`.trim()
        : `Not quite. You clicked ${h.label}; the ${target.label} is highlighted now. ${target.description || ''}`.trim(),
    )
    setIndex(index + 1)
  }

  const answeredIds = new Set(Object.keys(results))

  return (
    <div className="space-y-4">
      {config.intro && <p className="text-sm text-gray-600">{config.intro}</p>}

      <div className="flex flex-wrap items-center gap-3">
        {!done ? (
          <p className="text-base text-gray-900" role="status" aria-live="polite">
            Find: <strong className="text-emerald-700">{target?.label}</strong>
            <span className="text-xs text-gray-500 ml-2">({index + 1} of {order.length})</span>
          </p>
        ) : (
          <p className="text-base text-gray-900" role="status">All structures answered.</p>
        )}
        <span className="ml-auto text-sm text-gray-600">Score <strong>{score}</strong> / {maxScore}</span>
      </div>

      <div className="relative w-full mx-auto max-w-xl rounded-xl border border-gray-200 bg-white overflow-hidden" style={{ aspectRatio: '1 / 1' }}>
        <div className="absolute inset-0 p-2">
          <Diagram diagram={config.diagram} />
        </div>
        {hotspots.map((h, i) => {
          const state = results[h.id]
          const isReveal = revealId === h.id
          return (
            <button
              key={h.id}
              type="button"
              onClick={() => pick(h)}
              disabled={finished || done}
              aria-label={`Structure ${i + 1}`}
              title={answeredIds.has(h.id) ? h.label : undefined}
              className={`absolute -translate-x-1/2 -translate-y-1/2 w-5 h-5 rounded-full border-2 transition focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-emerald-500 ${
                state === 'correct'
                  ? 'bg-emerald-500 border-emerald-700'
                  : state === 'wrong'
                    ? 'bg-red-400 border-red-600'
                    : 'bg-white/80 border-gray-700 hover:bg-emerald-100 motion-safe:animate-pulse'
              } ${isReveal ? 'ring-4 ring-amber-400' : ''}`}
              style={{ left: `${h.x}%`, top: `${h.y}%` }}
            />
          )
        })}
      </div>

      {lastMessage && (
        <p className="text-sm text-gray-700" role="status">{lastMessage}</p>
      )}

      {done && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
          <p className="text-xs font-semibold text-gray-700 mb-1">Review</p>
          <ul className="text-xs text-gray-600 grid sm:grid-cols-2 gap-x-4 gap-y-0.5">
            {hotspots.map((h) => (
              <li key={h.id}>
                <span className={results[h.id] === 'correct' ? 'text-emerald-700' : 'text-red-600'}>
                  {results[h.id] === 'correct' ? '✓' : '✗'}
                </span>{' '}
                {h.label}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!finished && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-500">{answeredIds.size} of {hotspots.length} answered</p>
          <button
            type="button"
            onClick={() => onFinish(score, maxScore)}
            disabled={!done}
            className="px-4 py-2 text-sm font-semibold rounded-lg bg-gray-900 text-white hover:bg-black disabled:opacity-40"
          >
            Finish lab
          </button>
        </div>
      )}
    </div>
  )
}

export default IdentifyLab
