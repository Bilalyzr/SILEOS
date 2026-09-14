import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { InstitutionOverview } from "@/api/institutions";

const axios = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));
const checkout = vi.hoisted(() => ({ openRazorpay: vi.fn() }));
const blobs = vi.hoisted(() => ({ openBlob: vi.fn() }));
const reminders = vi.hoisted(() => ({ policy: vi.fn(), list: vi.fn(), savePolicy: vi.fn(), runNow: vi.fn(), retry: vi.fn(), remind: vi.fn() }));

vi.mock("@/api/axios", () => ({ api: axios }));
vi.mock("react-hot-toast", () => ({ default: toast }));
vi.mock("@/lib/razorpayCheckout", () => checkout);
vi.mock("@/api/campus-exams", () => blobs);
vi.mock("@/api/tuition-reminders", () => ({ remindersApi: reminders }));
vi.mock("@/store/auth", () => ({ useAuthStore: (selector: (s: { user: { id: number } }) => unknown) => selector({ user: { id: 1 } }) }));

import { CampusFinance } from "../CampusFinance";

const overview = {
  institution: { id: 3, name: "Greenwood College", academic_year: "2026-27", role: "owner", timezone: "Asia/Kolkata" },
  members: [
    { id: 1, user_id: 1, name: "Owner One", email: "owner@example.org", role: "owner", department: "", status: "active" },
    { id: 2, user_id: 2, name: "Admin Two", email: "admin@example.org", role: "admin", department: "", status: "active" },
    { id: 7, user_id: 70, name: "Asha Rao", email: "asha@example.org", role: "student", department: "", status: "active" },
  ],
  batches: [],
  courses: [],
  invites: [],
  activity: [],
  usage: { members: 3, reserved_seats: 0 },
} as unknown as InstitutionOverview;

const summary = {
  as_of: "2026-09-12", currency: "INR", mixed_currency: false,
  totals: { assessed: 3000, discounts: 0, waivers: 0, paid: 300, outstanding: 2700, overdue: 1000, due_today: 0, due_next_30_days: 1000 },
  accounts: { total: 1, with_balance: 1, overdue: 1 },
  aging: { current: 1700, days_1_30: 0, days_31_60: 1000, days_61_90: 0, days_91_plus: 0 },
};
const payment = {
  id: 11, amount: 300, paid_at: "2026-09-12T04:00:00Z", method: "cash", reference: "", note: "", status: "posted",
  receipt: { id: 21, receipt_number: "TF-3-2026-00000011", issued_at: "2026-09-12T04:00:00Z" },
  received_by: { id: 1, name: "Owner One" },
  verification: { status: "pending", verified_by: null, verified_at: null, note: "" },
};
const desk = {
  day: "2026-09-12", currency: "INR",
  rows: [{ payment_id: 11, receipt_id: 21, receipt_number: "TF-3-2026-00000011", student_name: "Asha Rao", plan_name: "Annual tuition", amount: 300, currency: "INR", method: "cash", reference: "", paid_at: "2026-09-12T04:00:00Z", status: "posted", received_by: { id: 1, name: "Owner One" }, verification: { status: "pending", verified_by: null, verified_at: null, note: "" } }],
  receivers: [{ id: 1, name: "Owner One", count: 1, total: 300, pending: 1 }],
  pending_total: 300, verified_total: 0, pending_count: 1, excess_orders: [],
};
const accounts = {
  student: { member_id: 7, user_id: 70, name: "Asha Rao", email: "asha@example.org" },
  assignments: [{
    id: 9, institution_id: 3, student: { member_id: 7, user_id: 70, name: "Asha Rao", email: "asha@example.org" },
    plan: { id: 1, name: "Annual tuition", academic_year: "2026-27" }, currency: "INR", status: "active", assigned_on: "2026-06-01", note: "",
    gross_amount: 3000, discounts_total: 0, waivers_total: 0, paid_total: 300, balance: 2700,
    installments: [
      { id: 1, name: "Term 1", sequence: 1, due_on: "2026-06-04", amount_due: 1000, credited: 300, balance: 700, status: "overdue" },
      { id: 2, name: "Term 2", sequence: 2, due_on: "2026-08-23", amount_due: 1000, credited: 0, balance: 1000, status: "overdue" },
      { id: 3, name: "Term 3", sequence: 3, due_on: "2026-09-22", amount_due: 1000, credited: 0, balance: 1000, status: "due" },
    ],
    payments: [payment],
    adjustments: [],
  }],
};

function route(url: string, ready = true) {
  if (url.endsWith("/fees/summary")) return summary;
  if (url.endsWith("/fees/aging")) return { as_of: "2026-09-12", rows: [{ assignment_id: 9, student_member_id: 7, student_user_id: 70, student_name: "Asha Rao", plan_name: "Annual tuition", currency: "INR", outstanding: 2700, overdue: 1000, oldest_due_on: "2026-06-04", aging: summary.aging }] };
  if (url.endsWith("/fees/plans")) return { items: [] };
  if (url.endsWith("/fees/cash")) return desk;
  if (url.endsWith("/fees/me")) return accounts;
  if (url.endsWith("/fees/online/status")) return { ready };
  throw new Error(`unexpected GET ${url}`);
}

function mount(role: "owner" | "student", ready = true) {
  axios.get.mockImplementation(async (url: string) => ({ data: route(url, ready) }));
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <CampusFinance data={overview} role={role} studentUserId={role === "student" ? 70 : undefined} />
    </QueryClientProvider>,
  );
}

afterEach(cleanup);
beforeEach(() => {
  vi.resetAllMocks();
  reminders.policy.mockResolvedValue({ institution_id: 3, enabled: false, days_before: [7, 1], overdue_every_days: 7, overdue_max: 3, send_hour: 9, channels: ["email"], whatsapp_template: "", whatsapp_language: "en", updated_at: null });
  reminders.list.mockResolvedValue({ items: [], next_after_id: null });
});

describe("cash desk (manager)", () => {
  it("lists pending cash and verifies an entry with a note", async () => {
    axios.post.mockResolvedValue({ data: { ...payment, verification: { status: "verified", verified_by: { id: 2, name: "Admin Two" }, verified_at: "2026-09-12T05:00:00Z", note: "counted" } } });
    mount("owner");
    await screen.findByRole("heading", { name: "Cash desk" });
    expect(await screen.findByText("Asha Rao", { selector: "strong" })).toBeTruthy();
    expect(screen.getAllByText("Pending").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: /^Verify$/ }));
    const note = await screen.findByPlaceholderText("Counted and matched the drawer");
    fireEvent.change(note, { target: { value: "counted" } });
    fireEvent.click(screen.getByRole("button", { name: "Mark verified" }));
    await waitFor(() => expect(axios.post).toHaveBeenCalledWith("/institutions/3/fees/payments/11/verify", { note: "counted" }));
    expect(toast.success).toHaveBeenCalledWith("Cash verified");
  });

  it("asks for the receiver only for cash and cheque", async () => {
    mount("owner");
    fireEvent.click(await screen.findByRole("button", { name: "Record payment" }));
    expect(screen.queryByLabelText("Received by")).toBeNull();
    fireEvent.change(screen.getByLabelText("Method"), { target: { value: "cash" } });
    const receiver = (await screen.findByLabelText("Received by")) as HTMLSelectElement;
    expect(receiver.value).toBe("1");
    expect(receiver.options.length).toBe(3); // placeholder + owner + admin, no student
  });
});

describe("learner fee page", () => {
  it("starts an online payment for one installment and verifies it", async () => {
    axios.post.mockImplementation(async (url: string) => {
      if (url.endsWith("/online-orders")) return { data: { order: { id: 5, status: "created" }, checkout: { key: "rzp_test", order_id: "order_1", amount_paise: 100000, currency: "INR", name: "Greenwood College", description: "Annual tuition · Term 2", prefill: { name: "Asha", email: "" } } } };
      if (url.endsWith("/online-orders/5/verify")) return { data: { id: 5, status: "paid", payment } };
      throw new Error(`unexpected POST ${url}`);
    });
    checkout.openRazorpay.mockImplementation(async (_c, handlers) => {
      handlers.onSuccess({ razorpay_order_id: "order_1", razorpay_payment_id: "pay_1", razorpay_signature: "sig" });
    });
    mount("student");
    fireEvent.click(await screen.findByRole("button", { name: "Pay online · Term 2" }));
    await waitFor(() => expect(axios.post).toHaveBeenCalledWith("/institutions/3/fees/assignments/9/online-orders", { installment_id: 2, amount: null }));
    await waitFor(() => expect(axios.post).toHaveBeenCalledWith("/institutions/3/fees/online-orders/5/verify", { razorpay_order_id: "order_1", razorpay_payment_id: "pay_1", razorpay_signature: "sig" }));
    expect(toast.success).toHaveBeenCalledWith("Paid · receipt TF-3-2026-00000011");
  });

  it("shows the honest notice and disables paying when the gateway is not set up", async () => {
    mount("student", false);
    await screen.findByText("Online payment is not set up for this campus yet. Pay at the office or ask them to enable it.");
    const button = (await screen.findByRole("button", { name: "Pay online · Term 2" })) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Pay balance" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("opens invoice and receipt PDFs", async () => {
    axios.post.mockResolvedValue({ data: { id: 4, invoice_number: "TI-3-2026-000004" } });
    mount("student");
    // mount() installs the JSON router; blob downloads need the responseType-aware version.
    axios.get.mockImplementation(async (url: string, config?: { responseType?: string }) => {
      if (config?.responseType === "blob") return { data: new Blob(["%PDF"]) };
      return { data: route(url) };
    });
    fireEvent.click(await screen.findByRole("button", { name: "Invoice · Term 3" }));
    await waitFor(() => expect(axios.post).toHaveBeenCalledWith("/institutions/3/fees/assignments/9/invoices", { installment_id: 3 }));
    await waitFor(() => expect(blobs.openBlob).toHaveBeenCalledWith(expect.any(Blob), "invoice-TI-3-2026-000004.pdf"));
    fireEvent.click(screen.getByRole("button", { name: "Receipt PDF · TF-3-2026-00000011" }));
    await waitFor(() => expect(blobs.openBlob).toHaveBeenCalledWith(expect.any(Blob), "receipt-TF-3-2026-00000011.pdf"));
    expect(screen.getByText(/received by Owner One/)).toBeTruthy();
  });
});
