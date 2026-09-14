/** QuizRush — timed MCQ race (spec §1 row 1). Pure props; scoring via
 * engines/scoring.ts only. All config strings render as React TEXT. */
import * as React from 'react'
import type { QuizRushConfig } from '@/api/games'
import { GameShell } from '../GameShell'
import {
  capScore,
  deriveMaxScore,
  scoreQuizRushAnswer,
} from './scoring'

export interface GameOutcome {
  score: number
  maxScore: number
  durationS: number
}

export interface EngineProps<C> {
  config: C
  onComplete: (outcome: GameOutcome) => void
  title?: string
  /** Best score across all of this user's attempts, surfaced on the
   * results screen once GamePlayer's result POST resolves (spec §6's
   * bestScore prop path). Arrives AFTER the engine's own onComplete has
   * already flipped to the results screen, so engines must read this on
   * every render rather than only capturing it once at completion time. */
  bestScore?: number | null
  /** Called when the results screen's "Play again" button is clicked.
   * Engines forward this straight to GameShell's onReplay — GamePlayer
   * supplies a key-bump remount instead of a page reload, so replaying
   * inside a lesson never navigates away. Defaults to a page reload only
   * for engines rendered standalone outside GamePlayer (e.g. isolated
   * Storybook/tests), where no remount key is available. */
  onReplay?: () => void
}

function shuffled<T>(arr: T[]): T[] {
  const copy = [...arr]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

export const QuizRush: React.FC<EngineProps<QuizRushConfig>> = ({
  config, onComplete, title = '', bestScore = null, onReplay = () => window.location.reload(),
}) => {
  const items = React.useMemo(
    () => (config.settings.shuffle ? shuffled(config.items) : config.items),
    [config]
  )
  const maxScore = deriveMaxScore(config.items.length)
  const perQuestion = config.settings.seconds_per_question

  const [index, setIndex] = React.useState(0)
  const [score, setScore] = React.useState(0)
  const [timeRemaining, setTimeRemaining] = React.useState(perQuestion)
  const [paused, setPaused] = React.useState(false)
  const [done, setDone] = React.useState(false)
  const startedAtRef = React.useRef(Date.now())
  const completedRef = React.useRef(false)
  // Mirrors timeRemaining for the interval below. Expiry must be DETECTED
  // and answer(null) CALLED from the interval body (a real side-effect
  // location), never from inside the setTimeRemaining updater itself —
  // updater functions must stay pure. Calling answer() there mixed a state
  // read+write with an unrelated side effect (advancing the question),
  // which risks double-firing if the updater is ever evaluated more than
  // once for a single logical tick (e.g. multiple ticks flushed together).
  const remainingRef = React.useRef(perQuestion)
  // index/score mirrors (and streak, which has no rendered state — it only
  // ever fed the scoring calc), updated synchronously wherever the
  // corresponding state setter is called. answer() reads from these
  // instead of from closed-over state so that several expiries handled
  // back-to-back inside one interval-driven side effect (before React has
  // had a chance to re-render and hand `answer` a fresh closure) still see
  // each other's effects rather than all operating on the same stale
  // index/score/streak captured at last render.
  const indexRef = React.useRef(0)
  const scoreRef = React.useRef(0)
  const streakRef = React.useRef(0)

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

  const answer = React.useCallback((optionIndex: number | null) => {
    const currentIndex = indexRef.current
    const item = items[currentIndex]
    const correct = optionIndex !== null && optionIndex === item.answer_index
    const points = scoreQuizRushAnswer(correct, remainingRef.current, perQuestion, streakRef.current)
    const nextScore = capScore(scoreRef.current + points, maxScore)
    scoreRef.current = nextScore
    setScore(nextScore)
    streakRef.current = correct ? streakRef.current + 1 : 0
    if (currentIndex + 1 >= items.length) {
      finish(nextScore)
    } else {
      indexRef.current = currentIndex + 1
      setIndex(currentIndex + 1)
      remainingRef.current = perQuestion
      setTimeRemaining(perQuestion)
    }
  }, [items, perQuestion, maxScore, finish])

  React.useEffect(() => {
    if (paused || done) return
    const t = setInterval(() => {
      // Expiry is detected from the ref (kept in sync with timeRemaining
      // by answer() and by the else-branch below) BEFORE touching state,
      // so this callback stays a single, ordinary side-effect site instead
      // of splitting the check into the setTimeRemaining updater. The
      // updater itself does nothing but pure arithmetic. answer() itself
      // reads/writes indexRef/scoreRef/streakRef synchronously, so calling
      // it here — even for several expiries handled inside one flush,
      // before React re-renders — always operates on the latest values.
      if (remainingRef.current <= 1) {
        remainingRef.current = perQuestion
        setTimeRemaining(perQuestion)
        answer(null) // time up = wrong
      } else {
        remainingRef.current -= 1
        setTimeRemaining((prev) => prev - 1)
      }
    }, 1000)
    return () => clearInterval(t)
  }, [paused, done, perQuestion, answer])

  const item = items[Math.min(index, items.length - 1)]

  return (
    <GameShell
      title={title}
      accentClass="text-violet-600"
      currentIndex={index}
      totalItems={items.length}
      score={score}
      maxScore={maxScore}
      timeRemainingS={timeRemaining}
      totalTimeS={perQuestion}
      paused={paused}
      onPauseToggle={() => setPaused((p) => !p)}
      result={done ? { score, maxScore, bestScore } : null}
      onReplay={onReplay}
    >
      <div className="p-4 space-y-4">
        <p className="text-lg font-medium text-gray-900">{item.prompt}</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {item.options.map((option, i) => (
            <button key={i} type="button" onClick={() => answer(i)}
              className="px-4 py-3 rounded-xl border-2 border-gray-200 text-left text-sm hover:border-violet-400 active:scale-[0.98] transition">
              {option}
            </button>
          ))}
        </div>
      </div>
    </GameShell>
  )
}

export default QuizRush
