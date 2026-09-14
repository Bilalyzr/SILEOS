import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { InstitutionOverview } from "@/api/institutions";

const api = vi.hoisted(() => ({
  list: vi.fn(),
  invitations: vi.fn(),
  overview: vi.fn(),
  create: vi.fn(),
  invite: vi.fn(),
  batch: vi.fn(),
  available: vi.fn(),
  connect: vi.fn(),
  assign: vi.fn(),
  addStudents: vi.fn(),
  requestPlan: vi.fn(),
  update: vi.fn(),
  updateMember: vi.fn(),
  revoke: vi.fn(),
  export: vi.fn(),
}));
vi.mock("@/api/institutions", () => ({ institutionApi: api }));
vi.mock("@/store/auth", () => ({
  useAuthStore: (selector: (s: unknown) => unknown) =>
    selector({ user: { id: 1, role: "instructor" } }),
}));
vi.mock("@/components/dashboard/DashboardWorkspace", () => ({
  DashboardWorkspace: ({ children }: { children: React.ReactNode }) => (
    <main>{children}</main>
  ),
}));
vi.mock("react-hot-toast", () => ({ default: { success: vi.fn() } }));
vi.mock("@/api/campus", () => ({campusApi: {branding: async () => ({title:"Your campus", subtitle:"Learning together",has_image:false}), billing: async () => ({plans:[],subscriptions:[],effective_plan:"starter"})}}));
import InstitutionsPage from "../institutions";

const fixture: InstitutionOverview = {
  institution: {
    id: 1,
    name: "Greenwood College",
    slug: "greenwood",
    kind: "college",
    academic_year: "2026–2027",
    timezone: "Asia/Kolkata",
    description: "",
    plan: "starter",
    role: "owner",
  },
  members: [
    {
      id: 1,
      user_id: 1,
      name: "Owner",
      email: "owner@example.org",
      role: "owner",
      department: "",
      status: "active",
    },
  ],
  courses: [],
  batches: [],
  invites: [],
  activity: [],
  plan_requests: [],
  report: [],
  usage: {
    members: 1,
    reserved_seats: 0,
    batches: 0,
    courses: 0,
    limits: { members: 100, batches: 10, courses: 20 },
  },
};
function mount(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/institutions" element={<InstitutionsPage />} />
          <Route
            path="/institutions/:institutionId/*"
            element={<InstitutionsPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.resetAllMocks();
  api.list.mockResolvedValue([fixture.institution]);
  api.invitations.mockResolvedValue([]);
  api.overview.mockResolvedValue(fixture);
  api.available.mockResolvedValue([]);
});
afterEach(cleanup);

describe("Institution workspace", () => {
  it("creates a school through a validated dialog and opens the persisted workspace", async () => {
    api.create.mockResolvedValue(fixture.institution);
    mount("/institutions");
    fireEvent.click(
      await screen.findByRole("button", { name: "Create institution" }),
    );
    fireEvent.change(screen.getByLabelText("Institution name"), {
      target: { value: "Greenwood College" },
    });
    fireEvent.change(screen.getByLabelText("Institution type"), {
      target: { value: "college" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create institution" }));
    await waitFor(() =>
      expect(api.create).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Greenwood College",
          kind: "college",
          timezone: "Asia/Kolkata",
        }),
      ),
    );
    expect(
      await screen.findByRole("heading", { name: "Greenwood College" }),
    ).toBeInTheDocument();
  });
  it("shows account-inbox delivery before creating an invitation", async () => {
    api.invite.mockResolvedValue({});
    mount("/institutions/1/people");
    fireEvent.click(
      await screen.findByRole("button", { name: "Invite people" }),
    );
    expect(
      screen.getByText(/No email is sent automatically/),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Email address"), {
      target: { value: "student@example.org" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create invitation" }));
    await waitFor(() =>
      expect(api.invite).toHaveBeenCalledWith(1, {
        email: "student@example.org",
        role: "student",
        department: "",
      }),
    );
  });
  it("keeps failed forms open with an actionable server error", async () => {
    api.batch.mockRejectedValue({
      response: { data: { detail: "This batch already exists." } },
    });
    mount("/institutions/1/batches");
    fireEvent.click(
      await screen.findByRole("button", { name: "Create batch" }),
    );
    fireEvent.change(screen.getByLabelText("Batch or class name"), {
      target: { value: "Grade 11" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create batch" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This batch already exists.",
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
  it("hides administrative sections and actions from students", async () => {
    api.overview.mockResolvedValue({
      ...fixture,
      institution: { ...fixture.institution, role: "student" },
      usage: null,
    });
    mount("/institutions/1");
    await screen.findByRole("heading", { name: "Greenwood College" });
    expect(
      screen.queryByRole("button", { name: "Invite people" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "People" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Plan & usage" }),
    ).not.toBeInTheDocument();
  });
  it("does not offer a paid checkout or silently activate a requested plan", async () => {
    api.requestPlan.mockResolvedValue({});
    mount("/institutions/1/plan");
    fireEvent.click(
      await screen.findByRole("button", { name: "Request Campus" }),
    );
    expect(
      screen.getByText(/does not charge you or change your current limits/),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save request" }));
    await waitFor(() =>
      expect(api.requestPlan).toHaveBeenCalledWith(1, "campus", ""),
    );
  });
  it("disables course connection when no editable courses exist", async () => {
    mount("/institutions/1/courses");
    fireEvent.click(
      await screen.findByRole("button", { name: "Connect your first course" }),
    );
    await screen.findByText(/No new editable courses are available/);
    expect(
      screen.getByRole("button", { name: "Connect course" }),
    ).toBeDisabled();
  });
  it("offers retry when the institution cannot be loaded", async () => {
    api.overview.mockRejectedValue(new Error("offline"));
    mount("/institutions/1");
    await screen.findByText("We couldn’t open this institution");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
