import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, screen, cleanup, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { H5PPicker } from '../H5PPicker'
import * as h5pApi from '@/api/h5p'

// vi.mock factories are hoisted above imports/top-level consts, so the
// fixture content object is defined INSIDE the factory (not referenced from
// an outer const) to avoid a "Cannot access before initialization" error.
vi.mock('@/api/h5p', async () => {
  const actual = await vi.importActual<typeof h5pApi>('@/api/h5p')
  const content = {
    id: 1,
    public_id: 'a'.repeat(32),
    owner_id: 1,
    title: 'Interactive Quiz',
    library: 'H5P.QuestionSet 1.20',
    size_bytes: 12345,
    status: 'ready' as const,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
  return {
    ...actual,
    listH5PContents: vi.fn().mockResolvedValue({ contents: [content], count: 1 }),
    submitH5PResult: vi.fn().mockResolvedValue({
      content_public_id: content.public_id,
      user_id: 1,
      score: null,
      max_score: null,
      completed: true,
      updated_at: new Date().toISOString(),
    }),
  }
})

const CONTENT_A: h5pApi.H5PContent = {
  id: 1,
  public_id: 'a'.repeat(32),
  owner_id: 1,
  title: 'Interactive Quiz',
  library: 'H5P.QuestionSet 1.20',
  size_bytes: 12345,
  status: 'ready',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}

const submitH5PResultMock = h5pApi.submitH5PResult as unknown as ReturnType<typeof vi.fn>

afterEach(() => cleanup())
beforeEach(() => {
  submitH5PResultMock.mockClear()
})

describe('H5PPicker preview modal (spec B7)', () => {
  it('shows a Preview button once a ready content item is selected', async () => {
    render(<H5PPicker value={CONTENT_A.id} onChange={vi.fn()} />)
    await waitFor(() => expect(screen.getByText(/Selected: Interactive Quiz/)).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /preview/i })).toBeInTheDocument()
  })

  it('opens a modal rendering H5PLesson with previewOnly when Preview is clicked, and it never calls submitH5PResult', async () => {
    const user = userEvent.setup()
    render(<H5PPicker value={CONTENT_A.id} onChange={vi.fn()} />)
    await waitFor(() => expect(screen.getByText(/Selected: Interactive Quiz/)).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /preview/i }))

    // The modal renders H5PLesson's sandboxed iframe pointed at the
    // selected content's public_id.
    const iframe = await screen.findByTitle('Interactive Quiz')
    expect(iframe.getAttribute('sandbox')).toBe('allow-scripts')
    expect(iframe.getAttribute('src')).toBe(`/h5p-player.html?content=${CONTENT_A.public_id}`)

    // Simulate the player reporting a result while in preview — previewOnly
    // must suppress the POST entirely (no advisory-result side effect from
    // an instructor just previewing their own content).
    const contentWindow = (iframe as HTMLIFrameElement).contentWindow
    const event = new MessageEvent('message', {
      data: { type: 'h5p-result', score: 10, maxScore: 10, completed: true },
      source: contentWindow as Window,
    })
    act(() => { window.dispatchEvent(event) })
    await new Promise((r) => setTimeout(r, 10))
    expect(submitH5PResultMock).not.toHaveBeenCalled()
  })

  it('closes the modal via the close button', async () => {
    const user = userEvent.setup()
    render(<H5PPicker value={CONTENT_A.id} onChange={vi.fn()} />)
    await waitFor(() => expect(screen.getByText(/Selected: Interactive Quiz/)).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /preview/i }))
    await screen.findByTitle('Interactive Quiz')

    await user.click(screen.getByRole('button', { name: /close preview/i }))
    expect(screen.queryByTitle('Interactive Quiz')).not.toBeInTheDocument()
  })
})
