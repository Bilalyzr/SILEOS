import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as liveClassesApi from '@/api/liveClasses'
import InstructorLiveClassesPage from '../live-classes'

// I-H1: edit/cancel actions for scheduled live classes.

vi.mock('@/api/liveClasses', async (importOriginal) => {
  const actual = await importOriginal<typeof liveClassesApi>()
  return {
    ...actual,
    listLiveClasses: vi.fn(),
    startLiveClass: vi.fn(),
    updateLiveClass: vi.fn(),
    cancelLiveClass: vi.fn(),
    fetchCalendarIcs: vi.fn(),
  }
})

vi.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: vi.fn(), error: vi.fn() },
}))

const scheduledClass: liveClassesApi.LiveClassOut = {
  id: 101,
  schedule_id: null,
  course_id: 5,
  lesson_id: null,
  instructor_id: 9,
  title: 'Week 3 Live Q&A',
  description: 'Bring your questions',
  scheduled_start: '2026-09-10T10:00:00.000Z',
  scheduled_end: '2026-09-10T11:00:00.000Z',
  timezone: 'Asia/Kolkata',
  room_name: 'room-101',
  status: 'scheduled',
  started_at: null,
  ended_at: null,
  live_participants: 0,
  recording_video_id: null,
  recording_status: 'none',
  settings: {},
  server_ts: '2026-09-01T00:00:00.000Z',
  my_attendance: null,
  can_start: true,
  join_opens_at: '2026-09-10T09:45:00.000Z',
}

function renderPage() {
  return render(
    <MemoryRouter>
      <InstructorLiveClassesPage />
    </MemoryRouter>
  )
}

describe('InstructorLiveClassesPage — I-H1 edit/cancel', () => {
  beforeEach(() => {
    vi.mocked(liveClassesApi.listLiveClasses).mockReset().mockResolvedValue({
      items: [scheduledClass], total: 1, page: 1, page_size: 50,
    })
    vi.mocked(liveClassesApi.updateLiveClass).mockReset()
    vi.mocked(liveClassesApi.cancelLiveClass).mockReset()
  })

  it('shows Edit and Cancel actions for a scheduled class', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Week 3 Live Q&A')).toBeInTheDocument())
    expect(screen.getByText('Edit')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('opens the edit modal and saves changes via updateLiveClass', async () => {
    vi.mocked(liveClassesApi.updateLiveClass).mockResolvedValue({
      ...scheduledClass, title: 'Updated title',
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('Week 3 Live Q&A')).toBeInTheDocument())

    fireEvent.click(screen.getByText('Edit'))
    await waitFor(() => expect(screen.getByText('Edit class')).toBeInTheDocument())

    const titleInput = screen.getByDisplayValue('Week 3 Live Q&A')
    fireEvent.change(titleInput, { target: { value: 'Updated title' } })
    fireEvent.click(screen.getByText('Save changes'))

    await waitFor(() => expect(liveClassesApi.updateLiveClass).toHaveBeenCalledWith(
      101,
      expect.objectContaining({ title: 'Updated title' })
    ))
  })

  it('confirms and cancels a scheduled class via cancelLiveClass', async () => {
    vi.mocked(liveClassesApi.cancelLiveClass).mockResolvedValue({
      ...scheduledClass, status: 'cancelled',
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('Week 3 Live Q&A')).toBeInTheDocument())

    fireEvent.click(screen.getByText('Cancel'))
    await waitFor(() => expect(screen.getByText('Cancel this class?')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: 'Cancel class' }))

    await waitFor(() => expect(liveClassesApi.cancelLiveClass).toHaveBeenCalledWith(101))
  })

  it('does not show Edit/Cancel actions for an ended class', async () => {
    vi.mocked(liveClassesApi.listLiveClasses).mockResolvedValue({
      items: [{ ...scheduledClass, status: 'ended' }], total: 1, page: 1, page_size: 50,
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('Week 3 Live Q&A')).toBeInTheDocument())
    expect(screen.queryByText('Edit')).not.toBeInTheDocument()
    expect(screen.queryByText('Cancel')).not.toBeInTheDocument()
  })
})

describe('InstructorLiveClassesPage — M-11 add to calendar', () => {
  beforeEach(() => {
    vi.mocked(liveClassesApi.listLiveClasses).mockReset().mockResolvedValue({
      items: [scheduledClass], total: 1, page: 1, page_size: 50,
    })
    vi.mocked(liveClassesApi.fetchCalendarIcs).mockReset()
  })

  it('downloads the .ics via fetchCalendarIcs (authenticated blob fetch)', async () => {
    const blob = new Blob(['BEGIN:VCALENDAR'], { type: 'text/calendar' })
    vi.mocked(liveClassesApi.fetchCalendarIcs).mockResolvedValue(blob)
    const createObjectURL = vi.fn().mockReturnValue('blob:mock-url')
    const revokeObjectURL = vi.fn()
    window.URL.createObjectURL = createObjectURL
    window.URL.revokeObjectURL = revokeObjectURL

    renderPage()
    await waitFor(() => expect(screen.getByText('Week 3 Live Q&A')).toBeInTheDocument())

    fireEvent.click(screen.getByText('Add to calendar'))

    await waitFor(() => expect(liveClassesApi.fetchCalendarIcs).toHaveBeenCalledWith(101))
    expect(createObjectURL).toHaveBeenCalledWith(blob)
  })

  it('does not show the calendar button for a non-scheduled class', async () => {
    vi.mocked(liveClassesApi.listLiveClasses).mockResolvedValue({
      items: [{ ...scheduledClass, status: 'ended' }], total: 1, page: 1, page_size: 50,
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('Week 3 Live Q&A')).toBeInTheDocument())
    expect(screen.queryByText('Add to calendar')).not.toBeInTheDocument()
  })
})
