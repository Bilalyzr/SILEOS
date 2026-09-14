/**
 * Studio faces client (v2.0 §4 — WP6) — mirrors backend/app/routers/studio.py.
 * Per-course Parent View Configurator, Reward System Designer, opening-face
 * dismissal and the SP Schedule Builder (term view + clone week).
 */
import { api } from './axios'

export type OpeningFace = 'asset_library' | 'schedule' | 'outcome' | 'curriculum'
export type ParentViewKey = 'attendance' | 'completion' | 'scores' | 'time_spent' | 'teacher_notes' | 'class_reports'
export const PARENT_VIEW_LABELS: Record<ParentViewKey, string> = {
  attendance: 'Live-class attendance',
  completion: 'Lesson completion / progress',
  scores: 'Quiz scores and at-risk flags',
  time_spent: 'Time spent learning',
  teacher_notes: 'Instructor notes',
  class_reports: 'Shared class reports',
}
export type BadgeRule = 'lessons_completed' | 'quizzes_passed' | 'live_classes_attended' | 'games_completed' | 'labs_completed' | 'streak_days'
export const BADGE_RULE_LABELS: Record<BadgeRule, string> = {
  lessons_completed: 'lessons completed',
  quizzes_passed: 'quizzes passed',
  live_classes_attended: 'live classes attended',
  games_completed: 'games completed',
  labs_completed: 'labs completed',
  streak_days: 'day streak',
}
export const POINT_ACTIVITIES: [string, string][] = [
  ['lesson_completed', 'Lesson completed'], ['quiz_passed', 'Quiz passed'], ['quiz_passed_bonus', 'Quiz ≥ 90% bonus'],
  ['assignment_submitted', 'Assignment submitted'], ['assignment_graded_pass', 'Assignment passed'],
  ['course_completed', 'Course completed'], ['live_class_attended', 'Live class attended'],
  ['h5p_completed', 'H5P completed'], ['game_completed', 'Game completed'], ['game_perfect', 'Game perfect score'],
  ['lab_completed', 'Lab completed'], ['lab_perfect', 'Lab perfect score'],
  ['three_d_task_completed', '3D task completed'], ['three_d_task_perfect', '3D task perfect score'],
]

export interface CourseBadge { name: string; slug?: string; rule: BadgeRule; threshold: number; points: number }
export interface Rewards {
  points: Record<string, number>
  badges: CourseBadge[]
  streak_freeze_days_per_month: number
  leaderboard_opt_out: boolean
}
export interface StudioSettings {
  course_id: number
  opening_face: OpeningFace
  parent_view: Record<ParentViewKey, boolean>
  rewards: Rewards
  face_dismissed: boolean
}
export interface ScheduleSession {
  kind: 'live'; class_id: number; title: string; start: string; end: string | null
  status: string | null; purpose: string | null; mode: string | null; has_recording: boolean
}
export interface TermSchedule {
  course_id: number
  weeks: { week_start: string; sessions: ScheduleSession[] }[]
  live_classes: number
  recorded_lessons: number
  assessments: number
}
export interface MyCourseRewards {
  course_id: number
  points_in_course: number
  badges: (CourseBadge & { earned: boolean; progress: number })[]
  leaderboard_opt_out: boolean
  streak_freeze_days_per_month: number
}

export const studioAPI = {
  settings: async (courseId: number) => (await api.get<StudioSettings>(`/studio/courses/${courseId}/settings`)).data,
  update: async (courseId: number, body: { parent_view?: Partial<Record<ParentViewKey, boolean>>; rewards?: Rewards; face_dismissed?: boolean }) =>
    (await api.put<StudioSettings>(`/studio/courses/${courseId}/settings`, body)).data,
  schedule: async (courseId: number) => (await api.get<TermSchedule>(`/studio/courses/${courseId}/schedule`)).data,
  cloneWeek: async (courseId: number, from_week_start: string, to_week_start: string) =>
    (await api.post<{ created: number[]; schedule: TermSchedule }>(`/studio/courses/${courseId}/schedule/clone-week`, { from_week_start, to_week_start })).data,
  myRewards: async (courseId: number) => (await api.get<MyCourseRewards>(`/studio/courses/${courseId}/rewards/me`)).data,
}
