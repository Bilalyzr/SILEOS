import { api } from './axios'

export interface ImpersonationTarget {
  id: number
  display_name: string
  role: string
  email: string
}

export interface StartImpersonationResponse {
  access_token: string
  token_type: string
  expires_in: number
  target: ImpersonationTarget
  log_id?: number
}

/**
 * Admin-only API wrappers. Right now only impersonation lives here;
 * other admin calls use direct fetch() elsewhere in the codebase.
 */
export interface CompanyImpersonationResponse {
  access_token: string
  token_type: string
  redirect: string
  company_name: string
  owner_email: string
}

export const adminApi = {
  /**
   * Start a "View as Instructor" session. Backend mints a 30-minute
   * impersonation_access JWT scoped to `userId` and inserts an audit row.
   *
   * Reject cases (caller should surface to user):
   *   - 400 if the target isn't an instructor
   *   - 403 if the caller is already inside an impersonation session
   *   - 404 if the user doesn't exist
   */
  async impersonate(userId: number, reason?: string): Promise<StartImpersonationResponse> {
    const body: Record<string, unknown> = {}
    if (reason && reason.trim()) body.reason = reason.trim()
    const res = await api.post(`/admin/impersonate/${userId}`, body)
    return res.data
  },

  /**
   * Start a "View as Company" session. Backend mints a 30-minute
   * impersonation_access JWT scoped to the company owner and inserts an audit row.
   *
   * Reject cases (caller should surface to user):
   *   - 403 if the caller is already inside an impersonation session
   *   - 404 if the company doesn't exist
   */
  async impersonateCompany(companyId: number): Promise<CompanyImpersonationResponse> {
    const res = await api.post(`/admin/impersonate/company/${companyId}`)
    return res.data
  },

  /**
   * Start a "View as SPOC" session. Backend mints a 30-minute
   * impersonation_access JWT scoped to the SPOC and inserts an audit row.
   *
   * Reject cases (caller should surface to user):
   *   - 400 if the target isn't a SPOC
   *   - 403 if the caller is already inside an impersonation session
   *   - 404 if the SPOC doesn't exist
   */
  async impersonateSpoc(spocUserId: number): Promise<StartImpersonationResponse> {
    const res = await api.post(`/admin/impersonate/spoc/${spocUserId}`)
    return res.data
  },

  /**
   * Start a "View as Student" session. Backend mints a 30-minute
   * impersonation_access JWT scoped to the student and inserts an audit row.
   *
   * Reject cases (caller should surface to user):
   *   - 400 if the target isn't a student
   *   - 403 if the caller is already inside an impersonation session
   *   - 404 if the student doesn't exist
   */
  async impersonateStudent(studentUserId: number): Promise<StartImpersonationResponse> {
    const res = await api.post(`/admin/impersonate/student/${studentUserId}`)
    return res.data
  },

  /**
   * End the current impersonation session server-side. Idempotent — the
   * backend returns 200 even if no open audit row is found. Safe to call
   * with either the impersonation token or (after local restore) the
   * admin token.
   */
  async endImpersonation(): Promise<{ ok: boolean; closed?: boolean; log_id?: number }> {
    const res = await api.post('/admin/impersonate/end')
    return res.data
  },
}

// ============================================================================
// Internship Requests admin queue (Phase 5b.2)
// ============================================================================

export interface AdminInternshipRequestItem {
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
  status: string
  rejection_reason: string
  approved_internship_id: number | null
  reviewed_by: number | null
  reviewer_name: string | null
  reviewed_at: string | null
  created_at: string
}

export interface AdminInstructorOption {
  id: number
  name: string
  email: string
}

export async function listInternshipRequests(status?: string): Promise<AdminInternshipRequestItem[]> {
  const params = new URLSearchParams()
  if (status) params.set('status_filter', status)
  const qs = params.toString() ? `?${params}` : ''
  const res = await api.get(`/admin/internship-requests${qs}`)
  return res.data?.items ?? []
}

export async function approveInternshipRequest(
  requestId: number,
  body: { spoc_user_id: number; price: number; slug?: string }
): Promise<{ message: string; internship_id: number; slug: string }> {
  const res = await api.post(`/admin/internship-requests/${requestId}/approve`, body)
  return res.data
}

export async function rejectInternshipRequest(
  requestId: number,
  reason: string
): Promise<{ message: string }> {
  const res = await api.post(`/admin/internship-requests/${requestId}/reject`, { reason })
  return res.data
}

export async function deleteInternshipRequest(
  requestId: number
): Promise<void> {
  await api.delete(`/admin/internship-requests/${requestId}`)
}

export async function listInstructorOptions(): Promise<AdminInstructorOption[]> {
  const res = await api.get('/admin/instructors/list')
  return res.data ?? []
}

// ============================================================================
// Certificate Template Management (Admin)
// ============================================================================

export interface TemplateElement {
  id: string
  type: 'text' | 'image' | 'signature' | 'logo' | 'date' | 'course_name' | 'student_name'
  x: number
  y: number
  width: number
  height: number
  content?: string
  font_size?: number
  font_family?: string
  font_color?: string
  font_weight?: string
  text_align?: string
  background_color?: string
  border?: string
  z_index: number
  image_url?: string
  rotation?: number
}

export interface TemplateDimensions {
  width: number
  height: number
}

export interface TemplateBackground {
  type: 'color' | 'image' | 'gradient'
  value?: string
  image_url?: string
}

export interface CertificateTemplate {
  id: number
  name: string
  description: string
  template_type: 'builder' | 'upload' | 'legacy'
  orientation: 'landscape' | 'portrait'
  background: TemplateBackground
  dimensions: TemplateDimensions
  elements: TemplateElement[]
  preview_url?: string
  is_default: boolean
  created_by: number
  created_at: string
  updated_at?: string
  usage_count: number
}

export interface CertificateTemplateCreate {
  name: string
  description?: string
  template_type?: string
  background: TemplateBackground
  dimensions: TemplateDimensions
  elements: TemplateElement[]
  orientation?: 'landscape' | 'portrait'
  is_default?: boolean
}

export interface UploadedTemplateCreate {
  name: string
  description?: string
  file_url: string
  file_type?: 'image' | 'pdf'
  orientation?: 'landscape' | 'portrait'
}

export interface TemplatePreviewResponse {
  preview_url: string
  preview_type?: 'pdf' | 'image'
  template_id: number
  sample_data: Record<string, string>
}

/**
 * Get all certificate templates (builder + uploaded)
 */
export async function getCertificateTemplates(): Promise<CertificateTemplate[]> {
  const res = await api.get('/admin/certificate-templates-v2')
  return res.data ?? []
}

/**
 * Create a new certificate template (builder type)
 */
export async function createCertificateTemplate(
  template: CertificateTemplateCreate
): Promise<{ id: number; name: string; message: string }> {
  const res = await api.post('/admin/certificate-templates-v2', template)
  return res.data
}

/**
 * Update an existing certificate template
 */
export async function updateCertificateTemplate(
  templateId: number,
  updates: Partial<CertificateTemplateCreate>
): Promise<{ message: string }> {
  const res = await api.put(`/admin/certificate-templates-v2/${templateId}`, updates)
  return res.data
}

/**
 * Delete a certificate template
 */
export async function deleteCertificateTemplate(
  templateId: number
): Promise<{ message: string }> {
  const res = await api.delete(`/admin/certificate-templates-v2/${templateId}`)
  return res.data
}

/**
 * Upload a certificate template (image/PDF)
 */
export async function uploadCertificateTemplate(
  template: UploadedTemplateCreate
): Promise<{ id: number; name: string; message: string }> {
  const res = await api.post('/admin/certificate-templates/upload', template)
  return res.data
}

/**
 * Generate a preview of a certificate template
 */
export async function previewCertificateTemplate(
  templateId: number,
  previewData?: Record<string, string>
): Promise<TemplatePreviewResponse> {
  const res = await api.post(`/admin/certificate-templates/${templateId}/preview`, previewData)
  return res.data
}

/**
 * Get legacy certificate templates (for dropdown)
 */
export async function getLegacyCertificateTemplates(): Promise<
  Array<{ id: number; name: string; bg_color: string; title_color: string; font: string }>
> {
  const res = await api.get('/admin/certificate-templates')
  return res.data ?? []
}

// ============================================================================
// Export / Import (Admin)
// ============================================================================

export type ExportSection = 'students' | 'instructors' | 'spocs' | 'companies' | 'courses' | 'blogs' | 'certificates' | 'orders' | 'coupons' | 'dashboard' | 'internships' | 'internship_roster'
  // Admin list sections (backend get_section_query)
  | 'enrollments' | 'reviews' | 'cohorts' | 'lessons' | 'quizzes' | 'internship_requests'
  // Instructor sections
  | 'instructor_courses' | 'instructor_students' | 'instructor_quiz_results' | 'instructor_assignment_results'
  // SPOC sections
  | 'spoc_students' | 'spoc_internships' | 'spoc_placements'
  // Company sections
  | 'company_positions' | 'company_interns' | 'company_performance'
  // Student ("my learning") sections
  | 'student_courses' | 'student_certificates' | 'student_quiz_results' | 'student_assignment_results'
export type ExportFormat = 'csv' | 'excel' | 'pdf'

export interface ExportDataParams {
  section: ExportSection
  format: ExportFormat
  filters?: Record<string, any>
}

export interface ImportResult {
  success_count: number
  error_count: number
  errors?: Array<{ row: number; message: string }>
  message?: string
}

export interface ExportSchema {
  fields: Array<{
    name: string
    type: string
    required: boolean
    description?: string
  }>
  example_row?: Record<string, any>
}

/**
 * Export data from a section (students, instructors, etc.)
 * @param section - The section to export
 * @param format - 'csv' or 'excel'
 * @param filters - Optional filters for the export
 * @returns Promise<Blob> - The exported file as a blob
 */
export async function exportData({
  section,
  format,
  filters = {}
}: ExportDataParams): Promise<Blob> {
  const queryParams = new URLSearchParams({
    format,
    ...Object.entries(filters).reduce((acc, [k, v]) => ({ ...acc, [k]: String(v) }), {})
  }).toString()

  const response = await api.get(`/admin/export/${section}?${queryParams}`, {
    responseType: 'blob'
  })
  return response.data
}

/**
 * Import data into a section (students, instructors, etc.)
 * @param section - The section to import into
 * @param file - The file to import
 * @param format - 'csv' or 'excel'
 * @returns Promise<ImportResult> - Import results with success/error counts
 */
export async function importData(
  section: ExportSection,
  file: File,
  format: ExportFormat
): Promise<ImportResult> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('format', format)

  const res = await api.post(`/admin/import/${section}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return res.data
}

/**
 * Get the export schema for a section (field definitions, example data)
 * @param section - The section to get the schema for
 * @returns Promise<ExportSchema> - Schema with field definitions
 */
export async function getExportSchema(section: ExportSection): Promise<ExportSchema> {
  const res = await api.get(`/admin/export/schema/${section}`)
  return res.data
}

/**
 * Download Excel template for a section
 * @param section - The section to get the template for
 * @returns Promise<Blob> - The template file as a blob
 */
export async function downloadTemplate(section: ExportSection): Promise<Blob> {
  // Use public endpoint - no auth required
  const response = await api.get(`/templates/${section}`, {
    responseType: 'blob'
  })
  return response.data
}

// ============================================================================
// Role-based Export/Import
// ============================================================================

export async function exportRoleData({
  role,
  section,
  format,
  filters = {}
}: {
  role: 'instructor' | 'spoc' | 'company' | 'student'
  section: string
  format: ExportFormat
  filters?: Record<string, any>
}): Promise<Blob> {
  const queryParams = new URLSearchParams({
    format,
    ...Object.entries(filters).reduce((acc, [k, v]) => ({ ...acc, [k]: String(v) }), {})
  }).toString()

  const response = await api.get(`/${role}/export/${section}?${queryParams}`, {
    responseType: 'blob'
  })
  return response.data
}

export default adminApi
