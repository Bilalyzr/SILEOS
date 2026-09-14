import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { InstitutionOverview } from "@/api/institutions";

const mocks = vi.hoisted(() => ({
  pilot: vi.fn(),
  events: vi.fn(),
  createEvent: vi.fn(),
  announcements: vi.fn(),
  notifications: vi.fn(),
  createAnnouncement: vi.fn(),
  readAnnouncement: vi.fn(),
  goals: vi.fn(),
  createGoal: vi.fn(),
  updateGoal: vi.fn(),
  reportCard: vi.fn(),
  gradingPolicy: vi.fn(),
  whatsappStatus: vi.fn(),
  whatsappContacts: vi.fn(),
  whatsappCampaigns: vi.fn(),
  createWhatsAppCampaign: vi.fn(),
  saveWhatsAppConsent: vi.fn(),
  removeWhatsAppConsent: vi.fn(),
}));

vi.mock("@/api/campus", () => ({ campusApi: mocks }));
vi.mock("@/store/auth", () => ({
  useAuthStore: (selector: (state: unknown) => unknown) =>
    selector({ user: { id: 30, role: "student" } }),
}));
vi.mock("react-hot-toast", () => ({
  default: { success: vi.fn() },
}));

import {
  CampusAnnouncements,
  CampusPilot,
  CampusWhatsApp,
} from "../CampusPilot";

const base = {
  institution: {
    id: 7,
    name: "Greenwood College",
    slug: "greenwood",
    kind: "college",
    academic_year: "2026–27",
    timezone: "Asia/Kolkata",
    description: "A learning community",
    plan: "Campus",
    role: "student",
  },
  members: [
    {
      id: 12,
      user_id: 30,
      name: "Diya Shah",
      email: "diya@example.org",
      role: "student",
      department: "Science",
      status: "active",
    },
  ],
  batches: [
    {
      id: 2,
      name: "Science A",
      department: "Science",
      academic_year: "2026–27",
      student_count: 1,
      member_ids: [12],
      assignments: [],
    },
  ],
  courses: [],
  invites: [],
  activity: [],
  usage: null,
  plan_requests: [],
  report: [],
} as InstitutionOverview;

function mount(node: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.pilot.mockResolvedValue({
    dismissed: false,
    progress: 25,
    total_steps: 8,
    completed_steps: 2,
    steps: [
      { key: "profile", label: "Campus profile", complete: true, href: "/institutions/7/settings" },
      { key: "timetable", label: "First timetable", complete: false, href: "/institutions/7/pilot" },
    ],
  });
  mocks.events.mockResolvedValue([]);
  mocks.announcements.mockResolvedValue([]);
  mocks.goals.mockResolvedValue([]);
  mocks.reportCard.mockResolvedValue({
    member_id: 12,
    student_name: "Diya Shah",
    term_id: 4,
    term_name: "Autumn 2026",
    status: "complete",
    attendance_percent: 94,
    overall_comment: "A strong term.",
    rows: [],
  });
  mocks.gradingPolicy.mockResolvedValue({
    bands: [
      { label: "A", min_percent: 80 },
      { label: "Pass", min_percent: 40 },
      { label: "Needs support", min_percent: 0 },
    ],
  });
  mocks.whatsappStatus.mockResolvedValue({
    configured: true,
    api_version: "v20.0",
    phone_number_configured: true,
    business_account_configured: true,
    business_phone_configured: true,
    webhook_ready: true,
    approved_templates: ["campus_update"],
    missing_fields: [],
    opted_in: false,
    contact_status: "not_started",
    phone: null,
    consent_at: null,
    join_url: null,
    join_expires_at: null,
  });
  mocks.whatsappContacts.mockResolvedValue([]);
  mocks.whatsappCampaigns.mockResolvedValue([]);
  mocks.notifications.mockResolvedValue([]);
});

afterEach(cleanup);

describe("campus pilot UI", () => {
  it("starts learners on goals and keeps manager-only setup out of their navigation", () => {
    mount(<CampusPilot data={base} />);

    expect(screen.queryByRole("button", { name: /setup/i })).not.toBeInTheDocument();
    expect(screen.getByText("Turn a big ambition into visible progress.")).toBeInTheDocument();
  });

  it("keeps the orange brand banner on every pilot module", async () => {
    mount(
      <CampusPilot
        data={{
          ...base,
          institution: { ...base.institution, role: "owner" },
        }}
      />,
    );
    expect(screen.getByText("A confident first week starts with a clear setup.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /calendar/i }));
    expect(screen.getByText("Everyone knows where to be—and what comes next.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /inbox/i }));
    expect(screen.getByText("The right update reaches the right people.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^goals$/i }));
    expect(screen.getByText("Give every learner a goal worth returning to.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /report cards/i }));
    expect(screen.getByText("Make progress clear, personal and worth celebrating.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /whatsapp/i }));
    expect(screen.getByText("Useful campus updates, sent with consent.")).toBeInTheDocument();
  });

  it("publishes a scoped in-app announcement without an invented audience field", async () => {
    mocks.createAnnouncement.mockResolvedValue({ id: 1 });
    const managerData = {
      ...base,
      institution: { ...base.institution, role: "owner" as const },
    };
    mount(<CampusAnnouncements data={managerData} />);

    fireEvent.click(screen.getByRole("button", { name: /new announcement/i }));
    fireEvent.change(screen.getByLabelText("Headline"), {
      target: { value: "Science fair opens Friday" },
    });
    fireEvent.change(screen.getByLabelText("Audience"), {
      target: { value: "2" },
    });
    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "Bring your projects to the main hall." },
    });
    fireEvent.click(screen.getByRole("button", { name: /publish announcement/i }));

    await waitFor(() =>
      expect(mocks.createAnnouncement).toHaveBeenCalledWith(7, {
        title: "Science fair opens Friday",
        body: "Bring your projects to the main hall.",
        batch_id: 2,
      }),
    );
  });

  it("sends personal WhatsApp permission to the account-wide preferences page", async () => {
    mount(<CampusWhatsApp data={base} />);

    const link = await screen.findByRole("link", {
      name: /manage my account preference/i,
    });
    expect(link).toHaveAttribute("href", "/communication-preferences");
    expect(screen.queryByLabelText("My WhatsApp number")).not.toBeInTheDocument();
    expect(mocks.saveWhatsAppConsent).not.toHaveBeenCalled();
  });

  it("keeps the manager consent directory read-only", async () => {
    mocks.whatsappContacts.mockResolvedValue([
      {
        member_id: 12,
        name: "Diya Shah",
        phone: null,
        status: "not_started",
        member_status: "active",
        consent_at: null,
      },
    ]);
    const managerData = {
      ...base,
      institution: { ...base.institution, role: "admin" as const },
    };
    mount(<CampusWhatsApp data={managerData} />);

    expect(await screen.findByText("Diya Shah")).toBeInTheDocument();
    expect(screen.getByText(/managers can review consent but cannot grant it/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /record consent/i })).not.toBeInTheDocument();
  });

  it("reuses the campus campaign request key after a failed response", async () => {
    mocks.createWhatsAppCampaign
      .mockRejectedValueOnce(new Error("Connection lost after submit"))
      .mockResolvedValueOnce({ id: 8 });
    const managerData = {
      ...base,
      institution: { ...base.institution, role: "admin" as const },
    };
    mount(<CampusWhatsApp data={managerData} />);

    const open = await screen.findByRole("button", { name: "New campaign" });
    await waitFor(() => expect(open).toBeEnabled());
    fireEvent.click(open);
    fireEvent.change(screen.getByLabelText("Approved template name"), {
      target: { value: "campus_update" },
    });

    const submit = screen.getByRole("button", { name: "Queue campaign once" });
    fireEvent.click(submit);
    await waitFor(() => expect(mocks.createWhatsAppCampaign).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(submit).toBeEnabled());

    fireEvent.click(submit);
    await waitFor(() => expect(mocks.createWhatsAppCampaign).toHaveBeenCalledTimes(2));

    const firstRequest = mocks.createWhatsAppCampaign.mock.calls[0][1];
    const retryRequest = mocks.createWhatsAppCampaign.mock.calls[1][1];
    expect(retryRequest.request_key).toBe(firstRequest.request_key);
  });
});
