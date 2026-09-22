/**
 * Learning-signals client (2026-09-06). `signal()` buffers behaviour events
 * and flushes them in batches (every 8 s, when the tab hides, and at
 * unmount); nothing here ever blocks the UI or throws.
 */
import { api } from './axios'

export type SignalKind = 'video_rewind' | 'video_replay' | 'video_pause' | 'video_skip' | 'rate_change' | 'quit_early'
  | 'note_written' | 'question_time' | 'answer_change'
export interface SignalEvent {
  kind: SignalKind; course_id?: number; lesson_id?: number; quiz_id?: number; question_id?: number
  position_s?: number; value?: number; meta?: Record<string, string | number | boolean>
}

const buffer: SignalEvent[] = []
let timer: ReturnType<typeof setTimeout> | null = null

export function flushSignals(): void {
  if (buffer.length === 0) return
  const batch = buffer.splice(0, 200)
  api.post('/signals/events', { events: batch }).catch(() => { /* best-effort */ })
}

export function signal(ev: SignalEvent): void {
  buffer.push(ev)
  if (buffer.length >= 50) { flushSignals(); return }
  if (!timer) timer = setTimeout(() => { timer = null; flushSignals() }, 8000)
}

if (typeof window !== 'undefined') {
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') flushSignals() })
  window.addEventListener('pagehide', flushSignals)
}

export interface StruggleConcept { concept: string; struggle: number; raw: number; why: string[]; mastery: number | null; confidence: number | null }
export interface StruggleProfile { user_id: number; course_id: number | null; days: number; signals: number; concepts: StruggleConcept[]; struggling: StruggleConcept[]; confident: StruggleConcept[] }
export interface AdaptiveQuestion { question_id: number; title: string; type: string; marks: number; options: string[]; concepts: string[]; difficulty: string }
export interface AdaptiveBuild { session_id: number; plan: { concepts: string[]; why: string[] }; questions: AdaptiveQuestion[] }
export interface AdaptiveResult { session_id: number; score: number; max_score: number; results: { question_id: number; correct: boolean; concepts: string[]; expected: string[] }[]; by_concept: { concept: string; correct: number; total: number }[] }
export interface HeatSegment { segment: number; start_s: number; end_s: number; rewinds: number; replays: number; pauses: number; skips: number; learners: number; score: number; concepts: string[] }
export interface Heatmap { lesson_id: number; segments: HeatSegment[]; struggle_segments: HeatSegment[]; early_quits: number; markers: { id: number; time_s: number; concept: string }[]; lesson_concepts: string[] }

export interface CourseHotspot { lesson_id: number; lesson_title: string; segment: number; start_s: number; end_s: number; score: number; learners: number; rewinds: number; replays: number; early_quits: number; concepts: string[] }
export interface CourseHotspots { course_id: number; days: number; hotspots: CourseHotspot[]; early_quits_by_lesson: { lesson_id: number; lesson_title: string; early_quits: number }[]; struggling_by_concept: { concept: string; learners: number }[] }

export interface SashaInsightStudent {
  user_id: number; name: string; email: string; risk_score: number
  severity: 'high' | 'watch' | 'developing'; questions: number
  top_concepts: string[]; likely_gap: string; evidence: string[]; last_seen: string | null
}
export interface SashaInsightConcept {
  concept: string; score: number; questions: number; learners: number; likely_gap: string
}
export interface SashaRecentSignal {
  id: number; user_id: number; student_name: string; concept: string; score: number
  severity: 'high' | 'watch' | 'developing'; likely_gap: string; excerpt: string
  reasons: string[]; created_at: string | null
}
export interface SashaCourseInsights {
  course_id: number; days: number
  summary: { questions: number; active_students: number; students_needing_attention: number; average_struggle: number; high_concern_questions: number }
  students: SashaInsightStudent[]; concepts: SashaInsightConcept[]; recent: SashaRecentSignal[]
  privacy: string; generated_at: string | null
}

export const signalsAPI = {
  courseHotspots: async (courseId: number) => (await api.get<CourseHotspots>(`/signals/courses/${courseId}/hotspots`)).data,
  sashaInsights: async (courseId: number, days = 30) => (await api.get<SashaCourseInsights>(`/signals/courses/${courseId}/sasha-insights`, { params: { days } })).data,
  myProfile: async (courseId?: number) => (await api.get<StruggleProfile>('/signals/me/profile', { params: courseId ? { course_id: courseId } : undefined })).data,
  studentProfile: async (userId: number, courseId: number) => (await api.get<StruggleProfile>(`/signals/students/${userId}/profile`, { params: { course_id: courseId } })).data,
  heatmap: async (lessonId: number, userId?: number) => (await api.get<Heatmap>(`/signals/lessons/${lessonId}/heatmap`, { params: userId ? { user_id: userId } : undefined })).data,
  addMarker: async (lessonId: number, time_s: number, concept: string) => (await api.post<{ markers: Heatmap['markers'] }>(`/signals/lessons/${lessonId}/markers`, { time_s, concept })).data.markers,
  removeMarker: async (lessonId: number, markerId: number) => (await api.delete<{ markers: Heatmap['markers'] }>(`/signals/lessons/${lessonId}/markers/${markerId}`)).data.markers,
  buildAdaptive: async (courseId: number, count = 8, focus: string[] = []) => {
    const params = new URLSearchParams({ count: String(count) })
    focus.forEach((concept) => params.append('focus', concept))
    return (await api.post<AdaptiveBuild>(`/signals/adaptive/${courseId}/build`, null, { params })).data
  },
  submitAdaptive: async (sessionId: number, answers: Record<string, string | string[]>) => (await api.post<AdaptiveResult>(`/signals/adaptive/${sessionId}/submit`, { answers })).data,
}
