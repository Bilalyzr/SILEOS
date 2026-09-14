import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { StreakCard, buildLastNDaysActivity } from '../StreakCard'
import type { GamificationEvent, GamificationStats } from '@/api/gamification'

afterEach(() => cleanup())

function ev(id: number, isoDate: string): GamificationEvent {
  return { id, event_type: 'lesson_completed', points: 10, course_id: null, meta: {}, created_at: isoDate }
}

describe('buildLastNDaysActivity', () => {
  const today = new Date('2026-01-10T12:00:00Z')

  it('returns 7 days, oldest first, ending on today (UTC)', () => {
    const days = buildLastNDaysActivity([], 7, today)
    expect(days).toHaveLength(7)
    expect(days[6].date).toBe('2026-01-10')
    expect(days[0].date).toBe('2026-01-04')
  })

  it('marks a day active when an event exists on that UTC calendar day', () => {
    const days = buildLastNDaysActivity([ev(1, '2026-01-08T23:59:59Z')], 7, today)
    const day = days.find((d) => d.date === '2026-01-08')!
    expect(day.active).toBe(true)
  })

  it('marks a day inactive when no event falls on it', () => {
    const days = buildLastNDaysActivity([ev(1, '2026-01-08T23:59:59Z')], 7, today)
    const day = days.find((d) => d.date === '2026-01-05')!
    expect(day.active).toBe(false)
  })

  it('ignores events with a null created_at', () => {
    const events = [{ ...ev(1, '2026-01-08T00:00:00Z'), created_at: null }]
    const days = buildLastNDaysActivity(events, 7, today)
    expect(days.every((d) => !d.active)).toBe(true)
  })

  it('multiple events on the same day only count once (day still just active/inactive)', () => {
    const days = buildLastNDaysActivity(
      [ev(1, '2026-01-08T01:00:00Z'), ev(2, '2026-01-08T20:00:00Z')],
      7,
      today,
    )
    expect(days.filter((d) => d.date === '2026-01-08')).toHaveLength(1)
    expect(days.find((d) => d.date === '2026-01-08')!.active).toBe(true)
  })

  it('an event outside the N-day window does not appear/activate any returned day', () => {
    const days = buildLastNDaysActivity([ev(1, '2025-12-01T00:00:00Z')], 7, today)
    expect(days.every((d) => !d.active)).toBe(true)
  })
})

describe('StreakCard', () => {
  function makeStats(overrides: Partial<GamificationStats> = {}): GamificationStats {
    return {
      total_xp: 0, current_streak: 3, longest_streak: 10, last_active_date: '2026-01-10',
      leaderboard_visible: true, badges_count: 0, level: 1, current_level_floor_xp: 0,
      next_level_xp: 100, xp_into_level: 0, xp_to_next_level: 100, progress_fraction: 0,
      ...overrides,
    }
  }

  it('renders current and longest streak counts', () => {
    render(<StreakCard stats={makeStats({ current_streak: 5, longest_streak: 12 })} />)
    expect(screen.getByText('5 days')).toBeInTheDocument()
    expect(screen.getByText(/Longest: 12 days/)).toBeInTheDocument()
  })

  it('singularizes "day" for a streak of 1', () => {
    render(<StreakCard stats={makeStats({ current_streak: 1, longest_streak: 1 })} />)
    expect(screen.getByText('1 day')).toBeInTheDocument()
  })

  it('degrades gracefully with null stats (loading state)', () => {
    render(<StreakCard stats={null} />)
    expect(screen.getByText('0 days')).toBeInTheDocument()
  })

  it('renders 7 day-activity dots', () => {
    render(<StreakCard stats={makeStats()} recentEvents={[]} />)
    for (let i = 0; i < 7; i++) {
      expect(screen.getByTestId(`streak-dot-${i}`)).toBeInTheDocument()
    }
  })
})
