/**
 * S-H4 — student change-password. auth.py:939 (POST /auth/change-password)
 * and api/auth.ts's authAPI.changePassword already existed — only the
 * ADMIN settings page called them. Adds the same section to the student
 * settings page.
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/hooks/use-auth', () => ({
  useAuth: () => ({ user: { id: 9 }, fullName: 'Jane Student' }),
}))

vi.mock('@/components/dashboard/two-factor-section', () => ({
  TwoFactorSection: () => null,
}))

const mockChangePassword = vi.hoisted(() => vi.fn())
vi.mock('@/api/auth', () => ({
  authAPI: { changePassword: mockChangePassword },
}))

vi.mock('react-hot-toast', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

import { toast } from 'react-hot-toast'
import { SettingsPage } from '../settings'

const renderSettings = () => render(<MemoryRouter><SettingsPage /></MemoryRouter>)

describe('SettingsPage — S-H4 change password', () => {
  beforeEach(() => {
    mockChangePassword.mockReset()
    localStorage.clear()
  })

  it('renders a Change password section', () => {
    renderSettings()
    expect(screen.getAllByText('Change password').length).toBeGreaterThan(0)
    expect(screen.getByLabelText(/current password/i)).toBeInTheDocument()
  })

  it('calls authAPI.changePassword with valid matching passwords', async () => {
    mockChangePassword.mockResolvedValue(undefined)
    renderSettings()

    fireEvent.change(screen.getByLabelText(/current password/i), { target: { value: 'OldPass1' } })
    fireEvent.change(screen.getByLabelText(/^new password$/i), { target: { value: 'NewPass1' } })
    fireEvent.change(screen.getByLabelText(/confirm new password/i), { target: { value: 'NewPass1' } })

    fireEvent.click(screen.getByRole('button', { name: /change password/i }))

    await waitFor(() => expect(mockChangePassword).toHaveBeenCalledWith({
      currentPassword: 'OldPass1', newPassword: 'NewPass1',
    }))
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Password changed successfully'))
  })

  it('rejects mismatched passwords client-side without calling the API', async () => {
    renderSettings()

    fireEvent.change(screen.getByLabelText(/current password/i), { target: { value: 'OldPass1' } })
    fireEvent.change(screen.getByLabelText(/^new password$/i), { target: { value: 'NewPass1' } })
    fireEvent.change(screen.getByLabelText(/confirm new password/i), { target: { value: 'Different1' } })

    fireEvent.click(screen.getByRole('button', { name: /change password/i }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('New passwords do not match'))
    expect(mockChangePassword).not.toHaveBeenCalled()
  })

  it('rejects a weak password client-side (no uppercase) without calling the API', async () => {
    renderSettings()

    fireEvent.change(screen.getByLabelText(/current password/i), { target: { value: 'OldPass1' } })
    fireEvent.change(screen.getByLabelText(/^new password$/i), { target: { value: 'lowercase1' } })
    fireEvent.change(screen.getByLabelText(/confirm new password/i), { target: { value: 'lowercase1' } })

    fireEvent.click(screen.getByRole('button', { name: /change password/i }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith(
      'Password must contain at least one uppercase letter'
    ))
    expect(mockChangePassword).not.toHaveBeenCalled()
  })

  it('surfaces a server error via toast', async () => {
    mockChangePassword.mockRejectedValue({ response: { data: { detail: 'Incorrect current password' } } })
    renderSettings()

    fireEvent.change(screen.getByLabelText(/current password/i), { target: { value: 'WrongPass1' } })
    fireEvent.change(screen.getByLabelText(/^new password$/i), { target: { value: 'NewPass1' } })
    fireEvent.change(screen.getByLabelText(/confirm new password/i), { target: { value: 'NewPass1' } })

    fireEvent.click(screen.getByRole('button', { name: /change password/i }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Incorrect current password'))
  })
})
