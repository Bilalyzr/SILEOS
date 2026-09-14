import { api } from "./axios";
import type { HostelPass } from "./campus-hostel";
import type { TransportMe } from "./campus-transport";

export interface PortalAlert {
  kind: "fees_overdue" | "attendance_low" | "transport_not_boarded" | "hostel_pass_pending" | "results_published";
  message: string;
}

export interface PortalExam {
  id: number;
  name: string;
  status: string;
  published_at: string | null;
  total: number;
  max_total: number;
  percent: number | null;
  passed: boolean;
  rank: number;
  students: number;
}

export interface PortalInstitution {
  institution: { id: number; name: string; academic_year: string; timezone: string };
  member_id: number;
  batches: string[];
  attendance: { present: number; total: number; percent: number } | null;
  fees: {
    currency: string;
    outstanding: number;
    overdue: number;
    next_due: { name: string; due_on: string; balance: number; assignment_id: number; installment_id: number } | null;
    accounts: number;
    assignment_id: number | null;
  } | null;
  exams: PortalExam[];
  transport: TransportMe | null;
  hostel: {
    resident: boolean;
    block: string | null;
    room: string | null;
    pending_pass: HostelPass | null;
    approved_pass: HostelPass | null;
  } | null;
  notices: { id: number; title: string; body: string; created_at: string | null }[];
  alerts: PortalAlert[];
}

export interface PortalChild {
  student: { id: number; name: string; email: string };
  institutions: PortalInstitution[];
}

export interface PortalOverview {
  children: PortalChild[];
  pending_requests: number;
  generated_at: string;
}

export const parentPortalApi = {
  overview: async () => (await api.get<PortalOverview>("/parents/campus")).data,
};
