/**
 * Pure helpers for the instructor gradebook + grading-queue UI (plan Task 3).
 * No React/DOM/network — safe to unit test in isolation.
 *
 * Matrix cell shape returned by GET /courses/{id}/gradebook (see
 * backend/app/services/gradebook_service.py build_matrix):
 *   { score: number|null, max: number, status: 'graded'|'pending'|'missing'|'late', is_late: boolean }
 *
 * Gotcha from the Task 2 ledger: a RETURNED assignment submission comes
 * back from the backend as status "pending" or "late" (is_late), NOT as a
 * distinct value — the gradebook matrix has no "returned" cell status of
 * its own. There is no reliable client-side signal to distinguish a
 * RETURNED submission from a plain pending one using the matrix payload
 * alone (both read as pending/late) — see cellStatusMeta's 'pending'/'late'
 * label wording, which intentionally stays generic instead of claiming
 * "returned" it cannot verify.
 */

export type CellStatus = 'graded' | 'pending' | 'missing' | 'late'

export interface GradebookCell {
  score: number | null
  max: number
  status: CellStatus
  is_late?: boolean
}

export interface GradebookItem {
  type: 'quiz' | 'assignment'
  id: number
  title: string
  max: number
}

/** Build the matrix cell lookup key exactly as the backend does — key off
 * item.type + item.id, never array-index alignment (Task 2 ledger gotcha). */
export function cellKey(item: Pick<GradebookItem, 'type' | 'id'>): string {
  return `${item.type}:${item.id}`
}

export interface CellStatusMeta {
  label: string
  /** Tailwind classes for the matrix cell background + text. */
  className: string
}

/** Map a gradebook cell to its display label + Tailwind classes.
 * graded=green, pending=amber, missing=gray, late=red-tinted (plan Task 3). */
export function cellStatusMeta(cell: Pick<GradebookCell, 'status' | 'is_late' | 'score' | 'max'> | undefined): CellStatusMeta {
  if (!cell) {
    return { label: '—', className: 'bg-slate-50 text-slate-400' }
  }
  if (cell.status === 'graded') {
    const scoreLabel = cell.score !== null ? `${formatScore(cell.score)}/${formatScore(cell.max)}` : 'Graded'
    return {
      label: cell.is_late ? `${scoreLabel} (late)` : scoreLabel,
      className: cell.is_late
        ? 'bg-emerald-50 text-emerald-800 ring-1 ring-inset ring-rose-200'
        : 'bg-emerald-50 text-emerald-800',
    }
  }
  if (cell.status === 'late') {
    return { label: 'Late', className: 'bg-rose-50 text-rose-700' }
  }
  if (cell.status === 'pending') {
    return { label: 'Pending', className: 'bg-amber-50 text-amber-700' }
  }
  return { label: 'Missing', className: 'bg-slate-100 text-slate-500' }
}

function formatScore(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

/** Late-submission label used across the quiz-taking + gradebook UI. */
export function lateLabel(isLate: boolean | undefined | null): string | null {
  return isLate ? 'Submitted late' : null
}

/** Rubric criterion shape shared by RubricEditor/RubricScorer. */
export interface RubricCriterion {
  criterion: string
  max_points: number
}

export interface RubricScoreEntry {
  criterion: string
  points: number
}

/** Sum of a rubric's max_points — the "total possible" display. */
export function rubricMaxTotal(rubric: RubricCriterion[]): number {
  return rubric.reduce((sum, c) => sum + (Number.isFinite(c.max_points) ? c.max_points : 0), 0)
}

/** Sum of entered scores for a rubric-scoring pass — the running total
 * shown to the instructor while grading (RubricScorer "use as grade"). */
export function rubricScoreTotal(scores: RubricScoreEntry[]): number {
  return scores.reduce((sum, s) => sum + (Number.isFinite(s.points) ? s.points : 0), 0)
}

/** Clamp a rubric criterion's entered points into [0, max_points]. */
export function clampRubricPoints(points: number, maxPoints: number): number {
  if (!Number.isFinite(points)) return 0
  return Math.max(0, Math.min(maxPoints, points))
}

export const MAX_RUBRIC_CRITERIA = 20

/** Compute the raw vs. penalized grade a late `penalty` policy applies —
 * mirrors the backend's grade_submission math exactly (raw * (1 - pct/100)),
 * for client-side preview before the instructor submits. */
export function penalizedGrade(rawGrade: number, latePenaltyPct: number): number {
  return rawGrade * (1 - latePenaltyPct / 100)
}
