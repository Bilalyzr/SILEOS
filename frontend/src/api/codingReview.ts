import { api } from './axios'

export interface ReviewComment {
  id: number
  submission_id: number
  line: number
  body: string
  status: 'open' | 'resolved'
  author_name: string
  author_is_staff: boolean
  created_at: string | null
  resolved_at: string | null
}

export interface ReviewQueueItem {
  submission_id: number
  challenge_slug: string
  challenge_title: string
  learner_name: string
  language: string
  status: string
  score: number
  submitted_at: string | null
  requested_at: string | null
  open_comments: number
}

export interface ReviewQueue {
  course_id: number
  count: number
  items: ReviewQueueItem[]
}

export const codingReviewAPI = {
  comments: async (submissionId: number) =>
    (await api.get<ReviewComment[]>(`/utporul/coding/submissions/${submissionId}/comments`)).data,
  addComment: async (submissionId: number, line: number, body: string) =>
    (await api.post<ReviewComment>(`/utporul/coding/submissions/${submissionId}/comments`, { line, body })).data,
  resolve: async (commentId: number) =>
    (await api.post<ReviewComment>(`/utporul/coding/comments/${commentId}/resolve`)).data,
  requestReview: async (submissionId: number) =>
    (await api.post<{ submission_id: number; requested: boolean; reviewed: boolean }>(
      `/utporul/coding/submissions/${submissionId}/review-request`,
    )).data,
  markReviewed: async (submissionId: number) =>
    (await api.post<{ submission_id: number; requested: boolean; reviewed: boolean }>(
      `/utporul/coding/submissions/${submissionId}/review-done`,
    )).data,
  queue: async (courseId: number) =>
    (await api.get<ReviewQueue>(`/utporul/coding/courses/${courseId}/review-queue`)).data,
}
