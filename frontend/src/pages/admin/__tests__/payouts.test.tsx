import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ConfirmProvider } from "@/components/ui/confirm";
import AdminPayoutsPage from "../payouts";

const mocks = vi.hoisted(() => ({
  adminList: vi.fn(),
  approve: vi.fn(),
  reject: vi.fn(),
  markPaid: vi.fn(),
}));
vi.mock("@/api/payouts", async () => {
  const actual = await vi.importActual<typeof import("@/api/payouts")>("@/api/payouts");
  return { ...actual, payoutAPI: mocks };
});

const request = {
  id: 12,
  user_id: 4,
  user_email: "coach@example.com",
  display_name: "Course Coach",
  processed_by: null,
  amount: 800,
  method_data: {
    type: "bank" as const,
    account_holder: "Course Coach",
    account_number: "123456789012",
    ifsc: "HDFC0001234",
    bank_name: "HDFC",
  },
  status: "pending" as const,
  reject_detail: "",
  paid_reference: "",
  created_at: "2026-09-12T00:00:00Z",
  processed_at: null,
};

beforeEach(() => {
  vi.resetAllMocks();
  mocks.adminList.mockResolvedValue([request]);
  mocks.approve.mockResolvedValue({ ...request, status: "approved" });
});
afterEach(cleanup);

it("keeps bank numbers masked and confirms an approval", async () => {
  render(
    <ConfirmProvider>
      <AdminPayoutsPage />
    </ConfirmProvider>,
  );
  expect(await screen.findByText(/•••• 9012/)).toBeInTheDocument();
  expect(screen.queryByText(/123456789012/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Approve" }));
  const dialog = screen.getByRole("dialog");
  fireEvent.click(within(dialog).getByRole("button", { name: "Approve request" }));
  await waitFor(() => expect(mocks.approve).toHaveBeenCalledWith(12));
});
