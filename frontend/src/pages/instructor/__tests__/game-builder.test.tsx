import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as gamesApi from '@/api/games'
import GameBuilderPage from '../game-builder'

vi.mock('@/api/games', async (importOriginal) => {
  const actual = await importOriginal<typeof gamesApi>()
  return {
    ...actual,
    getGame: vi.fn(),
    createGame: vi.fn(),
    updateGame: vi.fn(),
    publishGame: vi.fn(),
  }
})

vi.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: vi.fn(), error: vi.fn() },
}))

const existingGame: gamesApi.Game = {
  id: 42,
  owner_id: 9,
  title: 'Fractions Rush',
  status: 'draft',
  template: 'quiz_rush',
  config: {
    items: [{ prompt: 'What is 1/2 + 1/2?', options: ['1', '2'], answer_index: 0 }],
    settings: { seconds_per_question: 20, shuffle: false },
  },
  item_count: 1,
  max_score: 10,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/instructor/games/new" element={<GameBuilderPage />} />
        <Route path="/instructor/games/:id/edit" element={<GameBuilderPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('GameBuilderPage', () => {
  beforeEach(() => {
    vi.mocked(gamesApi.getGame).mockReset()
    vi.mocked(gamesApi.createGame).mockReset()
    vi.mocked(gamesApi.updateGame).mockReset()
    vi.mocked(gamesApi.publishGame).mockReset()
  })

  it('reads ?template= and starts a fresh quiz_rush draft', async () => {
    renderAt('/instructor/games/new?template=quiz_rush')
    await waitFor(() => expect(screen.getByText('New game')).toBeInTheDocument())
    expect(screen.getByText('Quiz Rush')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Question prompt')).toBeInTheDocument()
  })

  it('loads an existing game via getGame and pre-fills the title/config', async () => {
    vi.mocked(gamesApi.getGame).mockResolvedValue(existingGame)
    renderAt('/instructor/games/42/edit')
    await waitFor(() => expect(gamesApi.getGame).toHaveBeenCalledWith(42))
    await waitFor(() =>
      expect(screen.getByDisplayValue('Fractions Rush')).toBeInTheDocument())
    expect(screen.getByDisplayValue('What is 1/2 + 1/2?')).toBeInTheDocument()
  })

  it('constructs the correct updateGame payload on Save draft', async () => {
    vi.mocked(gamesApi.getGame).mockResolvedValue(existingGame)
    vi.mocked(gamesApi.updateGame).mockResolvedValue(existingGame)
    renderAt('/instructor/games/42/edit')
    await waitFor(() =>
      expect(screen.getByDisplayValue('Fractions Rush')).toBeInTheDocument())

    const titleInput = screen.getByDisplayValue('Fractions Rush')
    fireEvent.change(titleInput, { target: { value: 'Fractions Rush 2' } })

    const saveButton = screen.getByRole('button', { name: 'Save draft' })
    fireEvent.click(saveButton)

    await waitFor(() =>
      expect(gamesApi.updateGame).toHaveBeenCalledWith(42, {
        title: 'Fractions Rush 2',
        config: existingGame.config,
      }))
  })

  it('surfaces server 400 detail verbatim on save failure', async () => {
    vi.mocked(gamesApi.getGame).mockResolvedValue(existingGame)
    vi.mocked(gamesApi.updateGame).mockRejectedValue({
      response: { status: 400, data: { detail: 'config exceeds 64KB limit' } },
    })
    renderAt('/instructor/games/42/edit')
    await waitFor(() =>
      expect(screen.getByDisplayValue('Fractions Rush')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: 'Save draft' }))

    await waitFor(() =>
      expect(screen.getByText('config exceeds 64KB limit')).toBeInTheDocument())
  })

  it('disables Save/Publish while validation errors exist', async () => {
    renderAt('/instructor/games/new?template=quiz_rush')
    await waitFor(() => expect(screen.getByText('New game')).toBeInTheDocument())
    // Fresh quiz_rush draft has an empty prompt -> invalid -> Save disabled.
    expect(screen.getByRole('button', { name: 'Save draft' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Publish' })).toBeDisabled()
  })

  it('shows a non-blocking amber duplicate-options warning without disabling Save/Publish', async () => {
    const duplicateOptionsGame: gamesApi.Game = {
      ...existingGame,
      config: {
        items: [{ prompt: 'Pick a color', options: ['Blue', 'blue', 'Green'], answer_index: 0 }],
        settings: { seconds_per_question: 20, shuffle: false },
      },
    }
    vi.mocked(gamesApi.getGame).mockResolvedValue(duplicateOptionsGame)
    renderAt('/instructor/games/42/edit')
    await waitFor(() =>
      expect(screen.getByDisplayValue('Fractions Rush')).toBeInTheDocument())

    expect(screen.getByText(/Possible duplicates/)).toBeInTheDocument()
    expect(screen.getByText(/Question 1 has duplicate options/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save draft' })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: 'Publish' })).not.toBeDisabled()
  })
})
