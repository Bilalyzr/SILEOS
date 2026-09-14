/**
 * RubricScorer — per-criterion points inputs + running total for grading
 * one submission against its assignment's rubric (plan Task 3). Wired into
 * assignment-grading.tsx. Purely controlled: the parent owns the score
 * state and receives updates via onChange; "Use as grade" hands the parent
 * the current rubric total so it can adopt it as the overall grade.
 */
import * as React from 'react'
import { Button } from '@/components/ui/button'
import {
  clampRubricPoints,
  rubricMaxTotal,
  rubricScoreTotal,
  type RubricCriterion,
  type RubricScoreEntry,
} from '@/lib/gradebook'

export interface RubricScorerProps {
  rubric: RubricCriterion[]
  scores: RubricScoreEntry[]
  onChange: (scores: RubricScoreEntry[]) => void
  onUseAsGrade?: (total: number) => void
  className?: string
}

function scoreFor(scores: RubricScoreEntry[], criterion: string): number {
  return scores.find((s) => s.criterion === criterion)?.points ?? 0
}

export const RubricScorer: React.FC<RubricScorerProps> = ({
  rubric, scores, onChange, onUseAsGrade, className = '',
}) => {
  if (rubric.length === 0) return null

  const maxTotal = rubricMaxTotal(rubric)
  const total = rubricScoreTotal(
    rubric.map((c) => ({ criterion: c.criterion, points: scoreFor(scores, c.criterion) }))
  )

  const setPoints = (criterion: string, maxPoints: number, raw: number) => {
    const clamped = clampRubricPoints(raw, maxPoints)
    const exists = scores.some((s) => s.criterion === criterion)
    const next = exists
      ? scores.map((s) => (s.criterion === criterion ? { ...s, points: clamped } : s))
      : [...scores, { criterion, points: clamped }]
    onChange(next)
  }

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-neutral-900">Rubric scoring</h4>
        <span className="text-sm font-medium text-neutral-700">
          {total} / {maxTotal} pts
        </span>
      </div>

      <div className="space-y-3">
        {rubric.map((c) => {
          const value = scoreFor(scores, c.criterion)
          return (
            <div key={c.criterion} className="flex items-center gap-3">
              <span className="flex-1 text-sm text-neutral-700">{c.criterion}</span>
              <input
                type="number"
                min={0}
                max={c.max_points}
                value={value}
                onChange={(e) => setPoints(c.criterion, c.max_points, parseFloat(e.target.value))}
                aria-label={`${c.criterion} score`}
                className="input w-20"
              />
              <span className="text-xs text-neutral-500 w-16">/ {c.max_points} pts</span>
            </div>
          )
        })}
      </div>

      {onUseAsGrade && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-3"
          onClick={() => onUseAsGrade(total)}
        >
          Use {total} as grade
        </Button>
      )}
    </div>
  )
}

export default RubricScorer
