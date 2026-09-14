import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const portal = vi.hoisted(() => ({ overview: vi.fn() }));
const axios = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
const checkout = vi.hoisted(() => ({ openRazorpay: vi.fn() }));
vi.mock("@/api/parent-portal", () => ({ parentPortalApi: portal }));
vi.mock("@/api/axios", () => ({ api: axios }));
vi.mock("@/lib/razorpayCheckout", () => checkout);
vi.mock("react-hot-toast", () => ({ default: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/components/design-system/PageLayout", () => ({
  PageLayout: ({ children, header }: { children: React.ReactNode; header: React.ReactNode }) => (
    <main>
      {header}
      {children}
    </main>
  ),
  PageHeader: ({ children }: { children: React.ReactNode }) => <header>{children}</header>,
}));

import ParentDashboard from "../parent/dashboard";

function mount() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>
        <ParentDashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(cleanup);
beforeEach(() => {
  vi.resetAllMocks();
  axios.get.mockResolvedValue({ data: { digests: [] } });
  portal.overview.mockResolvedValue({
    pending_requests: 1,
    generated_at: "2026-09-12T10:00:00+00:00",
    children: [
      {
        student: { id: 70, name: "Diya Shah", email: "diya@example.org" },
        institutions: [
          {
            institution: { id: 1, name: "Greenwood College", academic_year: "2026-27", timezone: "Asia/Kolkata" },
            member_id: 3,
            batches: ["Grade 8"],
            attendance: { present: 4, total: 8, percent: 50 },
            fees: { currency: "INR", outstanding: 2000, overdue: 1000, next_due: { name: "Tuition · Overdue part", due_on: "2026-09-02", balance: 1000, assignment_id: 5, installment_id: 12 }, accounts: 1, assignment_id: 5 },
            exams: [{ id: 1, name: "Unit test 1", status: "published", published_at: "2026-09-12T09:00:00+00:00", total: 45, max_total: 50, percent: 90, passed: true, rank: 1, students: 2 }],
            transport: { assigned: true, route: { id: 1, name: "Loop", vehicle_number: "TN 01", driver_name: "Kumar", driver_phone: "" }, stop: { id: 1, sequence: 1, name: "Gate", pickup_time: "07:00", drop_time: "", landmark: "" }, today: { day: "2026-09-12", boarded: false, dropped: false } },
            hostel: { resident: true, block: "Girls block", room: "G1", pending_pass: { id: 9, status: "pending" }, approved_pass: null },
            notices: [{ id: 5, title: "PTM on Friday", body: "Parents are invited.", created_at: "2026-09-11T08:00:00+00:00" }],
            alerts: [
              { kind: "fees_overdue", message: "INR 1,000.00 is overdue." },
              { kind: "attendance_low", message: "Attendance is 50.0% over the last 30 days." },
              { kind: "transport_not_boarded", message: "Not marked as boarded today." },
            ],
          },
        ],
      },
    ],
  });
});

describe("parent portal", () => {
  it("shows every signal for the child in one place", async () => {
    mount();
    await screen.findByRole("heading", { name: "Diya Shah" });
    expect(screen.getByText("Greenwood College")).toBeTruthy();
    expect(screen.getByText("50%")).toBeTruthy();
    expect(screen.getAllByText(/1,000.*overdue/).length).toBeGreaterThan(0);
    expect(screen.getByText("Not boarded")).toBeTruthy();
    expect(screen.getByText("Girls block · G1")).toBeTruthy();
    expect(screen.getByText("Out-pass waiting for approval")).toBeTruthy();
    expect(screen.getByText("Unit test 1")).toBeTruthy();
    expect(screen.getByText("PTM on Friday")).toBeTruthy();
    expect(screen.getByRole("list", { name: "Alerts" }).children).toHaveLength(3);
    expect(screen.getByRole("status").textContent).toContain("1 access request waiting");
  });

  it("offers Pay now and Invoice on the fee tile when something is outstanding", async () => {
    axios.post.mockImplementation(async (url: string) => {
      if (url.endsWith("/online-orders")) return { data: { order: { id: 8, status: "created" }, checkout: { key: "rzp_test", order_id: "order_8", amount_paise: 100000, currency: "INR", name: "Greenwood College", description: "Tuition · Overdue part", prefill: { name: "", email: "" } } } };
      throw new Error(`unexpected POST ${url}`);
    });
    mount();
    await screen.findByRole("heading", { name: "Diya Shah" });
    expect(screen.getByRole("button", { name: "Invoice" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Pay now" }));
    await waitFor(() => expect(axios.post).toHaveBeenCalledWith("/institutions/1/fees/assignments/5/online-orders", { installment_id: 12, amount: null }));
    expect(checkout.openRazorpay).toHaveBeenCalled();
  });

  it("shows the empty state when nothing is linked", async () => {
    portal.overview.mockResolvedValue({ pending_requests: 0, generated_at: "", children: [] });
    mount();
    await screen.findByText("No children linked yet");
  });
});
