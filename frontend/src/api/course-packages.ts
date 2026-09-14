import { api } from "./axios";
export interface CoursePackagePreview {
  id: string;
  kind: "backup" | "documents";
  filename: string;
  status: string;
  course_id: number | null;
  expires_at: string;
  warnings: string[];
  preview: {
    title: string;
    lessons: number;
    quizzes: number;
    assignments: number;
    assessment_drafts: number;
    dependencies: Record<string, number>;
    lesson_titles: string[];
    categories?: Record<string, number>;
    assets?: {filename: string; category: string; size: number}[];
  };
}
export const coursePackagesAPI = {
  courses: async () =>
    (
      await api.get<{
        courses: { id: number; title: string; status: string }[];
      }>("/course-packages/courses")
    ).data.courses,
  previews: async () =>
    (
      await api.get<{ previews: CoursePackagePreview[] }>(
        "/course-packages/previews",
      )
    ).data.previews,
  inspect: async (files: File[], progress: (percent: number) => void) => {
    const body = new FormData();
    files.forEach((file) => body.append("files", file));
    return (
      await api.post<CoursePackagePreview>("/course-packages/inspect", body, {
        onUploadProgress: (e) => {
          if (e.total) progress(Math.round((100 * e.loaded) / e.total));
        },
      })
    ).data;
  },
  restore: async (id: string, title: string) =>
    (
      await api.post<{
        course_id: number;
        status: string;
        already_restored: boolean;
      }>(`/course-packages/previews/${id}/restore`, { title })
    ).data,
  discard: async (id: string) => api.delete(`/course-packages/previews/${id}`),
  backup: async (id: number) =>
    (
      await api.get<Blob>(`/course-packages/courses/${id}/backup`, {
        responseType: "blob",
      })
    ).data,
};
