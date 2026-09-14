import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as gamesApi from '@/api/games'
import { courseAPI } from '@/api/course'
import GamePlayPage from '../game-play'

vi.mock('@/api/games', async (importOriginal) => {
  const actual = await importOriginal<typeof gamesApi>()
  return {
    ...actual,
    getGamePlay: vi.fn(),
    submitGameResult: vi.fn(),
  }
})

vi.mock('@/api/course', () => ({
  courseAPI: {
    getCourse: vi.fn(),
  },
}))

const playPayload: gamesApi.GamePlayPayload = {
  id: 1,
  title: 'Fractions Rush',
  template: 'quiz_rush',
  config: {
    items: [{ prompt: 'Q1?', options: ['a', 'b'], answer_index: 0 }],
    settings: { seconds_per_question: 20, shuffle: false },
  },
  max_score: 10,
  preview: false,
}

function renderPage(path = '/games/1/play') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/games/:id/play" element={<GamePlayPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('GamePlayPage', () => {
  beforeEach(() => {
    vi.mocked(gamesApi.getGamePlay).mockReset()
    vi.mocked(courseAPI.getCourse).mockReset()
    vi.mocked(courseAPI.getCourse).mockResolvedValue({ post_title: 'Algebra 101' } as any)
  })

  it('renders GamePlayer (game title) once the play gate passes', async () => {
    vi.mocked(gamesApi.getGamePlay).mockResolvedValue(playPayload)
    renderPage()
    await waitFor(() => expect(screen.getByText('Fractions Rush')).toBeInTheDocument())
  })

  it('shows invalid-link guidance for a non-numeric id without calling the API', () => {
    renderPage('/games/not-a-number/play')
    expect(screen.getByText(/invalid game link/i)).toBeInTheDocument()
    expect(gamesApi.getGamePlay).not.toHaveBeenCalled()
  })

  it('403 -> friendly enrollment guidance, with a link to the course when courseId is present', async () => {
    vi.mocked(gamesApi.getGamePlay).mockRejectedValue({ response: { status: 403 } })
    renderPage('/games/1/play?courseId=42')
    await waitFor(() =>
      expect(screen.getByText(/not enrolled/i)).toBeInTheDocument()
    )
    const courseLink = screen.getByRole('link', { name: /go to course/i })
    expect(courseLink).toHaveAttribute('href', '/courses/42')
  })

  it('403 without courseId -> enrollment guidance with a fallback link to my courses', async () => {
    vi.mocked(gamesApi.getGamePlay).mockRejectedValue({ response: { status: 403 } })
    renderPage('/games/1/play')
    await waitFor(() =>
      expect(screen.getByText(/not enrolled/i)).toBeInTheDocument()
    )
    expect(screen.getByRole('link', { name: /view my courses/i })).toBeInTheDocument()
  })

  it('404 -> generic not-found guidance (no enrollment wording)', async () => {
    vi.mocked(gamesApi.getGamePlay).mockRejectedValue({ response: { status: 404 } })
    renderPage('/games/1/play')
    await waitFor(() =>
      expect(screen.getByText(/game not found/i)).toBeInTheDocument()
    )
    expect(screen.queryByText(/not enrolled/i)).not.toBeInTheDocument()
  })

  it('an unexpected error status also falls back to the generic not-found guidance', async () => {
    vi.mocked(gamesApi.getGamePlay).mockRejectedValue({ response: { status: 500 } })
    renderPage('/games/1/play')
    await waitFor(() =>
      expect(screen.getByText(/game not found/i)).toBeInTheDocument()
    )
  })
})
