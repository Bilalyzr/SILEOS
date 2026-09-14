import { api } from "./axios";

const root = (id: number) => `/institutions/${id}/fees`;

export type ReminderChannel = "whatsapp" | "email";
export type ReminderStatus = "queued" | "sent" | "failed" | "skipped";

export interface ReminderPolicy {
  institution_id: number;
  enabled: boolean;
  days_before: number[];
  overdue_every_days: number;
  overdue_max: number;
  send_hour: number;
  channels: ReminderChannel[];
  whatsapp_template: string;
  whatsapp_language: string;
  updated_at: string | null;
}

export type ReminderPolicyInput = Omit<ReminderPolicy, "institution_id" | "updated_at">;

export interface ReminderRow {
  id: number;
  assignment_id: number;
  installment_id: number | null;
  receipt_id: number | null;
  student_member_id: number;
  student_name: string;
  recipient_user_id: number;
  recipient_name: string;
  recipient_role: string;
  kind: "upcoming" | "due" | "overdue" | "receipt" | "manual";
  stage: string;
  channel: ReminderChannel;
  status: ReminderStatus;
  skip_reason: string;
  error: string;
  attempts: number;
  amount: number;
  currency: string;
  due_on: string | null;
  created_at: string | null;
  sent_at: string | null;
}

export interface ReminderList {
  items: ReminderRow[];
  next_after_id: number | null;
}

export interface RunResult {
  staged: number;
  sent: number;
  failed: number;
  skipped: number;
}

export const remindersApi = {
  policy: async (id: number) => (await api.get<ReminderPolicy>(`${root(id)}/reminders/policy`)).data,
  savePolicy: async (id: number, data: ReminderPolicyInput) =>
    (await api.put<ReminderPolicy>(`${root(id)}/reminders/policy`, data)).data,
  list: async (id: number, params: { status?: ReminderStatus; after_id?: number; limit?: number } = {}) =>
    (await api.get<ReminderList>(`${root(id)}/reminders`, { params })).data,
  runNow: async (id: number) => (await api.post<RunResult>(`${root(id)}/reminders/run-now`)).data,
  retry: async (id: number, reminderId: number) =>
    (await api.post<ReminderRow>(`${root(id)}/reminders/${reminderId}/retry`)).data,
  remind: async (id: number, assignmentId: number) =>
    (await api.post<ReminderRow[]>(`${root(id)}/assignments/${assignmentId}/remind`)).data,
};
