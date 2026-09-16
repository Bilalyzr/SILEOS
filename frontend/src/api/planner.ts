import { isAxiosError } from 'axios'
import { api } from './axios'
import type { AdaptiveBuild } from './signals'

export interface PlanOutcome { note: string; freshness_note?: string; new_question_count?: number; reused_question_count?: number; score?: number; questions?: number; enough_evidence?: boolean; intervention_status?: string; results?: { question_id: number; correct: boolean; expected: string[]; explanation?: string }[] }
export interface PlanTask { id: number; kind: 'lesson' | 'review' | 'practice' | 'followup'; title: string; reason: string; concept: string | null; minutes: number; due_date: string; not_before: string; status: 'pending' | 'done' | 'skipped'; session_id: number | null; intervention_id: number | null; lesson_url: string | null; outcome: PlanOutcome | null }
export interface Intervention { id: number; concept: string; status: 'suggested' | 'monitoring' | 'needs_instructor' | 'resolved' | 'dismissed'; reason: string; baseline_score: number | null; latest_score: number | null; followup_score: number | null; instructor_note: string | null; change: number | null; reviewed_at: string | null }
export interface PlanGoal { id: number; course_id: number; title: string; target_date: string; daily_minutes: number; timezone: string; status: 'active' | 'paused'; today: string; estimated_finish: string; warnings: string[]; remaining_minutes: number; tasks: PlanTask[]; interventions: Intervention[] }
export interface GoalInput { course_id: number; title: string; target_date: string; daily_minutes: number; timezone: string; status: 'active' | 'paused' }
export interface PlannerData { courses: { id: number; title: string }[]; goals: PlanGoal[] }
export interface QueueIntervention extends Intervention { goal_id: number; course_id: number; course_title: string; learner_id: number; learner_name: string; goal_status: 'active' | 'paused' }
export function plannerError(error: unknown): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') return error.response.data.detail
  return 'This request could not be completed. Please try again.'
}
export const plannerAPI = {
  me: async () => (await api.get<PlannerData>('/planner/me')).data,
  save: async (goal: GoalInput) => (await api.post<PlanGoal>('/planner/goals', goal)).data,
  refresh: async (id: number) => (await api.post<PlanGoal>(`/planner/goals/${id}/refresh`)).data,
  action: async (id: number, action: 'done' | 'snooze') => (await api.post<PlanGoal>(`/planner/tasks/${id}/action`, { action })).data,
  start: async (id: number) => (await api.post<AdaptiveBuild>(`/planner/tasks/${id}/start`)).data,
  submit: async (id: number, answers: Record<string, string | string[]>) => (await api.post<{ outcome: PlanOutcome; goal: PlanGoal }>(`/planner/tasks/${id}/submit`, { answers })).data,
  queue: async () => (await api.get<{ interventions: QueueIntervention[] }>('/planner/instructor/interventions')).data,
  review: async (id: number, action: 'dismiss' | 'request_check', note: string) => (await api.post<Intervention>(`/planner/instructor/interventions/${id}/review`, { action, note })).data,
}
export const interventionLabels: Record<Intervention['status'], string> = { suggested: 'Check suggested', monitoring: 'Follow-up scheduled', needs_instructor: 'Instructor support needed', resolved: 'Retention check passed', dismissed: 'Closed by instructor' }
