import { api, apiRequest } from './axios'

// ---------------------------------------------------------------------------
// Types — mirror backend/app/schemas/live_class.py exactly (field names,
// optionality). No response envelope (deviations file item 2) — apiRequest<T>
// tolerates plain payloads, so these functions just return response.data.
// ---------------------------------------------------------------------------

export type LiveClassStatus = 'scheduled' | 'live' | 'ended' | 'cancelled'
export type RecordingStatus = 'none' | 'requested' | 'processing' | 'available' | 'failed'
export type PollStatusValue = 'draft' | 'active' | 'closed'

export interface LiveClassSettings {
  lobby_enabled: boolean
  start_muted: boolean
  allow_chat: boolean
  allow_share: boolean
  record: boolean
  attendance_threshold_pct: number
  // v2.0 §7.1 classification + §7.4 retention (WP5)
  purpose?: string | null
  mode?: string | null
  audience?: string | null
  recording_policy?: string | null
  retention_days?: number | null
}

export interface LiveClassOut {
  id: number
  schedule_id: number | null
  course_id: number
  lesson_id: number | null
  instructor_id: number
  title: string
  description: string | null
  scheduled_start: string
  scheduled_end: string
  timezone: string
  room_name: string
  status: LiveClassStatus
  started_at: string | null
  ended_at: string | null
  live_participants: number
  recording_video_id: string | null
  recording_status: RecordingStatus
  settings: Partial<LiveClassSettings> & Record<string, unknown>

  // Derived / request-time fields
  server_ts: string
  my_attendance: Record<string, unknown> | null
  can_start: boolean
  join_opens_at: string
}

export interface LiveClassListOut {
  items: LiveClassOut[]
  total: number
  page: number
  page_size: number
}

export interface LiveNowOut {
  classes: LiveClassOut[]
}

export interface JoinTokenOut {
  class_summary: LiveClassOut
  room_name: string
  jitsi_url: string
  jwt: string
  expires_in: number
}

export interface HeartbeatOut {
  accumulated_seconds: number
  delta: number
}

export interface PollOut {
  id: number
  class_id: number
  question: string
  options: string[]
  status: PollStatusValue
  show_results: boolean
  created_at: string
  activated_at: string | null
  closed_at: string | null
  tallies: number[] | null
  my_vote: number | null
}

export interface PollCreateIn {
  question: string
  options: string[]
  show_results?: boolean
}

export interface RecordingIntentOut {
  class_id: number
  recording_status: RecordingStatus
}

export interface RecordingPlaybackOut {
  class_id: number
  video_id: string
  hls_url: string
  expires_in: number | null
  signed: boolean
}

export interface AttendanceRowOut {
  user_id: number
  name: string
  email: string
  first_joined_at: string | null
  accumulated_minutes: number
  present: boolean | null
}

/** Mirrors backend/app/routers/live_class_attendance.py's local
 * AttendanceSummaryOut (response_model for GET .../attendance and
 * POST .../attendance/recompute) exactly — NOT a bare AttendanceRowOut[]. */
export interface AttendanceSummaryOut {
  rows: AttendanceRowOut[]
  total_participants: number
  present_count: number
  live_participants: number
}

export interface LiveClassCreateIn {
  course_id: number
  lesson_id?: number | null
  title: string
  description?: string | null
  scheduled_start: string
  duration_minutes: number
  timezone?: string
  recurrence_weekly?: string[] | null
  weeks?: number | null
  settings?: Partial<LiveClassSettings>
}

export interface LiveClassUpdateIn {
  title?: string
  description?: string | null
  scheduled_start?: string
  duration_minutes?: number
  timezone?: string
  settings?: Partial<LiveClassSettings>
}

export type LiveClassScope = 'upcoming' | 'past' | 'live' | `course:${number}`

// ---------------------------------------------------------------------------
// Scheduling / listing
// ---------------------------------------------------------------------------

export const listLiveClasses = (
  params: { scope?: LiveClassScope; page?: number; page_size?: number } = {}
): Promise<LiveClassListOut> =>
  apiRequest<LiveClassListOut>(api.get('/live/classes', { params }))

export const getLiveClass = (classId: number): Promise<LiveClassOut> =>
  apiRequest<LiveClassOut>(api.get(`/live/classes/${classId}`))

export const createLiveClass = (payload: LiveClassCreateIn): Promise<LiveClassOut[]> =>
  apiRequest<LiveClassOut[]>(api.post('/live/classes', payload))

export const updateLiveClass = (classId: number, payload: LiveClassUpdateIn): Promise<LiveClassOut> =>
  apiRequest<LiveClassOut>(api.patch(`/live/classes/${classId}`, payload))

export const cancelLiveClass = (classId: number): Promise<LiveClassOut> =>
  apiRequest<LiveClassOut>(api.delete(`/live/classes/${classId}`))

export const fetchLiveNow = (): Promise<LiveNowOut> =>
  apiRequest<LiveNowOut>(api.get('/live/live-now'))

/** Builds the authenticated .ics download URL for a class. The endpoint
 * requires the bearer token (added by the axios interceptor for XHR/fetch
 * calls made through `api`), so this is meant to be fetched via `api.get`
 * with `responseType: 'blob'` rather than used as a plain <a href>. */
export const icsUrl = (classId: number): string => `/live/classes/${classId}/calendar.ics`

export const fetchCalendarIcs = async (classId: number): Promise<Blob> => {
  const response = await api.get(icsUrl(classId), { responseType: 'blob' })
  return response.data
}

// ---------------------------------------------------------------------------
// Session (start / end / join-token / heartbeat)
// ---------------------------------------------------------------------------

export const startLiveClass = (classId: number): Promise<LiveClassOut> =>
  apiRequest<LiveClassOut>(api.post(`/live/classes/${classId}/start`))

export const endLiveClass = (classId: number): Promise<LiveClassOut> =>
  apiRequest<LiveClassOut>(api.post(`/live/classes/${classId}/end`))

export const requestJoinToken = (classId: number): Promise<JoinTokenOut> =>
  apiRequest<JoinTokenOut>(api.post(`/live/classes/${classId}/join-token`))

export const sendHeartbeat = (classId: number): Promise<HeartbeatOut> =>
  apiRequest<HeartbeatOut>(
    api.post(`/live/classes/${classId}/heartbeat`, { client_ts: new Date().toISOString() })
  )

// ---------------------------------------------------------------------------
// Polls
// ---------------------------------------------------------------------------

export const listPolls = (classId: number): Promise<PollOut[]> =>
  apiRequest<PollOut[]>(api.get(`/live/classes/${classId}/polls`))

export const createPoll = (classId: number, payload: PollCreateIn): Promise<PollOut> =>
  apiRequest<PollOut>(api.post(`/live/classes/${classId}/polls`, payload))

export const activatePoll = (classId: number, pollId: number): Promise<PollOut> =>
  apiRequest<PollOut>(api.post(`/live/classes/${classId}/polls/${pollId}/activate`))

export const closePoll = (classId: number, pollId: number): Promise<PollOut> =>
  apiRequest<PollOut>(api.post(`/live/classes/${classId}/polls/${pollId}/close`))

export const votePoll = (classId: number, pollId: number, optionIndex: number): Promise<PollOut> =>
  apiRequest<PollOut>(
    api.post(`/live/classes/${classId}/polls/${pollId}/vote`, { option_index: optionIndex })
  )

/** SSE stream URL for a poll's live results. EventSource cannot carry an
 * Authorization header, so callers needing auth must fall back to the 10s
 * poll (listPolls) — kept here as a pure URL builder for callers that do
 * have a way to authenticate (e.g. a same-origin cookie) or that accept the
 * unauthenticated 401 -> poll fallback path. */
export const pollStreamUrl = (classId: number, pollId: number): string =>
  `/api/v1/live/classes/${classId}/polls/${pollId}/stream`

// ---------------------------------------------------------------------------
// Recording
// ---------------------------------------------------------------------------

export const startRecordingIntent = (classId: number): Promise<RecordingIntentOut> =>
  apiRequest<RecordingIntentOut>(api.post(`/live/classes/${classId}/recording/start`))

export const stopRecordingIntent = (classId: number): Promise<RecordingIntentOut> =>
  apiRequest<RecordingIntentOut>(api.post(`/live/classes/${classId}/recording/stop`))

export const fetchRecordingPlayback = (classId: number): Promise<RecordingPlaybackOut> =>
  apiRequest<RecordingPlaybackOut>(api.get(`/live/classes/${classId}/recording-playback`))

// ---------------------------------------------------------------------------
// Attendance
// ---------------------------------------------------------------------------

export const fetchAttendance = (classId: number): Promise<AttendanceSummaryOut> =>
  apiRequest<AttendanceSummaryOut>(api.get(`/live/classes/${classId}/attendance`))

export const recomputeAttendance = (classId: number, thresholdPct: number): Promise<AttendanceSummaryOut> =>
  apiRequest<AttendanceSummaryOut>(
    api.post(`/live/classes/${classId}/attendance/recompute`, { threshold_pct: thresholdPct })
  )

export const attendanceExportUrl = (classId: number): string =>
  `/live/classes/${classId}/attendance/export.csv`

export const fetchAttendanceExportCsv = async (classId: number): Promise<Blob> => {
  const response = await api.get(attendanceExportUrl(classId), { responseType: 'blob' })
  return response.data
}
