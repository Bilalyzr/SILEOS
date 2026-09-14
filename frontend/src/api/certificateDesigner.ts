/**
 * Certificate designer API client (plan Task 7, consuming Task 6's
 * /api/v1/certificates/designer endpoints — backend/app/routers/
 * certificate_designer.py). Instructors get CRUD over their OWN templates;
 * admins see/edit all; every instructor also sees is_global templates
 * (read-only unless they own the row or are admin).
 */
import { api } from './axios'
import type { DesignerElement, DesignerTemplate, Orientation } from '@/lib/certificateDesignerTypes'
import { toServerElements, fromServerElements } from '@/lib/designerSerialize'

const BASE = '/certificates/designer'

interface RawDesignerTemplate {
  id: number
  name: string
  description: string
  orientation: Orientation
  certificate_width: number
  certificate_height: number
  background_color: string
  background_image: string
  elements_config: Record<string, unknown>[]
  is_global: boolean
  is_own: boolean
  post_author: number
  created_at?: string | null
  updated_at?: string | null
}

function fromRaw(raw: RawDesignerTemplate): DesignerTemplate {
  return {
    ...raw,
    elements_config: fromServerElements(raw.elements_config || []),
  }
}

export interface DesignerTemplatePayload {
  name: string
  description?: string
  orientation: Orientation
  certificate_width: number
  certificate_height: number
  background_color: string
  background_image?: string
  elements_config: DesignerElement[]
  is_global?: boolean
}

export async function listDesignerTemplates(): Promise<DesignerTemplate[]> {
  const res = await api.get<RawDesignerTemplate[]>(`${BASE}/`)
  return (res.data || []).map(fromRaw)
}

export async function createDesignerTemplate(payload: DesignerTemplatePayload): Promise<DesignerTemplate> {
  const res = await api.post<RawDesignerTemplate>(`${BASE}/`, {
    ...payload,
    elements_config: toServerElements(payload.elements_config),
  })
  return fromRaw(res.data)
}

export async function updateDesignerTemplate(
  id: number,
  payload: Partial<DesignerTemplatePayload>
): Promise<DesignerTemplate> {
  const body: Record<string, unknown> = { ...payload }
  if (payload.elements_config) {
    body.elements_config = toServerElements(payload.elements_config)
  }
  const res = await api.put<RawDesignerTemplate>(`${BASE}/${id}`, body)
  return fromRaw(res.data)
}

export async function deleteDesignerTemplate(id: number): Promise<{ message: string }> {
  const res = await api.delete(`${BASE}/${id}`)
  return res.data
}

export async function duplicateDesignerTemplate(id: number): Promise<DesignerTemplate> {
  const res = await api.post<RawDesignerTemplate>(`${BASE}/${id}/duplicate`)
  return fromRaw(res.data)
}

export interface DesignerPreviewResponse {
  preview_url: string
  preview_type: 'pdf' | 'image'
  renderer: 'chrome' | 'reportlab'
  template_id: number
  sample_data: Record<string, string>
}

export async function previewDesignerTemplate(
  id: number,
  values?: Record<string, string>
): Promise<DesignerPreviewResponse> {
  const res = await api.post<DesignerPreviewResponse>(`${BASE}/${id}/preview`, values ? { values } : {})
  return res.data
}

/** 409 Conflict signals a delete blocked because the template is
 * assigned to a course or has issued certificates — callers surface this
 * distinctly (toast) rather than a generic error. */
export function isDeleteConflict(err: unknown): boolean {
  const status = (err as { response?: { status?: number } })?.response?.status
  return status === 409
}

export function errorDetail(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return detail || (err as { message?: string })?.message || fallback
}
