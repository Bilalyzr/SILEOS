import { api } from "./axios";

export type InstitutionRole = "owner" | "admin" | "teacher" | "student";
export interface Institution {
  id: number;
  name: string;
  slug: string;
  kind: "school" | "college";
  academic_year: string;
  timezone: string;
  description: string;
  plan: string;
  role: InstitutionRole;
}
export interface InstitutionInput {
  name: string;
  kind: "school" | "college";
  academic_year: string;
  timezone: string;
  description: string;
}
export interface InstitutionMember {
  id: number;
  user_id: number;
  name: string;
  email: string;
  role: InstitutionRole;
  department: string;
  status: string;
}
export interface InstitutionBatch {
  id: number;
  name: string;
  department: string;
  academic_year: string;
  student_count: number;
  member_ids: number[];
  assignments: {
    id: number;
    institution_course_id: number;
    due_date: string | null;
  }[];
}
export interface InstitutionCourse {
  id: number;
  course_id: number;
  title: string;
  status: string;
  can_edit: boolean;
}
export interface ProgressRow {
  batch_id: number;
  batch: string;
  student: string;
  user_id: number;
  course_id: number;
  course: string;
  due_date: string | null;
  progress: number;
  has_access: boolean;
}
export interface PlatformPlanRequest {
  id: number;
  institution: string;
  institution_id: number;
  plan: string;
  status: string;
  note: string;
  contact_email: string;
  created_at: string;
}
export interface InstitutionOverview {
  institution: Institution;
  members: InstitutionMember[];
  batches: InstitutionBatch[];
  courses: InstitutionCourse[];
  invites: {
    id: number;
    email: string;
    role: string;
    status: string;
    expires_at: string;
  }[];
  activity: {
    id: number;
    action: string;
    detail: string;
    created_at: string;
  }[];
  usage: {
    members: number;
    reserved_seats: number;
    batches: number;
    courses: number;
    limits: { members: number; batches: number; courses: number };
  } | null;
  plan_requests: {
    id: number;
    plan: string;
    status: string;
    created_at: string;
  }[];
  report: ProgressRow[];
}
const root = "/institutions";
export const institutionApi = {
  platformRequests: async () =>
    (await api.get<PlatformPlanRequest[]>(`${root}/platform/plan-requests`))
      .data,
  reviewRequest: async (id: number, status: string, note: string) =>
    api.patch(`${root}/platform/plan-requests/${id}`, { status, note }),
  list: async () => (await api.get<Institution[]>(root)).data,
  invitations: async () =>
    (
      await api.get<
        {
          id: number;
          institution_name: string;
          role: string;
          expires_at: string;
        }[]
      >(`${root}/invitations`)
    ).data,
  accept: async (id: number) =>
    (await api.post<Institution>(`${root}/invitations/${id}/accept`)).data,
  create: async (data: InstitutionInput) =>
    (await api.post<Institution>(root, data)).data,
  overview: async (id: number) =>
    (await api.get<InstitutionOverview>(`${root}/${id}`)).data,
  update: async (id: number, data: InstitutionInput) =>
    (await api.patch<Institution>(`${root}/${id}`, data)).data,
  invite: async (
    id: number,
    data: { email: string; role: string; department: string },
  ) => api.post(`${root}/${id}/invitations`, data),
  revoke: async (id: number, inviteId: number) =>
    api.delete(`${root}/${id}/invitations/${inviteId}`),
  updateMember: async (
    id: number,
    memberId: number,
    data: { role: string; department: string; status: string },
  ) => api.patch(`${root}/${id}/members/${memberId}`, data),
  batch: async (
    id: number,
    data: { name: string; department: string; academic_year: string },
  ) => api.post(`${root}/${id}/batches`, data),
  addStudents: async (id: number, batchId: number, member_ids: number[]) =>
    api.post(`${root}/${id}/batches/${batchId}/members`, { member_ids }),
  removeStudent: async (id: number, batchId: number, memberId: number) =>
    api.delete(`${root}/${id}/batches/${batchId}/members/${memberId}`),
  available: async (id: number) =>
    (
      await api.get<{ id: number; title: string; status: string }[]>(
        `${root}/${id}/available-courses`,
      )
    ).data,
  connect: async (id: number, course_id: number) =>
    api.post(`${root}/${id}/courses`, { course_id }),
  assign: async (
    id: number,
    batchId: number,
    institution_course_id: number,
    due_date: string | null,
  ) =>
    api.post(`${root}/${id}/batches/${batchId}/assignments`, {
      institution_course_id,
      due_date,
    }),
  requestPlan: async (id: number, plan: string, note: string) =>
    api.post(`${root}/${id}/plan-requests`, { plan, note }),
  export: async (id: number) =>
    (await api.get<Blob>(`${root}/${id}/report.csv`, { responseType: "blob" }))
      .data,
};
