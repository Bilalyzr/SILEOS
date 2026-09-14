/**
 * Flywheel client (v2.0 §10 — WP8) — mirrors backend/app/routers/flywheel.py.
 */
import { api } from './axios'

export interface AgendaItem { kind: 'recap' | 'reteach' | 'catch_up' | 'questions' | 'fix' | 'advance'; text: string; minutes: number; concept?: string }
export interface NextAgenda {
  course_id: number; based_on_class_id: number | null; last_class_title: string | null
  weak_concepts: { concept: string; learners: number; avg_estimate: number }[]
  absent_count: number; open_escalations: number; open_error_reports: number
  agenda: AgendaItem[]; prose: string | null; llm_configured: boolean
}
export interface PathStat { share_pct: number; avg_task_score: number; avg_quiz_score: number | null }
export interface InsightCard {
  task_id: number; task_title: string; task_type: string; attempts: number; concepts: string[]
  paths: { clean: PathStat; mixed: PathStat; trial_and_error: PathStat }; insights: string[]
}
export interface TeachBack {
  id: number; user_id: number; author: string | null; course_id: number | null; concept: string; text: string
  status: string; helpful_count: number; not_helpful_count: number; my_vote: boolean | null; created_at: string | null
}

export const flywheelAPI = {
  nextAgenda: async (courseId: number, opts?: { class_id?: number; polish?: boolean }) =>
    (await api.get<NextAgenda>(`/flywheel/courses/${courseId}/next-agenda`, { params: opts })).data,
  insightCards: async (courseId: number) => (await api.get<{ cards: InsightCard[] }>(`/flywheel/courses/${courseId}/insight-cards`)).data.cards,
  teachBacks: async (params: { concept?: string; course_id?: number; mine?: boolean }) =>
    (await api.get<{ teach_backs: TeachBack[] }>('/flywheel/teach-back', { params })).data.teach_backs,
  writeTeachBack: async (body: { concept: string; text: string; course_id?: number }) => (await api.post<TeachBack>('/flywheel/teach-back', body)).data,
  rate: async (id: number, helpful: boolean) => (await api.post<TeachBack & { changed: boolean }>(`/flywheel/teach-back/${id}/rate`, { helpful })).data,
  hide: async (id: number) => (await api.post(`/flywheel/teach-back/${id}/hide`)).data,
  digilockerStatus: async () => (await api.get<{ configured: boolean; needs: string[]; note: string }>('/flywheel/digilocker/status')).data,
  pushDigilocker: async (issuedId: number) => (await api.post(`/flywheel/certificates/${issuedId}/digilocker`)).data,
}
