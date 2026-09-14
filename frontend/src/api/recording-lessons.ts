import { api } from './axios'
export interface Segment { start: number; end: number; text: string }
export interface Chapter { start: number; title: string }
export interface RecordingWork {
  id: number; class_id: number; course_id: number; status: string; version: number; language: string
  attempts: number; error: string | null; title: string; notes: string; segments: Segment[]; chapters: Chapter[]
  concepts: string[]; question_ids: number[]; lesson_id: number | null; lesson_status: string | null
  suggestions: { concept: string; title: string; answer: string; explanation: string }[]
}
export interface RecordingClass { class_id: number; course_id: number; title: string; status: string; lesson_id: number | null; has_recording: boolean }
export interface LocalTranscription { configured: boolean; note: string }
export interface RecordingReader { class_id: number; course_id: number; title: string; notes: string; segments: Segment[]; chapters: Chapter[]; language: string; recording_available: boolean }
const root = '/recording-lessons'
export const recordingAPI = {
  list: async () => (await api.get<{classes: RecordingClass[]; transcription: LocalTranscription}>(root)).data,
  detail: async (id: number) => (await api.get<{work: RecordingWork | null; transcription: LocalTranscription}>(`${root}/${id}`)).data,
  transcribe: async (id: number, language: string, version?: number) => (await api.post<RecordingWork>(`${root}/${id}/transcribe`, {language, version})).data,
  save: async (work: RecordingWork) => (await api.put<RecordingWork>(`${root}/${work.class_id}`, {version: work.version, title: work.title, notes: work.notes, chapters: work.chapters, concepts: work.concepts, segments: work.segments})).data,
  action: async (id: number, version: number, action: 'create-lesson' | 'assessment-drafts') => (await api.post<RecordingWork>(`${root}/${id}/${action}`, {version})).data,
  reader: async (id: number) => (await api.get<RecordingReader>(`${root}/${id}/reader`)).data,
}
