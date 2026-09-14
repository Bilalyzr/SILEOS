/**
 * RubricEditor — instructor-facing criteria list editor for an assignment's
 * rubric (plan Task 3). Wired into assignment-builder.tsx.
 *
 * Shape matches the backend's `_validate_rubric_shape` (app/routers/
 * assignments.py): a list of at most MAX_RUBRIC_CRITERIA {criterion,
 * max_points} entries, each with a non-empty criterion string and a
 * positive numeric max_points.
 */
import * as React from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MAX_RUBRIC_CRITERIA, rubricMaxTotal, type RubricCriterion } from '@/lib/gradebook'

export interface RubricEditorProps {
  rubric: RubricCriterion[]
  onChange: (rubric: RubricCriterion[]) => void
  className?: string
}

export const RubricEditor: React.FC<RubricEditorProps> = ({ rubric, onChange, className = '' }) => {
  const total = rubricMaxTotal(rubric)
  const atCap = rubric.length >= MAX_RUBRIC_CRITERIA

  const addCriterion = () => {
    if (atCap) return
    onChange([...rubric, { criterion: '', max_points: 10 }])
  }

  const removeCriterion = (index: number) => {
    onChange(rubric.filter((_, i) => i !== index))
  }

  const renameCriterion = (index: number, name: string) => {
    onChange(rubric.map((c, i) => (i === index ? { ...c, criterion: name } : c)))
  }

  const setMaxPoints = (index: number, value: number) => {
    const safe = Number.isFinite(value) ? Math.max(0, value) : 0
    onChange(rubric.map((c, i) => (i === index ? { ...c, max_points: safe } : c)))
  }

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-3">
        <label className="block text-sm font-medium text-neutral-700">
          Grading rubric (optional)
        </label>
        <span className="text-xs text-neutral-500">
          {rubric.length}/{MAX_RUBRIC_CRITERIA} criteria &middot; {total} pts total
        </span>
      </div>

      {rubric.length === 0 && (
        <p className="text-sm text-neutral-500 mb-3">
          No rubric yet — grading will use a single overall grade. Add criteria to score
          submissions per-criterion instead.
        </p>
      )}

      <div className="space-y-2">
        {rubric.map((c, index) => (
          <div key={index} className="flex items-center gap-2">
            <input
              type="text"
              value={c.criterion}
              onChange={(e) => renameCriterion(index, e.target.value)}
              placeholder={`Criterion ${index + 1} (e.g. Clarity)`}
              aria-label={`Criterion ${index + 1} name`}
              className="input flex-1"
            />
            <input
              type="number"
              min={0}
              value={c.max_points}
              onChange={(e) => setMaxPoints(index, parseFloat(e.target.value))}
              aria-label={`Criterion ${index + 1} max points`}
              className="input w-24"
            />
            <span className="text-xs text-neutral-500 w-6">pts</span>
            <button
              type="button"
              onClick={() => removeCriterion(index)}
              aria-label={`Remove criterion ${index + 1}`}
              className="btn btn-ghost btn-sm text-danger-600 hover:bg-danger-50"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      <Button
        type="button"
        variant="outline"
        size="sm"
        className="mt-3"
        onClick={addCriterion}
        disabled={atCap}
      >
        <Plus className="w-4 h-4 mr-1" />
        Add criterion
      </Button>
      {atCap && (
        <p className="text-xs text-neutral-500 mt-1">Maximum of {MAX_RUBRIC_CRITERIA} criteria reached.</p>
      )}
    </div>
  )
}

export default RubricEditor
