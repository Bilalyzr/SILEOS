import { api } from './axios'

export type CodingLanguage = 'python' | 'javascript' | 'typescript' | 'java' | 'cpp' | 'c'
export type ChallengeStatus = 'draft' | 'published' | 'retired'

export interface CodingCourse {
  id: number
  title: string
  status: string
  course_type: 'utporul'
}

export interface CodingTestCaseDraft {
  id?: number
  ordinal?: number
  visibility: 'sample' | 'hidden'
  input_text: string
  expected_output: string
  comparison: 'exact' | 'trimmed' | 'tokens'
  weight: number
}

export interface CodingChallengeDefinition {
  title: string
  problem_statement: string
  input_format: string
  output_format: string
  constraints_text: string
  allowed_languages: CodingLanguage[]
  starter_code: Partial<Record<CodingLanguage, string>>
  time_limit_ms: number
  memory_limit_mb: number
  max_source_bytes: number
  max_attempts: number
  test_cases: CodingTestCaseDraft[]
}

export interface EditorChallenge extends CodingChallengeDefinition {
  id: number
  course_id: number
  tenant_id: number | null
  slug: string
  status: ChallengeStatus
  version: number
  published_at: string | null
}

export interface ChallengeSummary {
  id: number
  slug: string
  course_id: number
  course_title: string
  title: string
  allowed_languages: CodingLanguage[]
  time_limit_ms: number
  memory_limit_mb: number
  max_attempts: number
  attempts_used: number
}

export interface LearnerChallenge extends Omit<EditorChallenge, 'test_cases'> {
  sample_cases: Array<{
    ordinal: number
    input_text: string
    expected_output: string
    comparison: string
  }>
  attempts_used: number
}

export interface CodingCaseResult {
  test_case_id: number | null
  visibility: 'sample' | 'hidden'
  status: string
  actual_output: string
  stderr: string
  execution_ms: number
  memory_kb: number
  score_awarded: number
}

export interface CodingSubmission {
  id: number
  challenge_id: number
  challenge_slug: string
  language: CodingLanguage
  source_code: string
  source_sha256: string
  status: 'queued' | 'running' | 'passed' | 'failed' | 'error' | 'cancelled'
  score: number
  passed_cases: number
  total_cases: number
  error_code: string
  attempt_number: number
  judge_version: string
  submitted_at: string
  started_at: string | null
  completed_at: string | null
  results: CodingCaseResult[]
}

export const codingAPI = {
  editorCourses: async () =>
    (await api.get<CodingCourse[]>('/utporul/coding/courses')).data,
  editorChallenges: async (courseId: number) =>
    (await api.get<EditorChallenge[]>(`/utporul/coding/courses/${courseId}/challenges`)).data,
  create: async (courseId: number, body: CodingChallengeDefinition) =>
    (await api.post<EditorChallenge>(`/utporul/coding/courses/${courseId}/challenges`, body)).data,
  update: async (challengeId: number, body: CodingChallengeDefinition & { version: number }) =>
    (await api.put<EditorChallenge>(`/utporul/coding/challenges/${challengeId}`, body)).data,
  action: async (challengeId: number, version: number, action: 'publish' | 'retire') =>
    (await api.post<EditorChallenge>(`/utporul/coding/challenges/${challengeId}/action`, {
      action,
      version,
      reason: action === 'publish' ? 'Instructor review complete' : 'Retired by instructor',
    })).data,
  learnerChallenges: async () =>
    (await api.get<ChallengeSummary[]>('/utporul/coding/learner/challenges')).data,
  learnerChallenge: async (slug: string) =>
    (await api.get<LearnerChallenge>(`/utporul/coding/challenges/${slug}`)).data,
  submit: async (slug: string, language: CodingLanguage, sourceCode: string, idempotencyKey: string) =>
    (await api.post<CodingSubmission>(`/utporul/coding/challenges/${slug}/submissions`, {
      language,
      source_code: sourceCode,
      idempotency_key: idempotencyKey,
    })).data,
  submission: async (submissionId: number) =>
    (await api.get<CodingSubmission>(`/utporul/coding/submissions/${submissionId}`)).data,
}
