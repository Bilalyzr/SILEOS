import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, screen, cleanup, waitFor } from '@testing-library/react'
import { AwardToaster, eventToToast } from '../AwardToaster'
import * as gamificationApi from '@/api/gamification'
import type { GamificationEvent } from '@/api/gamification'

vi.mock('@/utils/animations', () => ({
  celebrationAnimation: vi.fn(),
}))

vi.mock('@/api/gamification', async () => {
  const actual = await vi.importActual<typeof gamificationApi>('@/api/gamification')
  return {
    ...actual,
    gamificationAPI: {
      ...actual.gamificationAPI,
      getUnseen: vi.fn(),
      markSeen: vi.fn().mockResolvedValue({ updated: 1 }),
    },
  }
})

const getUnseenMock = gamificationApi.gamificationAPI.getUnseen as unknown as ReturnType<typeof vi.fn>
const markSeenMock = gamificationApi.gamificationAPI.markSeen as unknown as ReturnType<typeof vi.fn>

function badgeEvent(id: number, badgeName: string): GamificationEvent {
  return {
    id, event_type: `badge:${badgeName.toLowerCase().replace(/\s+/g, '-')}`, points: 0, course_id: null,
    meta: { seen: false, badge_name: badgeName }, created_at: '2026-01-01T00:00:00Z',
  }
}

afterEach(() => cleanup())
beforeEach(async () => {
  getUnseenMock.mockReset()
  markSeenMock.mockClear()
  const { celebrationAnimation } = await import('@/utils/animations')
  ;(celebrationAnimation as unknown as ReturnType<typeof vi.fn>).mockClear()
})

describe('eventToToast', () => {
  it('maps a badge event to a "Badge earned!" toast using meta.badge_name', () => {
    const t = eventToToast(badgeEvent(1, 'First Steps'))
    expect(t.kind).toBe('badge')
    expect(t.title).toBe('Badge earned!')
    expect(t.description).toBe('First Steps')
  })

  it('maps a streak_milestone event to a streak toast with the point total', () => {
    const ev: GamificationEvent = {
      id: 2, event_type: 'streak_milestone:7', points: 50, course_id: null,
      meta: { seen: false, streak: 7 }, created_at: '2026-01-01T00:00:00Z',
    }
    const t = eventToToast(ev)
    expect(t.kind).toBe('streak')
    expect(t.description).toContain('7-day streak')
    expect(t.description).toContain('+50 XP')
  })

  it('falls back to a generic toast for an unrecognized event_type', () => {
    const ev: GamificationEvent = {
      id: 3, event_type: 'lesson_completed', points: 10, course_id: 5,
      meta: {}, created_at: '2026-01-01T00:00:00Z',
    }
    const t = eventToToast(ev)
    expect(t.kind).toBe('other')
    expect(t.description).toContain('+10 XP')
  })
})

describe('AwardToaster', () => {
  it('renders nothing when there are no unseen events, and does not call markSeen', async () => {
    getUnseenMock.mockResolvedValue({ unseen: [] })
    render(<AwardToaster />)
    await waitFor(() => expect(getUnseenMock).toHaveBeenCalledTimes(1))
    expect(screen.queryByTestId('award-toaster')).not.toBeInTheDocument()
    expect(markSeenMock).not.toHaveBeenCalled()
  })

  it('fires a toast per unseen event and calls markSeen once with all ids', async () => {
    const events = [badgeEvent(11, 'First Steps'), badgeEvent(12, 'Course Finisher')]
    getUnseenMock.mockResolvedValue({ unseen: events })

    render(<AwardToaster />)

    await waitFor(() => expect(screen.getByTestId('award-toaster')).toBeInTheDocument())
    expect(screen.getByTestId('award-toast-11')).toBeInTheDocument()
    expect(screen.getByTestId('award-toast-12')).toBeInTheDocument()

    await waitFor(() => expect(markSeenMock).toHaveBeenCalledTimes(1))
    expect(markSeenMock).toHaveBeenCalledWith([11, 12])
  })

  it('fires celebrationAnimation exactly once when unseen events are present', async () => {
    const { celebrationAnimation } = await import('@/utils/animations')
    getUnseenMock.mockResolvedValue({ unseen: [badgeEvent(21, 'Quiz Ace')] })

    render(<AwardToaster />)

    await waitFor(() => expect(screen.getByTestId('award-toaster')).toBeInTheDocument())
    expect(celebrationAnimation).toHaveBeenCalledTimes(1)
  })

  it('never calls markSeen more than once even if getUnseen resolves after unmount/remount churn', async () => {
    getUnseenMock.mockResolvedValue({ unseen: [badgeEvent(31, 'Streak Warrior')] })
    const { unmount } = render(<AwardToaster />)
    await waitFor(() => expect(markSeenMock).toHaveBeenCalledTimes(1))
    unmount()
    // No further calls after unmount.
    expect(markSeenMock).toHaveBeenCalledTimes(1)
  })

  it('degrades silently (no throw, no toaster) when getUnseen rejects', async () => {
    getUnseenMock.mockRejectedValue(new Error('network error'))
    render(<AwardToaster />)
    await waitFor(() => expect(getUnseenMock).toHaveBeenCalledTimes(1))
    expect(screen.queryByTestId('award-toaster')).not.toBeInTheDocument()
    expect(markSeenMock).not.toHaveBeenCalled()
  })
})
