/**
 * S-H1 — wishlist heart was `// TODO: Implement wishlist logic` (a local
 * toggle only). POST/DELETE /wishlist already existed (wishlist.py:45,94)
 * with zero UI callers. Wires the heart to the real endpoints with
 * optimistic UI + rollback on failure.
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockApi = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
}))

vi.mock('@/api/axios', () => ({ api: mockApi }))

vi.mock('@/hooks/use-auth', () => ({
  useAuth: () => ({ isAuthenticated: true, user: { id: 9, role: 'student' } }),
}))

vi.mock('@/hooks/use-seo', () => ({ useSEO: () => {} }))
vi.mock('@/store/course', () => ({ useCourseStore: () => ({}) }))

vi.mock('react-hot-toast', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/components/video/video-player', () => ({
  VideoPlayer: () => null,
}))

import { CourseDetailPage } from '../course-detail'

const courseFixture = {
  id: 55,
  title: 'Advanced TypeScript',
  slug: 'advanced-typescript',
  content: '<p>Learn TS</p>',
  excerpt: 'Learn TS',
  price: 999,
  sale_price: 0,
  level: 'intermediate',
  thumbnail: '/thumb.jpg',
  intro_video: '',
  rating: 4.5,
  stats: { duration: 120, students: 10, lessons: 5 },
  instructor: { id: 3, name: 'Instructor X', avatar: '' },
  lessons: [],
  is_enrolled: false,
  status: 'publish',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/courses/55']}>
      <Routes>
        <Route path="/courses/:id" element={<CourseDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('CourseDetailPage — S-H1 wishlist', () => {
  beforeEach(() => {
    mockApi.get.mockReset().mockImplementation((url: string) => {
      if (url === '/wishlist') {
        return Promise.resolve({ data: { courses: [], total: 0 } })
      }
      if (url.includes('/courses?')) {
        return Promise.resolve({ data: { courses: [] } })
      }
      return Promise.resolve({ data: courseFixture })
    })
    mockApi.post.mockReset().mockResolvedValue({ data: { message: 'ok', wishlist_item_id: 1 } })
    mockApi.delete.mockReset().mockResolvedValue({ data: { message: 'ok' } })
  })

  it('starts unfilled and adds to wishlist via POST /wishlist on click', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Wishlist')).toBeInTheDocument())

    fireEvent.click(screen.getByText('Wishlist').closest('button')!)

    await waitFor(() => expect(mockApi.post).toHaveBeenCalledWith('/wishlist', { course_id: 55 }))
  })

  it('reflects existing wishlist membership on load', async () => {
    mockApi.get.mockImplementation((url: string) => {
      if (url === '/wishlist') {
        return Promise.resolve({ data: { courses: [{ id: 55 }], total: 1 } })
      }
      if (url.includes('/courses?')) {
        return Promise.resolve({ data: { courses: [] } })
      }
      return Promise.resolve({ data: courseFixture })
    })

    renderPage()
    await waitFor(() => expect(screen.getByText('Wishlist')).toBeInTheDocument())

    const heartButton = screen.getByText('Wishlist').closest('button')!
    await waitFor(() => expect(heartButton.querySelector('.fill-current')).toBeTruthy())
  })

  it('removes from wishlist via DELETE when already wishlisted', async () => {
    mockApi.get.mockImplementation((url: string) => {
      if (url === '/wishlist') {
        return Promise.resolve({ data: { courses: [{ id: 55 }], total: 1 } })
      }
      if (url.includes('/courses?')) {
        return Promise.resolve({ data: { courses: [] } })
      }
      return Promise.resolve({ data: courseFixture })
    })

    renderPage()
    await waitFor(() => expect(screen.getByText('Wishlist')).toBeInTheDocument())
    const heartButton = screen.getByText('Wishlist').closest('button')!
    await waitFor(() => expect(heartButton.querySelector('.fill-current')).toBeTruthy())

    fireEvent.click(heartButton)

    await waitFor(() => expect(mockApi.delete).toHaveBeenCalledWith('/wishlist/55'))
  })

  it('rolls back the optimistic UI state when the request fails', async () => {
    mockApi.post.mockRejectedValue({ response: { data: { detail: 'boom' } } })

    renderPage()
    await waitFor(() => expect(screen.getByText('Wishlist')).toBeInTheDocument())
    const heartButton = screen.getByText('Wishlist').closest('button')!

    fireEvent.click(heartButton)

    await waitFor(() => expect(mockApi.post).toHaveBeenCalled())
    await waitFor(() => expect(heartButton.querySelector('.fill-current')).toBeFalsy())
  })
})
