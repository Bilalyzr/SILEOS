/**
 * M-12 — Home footer's newsletter form was `onSubmit={(e) =>
 * e.preventDefault()}` only, never calling the backend.
 * POST /blog/newsletter/subscribe already existed (blog.py:721).
 * Imports just the NewsletterSection (exported for exactly this reason)
 * rather than mounting the whole THREE.js-heavy HomePage.
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockApi = vi.hoisted(() => ({ post: vi.fn() }))
vi.mock('@/api/axios', () => ({ api: mockApi }))

vi.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: vi.fn(), error: vi.fn() },
}))

import toast from 'react-hot-toast'
import { NewsletterSection } from '../Home'

describe('NewsletterSection — M-12', () => {
  beforeEach(() => {
    mockApi.post.mockReset()
  })

  it('submits a valid email to POST /blog/newsletter/subscribe', async () => {
    mockApi.post.mockResolvedValue({ data: { success: true, message: 'Subscribed successfully!' } })
    render(<NewsletterSection />)

    fireEvent.change(screen.getByPlaceholderText('Enter your email'), {
      target: { value: 'reader@example.com' },
    })
    fireEvent.click(screen.getByText('Subscribe'))

    await waitFor(() => expect(mockApi.post).toHaveBeenCalledWith(
      '/blog/newsletter/subscribe', { email: 'reader@example.com' }
    ))
    await waitFor(() => expect(toast.success).toHaveBeenCalled())
  })

  it('rejects an invalid email client-side without calling the API', async () => {
    const { container } = render(<NewsletterSection />)

    const input = screen.getByPlaceholderText('Enter your email') as HTMLInputElement
    // jsdom enforces native type=email/required validation on a real
    // click-triggered submit; fire the form's submit event directly so our
    // own isValidEmail() re-check (defense in depth against a bypassed or
    // stale native validation) is what's actually under test here.
    input.removeAttribute('required')
    input.setAttribute('type', 'text')

    fireEvent.change(input, { target: { value: 'not-an-email' } })
    const form = container.querySelector('form')!
    fireEvent.submit(form)

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Please enter a valid email address'))
    expect(mockApi.post).not.toHaveBeenCalled()
  })

  it('surfaces a server error via toast', async () => {
    mockApi.post.mockRejectedValue({ response: { data: { detail: 'Invalid email address' } } })
    render(<NewsletterSection />)

    fireEvent.change(screen.getByPlaceholderText('Enter your email'), {
      target: { value: 'reader2@example.com' },
    })
    fireEvent.click(screen.getByText('Subscribe'))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Invalid email address'))
  })
})
