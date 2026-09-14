/**
 * GamePlayer — fetches /games/{id}/play, dispatches to the template's
 * engine, POSTs the advisory result on completion, and fires
 * onLessonComplete AFTER a successful POST when embedded in a lesson.
 * previewOnly (instructor preview) suppresses BOTH — mirrors H5PLesson's
 * semantics exactly. Server-side the same flag is enforced anyway
 * (owner/admin POSTs return {preview: true} without writing).
 */
import * as React from 'react'
import { Loader2, AlertTriangle } from 'lucide-react'
import {
  getGamePlay,
  submitGameResult,
  type GamePlayPayload,
} from '@/api/games'
import { QuizRush, type GameOutcome } from './engines/QuizRush'
import { MatchPairs } from './engines/MatchPairs'
import { DragSort } from './engines/DragSort'
import { WordBuilder } from './engines/WordBuilder'
import { SequenceGame } from './engines/SequenceGame'

export interface GamePlayerProps {
  gameId: number
  /** Instructor preview: play normally but NEVER POST a result and never
   * fire onLessonComplete — mirrors H5PLesson's previewOnly semantics. */
  previewOnly?: boolean
  /** Fired once, after the result POST resolves successfully, when embedded
   * in a lesson (lesson-redesigned wires its lesson-complete call here). */
  onLessonComplete?: () => void
  className?: string
}

export const GamePlayer: React.FC<GamePlayerProps> = ({
  gameId, previewOnly = false, onLessonComplete, className = '',
}) => {
  const [payload, setPayload] = React.useState<GamePlayPayload | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [bestScore, setBestScore] = React.useState<number | null>(null)
  // Bumped on replay and used as the engine element's `key` below, forcing
  // a full remount (fresh internal state, score back to 0) in place —
  // replacing the old window.location.reload() so replaying inside a
  // lesson never navigates away from the page.
  const [replayKey, setReplayKey] = React.useState(0)
  const completionHandledRef = React.useRef(false)

  React.useEffect(() => {
    completionHandledRef.current = false
    setPayload(null)
    setError(null)
    setBestScore(null)
    // Stale-response guard: if gameId changes again before this fetch
    // resolves, a late response for the PREVIOUS id must not overwrite the
    // state a newer effect run already reset/populated.
    let cancelled = false
    getGamePlay(gameId)
      .then((data) => {
        if (cancelled) return
        setPayload(data)
      })
      .catch((err: any) => {
        if (cancelled) return
        setError(err?.response?.data?.detail || 'This game could not be loaded.')
      })
    return () => {
      cancelled = true
    }
  }, [gameId])

  const handleComplete = React.useCallback(async (outcome: GameOutcome) => {
    if (completionHandledRef.current) return
    completionHandledRef.current = true
    if (previewOnly) return
    try {
      const result = await submitGameResult(gameId, {
        score: outcome.score,
        max_score: outcome.maxScore,
        duration_s: outcome.durationS,
      })
      // Owner/admin preview writes come back as {preview: true} with no
      // best_score to show — only a real result row carries one.
      if ('best_score' in result) {
        setBestScore(result.best_score)
      }
      onLessonComplete?.()
    } catch (err) {
      // Advisory data — a failed POST must not break the results screen —
      // but leave a trail for debugging instead of swallowing it silently.
      console.warn('game result submission failed', err)
    }
  }, [gameId, previewOnly, onLessonComplete])

  const handleReplay = React.useCallback(() => {
    completionHandledRef.current = false
    setBestScore(null)
    setReplayKey((k) => k + 1)
  }, [])

  if (error) {
    return (
      <div className={`flex items-center justify-center p-8 text-red-600 ${className}`}>
        <AlertTriangle className="w-5 h-5 mr-2" /> <span className="text-sm">{error}</span>
      </div>
    )
  }
  if (!payload) {
    return (
      <div className={`flex items-center justify-center p-8 text-gray-500 ${className}`}>
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        <span className="text-sm">Loading game&hellip;</span>
      </div>
    )
  }

  const common = {
    onComplete: handleComplete, title: payload.title, bestScore, onReplay: handleReplay,
  }
  return (
    <div className={`h-full w-full ${className}`}>
      {payload.template === 'quiz_rush' && (
        <QuizRush key={replayKey} config={payload.config} {...common} />
      )}
      {payload.template === 'match_pairs' && (
        <MatchPairs key={replayKey} config={payload.config} {...common} />
      )}
      {payload.template === 'drag_sort' && (
        <DragSort key={replayKey} config={payload.config} {...common} />
      )}
      {payload.template === 'word_builder' && (
        <WordBuilder key={replayKey} config={payload.config} {...common} />
      )}
      {payload.template === 'sequence' && (
        <SequenceGame key={replayKey} config={payload.config} {...common} />
      )}
    </div>
  )
}

export default GamePlayer
