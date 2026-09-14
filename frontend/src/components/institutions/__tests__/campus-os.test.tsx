import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { InstitutionOverview } from "@/api/institutions";
import { CampusActionCenter } from "../CampusActionCenter";
import { CampusAdmissions } from "../CampusAdmissions";
import { CampusFinance } from "../CampusFinance";

vi.mock("react-hot-toast", () => ({
  default: { success: vi.fn(), error: vi.fn() },
}));

const baseData = {
  institution: {
    id: 1,
    name: "Astra Valley College",
    slug: "astra-valley",
    kind: "college",
    academic_year: "2026–27",
    timezone: "Asia/Kolkata",
    description: "",
    plan: "growth",
    role: "owner",
  },
  members: [
    { id: 21, user_id: 91, name: "Arjun Rao", email: "arjun@example.edu", role: "student", department: "Science", status: "active" },
  ],
  batches: [],
  courses: [],
  invites: [],
  activity: [],
  usage: null,
  plan_requests: [],
  report: [],
} as InstitutionOverview;

function mount(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>,
  );
}

afterEach(cleanup);

describe("Campus OS workspaces", () => {
  it("adapts Today to the viewer and lets them complete an action", async () => {
    mount(<CampusActionCenter data={baseData} role="teacher" demo />);

    expect(await screen.findByText("Needs grading")).toBeInTheDocument();
    const complete = screen.getByRole("button", {
      name: "Mark Record attendance for Class 10 A complete",
    });
    fireEvent.click(complete);

    await waitFor(() =>
      expect(
        screen.queryByText("Record attendance for Class 10 A"),
      ).not.toBeInTheDocument(),
    );
  });

  it("keeps applicant personal information private for teachers", () => {
    mount(<CampusAdmissions data={baseData} role="teacher" demo />);

    expect(screen.getByText("Private admissions workspace")).toBeInTheDocument();
    expect(screen.queryByText("Ananya Iyer")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add application" })).not.toBeInTheDocument();
  });

  it("filters admissions and supports a version-aware stage update", async () => {
    mount(<CampusAdmissions data={baseData} demo />);

    expect(await screen.findByText("Ananya Iyer")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox", { name: "Search applications" }), {
      target: { value: "Meera" },
    });
    await waitFor(() => expect(screen.queryByText("Ananya Iyer")).not.toBeInTheDocument());
    expect(screen.getByText("Meera Nair")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Stage for Meera Nair"), {
      target: { value: "admitted" },
    });
    await waitFor(() =>
      expect(screen.getByLabelText("Stage for Meera Nair")).toHaveValue("admitted"),
    );
  });

  it("shows major-unit INR balances and opens the exact student payment flow", async () => {
    mount(<CampusFinance data={baseData} demo />);

    expect(await screen.findByText("₹78,50,000")).toBeInTheDocument();
    expect(screen.getByText("Arjun Rao")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Record payment" })[0]);
    expect(screen.getByRole("dialog", { name: "Record payment · Arjun Rao" })).toBeInTheDocument();
    expect(screen.getByText(/Outstanding balance:/)).toBeInTheDocument();
  });

  it("gives learners a private installment and receipt view", async () => {
    mount(
      <CampusFinance
        data={{
          ...baseData,
          institution: { ...baseData.institution, role: "student" },
        }}
        demo
      />,
    );

    expect(screen.getByText("Fees and receipts, clear for every term.")).toBeInTheDocument();
    expect(await screen.findByText("REC-2026-0048")).toBeInTheDocument();
    expect(screen.queryByText("Merit scholarship")).not.toBeInTheDocument();
  });
});
