import { api } from "./axios";

const root = (id: number) => `/institutions/${id}/staff`;

export type LeaveStatus = "pending" | "approved" | "rejected" | "cancelled";
export type SubstitutionStatus = "open" | "assigned" | "released";

export interface LeaveType {
  id: number;
  academic_year: string;
  code: string;
  name: string;
  annual_quota: number;
}

export interface LeaveTypesResponse {
  academic_year: string;
  types: LeaveType[];
}

export interface LeaveBalance {
  type_id: number;
  code: string;
  name: string;
  quota: number;
  used: number;
  remaining: number;
}

export interface LeaveBalances {
  member_id: number;
  name: string | null;
  academic_year: string;
  balances: LeaveBalance[];
}

export interface LeaveRequest {
  id: number;
  member_id: number;
  member_name: string | null;
  type_id: number;
  type_code: string | null;
  type_name: string | null;
  starts_on: string;
  ends_on: string;
  days: number;
  note: string;
  status: LeaveStatus;
  decided_by: number | null;
  decided_at: string | null;
  decision_note: string;
  override: boolean;
  substitutions: { total: number; open: number; assigned: number };
  created_at: string | null;
}

export interface Substitution {
  id: number;
  leave_id: number;
  event_id: number;
  title: string;
  kind: string;
  starts_at: string | null;
  ends_at: string | null;
  room: string;
  batch_id: number | null;
  batch_name: string | null;
  absent_member_id: number;
  absent_name: string | null;
  substitute_member_id: number | null;
  substitute_name: string | null;
  status: SubstitutionStatus;
  note: string;
  assigned_at: string | null;
}

export interface Candidate {
  member_id: number;
  name: string;
  role: string;
  department: string;
}

export interface LeaveReport {
  academic_year: string;
  types: LeaveType[];
  rows: {
    member_id: number;
    name: string;
    role: string;
    department: string;
    balances: Record<string, { quota: number; used: number; remaining: number }>;
    substitution_hours: number;
  }[];
}

export const staffApi = {
  types: async (id: number, academicYear?: string) =>
    (await api.get<LeaveTypesResponse>(`${root(id)}/leave/types`, { params: { academic_year: academicYear } })).data,
  saveTypes: async (id: number, academicYear: string, types: { code: string; name: string; annual_quota: number }[]) =>
    (await api.put<LeaveTypesResponse>(`${root(id)}/leave/types`, { academic_year: academicYear, types })).data,
  balances: async (id: number, memberId?: number) =>
    (await api.get<LeaveBalances>(`${root(id)}/leave/balances`, { params: { member_id: memberId } })).data,
  leave: async (id: number, params: { status?: LeaveStatus; member_id?: number } = {}) =>
    (await api.get<LeaveRequest[]>(`${root(id)}/leave`, { params })).data,
  createLeave: async (id: number, data: { type_id: number; starts_on: string; ends_on: string; note: string }) =>
    (await api.post<LeaveRequest>(`${root(id)}/leave`, data)).data,
  approve: async (id: number, leaveId: number, data: { override: boolean; note: string }) =>
    (await api.post<LeaveRequest>(`${root(id)}/leave/${leaveId}/approve`, data)).data,
  reject: async (id: number, leaveId: number, note: string) =>
    (await api.post<LeaveRequest>(`${root(id)}/leave/${leaveId}/reject`, { note })).data,
  cancel: async (id: number, leaveId: number) =>
    (await api.post<LeaveRequest>(`${root(id)}/leave/${leaveId}/cancel`)).data,
  substitutions: async (id: number, status?: SubstitutionStatus) =>
    (await api.get<Substitution[]>(`${root(id)}/substitutions`, { params: { status } })).data,
  candidates: async (id: number, subId: number) =>
    (await api.get<Candidate[]>(`${root(id)}/substitutions/${subId}/candidates`)).data,
  assign: async (id: number, subId: number, substituteMemberId: number, note = "") =>
    (await api.post<Substitution>(`${root(id)}/substitutions/${subId}/assign`, { substitute_member_id: substituteMemberId, note })).data,
  unassign: async (id: number, subId: number) =>
    (await api.post<Substitution>(`${root(id)}/substitutions/${subId}/unassign`)).data,
  report: async (id: number, academicYear?: string) =>
    (await api.get<LeaveReport>(`${root(id)}/leave/report`, { params: { academic_year: academicYear } })).data,
  reportCsv: async (id: number, academicYear?: string) =>
    (
      await api.get<Blob>(`${root(id)}/leave/report`, {
        params: { academic_year: academicYear, format: "csv" },
        responseType: "blob",
      })
    ).data,
};
