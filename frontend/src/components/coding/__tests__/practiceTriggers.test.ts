import { describe, expect, it } from 'vitest'
import type { LessonCodingBlock } from '@/api/coding'
import { dueBlock, formatPosition } from '../practiceTriggers'
import { draftKey } from '../useCodingDraft'

function block(id: number, position: number | null): LessonCodingBlock {
  return {
    id,
    challenge_slug: `challenge-${id}`,
    title: `Challenge ${id}`,
    allowed_languages: ['python'],
    time_limit_ms: 2000,
    memory_limit_mb: 256,
    max_attempts: 20,
    position_seconds: position,
    instructions: '',
    ordinal: id,
  }
}

describe('dueBlock', () => {
  it('returns nothing before the first timestamp', () => {
    expect(dueBlock([block(1, 30)], 29.9, new Set())).toBeNull()
  })

  it('returns a timed block once playback reaches it', () => {
    expect(dueBlock([block(1, 30)], 30, new Set())?.id).toBe(1)
  })

  it('skips blocks already finished in this view', () => {
    expect(dueBlock([block(1, 30)], 45, new Set([1]))).toBeNull()
  })

  it('never triggers an untimed block', () => {
    expect(dueBlock([block(1, null)], 9999, new Set())).toBeNull()
  })

  it('returns the earliest due block first', () => {
    const blocks = [block(2, 60), block(1, 20), block(3, 40)]
    expect(dueBlock(blocks, 70, new Set())?.id).toBe(1)
    expect(dueBlock(blocks, 70, new Set([1]))?.id).toBe(3)
  })
})

describe('formatPosition', () => {
  it('formats minutes and seconds', () => {
    expect(formatPosition(0)).toBe('0:00')
    expect(formatPosition(9.7)).toBe('0:09')
    expect(formatPosition(90)).toBe('1:30')
  })

  it('clamps negative values to zero', () => {
    expect(formatPosition(-4)).toBe('0:00')
  })
})

describe('draftKey', () => {
  it('separates challenges and languages', () => {
    expect(draftKey('sum', 'python')).not.toBe(draftKey('sum', 'c'))
    expect(draftKey('sum', 'python')).not.toBe(draftKey('other', 'python'))
  })
})
