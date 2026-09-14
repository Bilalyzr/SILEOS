import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { InstitutionOverview } from "@/api/institutions";

const transport = vi.hoisted(() => ({
  routes: vi.fn(),
  createRoute: vi.fn(),
  updateRoute: vi.fn(),
  roster: vi.fn(),
  rosterCsv: vi.fn(),
  boarding: vi.fn(),
  assign: vi.fn(),
  end: vi.fn(),
  me: vi.fn(),
}));
const hostel = vi.hoisted(() => ({
  blocks: vi.fn(),
  createBlock: vi.fn(),
  updateBlock: vi.fn(),
  saveRooms: vi.fn(),
  occupancy: vi.fn(),
  occupancyCsv: vi.fn(),
  allocate: vi.fn(),
  checkout: vi.fn(),
  passes: vi.fn(),
  createPass: vi.fn(),
  approvePass: vi.fn(),
  rejectPass: vi.fn(),
  returnPass: vi.fn(),
  visitors: vi.fn(),
  logVisitor: vi.fn(),
  visitorCheckout: vi.fn(),
  me: vi.fn(),
}));
const auth = vi.hoisted(() => ({ user: { id: 7, role: "instructor" } as { id: number; role: string } }));
vi.mock("@/api/campus-transport", () => ({ transportApi: transport }));
vi.mock("@/api/campus-hostel", () => ({ hostelApi: hostel }));
vi.mock("@/api/campus-exams", () => ({ openBlob: vi.fn() }));
vi.mock("@/store/auth", () => ({ useAuthStore: (fn: (s: unknown) => unknown) => fn({ user: auth.user }) }));
vi.mock("react-hot-toast", () => ({ default: { success: vi.fn(), error: vi.fn() } }));

import { CampusTransport } from "../CampusTransport";
import { CampusHostel } from "../CampusHostel";

const route = {
  id: 1, name: "North loop", vehicle_number: "TN 01", driver_name: "Kumar", driver_phone: "", capacity: 2, occupied: 1,
  fee_amount: 1500, currency: "INR", fee_plan_id: 9, active: true,
  stops: [{ id: 11, sequence: 1, name: "Anna Nagar", pickup_time: "07:10", drop_time: "", landmark: "" }],
};
const roster = {
  route, day: "2026-09-12",
  students: [{ id: 5, route_id: 1, stop_id: 11, stop_name: "Anna Nagar", member_id: 21, student_name: "Asha", fee_assignment_id: 3, status: "active", started_on: "2026-09-12", ended_on: null, boarded: null, dropped: null }],
};
const data = {
  institution: { id: 3, role: "owner" },
  members: [
    { id: 21, user_id: 70, name: "Asha", email: "", role: "student", department: "", status: "active" },
    { id: 22, user_id: 71, name: "Ravi", email: "", role: "student", department: "", status: "active" },
    { id: 30, user_id: 72, name: "Meena", email: "", role: "teacher", department: "", status: "active" },
  ],
  batches: [],
} as unknown as InstitutionOverview;

function mount(ui: React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{ui}</QueryClientProvider>);
}

afterEach(cleanup);
beforeEach(() => {
  vi.resetAllMocks();
  auth.user = { id: 7, role: "instructor" };
  transport.routes.mockResolvedValue([route]);
  transport.roster.mockResolvedValue(roster);
  transport.assign.mockResolvedValue({ ...roster.students[0], id: 6, member_id: 22, student_name: "Ravi" });
  transport.boarding.mockResolvedValue(roster);
  transport.me.mockResolvedValue({ assigned: true, route: { id: 1, name: "North loop", vehicle_number: "TN 01", driver_name: "Kumar", driver_phone: "" }, stop: route.stops[0], today: { day: "2026-09-12", boarded: true, dropped: false } });
  hostel.occupancy.mockResolvedValue({
    capacity: 3, occupied: 1,
    blocks: [{ id: 1, name: "Block A", warden_member_id: 30, warden_name: "Meena", gender: "any", fee_amount: 24000, currency: "INR", fee_plan_id: 8, active: true, capacity: 3, occupied: 1, rooms: [{ id: 101, block_id: 1, number: "101", floor: "1", room_type: "double", capacity: 2, occupied: 1, active: true }, { id: 102, block_id: 1, number: "102", floor: "1", room_type: "single", capacity: 1, occupied: 0, active: true }] }],
    allocations: [{ id: 50, room_id: 101, room_number: "101", block_id: 1, block_name: "Block A", member_id: 21, student_name: "Asha", fee_assignment_id: 4, status: "active", checked_in_on: "2026-09-01", checked_out_on: null }],
  });
  hostel.allocate.mockResolvedValue({ id: 51, room_id: 102, room_number: "102", block_id: 1, block_name: "Block A", member_id: 22, student_name: "Ravi", fee_assignment_id: 5, status: "active", checked_in_on: "2026-09-12", checked_out_on: null });
  hostel.passes.mockResolvedValue([{ id: 9, member_id: 21, student_name: "Asha", kind: "outpass", reason: "Dentist", leaves_at: "2026-09-13T04:00:00+00:00", returns_at: "2026-09-13T10:00:00+00:00", status: "pending", decided_by: null, decided_at: null, decision_note: "", returned_at: null, created_at: null }]);
  hostel.approvePass.mockResolvedValue({ id: 9, status: "approved" });
  hostel.me.mockResolvedValue({ resident: true, allocation: { id: 50, room_id: 101, room_number: "101", block_id: 1, block_name: "Block A", member_id: 21, student_name: "Asha", fee_assignment_id: 4, status: "active", checked_in_on: "2026-09-01", checked_out_on: null }, passes: [] });
});

describe("campus transport", () => {
  it("assigns an unassigned student to a stop and records boarding", async () => {
    mount(<CampusTransport data={data} />);
    await screen.findByRole("heading", { name: "North loop" });
    await screen.findByLabelText("Boarded Asha");
    const select = screen.getByLabelText("Student to assign");
    expect(Array.from((select as HTMLSelectElement).options).map((o) => o.textContent)).toEqual(["Choose…", "Ravi"]);
    fireEvent.change(select, { target: { value: "22" } });
    fireEvent.click(screen.getByRole("button", { name: "Assign to route" }));
    await waitFor(() => expect(transport.assign).toHaveBeenCalledWith(3, 1, 22, 11));
    fireEvent.click(screen.getByLabelText("Boarded Asha"));
    fireEvent.click(screen.getByRole("button", { name: "Save boarding" }));
    await waitFor(() => expect(transport.boarding).toHaveBeenCalledWith(3, 1, "2026-09-12", [{ member_id: 21, boarded: true, dropped: false }]));
  });

  it("shows a student their own route and status", async () => {
    auth.user = { id: 70, role: "student" };
    mount(<CampusTransport data={{ ...data, institution: { id: 3, role: "student" } } as unknown as InstitutionOverview} studentUserId={70} />);
    await screen.findByText("Boarded");
    expect(screen.getByText("Anna Nagar")).toBeTruthy();
    expect(transport.me).toHaveBeenCalledWith(3, undefined);
  });
});

describe("campus hostel", () => {
  it("allocates a free room to a non-resident and approves a pass", async () => {
    mount(<CampusHostel data={data} />);
    await screen.findByRole("heading", { name: "Block A" });
    const buttons = screen.getAllByRole("button", { name: "Allocate" });
    expect(buttons[0].hasAttribute("disabled")).toBe(false);
    fireEvent.click(buttons[1]);
    const select = await screen.findByLabelText("Resident");
    expect(Array.from((select as HTMLSelectElement).options).map((o) => o.textContent)).toEqual(["Choose…", "Ravi"]);
    fireEvent.change(select, { target: { value: "22" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Allocate" }).at(-1)!);
    await waitFor(() => expect(hostel.allocate).toHaveBeenCalledWith(3, 102, 22));
    fireEvent.click(screen.getByRole("tab", { name: "Out-passes" }));
    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));
    await waitFor(() => expect(hostel.approvePass).toHaveBeenCalledWith(3, 9));
  });

  it("lets a resident request an out-pass", async () => {
    auth.user = { id: 70, role: "student" };
    mount(<CampusHostel data={{ ...data, institution: { id: 3, role: "student" } } as unknown as InstitutionOverview} studentUserId={70} />);
    await screen.findByText("Block A · Room 101");
    fireEvent.click(screen.getByRole("button", { name: "Request out-pass" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(dialog.querySelector('input[name="leaves_at"]')!, { target: { value: "2026-09-20T09:00" } });
    fireEvent.change(dialog.querySelector('input[name="returns_at"]')!, { target: { value: "2026-09-20T18:00" } });
    fireEvent.change(dialog.querySelector('input[name="reason"]')!, { target: { value: "Family visit" } });
    fireEvent.click(screen.getByRole("button", { name: "Send request" }));
    await waitFor(() => expect(hostel.createPass).toHaveBeenCalled());
    expect(hostel.createPass.mock.calls[0][1].reason).toBe("Family visit");
  });
});
