import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, waitFor } from '@testing-library/react'
import { LiveChallengePanel } from '../LiveChallengePanel'
import * as liveCoding from '@/api/liveCoding'
import type { LiveCodingChallenge } from '@/api/liveCoding'

vi.mock('@/api/liveCoding', async () => {
  const actual = await vi.importActual<typeof liveCoding>('@/api/liveCoding')
  return {
    ...actual,
    liveCodingAPI: {
      ...actual.liveCodingAPI,
      list: vi.fn(),
      push: vi.fn(),
      close: vi.fn(),
      reveal: vi.fn(),
      board: vi.fn(),
      submit: vi.fn(),
    },
  }
})

vi.mock('@/api/coding', async () => {
  const actual = await vi.importActual<typeof import('@/api/coding')>('@/api/coding')
  return { ...actual, codingAPI: { ...actual.codingAPI, editorChallenges: vi.fn().mockResolvedValue([]) } }
})

vi.mock('@/components/coding/CodingWorkspace', () => ({
  CodingWorkspace: ({ slug }: { slug: string }) => <div data-testid="workspace">{slug}</div>,
}))

const api = liveCoding.liveCodingAPI as unknown as Record<string, ReturnType<typeof vi.fn>>

const openChallenge: LiveCodingChallenge = {
  id: 7,
  class_id: 42,
  challenge_id: 3,
  challenge_slug: 'add-two-integers-abc',
  challenge_title: 'Add two integers',
  status: 'open',
  graded: false,
  instructions: 'Read two numbers.',
  pushed_at: '2026-11-27T10:00:00.000Z',
  closed_at: null,
  solution_revealed: false,
  model_solution: null,
}

const emptyBoard = {
  live_id: 7,
  status: 'open' as const,
  graded: false,
  pending_submissions: 0,
  summary: { learners_submitted: 0, learners_passed: 0 },
  rows: [],
  my_row: null,
}

describe('LiveChallengePanel', () => {
  beforeEach(() => {
    api.list.mockReset()
    api.board.mockReset()
    api.board.mockResolvedValue(emptyBoard)
  })

  afterEach(() => {
    cleanup()
  })

  it('shows learners the open challenge and their own result', async () => {
    api.list.mockResolvedValue([openChallenge])
    render(<LiveChallengePanel classId={42} />)
    await waitFor(() => expect(screen.getByTestId('workspace')).toHaveTextContent('add-two-integers-abc'))
    expect(screen.getByText('Add two integers')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('live-my-result')).toHaveTextContent('No submission yet.'))
  })

  it('renders nothing for learners when no challenge is open or revealed', async () => {
    api.list.mockResolvedValue([])
    const { container } = render(<LiveChallengePanel classId={42} />)
    await waitFor(() => expect(api.list).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })

  it('shows the model solution to learners only after reveal', async () => {
    api.list.mockResolvedValue([
      {
        ...openChallenge,
        status: 'closed',
        solution_revealed: true,
        model_solution: 'print(2 + 3)',
      },
    ])
    render(<LiveChallengePanel classId={42} />)
    await waitFor(() => expect(screen.getByText('print(2 + 3)')).toBeInTheDocument())
  })

  it('gives instructors the push form and the live results board', async () => {
    api.list.mockResolvedValue([openChallenge])
    render(<LiveChallengePanel classId={42} isStaff courseId={5} />)
    await waitFor(() => expect(screen.getByTestId('live-board')).toBeInTheDocument())
    expect(screen.getByText(/is open\. Close it before pushing another/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Close' })).toBeInTheDocument()
  })
})
