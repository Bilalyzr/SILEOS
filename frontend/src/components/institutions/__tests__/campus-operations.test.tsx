import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { InstitutionOverview } from "@/api/institutions";
const api = vi.hoisted(() => ({
  importPeople: vi.fn(),
  academics: vi.fn(),
  attendance: vi.fn(),
  scores: vi.fn(),
  billing: vi.fn(),
  subscribe: vi.fn(),
  price: vi.fn(),
  resources: vi.fn(),
  upload: vi.fn(),
}));
vi.mock("@/api/campus", () => ({ campusApi: api }));
vi.mock("@/store/auth", () => ({
  useAuthStore: (fn: (s: unknown) => unknown) =>
    fn({ user: { id: 7, role: "instructor" } }),
}));
vi.mock("react-hot-toast", () => ({ default: { success: vi.fn() } }));
import { BulkInvites, CampusResources } from "../CampusTools";
import { CampusAcademics } from "../CampusAcademics";
import { CampusBilling } from "../CampusBilling";
const data = {
  institution: { id: 3, role: "owner" },
  batches: [{ id: 2, name: "Class A" }],
} as InstitutionOverview;
function mount(ui: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      {ui}
    </QueryClientProvider>,
  );
}
afterEach(cleanup);
beforeEach(() => {
  vi.resetAllMocks();
});
describe("campus workflows", () => {
  it("requires preview before committing the exact CSV", async () => {
    const result = {
      ready: 1,
      errors: 0,
      available_seats: 10,
      created: 0,
      committed: false,
      rows: [],
    };
    api.importPeople
      .mockResolvedValueOnce(result)
      .mockResolvedValueOnce({ ...result, created: 1, committed: true });
    const saved = vi.fn();
    mount(<BulkInvites id={3} saved={saved} />);
    fireEvent.click(screen.getByText("Import people from CSV"));
    expect(screen.getByText("Create 0 invitations")).toBeDisabled();
    fireEvent.change(screen.getByLabelText("CSV content"), {
      target: { value: "email\nlearner@example.org" },
    });
    fireEvent.click(screen.getByText("Preview import"));
    await screen.findByText("Create 1 invitations");
    fireEvent.click(screen.getByText("Create 1 invitations"));
    await waitFor(() =>
      expect(api.importPeople).toHaveBeenLastCalledWith(
        3,
        "email\nlearner@example.org",
        true,
      ),
    );
    expect(saved).toHaveBeenCalled();
  });
  it("editing a previewed file disables commit", async () => {
    api.importPeople.mockResolvedValue({
      ready: 1,
      errors: 0,
      available_seats: 5,
      rows: [],
    });
    mount(<BulkInvites id={3} saved={vi.fn()} />);
    fireEvent.click(screen.getByText("Import people from CSV"));
    fireEvent.change(screen.getByLabelText("CSV content"), {
      target: { value: "email\na@example.org" },
    });
    fireEvent.click(screen.getByText("Preview import"));
    await screen.findByText("Create 1 invitations");
    fireEvent.change(screen.getByLabelText("CSV content"), {
      target: { value: "email\nb@example.org" },
    });
    expect(screen.getByText("Create 0 invitations")).toBeDisabled();
  });
  it("does not silently mark unrecorded students present", async () => {
    api.academics.mockResolvedValue({
      terms: [],
      students: [{ id: 4, name: "Aarav" }],
      attendance: [],
      assessments: [],
    });
    api.attendance.mockResolvedValue({});
    mount(<CampusAcademics data={data} />);
    await screen.findByText("Aarav");
    expect(screen.getByText("Save attendance")).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Attendance for Aarav"), {
      target: { value: "absent" },
    });
    fireEvent.click(screen.getByText("Save attendance"));
    await waitFor(() =>
      expect(api.attendance).toHaveBeenCalledWith(
        3,
        expect.objectContaining({
          batch_id: 2,
          entries: [{ member_id: 4, status: "absent" }],
        }),
      ),
    );
  });
  it("keeps student academics read-only", async () => {
    api.academics.mockResolvedValue({
      terms: [],
      students: [{ id: 4, name: "Aarav" }],
      attendance: [],
      assessments: [],
    });
    mount(
      <CampusAcademics
        data={{
          ...data,
          institution: { ...data.institution, role: "student" },
        }}
      />,
    );
    await screen.findByText("Aarav");
    expect(screen.queryByText("Save attendance")).not.toBeInTheDocument();
    expect(screen.queryByText("Add assessment")).not.toBeInTheDocument();
  });
  it("shows honest billing state when merchant plans are missing", async () => {
    api.billing.mockResolvedValue({
      plans: [],
      subscriptions: [],
      effective_plan: "starter",
    });
    mount(<CampusBilling id={3} owner />);
    await screen.findByText(
      /Online institutional checkout is not configured yet/,
    );
    expect(api.subscribe).not.toHaveBeenCalled();
  });
  it("students cannot upload institution resources", async () => {
    api.resources.mockResolvedValue([]);
    mount(
      <CampusResources
        data={{
          ...data,
          institution: { ...data.institution, role: "student" },
        }}
      />,
    );
    await screen.findByText("Your library is ready for its first resource.");
    expect(screen.queryByText("Upload resource")).not.toBeInTheDocument();
  });
});
