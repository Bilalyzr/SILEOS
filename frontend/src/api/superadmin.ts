/**
 * SuperAdmin API client.
 *
 * All endpoints here live under `/api/v1/superadmin` and are gated by
 * `AuthService.require_superadmin`. SuperAdmin also inherits every
 * `/admin` endpoint (via `require_admin` accepting `("admin","superadmin")`),
 * so for those the existing `adminApi` client is reused.
 */
import { api } from './axios'

/** Minimal target descriptor echoed by the impersonation starter. */
export interface SuperadminImpersonationTarget {
  id: number
  display_name: string
  role: string
  email: string
}

export interface StartSuperadminImpersonationResponse {
  access_token: string
  token_type: string
  expires_in: number
  target: SuperadminImpersonationTarget
  log_id: number
  actor_role: 'superadmin'
}

export interface SuperadminOverview {
  generated_at: string
  cached?: boolean
  active_users_by_role: Record<string, number>
  dau: number
  wau: number
  revenue_trend: { day: string; revenue: number; orders: number }[]
  role_distribution: { name: string; value: number }[]
  activity_trend: {
    day: string
    revenue: number
    orders: number
    enrollments: number
    active_users: number
  }[]
  /** Open AND started inside the impersonation-token TTL, i.e. genuinely live. */
  open_impersonation_sessions: number
  /** Never-closed rows too old for their token to still be valid. */
  stale_impersonation_sessions: number
  totals: {
    students: number
    instructors: number
    admins: number
    courses: number
    enrollments: number
  }
}

export interface SuperadminStudentRow {
  id: number
  display_name: string
  email: string
  enrollments: number
  completion_pct: number
  pass_rate: number
  certificates: number
  streak_days: number
  last_active: string | null
}

export interface SuperadminInstructorRow {
  id: number
  display_name: string
  email: string
  courses_published: number
  students_enrolled: number
  avg_rating: number
  pending_approvals: number
  revenue_attributed: number
  last_active: string | null
}

export interface SuperadminAdminRow {
  id: number
  display_name: string
  email: string
  role: string
  last_login: string | null
  impersonations_run: number
}

export interface SuperadminImpersonationAuditRow {
  id: number
  actor_user_id: number
  actor_name: string
  actor_role: string | null
  target_user_id: number
  target_name: string
  target_role: string
  started_at: string
  ended_at: string | null
  duration_seconds: number | null
  reason: string | null
}

export interface SuperadminListResponse<T> {
  items: T[]
  total: number
}

export const superadminApi = {
  /** Impersonate ANY non-superadmin user (student/instructor/spoc/company/admin). */
  async impersonate(
    targetUserId: number,
    reason?: string,
  ): Promise<StartSuperadminImpersonationResponse> {
    const body = reason && reason.trim() ? { reason: reason.trim() } : undefined
    const res = await api.post(`/superadmin/impersonate/${targetUserId}`, body)
    return res.data
  },

  /** Overview KPIs. Cached 5 min server-side. */
  async overview(): Promise<SuperadminOverview> {
    const res = await api.get('/superadmin/overview')
    return res.data
  },

  async listStudents(
    params: { search?: string; limit?: number; offset?: number } = {},
  ): Promise<SuperadminListResponse<SuperadminStudentRow>> {
    const res = await api.get('/superadmin/students', { params })
    return res.data
  },

  async listInstructors(
    params: { search?: string; limit?: number; offset?: number } = {},
  ): Promise<SuperadminListResponse<SuperadminInstructorRow>> {
    const res = await api.get('/superadmin/instructors', { params })
    return res.data
  },

  async listAdmins(
    params: { search?: string; limit?: number; offset?: number } = {},
  ): Promise<SuperadminListResponse<SuperadminAdminRow>> {
    const res = await api.get('/superadmin/admins', { params })
    return res.data
  },

  async auditImpersonations(
    params: { limit?: number; offset?: number; open_only?: boolean } = {},
  ): Promise<SuperadminListResponse<SuperadminImpersonationAuditRow>> {
    const res = await api.get('/superadmin/audit/impersonations', { params })
    return res.data
  },
}

export default superadminApi
