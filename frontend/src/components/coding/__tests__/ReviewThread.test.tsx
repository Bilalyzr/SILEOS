import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, waitFor, fireEvent } from '@testing-library/react'
import { ReviewThread } from '../ReviewThread'
import * as reviewApi from '@/api/codingReview'

vi.mock('@/api/codingReview', async () => {
  const actual = await vi.importActual<typeof reviewApi>('@/api/codingReview')
  return {
    ...actual,
    codingReviewAPI: {
      ...actual.codingReviewAPI,
      comments: vi.fn(),
      addComment: vi.fn(),
      resolve: vi.fn(),
    },
  }
})

const api = reviewApi.codingReviewAPI as unknown as Record<string, ReturnType<typeof vi.fn>>

const source = 'a, b = map(int, input().split())\nprint(a + b)'

describe('ReviewThread', () => {
  beforeEach(() => {
    api.comments.mockReset()
    api.addComment.mockReset()
    api.resolve.mockReset()
    api.comments.mockResolvedValue([
      {
        id: 1,
        submission_id: 9,
        line: 2,
        body: 'Use an f-string here.',
        status: 'open',
        author_name: 'Sasha Tutor',
        author_is_staff: true,
        created_at: null,
        resolved_at: null,
      },
    ])
  })

  afterEach(() => cleanup())

  it('shows the code and the comment on its line', async () => {
    render(<ReviewThread submissionId={9} source={source} />)
    await waitFor(() => expect(screen.getByText('Use an f-string here.')).toBeInTheDocument())
    expect(screen.getByText('print(a + b)')).toBeInTheDocument()
    expect(screen.getByText(/Sasha Tutor · staff/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Resolve' })).not.toBeInTheDocument()
  })

  it('lets a learner add a comment on the chosen line', async () => {
    api.addComment.mockResolvedValue({
      id: 2,
      submission_id: 9,
      line: 1,
      body: 'Why map?',
      status: 'open',
      author_name: 'Learner',
      author_is_staff: false,
      created_at: null,
      resolved_at: null,
    })
    render(<ReviewThread submissionId={9} source={source} />)
    await waitFor(() => expect(api.comments).toHaveBeenCalled())
    fireEvent.click(screen.getByRole('button', { name: 'Comment on line 1' }))
    fireEvent.change(screen.getByLabelText('Comment'), { target: { value: 'Why map?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add comment' }))
    await waitFor(() => expect(api.addComment).toHaveBeenCalledWith(9, 1, 'Why map?'))
    await waitFor(() => expect(screen.getByText('Why map?')).toBeInTheDocument())
  })

  it('offers resolve to course editors', async () => {
    render(<ReviewThread submissionId={9} source={source} isEditor />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Resolve' })).toBeInTheDocument())
  })
})
