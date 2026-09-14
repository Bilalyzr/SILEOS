import { describe, expect, it } from 'vitest'
import {
  capScore,
  deriveMaxScore,
  scoreDragSortItem,
  scoreMatchPair,
  scoreQuizRushAnswer,
  scoreSequenceSubmit,
  scoreWordBuilderItem,
  QUIZ_RUSH_STREAK_THRESHOLD,
} from '../scoring'

describe('deriveMaxScore', () => {
  it('is 10 x item count (mirrors the server rule)', () => {
    expect(deriveMaxScore(0)).toBe(0)
    expect(deriveMaxScore(7)).toBe(70)
  })
})

describe('scoreQuizRushAnswer', () => {
  it('wrong answer is 0 regardless of time', () => {
    expect(scoreQuizRushAnswer(false, 20, 20, 5)).toBe(0)
  })
  it('instant correct answer earns 10, last-moment earns floor 4', () => {
    expect(scoreQuizRushAnswer(true, 20, 20, 0)).toBe(10)
    expect(scoreQuizRushAnswer(true, 0, 20, 0)).toBe(4)
  })
  it('halfway remaining earns 7 (linear 4 + 6 x fraction, rounded)', () => {
    expect(scoreQuizRushAnswer(true, 10, 20, 0)).toBe(7)
  })
  it('the multiplier applies ON the 3rd consecutive correct answer (streakBefore >= 2)', () => {
    expect(QUIZ_RUSH_STREAK_THRESHOLD).toBe(3)
    // streakBefore = consecutive correct answers BEFORE this one, so
    // streakBefore=2 means this answer IS the 3rd consecutive correct.
    expect(scoreQuizRushAnswer(true, 20, 20, 2)).toBe(15) // 3rd consecutive: 10 * 1.5
    expect(scoreQuizRushAnswer(true, 20, 20, 1)).toBe(10) // 2nd consecutive: no multiplier
  })
  it('zero seconds_per_question does not divide by zero', () => {
    expect(scoreQuizRushAnswer(true, 0, 0, 0)).toBe(4)
  })
})

describe('capScore', () => {
  it('caps the running total at max_score', () => {
    expect(capScore(37, 30)).toBe(30)
    expect(capScore(12, 30)).toBe(12)
    expect(capScore(-1, 30)).toBe(0)
  })
})

describe('scoreMatchPair', () => {
  it('10 per pair minus 1 per miss on that pair (no free first miss), floor 3', () => {
    expect(scoreMatchPair(0)).toBe(10)
    expect(scoreMatchPair(1)).toBe(9)
    expect(scoreMatchPair(2)).toBe(8)
    expect(scoreMatchPair(15)).toBe(3)
  })
})

describe('scoreDragSortItem', () => {
  it('10 per correct placement, -3 per bounce-back retry, floor 2', () => {
    expect(scoreDragSortItem(0)).toBe(10)
    expect(scoreDragSortItem(1)).toBe(7)
    expect(scoreDragSortItem(2)).toBe(4)
    expect(scoreDragSortItem(3)).toBe(2)
    expect(scoreDragSortItem(9)).toBe(2)
  })
})

describe('scoreWordBuilderItem', () => {
  it('10 minus 2 per hint used, floor 0', () => {
    expect(scoreWordBuilderItem(0)).toBe(10)
    expect(scoreWordBuilderItem(3)).toBe(4)
    expect(scoreWordBuilderItem(6)).toBe(0)
  })
})

describe('scoreSequenceSubmit', () => {
  it('10 per correct final position on first submit, 7 on the retry', () => {
    expect(scoreSequenceSubmit(4, false)).toBe(40)
    expect(scoreSequenceSubmit(4, true)).toBe(28)
    expect(scoreSequenceSubmit(0, true)).toBe(0)
  })
})
