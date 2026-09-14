/**
 * Conversion funnel client (roadmap R1) — mirrors backend/app/routers/funnel.py.
 * `track()` is fire-and-forget and never throws; visitors are keyed by a
 * per-browser session id kept in localStorage.
 */
import { api } from './axios'

export type FunnelKind = 'course_view' | 'preview_open' | 'checkout_start'

export function funnelSessionId(): string {
  try {
    let id = localStorage.getItem('si.funnel.sid')
    if (!id) {
      id = 'fs-' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36)
      localStorage.setItem('si.funnel.sid', id)
    }
    return id
  } catch {
    return 'fs-anon-' + Date.now().toString(36)
  }
}

const seen = new Set<string>()

/** Record one funnel event; de-duplicated per page load for view events. */
export function track(kind: FunnelKind, courseId: number, meta?: Record<string, string | number | boolean>): void {
  const key = `${kind}:${courseId}:${meta?.lesson_id ?? ''}`
  if (kind === 'course_view' && seen.has(key)) return
  seen.add(key)
  api.post('/funnel/events', { kind, course_id: courseId, session_id: funnelSessionId(), meta }).catch(() => { /* never block the UI */ })
}

export interface FunnelSummary {
  course_id: number; days: number; views: number; preview_opens: number; checkout_starts: number; enrolments: number
  rates: { view_to_preview: number | null; preview_to_checkout: number | null; checkout_to_enrol: number | null; view_to_enrol: number | null }
  top_preview_lessons: { lesson_id: string; opens: number }[]
  title?: string
}
export interface ContinueItem {
  course_id: number; course_title: string; course_slug: string | null; lesson_id: number; lesson_title: string
  lesson_type: string; lesson_status: string; video_pct: number; course_pct: number; touched_at: string | null
}

export const funnelAPI = {
  summary: async (courseId: number, days = 30) => (await api.get<FunnelSummary>(`/funnel/courses/${courseId}/summary`, { params: { days } })).data,
  overview: async (days = 30) => (await api.get<{ days: number; courses: FunnelSummary[] }>('/funnel/overview', { params: { days } })).data.courses,
  continueLearning: async () => (await api.get<{ items: ContinueItem[] }>('/funnel/me/continue')).data.items,
}
