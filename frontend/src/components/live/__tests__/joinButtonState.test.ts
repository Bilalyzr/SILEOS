import { describe, it, expect } from 'vitest'
import { joinButtonState } from '../joinButtonState'

// Full six-state matrix: locked / opens-in-Xm / join / live / ended-no-recording / watch-recording.
describe('joinButtonState', () => {
  const now = new Date('2026-09-02T10:00:00.000Z')

  it('locked: student more than 15 minutes before start', () => {
    const cls = { status: 'scheduled', scheduled_start: '2026-09-02T10:30:00.000Z' }
    const result = joinButtonState(cls, now)
    expect(result.disabled).toBe(true)
    expect(result.action).toBe('none')
    expect(result.label).toMatch(/opens in/i)
  })

  it('opens-in-Xm: shows minutes remaining until the 15-minute join window', () => {
    const cls = { status: 'scheduled', scheduled_start: '2026-09-02T10:20:00.000Z' }
    // join_opens_at = 10:05, now = 10:00 -> 5 minutes to open
    const result = joinButtonState(cls, now)
    expect(result.disabled).toBe(true)
    expect(result.action).toBe('none')
    expect(result.label).toBe('Opens in 5m')
  })

  it('opens-in-<1m: sub-minute remaining is labeled distinctly', () => {
    const cls = { status: 'scheduled', scheduled_start: '2026-09-02T10:15:30.000Z' }
    // join_opens_at = 10:00:30, now = 10:00:00 -> 30s to open
    const result = joinButtonState(cls, now)
    expect(result.disabled).toBe(true)
    expect(result.label).toBe('Opens in <1m')
  })

  it('join: student within the 15-minute join window before start', () => {
    const cls = { status: 'scheduled', scheduled_start: '2026-09-02T10:10:00.000Z' }
    // join_opens_at = 09:55, now = 10:00 -> window open
    const result = joinButtonState(cls, now)
    expect(result.disabled).toBe(false)
    expect(result.action).toBe('join')
    expect(result.label).toBe('Join')
  })

  it('join: staff (instructor/admin) can join anytime before the class starts', () => {
    const cls = { status: 'scheduled', scheduled_start: '2026-09-02T14:00:00.000Z' }
    const result = joinButtonState(cls, now, true)
    expect(result.disabled).toBe(false)
    expect(result.action).toBe('join')
    expect(result.label).toBe('Start class')
  })

  it('live: class is currently live', () => {
    const cls = { status: 'live', scheduled_start: '2026-09-02T09:00:00.000Z' }
    const result = joinButtonState(cls, now)
    expect(result.disabled).toBe(false)
    expect(result.action).toBe('join')
    expect(result.label).toBe('Join — LIVE')
  })

  it('ended-no-recording: class ended and no recording is available', () => {
    const cls = { status: 'ended', scheduled_start: '2026-09-02T08:00:00.000Z', recording_status: 'none' }
    const result = joinButtonState(cls, now)
    expect(result.disabled).toBe(true)
    expect(result.action).toBe('none')
    expect(result.label).toBe('Class ended')
  })

  it('ended-no-recording: recording still processing counts as no-recording state', () => {
    const cls = { status: 'ended', scheduled_start: '2026-09-02T08:00:00.000Z', recording_status: 'processing' }
    const result = joinButtonState(cls, now)
    expect(result.disabled).toBe(true)
    expect(result.action).toBe('none')
  })

  it('watch-recording: class ended and recording is available', () => {
    const cls = { status: 'ended', scheduled_start: '2026-09-02T08:00:00.000Z', recording_status: 'available' }
    const result = joinButtonState(cls, now)
    expect(result.disabled).toBe(false)
    expect(result.action).toBe('recording')
    expect(result.label).toBe('Watch recording')
  })

  it('cancelled: always disabled regardless of staff flag', () => {
    const cls = { status: 'cancelled', scheduled_start: '2026-09-02T08:00:00.000Z' }
    expect(joinButtonState(cls, now).disabled).toBe(true)
    expect(joinButtonState(cls, now, true).disabled).toBe(true)
    expect(joinButtonState(cls, now).label).toBe('Cancelled')
  })
})
