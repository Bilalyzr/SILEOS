/**
 * 3D match-and-verify tasks client (v2.0 §6, WP2) — mirrors
 * backend/app/routers/three_d_tasks.py. Prefix '/three-d-tasks' is in axios
 * noSlashEndpoints. Grading happens server-side from submitted state.
 */
import { api } from './axios'
import type { Tier } from './scorable'

export type TaskType = 'match' | 'identify' | 'verify' | 'assemble' | 'measure' | 'manipulate' | 'sequence'
export const TASK_TYPES: TaskType[] = ['match', 'identify', 'verify', 'assemble', 'measure', 'manipulate', 'sequence']
export const TASK_TYPE_INFO: Record<TaskType, { label: string; learner: string; graded: string }> = {
  match: { label: 'Match', learner: 'Match labels to parts of the object', graded: 'Correct anchor per label, partial credit' },
  identify: { label: 'Identify', learner: 'Select the part that satisfies a condition', graded: 'Selected anchor against the expected one' },
  verify: { label: 'Verify', learner: 'Manipulate parameters to prove or disprove a claim', graded: 'Verdict + final state + whether the path tested the claim' },
  assemble: { label: 'Assemble', learner: 'Put exploded parts back into their slots', graded: 'Each part in its correct slot' },
  measure: { label: 'Measure', learner: 'Determine a quantity with the ruler', graded: 'Numeric answer within tolerance' },
  manipulate: { label: 'Manipulate to target', learner: 'Adjust parameters until a condition holds', graded: 'Each parameter within its accepted range' },
  sequence: { label: 'Sequence', learner: 'Perform steps in the right order', graded: 'Each step in its correct position' },
}

export interface Anchor { id: string; label: string; region?: string | null; position: number[]; description?: string | null }
export interface Parameter { id: string; label: string; min: number; max: number; step?: number | null; unit?: string | null; default?: number | null }
export interface ParamRange { param_id: string; min: number; max: number }

export interface MatchConfig { anchors: Anchor[]; pairs: { label: string; anchor_id: string }[]; intro?: string | null }
export interface IdentifyConfig { anchors: Anchor[]; prompts: { condition: string; anchor_id: string }[]; intro?: string | null }
export interface VerifyConfig { parameters: Parameter[]; anchors?: Anchor[]; claim: string; claim_holds: boolean; expected_state: ParamRange[]; must_explore: ParamRange[]; intro?: string | null }
export interface AssembleConfig { slots: { id: string; label: string }[]; parts: { id: string; label: string; slot_id: string; position?: number[] | null }[]; intro?: string | null }
export interface MeasureConfig { anchors?: Anchor[]; questions: { prompt: string; answer: number; tolerance: number; unit?: string | null; anchor_a?: string | null; anchor_b?: string | null }[]; intro?: string | null }
export interface ManipulateConfig { parameters: Parameter[]; anchors?: Anchor[]; targets: { prompt: string; param_id: string; min: number; max: number }[]; intro?: string | null }
export interface SequenceConfig { steps: { id: string; text: string }[]; anchors?: Anchor[]; intro?: string | null }
export type TaskConfig = MatchConfig | IdentifyConfig | VerifyConfig | AssembleConfig | MeasureConfig | ManipulateConfig | SequenceConfig

export interface ThreeDTask {
  id: number
  owner_id: number
  model_id: number
  title: string
  task_type: TaskType
  concepts: string[]
  tier_floor: Tier
  status: 'draft' | 'published'
  max_score: number
  config?: TaskConfig
  created_at: string
  updated_at: string
}

export interface TaskPlay extends ThreeDTask { config: TaskConfig; best_score: number | null; attempts: number }

export interface EvidenceEvent { type: string; t: number; [k: string]: string | number | boolean | null | undefined }

export interface AttemptResult {
  id: number | null
  score: number
  max_score: number
  grading: Record<string, unknown>
  confidence: 'clean' | 'mixed' | 'trial_and_error' | 'unknown'
  confidence_detail: Record<string, number | string>
  preview: boolean
  best_score: number
}

export const threeDTasksAPI = {
  mine: async () => (await api.get<{ tasks: ThreeDTask[] }>('/three-d-tasks/mine')).data.tasks,
  /** Published tasks on one model (learner check-yourself strip, editor teaching kit) */
  forModel: async (modelId: number) => (await api.get<{ tasks: ThreeDTask[] }>(`/three-d-tasks/for-model/${modelId}`)).data.tasks,
  get: async (id: number) => (await api.get<ThreeDTask>(`/three-d-tasks/${id}`)).data,
  create: async (payload: { title: string; model_id: number; task_type: TaskType; config: TaskConfig; concepts?: string[]; tier_floor?: Tier }) =>
    (await api.post<ThreeDTask>('/three-d-tasks', payload)).data,
  update: async (id: number, payload: Partial<{ title: string; model_id: number; task_type: TaskType; config: TaskConfig; concepts: string[]; tier_floor: Tier }>) =>
    (await api.put<ThreeDTask>(`/three-d-tasks/${id}`, payload)).data,
  publish: async (id: number) => (await api.post<ThreeDTask>(`/three-d-tasks/${id}/publish`)).data,
  unpublish: async (id: number) => (await api.post<ThreeDTask>(`/three-d-tasks/${id}/unpublish`)).data,
  remove: async (id: number) => (await api.delete(`/three-d-tasks/${id}`)).data,
  play: async (id: number) => (await api.get<TaskPlay>(`/three-d-tasks/${id}/play`)).data,
  submit: async (id: number, payload: { answers: Record<string, unknown>; evidence: EvidenceEvent[]; duration_s: number; mode: Tier }) =>
    (await api.post<AttemptResult>(`/three-d-tasks/${id}/attempts`, payload)).data,
  attempts: async (id: number) =>
    (await api.get<{ attempts: { id: number; user_id: number; score: number; max_score: number; mode: string; confidence: string; confidence_detail: Record<string, number | string>; duration_s: number; created_at: string }[] }>(`/three-d-tasks/${id}/attempts`)).data.attempts,
}
