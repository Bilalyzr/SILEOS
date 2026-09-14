/**
 * I-H4 — instructor H5P Library page. DELETE /h5p/{public_id} (h5p.py:372,
 * 409-guarded while attached) and api/h5p.ts's deleteH5PContent existed
 * with zero UI callers; there was no H5P management page at all.
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as h5pApi from '@/api/h5p'
import InstructorH5PLibraryPage from '../h5p-library'

vi.mock('@/api/h5p', async (importOriginal) => {
  const actual = await importOriginal<typeof h5pApi>()
  return {
    ...actual,
    listH5PContents: vi.fn(),
    deleteH5PContent: vi.fn(),
    uploadAndFinalizeH5P: vi.fn(),
  }
})

vi.mock('@/components/h5p/H5PLesson', () => ({
  H5PLesson: ({ contentId }: { contentId: string }) => <div data-testid="h5p-preview" data-id={contentId} />,
}))

vi.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: vi.fn(), error: vi.fn() },
}))

import toast from 'react-hot-toast'

const contents: h5pApi.H5PContent[] = [
  {
    id: 1, public_id: 'pub-loose', owner_id: 9, title: 'Loose Package', library: 'H5P.InteractiveVideo 1.22',
    size_bytes: 2_500_000, status: 'ready', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
    attached_lesson_count: 0,
  },
  {
    id: 2, public_id: 'pub-attached', owner_id: 9, title: 'Attached Package', library: 'H5P.CoursePresentation 1.24',
    size_bytes: 512, status: 'ready', created_at: '2026-01-02T00:00:00Z', updated_at: '2026-01-02T00:00:00Z',
    attached_lesson_count: 2,
  },
]

function renderPage() {
  return render(
    <MemoryRouter>
      <InstructorH5PLibraryPage />
    </MemoryRouter>
  )
}

describe('InstructorH5PLibraryPage — I-H4', () => {
  beforeEach(() => {
    vi.mocked(h5pApi.listH5PContents).mockReset().mockResolvedValue({ contents, count: 2 })
    vi.mocked(h5pApi.deleteH5PContent).mockReset()
    vi.mocked(h5pApi.uploadAndFinalizeH5P).mockReset()
    vi.mocked(toast.error).mockReset()
  })

  it('lists uploads with title, status, size and attached count', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Loose Package')).toBeInTheDocument())
    expect(screen.getByText('Attached Package')).toBeInTheDocument()
    expect(screen.getByText('2.4 MB')).toBeInTheDocument()
    expect(screen.getByText('2 lessons')).toBeInTheDocument()
  })

  it('deletes an unattached package after confirm and removes the row', async () => {
    vi.mocked(h5pApi.deleteH5PContent).mockResolvedValue({ success: true, public_id: 'pub-loose' })
    renderPage()
    await waitFor(() => expect(screen.getByText('Loose Package')).toBeInTheDocument())

    fireEvent.click(screen.getByLabelText('Delete Loose Package'))
    await waitFor(() => expect(screen.getByText('Delete this package?')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(h5pApi.deleteH5PContent).toHaveBeenCalledWith('pub-loose'))
    await waitFor(() => expect(screen.queryByText('Loose Package')).not.toBeInTheDocument())
  })

  it('surfaces the 409 detail when the package is still attached', async () => {
    const detail = 'Cannot delete: 2 lesson(s) still reference this content. Remove or repoint those lessons first.'
    vi.mocked(h5pApi.deleteH5PContent).mockRejectedValue({ response: { status: 409, data: { detail } } })
    renderPage()
    await waitFor(() => expect(screen.getByText('Attached Package')).toBeInTheDocument())

    fireEvent.click(screen.getByLabelText('Delete Attached Package'))
    await waitFor(() => expect(screen.getByText(/still attached to 2 lesson/i)).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith(detail, expect.anything()))
    expect(screen.getByText('Attached Package')).toBeInTheDocument()
  })

  it('uploads a package via uploadAndFinalizeH5P and refreshes the list', async () => {
    vi.mocked(h5pApi.uploadAndFinalizeH5P).mockResolvedValue(contents[0])
    renderPage()
    await waitFor(() => expect(screen.getByText('Loose Package')).toBeInTheDocument())

    const file = new File(['zip'], 'quiz.h5p', { type: 'application/zip' })
    fireEvent.change(screen.getByTestId('h5p-library-upload-input'), { target: { files: [file] } })

    await waitFor(() => expect(h5pApi.uploadAndFinalizeH5P).toHaveBeenCalledWith(
      file, expect.objectContaining({ title: 'quiz' })
    ))
    await waitFor(() => expect(h5pApi.listH5PContents).toHaveBeenCalledTimes(2))
  })

  it('rejects a non-.h5p/.zip file client-side', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Loose Package')).toBeInTheDocument())

    const file = new File(['x'], 'notes.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByTestId('h5p-library-upload-input'), { target: { files: [file] } })

    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    expect(h5pApi.uploadAndFinalizeH5P).not.toHaveBeenCalled()
  })

  it('opens the sandboxed preview for a ready package', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Loose Package')).toBeInTheDocument())

    fireEvent.click(screen.getByLabelText('Preview Loose Package'))
    await waitFor(() => expect(screen.getByTestId('h5p-preview').getAttribute('data-id')).toBe('pub-loose'))
  })
})
