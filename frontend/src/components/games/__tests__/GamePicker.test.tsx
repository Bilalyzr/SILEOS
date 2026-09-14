import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as gamesApi from '@/api/games'
import { GamePicker } from '../GamePicker'

// vi.mock factories are hoisted above imports/top-level consts, so the
// fixture list is built INSIDE the factory (mirrors H5PPicker.test.tsx's
// note on this) to avoid a "Cannot access before initialization" error.
vi.mock('@/api/games', async (importOriginal) => {
  const actual = await importOriginal<typeof gamesApi>()
  return { ...actual, listMyGames: vi.fn() }
})

const summaries: gamesApi.GameSummary[] = [
  {
    id: 1,
    owner_id: 9,
    title: 'Published Game',
    template: 'quiz_rush',
    status: 'published',
    item_count: 3,
    max_score: 30,
    attached_lesson_count: 0,
    created_at: 'x',
    updated_at: 'x',
  },
  {
    id: 2,
    owner_id: 9,
    title: 'Draft Game',
    template: 'sequence',
    status: 'draft',
    item_count: 3,
    max_score: 30,
    attached_lesson_count: 0,
    created_at: 'x',
    updated_at: 'x',
  },
]

describe('GamePicker', () => {
  beforeEach(() => {
    vi.mocked(gamesApi.listMyGames).mockResolvedValue({ games: summaries, count: 2 })
  })

  it('lists only PUBLISHED games as selectable options', async () => {
    render(
      <MemoryRouter>
        <GamePicker value={null} onChange={() => {}} />
      </MemoryRouter>
    )
    await waitFor(() => expect(screen.getByText(/Published Game/)).toBeInTheDocument())
    expect(screen.queryByText(/Draft Game/)).not.toBeInTheDocument()
  })

  it('emits the selected game id', async () => {
    const onChange = vi.fn()
    render(
      <MemoryRouter>
        <GamePicker value={null} onChange={onChange} />
      </MemoryRouter>
    )
    await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '1' } })
    expect(onChange).toHaveBeenCalledWith(1)
  })

  it('links to the games library for creating a new game', async () => {
    render(
      <MemoryRouter>
        <GamePicker value={null} onChange={() => {}} />
      </MemoryRouter>
    )
    await waitFor(() =>
      expect(screen.getByRole('link', { name: /create new game/i })).toHaveAttribute(
        'href',
        '/instructor/games'
      )
    )
  })

  it('shows a Preview button and selected-game summary once a published game is chosen', async () => {
    render(
      <MemoryRouter>
        <GamePicker value={1} onChange={() => {}} />
      </MemoryRouter>
    )
    await waitFor(() =>
      expect(screen.getByText(/Selected: Published Game/)).toBeInTheDocument()
    )
    expect(screen.getByRole('button', { name: /preview/i })).toBeInTheDocument()
  })
})
