/**
 * React Query hooks for the Company Dashboard v2 API.
 * All hooks are typed and use real API endpoints — no mock data.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { api } from './axios'
import type { AxiosError } from 'axios'

// ============================================================================
// Types
// ============================================================================

export interface OverviewStats {
  active_interns: number
  active_internships: number
  week_attendance_pct: number
  pending_work_log_reviews: number
  today_present: number
  today_absent: number
  today_late: number
  today_excused: number
  today_not_marked: number
  activity: Array<Record<string, unknown>>
}

export interface Student {
  user_id: number
  voucher_id: number
  name: string
  email: string
  internship_id: number
  internship_title: string
  progress_pct: number
  attendance_pct: number
  reporting_manager_user_id: number | null
  reporting_manager_name: string | null
  cert_status: string
  notes: string
  // Candidate profile links
  resume_url: string | null
  linkedin_url: string | null
  github_url: string | null
  portfolio_url: string | null
}

export interface StudentListResponse {
  items: Student[]
  total: number
}

export interface CompanyInternship {
  id: number
  title: string
  slug: string
  cover_image: string
  student_count: number
  avg_progress_pct: number
  spoc_name: string | null
}

export interface InternshipListResponse {
  items: CompanyInternship[]
}

export interface AttendanceEntry {
  id: number | null
  student_user_id: number
  internship_id: number
  date: string
  status: string
  hours_worked: number
  notes: string
}

export interface AttendanceGridResponse {
  students: Array<{
    user_id: number
    name: string
    email: string
    voucher_id: number
    entries: AttendanceEntry[]
  }>
  dates: string[]
}

export interface WorkLogItem {
  id: number
  student_user_id: number
  student_name: string
  internship_id: number
  internship_title: string
  log_date: string
  content: string
  attachment_url: string
  review_status: string
  reviewed_by_name: string | null
  reviewer_comment: string
}

export interface WorkLogListResponse {
  items: WorkLogItem[]
  total: number
}

export interface AnnouncementItem {
  id: number
  title: string
  body: string
  internship_id: number | null
  internship_title: string | null
  created_at: string
  created_by_name: string | null
}

export interface AnnouncementListResponse {
  items: AnnouncementItem[]
}

export interface ManagerItem {
  id: number
  user_id: number
  email: string
  name: string
  accepted_at: string | null
  invited_at: string
}

export interface PerformanceReviewItem {
  id: number
  company_id: number
  student_user_id: number
  student_name: string
  internship_id: number
  internship_title: string
  rating: number
  feedback: string
  hire_recommendation: string
  submitted_at: string
}

// ============================================================================
// Overview
// ============================================================================

export function useOverview() {
  return useQuery<OverviewStats>({
    queryKey: ['company-dashboard', 'overview'],
    queryFn: async () => {
      const { data } = await api.get('/companies/me/overview')
      return data
    },
    retry: 1,
  })
}

// ============================================================================
// Students
// ============================================================================

export function useStudents(filters?: {
  internship_id?: number
  manager_id?: number
  search?: string
}) {
  return useQuery<StudentListResponse>({
    queryKey: ['company-dashboard', 'students', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters?.internship_id) params.set('internship_id', String(filters.internship_id))
      if (filters?.manager_id) params.set('manager_id', String(filters.manager_id))
      if (filters?.search) params.set('search', filters.search)
      const { data } = await api.get(`/companies/me/students?${params}`)
      return data
    },
  })
}

export function useStudent(userId: number) {
  return useQuery<Student>({
    queryKey: ['company-dashboard', 'students', userId],
    queryFn: async () => {
      const { data } = await api.get(`/companies/me/students/${userId}`)
      return data
    },
    enabled: !!userId,
  })
}

export interface UpdateStudentRequest {
  reporting_manager_user_id?: number
  notes?: string
  internship_status?: string
}

export function useUpdateStudent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ userId, data: requestData }: { userId: number; data: UpdateStudentRequest }) => {
      const { data } = await api.patch(`/companies/me/students/${userId}`, requestData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-dashboard', 'students'] })
      toast.success('Student updated successfully')
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      toast.error(err.response?.data?.detail || 'Failed to update student')
    },
  })
}

// ============================================================================
// Internships
// ============================================================================

export function useInternships() {
  return useQuery<InternshipListResponse>({
    queryKey: ['company-dashboard', 'internships'],
    queryFn: async () => {
      const { data } = await api.get('/companies/me/internships')
      return data
    },
  })
}

export function useInternship(internshipId: number) {
  return useQuery<CompanyInternship>({
    queryKey: ['company-dashboard', 'internships', internshipId],
    queryFn: async () => {
      const { data } = await api.get(`/companies/me/internships/${internshipId}`)
      return data
    },
    enabled: !!internshipId,
  })
}

// ============================================================================
// Attendance
// ============================================================================

export function useAttendance(fromDate?: string, toDate?: string) {
  return useQuery<AttendanceGridResponse>({
    queryKey: ['company-dashboard', 'attendance', fromDate, toDate],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (fromDate) params.set('from_date', fromDate)
      if (toDate) params.set('to_date', toDate)
      const { data } = await api.get(`/companies/me/attendance?${params}`)
      return data
    },
  })
}

export function useUpsertAttendance() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (entries: AttendanceEntry[]) => {
      const { data } = await api.post('/companies/me/attendance', { entries })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-dashboard', 'attendance'] })
      queryClient.invalidateQueries({ queryKey: ['company-dashboard', 'overview'] })
      toast.success('Attendance saved successfully')
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      toast.error(err.response?.data?.detail || 'Failed to save attendance')
    },
  })
}

// ============================================================================
// Work Logs
// ============================================================================

export function useWorkLogs(filters?: {
  student_id?: number
  internship_id?: number
  status?: string
}) {
  return useQuery<WorkLogListResponse>({
    queryKey: ['company-dashboard', 'work-logs', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters?.student_id) params.set('student_id', String(filters.student_id))
      if (filters?.internship_id) params.set('internship_id', String(filters.internship_id))
      if (filters?.status) params.set('status', filters.status)
      const { data } = await api.get(`/companies/me/work-logs?${params}`)
      return data
    },
  })
}

export interface ReviewWorkLogRequest {
  status: string
  comment: string
}

export function useReviewWorkLog() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ logId, data: requestData }: { logId: number; data: ReviewWorkLogRequest }) => {
      const { data } = await api.post(`/companies/me/work-logs/${logId}/review`, requestData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-dashboard', 'work-logs'] })
      queryClient.invalidateQueries({ queryKey: ['company-dashboard', 'overview'] })
      toast.success('Work log reviewed successfully')
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      toast.error(err.response?.data?.detail || 'Failed to review work log')
    },
  })
}

// ============================================================================
// Announcements
// ============================================================================

export function useAnnouncements() {
  return useQuery<AnnouncementListResponse>({
    queryKey: ['company-dashboard', 'announcements'],
    queryFn: async () => {
      const { data } = await api.get('/companies/me/announcements')
      return data
    },
  })
}

export interface CreateAnnouncementRequest {
  title: string
  body: string
  internship_id?: number
}

export function useCreateAnnouncement() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (requestData: CreateAnnouncementRequest) => {
      const { data } = await api.post('/companies/me/announcements', requestData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-dashboard', 'announcements'] })
      toast.success('Announcement created successfully')
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      toast.error(err.response?.data?.detail || 'Failed to create announcement')
    },
  })
}

export function useDeleteAnnouncement() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (announcementId: number) => {
      const { data } = await api.delete(`/companies/me/announcements/${announcementId}`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-dashboard', 'announcements'] })
      toast.success('Announcement deleted successfully')
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      toast.error(err.response?.data?.detail || 'Failed to delete announcement')
    },
  })
}

// ============================================================================
// Managers
// ============================================================================

export function useManagers() {
  return useQuery<{ items: ManagerItem[] }>({
    queryKey: ['company-dashboard', 'managers'],
    queryFn: async () => {
      const { data } = await api.get('/companies/me/managers')
      return { items: data }
    },
  })
}

export interface InviteManagerRequest {
  email: string
  name: string
}

export function useInviteManager() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (requestData: InviteManagerRequest) => {
      const { data } = await api.post('/companies/me/managers', requestData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-dashboard', 'managers'] })
      toast.success('Manager invited successfully')
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      toast.error(err.response?.data?.detail || 'Failed to invite manager')
    },
  })
}

export function useRevokeManager() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (managerId: number) => {
      const { data } = await api.delete(`/companies/me/managers/${managerId}`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-dashboard', 'managers'] })
      toast.success('Manager revoked successfully')
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      toast.error(err.response?.data?.detail || 'Failed to revoke manager')
    },
  })
}

// ============================================================================
// Performance Reviews
// ============================================================================

export function usePerformanceReviews() {
  return useQuery<PerformanceReviewItem[]>({
    queryKey: ['company-dashboard', 'reviews'],
    queryFn: async () => {
      const { data } = await api.get('/companies/me/reviews')
      return data
    },
  })
}

export interface CreateReviewRequest {
  student_user_id: number
  internship_id: number
  rating: number
  feedback: string
  hire_recommendation: string
}

export function useCreateReview() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (requestData: CreateReviewRequest) => {
      const { data } = await api.post('/companies/me/reviews', requestData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-dashboard', 'reviews'] })
      toast.success('Performance review submitted successfully')
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      toast.error(err.response?.data?.detail || 'Failed to submit review')
    },
  })
}

// ============================================================================
// Reports
// ============================================================================

export interface ReportRow {
  log_date: string
  student_name: string
  student_email: string
  internship_title: string
  reporting_manager: string
  status: string
  hours: number
  note: string
  marked_by_name: string
}

export interface AttendanceReportParams {
  from_date: string
  to_date: string
  internship_id?: number[]
  student_id?: number[]
  manager_id?: number[]
  format?: 'json' | 'csv' | 'pdf'
}

export function useAttendanceReport(params: AttendanceReportParams) {
  return useQuery<{ rows: ReportRow[] }>({
    queryKey: ['company-dashboard', 'reports', 'attendance', params],
    queryFn: async () => {
      const queryParams = new URLSearchParams()
      queryParams.set('from_date', params.from_date)
      queryParams.set('to_date', params.to_date)
      if (params.format) queryParams.set('format', params.format)
      params.internship_id?.forEach(id => queryParams.append('internship_id', String(id)))
      params.student_id?.forEach(id => queryParams.append('student_id', String(id)))
      params.manager_id?.forEach(id => queryParams.append('manager_id', String(id)))

      const { data } = await api.get(`/companies/me/reports/attendance?${queryParams}`)
      return data
    },
    enabled: !!params.from_date && !!params.to_date,
  })
}

// ============================================================================
// Company profile (GET /companies/me) — used by header identity block
// ============================================================================

export interface CompanyProfile {
  id: number
  owner_user_id: number
  name: string
  slug: string
  website: string
  industry: string
  team_size: string
  description: string
  logo_url: string
  contact_email: string
  contact_phone: string
  is_approved: boolean
  approval_source: string
  approved_at: string | null
  created_at: string | null
  updated_at: string | null
}

export function useCompany() {
  return useQuery<CompanyProfile>({
    queryKey: ['company-profile', 'me'],
    queryFn: async () => {
      const { data } = await api.get('/companies/me')
      return data
    },
    retry: 1,
  })
}

// ============================================================================
// Internship Requests (company-side) — Phase 5b.2
// ============================================================================

export interface InternshipRequestItem {
  id: number
  company_id: number
  company_name: string
  requested_by: number
  requester_name: string
  title: string
  start_date: string
  end_date: string
  intern_count: number
  description: string
  status: string // 'pending' | 'approved' | 'rejected'
  rejection_reason: string
  approved_internship_id: number | null
  reviewed_by: number | null
  reviewer_name: string | null
  reviewed_at: string | null
  created_at: string
}

export interface InternshipRequestListResponse {
  items: InternshipRequestItem[]
}

export interface CreateInternshipRequestRequest {
  title: string
  start_date: string
  end_date: string
  intern_count: number
  description: string
}

export function useInternshipRequests(filters?: { status?: string }) {
  return useQuery<InternshipRequestListResponse>({
    queryKey: ['company-dashboard', 'internship-requests', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters?.status) params.set('status_filter', filters.status)
      const qs = params.toString() ? `?${params}` : ''
      const { data } = await api.get(`/companies/me/internship-requests${qs}`)
      return data
    },
  })
}

export function useCreateInternshipRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (requestData: CreateInternshipRequestRequest) => {
      const { data } = await api.post('/companies/me/internship-requests', requestData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-dashboard', 'internship-requests'] })
      toast.success('Request submitted to admin')
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      toast.error(err.response?.data?.detail || 'Failed to submit request')
    },
  })
}

export function useDeleteInternshipRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (requestId: number) => {
      const { data } = await api.delete(`/companies/me/internship-requests/${requestId}`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-dashboard', 'internship-requests'] })
      toast.success('Request withdrawn')
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      toast.error(err.response?.data?.detail || 'Failed to withdraw request')
    },
  })
}

export async function downloadAttendanceReport(
  params: AttendanceReportParams,
  format: 'csv' | 'pdf'
): Promise<Blob> {
  const queryParams = new URLSearchParams()
  queryParams.set('from_date', params.from_date)
  queryParams.set('to_date', params.to_date)
  queryParams.set('format', format)
  params.internship_id?.forEach(id => queryParams.append('internship_id', String(id)))
  params.student_id?.forEach(id => queryParams.append('student_id', String(id)))
  params.manager_id?.forEach(id => queryParams.append('manager_id', String(id)))

  const { data } = await api.get(`/companies/me/reports/attendance?${queryParams}`, {
    responseType: 'blob',
  })
  return data
}
