/**
 * AI layer completion client (v2.0 §9 — WP7) — mirrors backend/app/routers/ai_engines.py
 * plus the transcript endpoints on live_class_recordings.py. Every LLM-backed
 * call can return 503 when GLM_API_KEY is absent; callers show that honestly.
 */
import { api } from './axios'

export type AdaptiveMode = 'recover' | 'consolidate' | 'extend'
export interface AdaptiveLesson {
  job_id: number; mode: AdaptiveMode; concept: string | null; estimate: number | null
  lesson: { title?: string; mode?: string; concept?: string; sections?: { heading: string; body: string }[]; check?: { question: string; answer: string } }
  note: string
}
export interface CheckQuestion {
  job_id: number; concept: string | null; level: 'easy' | 'medium' | 'hard'
  check: { question: string; kind: 'open' | 'mcq'; options?: string[]; answer: string; why?: string }
}
export interface Escalation {
  id: number; course_id: number; student_id: number; instructor_id: number; question: string
  context: { history?: { role: string; content: string }[]; lesson_id?: number | null; weak_concepts?: string[] }
  status: 'open' | 'answered'; instructor_reply: string | null; created_at: string | null; answered_at: string | null
  student_name?: string | null
}
export type ErrorKind = 'quiz_question' | 'lesson' | 'bank_question' | 'other'
export interface ErrorReport {
  id: number; reporter_id: number; course_id: number; instructor_id: number; kind: ErrorKind; ref_id: number | null
  message: string; status: 'open' | 'resolved' | 'dismissed'; resolution: string | null; created_at: string | null; resolved_at: string | null
}
export interface FlaggedItem {
  question_id: number; quiz_id: number; quiz_title: string; course_id: number; question_title: string
  attempts: number; facility: number | null; discrimination: number | null; reasons: string[]
}
export interface DraftQuestion {
  question_id: number; bank_id: number; bank_title: string; question_title: string; question_type: string
  options: string[] | null; correct_answer: unknown; difficulty: string; tags: string[]
}
export interface ReviewQueue {
  ai_drafts: DraftQuestion[]; flagged_items: FlaggedItem[]; error_reports: ErrorReport[]; escalations: Escalation[]
  counts: { ai_drafts: number; flagged_items: number; error_reports: number; escalations: number }
  llm_configured: boolean
}

export const aiLayerAPI = {
  adaptiveLesson: async (courseId: number, body: { mode?: AdaptiveMode; concept?: string; student_id?: number }) =>
    (await api.post<AdaptiveLesson>(`/ai/adaptive-lesson/${courseId}`, body)).data,
  checkQuestion: async (course_id: number, concept?: string) =>
    (await api.post<CheckQuestion>('/ai/tutor/check-question', { course_id, concept })).data,
  escalate: async (body: { course_id: number; question: string; history?: { role: string; content: string }[]; lesson_id?: number }) =>
    (await api.post<Escalation>('/ai/tutor/escalate', body)).data,
  escalations: async (status?: 'open' | 'answered') =>
    (await api.get<{ escalations: Escalation[] }>('/ai/tutor/escalations', { params: status ? { status } : undefined })).data.escalations,
  reply: async (id: number, reply: string) => (await api.post<Escalation>(`/ai/tutor/escalations/${id}/reply`, { reply })).data,
  reportError: async (body: { course_id: number; kind: ErrorKind; ref_id?: number; message: string }) =>
    (await api.post<ErrorReport>('/ai/error-reports', body)).data,
  errorReports: async (status?: string) =>
    (await api.get<{ reports: ErrorReport[] }>('/ai/error-reports', { params: status ? { status } : undefined })).data.reports,
  resolveReport: async (id: number, status: 'resolved' | 'dismissed', resolution?: string) =>
    (await api.post<ErrorReport>(`/ai/error-reports/${id}/resolve`, { status, resolution })).data,
  reviewQueue: async () => (await api.get<ReviewQueue>('/ai/review-queue')).data,
  approveDraft: async (id: number) => (await api.post(`/ai/review-queue/questions/${id}/approve`)).data,
  rejectDraft: async (id: number) => (await api.post(`/ai/review-queue/questions/${id}/reject`)).data,
  pasteTranscript: async (classId: number, transcript: string) =>
    (await api.post<{ class_id: number; processing_status: string; ai_topics: unknown[] | null; note: string | null }>(`/live/classes/${classId}/report/transcript`, { transcript })).data,
}

export function errDetail(e: unknown, fallback: string): { status?: number; detail: string } {
  const status = (e as { response?: { status?: number } })?.response?.status
  const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return { status, detail: typeof detail === 'string' ? detail : fallback }
}
