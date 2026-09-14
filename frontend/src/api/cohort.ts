import { api } from './axios'

// ---------------- Types ----------------

export interface College {
  id: number
  name: string
  slug: string
  city: string
  state: string
  contact_name: string
  contact_email: string
  created_by?: number | null
  created_at: string
  updated_at?: string | null
}

export interface ReferralCodeOut {
  id: number
  cohort_id: number
  code: string
  max_uses: number
  used_count: number
  expires_at?: string | null
  created_at: string
}

export interface Cohort {
  id: number
  college_id: number
  course_id: number
  spoc_user_id: number
  name: string
  slug: string
  max_students: number
  starts_on?: string | null
  ends_on?: string | null
  is_active: boolean
  seat_price?: number | null
  created_at: string
  updated_at?: string | null
  referral_code?: ReferralCodeOut | null
}

export interface RosterRow {
  user_id: number
  display_name: string
  email: string
  joined_at: string
  active_today: boolean
}

export interface TaskStatsRow {
  user_id: number
  display_name: string
  completed_lessons: number
  quiz_attempts: number
  assignment_submissions: number
}

export type SessionType = 'lecture' | 'lab' | 'evaluation' | 'other'
export type AttendanceStatus = 'present' | 'absent' | 'late' | 'excused'

export interface CohortSession {
  id: number
  cohort_id: number
  scheduled_at: string
  duration_minutes: number
  topic: string
  session_type: string
  created_by?: number | null
  created_at: string
}

export interface AttendanceEntry {
  user_id: number
  status: AttendanceStatus
  notes?: string
}

// ---------------- Admin: colleges ----------------

export const collegeApi = {
  list: () => api.get<College[]>('/cohorts/admin/colleges').then(r => r.data),
  get: (id: number) => api.get<College>(`/cohorts/admin/colleges/${id}`).then(r => r.data),
  create: (body: Partial<College>) =>
    api.post<College>('/cohorts/admin/colleges', body).then(r => r.data),
  update: (id: number, body: Partial<College>) =>
    api.put<College>(`/cohorts/admin/colleges/${id}`, body).then(r => r.data),
  remove: (id: number) =>
    api.delete(`/cohorts/admin/colleges/${id}`).then(r => r.data),
}

// ---------------- Admin: cohorts ----------------

export interface CohortCreatePayload {
  college_id: number
  course_id: number
  spoc_user_id: number
  name: string
  slug?: string
  max_students?: number
  starts_on?: string | null
  ends_on?: string | null
  is_active?: boolean
  referral_max_uses?: number
  referral_expires_at?: string | null
  // Only meaningful on update (PUT) — backend CohortUpdate accepts it,
  // CohortCreate does not. null clears the override; omit to leave untouched.
  seat_price?: number | null
}

export const cohortApi = {
  list: () => api.get<Cohort[]>('/cohorts/admin/cohorts').then(r => r.data),
  get: (id: number) => api.get<Cohort>(`/cohorts/admin/cohorts/${id}`).then(r => r.data),
  create: (body: CohortCreatePayload) =>
    api.post<Cohort>('/cohorts/admin/cohorts', body).then(r => r.data),
  update: (id: number, body: Partial<CohortCreatePayload>) =>
    api.put<Cohort>(`/cohorts/admin/cohorts/${id}`, body).then(r => r.data),
  remove: (id: number) =>
    api.delete(`/cohorts/admin/cohorts/${id}`).then(r => r.data),
  // Manual cohort membership management
  listMembers: (cohortId: number) =>
    api.get<CohortMember[]>(`/cohorts/admin/cohorts/${cohortId}/members`).then(r => r.data),
  addMember: (cohortId: number, body: { email?: string; user_id?: number }) =>
    api.post<CohortMember>(`/cohorts/admin/cohorts/${cohortId}/members`, body).then(r => r.data),
  removeMember: (cohortId: number, userId: number) =>
    api.delete(`/cohorts/admin/cohorts/${cohortId}/members/${userId}`).then(r => r.data),
  // Regenerate referral code — invalidates the previous one immediately.
  regenerateCode: (cohortId: number) =>
    api.post<ReferralCodeOut>(`/cohorts/admin/cohorts/${cohortId}/referral-code/regenerate`)
      .then(r => r.data),
}

export interface CohortMember {
  membership_id: number
  user_id: number
  email: string
  display_name: string
  joined_at: string
}

// ---------------- SPOC ----------------

export const spocApi = {
  myCohorts: () => api.get<Cohort[]>('/cohorts/spoc/my-cohorts').then(r => r.data),
  roster: (cohortId: number) =>
    api.get<RosterRow[]>(`/cohorts/spoc/cohorts/${cohortId}/roster`).then(r => r.data),
  taskStats: (cohortId: number) =>
    api.get<TaskStatsRow[]>(`/cohorts/spoc/cohorts/${cohortId}/task-stats`).then(r => r.data),
  listSessions: (cohortId: number) =>
    api.get<CohortSession[]>(`/cohorts/spoc/cohorts/${cohortId}/sessions`).then(r => r.data),
  createSession: (cohortId: number, body: Partial<CohortSession>) =>
    api.post<CohortSession>(`/cohorts/spoc/cohorts/${cohortId}/sessions`, body).then(r => r.data),
  updateSession: (cohortId: number, sessionId: number, body: Partial<CohortSession>) =>
    api.put<CohortSession>(`/cohorts/spoc/cohorts/${cohortId}/sessions/${sessionId}`, body).then(r => r.data),
  deleteSession: (cohortId: number, sessionId: number) =>
    api.delete(`/cohorts/spoc/cohorts/${cohortId}/sessions/${sessionId}`).then(r => r.data),
  bulkAttendance: (sessionId: number, entries: AttendanceEntry[]) =>
    api.post(`/cohorts/spoc/sessions/${sessionId}/attendance`, { entries }).then(r => r.data),
  setEligibility: (userId: number, body: { eligible: boolean; reason?: string }) =>
    api.post(`/cohorts/spoc/students/${userId}/internship-eligible`, body).then(r => r.data),
}
