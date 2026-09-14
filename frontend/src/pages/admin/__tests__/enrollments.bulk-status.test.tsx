/**
 * M-2 — admin enrollments page: PUT /admin/enrollments/bulk-update
 * (admin.py) existed with zero UI callers. Adds multi-select + a bulk
 * status action. This page uses raw fetch (not the axios instance), so the
 * test stubs global.fetch and asserts on the request it makes.
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/utils/auth-helper', () => ({ getAuthToken: () => 'tok' }))
vi.mock('@/components/admin/ExportImportPanel', () => ({ ExportImportPanel: () => null }))
vi.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: vi.fn(), error: vi.fn() },
}))

import toast from 'react-hot-toast'
import { AdminEnrollments } from '../enrollments'

const rows = [
  { id: 1, student_name: 'Ann', student_email: 'ann@x.io', course_title: 'C1', course_id: 5, enrollment_date: '2026-01-01T00:00:00Z', status: 'enrolled', progress: 10, completed_lessons: 1, total_lessons: 10, completion_date: null },
  { id: 2, student_name: 'Bob', student_email: 'bob@x.io', course_title: 'C2', course_id: 6, enrollment_date: '2026-01-02T00:00:00Z', status: 'enrolled', progress: 50, completed_lessons: 5, total_lessons: 10, completion_date: null },
  { id: 3, student_name: 'Cid', student_email: 'cid@x.io', course_title: 'C3', course_id: 7, enrollment_date: '2026-01-03T00:00:00Z', status: 'completed', progress: 100, completed_lessons: 10, total_lessons: 10, completion_date: '2026-02-01T00:00:00Z' },
]

const fetchMock = vi.fn()

function jsonResponse(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) })
}

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminEnrollments />
    </MemoryRouter>
  )
}

describe('AdminEnrollments — M-2 bulk status', () => {
  beforeEach(() => {
    fetchMock.mockReset()
    fetchMock.mockImplementation((url: string) => {
      if (url.includes('/admin/enrollments/bulk-update')) return jsonResponse({ message: 'ok' })
      return jsonResponse(rows)
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the bulk action bar only once rows are selected', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Ann')).toBeInTheDocument())
    expect(screen.queryByTestId('bulk-action-bar')).not.toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Select enrollment 1'))
    expect(screen.getByTestId('bulk-action-bar')).toBeInTheDocument()
    expect(screen.getByText('1 selected')).toBeInTheDocument()
  })

  it('PUTs the selected ids to /admin/enrollments/bulk-update with the chosen status', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Ann')).toBeInTheDocument())

    fireEvent.click(screen.getByLabelText('Select enrollment 1'))
    fireEvent.click(screen.getByLabelText('Select enrollment 2'))
    fireEvent.change(screen.getByLabelText('Bulk status'), { target: { value: 'suspended' } })
    fireEvent.click(screen.getByText('Apply to selected'))

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => String(url).includes('/admin/enrollments/bulk-update'))
      expect(call).toBeTruthy()
      const [url, init] = call!
      expect(String(url)).toContain('status=suspended')
      expect(init.method).toBe('PUT')
      expect(JSON.parse(init.body)).toEqual([1, 2])
    })
    await waitFor(() => expect(toast.success).toHaveBeenCalled())
    // Selection clears and the list is refetched after success.
    await waitFor(() => expect(screen.queryByTestId('bulk-action-bar')).not.toBeInTheDocument())
  })

  it('select-all toggles every visible row', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Ann')).toBeInTheDocument())

    fireEvent.click(screen.getByLabelText('Select all visible enrollments'))
    expect(screen.getByText('3 selected')).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Select all visible enrollments'))
    expect(screen.queryByTestId('bulk-action-bar')).not.toBeInTheDocument()
  })

  it('surfaces a server error detail and keeps the selection', async () => {
    fetchMock.mockImplementation((url: string) => {
      if (url.includes('/admin/enrollments/bulk-update')) {
        return jsonResponse({ detail: 'Invalid status' }, false, 400)
      }
      return jsonResponse(rows)
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('Ann')).toBeInTheDocument())

    fireEvent.click(screen.getByLabelText('Select enrollment 3'))
    fireEvent.click(screen.getByText('Apply to selected'))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Invalid status'))
    expect(screen.getByTestId('bulk-action-bar')).toBeInTheDocument()
  })
})
