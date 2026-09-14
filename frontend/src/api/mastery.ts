/**
 * Learner mastery graph client (v2.0 §9.5 / §8.3 — WP3). Mirrors
 * backend/app/routers/mastery.py. Prefix '/mastery' is in axios noSlashEndpoints.
 */
import { api } from './axios'

export type LinkKind = 'quiz' | 'question' | 'game' | 'h5p' | 'lab' | 'three_d_task' | 'lesson' | 'assignment' | 'course'

export interface ConceptNode {
  concept: string
  estimate: number
  confidence: number
  level: 'novice' | 'developing' | 'proficient' | 'mastered'
  evidence_count: number
  last_evidence_at: string | null
  requires: string[]
  prerequisite_gaps: string[]
}

export interface LearnerGraph {
  user_id: number
  concepts: ConceptNode[]
  weak_concepts: string[]
  recover_first: { concept: string; recover_first: string[] }[]
  overall: number
  overall_level: string
}

export interface EvidenceRow {
  source_kind: string
  source_ref: string
  score_pct: number
  weight: number
  course_id: number | null
  detail: Record<string, unknown> | null
  created_at: string
}

export interface CoverageElement {
  kind: LinkKind
  ref_id: string
  title: string
  role: string
  content_type?: string
  practice_only?: boolean
  concepts: string[]
}

export interface CoverageRow {
  concept: string
  taught_by: string[]
  assessed_by: string[]
  is_target: boolean
  gap: 'no_teaching' | 'no_assessment' | 'target_uncovered' | null
}

export interface Coverage {
  course_id: number
  outcome: { text: string; target_concepts: string[] }
  elements: CoverageElement[]
  concepts: CoverageRow[]
  gaps: CoverageRow[]
  summary: { concepts: number; taught: number; assessed: number; targets: number; gaps: number }
}

export interface Milestone extends CoverageElement {
  state: 'not_started' | 'completed'
  score_pct: number | null
  concept_mastery: { concept: string; estimate: number | null }[]
  mastery: number | null
}

export const masteryAPI = {
  me: async () => (await api.get<LearnerGraph>('/mastery/me')).data,
  student: async (uid: number) => (await api.get<LearnerGraph>(`/mastery/students/${uid}`)).data,
  evidence: async (uid: number, concept: string) =>
    (await api.get<{ concept: string; evidence: EvidenceRow[] }>(`/mastery/students/${uid}/concepts/${encodeURIComponent(concept)}`)).data,
  links: async (kind: LinkKind, ref: string | number) =>
    (await api.get<{ concepts: string[] }>(`/mastery/links/${kind}/${encodeURIComponent(String(ref))}`)).data.concepts,
  setLinks: async (kind: LinkKind, ref: string | number, concepts: string[], course_id?: number) =>
    (await api.put<{ concepts: string[] }>(`/mastery/links/${kind}/${encodeURIComponent(String(ref))}`, { concepts, course_id })).data.concepts,
  prerequisites: async (concept?: string) =>
    (await api.get<{ prerequisites: { concept: string; requires: string }[] }>('/mastery/prerequisites', { params: concept ? { concept } : undefined })).data.prerequisites,
  addPrerequisite: async (concept: string, requires: string) =>
    (await api.put('/mastery/prerequisites', { concept, requires })).data,
  removePrerequisite: async (concept: string, requires: string) =>
    (await api.delete('/mastery/prerequisites', { params: { concept, requires } })).data,
  coverage: async (courseId: number) => (await api.get<Coverage>(`/mastery/courses/${courseId}/coverage`)).data,
  outcome: async (courseId: number) =>
    (await api.get<{ outcome_text: string; target_concepts: string[] }>(`/mastery/courses/${courseId}/outcome`)).data,
  setOutcome: async (courseId: number, outcome_text: string, target_concepts: string[]) =>
    (await api.put(`/mastery/courses/${courseId}/outcome`, { outcome_text, target_concepts })).data,
  progressMap: async (courseId: number, uid: number) =>
    (await api.get<{ course_id: number; user_id: number; progress_pct: number; milestones: Milestone[] }>(`/mastery/courses/${courseId}/students/${uid}/progress-map`)).data,
}

export function parseConcepts(text: string): string[] {
  return Array.from(new Set(text.split(',').map((s) => s.trim().toLowerCase()).filter(Boolean)))
}
