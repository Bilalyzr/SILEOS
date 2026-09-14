/**
 * I-H5 — instructor can unpublish their own course. api/course.ts's
 * unpublishCourse (PATCH /courses/{id}/unpublish) already existed and the
 * backend already allows the owning instructor (courses.py:936-937), but
 * the instructor courses page had no button to reach it.
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockApi = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}))

vi.mock('@/api/axios', () => ({ api: mockApi }))

const currentUser = { id: 9, role: 'instructor' }

vi.mock('@/store/auth', () => {
  const store: any = () => ({ accessToken: 'tok' })
  store.getState = () => ({ user: currentUser, accessToken: 'tok' })
  return { useAuthStore: store }
})

vi.mock('react-hot-toast', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

import { InstructorCourses } from '../courses'

const ownedPublishedCourse = {
  id: 1,
  post_title: 'My Live Course',
  post_excerpt: 'desc',
  course_thumbnail: '/thumb.jpg',
  post_status: 'publish',
  total_enrollments: 0,
  average_rating: 0,
  course_price: 100,
  course_sale_price: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
  course_category: 'Dev',
  course_duration: '2h',
  instructor: { id: 9, name: 'Me' },
}

function renderPage() {
  return render(
    <MemoryRouter>
      <InstructorCourses />
    </MemoryRouter>
  )
}

describe('InstructorCourses — I-H5 unpublish', () => {
  beforeEach(() => {
    mockApi.get.mockReset().mockResolvedValue({
      data: { courses: [ownedPublishedCourse], total: 1, total_pages: 1 },
    })
    mockApi.patch.mockReset().mockResolvedValue({ data: { message: 'ok', course_id: 1, status: 'draft' } })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  it('shows an Unpublish action for the owner\'s own published course', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('My Live Course')).toBeInTheDocument())
    expect(screen.getByText('Unpublish')).toBeInTheDocument()
  })

  it('calls PATCH /courses/{id}/unpublish and flips the status chip after confirm', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('My Live Course')).toBeInTheDocument())

    fireEvent.click(screen.getByText('Unpublish'))

    await waitFor(() => expect(mockApi.patch).toHaveBeenCalledWith('/courses/1/unpublish'))
    // Badge text is ambiguous with the "Draft" filter <option>; scope to
    // elements that aren't a select option (the status chip is a <div>).
    await waitFor(() => {
      const matches = screen.getAllByText('Draft').filter((el) => el.tagName !== 'OPTION')
      expect(matches.length).toBeGreaterThan(0)
    })
  })

  it('does nothing when the confirm dialog is dismissed', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderPage()
    await waitFor(() => expect(screen.getByText('My Live Course')).toBeInTheDocument())

    fireEvent.click(screen.getByText('Unpublish'))

    await new Promise((r) => setTimeout(r, 0))
    expect(mockApi.patch).not.toHaveBeenCalled()
  })
})
