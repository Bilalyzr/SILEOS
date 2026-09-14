/**
 * GameShell — shared chrome for all 5 engines (spec §6): title bar, SVG
 * timer ring, score counter, progress dots, pause overlay, and the results
 * screen (score, best score, replay, pure CSS/SVG confetti that respects
 * prefers-reduced-motion). All strings render as React text — instructor
 * config is untrusted; NO dangerouslySetInnerHTML anywhere in games code.
 */
import * as React from 'react'
import { Pause, Play, RotateCcw } from 'lucide-react'

export interface GameShellResult {
  score: number
  maxScore: number
  bestScore?: number | null
}

export interface GameShellProps {
  title: string
  accentClass?: string          // per-template Tailwind accent, e.g. 'text-violet-600'
  currentIndex: number          // 0-based progress dot position
  totalItems: number
  score: number
  maxScore: number
  timeRemainingS?: number | null // null = untimed
  totalTimeS?: number | null
  paused: boolean
  onPauseToggle: () => void
  result?: GameShellResult | null // non-null flips to the results screen
  onReplay: () => void
  children: React.ReactNode
}

export const GameShell: React.FC<GameShellProps> = ({
  title, accentClass = 'text-primary-600', currentIndex, totalItems, score,
  maxScore, timeRemainingS, totalTimeS, paused, onPauseToggle, result,
  onReplay, children,
}) => {
  const prefersReducedMotion = React.useMemo(
    () => typeof window !== 'undefined'
      && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
    []
  )
  const ringFraction =
    timeRemainingS != null && totalTimeS ? Math.max(0, timeRemainingS / totalTimeS) : null

  if (result) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 p-8 text-center">
        <style>{CONFETTI_KEYFRAMES}</style>
        {!prefersReducedMotion && <ConfettiBurst />}
        <h2 className="text-xl font-bold text-gray-900">{title}</h2>
        <p className="text-4xl font-extrabold tabular-nums">
          {result.score} <span className="text-gray-400 text-2xl">/ {result.maxScore}</span>
        </p>
        {result.bestScore != null && (
          <p className="text-sm text-gray-500">Best score: {result.bestScore}</p>
        )}
        <button type="button" onClick={onReplay}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium">
          <RotateCcw className="w-4 h-4" /> Play again
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between gap-3 px-4 py-2 border-b border-gray-100">
        <p className={`font-semibold truncate ${accentClass}`}>{title}</p>
        <div className="flex items-center gap-3 shrink-0">
          {ringFraction != null && (
            <svg viewBox="0 0 36 36" className={`w-8 h-8 -rotate-90 ${accentClass}`} aria-label="Time remaining">
              <circle cx="18" cy="18" r="15" fill="none" strokeWidth="3" className="stroke-gray-200" />
              <circle cx="18" cy="18" r="15" fill="none" strokeWidth="3"
                className="stroke-current" strokeDasharray={`${ringFraction * 94.2} 94.2`} />
            </svg>
          )}
          <span className="text-sm font-semibold tabular-nums">{score}/{maxScore}</span>
          <button type="button" onClick={onPauseToggle} aria-label={paused ? 'Resume' : 'Pause'}
            className="text-gray-500 hover:text-gray-800">
            {paused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
          </button>
        </div>
      </div>
      <div className="flex justify-center gap-1.5 py-2" aria-label="Progress">
        {Array.from({ length: totalItems }).map((_, i) => (
          <span key={i} className={`w-2 h-2 rounded-full ${i <= currentIndex ? 'bg-primary-500' : 'bg-gray-200'}`} />
        ))}
      </div>
      <div className="relative flex-1 min-h-0">
        {paused && (
          <div className="absolute inset-0 z-10 bg-white/90 flex items-center justify-center">
            <p className="text-gray-600 font-medium">Paused</p>
          </div>
        )}
        {children}
      </div>
    </div>
  )
}

const CONFETTI_KEYFRAMES = `
@keyframes confetti-fall {
  0% { transform: translateY(-10vh) rotate(0deg); opacity: 1; }
  100% { transform: translateY(60vh) rotate(360deg); opacity: 0; }
}
`

/** Pure CSS/SVG confetti — ~20 absolutely-positioned falling shapes, no images. */
const ConfettiBurst: React.FC = () => (
  <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
    {Array.from({ length: 20 }).map((_, i) => (
      <span key={i}
        className="absolute w-2 h-3 rounded-sm"
        style={{
          left: `${(i * 5) % 100}%`,
          backgroundColor: ['#7c3aed', '#f59e0b', '#10b981', '#ef4444'][i % 4],
          animation: 'confetti-fall 1.8s ease-in forwards',
          animationDelay: `${(i % 7) * 0.12}s`,
        }} />
    ))}
  </div>
)

export default GameShell
