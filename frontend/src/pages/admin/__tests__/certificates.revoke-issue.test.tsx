/**
 * A-H5 — admin certificate revoke/issue on /admin/certificates. Both
 * backend routes already existed (certificates.py:1790 issue, :1838
 * revoke) and internshipApi already wrapped them, but the only UI callers
 * were on the Internships roster page. This page had none.
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockApi = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}))

vi.mock('@/api/axios', () => ({ api: mockApi }))

vi.mock('@/api/certificateDesigner', () => ({
  listDesignerTemplates: vi.fn().mockResolvedValue([]),
  errorDetail: (_err: any, fallback: string) => fallback,
}))

const mockInternshipApi = vi.hoisted(() => ({
  adminRevokeCert: vi.fn(),
  adminIssueCertForEnrollment: vi.fn(),
}))
vi.mock('@/api/internship', () => ({ internshipApi: mockInternshipApi }))

vi.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: vi.fn(), error: vi.fn() },
}))

import { AdminCertificates } from '../certificates'

const certFixture = {
  id: 77,
  student_name: 'Jane Doe',
  student_email: 'jane@example.com',
  course_title: 'Intro to Python',
  course_id: 5,
  certificate_id: 'CERT-77',
  secure_certificate_id: 'sec-77',
  certificate_hash: 'hash-77',
  issue_date: '2026-01-01T00:00:00Z',
  completion_date: '2026-01-01T00:00:00Z',
  grade: 95,
}

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminCertificates />
    </MemoryRouter>
  )
}

describe('AdminCertificates — A-H5 revoke/issue', () => {
  beforeEach(() => {
    mockApi.get.mockReset().mockResolvedValue({ data: [certFixture] })
    mockInternshipApi.adminRevokeCert.mockReset()
    mockInternshipApi.adminIssueCertForEnrollment.mockReset()
  })

  it('revokes a certificate with a reason prompt and confirm', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('Fraudulent submission')
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockInternshipApi.adminRevokeCert.mockResolvedValue({ message: 'ok' })

    renderPage()
    await waitFor(() => expect(screen.getByText('Jane Doe')).toBeInTheDocument())

    fireEvent.click(screen.getByTitle('Revoke certificate'))

    await waitFor(() => expect(mockInternshipApi.adminRevokeCert).toHaveBeenCalledWith(
      77, 'Fraudulent submission'
    ))
  })

  it('does not revoke when the reason prompt is cancelled', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue(null)

    renderPage()
    await waitFor(() => expect(screen.getByText('Jane Doe')).toBeInTheDocument())

    fireEvent.click(screen.getByTitle('Revoke certificate'))

    await new Promise((r) => setTimeout(r, 0))
    expect(mockInternshipApi.adminRevokeCert).not.toHaveBeenCalled()
  })

  it('issues a certificate for an enrollment via the standalone action', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('42')
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockInternshipApi.adminIssueCertForEnrollment.mockResolvedValue({ certificate_id: 99 })

    renderPage()
    await waitFor(() => expect(screen.getByText('Jane Doe')).toBeInTheDocument())

    fireEvent.click(screen.getByText('Issue certificate for enrollment'))

    await waitFor(() => expect(mockInternshipApi.adminIssueCertForEnrollment).toHaveBeenCalledWith(42, true))
  })

  it('rejects a non-numeric enrollment id without calling the API', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('not-a-number')

    renderPage()
    await waitFor(() => expect(screen.getByText('Jane Doe')).toBeInTheDocument())

    fireEvent.click(screen.getByText('Issue certificate for enrollment'))

    await new Promise((r) => setTimeout(r, 0))
    expect(mockInternshipApi.adminIssueCertForEnrollment).not.toHaveBeenCalled()
  })
})
