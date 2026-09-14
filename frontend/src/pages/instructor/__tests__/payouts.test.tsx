import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import InstructorPayoutsPage from "../payouts";

const mocks = vi.hoisted(() => ({ mine: vi.fn(), request: vi.fn() }));
vi.mock("@/api/payouts", async () => {
  const actual = await vi.importActual<typeof import("@/api/payouts")>("@/api/payouts");
  return { ...actual, payoutAPI: mocks };
});

const ledger = {
  balance: { earned: 2000, withdrawn_or_pending: 500, available: 1500 },
  min_withdrawal_inr: 500,
  items: [
    {
      id: 7,
      amount: 500,
      method_data: {
        type: "bank" as const,
        account_holder: "Course Coach",
        account_number: "123456789012",
        ifsc: "HDFC0001234",
        bank_name: "HDFC",
      },
      status: "paid" as const,
      reject_detail: "",
      paid_reference: "UTR-7",
      created_at: "2026-09-12T00:00:00Z",
      processed_at: "2026-09-13T00:00:00Z",
    },
  ],
};

beforeEach(() => {
  vi.resetAllMocks();
  mocks.mine.mockResolvedValue(ledger);
  mocks.request.mockResolvedValue({ ...ledger.items[0], id: 8, status: "pending" });
});
afterEach(cleanup);

it("masks bank details and submits a UPI withdrawal", async () => {
  render(<InstructorPayoutsPage />);
  expect(await screen.findByText(/•••• 9012/)).toBeInTheDocument();
  expect(screen.queryByText(/123456789012/)).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Request withdrawal" }));
  const dialog = screen.getByRole("dialog");
  fireEvent.change(within(dialog).getByLabelText("Amount (INR)"), {
    target: { value: "750" },
  });
  fireEvent.change(within(dialog).getByLabelText("UPI ID"), {
    target: { value: "coach@upi" },
  });
  fireEvent.click(within(dialog).getByRole("button", { name: "Submit request" }));

  await waitFor(() =>
    expect(mocks.request).toHaveBeenCalledWith(750, {
      type: "upi",
      upi_id: "coach@upi",
    }),
  );
  expect(await screen.findByText(/submitted for admin review/i)).toBeInTheDocument();
});
