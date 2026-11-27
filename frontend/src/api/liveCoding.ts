import { api } from './axios'
import type { CodingLanguage, CodingSubmission, LearnerChallenge } from './coding'

export interface LiveCodingChallenge {
  id: number
  class_id: number
  challenge_id: number
  challenge_slug: string
  challenge_title: string
  status: 'open' | 'closed'
  graded: boolean
  instructions: string
  pushed_at: string | null
  closed_at: string | null
  solution_revealed: boolean
  /** Null for learners until the instructor reveals it. */
  model_solution: string | null
}

export interface LiveBoardRow {
  user_id: number
  learner_name: string
  best_score: number
  passed: boolean
  attempts: number
  total_ms: number
  peak_memory_kb: number
  rank: number
}

export interface LiveBoard {
  live_id: number
  status: 'open' | 'closed'
  graded: boolean
  pending_submissions: number
  summary: { learners_submitted: number; learners_passed: number }
  /** Instructors only. */
  rows?: LiveBoardRow[]
  /** Learners only. */
  my_row?: LiveBoardRow | null
}

export interface LiveChallengePush {
  challenge_id: number
  graded: boolean
  instructions: string
  model_solution: string
}

export interface LearnerLiveChallenge {
  live: LiveCodingChallenge
  challenge: LearnerChallenge
}

export interface LiveSubmitResult {
  live_id: number
  counts_for_grade: boolean
  submission: CodingSubmission
}

export const liveCodingAPI = {
  list: async (classId: number) =>
    (await api.get<LiveCodingChallenge[]>(`/live/classes/${classId}/coding-challenges`)).data,
  push: async (classId: number, body: LiveChallengePush) =>
    (await api.post<LiveCodingChallenge>(`/live/classes/${classId}/coding-challenges`, body)).data,
  close: async (liveId: number) =>
    (await api.post<LiveCodingChallenge>(`/live/coding-challenges/${liveId}/close`)).data,
  reveal: async (liveId: number) =>
    (await api.post<LiveCodingChallenge>(`/live/coding-challenges/${liveId}/reveal`)).data,
  learnerView: async (liveId: number) =>
    (await api.get<LearnerLiveChallenge>(`/live/coding-challenges/${liveId}`)).data,
  submit: async (liveId: number, language: CodingLanguage, sourceCode: string, idempotencyKey: string) =>
    (await api.post<LiveSubmitResult>(`/live/coding-challenges/${liveId}/submissions`, {
      language,
      source_code: sourceCode,
      idempotency_key: idempotencyKey,
    })).data,
  board: async (liveId: number) =>
    (await api.get<LiveBoard>(`/live/coding-challenges/${liveId}/board`)).data,
}
