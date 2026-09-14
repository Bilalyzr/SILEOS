/**
 * M-12 — layout Footer's newsletter form had a `// TODO: Implement
 * newsletter subscription` onSubmit that only cleared the field.
 * POST /blog/newsletter/subscribe already existed (blog.py:721).
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockApi = vi.hoisted(() => ({ post: vi.fn() }))
vi.mock('@/api/axios', () => ({ api: mockApi }))

vi.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: vi.fn(), error: vi.fn() },
}))

import toast from 'react-hot-toast'
import { Footer } from '../footer'

function renderFooter() {
  return render(
    <MemoryRouter>
      <Footer />
    </MemoryRouter>
  )
}

describe('Footer newsletter — M-12', () => {
  beforeEach(() => {
    mockApi.post.mockReset()
  })

  it('submits a valid email to POST /blog/newsletter/subscribe', async () => {
    mockApi.post.mockResolvedValue({ data: { success: true } })
    renderFooter()

    fireEvent.change(screen.getByPlaceholderText('Enter your email'), {
      target: { value: 'footer-reader@example.com' },
    })
    fireEvent.click(screen.getByText('Subscribe'))

    await waitFor(() => expect(mockApi.post).toHaveBeenCalledWith(
      '/blog/newsletter/subscribe', { email: 'footer-reader@example.com' }
    ))
    await waitFor(() => expect(toast.success).toHaveBeenCalled())
  })

  it('clears the input after a successful subscribe', async () => {
    mockApi.post.mockResolvedValue({ data: { success: true } })
    renderFooter()

    const input = screen.getByPlaceholderText('Enter your email') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'footer-reader2@example.com' } })
    fireEvent.click(screen.getByText('Subscribe'))

    await waitFor(() => expect(input.value).toBe(''))
  })

  it('surfaces a server error via toast and keeps the typed email', async () => {
    mockApi.post.mockRejectedValue({ response: { data: { detail: 'Invalid email address' } } })
    renderFooter()

    const input = screen.getByPlaceholderText('Enter your email') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'footer-reader3@example.com' } })
    fireEvent.click(screen.getByText('Subscribe'))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Invalid email address'))
    expect(input.value).toBe('footer-reader3@example.com')
  })
})
