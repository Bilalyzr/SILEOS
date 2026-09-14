/**
 * Gradebook + grading-queue API (plan Task 3, consuming backend/app/routers/gradebook.py
 * and the quiz manual-grading endpoints added in Task 1/2).
 */
import { api } from './axios'

export interface GradebookItem {
  type: 'quiz' | 'assignment'
  id: number
  title: string
  max: number
}

export interface GradebookCell {
  score: number | null
  max: number
  status: 'graded' | 'pending' | 'missing' | 'late'
  is_late?: boolean
}

export interface GradebookRow {
  student: { id: number; name: string; email: string | null }
  cells: Record<string, GradebookCell>
}

export interface GradebookMatrix {
  items: GradebookItem[]
  rows: GradebookRow[]
}

export const getGradebook = async (courseId: number): Promise<GradebookMatrix> => {
  const response = await api.get(`/courses/${courseId}/gradebook`)
  return response.data
}

export const getGradebookCsv = async (courseId: number): Promise<Blob> => {
  const response = await api.get(`/courses/${courseId}/gradebook.csv`, { responseType: 'blob' })
  return response.data
}

export interface QuizEssayQueueEntry {
  type: 'quiz_essay'
  attempt_id: number
  quiz_id: number
  quiz_title: string | null
  course_id: number
  student_id: number
  student_name: string
  student_email: string | null
  submitted_at: string | null
  manual_answer_ids: number[]
  ungraded_answer_ids: number[]
}

export interface AssignmentQueueEntry {
  type: 'assignment'
  submission_id: number
  assignment_id: number
  assignment_title: string | null
  course_id: number
  student_id: number
  student_name: string
  student_email: string | null
  submitted_at: string | null
  is_late: boolean
}

export type GradingQueueEntry = QuizEssayQueueEntry | AssignmentQueueEntry

export const getGradingQueue = async (
  courseId: number
): Promise<{ queue: GradingQueueEntry[]; count: number }> => {
  const response = await api.get(`/courses/${courseId}/grading-queue`)
  return response.data
}

// -- Quiz manual grading (essay/open-ended answers within a pending_review attempt) --

export interface QuizAttemptQuestionForGrading {
  question_id: number
  question: string
  type: string
  points: number
  user_answer: string | number | null
  achieved_mark: number | null
  needs_review: boolean
  /** QuizAttemptAnswer PK — pass to gradeQuizAnswer. Only present on
   * manually-graded questions of a submitted attempt. */
  attempt_answer_id?: number | null
}

export const getQuizAttemptResults = async (attemptId: number) => {
  const response = await api.get(`/quiz-attempts/${attemptId}/results`)
  return response.data
}

export const gradeQuizAnswer = async (
  attemptId: number,
  answerId: number,
  data: { achieved_mark: number; feedback?: string }
) => {
  const response = await api.post(`/quiz-attempts/${attemptId}/answers/${answerId}/grade`, data)
  return response.data
}

export const finalizeQuizAttempt = async (attemptId: number) => {
  const response = await api.post(`/quiz-attempts/${attemptId}/finalize`)
  return response.data
}
