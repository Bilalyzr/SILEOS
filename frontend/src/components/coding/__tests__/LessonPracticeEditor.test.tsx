import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AxiosError, AxiosHeaders } from 'axios'
import { codingAPI } from '@/api/coding'
import LessonPracticeEditor from '../LessonPracticeEditor'

vi.mock('@/api/coding', async () => {
  const actual = await vi.importActual<typeof import('@/api/coding')>('@/api/coding')
  return {
    ...actual,
    codingAPI: { ...actual.codingAPI, editorChallenges: vi.fn(), lessonBlocks: vi.fn(), saveLessonBlocks: vi.fn() },
  }
})

const challengesMock = codingAPI.editorChallenges as unknown as ReturnType<typeof vi.fn>
const blocksMock = codingAPI.lessonBlocks as unknown as ReturnType<typeof vi.fn>

function renderEditor() {
  return render(
    <MemoryRouter>
      <LessonPracticeEditor courseId={5} lessonId={126} />
    </MemoryRouter>,
  )
}

describe('LessonPracticeEditor', () => {
  beforeEach(() => {
    challengesMock.mockReset()
    blocksMock.mockReset()
    blocksMock.mockResolvedValue([])
  })

  afterEach(() => cleanup())

  it('offers New challenge in place and links to Coding Studio when none is published', async () => {
    challengesMock.mockResolvedValue([])
    renderEditor()
    const link = await screen.findByRole('link', { name: 'Coding Studio' })
    expect(link).toHaveAttribute('href', '/instructor/coding-studio?course=5')
    expect(screen.getByRole('button', { name: 'Add practice' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'New challenge' })).toBeEnabled()
  })

  it('shows the real reason when challenges cannot be loaded', async () => {
    const detail = 'Coding assessments belong to Utporul skill-development courses.'
    challengesMock.mockRejectedValue(
      new AxiosError('Unprocessable', '422', undefined, undefined, {
        status: 422,
        statusText: 'Unprocessable Entity',
        data: { detail },
        headers: {},
        config: { headers: new AxiosHeaders() },
      }),
    )
    renderEditor()
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(detail))
    expect(screen.queryByRole('link', { name: 'Coding Studio' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'New challenge' })).toBeDisabled()
  })
})
