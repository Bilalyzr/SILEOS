import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "./axios";

export type CampusOsRole =
  | "owner"
  | "admin"
  | "teacher"
  | "student"
  | "parent"
  | "spoc";

export type CampusTone = "orange" | "success" | "warning" | "danger" | "neutral";

export interface TodayMetric {
  key: string;
  label: string;
  value: string | number;
  detail: string;
  tone: CampusTone;
  trend?: string | null;
}

export type TodayActionStatus = "open" | "done" | "snoozed";
export type TodayActionPriority = "urgent" | "high" | "normal" | "low";

export interface TodayAction {
  id: string;
  kind: string;
  title: string;
  detail: string;
  priority: TodayActionPriority;
  status: TodayActionStatus;
  due_at?: string | null;
  href?: string | null;
  cta_label?: string | null;
  owner_name?: string | null;
}

export interface TodayScheduleItem {
  id: string;
  title: string;
  kind: string;
  starts_at: string;
  ends_at?: string | null;
  location?: string | null;
  href?: string | null;
}

export interface TodayNotice {
  id: string;
  title: string;
  detail: string;
  tone: CampusTone;
  href?: string | null;
}

export interface TodayDashboard {
  role: CampusOsRole;
  generated_at: string;
  greeting: string;
  headline: string;
  metrics: TodayMetric[];
  actions: TodayAction[];
  schedule: TodayScheduleItem[];
  notices: TodayNotice[];
}

export const ADMISSION_STAGES = [
  "draft",
  "submitted",
  "screening",
  "documents",
  "assessment",
  "interview",
  "decision",
  "waitlisted",
  "offered",
  "admitted",
  "rejected",
  "withdrawn",
  "enrolled",
] as const;

export type AdmissionStage = (typeof ADMISSION_STAGES)[number] | string;
export type AdmissionOfferStatus =
  | "none"
  | "draft"
  | "issued"
  | "accepted"
  | "declined"
  | "expired"
  | "revoked";

export interface AdmissionStageCount {
  stage: AdmissionStage;
  count: number;
}

export interface AdmissionOfferCount {
  status: AdmissionOfferStatus;
  count: number;
}

export interface AdmissionIntakeSummary {
  id: number;
  program_id: number;
  name: string;
  program_name: string;
  academic_year: string;
  starts_on: string;
  closes_on: string;
  status: string;
  capacity: number;
  batch_id: number | null;
  applications: number;
  enrolled: number;
  available: number;
}

export interface AdmissionApplicationListItem {
  id: number;
  application_number: string;
  full_name: string;
  email: string;
  phone: string;
  program_id: number;
  program_name: string;
  intake_id: number;
  intake_name: string;
  stage: AdmissionStage;
  offer_status: AdmissionOfferStatus;
  source: string;
  owner_member_id: number | null;
  enrollment_member_id: number | null;
  submitted_at: string;
  updated_at: string;
  version: number;
}

export interface AdmissionSummary {
  counts: {
    total: number;
    active: number;
    offered: number;
    admitted: number;
    enrolled: number;
    rejected: number;
    withdrawn: number;
  };
  stage_counts: AdmissionStageCount[];
  offer_counts: AdmissionOfferCount[];
  tasks: { open: number; overdue: number; due_soon: number };
  intakes: AdmissionIntakeSummary[];
  recent_applications: AdmissionApplicationListItem[];
}

export interface AdmissionProgram {
  id: number;
  name: string;
  code: string;
  level: string;
  department: string;
  duration_months: number;
  status: string;
  created_at: string;
}

export interface AdmissionIntake {
  id: number;
  program_id: number;
  program_name: string;
  name: string;
  academic_year: string;
  starts_on: string;
  closes_on: string;
  capacity: number;
  status: string;
  batch_id: number | null;
  applications: number;
  enrolled: number;
  available: number;
}

export interface AdmissionApplicationsPage {
  items: AdmissionApplicationListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateAdmissionApplication {
  full_name: string;
  email: string;
  phone?: string;
  program_id: number;
  intake_id: number;
  date_of_birth?: string | null;
  address?: string;
  prior_institution?: string;
  source?: string;
}

export interface FeeMoneyTotals {
  assessed: number;
  discounts: number;
  waivers: number;
  paid: number;
  outstanding: number;
  overdue: number;
  due_today: number;
  due_next_30_days: number;
}

export interface FeeAgingBuckets {
  current: number;
  days_1_30: number;
  days_31_60: number;
  days_61_90: number;
  days_91_plus: number;
}

export interface FeeSummary {
  as_of: string;
  currency: string | null;
  mixed_currency: boolean;
  totals: FeeMoneyTotals;
  accounts: { total: number; with_balance: number; overdue: number };
  aging: FeeAgingBuckets;
}

export interface FeeAgingRow {
  assignment_id: number;
  student_member_id: number;
  student_user_id: number;
  student_name: string;
  plan_name: string;
  currency: string;
  outstanding: number;
  overdue: number;
  oldest_due_on: string | null;
  aging: FeeAgingBuckets;
}

export interface FeeAgingReport {
  as_of: string;
  rows: FeeAgingRow[];
  next_cursor?: number | null;
}

export interface FeeComponent {
  id?: number;
  code: string;
  name: string;
  amount: number;
}

export interface FeeInstallment {
  id?: number;
  name: string;
  sequence?: number;
  due_on: string;
  amount: number;
}

export interface FeePlan {
  id: number;
  name: string;
  academic_year: string;
  currency: string;
  status: string;
  description: string;
  total_amount: number;
  components: FeeComponent[];
  installments: FeeInstallment[];
  created_at: string;
}

export interface FeePlansResponse {
  items: FeePlan[];
}

export interface CreateFeePlan {
  name: string;
  academic_year: string;
  currency?: string;
  description?: string;
  components: Omit<FeeComponent, "id">[];
  installments: Omit<FeeInstallment, "id" | "sequence">[];
}

export interface CreateFeeAssignment {
  student_member_id: number;
  plan_id: number;
  note?: string;
}

export interface RecordFeePayment {
  amount: number;
  paid_at?: string | null;
  method: string;
  reference?: string;
  note?: string;
  received_by_member_id?: number | null;
}

export interface RecordFeeAdjustment {
  kind: "discount" | "waiver";
  amount: number;
  reason: string;
  installment_id?: number | null;
}

export interface TuitionStudent {
  member_id: number;
  user_id: number;
  name: string;
  email: string;
}

export interface TuitionAssignmentPlan {
  id: number;
  name: string;
  academic_year: string;
}

export interface TuitionInstallment {
  id: number;
  name: string;
  sequence: number;
  due_on: string;
  amount_due: number;
  credited: number;
  balance: number;
  status: "paid" | "due" | "overdue" | "upcoming";
}

export interface TuitionPerson {
  id: number;
  name: string;
}

export interface TuitionVerification {
  status: "not_required" | "pending" | "verified";
  verified_by: TuitionPerson | null;
  verified_at: string | null;
  note: string;
}

export interface TuitionPayment {
  id: number;
  amount: number;
  paid_at: string;
  method: string;
  reference: string;
  note: string;
  status: string;
  receipt: { id: number; receipt_number: string; issued_at: string };
  received_by: TuitionPerson | null;
  verification: TuitionVerification;
}

export interface CashDeskRow {
  payment_id: number;
  receipt_id: number;
  receipt_number: string;
  student_name: string;
  plan_name: string;
  amount: number;
  currency: string;
  method: string;
  reference: string;
  paid_at: string;
  status: string;
  received_by: TuitionPerson | null;
  verification: TuitionVerification;
}

export interface CashDesk {
  day: string;
  currency: string;
  rows: CashDeskRow[];
  receivers: { id: number | null; name: string; count: number; total: number; pending: number }[];
  pending_total: number;
  verified_total: number;
  pending_count: number;
  excess_orders: { id: number; student_name: string; excess_amount: number; currency: string; gateway_payment_id: string | null; paid_at: string | null }[];
}

export interface TuitionInvoiceLine {
  installment_id: number;
  name: string;
  due_on: string;
  amount_due: number;
  credited: number;
  balance: number;
}

export interface TuitionInvoice {
  id: number;
  invoice_number: string;
  assignment_id: number;
  installment_id: number | null;
  amount: number;
  currency: string;
  due_on: string;
  status: "open" | "settled";
  lines: TuitionInvoiceLine[];
  issued_at: string;
}

export interface OnlineCheckout {
  key: string;
  order_id: string;
  amount_paise: number;
  currency: string;
  name: string;
  description: string;
  prefill: { name: string; email: string };
}

export interface OnlineOrder {
  id: number;
  assignment_id: number;
  installment_id: number | null;
  status: "created" | "paid" | "paid_excess" | "failed";
  amount: number;
  amount_paise: number;
  currency: string;
  excess_amount: number;
  gateway_order_id: string;
  gateway_payment_id: string | null;
  payment: TuitionPayment | null;
}

export interface OnlineVerifyInput {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export interface TuitionAdjustment {
  id: number;
  kind: string;
  amount: number;
  reason: string;
  installment_id: number | null;
  status: string;
  created_at: string;
}

export interface TuitionAssignment {
  id: number;
  institution_id: number;
  student: TuitionStudent;
  plan: TuitionAssignmentPlan;
  currency: string;
  status: string;
  assigned_on: string;
  note: string;
  gross_amount: number;
  discounts_total: number;
  waivers_total: number;
  paid_total: number;
  balance: number;
  installments: TuitionInstallment[];
  payments: TuitionPayment[];
  adjustments: TuitionAdjustment[];
}

export interface TuitionSelfAccounts {
  student: TuitionStudent;
  assignments: TuitionAssignment[];
}

export interface AdmissionApplicationFilters {
  search?: string;
  stage?: string;
  offer_status?: string;
  intake_id?: number;
  limit?: number;
  offset?: number;
}

const root = (institutionId: number) => `/institutions/${institutionId}`;

export const campusOsKeys = {
  all: (institutionId: number) => ["campus-os", institutionId] as const,
  today: (institutionId: number, demo = false) =>
    [...campusOsKeys.all(institutionId), "today", { demo }] as const,
  admissions: (institutionId: number) =>
    [...campusOsKeys.all(institutionId), "admissions"] as const,
  admissionSummary: (institutionId: number, demo = false) =>
    [...campusOsKeys.admissions(institutionId), "summary", { demo }] as const,
  applications: (
    institutionId: number,
    filters: AdmissionApplicationFilters,
    demo = false,
  ) =>
    [
      ...campusOsKeys.admissions(institutionId),
      "applications",
      filters,
      { demo },
    ] as const,
  programs: (institutionId: number, demo = false) =>
    [...campusOsKeys.admissions(institutionId), "programs", { demo }] as const,
  intakes: (institutionId: number, demo = false) =>
    [...campusOsKeys.admissions(institutionId), "intakes", { demo }] as const,
  fees: (institutionId: number) =>
    [...campusOsKeys.all(institutionId), "fees"] as const,
  feeSummary: (institutionId: number, asOf: string, demo = false) =>
    [...campusOsKeys.fees(institutionId), "summary", asOf, { demo }] as const,
  feeAging: (institutionId: number, asOf: string, demo = false) =>
    [...campusOsKeys.fees(institutionId), "aging", asOf, { demo }] as const,
  feePlans: (institutionId: number, demo = false) =>
    [...campusOsKeys.fees(institutionId), "plans", { demo }] as const,
  feeSelf: (institutionId: number, studentUserId?: number, demo = false) =>
    [...campusOsKeys.fees(institutionId), "me", studentUserId ?? "self", { demo }] as const,
  cashDesk: (institutionId: number, day: string) =>
    [...campusOsKeys.fees(institutionId), "cash", day] as const,
  onlineStatus: (institutionId: number) =>
    [...campusOsKeys.fees(institutionId), "online-status"] as const,
};

export const campusOsApi = {
  today: async (institutionId: number) =>
    (await api.get<TodayDashboard>(`${root(institutionId)}/today`)).data,
  updateTodayAction: async (
    institutionId: number,
    actionId: string,
    status: TodayActionStatus,
  ) =>
    (
      await api.patch<TodayAction>(
        `${root(institutionId)}/today/actions/${encodeURIComponent(actionId)}`,
        { status },
      )
    ).data,
  admissionSummary: async (institutionId: number) =>
    (
      await api.get<AdmissionSummary>(
        `${root(institutionId)}/admissions/summary`,
      )
    ).data,
  admissionApplications: async (
    institutionId: number,
    filters: AdmissionApplicationFilters,
  ) =>
    (
      await api.get<AdmissionApplicationsPage>(
        `${root(institutionId)}/admissions/applications`,
        { params: filters },
      )
    ).data,
  admissionPrograms: async (institutionId: number) =>
    (
      await api.get<AdmissionProgram[]>(
        `${root(institutionId)}/admissions/programs`,
      )
    ).data,
  admissionIntakes: async (institutionId: number) =>
    (
      await api.get<AdmissionIntake[]>(
        `${root(institutionId)}/admissions/intakes`,
      )
    ).data,
  createAdmissionApplication: async (
    institutionId: number,
    input: CreateAdmissionApplication,
  ) =>
    (
      await api.post<AdmissionApplicationListItem>(
        `${root(institutionId)}/admissions/applications`,
        input,
      )
    ).data,
  updateAdmissionStage: async (
    institutionId: number,
    applicationId: number,
    stage: string,
    expectedVersion: number,
    reason = "",
  ) =>
    (
      await api.patch<AdmissionApplicationListItem>(
        `${root(institutionId)}/admissions/applications/${applicationId}/stage`,
        { stage, reason, expected_version: expectedVersion },
      )
    ).data,
  feeSummary: async (institutionId: number, asOf: string) =>
    (
      await api.get<FeeSummary>(`${root(institutionId)}/fees/summary`, {
        params: { as_of: asOf },
      })
    ).data,
  feeAging: async (institutionId: number, asOf: string) =>
    (
      await api.get<FeeAgingReport>(`${root(institutionId)}/fees/aging`, {
        params: { as_of: asOf },
      })
    ).data,
  feePlans: async (institutionId: number) =>
    (
      await api.get<FeePlansResponse>(`${root(institutionId)}/fees/plans`)
    ).data,
  feeSelf: async (institutionId: number, studentUserId?: number) =>
    (
      await api.get<TuitionSelfAccounts>(`${root(institutionId)}/fees/me`, {
        params: { student_user_id: studentUserId },
      })
    ).data,
  createFeePlan: async (institutionId: number, input: CreateFeePlan) =>
    (
      await api.post<FeePlan>(`${root(institutionId)}/fees/plans`, input)
    ).data,
  publishFeePlan: (institutionId: number, planId: number) =>
    api.post(`${root(institutionId)}/fees/plans/${planId}/publish`),
  createFeeAssignment: (institutionId: number, input: CreateFeeAssignment) =>
    api.post(`${root(institutionId)}/fees/assignments`, input),
  recordFeePayment: (
    institutionId: number,
    assignmentId: number,
    input: RecordFeePayment,
    idempotencyKey: string,
  ) =>
    api.post(
      `${root(institutionId)}/fees/assignments/${assignmentId}/payments`,
      input,
      { headers: { "Idempotency-Key": idempotencyKey } },
    ),
  recordFeeAdjustment: (
    institutionId: number,
    assignmentId: number,
    input: RecordFeeAdjustment,
    idempotencyKey: string,
  ) =>
    api.post(
      `${root(institutionId)}/fees/assignments/${assignmentId}/adjustments`,
      input,
      { headers: { "Idempotency-Key": idempotencyKey } },
    ),
  // Fee collection (cash desk, documents, online orders)
  cashDesk: async (institutionId: number, day: string) =>
    (await api.get<CashDesk>(`${root(institutionId)}/fees/cash`, { params: { day } })).data,
  cashDeskCsv: async (institutionId: number, day: string) =>
    (await api.get<Blob>(`${root(institutionId)}/fees/cash/csv`, { params: { day }, responseType: "blob" })).data,
  verifyPayment: async (institutionId: number, paymentId: number, note: string) =>
    (await api.post<TuitionPayment>(`${root(institutionId)}/fees/payments/${paymentId}/verify`, { note })).data,
  receiptPdf: async (institutionId: number, receiptId: number) =>
    (await api.get<Blob>(`${root(institutionId)}/fees/receipts/${receiptId}/pdf`, { responseType: "blob" })).data,
  createInvoice: async (institutionId: number, assignmentId: number, installmentId: number | null) =>
    (
      await api.post<TuitionInvoice>(`${root(institutionId)}/fees/assignments/${assignmentId}/invoices`, {
        installment_id: installmentId,
      })
    ).data,
  invoicePdf: async (institutionId: number, invoiceId: number) =>
    (await api.get<Blob>(`${root(institutionId)}/fees/invoices/${invoiceId}/pdf`, { responseType: "blob" })).data,
  onlineStatus: async (institutionId: number) =>
    (await api.get<{ ready: boolean }>(`${root(institutionId)}/fees/online/status`)).data,
  createOnlineOrder: async (
    institutionId: number,
    assignmentId: number,
    input: { installment_id: number | null; amount: number | null },
  ) =>
    (
      await api.post<{ order: OnlineOrder; checkout: OnlineCheckout }>(
        `${root(institutionId)}/fees/assignments/${assignmentId}/online-orders`,
        input,
      )
    ).data,
  verifyOnlineOrder: async (institutionId: number, orderId: number, input: OnlineVerifyInput) =>
    (await api.post<OnlineOrder>(`${root(institutionId)}/fees/online-orders/${orderId}/verify`, input)).data,
  reconcileOnlineOrder: async (institutionId: number, orderId: number) =>
    (await api.post<OnlineOrder>(`${root(institutionId)}/fees/online-orders/${orderId}/reconcile`)).data,
};

function demoToday(role: CampusOsRole, institutionName: string): TodayDashboard {
  const now = new Date();
  const inMinutes = (minutes: number) =>
    new Date(now.getTime() + minutes * 60_000).toISOString();
  const shared = {
    role,
    generated_at: now.toISOString(),
    greeting: "Good morning",
    notices: [
      {
        id: "notice-1",
        title: "Family update is ready",
        detail: "The weekly campus banner can be reviewed before it is shared.",
        tone: "orange" as const,
        href: "/admin/communications",
      },
    ],
  };
  if (role === "student") {
    return {
      ...shared,
      headline: `Make today count at ${institutionName}.`,
      metrics: [
        { key: "classes", label: "Classes today", value: 4, detail: "Next at 10:30 AM", tone: "orange" },
        { key: "tasks", label: "Tasks due", value: 2, detail: "One due today", tone: "warning" },
        { key: "attendance", label: "Attendance", value: "94%", detail: "This term", tone: "success" },
        { key: "progress", label: "Weekly goal", value: "72%", detail: "Keep going", tone: "neutral" },
      ],
      actions: [
        { id: "task-student-assignment", kind: "assignment", title: "Submit the physics lab reflection", detail: "Two questions remain before your work is ready.", priority: "high", status: "open", due_at: inMinutes(360), href: "/dashboard", cta_label: "Continue work" },
        { id: "task-student-review", kind: "practice", title: "Review quadratic equations", detail: "A 12-minute practice set is ready from your last lesson.", priority: "normal", status: "open", href: "/planner", cta_label: "Start practice" },
      ],
      schedule: [
        { id: "class-1", title: "Physics · Motion", kind: "class", starts_at: inMinutes(45), ends_at: inMinutes(105), location: "Lab 2" },
        { id: "class-2", title: "Mathematics", kind: "class", starts_at: inMinutes(150), ends_at: inMinutes(210), location: "Room 204" },
      ],
    };
  }
  if (role === "teacher") {
    return {
      ...shared,
      headline: `Your teaching day at ${institutionName}, arranged by priority.`,
      metrics: [
        { key: "classes", label: "Classes today", value: 5, detail: "Two labs", tone: "orange" },
        { key: "grading", label: "Needs grading", value: 18, detail: "Across three courses", tone: "warning" },
        { key: "support", label: "Need support", value: 6, detail: "Learning signals", tone: "danger" },
        { key: "attendance", label: "Attendance saved", value: "3/5", detail: "Two classes remain", tone: "success" },
      ],
      actions: [
        { id: "task-teacher-attendance", kind: "attendance", title: "Record attendance for Class 10 A", detail: "The class ended 18 minutes ago.", priority: "urgent", status: "open", due_at: inMinutes(-18), href: "/institutions", cta_label: "Take attendance" },
        { id: "task-teacher-grading", kind: "grading", title: "Grade 12 new submissions", detail: "Students are waiting for feedback on Algebra II.", priority: "high", status: "open", href: "/instructor/grading", cta_label: "Open grading" },
      ],
      schedule: [
        { id: "teacher-class-1", title: "Class 10 A · Physics", kind: "class", starts_at: inMinutes(-80), ends_at: inMinutes(-20), location: "Lab 2" },
        { id: "teacher-class-2", title: "Class 11 B · Physics", kind: "class", starts_at: inMinutes(35), ends_at: inMinutes(95), location: "Lab 1" },
      ],
    };
  }
  return {
    ...shared,
    headline: `${institutionName} is moving. Here is what needs you today.`,
    metrics: [
      { key: "attendance", label: "Attendance today", value: "91%", detail: "842 of 925 recorded", tone: "success", trend: "+2.4%" },
      { key: "admissions", label: "Admission actions", value: 14, detail: "Three overdue", tone: "warning" },
      { key: "fees", label: "Fees overdue", value: "₹2.8L", detail: "41 student accounts", tone: "danger" },
      { key: "messages", label: "Messages delivered", value: "96%", detail: "Last 24 hours", tone: "orange" },
    ],
    actions: [
      { id: "task-admin-admission", kind: "admission", title: "Review three completed applications", detail: "All required documents have been verified.", priority: "urgent", status: "open", due_at: inMinutes(120), href: "/institutions", cta_label: "Review applications", owner_name: "Admissions office" },
      { id: "task-admin-fees", kind: "fees", title: "Approve the September reminder", detail: "A consented WhatsApp audience of 41 families is ready.", priority: "high", status: "open", href: "/admin/communications", cta_label: "Review reminder", owner_name: "Finance office" },
      { id: "task-admin-attendance", kind: "attendance", title: "Follow up on attendance anomalies", detail: "Six learners crossed the support threshold this week.", priority: "normal", status: "open", href: "/institutions", cta_label: "View learners" },
    ],
    schedule: [
      { id: "admin-event-1", title: "Admissions stand-up", kind: "meeting", starts_at: inMinutes(30), ends_at: inMinutes(60), location: "Admin room" },
      { id: "admin-event-2", title: "Parent orientation", kind: "event", starts_at: inMinutes(300), ends_at: inMinutes(390), location: "Auditorium" },
    ],
  };
}

const demoApplications: AdmissionApplicationListItem[] = [
  { id: 101, application_number: "APP-2026-0101", full_name: "Ananya Iyer", email: "ananya.iyer@example.edu", phone: "+919876543210", program_id: 1, program_name: "B.Sc. Computer Science", intake_id: 1, intake_name: "2026–27 Main Intake", stage: "screening", offer_status: "none", source: "website", owner_member_id: 12, enrollment_member_id: null, submitted_at: "2026-09-09T09:30:00Z", updated_at: "2026-09-10T11:15:00Z", version: 2 },
  { id: 102, application_number: "APP-2026-0102", full_name: "Kabir Mehta", email: "kabir.mehta@example.edu", phone: "+919765432109", program_id: 2, program_name: "B.Com.", intake_id: 2, intake_name: "2026–27 Main Intake", stage: "documents", offer_status: "none", source: "referral", owner_member_id: null, enrollment_member_id: null, submitted_at: "2026-09-08T07:20:00Z", updated_at: "2026-09-10T08:05:00Z", version: 1 },
  { id: 103, application_number: "APP-2026-0103", full_name: "Meera Nair", email: "meera.nair@example.edu", phone: "+91 99887 77665", program_id: 1, program_name: "B.Sc. Computer Science", intake_id: 1, intake_name: "2026–27 Main Intake", stage: "offered", offer_status: "issued", source: "open_day", owner_member_id: 12, enrollment_member_id: null, submitted_at: "2026-09-04T12:00:00Z", updated_at: "2026-09-09T16:40:00Z", version: 4 },
  { id: 104, application_number: "APP-2026-0104", full_name: "Rohan Das", email: "rohan.das@example.edu", phone: "+91 91234 56789", program_id: 3, program_name: "B.A. Economics", intake_id: 3, intake_name: "2026–27 Main Intake", stage: "enrolled", offer_status: "accepted", source: "website", owner_member_id: 14, enrollment_member_id: 304, submitted_at: "2026-08-28T10:10:00Z", updated_at: "2026-09-08T10:30:00Z", version: 6 },
];

const demoPrograms: AdmissionProgram[] = [
  { id: 1, name: "B.Sc. Computer Science", code: "BSC-CS", level: "undergraduate", department: "Computer Science", duration_months: 36, status: "active", created_at: "2026-06-01T00:00:00Z" },
  { id: 2, name: "B.Com.", code: "BCOM", level: "undergraduate", department: "Commerce", duration_months: 36, status: "active", created_at: "2026-06-01T00:00:00Z" },
  { id: 3, name: "B.A. Economics", code: "BA-ECO", level: "undergraduate", department: "Economics", duration_months: 36, status: "active", created_at: "2026-06-01T00:00:00Z" },
];

const demoIntakes: AdmissionIntake[] = demoPrograms.map((program) => ({
  id: program.id,
  program_id: program.id,
  program_name: program.name,
  name: "2026–27 Main Intake",
  academic_year: "2026–27",
  starts_on: "2026-07-01",
  closes_on: "2026-11-30",
  capacity: program.id === 1 ? 120 : 80,
  status: "open",
  batch_id: null,
  applications: program.id === 1 ? 64 : 31,
  enrolled: program.id === 1 ? 28 : 18,
  available: (program.id === 1 ? 120 : 80) - (program.id === 1 ? 28 : 18),
}));

function demoAdmissionSummary(): AdmissionSummary {
  return {
    counts: { total: 142, active: 97, offered: 26, admitted: 21, enrolled: 45, rejected: 5, withdrawn: 3 },
    stage_counts: [
      { stage: "submitted", count: 24 },
      { stage: "documents", count: 18 },
      { stage: "screening", count: 29 },
      { stage: "interview", count: 12 },
      { stage: "offered", count: 26 },
      { stage: "enrolled", count: 45 },
    ],
    offer_counts: [{ status: "issued", count: 26 }, { status: "accepted", count: 21 }],
    tasks: { open: 17, overdue: 3, due_soon: 8 },
    intakes: demoIntakes,
    recent_applications: demoApplications,
  };
}

const demoFeeSummary: FeeSummary = {
  as_of: "2026-09-11",
  currency: "INR",
  mixed_currency: false,
  totals: { assessed: 7850000, discounts: 310000, waivers: 85000, paid: 6125000, outstanding: 1330000, overdue: 284000, due_today: 76000, due_next_30_days: 621000 },
  accounts: { total: 412, with_balance: 128, overdue: 41 },
  aging: { current: 1046000, days_1_30: 168000, days_31_60: 71000, days_61_90: 29000, days_91_plus: 16000 },
};

const demoFeeAging: FeeAgingReport = {
  as_of: "2026-09-11",
  rows: [
    { assignment_id: 401, student_member_id: 301, student_user_id: 901, student_name: "Arjun Rao", plan_name: "Grade 11 · 2026–27", currency: "INR", outstanding: 42000, overdue: 18000, oldest_due_on: "2026-08-10", aging: { current: 24000, days_1_30: 18000, days_31_60: 0, days_61_90: 0, days_91_plus: 0 } },
    { assignment_id: 402, student_member_id: 302, student_user_id: 902, student_name: "Diya Shah", plan_name: "Grade 10 · 2026–27", currency: "INR", outstanding: 36500, overdue: 12500, oldest_due_on: "2026-07-31", aging: { current: 24000, days_1_30: 0, days_31_60: 12500, days_61_90: 0, days_91_plus: 0 } },
    { assignment_id: 403, student_member_id: 303, student_user_id: 903, student_name: "Vivaan Singh", plan_name: "Grade 12 · 2026–27", currency: "INR", outstanding: 28000, overdue: 9000, oldest_due_on: "2026-08-22", aging: { current: 19000, days_1_30: 9000, days_31_60: 0, days_61_90: 0, days_91_plus: 0 } },
  ],
};

const demoFeePlans: FeePlansResponse = {
  items: [
    { id: 501, name: "Grade 11 · 2026–27", academic_year: "2026–27", currency: "INR", status: "published", description: "Annual tuition and campus services", total_amount: 96000, components: [{ id: 1, code: "TUITION", name: "Tuition", amount: 84000 }, { id: 2, code: "LAB", name: "Laboratory", amount: 12000 }], installments: [{ id: 1, name: "Term 1", sequence: 1, due_on: "2026-07-10", amount: 48000 }, { id: 2, name: "Term 2", sequence: 2, due_on: "2026-12-10", amount: 48000 }], created_at: "2026-06-12T00:00:00Z" },
    { id: 502, name: "Grade 10 · 2026–27", academic_year: "2026–27", currency: "INR", status: "published", description: "Annual tuition", total_amount: 84000, components: [{ id: 3, code: "TUITION", name: "Tuition", amount: 84000 }], installments: [{ id: 3, name: "Term 1", sequence: 1, due_on: "2026-07-10", amount: 42000 }, { id: 4, name: "Term 2", sequence: 2, due_on: "2026-12-10", amount: 42000 }], created_at: "2026-06-12T00:00:00Z" },
  ],
};

export function useCampusToday(
  institutionId: number,
  options: { demo?: boolean; role?: CampusOsRole; institutionName?: string } = {},
) {
  const demo = options.demo ?? false;
  return useQuery({
    queryKey: campusOsKeys.today(institutionId, demo),
    queryFn: () =>
      demo
        ? Promise.resolve(
            demoToday(
              options.role ?? "admin",
              options.institutionName ?? "your campus",
            ),
          )
        : campusOsApi.today(institutionId),
    enabled: institutionId > 0,
  });
}

export function useUpdateTodayAction(institutionId: number, demo = false) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ actionId, status }: { actionId: string; status: TodayActionStatus }) => {
      if (!demo) await campusOsApi.updateTodayAction(institutionId, actionId, status);
      return { actionId, status };
    },
    onSuccess: (_result, variables) => {
      queryClient.setQueriesData<TodayDashboard>(
        { queryKey: campusOsKeys.today(institutionId, demo) },
        (current) =>
          current
            ? {
                ...current,
                actions: current.actions.map((action) =>
                  action.id === variables.actionId
                    ? { ...action, status: variables.status }
                    : action,
                ),
              }
            : current,
      );
      if (!demo) {
        void queryClient.invalidateQueries({
          queryKey: campusOsKeys.today(institutionId, demo),
        });
      }
    },
  });
}

export function useAdmissionSummary(institutionId: number, demo = false) {
  return useQuery({
    queryKey: campusOsKeys.admissionSummary(institutionId, demo),
    queryFn: () =>
      demo
        ? Promise.resolve(demoAdmissionSummary())
        : campusOsApi.admissionSummary(institutionId),
    enabled: institutionId > 0,
  });
}

export function useAdmissionApplications(
  institutionId: number,
  filters: AdmissionApplicationFilters,
  demo = false,
) {
  return useQuery({
    queryKey: campusOsKeys.applications(institutionId, filters, demo),
    queryFn: () => {
      if (!demo) return campusOsApi.admissionApplications(institutionId, filters);
      const search = filters.search?.trim().toLowerCase() ?? "";
      const matching = demoApplications.filter(
        (item) =>
          (!search ||
            `${item.full_name} ${item.email} ${item.application_number}`
              .toLowerCase()
              .includes(search)) &&
          (!filters.stage || item.stage === filters.stage) &&
          (!filters.intake_id || item.intake_id === filters.intake_id),
      );
      const offset = filters.offset ?? 0;
      const limit = filters.limit ?? 25;
      return Promise.resolve({
        items: matching.slice(offset, offset + limit),
        total: matching.length,
        limit,
        offset,
      });
    },
    enabled: institutionId > 0,
    placeholderData: keepPreviousData,
  });
}

export function useAdmissionPrograms(institutionId: number, demo = false) {
  return useQuery({
    queryKey: campusOsKeys.programs(institutionId, demo),
    queryFn: () =>
      demo ? Promise.resolve(demoPrograms) : campusOsApi.admissionPrograms(institutionId),
    enabled: institutionId > 0,
  });
}

export function useAdmissionIntakes(institutionId: number, demo = false) {
  return useQuery({
    queryKey: campusOsKeys.intakes(institutionId, demo),
    queryFn: () =>
      demo ? Promise.resolve(demoIntakes) : campusOsApi.admissionIntakes(institutionId),
    enabled: institutionId > 0,
  });
}

export function useFeeSummary(institutionId: number, asOf: string, demo = false) {
  return useQuery({
    queryKey: campusOsKeys.feeSummary(institutionId, asOf, demo),
    queryFn: () =>
      demo
        ? Promise.resolve({ ...demoFeeSummary, as_of: asOf })
        : campusOsApi.feeSummary(institutionId, asOf),
    enabled: institutionId > 0 && Boolean(asOf),
  });
}

export function useFeeAging(institutionId: number, asOf: string, demo = false) {
  return useQuery({
    queryKey: campusOsKeys.feeAging(institutionId, asOf, demo),
    queryFn: () =>
      demo
        ? Promise.resolve({ ...demoFeeAging, as_of: asOf })
        : campusOsApi.feeAging(institutionId, asOf),
    enabled: institutionId > 0 && Boolean(asOf),
  });
}

export function useFeePlans(institutionId: number, demo = false) {
  return useQuery({
    queryKey: campusOsKeys.feePlans(institutionId, demo),
    queryFn: () =>
      demo ? Promise.resolve(demoFeePlans) : campusOsApi.feePlans(institutionId),
    enabled: institutionId > 0,
  });
}

const demoSelfAccounts: TuitionSelfAccounts = {
  student: { member_id: 301, user_id: 901, name: "Arjun Rao", email: "arjun.rao@example.edu" },
  assignments: [
    {
      id: 401,
      institution_id: 1,
      student: { member_id: 301, user_id: 901, name: "Arjun Rao", email: "arjun.rao@example.edu" },
      plan: { id: 501, name: "Grade 11 · 2026–27", academic_year: "2026–27" },
      currency: "INR",
      status: "active",
      assigned_on: "2026-06-20",
      note: "",
      gross_amount: 96000,
      discounts_total: 6000,
      waivers_total: 0,
      paid_total: 48000,
      balance: 42000,
      installments: [
        { id: 1, name: "Term 1", sequence: 1, due_on: "2026-07-10", amount_due: 48000, credited: 48000, balance: 0, status: "paid" },
        { id: 2, name: "Term 2", sequence: 2, due_on: "2026-12-10", amount_due: 42000, credited: 0, balance: 42000, status: "upcoming" },
      ],
      payments: [
        { id: 1, amount: 48000, paid_at: "2026-07-08T09:30:00Z", method: "upi", reference: "UPI-842019", note: "", status: "posted", receipt: { id: 1, receipt_number: "REC-2026-0048", issued_at: "2026-07-08T09:30:00Z" }, received_by: null, verification: { status: "not_required", verified_by: null, verified_at: null, note: "" } },
      ],
      adjustments: [
        { id: 1, kind: "discount", amount: 6000, reason: "Merit scholarship", installment_id: 2, status: "posted", created_at: "2026-06-22T08:00:00Z" },
      ],
    },
  ],
};

export function useFeeSelf(
  institutionId: number,
  studentUserId?: number,
  demo = false,
) {
  return useQuery({
    queryKey: campusOsKeys.feeSelf(institutionId, studentUserId, demo),
    queryFn: () =>
      demo
        ? Promise.resolve(demoSelfAccounts)
        : campusOsApi.feeSelf(institutionId, studentUserId),
    enabled: institutionId > 0,
  });
}

export function useCashDesk(institutionId: number, day: string, enabled = true) {
  return useQuery({
    queryKey: campusOsKeys.cashDesk(institutionId, day),
    queryFn: () => campusOsApi.cashDesk(institutionId, day),
    enabled: enabled && institutionId > 0 && Boolean(day),
  });
}

export function useOnlineStatus(institutionId: number, enabled = true) {
  return useQuery({
    queryKey: campusOsKeys.onlineStatus(institutionId),
    queryFn: () => campusOsApi.onlineStatus(institutionId),
    enabled: enabled && institutionId > 0,
    staleTime: 5 * 60_000,
  });
}
