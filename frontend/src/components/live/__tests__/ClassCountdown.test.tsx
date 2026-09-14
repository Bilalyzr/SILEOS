import { describe, it, expect } from 'vitest'
import { computeRemaining } from '../ClassCountdown'

describe('computeRemaining', () => {
  it('computes remaining time when clocks are in sync', () => {
    const fetchedAtLocal = new Date('2026-09-02T10:00:00.000Z')
    const serverTs = new Date('2026-09-02T10:00:00.000Z') // no skew
    const target = new Date('2026-09-02T10:05:00.000Z') // 5 min later
    const nowLocal = new Date('2026-09-02T10:00:00.000Z')

    const result = computeRemaining(serverTs, fetchedAtLocal, target, nowLocal)

    expect(result.isPast).toBe(false)
    expect(result.minutes).toBe(5)
    expect(result.seconds).toBe(0)
    expect(result.totalMs).toBe(5 * 60 * 1000)
  })

  it('applies a positive offset when the server clock is AHEAD of local', () => {
    // Server was 2 minutes ahead of local at fetch time.
    const fetchedAtLocal = new Date('2026-09-02T10:00:00.000Z')
    const serverTs = new Date('2026-09-02T10:02:00.000Z')
    const target = new Date('2026-09-02T10:05:00.000Z')
    // Local clock has ticked forward by 1 minute since fetch.
    const nowLocal = new Date('2026-09-02T10:01:00.000Z')

    // correctedNow = nowLocal + offset = 10:01 + 2min = 10:03
    // remaining = target(10:05) - correctedNow(10:03) = 2 min
    const result = computeRemaining(serverTs, fetchedAtLocal, target, nowLocal)

    expect(result.isPast).toBe(false)
    expect(result.minutes).toBe(2)
    expect(result.totalMs).toBe(2 * 60 * 1000)
  })

  it('applies a negative offset when the server clock is BEHIND local', () => {
    // Server was 90 seconds behind local at fetch time.
    const fetchedAtLocal = new Date('2026-09-02T10:00:00.000Z')
    const serverTs = new Date('2026-09-02T09:58:30.000Z')
    const target = new Date('2026-09-02T10:05:00.000Z')
    const nowLocal = new Date('2026-09-02T10:00:00.000Z')

    // offset = -90s; correctedNow = 10:00:00 - 90s = 09:58:30
    // remaining = 10:05:00 - 09:58:30 = 6m30s
    const result = computeRemaining(serverTs, fetchedAtLocal, target, nowLocal)

    expect(result.isPast).toBe(false)
    expect(result.minutes).toBe(6)
    expect(result.seconds).toBe(30)
  })

  it('clamps to zero and reports isPast when the target has already passed', () => {
    const fetchedAtLocal = new Date('2026-09-02T10:00:00.000Z')
    const serverTs = new Date('2026-09-02T10:00:00.000Z')
    const target = new Date('2026-09-02T09:00:00.000Z') // 1 hour in the past
    const nowLocal = new Date('2026-09-02T10:00:00.000Z')

    const result = computeRemaining(serverTs, fetchedAtLocal, target, nowLocal)

    expect(result.isPast).toBe(true)
    expect(result.totalMs).toBe(0)
    expect(result.minutes).toBe(0)
    expect(result.seconds).toBe(0)
  })

  it('reports isPast exactly at the target instant', () => {
    const fetchedAtLocal = new Date('2026-09-02T10:00:00.000Z')
    const serverTs = new Date('2026-09-02T10:00:00.000Z')
    const target = new Date('2026-09-02T10:05:00.000Z')
    const nowLocal = new Date('2026-09-02T10:05:00.000Z')

    const result = computeRemaining(serverTs, fetchedAtLocal, target, nowLocal)

    expect(result.isPast).toBe(true)
    expect(result.totalMs).toBe(0)
  })

  it('breaks down days/hours/minutes/seconds correctly for a long duration', () => {
    const fetchedAtLocal = new Date('2026-09-02T10:00:00.000Z')
    const serverTs = new Date('2026-09-02T10:00:00.000Z')
    const nowLocal = new Date('2026-09-02T10:00:00.000Z')
    // 1 day, 2 hours, 3 minutes, 4 seconds from now
    const target = new Date(nowLocal.getTime() + ((1 * 86400 + 2 * 3600 + 3 * 60 + 4) * 1000))

    const result = computeRemaining(serverTs, fetchedAtLocal, target, nowLocal)

    expect(result.days).toBe(1)
    expect(result.hours).toBe(2)
    expect(result.minutes).toBe(3)
    expect(result.seconds).toBe(4)
  })
})
