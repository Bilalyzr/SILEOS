import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RuntimeMonitor } from "../RuntimeMonitor";
import { api } from "@/api/axios";
vi.mock("@/api/axios", () => ({ api: { get: vi.fn(), post: vi.fn() } }));
vi.mock("@/api/planner", () => ({ plannerError: () => "Runtime request failed" }));
const runtime = { mode: "worker", worker: { status: "unknown", last_seen: null }, runs: [], queues: { email: { failed: 2 }, recordings: {} }, providers: [], jobs: [
  { name: "payment_reconciliation", label: "Payments & memberships", status: "dead", attempts: 5, max_attempts: 5,
    next_run_at: null, last_finished_at: null, last_error: "TimeoutError", lease_expired: false },
] };
describe("Runtime recovery", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.get).mockImplementation(async url => ({ data: String(url).endsWith("telemetry") ? { status: "unavailable" } : runtime }));
  });
  it("shows missing evidence honestly and queues a failed job without claiming success", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { status: "queued" } });
    render(<MemoryRouter><RuntimeMonitor /></MemoryRouter>);
    expect(await screen.findByText("Payments & memberships")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getByText("No active AI providers configured.")).toBeInTheDocument();
    expect(screen.getByText("No records yet")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Queue safe retry" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/admin/operations/runtime/payment_reconciliation/retry"));
    expect(await screen.findByText(/Retry queued/)).toBeInTheDocument();
  });
  it("keeps failed retry visible", async () => {
    vi.mocked(api.post).mockRejectedValue(new Error("409"));
    render(<MemoryRouter><RuntimeMonitor /></MemoryRouter>);
    fireEvent.click(await screen.findByRole("button", { name: "Queue safe retry" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Runtime request failed");
    expect(screen.queryByText(/Retry queued/)).not.toBeInTheDocument();
  });
});
