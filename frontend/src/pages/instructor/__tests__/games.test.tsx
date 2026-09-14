import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as gamesApi from '@/api/games'
import InstructorGamesPage from '../games'

vi.mock('@/api/games', async (importOriginal) => {
  const actual = await importOriginal<typeof gamesApi>()
  return {
    ...actual,
    listMyGames: vi.fn(),
    publishGame: vi.fn(),
    unpublishGame: vi.fn(),
    deleteGame: vi.fn(),
    listGameResults: vi.fn(),
  }
})

vi.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: vi.fn(), error: vi.fn() },
}))

const summaries: gamesApi.GameSummary[] = [
  {
    id: 1,
    owner_id: 9,
    title: 'Fractions Rush',
    template: 'quiz_rush',
    status: 'published',
    item_count: 5,
    max_score: 50,
    attached_lesson_count: 2,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
  },
  {
    id: 2,
    owner_id: 9,
    title: 'Vocab Match',
    template: 'match_pairs',
    status: 'draft',
    item_count: 6,
    max_score: 60,
    attached_lesson_count: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-03T00:00:00Z',
  },
]

function renderPage() {
  return render(
    <MemoryRouter>
      <InstructorGamesPage />
    </MemoryRouter>
  )
}

describe('InstructorGamesPage', () => {
  beforeEach(() => {
    vi.mocked(gamesApi.listMyGames).mockReset().mockResolvedValue({ games: summaries, count: 2 })
    vi.mocked(gamesApi.publishGame).mockReset()
    vi.mocked(gamesApi.unpublishGame).mockReset()
    vi.mocked(gamesApi.deleteGame).mockReset()
    vi.mocked(gamesApi.listGameResults).mockReset()
  })

  it('renders the template gallery with Create links', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Fractions Rush')).toBeInTheDocument())
    expect(screen.getByText('Start from a template')).toBeInTheDocument()
    expect(screen.getAllByText('Quiz Rush').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Match Pairs').length).toBeGreaterThan(0)
    expect(screen.getByText('Drag Sort')).toBeInTheDocument()
    expect(screen.getByText('Word Builder')).toBeInTheDocument()
    expect(screen.getByText('Sequence')).toBeInTheDocument()
    const createLinks = screen.getAllByRole('link').filter((a) =>
      a.getAttribute('href')?.startsWith('/instructor/games/new?template='))
    expect(createLinks).toHaveLength(5)
  })

  it('renders own games with status chips', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Fractions Rush')).toBeInTheDocument())
    expect(screen.getByText('Vocab Match')).toBeInTheDocument()
    expect(screen.getByText('Published')).toBeInTheDocument()
    expect(screen.getByText('Draft')).toBeInTheDocument()
  })

  it('surfaces a 409 detail on delete via toast', async () => {
    const toast = (await import('react-hot-toast')).default
    vi.mocked(gamesApi.deleteGame).mockRejectedValue({
      response: { status: 409, data: { detail: 'Game is attached to a published lesson' } },
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('Fractions Rush')).toBeInTheDocument())

    const deleteButtons = screen.getAllByTitle('Delete')
    deleteButtons[0].click()

    await waitFor(() => expect(screen.getByText('Delete this game?')).toBeInTheDocument())
    const confirmButtons = screen.getAllByRole('button', { name: 'Delete' })
    // The last "Delete" button is the modal's confirm action (row actions
    // use title="Delete" with an icon-only accessible name that also
    // resolves to "Delete").
    confirmButtons[confirmButtons.length - 1].click()

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('Game is attached to a published lesson'))
  })

  it('surfaces a 409 detail on publish toggle via toast', async () => {
    const toast = (await import('react-hot-toast')).default
    vi.mocked(gamesApi.unpublishGame).mockRejectedValue({
      response: { status: 409, data: { detail: 'Cannot unpublish: game is attached to a lesson' } },
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('Fractions Rush')).toBeInTheDocument())

    const unpublishButtons = screen.getAllByTitle('Unpublish')
    unpublishButtons[0].click()

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('Cannot unpublish: game is attached to a lesson'))
  })
})
