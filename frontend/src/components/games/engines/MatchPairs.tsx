/** MatchPairs — flip-card matching (spec §1 row 2). Pure props; scoring via
 * engines/scoring.ts only. All config strings render as React TEXT. */
import * as React from 'react'
import type { MatchPairsConfig } from '@/api/games'
import { GameShell } from '../GameShell'
import { capScore, deriveMaxScore, scoreMatchPair } from './scoring'
import type { EngineProps } from './QuizRush'

interface Card {
  key: string
  pairIndex: number
  side: 'left' | 'right'
  text: string
}

function shuffled<T>(arr: T[]): T[] {
  const copy = [...arr]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

export const MatchPairs: React.FC<EngineProps<MatchPairsConfig>> = ({
  config, onComplete, title = '', bestScore = null, onReplay = () => window.location.reload(),
}) => {
  const maxScore = deriveMaxScore(config.items.length)
  const timeLimit = config.settings.time_limit_s

  const cards = React.useMemo<Card[]>(() => {
    const built: Card[] = []
    config.items.forEach((item, pairIndex) => {
      built.push({ key: `${pairIndex}-left`, pairIndex, side: 'left', text: item.left })
      built.push({ key: `${pairIndex}-right`, pairIndex, side: 'right', text: item.right })
    })
    return shuffled(built)
  }, [config])

  const [flipped, setFlipped] = React.useState<string[]>([])
  const [matched, setMatched] = React.useState<Set<number>>(new Set())
  const [missesByPair, setMissesByPair] = React.useState<Record<number, number>>({})
  const [score, setScore] = React.useState(0)
  const [timeRemaining, setTimeRemaining] = React.useState<number | null>(
    timeLimit > 0 ? timeLimit : null
  )
  const [paused, setPaused] = React.useState(false)
  const [done, setDone] = React.useState(false)
  const [busy, setBusy] = React.useState(false)
  const startedAtRef = React.useRef(Date.now())
  const completedRef = React.useRef(false)
  // Mirrors `score` so the countdown interval (mounted once, deps exclude
  // score to avoid re-ticking the timer) always reads the LATEST banked
  // score on expiry instead of the value captured when the effect's
  // closure was created.
  const scoreRef = React.useRef(0)

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

  const flipCard = (card: Card) => {
    if (busy || paused || done) return
    if (matched.has(card.pairIndex)) return
    if (flipped.includes(card.key)) return

    if (flipped.length === 0) {
      setFlipped([card.key])
      return
    }

    const firstKey = flipped[0]
    const firstCard = cards.find((c) => c.key === firstKey)
    if (!firstCard) return

    setFlipped([firstKey, card.key])
    setBusy(true)

    const isMatch = firstCard.pairIndex === card.pairIndex && firstCard.side !== card.side

    window.setTimeout(() => {
      if (isMatch) {
        const misses = missesByPair[card.pairIndex] ?? 0
        const points = scoreMatchPair(misses)
        setScore((prev) => {
          const next = capScore(prev + points, maxScore)
          scoreRef.current = next
          const nextMatched = new Set(matched)
          nextMatched.add(card.pairIndex)
          setMatched(nextMatched)
          if (nextMatched.size >= config.items.length) {
            finish(next)
          }
          return next
        })
      } else {
        setMissesByPair((prev) => ({
          ...prev,
          [firstCard.pairIndex]: (prev[firstCard.pairIndex] ?? 0) + 1,
          [card.pairIndex]: (prev[card.pairIndex] ?? 0) + 1,
        }))
      }
      setFlipped([])
      setBusy(false)
    }, 700)
  }

  return (
    <GameShell
      title={title}
      accentClass="text-emerald-600"
      currentIndex={matched.size}
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
      <div className="p-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {cards.map((card) => {
            const isFlipped = flipped.includes(card.key) || matched.has(card.pairIndex)
            return (
              <button
                key={card.key}
                type="button"
                onClick={() => flipCard(card)}
                disabled={matched.has(card.pairIndex)}
                className={`min-h-16 px-3 py-3 rounded-xl border-2 text-sm text-center transition ${
                  matched.has(card.pairIndex)
                    ? 'border-emerald-400 bg-emerald-50 text-emerald-700'
                    : isFlipped
                      ? 'border-emerald-300 bg-white'
                      : 'border-gray-200 bg-gray-50 hover:border-emerald-300'
                }`}
              >
                {isFlipped ? card.text : '?'}
              </button>
            )
          })}
        </div>
      </div>
    </GameShell>
  )
}

export default MatchPairs
