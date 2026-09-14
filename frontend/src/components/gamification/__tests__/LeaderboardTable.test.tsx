import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { LeaderboardTable } from '../LeaderboardTable'
import type { LeaderboardEntry, MyRank } from '@/api/gamification'

afterEach(() => cleanup())

const ENTRIES: LeaderboardEntry[] = [
  { rank: 1, user_id: 10, display_name: 'Alice', level: 5, total_xp: 1200 },
  { rank: 2, user_id: 20, display_name: 'Bob', level: 4, total_xp: 900 },
  { rank: 3, user_id: 30, display_name: 'Carol', level: 3, total_xp: 600 },
]

describe('LeaderboardTable', () => {
  it('renders one row per entry with rank/name/level/XP', () => {
    render(<LeaderboardTable entries={ENTRIES} />)
    expect(screen.getByText('Alice')).toBeInTheDocument()
    expect(screen.getByText('Bob')).toBeInTheDocument()
    expect(screen.getByText('Carol')).toBeInTheDocument()
    expect(screen.getByText('1,200')).toBeInTheDocument()
  })

  it('renders an empty state when there are no entries', () => {
    render(<LeaderboardTable entries={[]} />)
    expect(screen.getByText(/No leaderboard entries yet/i)).toBeInTheDocument()
  })

  it('highlights the current user\'s own row when present in entries', () => {
    render(<LeaderboardTable entries={ENTRIES} currentUserId={20} />)
    const row = screen.getByTestId('leaderboard-row-20')
    expect(row.getAttribute('data-self')).toBe('true')
    expect(screen.getByText('(you)')).toBeInTheDocument()
  })

  it('does not mark any row as self when currentUserId is not in the list', () => {
    render(<LeaderboardTable entries={ENTRIES} currentUserId={999} />)
    expect(screen.getByTestId('leaderboard-row-10').getAttribute('data-self')).toBe('false')
    expect(screen.getByTestId('leaderboard-row-20').getAttribute('data-self')).toBe('false')
    expect(screen.getByTestId('leaderboard-row-30').getAttribute('data-self')).toBe('false')
  })

  it('renders a my_rank footer when the caller is outside the listed entries', () => {
    const myRank: MyRank = { rank: 42, total_xp: 150, level: 1 }
    render(<LeaderboardTable entries={ENTRIES} myRank={myRank} currentUserId={999} />)
    const footer = screen.getByTestId('leaderboard-my-rank-footer')
    expect(footer).toBeInTheDocument()
    expect(footer.textContent).toContain('#42')
    expect(footer.textContent).toContain('150')
  })

  it('does NOT render the my_rank footer when the caller is already shown in entries', () => {
    const myRank: MyRank = { rank: 2, total_xp: 900, level: 4 }
    render(<LeaderboardTable entries={ENTRIES} myRank={myRank} currentUserId={20} />)
    expect(screen.queryByTestId('leaderboard-my-rank-footer')).not.toBeInTheDocument()
  })

  it('omits the footer entirely when myRank is null', () => {
    render(<LeaderboardTable entries={ENTRIES} myRank={null} currentUserId={999} />)
    expect(screen.queryByTestId('leaderboard-my-rank-footer')).not.toBeInTheDocument()
  })
})
