/**
 * Instructor growth tools client (roadmap R6) — mirrors backend/app/routers/course_ops.py.
 */
import { api } from './axios'

export interface CourseOut { id: number; title: string; status: string; course_type: string; is_template: boolean; owner_id: number }
export interface CloneOut extends CourseOut { copied: { lessons: number; quizzes: number; assignments: number } }
export interface TemplateOut extends CourseOut { lessons: number; excerpt: string }
export interface Collaborator { id: number; user_id: number; name: string; email: string; role: string; created_at: string | null }

export const courseOpsAPI = {
  clone: async (courseId: number, title?: string) => (await api.post<CloneOut>(`/course-ops/courses/${courseId}/clone`, { title })).data,
  setTemplate: async (courseId: number, is_template: boolean) => (await api.post<CourseOut>(`/course-ops/courses/${courseId}/template`, { is_template })).data,
  templates: async () => (await api.get<{ templates: TemplateOut[] }>('/course-ops/templates')).data.templates,
  useTemplate: async (courseId: number, title?: string) => (await api.post<CloneOut>(`/course-ops/templates/${courseId}/use`, { title })).data,
  csvHelp: async () => (await api.get<{ help: string; types: string[]; example: string }>('/course-ops/csv-help')).data,
  importQuizCsv: async (courseId: number, file: File, title: string, passingGrade = 50) => {
    const form = new FormData()
    form.append('file', file)
    form.append('title', title)
    form.append('passing_grade', String(passingGrade))
    return (await api.post<{ quiz_id: number; title: string; questions: number }>(`/course-ops/courses/${courseId}/quizzes/import-csv`, form)).data
  },
  collaborators: async (courseId: number) => (await api.get<{ owner_id: number; collaborators: Collaborator[] }>(`/course-ops/courses/${courseId}/collaborators`)).data,
  addCollaborator: async (courseId: number, email: string) => (await api.post<{ created: boolean; collaborators: Collaborator[] }>(`/course-ops/courses/${courseId}/collaborators`, { email })).data,
  removeCollaborator: async (courseId: number, userId: number) => (await api.delete<{ removed: number; collaborators: Collaborator[] }>(`/course-ops/courses/${courseId}/collaborators/${userId}`)).data,
}
