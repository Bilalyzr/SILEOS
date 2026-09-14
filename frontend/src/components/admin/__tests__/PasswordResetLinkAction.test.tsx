/**
 * A-H3 UI — admin "Generate reset link" action. Backend route:
 * POST /admin/users/{id}/password-reset-link returns a one-time link once.
 * The component must show it once with a copy button and never offer any
 * way to type/set a password.
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
import { PasswordResetLinkAction } from '../PasswordResetLinkAction'

const LINK = 'https://lms.example/reset-password?token=abc.def.ghi'

describe('PasswordResetLinkAction — A-H3', () => {
  beforeEach(() => {
    mockApi.post.mockReset()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } })
  })

  it('POSTs to /admin/users/{id}/password-reset-link and shows the link once with a copy button', async () => {
    mockApi.post.mockResolvedValue({ data: { reset_link: LINK, user_id: 7, expires_in_hours: 1 } })
    render(<PasswordResetLinkAction userId={7} userName="Jane" />)

    fireEvent.click(screen.getByLabelText('Generate password reset link for Jane'))

    await waitFor(() => expect(mockApi.post).toHaveBeenCalledWith('/admin/users/7/password-reset-link'))
    const input = await screen.findByLabelText('Reset link') as HTMLInputElement
    expect(input.value).toBe(LINK)
    expect(input.readOnly).toBe(true)

    fireEvent.click(screen.getByText('Copy'))
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith(LINK))
    await waitFor(() => expect(screen.getByText('Copied')).toBeInTheDocument())
  })

  it('discards the link when the modal is closed (shown once)', async () => {
    mockApi.post.mockResolvedValue({ data: { reset_link: LINK } })
    render(<PasswordResetLinkAction userId={7} userName="Jane" compact />)

    fireEvent.click(screen.getByLabelText('Generate password reset link for Jane'))
    await screen.findByLabelText('Reset link')

    fireEvent.click(screen.getByText('Done'))
    expect(screen.queryByLabelText('Reset link')).not.toBeInTheDocument()
  })

  it('does nothing when the confirm is dismissed', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    render(<PasswordResetLinkAction userId={7} userName="Jane" />)

    fireEvent.click(screen.getByLabelText('Generate password reset link for Jane'))
    await new Promise((r) => setTimeout(r, 0))
    expect(mockApi.post).not.toHaveBeenCalled()
  })

  it('surfaces a server error via toast', async () => {
    mockApi.post.mockRejectedValue({ response: { data: { detail: 'User not found' } } })
    render(<PasswordResetLinkAction userId={999} userName="Ghost" />)

    fireEvent.click(screen.getByLabelText('Generate password reset link for Ghost'))
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('User not found'))
    expect(screen.queryByLabelText('Reset link')).not.toBeInTheDocument()
  })

  it('never renders a password input — admin cannot set a password directly', async () => {
    mockApi.post.mockResolvedValue({ data: { reset_link: LINK } })
    const { container } = render(<PasswordResetLinkAction userId={7} userName="Jane" />)

    fireEvent.click(screen.getByLabelText('Generate password reset link for Jane'))
    await screen.findByLabelText('Reset link')

    expect(container.querySelector('input[type="password"]')).toBeNull()
  })
})
