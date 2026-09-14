import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { XPLevelCard, clampProgressFraction } from '../XPLevelCard'
import type { GamificationStats } from '@/api/gamification'

afterEach(() => cleanup())

function makeStats(overrides: Partial<GamificationStats> = {}): GamificationStats {
  return {
    total_xp: 250,
    current_streak: 0,
    longest_streak: 0,
    last_active_date: null,
    leaderboard_visible: true,
    badges_count: 0,
    level: 2,
    current_level_floor_xp: 300,
    next_level_xp: 600,
    xp_into_level: 0,
    xp_to_next_level: 300,
    progress_fraction: 0.5,
    ...overrides,
  }
}

describe('clampProgressFraction (level-ring math)', () => {
  it('passes through a normal in-range fraction', () => {
    expect(clampProgressFraction(0.42)).toBe(0.42)
  })

  it('clamps a fraction above 1 (e.g. floating point overshoot) to 1', () => {
    expect(clampProgressFraction(1.0001)).toBe(1)
  })

  it('clamps a negative fraction to 0', () => {
    expect(clampProgressFraction(-0.01)).toBe(0)
  })

  it('treats a non-finite fraction (span===0 upstream) as fully filled, matching the backend fallback', () => {
    expect(clampProgressFraction(NaN)).toBe(1)
    expect(clampProgressFraction(Infinity)).toBe(1)
    expect(clampProgressFraction(-Infinity)).toBe(0)
  })

  it('handles exact boundary values 0 and 1 unchanged', () => {
    expect(clampProgressFraction(0)).toBe(0)
    expect(clampProgressFraction(1)).toBe(1)
  })
})

describe('XPLevelCard', () => {
  it('renders the level number and total XP', () => {
    render(<XPLevelCard stats={makeStats({ level: 3, total_xp: 750 })} />)
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('750 XP')).toBeInTheDocument()
  })

  it('renders "Max level reached" when xp_to_next_level is 0', () => {
    render(<XPLevelCard stats={makeStats({ xp_to_next_level: 0, xp_into_level: 100 })} />)
    expect(screen.getByText(/Max level reached/i)).toBeInTheDocument()
  })

  it('renders progress copy toward the next level when xp_to_next_level > 0', () => {
    render(<XPLevelCard stats={makeStats({ level: 2, xp_into_level: 150, xp_to_next_level: 150 })} />)
    expect(screen.getByText(/to level 3/i)).toBeInTheDocument()
  })

  it('degrades gracefully with null/undefined stats (loading state)', () => {
    render(<XPLevelCard stats={null} />)
    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.getByText('0 XP')).toBeInTheDocument()
  })

  it('sets the SVG ring stroke-dashoffset proportional to the progress fraction', () => {
    const { container } = render(<XPLevelCard stats={makeStats({ progress_fraction: 0 })} />)
    const circles = container.querySelectorAll('circle')
    // Second circle is the progress ring (first is the track).
    const progressCircle = circles[1] as SVGCircleElement
    const circumference = 2 * Math.PI * 30
    // fraction 0 -> full circumference offset (empty ring)
    expect(Number(progressCircle.getAttribute('stroke-dashoffset'))).toBeCloseTo(circumference, 1)
  })

  it('a full progress fraction (1) sets stroke-dashoffset to 0 (full ring)', () => {
    const { container } = render(<XPLevelCard stats={makeStats({ progress_fraction: 1 })} />)
    const circles = container.querySelectorAll('circle')
    const progressCircle = circles[1] as SVGCircleElement
    expect(Number(progressCircle.getAttribute('stroke-dashoffset'))).toBeCloseTo(0, 1)
  })
})
