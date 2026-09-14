import { describe, it, expect } from 'vitest'
import {
  cellKey,
  cellStatusMeta,
  lateLabel,
  rubricMaxTotal,
  rubricScoreTotal,
  clampRubricPoints,
  penalizedGrade,
} from '../gradebook'

describe('cellKey', () => {
  it('builds "{type}:{id}" — never index alignment', () => {
    expect(cellKey({ type: 'quiz', id: 3 })).toBe('quiz:3')
    expect(cellKey({ type: 'assignment', id: 7 })).toBe('assignment:7')
  })
})

describe('cellStatusMeta', () => {
  it('graded cell shows score/max', () => {
    const meta = cellStatusMeta({ status: 'graded', score: 8, max: 10, is_late: false })
    expect(meta.label).toBe('8/10')
    expect(meta.className).toContain('emerald')
  })

  it('graded + late cell appends a late marker and keeps a rose ring', () => {
    const meta = cellStatusMeta({ status: 'graded', score: 8, max: 10, is_late: true })
    expect(meta.label).toBe('8/10 (late)')
    expect(meta.className).toContain('rose')
  })

  it('pending cell', () => {
    const meta = cellStatusMeta({ status: 'pending', score: null, max: 10 })
    expect(meta.label).toBe('Pending')
    expect(meta.className).toContain('amber')
  })

  it('late (ungraded) cell', () => {
    const meta = cellStatusMeta({ status: 'late', score: null, max: 10, is_late: true })
    expect(meta.label).toBe('Late')
    expect(meta.className).toContain('rose')
  })

  it('missing cell', () => {
    const meta = cellStatusMeta({ status: 'missing', score: null, max: 10 })
    expect(meta.label).toBe('Missing')
    expect(meta.className).toContain('slate')
  })

  it('undefined cell (item not in row) falls back gracefully', () => {
    const meta = cellStatusMeta(undefined)
    expect(meta.label).toBe('—')
  })

  it('formats non-integer scores with one decimal', () => {
    const meta = cellStatusMeta({ status: 'graded', score: 8.5, max: 10, is_late: false })
    expect(meta.label).toBe('8.5/10')
  })
})

describe('lateLabel', () => {
  it('returns a label when late', () => {
    expect(lateLabel(true)).toBe('Submitted late')
  })
  it('returns null when not late or unknown', () => {
    expect(lateLabel(false)).toBeNull()
    expect(lateLabel(undefined)).toBeNull()
    expect(lateLabel(null)).toBeNull()
  })
})

describe('rubric math', () => {
  const rubric = [
    { criterion: 'Clarity', max_points: 10 },
    { criterion: 'Correctness', max_points: 20 },
  ]

  it('rubricMaxTotal sums max_points', () => {
    expect(rubricMaxTotal(rubric)).toBe(30)
  })

  it('rubricMaxTotal handles an empty rubric', () => {
    expect(rubricMaxTotal([])).toBe(0)
  })

  it('rubricScoreTotal sums entered points', () => {
    const scores = [
      { criterion: 'Clarity', points: 7 },
      { criterion: 'Correctness', points: 15 },
    ]
    expect(rubricScoreTotal(scores)).toBe(22)
  })

  it('clampRubricPoints clamps into [0, max]', () => {
    expect(clampRubricPoints(-5, 10)).toBe(0)
    expect(clampRubricPoints(15, 10)).toBe(10)
    expect(clampRubricPoints(5, 10)).toBe(5)
    expect(clampRubricPoints(NaN, 10)).toBe(0)
  })
})

describe('penalizedGrade', () => {
  it('applies a percentage penalty exactly like the backend', () => {
    expect(penalizedGrade(100, 10)).toBe(90)
    expect(penalizedGrade(80, 25)).toBe(60)
  })

  it('0% penalty leaves the grade unchanged', () => {
    expect(penalizedGrade(50, 0)).toBe(50)
  })
})
