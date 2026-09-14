import { api } from './axios'
export interface DraftContent { title: string; type: 'multiple_choice' | 'multiple_select' | 'true_false' | 'fill_in_blanks' | 'short_answer'; options: string[]; answer: string | number | number[]; explanation: string; difficulty: 'easy' | 'medium' | 'hard'; concept: string; purpose: 'practice' | 'followup'; version?: number }
export interface StudioQuestion extends DraftContent { id: number; bank_question_id: number; status: 'draft' | 'reviewed' | 'published' | 'retired'; version: number; history: { action: string; note: string; at: string }[] }
export interface CoverageRow { concept: string; lessons: number; practice_questions: number; reserved_followups: number; practice_ready: boolean; followup_ready: boolean; needs_support: number; outcomes: { interventions: number; completed_checks: number; graded_questions: number; valid_followups: number; followups_passed: number; paired_learners: number; mean_practice_to_followup_change: number | null } }
export interface StudioData { course_id: number; concepts: CoverageRow[]; questions: StudioQuestion[]; lessons: { id: number; title: string; published: boolean; concepts: string[] }[]; live_questions: { id: number; title: string; concepts: string[] }[] }
export interface BankItem extends Omit<DraftContent, 'concept' | 'purpose'> { id: number; bank_title: string }
export const studioAPI = {
  courses: async () => (await api.get<{ courses: { id: number; title: string }[] }>('/assessment-studio/courses')).data.courses,
  detail: async (id: number) => (await api.get<StudioData>(`/assessment-studio/courses/${id}`)).data,
  banks: async () => (await api.get<{ questions: BankItem[] }>('/assessment-studio/bank-questions')).data.questions,
  save: async (course: number, body: DraftContent, id?: number) => (id ? await api.put<StudioQuestion>(`/assessment-studio/questions/${id}`, body) : await api.post<StudioQuestion>(`/assessment-studio/courses/${course}/questions`, body)).data,
  action: async (id: number, version: number, action: 'review' | 'publish' | 'retire', note: string) => (await api.post<StudioQuestion>(`/assessment-studio/questions/${id}/action`, { version, action, note })).data,
  link: async (course: number, kind: 'lesson' | 'question', ref_id: number, concept: string) => (await api.post(`/assessment-studio/courses/${course}/links`, { kind, ref_id, concept })).data,
  import: async (course: number, bank_question_id: number, concept: string, purpose: string) => (await api.post(`/assessment-studio/courses/${course}/import`, { bank_question_id, concept, purpose })).data,
}
