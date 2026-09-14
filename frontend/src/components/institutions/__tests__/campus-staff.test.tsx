import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { InstitutionOverview } from "@/api/institutions";

const api = vi.hoisted(() => ({
  types: vi.fn(),
  saveTypes: vi.fn(),
  balances: vi.fn(),
  leave: vi.fn(),
  createLeave: vi.fn(),
  approve: vi.fn(),
  reject: vi.fn(),
  cancel: vi.fn(),
  substitutions: vi.fn(),
  candidates: vi.fn(),
  assign: vi.fn(),
  unassign: vi.fn(),
  report: vi.fn(),
  reportCsv: vi.fn(),
}));
vi.mock("@/api/campus-staff", () => ({ staffApi: api }));
vi.mock("@/api/campus-exams", () => ({ openBlob: vi.fn() }));
vi.mock("react-hot-toast", () => ({ default: { success: vi.fn(), error: vi.fn() } }));

import { CampusStaff } from "../CampusStaff";

const pending = {
  id: 4, member_id: 2, member_name: "Ravi", type_id: 1, type_code: "CL", type_name: "Casual leave",
  starts_on: "2026-10-01", ends_on: "2026-10-02", days: 2, note: "", status: "pending", decided_by: null,
  decided_at: null, decision_note: "", override: false, substitutions: { total: 0, open: 0, assigned: 0 }, created_at: null,
};
const openSub = {
  id: 9, leave_id: 4, event_id: 11, title: "Physics", kind: "class", starts_at: "2026-10-01T09:00:00+00:00",
  ends_at: "2026-10-01T10:00:00+00:00", room: "Lab 1", batch_id: 2, batch_name: "Grade 9", absent_member_id: 2,
  absent_name: "Ravi", substitute_member_id: null, substitute_name: null, status: "open", note: "", assigned_at: null,
};

function mount(role: string) {
  const data = { institution: { id: 3, role, academic_year: "2026-27" }, batches: [] } as unknown as InstitutionOverview;
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <CampusStaff data={data} />
    </QueryClientProvider>,
  );
}

afterEach(cleanup);
beforeEach(() => {
  vi.resetAllMocks();
  api.types.mockResolvedValue({ academic_year: "2026-27", types: [{ id: 1, academic_year: "2026-27", code: "CL", name: "Casual leave", annual_quota: 12 }] });
  api.balances.mockResolvedValue({ member_id: 2, name: "Ravi", academic_year: "2026-27", balances: [{ type_id: 1, code: "CL", name: "Casual leave", quota: 12, used: 2, remaining: 10 }] });
  api.leave.mockResolvedValue([pending]);
  api.createLeave.mockResolvedValue({ ...pending, id: 5 });
  api.approve.mockResolvedValue({ ...pending, status: "approved", substitutions: { total: 2, open: 2, assigned: 0 } });
  api.substitutions.mockResolvedValue([openSub]);
  api.candidates.mockResolvedValue([{ member_id: 7, name: "Meena", role: "teacher", department: "Science" }]);
  api.assign.mockResolvedValue({ ...openSub, status: "assigned", substitute_member_id: 7, substitute_name: "Meena" });
});

describe("campus staff", () => {
  it("lets a teacher apply for leave and hides approvals", async () => {
    mount("teacher");
    await screen.findByText("Casual leave: 10 of 12 left");
    expect(screen.queryByRole("tab", { name: "Approvals" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Apply for leave" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(dialog.querySelector('input[name="starts_on"]')!, { target: { value: "2026-11-03" } });
    fireEvent.change(dialog.querySelector('input[name="ends_on"]')!, { target: { value: "2026-11-04" } });
    fireEvent.click(screen.getByRole("button", { name: "Send request" }));
    await waitFor(() => expect(api.createLeave).toHaveBeenCalledWith(3, { type_id: 1, starts_on: "2026-11-03", ends_on: "2026-11-04", note: "" }));
  });

  it("lets a manager approve with an override note", async () => {
    mount("owner");
    fireEvent.click(await screen.findByRole("tab", { name: "Approvals" }));
    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));
    fireEvent.change(await screen.findByLabelText("Decision note"), { target: { value: "Bereavement" } });
    fireEvent.click(screen.getByLabelText("Override the quota"));
    fireEvent.click(screen.getAllByRole("button", { name: "Approve" }).at(-1)!);
    await waitFor(() => expect(api.approve).toHaveBeenCalledWith(3, 4, { override: true, note: "Bereavement" }));
  });

  it("assigns a free colleague to an open substitution", async () => {
    mount("owner");
    fireEvent.click(await screen.findByRole("tab", { name: "Substitutions" }));
    fireEvent.click(await screen.findByRole("button", { name: "Assign" }));
    const select = await screen.findByLabelText("Substitute");
    fireEvent.change(select, { target: { value: "7" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Assign" }).at(-1)!);
    await waitFor(() => expect(api.assign).toHaveBeenCalledWith(3, 9, 7));
  });
});
