/**
 * B11 — GET /blog/{slug} vs GET /blog/id/{post_id}: blog-detail.tsx used
 * to always call /blog/{routeParam} regardless of shape, so a legacy
 * numeric URL (/blog/42) hit the slug-only backend route and 404'd.
 *
 * Fix: when the route param is all digits, call /blog/id/{id} instead of
 * treating it as a literal slug. Mocks the api module at the boundary
 * (per the lesson-redesigned.game.test.tsx convention) and asserts only
 * which URL is requested for each param shape — the response payload
 * itself is a fixed fixture, not under test here.
 */
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockApi = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}))

vi.mock('@/api/axios', () => ({ api: mockApi }))

vi.mock('@/store/auth', () => ({
  useAuthStore: () => ({ user: null, isAuthenticated: false }),
}))

vi.mock('@/hooks/use-seo', () => ({
  useSEO: () => {},
}))

import { BlogDetailPage } from '../blog-detail'

const postFixture = {
  id: 42,
  title: 'Legacy Post',
  slug: 'legacy-post',
  content: '<p>hello</p>',
  excerpt: 'hello',
  featured_image: null,
  status: 'PUBLISHED',
  category: null,
  tags: null,
  view_count: 1,
  comment_count: 0,
  post_date: '2026-01-01T00:00:00Z',
  post_modified: '2026-01-01T00:00:00Z',
  author: { id: 1, name: 'Author', email: 'a@example.com' },
  related_course_ids: [],
  related_internship_ids: [],
  related_courses: [],
  related_internships: [],
}

function renderPage(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/blog/:slug" element={<BlogDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('BlogDetailPage — numeric-id resolution (B11)', () => {
  beforeEach(() => {
    mockApi.get.mockReset()
    mockApi.get.mockImplementation((url: string) => {
      if (url.includes('/comments')) return Promise.resolve({ data: [] })
      return Promise.resolve({ data: postFixture })
    })
  })

  it('calls /blog/id/{id} for an all-digits route param', async () => {
    renderPage('/blog/42')
    await waitFor(() => expect(screen.getByText('Legacy Post')).toBeInTheDocument())
    expect(mockApi.get).toHaveBeenCalledWith('/blog/id/42')
  })

  it('calls /blog/{slug} for a non-numeric route param', async () => {
    renderPage('/blog/legacy-post')
    await waitFor(() => expect(screen.getByText('Legacy Post')).toBeInTheDocument())
    expect(mockApi.get).toHaveBeenCalledWith('/blog/legacy-post')
  })

  it('treats a mixed alphanumeric slug as a slug, not a numeric id', async () => {
    renderPage('/blog/post-42')
    await waitFor(() => expect(screen.getByText('Legacy Post')).toBeInTheDocument())
    expect(mockApi.get).toHaveBeenCalledWith('/blog/post-42')
  })
})
