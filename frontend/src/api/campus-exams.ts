import { api } from "./axios";

const root = (id: number) => `/institutions/${id}/exams`;

export type ExamKind = "unit" | "midterm" | "final" | "practical" | "other";
export type ExamStatus = "draft" | "scheduled" | "published";

export interface ExamPaper {
  id: number;
  exam_id: number;
  batch_id: number;
  batch_name: string | null;
  subject: string;
  max_marks: number;
  pass_marks: number;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
  room: string;
  event_id: number | null;
  marks_entered: number;
  students: number;
}

export interface Exam {
  id: number;
  term_id: number;
  term_name: string | null;
  name: string;
  kind: ExamKind;
  status: ExamStatus;
  published_at: string | null;
  papers: ExamPaper[];
}

export interface RosterRow {
  member_id: number;
  name: string;
  roll_number: string;
  marks: number | null;
  absent: boolean;
  remarks: string;
}

export interface MarkEntry {
  member_id: number;
  marks: number | null;
  absent: boolean;
  remarks: string;
}

export interface HallTicket {
  id: number;
  member_id: number;
  batch_id: number;
  name: string;
  roll_number: string;
  token: string;
  issued_at: string | null;
}

export interface ResultRow {
  member_id: number;
  name: string;
  roll_number: string;
  marks: Record<number, { marks: number | null; absent: boolean; remarks: string }>;
  total: number;
  max_total: number;
  percent: number | null;
  passed: boolean;
  rank: number;
}

export interface ResultsTable {
  exam: { id: number; name: string; status: ExamStatus };
  batch_id: number;
  batch_name: string | null;
  papers: { id: number; subject: string; max_marks: number; pass_marks: number }[];
  rows: ResultRow[];
}

export interface MyResult extends ResultRow {
  exam: { id: number; name: string; status: ExamStatus };
  batch_id: number;
  batch_name: string | null;
  papers: { id: number; subject: string; max_marks: number; pass_marks: number }[];
  students: number;
}

export interface PaperInput {
  batch_id: number;
  subject: string;
  max_marks: number;
  pass_marks: number;
  starts_at: string;
  duration_minutes: number;
  room: string;
}

export const examsApi = {
  list: async (id: number, termId?: number, studentUserId?: number) =>
    (
      await api.get<Exam[]>(root(id), {
        params: { term_id: termId, student_user_id: studentUserId },
      })
    ).data,
  create: async (id: number, data: { term_id: number; name: string; kind: ExamKind }) =>
    (await api.post<Exam>(root(id), data)).data,
  update: async (id: number, examId: number, data: { name?: string; kind?: ExamKind }) =>
    (await api.patch<Exam>(`${root(id)}/${examId}`, data)).data,
  publish: async (id: number, examId: number) =>
    (await api.post<Exam>(`${root(id)}/${examId}/publish`)).data,
  unpublish: async (id: number, examId: number) =>
    (await api.post<Exam>(`${root(id)}/${examId}/unpublish`)).data,
  createPaper: async (id: number, examId: number, data: PaperInput) =>
    (await api.post<ExamPaper>(`${root(id)}/${examId}/papers`, data)).data,
  updatePaper: async (id: number, examId: number, paperId: number, data: Partial<PaperInput>) =>
    (await api.patch<ExamPaper>(`${root(id)}/${examId}/papers/${paperId}`, data)).data,
  deletePaper: (id: number, examId: number, paperId: number) =>
    api.delete(`${root(id)}/${examId}/papers/${paperId}`),
  roster: async (id: number, examId: number, paperId: number) =>
    (await api.get<RosterRow[]>(`${root(id)}/${examId}/papers/${paperId}/marks`)).data,
  putMarks: async (id: number, examId: number, paperId: number, entries: MarkEntry[]) =>
    (await api.put<RosterRow[]>(`${root(id)}/${examId}/papers/${paperId}/marks`, { entries })).data,
  hallTickets: async (id: number, examId: number, batchId?: number) =>
    (await api.get<HallTicket[]>(`${root(id)}/${examId}/hall-tickets`, { params: { batch_id: batchId } })).data,
  hallTicketPdf: async (id: number, examId: number, memberId: number, studentUserId?: number) =>
    (
      await api.get<Blob>(`${root(id)}/${examId}/hall-tickets/${memberId}/pdf`, {
        params: { student_user_id: studentUserId },
        responseType: "blob",
      })
    ).data,
  myHallTicketPdf: async (id: number, examId: number, studentUserId?: number) =>
    (
      await api.get<Blob>(`${root(id)}/${examId}/hall-tickets/me/pdf`, {
        params: { student_user_id: studentUserId },
        responseType: "blob",
      })
    ).data,
  results: async (id: number, examId: number, batchId: number) =>
    (await api.get<ResultsTable>(`${root(id)}/${examId}/results`, { params: { batch_id: batchId } })).data,
  myResults: async (id: number, examId: number, studentUserId?: number) =>
    (await api.get<MyResult>(`${root(id)}/${examId}/results/me`, { params: { student_user_id: studentUserId } })).data,
  marksheetPdf: async (id: number, examId: number, memberId: number, studentUserId?: number) =>
    (
      await api.get<Blob>(`${root(id)}/${examId}/results/${memberId}/marksheet.pdf`, {
        params: { student_user_id: studentUserId },
        responseType: "blob",
      })
    ).data,
};

export function openBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
