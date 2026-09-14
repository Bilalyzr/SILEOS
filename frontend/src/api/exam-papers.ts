import { api } from "./axios";
export interface PriceSlab {
  id: number;
  exam: "JEE" | "NEET";
  title: string;
  min_questions: number;
  max_questions: number;
  price_paise: number;
  active: boolean;
}
export interface PaperQuestion {
  question_title: string;
  options?: string[];
  correct_answer: string | number;
  answer_explanation?: string;
  question_type: string;
}
export interface ExamPaper {
  id: string;
  exam: string;
  title: string;
  question_count: number;
  status: string;
  amount_paise: number;
  bank_id?: number;
  error?: string;
  questions?: PaperQuestion[];
}
export const money = (paise: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(
    paise / 100,
  );
export const paperError = (error: any) =>
  typeof error?.response?.data?.detail === "string"
    ? error.response.data.detail
    : "Could not complete this request. Please try again.";
export const examAPI = {
  pricing: () =>
    api
      .get<{
        slabs: PriceSlab[];
        staff_access: boolean;
        generation_available: boolean;
      }>("/exam-papers/pricing")
      .then((r) => r.data),
  list: () =>
    api.get<{ papers: ExamPaper[] }>("/exam-papers").then((r) => r.data.papers),
  get: (id: string) =>
    api.get<ExamPaper>(`/exam-papers/${id}`).then((r) => r.data),
  generate: (id: string) =>
    api.post<ExamPaper>(`/exam-papers/${id}/generate`).then((r) => r.data),
};
