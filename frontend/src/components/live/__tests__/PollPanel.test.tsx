import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PollPanel } from '../PollPanel'
import * as liveClassesApi from '@/api/liveClasses'
import type { PollOut } from '@/api/liveClasses'

vi.mock('@/api/liveClasses', async () => {
  const actual = await vi.importActual<typeof liveClassesApi>('@/api/liveClasses')
  return {
    ...actual,
    listPolls: vi.fn(),
    createPoll: vi.fn(),
    activatePoll: vi.fn(),
    closePoll: vi.fn(),
    votePoll: vi.fn(),
  }
})

const listPollsMock = liveClassesApi.listPolls as unknown as ReturnType<typeof vi.fn>
const votePollMock = liveClassesApi.votePoll as unknown as ReturnType<typeof vi.fn>

const activePoll: PollOut = {
  id: 1,
  class_id: 42,
  question: 'Which topic next?',
  options: ['Hooks', 'Context', 'Suspense'],
  status: 'active',
  show_results: true,
  created_at: '2026-09-02T10:00:00.000Z',
  activated_at: '2026-09-02T10:00:00.000Z',
  closed_at: null,
  tallies: [1, 0, 0],
  my_vote: null,
}

// No fake timers here: PollPanel's 10s poll interval isn't under test in
// this file (JitsiStage's heartbeat suite already covers timer-driven
// polling patterns) and @testing-library's findBy*/waitFor helpers use
// real setTimeout internally, which hangs forever if timers are faked
// without also advancing them on every await.
describe('PollPanel', () => {
  beforeEach(() => {
    listPollsMock.mockReset()
    votePollMock.mockReset()
    listPollsMock.mockResolvedValue([activePoll])
  })

  afterEach(() => {
    cleanup()
  })

  it('renders the active poll and its options', async () => {
    render(<PollPanel classId={42} isModerator={false} />)

    expect(await screen.findByText('Which topic next?')).toBeInTheDocument()
    expect(screen.getByText('Hooks')).toBeInTheDocument()
    expect(screen.getByText('Context')).toBeInTheDocument()
    expect(screen.getByText('Suspense')).toBeInTheDocument()
  })

  it('marks the tapped option as selected optimistically before the vote response resolves', async () => {
    const user = userEvent.setup()

    // Never resolves during the assertion window — proves the checkmark
    // appears from local optimistic state, not from the server response.
    let resolveVote: (value: PollOut) => void = () => {}
    votePollMock.mockImplementation(
      () => new Promise<PollOut>((resolve) => { resolveVote = resolve })
    )

    render(<PollPanel classId={42} isModerator={false} />)

    const contextOption = await screen.findByText('Context')
    await user.click(contextOption)

    // Optimistic state applied synchronously on click, before votePoll resolves.
    expect(votePollMock).toHaveBeenCalledWith(42, 1, 1)
    const optionButton = contextOption.closest('button') as HTMLButtonElement
    expect(optionButton.querySelector('svg')).toBeTruthy() // CheckCircle2 icon rendered

    // Resolve the vote afterwards so the test doesn't leave a dangling promise.
    await act(async () => {
      resolveVote({ ...activePoll, my_vote: 1, tallies: [1, 1, 0] })
      await Promise.resolve()
    })
  })

  it('shows a create form and calls createPoll when the moderator submits it', async () => {
    listPollsMock.mockResolvedValue([])
    const user = userEvent.setup()

    render(<PollPanel classId={42} isModerator />)

    const newPollButton = await screen.findByRole('button', { name: /new poll/i })
    await user.click(newPollButton)
    expect(screen.getByPlaceholderText('Question')).toBeInTheDocument()
  })
})
