import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { BadgeGrid, mergeBadges, BADGE_CATALOG } from '../BadgeGrid'
import type { GamificationBadge } from '@/api/gamification'

afterEach(() => cleanup())

describe('mergeBadges (earned/unearned split)', () => {
  it('returns every catalog badge, earned ones flagged true with an awarded date', () => {
    const earned: GamificationBadge[] = [
      { slug: 'first-lesson', name: 'First Steps', description: 'x', icon: 'footprints', awarded_at: '2026-01-01T00:00:00Z' },
    ]
    const merged = mergeBadges(earned)
    expect(merged).toHaveLength(BADGE_CATALOG.length)
    const firstLesson = merged.find((b) => b.slug === 'first-lesson')!
    expect(firstLesson.earned).toBe(true)
    expect(firstLesson.awardedAt).toBe('2026-01-01T00:00:00Z')
  })

  it('flags catalog badges not in the earned list as unearned with a null award date', () => {
    const merged = mergeBadges([])
    expect(merged.every((b) => b.earned === false)).toBe(true)
    expect(merged.every((b) => b.awardedAt === null)).toBe(true)
  })

  it('never drops or duplicates a catalog entry regardless of earned-list contents', () => {
    const earned: GamificationBadge[] = BADGE_CATALOG.map((b) => ({
      slug: b.slug, name: b.name, description: b.description, icon: b.icon, awarded_at: '2026-01-01T00:00:00Z',
    }))
    const merged = mergeBadges(earned)
    expect(merged).toHaveLength(BADGE_CATALOG.length)
    expect(merged.every((b) => b.earned)).toBe(true)
    expect(new Set(merged.map((b) => b.slug)).size).toBe(BADGE_CATALOG.length)
  })

  it('ignores an earned badge slug not present in the local catalog mirror (unknown to this build)', () => {
    const earned: GamificationBadge[] = [
      { slug: 'not-a-real-slug', name: 'Ghost', description: 'x', icon: 'award', awarded_at: '2026-01-01T00:00:00Z' },
    ]
    const merged = mergeBadges(earned)
    expect(merged).toHaveLength(BADGE_CATALOG.length)
    expect(merged.some((b) => b.slug === 'not-a-real-slug')).toBe(false)
  })
})

describe('BadgeGrid', () => {
  it('renders the earned/total count header', () => {
    const earned: GamificationBadge[] = [
      { slug: 'first-lesson', name: 'First Steps', description: 'x', icon: 'footprints', awarded_at: '2026-01-01T00:00:00Z' },
    ]
    render(<BadgeGrid badges={earned} />)
    expect(screen.getByText(`1 / ${BADGE_CATALOG.length} earned`)).toBeInTheDocument()
  })

  it('marks an earned badge tile with data-earned="true" and shows its award date', () => {
    const earned: GamificationBadge[] = [
      { slug: 'first-lesson', name: 'First Steps', description: 'x', icon: 'footprints', awarded_at: '2026-01-01T00:00:00Z' },
    ]
    render(<BadgeGrid badges={earned} />)
    const tile = screen.getByTestId('badge-first-lesson')
    expect(tile.getAttribute('data-earned')).toBe('true')
  })

  it('marks an unearned badge tile with data-earned="false" and shows the rule hint text', () => {
    render(<BadgeGrid badges={[]} />)
    const tile = screen.getByTestId('badge-course-finisher')
    expect(tile.getAttribute('data-earned')).toBe('false')
    expect(tile.textContent).toContain('Complete your first course.')
  })

  it('renders one tile per catalog badge regardless of how many are earned', () => {
    render(<BadgeGrid badges={[]} />)
    for (const b of BADGE_CATALOG) {
      expect(screen.getByTestId(`badge-${b.slug}`)).toBeInTheDocument()
    }
  })
})
