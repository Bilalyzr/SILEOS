import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import type { LessonCodingBlock } from '@/api/coding'
import { CodingWorkspace } from './CodingWorkspace'
import { dueBlock, formatPosition } from './practiceTriggers'

interface LessonPracticeBlocksProps {
  blocks: LessonCodingBlock[]
  currentTime: number
  isPlaying: boolean
  onPause: () => void
  onResume: () => void
}

/**
 * Practice blocks for a lesson. When playback reaches a timed block, the video
 * pauses and the workspace opens. "Continue lesson" closes it and resumes.
 * Blocks with no timestamp are listed under the video for practice at any time.
 */
export function LessonPracticeBlocks({ blocks, currentTime, isPlaying, onPause, onResume }: LessonPracticeBlocksProps) {
  const [finished, setFinished] = useState<Set<number>>(() => new Set())
  const [active, setActive] = useState<LessonCodingBlock | null>(null)
  const [resumeAfter, setResumeAfter] = useState(false)

  // Only a block that playback reaches while playing opens by itself.
  useEffect(() => {
    if (active || !isPlaying) return
    const due = dueBlock(blocks, currentTime, finished)
    if (!due) return
    setActive(due)
    setResumeAfter(true)
    onPause()
  }, [active, blocks, currentTime, finished, isPlaying, onPause])

  const open = (block: LessonCodingBlock) => {
    if (isPlaying) onPause()
    setResumeAfter(false)
    setActive(block)
  }

  // Closing a timed block, by any route, marks it done for this view. Otherwise
  // playback would reach the same timestamp again and reopen it straight away.
  const close = () => {
    if (active && active.position_seconds !== null) setFinished((prev) => new Set(prev).add(active.id))
    setActive(null)
    if (resumeAfter) onResume()
    setResumeAfter(false)
  }

  if (blocks.length === 0) return null

  return <section aria-labelledby="practice-heading" className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
    <h2 id="practice-heading" className="text-base font-semibold text-slate-100">Practice in this lesson</h2>
    <ul className="mt-3 space-y-2">
      {blocks.map((block) => <li key={block.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-black/20 px-4 py-3">
        <div>
          <p className="text-sm font-medium text-slate-100">{block.title}</p>
          <p className="text-xs text-slate-400">
            {block.position_seconds !== null ? `Opens at ${formatPosition(block.position_seconds)}` : 'Available any time'}
            {finished.has(block.id) && ' · Done in this session'}
          </p>
        </div>
        <button type="button" onClick={() => open(block)} className="rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-violet-500">
          Open practice
        </button>
      </li>)}
    </ul>

    {active && createPortal(
      <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/70 p-3 backdrop-blur-sm sm:p-6">
        <div role="dialog" aria-modal="true" aria-labelledby="practice-dialog-title" tabIndex={-1} autoFocus onKeyDown={(event) => { if (event.key === 'Escape') close() }} className="flex max-h-full w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#080b12] shadow-2xl">
          <header className="flex items-center justify-between gap-3 border-b border-white/10 px-5 py-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-violet-400">Practice</p>
              <h2 id="practice-dialog-title" className="font-semibold text-slate-100">{active.title}</h2>
            </div>
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => close()} className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500">
                {resumeAfter ? 'Continue lesson' : 'Done'}
              </button>
              <button type="button" aria-label="Close practice" onClick={() => close()} className="rounded-lg border border-white/10 p-2 text-slate-300 hover:bg-white/10">
                <X className="h-4 w-4" />
              </button>
            </div>
          </header>
          {active.instructions && <p className="border-b border-white/10 bg-violet-500/10 px-5 py-3 text-sm text-violet-100">{active.instructions}</p>}
          <div className="min-h-0 flex-1 overflow-y-auto p-5">
            <CodingWorkspace key={active.challenge_slug} slug={active.challenge_slug} embedded />
          </div>
        </div>
      </div>,
      document.body,
    )}
  </section>
}
