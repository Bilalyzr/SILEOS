import { api } from './axios'

export interface MathSession {
  id: number; course_id: number; version: string; sequence: number;
  stage: 'predict' | 'diagnose' | 'build' | 'transfer' | 'waiting' | 'retention' | 'complete';
  due_at: string | null; expires_at: string; hypothesis_note: string | null;
  intervention: string | null; explanation: string | null; notice: string;
  transfer_score: number | null; retention_score: number | null; feedback?: string;
  task: { prompt?: string; options?: string[]; questions?: string[] };
}
export interface MathData {
  catalog: { version: string; topic: string; notice: string };
  courses: { id: number; title: string; approved: boolean }[];
  sessions: MathSession[];
}
export interface MathEvidence extends MathSession {
  learner_id: number;
  events: { sequence: number; action: string; payload: Record<string, unknown>; result: Record<string, unknown> }[];
}
export interface MathReview {
  version: string; approved: boolean; review_note: string | null;
  material: Record<string, unknown>;
}
export const mathPilot = {
  me: async () => (await api.get<MathData>('/math-pilot/me')).data,
  start: async (course_id: number) => (await api.post<MathSession>('/math-pilot/sessions', { course_id, acknowledge: true })).data,
  answer: async (row: MathSession, answers: number[], key: string) => (await api.post<MathSession>(`/math-pilot/sessions/${row.id}/answers`, {
    version: row.version, sequence: row.sequence, stage: row.stage, answers, key,
  })).data,
  export: async (id: number) => (await api.get(`/math-pilot/sessions/${id}/export`)).data as unknown,
  remove: async (id: number) => { await api.delete(`/math-pilot/sessions/${id}`) },
  review: async (id: number) => (await api.get<MathReview>(`/math-pilot/courses/${id}/review`)).data,
  approve: async (id: number, version: string, note: string) => { await api.post(`/math-pilot/courses/${id}/approve`, {
    version, note, content_reviewed: true, data_arrangements_reviewed: true,
  }) },
  pause: async (id: number) => { await api.delete(`/math-pilot/courses/${id}/approve`) },
  evidence: async (id: number, offset = 0) => (await api.get<{ items: MathEvidence[]; notice: string }>(`/math-pilot/courses/${id}/evidence`, { params: { offset } })).data,
  override: async (row: MathSession, intervention: string, note: string) => {
    await api.post(`/math-pilot/sessions/${row.id}/review`, { key: crypto.randomUUID(), sequence: row.sequence, intervention, note })
  },
}
