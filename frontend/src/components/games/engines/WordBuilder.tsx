/** WordBuilder — tap-to-place letter tiles to spell the answer (spec §1 row
 * 4). Pure props; scoring via engines/scoring.ts only. All config strings
 * render as React TEXT. */
import * as React from 'react'
import { Lightbulb } from 'lucide-react'
import type { WordBuilderConfig } from '@/api/games'
import { GameShell } from '../GameShell'
import { capScore, deriveMaxScore, scoreWordBuilderItem } from './scoring'
import type { EngineProps } from './QuizRush'

function shuffledTiles(answer: string): { char: string; key: number }[] {
  const letters = answer.split('').filter((c) => c !== ' ')
  const tiles = letters.map((char, i) => ({ char, key: i }))
  for (let i = tiles.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[tiles[i], tiles[j]] = [tiles[j], tiles[i]]
  }
  return tiles
}

export const WordBuilder: React.FC<EngineProps<WordBuilderConfig>> = ({
  config, onComplete, title = '', bestScore = null, onReplay = () => window.location.reload(),
}) => {
  const maxScore = deriveMaxScore(config.items.length)

  const [index, setIndex] = React.useState(0)
  const [score, setScore] = React.useState(0)
  const [hintsUsed, setHintsUsed] = React.useState(0)
  const [placedKeys, setPlacedKeys] = React.useState<number[]>([])
  const [paused, setPaused] = React.useState(false)
  const [done, setDone] = React.useState(false)
  const startedAtRef = React.useRef(Date.now())
  const completedRef = React.useRef(false)

  const item = config.items[Math.min(index, config.items.length - 1)]
  const answer = item.answer
  const answerLetters = React.useMemo(() => answer.split('').filter((c) => c !== ' '), [answer])
  const tiles = React.useMemo(() => shuffledTiles(answer), [answer])

  // Reset per-item state when moving to a new item.
  React.useEffect(() => {
    setHintsUsed(0)
    setPlacedKeys([])
  }, [index])

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

  const placedChars = placedKeys.map((k) => tiles.find((t) => t.key === k)?.char ?? '')
  const solved = placedChars.length === answerLetters.length
    && placedChars.every((c, i) => c === answerLetters[i])

  const placeLetter = (key: number) => {
    if (paused || done || solved) return
    if (placedKeys.includes(key)) return
    setPlacedKeys((prev) => [...prev, key])
  }

  const backspace = () => {
    if (paused || done) return
    setPlacedKeys((prev) => prev.slice(0, -1))
  }

  const useHint = () => {
    if (paused || done || solved) return
    if (hintsUsed >= config.settings.hints_allowed) return
    // Reveal the next correct letter by placing the first unused tile whose
    // char matches the next required letter.
    const nextPos = placedChars.length
    const nextChar = answerLetters[nextPos]
    if (nextChar === undefined) return
    const candidate = tiles.find((t) => t.char === nextChar && !placedKeys.includes(t.key))
    if (!candidate) return
    setPlacedKeys((prev) => [...prev, candidate.key])
    setHintsUsed((prev) => prev + 1)
  }

  React.useEffect(() => {
    if (!solved || done) return
    const points = scoreWordBuilderItem(hintsUsed)
    const nextScore = capScore(score + points, maxScore)
    setScore(nextScore)
    const t = window.setTimeout(() => {
      if (index + 1 >= config.items.length) {
        finish(nextScore)
      } else {
        setIndex((i) => i + 1)
      }
    }, 600)
    return () => window.clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [solved])

  const availableTiles = tiles.filter((t) => !placedKeys.includes(t.key))

  return (
    <GameShell
      title={title}
      accentClass="text-sky-600"
      currentIndex={index}
      totalItems={config.items.length}
      score={score}
      maxScore={maxScore}
      timeRemainingS={null}
      totalTimeS={null}
      paused={paused}
      onPauseToggle={() => setPaused((p) => !p)}
      result={done ? { score, maxScore, bestScore } : null}
      onReplay={onReplay}
    >
      <div className="p-4 space-y-4">
        <p className="text-lg font-medium text-gray-900">{item.clue}</p>

        <div className="flex flex-wrap gap-1.5 min-h-12">
          {answer.split('').map((original, i) => {
            if (original === ' ') return <span key={i} className="w-4" />
            const letterPos = answer.slice(0, i).split('').filter((c) => c !== ' ').length
            const char = placedChars[letterPos]
            return (
              <span
                key={i}
                className="w-9 h-9 flex items-center justify-center rounded-lg border-2 border-gray-300 bg-gray-50 text-sm font-semibold uppercase"
              >
                {char ?? ''}
              </span>
            )
          })}
        </div>

        <div className="flex flex-wrap gap-2">
          {availableTiles.map((tile) => (
            <button
              key={tile.key}
              type="button"
              onClick={() => placeLetter(tile.key)}
              className="w-9 h-9 rounded-lg border-2 border-sky-200 bg-white text-sm font-semibold uppercase hover:border-sky-400"
            >
              {tile.char}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={backspace}
            disabled={placedKeys.length === 0}
            className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 disabled:opacity-40"
          >
            Backspace
          </button>
          {hintsUsed < config.settings.hints_allowed && (
            <button
              type="button"
              onClick={useHint}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-sky-200 text-sm text-sky-700"
            >
              <Lightbulb className="w-4 h-4" /> Hint
            </button>
          )}
        </div>
      </div>
    </GameShell>
  )
}

export default WordBuilder
