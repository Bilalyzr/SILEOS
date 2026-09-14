import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as gamesApi from '@/api/games'
import { GamePlayer } from '../GamePlayer'

vi.mock('@/api/games', async (importOriginal) => {
  const actual = await importOriginal<typeof gamesApi>()
  return {
    ...actual,
    getGamePlay: vi.fn(),
    submitGameResult: vi.fn(),
  }
})

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

describe('GamePlayer', () => {
  beforeEach(() => {
    vi.mocked(gamesApi.getGamePlay).mockReset()
    vi.mocked(gamesApi.submitGameResult).mockReset()
    vi.mocked(gamesApi.getGamePlay).mockResolvedValue(playPayload)
    vi.mocked(gamesApi.submitGameResult).mockResolvedValue({
      game_id: 1, user_id: 2, score: 10, max_score: 10, duration_s: 5,
      best_score: 10, created_at: 'now',
    })
  })

  it('fetches the play payload and renders the game title', async () => {
    render(<GamePlayer gameId={1} />)
    await waitFor(() => expect(screen.getByText('Fractions Rush')).toBeInTheDocument())
    expect(gamesApi.getGamePlay).toHaveBeenCalledWith(1)
  })

  it('POSTs the result and fires onLessonComplete on engine completion', async () => {
    const onLessonComplete = vi.fn()
    render(<GamePlayer gameId={1} onLessonComplete={onLessonComplete} />)
    await waitFor(() => expect(screen.getByText('Fractions Rush')).toBeInTheDocument())
    // Drive completion through the exported test hook (see GamePlayer:
    // engines call handleComplete; the test invokes it via the completion
    // path by finishing the single-question quiz).
    screen.getByRole('button', { name: 'a' }).click()
    await waitFor(() =>
      expect(gamesApi.submitGameResult).toHaveBeenCalledWith(1, {
        score: expect.any(Number), max_score: 10, duration_s: expect.any(Number),
      })
    )
    await waitFor(() => expect(onLessonComplete).toHaveBeenCalledTimes(1))
  })

  it('previewOnly suppresses the result POST and onLessonComplete', async () => {
    const onLessonComplete = vi.fn()
    vi.mocked(gamesApi.getGamePlay).mockResolvedValue({ ...playPayload, preview: true })
    render(<GamePlayer gameId={1} previewOnly onLessonComplete={onLessonComplete} />)
    await waitFor(() => expect(screen.getByText('Fractions Rush')).toBeInTheDocument())
    screen.getByRole('button', { name: 'a' }).click()
    // GameShell's results screen replaces the question with the replay CTA.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /play again/i })).toBeInTheDocument())
    expect(gamesApi.submitGameResult).not.toHaveBeenCalled()
    expect(onLessonComplete).not.toHaveBeenCalled()
  })

  it('renders "Best: N" on the results screen once the result POST resolves with a best_score', async () => {
    vi.mocked(gamesApi.submitGameResult).mockResolvedValue({
      game_id: 1, user_id: 2, score: 10, max_score: 10, duration_s: 5,
      best_score: 40, created_at: 'now',
    })
    render(<GamePlayer gameId={1} />)
    await waitFor(() => expect(screen.getByText('Fractions Rush')).toBeInTheDocument())
    screen.getByRole('button', { name: 'a' }).click()

    await waitFor(() => expect(gamesApi.submitGameResult).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText(/Best score: 40/i)).toBeInTheDocument())
  })

  it('replay resets the engine in place (score back to 0) WITHOUT reloading the page', async () => {
    const reloadSpy = vi.fn()
    const originalLocation = window.location
    // jsdom's window.location.reload throws "Not implemented" unless
    // stubbed — replace the whole location object so a real reload call
    // would be observable via reloadSpy instead of crashing the test.
    // @ts-expect-error - reassigning window.location for the test
    delete window.location
    // @ts-expect-error - partial Location stub is fine for this assertion
    window.location = { ...originalLocation, reload: reloadSpy }

    render(<GamePlayer gameId={1} />)
    await waitFor(() => expect(screen.getByText('Fractions Rush')).toBeInTheDocument())

    // Answer correctly -> single-question quiz completes -> results screen.
    screen.getByRole('button', { name: 'a' }).click()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /play again/i })).toBeInTheDocument())

    screen.getByRole('button', { name: /play again/i }).click()

    // Back to the live question screen with a fresh (0-score) engine
    // instance — never a full page reload.
    await waitFor(() => expect(screen.getByRole('button', { name: 'a' })).toBeInTheDocument())
    expect(reloadSpy).not.toHaveBeenCalled()

    // @ts-expect-error - restore for other tests
    window.location = originalLocation
  })
})
