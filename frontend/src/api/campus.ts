import { api } from "./axios";
export interface AcademicData {
  terms: { id: number; name: string; starts_on: string; ends_on: string }[];
  students: { id: number; name: string; email: string }[];
  attendance: { member_id: number; status: string; day: string }[];
  assessments: {
    id: number;
    title: string;
    term_id: number | null;
    max_score: number;
    due_on: string | null;
    scores: { member_id: number; score: number; feedback: string }[];
  }[];
}
export interface ImportResult {
  rows: { row: number; email: string; status: string; message: string }[];
  ready: number;
  errors: number;
  created: number;
  committed: boolean;
  available_seats: number;
}
export interface CampusResource {
  id: number;
  title: string;
  filename: string;
  batch_id: number | null;
  created_at: string;
}
export interface Branding {
  title: string;
  subtitle: string;
  has_image: boolean;
}
export interface Billing {
  plans: string[];
  effective_plan: string;
  subscriptions: {
    id: number;
    plan: string;
    status: string;
    paid_through: string | null;
    checkout_url: string;
  }[];
}
export interface CampusPrice {
  gateway_plan_id: string;
  plan: string;
  name: string;
  amount: number;
  currency: string;
  period: string;
  interval: number;
  total_cycles: number;
}

export type PilotStepKey =
  | "profile"
  | "branding"
  | "batches"
  | "staff"
  | "students"
  | "term"
  | "timetable"
  | "course";

export interface PilotStep {
  key: PilotStepKey;
  label: string;
  complete: boolean;
  href?: string;
}

export interface CampusPilotStatus {
  dismissed: boolean;
  progress: number;
  total_steps: number;
  completed_steps: number;
  steps: PilotStep[];
}

export interface CampusEvent {
  id: number;
  title: string;
  kind: "class" | "exam" | "holiday" | "event" | string;
  starts_at: string;
  ends_at: string;
  batch_id: number | null;
  batch_name?: string | null;
  location: string;
  description: string;
  teacher_member_id?: number | null;
  substitute_member_id?: number | null;
  substitute_name?: string | null;
  recurrence?: "none" | "daily" | "weekly";
  series_id?: string | null;
  can_edit?: boolean;
}

export interface CampusAnnouncement {
  id: number;
  title: string;
  body: string;
  audience: "everyone" | "staff" | "students" | "batch" | string;
  batch_id: number | null;
  batch_name?: string | null;
  created_at: string;
  read_at: string | null;
  author_name?: string;
  can_edit?: boolean;
}

export interface CampusNotification {
  id: string;
  type: string;
  title: string;
  detail: string;
  starts_at: string | null;
  due_on: string | null;
  severity: "info" | "important" | "alert";
  href: string | null;
  read_at: string | null;
}

export interface CampusGoal {
  id: number;
  title: string;
  target_date: string | null;
  progress: number;
  status: "planned" | "in_progress" | "completed" | string;
  student_name?: string;
  owner_id?: number;
  can_edit?: boolean;
}

export interface CampusGradingPolicy {
  bands: { label: string; min_percent: number }[];
}

export interface CampusReportCardRow {
  subject: string;
  score: number | null;
  max_score: number;
  grade: string;
  comment: string;
}

export interface CampusReportCard {
  member_id: number;
  student_name: string;
  term_id: number | null;
  term_name: string;
  status: "draft" | "complete" | string;
  attendance_percent: number | null;
  overall_comment: string;
  rows: CampusReportCardRow[];
  updated_at?: string | null;
  can_edit?: boolean;
}

export interface WhatsAppStatus {
  configured: boolean;
  api_version: string;
  phone_number_configured: boolean;
  business_account_configured: boolean;
  business_phone_configured: boolean;
  webhook_ready: boolean;
  approved_templates: string[];
  missing_fields: string[];
  opted_in: boolean;
  contact_status: "not_started" | "pending" | "confirmed" | "revoked";
  phone: string | null;
  consent_at: string | null;
  join_url: string | null;
  join_expires_at: string | null;
}

export interface WhatsAppContact {
  member_id: number;
  name: string;
  phone: string | null;
  status: "not_started" | "pending" | "confirmed" | "revoked" | string;
  member_status: string;
  consent_at: string | null;
}

export interface WhatsAppCampaign {
  id: number;
  request_key: string;
  template: string;
  language: string;
  parameters: string[];
  batch_id: number | null;
  status: "draft" | "queued" | "sending" | "sent" | "failed" | string;
  created_at: string;
  queued: number;
  sent: number;
  delivered: number;
  read: number;
  failed: number;
}
const root = (id: number) => `/institutions/${id}`;
export const campusApi = {
  academics: async (id: number, batch?: number, day?: string) =>
    (
      await api.get<AcademicData>(`${root(id)}/academics`, {
        params: { batch_id: batch, day },
      })
    ).data,
  term: (
    id: number,
    data: { name: string; starts_on: string; ends_on: string },
  ) => api.post(`${root(id)}/terms`, data),
  attendance: (
    id: number,
    data: {
      batch_id: number;
      day: string;
      entries: { member_id: number; status: string }[];
    },
  ) => api.put(`${root(id)}/attendance`, data),
  assessment: (
    id: number,
    data: {
      batch_id: number;
      title: string;
      max_score: number;
      term_id: number | null;
      due_on: string | null;
    },
  ) => api.post(`${root(id)}/assessments`, data),
  scores: (
    id: number,
    assessment: number,
    entries: { member_id: number; score: number; feedback: string }[],
  ) => api.put(`${root(id)}/assessments/${assessment}/scores`, { entries }),
  importPeople: async (id: number, csv: string, commit = false) =>
    (await api.post<ImportResult>(`${root(id)}/people/import`, { csv, commit }))
      .data,
  sendInvite: (id: number, invite: number) =>
    api.post(`${root(id)}/invitations/${invite}/send-email`),
  resources: async (id: number) =>
    (await api.get<CampusResource[]>(`${root(id)}/resources`)).data,
  upload: (id: number, data: FormData) =>
    api.post(`${root(id)}/resources`, data),
  resource: async (id: number, resource: number) =>
    (
      await api.get<Blob>(`${root(id)}/resources/${resource}/download`, {
        responseType: "blob",
      })
    ).data,
  removeResource: (id: number, resource: number) =>
    api.delete(`${root(id)}/resources/${resource}`),
  branding: async (id: number) =>
    (await api.get<Branding>(`${root(id)}/branding`)).data,
  saveBranding: (id: number, data: { title: string; subtitle: string }) =>
    api.put(`${root(id)}/branding`, data),
  image: async (id: number) =>
    (
      await api.get<Blob>(`${root(id)}/branding/image`, {
        responseType: "blob",
      })
    ).data,
  uploadImage: (id: number, file: File) => {
    const data = new FormData();
    data.append("file", file);
    return api.put(`${root(id)}/branding/image`, data);
  },
  removeImage: (id: number) => api.delete(`${root(id)}/branding/image`),
  billing: async (id: number) =>
    (await api.get<Billing>(`${root(id)}/billing`)).data,
  price: async (id: number, plan: string) =>
    (await api.get<CampusPrice>(`${root(id)}/billing/plans/${plan}`)).data,
  subscribe: async (id: number, plan: string, expected_plan_id: string) =>
    (
      await api.post<{ checkout_url: string }>(
        `${root(id)}/billing/subscribe`,
        { plan, expected_plan_id },
      )
    ).data,
  cancel: (id: number, sub: number) =>
    api.post(`${root(id)}/billing/${sub}/cancel`),
  invoices: async (id: number, sub: number) =>
    (
      await api.get<
        {
          id: string;
          amount: number;
          currency: string;
          status: string;
          url: string;
        }[]
      >(`${root(id)}/billing/${sub}/invoices`)
    ).data,
  pilot: async (id: number) =>
    (await api.get<CampusPilotStatus>(`${root(id)}/pilot/onboarding`)).data,
  updatePilot: async (id: number, dismissed: boolean) =>
    (
      await api.patch<CampusPilotStatus>(`${root(id)}/pilot/onboarding`, {
        dismissed,
      })
    ).data,
  events: async (id: number, startsAfter?: string, startsBefore?: string) =>
    (
      await api.get<CampusEvent[]>(`${root(id)}/pilot/events`, {
        params: {
          starts_after: startsAfter,
          starts_before: startsBefore,
        },
      })
    ).data,
  createEvent: async (
    id: number,
    data: Pick<
      CampusEvent,
      | "title"
      | "kind"
      | "starts_at"
      | "ends_at"
      | "batch_id"
      | "teacher_member_id"
      | "location"
      | "description"
      | "recurrence"
    > & { repeat_until?: string | null },
  ) =>
    (
      await api.post<{
        series_id: string | null;
        created_count: number;
        events: CampusEvent[];
      }>(`${root(id)}/pilot/events`, data)
    ).data,
  removeEvent: (id: number, eventId: number, series = false) =>
    api.delete(`${root(id)}/pilot/events/${eventId}`, { params: { series } }),
  announcements: async (id: number) =>
    (
      await api.get<CampusAnnouncement[]>(
        `${root(id)}/pilot/announcements`,
      )
    ).data,
  notifications: async (id: number) =>
    (
      await api.get<CampusNotification[]>(`${root(id)}/pilot/notifications`)
    ).data,
  createAnnouncement: async (
    id: number,
    data: Pick<CampusAnnouncement, "title" | "body" | "batch_id">,
  ) =>
    (
      await api.post<CampusAnnouncement>(
        `${root(id)}/pilot/announcements`,
        data,
      )
    ).data,
  readAnnouncement: (id: number, announcementId: number) =>
    api.post(`${root(id)}/pilot/announcements/${announcementId}/read`),
  goals: async (id: number) =>
    (await api.get<CampusGoal[]>(`${root(id)}/pilot/goals`)).data,
  createGoal: async (
    id: number,
    data: { title: string; target_date: string; member_id?: number },
  ) => (await api.post<CampusGoal>(`${root(id)}/pilot/goals`, data)).data,
  updateGoal: async (
    id: number,
    goalId: number,
    data: Partial<Pick<CampusGoal, "title" | "target_date" | "progress" | "status">>,
  ) =>
    (
      await api.patch<CampusGoal>(
        `${root(id)}/pilot/goals/${goalId}`,
        data,
      )
    ).data,
  gradingPolicy: async (id: number) =>
    (
      await api.get<CampusGradingPolicy>(
        `${root(id)}/pilot/grading-policy`,
      )
    ).data,
  saveGradingPolicy: (id: number, data: CampusGradingPolicy) =>
    api.put(`${root(id)}/pilot/grading-policy`, data),
  reportCard: async (id: number, memberId: number, termId?: number) =>
    (
      await api.get<CampusReportCard>(
        `${root(id)}/pilot/report-cards/${memberId}`,
        { params: { term_id: termId } },
      )
    ).data,
  saveReportComment: async (
    id: number,
    memberId: number,
    data: { term_id: number; overall_comment: string },
  ) =>
    (
      await api.put<CampusReportCard>(
        `${root(id)}/pilot/report-cards/${memberId}/comment`,
        data,
      )
    ).data,
  reportCardPdf: async (id: number, memberId: number, termId?: number) =>
    (
      await api.get<Blob>(
        `${root(id)}/pilot/report-cards/${memberId}.pdf`,
        { params: { term_id: termId }, responseType: "blob" },
      )
    ).data,
  whatsappStatus: async (id: number) =>
    (
      await api.get<WhatsAppStatus>(`${root(id)}/pilot/whatsapp/status`)
    ).data,
  whatsappContacts: async (id: number) =>
    (
      await api.get<WhatsAppContact[]>(
        `${root(id)}/pilot/whatsapp/contacts`,
      )
    ).data,
  saveWhatsAppConsent: (
    id: number,
    data: { phone: string },
  ) => api.post(`${root(id)}/pilot/whatsapp/opt-in`, data),
  removeWhatsAppConsent: (id: number) =>
    api.delete(`${root(id)}/pilot/whatsapp/opt-in`),
  whatsappCampaigns: async (id: number) =>
    (
      await api.get<WhatsAppCampaign[]>(
        `${root(id)}/pilot/whatsapp/campaigns`,
      )
    ).data,
  createWhatsAppCampaign: async (
    id: number,
    data: {
      request_key: string;
      template: string;
      language: string;
      parameters: string[];
      batch_id: number | null;
      header_image_url?: string | null;
    },
  ) =>
    (
      await api.post<WhatsAppCampaign>(
        `${root(id)}/pilot/whatsapp/campaigns`,
        data,
      )
    ).data,
};
