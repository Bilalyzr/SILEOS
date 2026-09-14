/**
 * S-H5 — recording playback page. The "Watch recording" button used to
 * link to the join page (no recording handling); the playback endpoint
 * (live_class_recordings.py:101) was never fetched by any UI.
 */
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as liveClassesApi from '@/api/liveClasses'
import StudentLiveClassRecordingPage from '../live-class-recording'

vi.mock('@/api/liveClasses', async (importOriginal) => {
  const actual = await importOriginal<typeof liveClassesApi>()
  return {
    ...actual,
    getLiveClass: vi.fn(),
    fetchRecordingPlayback: vi.fn(),
  }
})

vi.mock('@/components/video/video-player', () => ({
  VideoPlayer: ({ src }: { src: string }) => <div data-testid="video-player" data-src={src} />,
}))

const endedClass: liveClassesApi.LiveClassOut = {
  id: 202,
  schedule_id: null,
  course_id: 5,
  lesson_id: null,
  instructor_id: 9,
  title: 'Week 2 Recap',
  description: null,
  scheduled_start: '2026-08-01T10:00:00.000Z',
  scheduled_end: '2026-08-01T11:00:00.000Z',
  timezone: 'Asia/Kolkata',
  room_name: 'room-202',
  status: 'ended',
  started_at: '2026-08-01T10:00:00.000Z',
  ended_at: '2026-08-01T11:00:00.000Z',
  live_participants: 0,
  recording_video_id: 'vid-202',
  recording_status: 'available',
  settings: {},
  server_ts: '2026-08-01T11:05:00.000Z',
  my_attendance: null,
  can_start: false,
  join_opens_at: '2026-08-01T09:45:00.000Z',
}

function renderAt(classId: number) {
  return render(
    <MemoryRouter initialEntries={[`/student/live-classes/${classId}/recording`]}>
      <Routes>
        <Route path="/student/live-classes/:id/recording" element={<StudentLiveClassRecordingPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('StudentLiveClassRecordingPage', () => {
  beforeEach(() => {
    vi.mocked(liveClassesApi.getLiveClass).mockReset()
    vi.mocked(liveClassesApi.fetchRecordingPlayback).mockReset()
  })

  it('fetches and renders the signed playback URL for an available recording', async () => {
    vi.mocked(liveClassesApi.getLiveClass).mockResolvedValue(endedClass)
    vi.mocked(liveClassesApi.fetchRecordingPlayback).mockResolvedValue({
      class_id: 202, video_id: 'vid-202', hls_url: 'https://cdn.example/vid-202.m3u8?token=abc',
      expires_in: 3600, signed: true,
    })

    renderAt(202)

    await waitFor(() => expect(screen.getByText('Week 2 Recap')).toBeInTheDocument())
    const player = await screen.findByTestId('video-player')
    expect(player.getAttribute('data-src')).toBe('https://cdn.example/vid-202.m3u8?token=abc')
  })

  it('shows a clear empty state when there is no recording (404)', async () => {
    vi.mocked(liveClassesApi.getLiveClass).mockResolvedValue({ ...endedClass, recording_video_id: null })
    vi.mocked(liveClassesApi.fetchRecordingPlayback).mockRejectedValue({
      response: { status: 404, data: { detail: 'No recording is available for this class' } },
    })

    renderAt(202)

    await waitFor(() => expect(screen.getByText('No recording available')).toBeInTheDocument())
    expect(screen.queryByTestId('video-player')).not.toBeInTheDocument()
  })

  it('shows an error state with retry on a non-404 failure', async () => {
    vi.mocked(liveClassesApi.getLiveClass).mockResolvedValue(endedClass)
    vi.mocked(liveClassesApi.fetchRecordingPlayback).mockRejectedValue({
      response: { status: 403, data: { detail: 'You do not have access to this class' } },
    })

    renderAt(202)

    await waitFor(() => expect(screen.getByText('You do not have access to this class')).toBeInTheDocument())
  })
})
