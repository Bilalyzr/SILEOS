import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const api = vi.hoisted(() => ({
  policy: vi.fn(),
  savePolicy: vi.fn(),
  list: vi.fn(),
  runNow: vi.fn(),
  retry: vi.fn(),
  remind: vi.fn(),
}));
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));
vi.mock("@/api/tuition-reminders", () => ({ remindersApi: api }));
vi.mock("react-hot-toast", () => ({ default: toast }));

import { FeeReminders } from "../FeeReminders";

const policy = {
  institution_id: 3,
  enabled: false,
  days_before: [7, 1],
  overdue_every_days: 7,
  overdue_max: 3,
  send_hour: 9,
  channels: ["whatsapp", "email"],
  whatsapp_template: "",
  whatsapp_language: "en",
  updated_at: null,
};
const rows = [
  {
    id: 1, assignment_id: 9, installment_id: 4, receipt_id: null, student_member_id: 2, student_name: "Asha",
    recipient_user_id: 5, recipient_name: "Asha", recipient_role: "student", kind: "overdue", stage: "overdue:1",
    channel: "email", status: "failed", skip_reason: "", error: "Email delivery failed.", attempts: 1,
    amount: 1000, currency: "INR", due_on: "2026-09-01", created_at: "2026-09-11T09:00:00Z", sent_at: null,
  },
  {
    id: 2, assignment_id: 9, installment_id: 4, receipt_id: null, student_member_id: 2, student_name: "Asha",
    recipient_user_id: 6, recipient_name: "Ravi", recipient_role: "parent", kind: "overdue", stage: "overdue:1",
    channel: "whatsapp", status: "skipped", skip_reason: "no_consent", error: "", attempts: 0,
    amount: 1000, currency: "INR", due_on: "2026-09-01", created_at: "2026-09-11T09:00:00Z", sent_at: null,
  },
];

function mount() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <FeeReminders institutionId={3} />
    </QueryClientProvider>,
  );
}

afterEach(cleanup);
beforeEach(() => {
  vi.resetAllMocks();
  api.policy.mockResolvedValue(policy);
  api.list.mockResolvedValue({ items: rows, next_after_id: null });
  api.savePolicy.mockImplementation(async (_id: number, input: typeof policy) => ({ ...policy, ...input }));
  api.runNow.mockResolvedValue({ staged: 4, sent: 2, failed: 1, skipped: 1 });
  api.retry.mockResolvedValue({ ...rows[0], status: "sent", error: "" });
});

describe("fee reminders", () => {
  it("saves the policy with parsed day values", async () => {
    mount();
    fireEvent.click(await screen.findByLabelText("Send reminders automatically"));
    fireEvent.change(screen.getByLabelText("Days before due date"), { target: { value: "10, 3, 3, x" } });
    fireEvent.change(screen.getByLabelText("WhatsApp template name"), { target: { value: "fee_reminder" } });
    fireEvent.click(screen.getByRole("button", { name: "Save policy" }));
    await waitFor(() =>
      expect(api.savePolicy).toHaveBeenCalledWith(3, {
        enabled: true,
        days_before: [10, 3],
        overdue_every_days: 7,
        overdue_max: 3,
        send_hour: 9,
        channels: ["whatsapp", "email"],
        whatsapp_template: "fee_reminder",
        whatsapp_language: "en",
      }),
    );
  });

  it("runs now and shows the counts", async () => {
    mount();
    fireEvent.click(await screen.findByRole("button", { name: "Run now" }));
    await waitFor(() => expect(api.runNow).toHaveBeenCalledWith(3));
    await screen.findByText(/4 staged · 2 sent · 1 failed · 1 skipped/);
  });

  it("explains skips and offers retry only on failed rows", async () => {
    mount();
    await screen.findByText("No WhatsApp consent");
    const retries = screen.getAllByRole("button", { name: "Retry" });
    expect(retries).toHaveLength(1);
    fireEvent.click(retries[0]);
    await waitFor(() => expect(api.retry).toHaveBeenCalledWith(3, 1));
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith("Reminder sent"));
  });
});
