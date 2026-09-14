import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  status: vi.fn(),
  optIn: vi.fn(),
  optOut: vi.fn(),
  adminOverview: vi.fn(),
  adminContacts: vi.fn(),
  adminCampaigns: vi.fn(),
  createAdminCampaign: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock("@/api/whatsapp", () => ({ whatsappApi: mocks }));
vi.mock("@/store/auth", () => ({
  useAuthStore: (selector: (state: unknown) => unknown) =>
    selector({ user: { id: 9, role: "student" } }),
}));
vi.mock("react-hot-toast", () => ({
  default: { success: mocks.toastSuccess },
}));

import { CommunicationPreferencesPage } from "../communication-preferences";
import { AdminCommunicationsPage } from "../admin/communications";

const baseStatus = {
  configured: true,
  api_version: "v23.0",
  phone_number_configured: true,
  business_account_configured: true,
  business_phone_configured: true,
  webhook_ready: true,
  approved_templates: ["learning_update"],
  missing_fields: [],
  opted_in: false,
  contact_status: "not_started",
  phone: null,
  consent_at: null,
  join_url: null,
  join_expires_at: null,
};

function mount(node: React.ReactNode = <CommunicationPreferencesPage />) {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        {node}
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.status.mockResolvedValue(baseStatus);
  mocks.adminOverview.mockResolvedValue({
    ...baseStatus,
    display_phone_number: "+1 555 000 1111",
    consent_counts: {
      not_started: 40,
      pending: 3,
      confirmed: 18,
      revoked: 2,
      total_users: 63,
    },
    eligible_by_role: { student: 12, instructor: 4, admin: 2 },
  });
  mocks.adminContacts.mockResolvedValue({
    items: [
      {
        user_id: 21,
        name: "Diya Shah",
        email: "diya@example.org",
        role: "student",
        is_active: true,
        phone: "+********3210",
        status: "confirmed",
        consent_at: "2026-09-10T10:00:00Z",
      },
    ],
    total: 1,
    offset: 0,
    limit: 100,
  });
  mocks.adminCampaigns.mockResolvedValue([]);
});

describe("platform Communications Center", () => {
  it("shows provider health and an account-wide consent directory", async () => {
    mount(<AdminCommunicationsPage />);

    expect(
      screen.getByRole("heading", { name: "Reach the right people, with permission." }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Official WhatsApp Cloud API")).toBeInTheDocument();
    expect(screen.getByText("63 accounts")).toBeInTheDocument();
    expect(await screen.findByText("Diya Shah")).toBeInTheDocument();
    expect(
      screen.getByText(/Administrators cannot opt in for another person/i),
    ).toBeInTheDocument();
  });

  it("keeps campaign actions disabled while provider setup is incomplete", async () => {
    mocks.adminOverview.mockResolvedValue({
      ...baseStatus,
      configured: false,
      webhook_ready: false,
      approved_templates: [],
      missing_fields: ["WHATSAPP_ACCESS_TOKEN"],
      consent_counts: {
        not_started: 1,
        pending: 0,
        confirmed: 0,
        revoked: 0,
        total_users: 1,
      },
      eligible_by_role: {},
    });
    mount(<AdminCommunicationsPage />);

    expect(await screen.findByText("Campaign sending is paused.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "New WhatsApp campaign" }),
    ).toBeDisabled();
  });

  it("queues one approved template for explicit consented roles", async () => {
    mocks.createAdminCampaign.mockResolvedValue({ id: 5 });
    mount(<AdminCommunicationsPage />);

    const campaignButton = await screen.findByRole("button", {
      name: "New WhatsApp campaign",
    });
    await waitFor(() => expect(campaignButton).toBeEnabled());
    fireEvent.click(campaignButton);
    fireEvent.change(screen.getByLabelText("Approved template"), {
      target: { value: "learning_update" },
    });
    fireEvent.click(screen.getByLabelText(/Students \(12 eligible\)/i));
    fireEvent.click(screen.getByLabelText(/Instructors \(4 eligible\)/i));
    fireEvent.change(screen.getByLabelText(/Template parameters/i), {
      target: { value: "New learning is ready\nOpen SashaInfinity" },
    });
    fireEvent.change(screen.getByLabelText(/Approved header banner URL/i), {
      target: { value: "https://cdn.example.org/sasha-update.png" },
    });
    expect(screen.getByAltText("WhatsApp header banner preview")).toHaveAttribute(
      "src",
      "https://cdn.example.org/sasha-update.png",
    );
    fireEvent.click(screen.getByRole("button", { name: "Queue campaign once" }));

    await waitFor(() =>
      expect(mocks.createAdminCampaign).toHaveBeenCalledWith(
        expect.objectContaining({
          template: "learning_update",
          language: "en",
          parameters: ["New learning is ready", "Open SashaInfinity"],
          roles: ["student", "instructor"],
          header_image_url: "https://cdn.example.org/sasha-update.png",
        }),
      ),
    );
  });

  it("reuses the draft request key when a lost response is retried", async () => {
    mocks.createAdminCampaign
      .mockRejectedValueOnce(new Error("Connection lost after submit"))
      .mockResolvedValueOnce({ id: 5 });
    mount(<AdminCommunicationsPage />);

    const campaignButton = await screen.findByRole("button", {
      name: "New WhatsApp campaign",
    });
    await waitFor(() => expect(campaignButton).toBeEnabled());
    fireEvent.click(campaignButton);
    fireEvent.change(screen.getByLabelText("Approved template"), {
      target: { value: "learning_update" },
    });
    fireEvent.click(screen.getByLabelText(/Students \(12 eligible\)/i));

    const submit = screen.getByRole("button", { name: "Queue campaign once" });
    fireEvent.click(submit);
    await waitFor(() => expect(mocks.createAdminCampaign).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(submit).toBeEnabled());

    fireEvent.click(submit);
    await waitFor(() => expect(mocks.createAdminCampaign).toHaveBeenCalledTimes(2));

    const firstRequest = mocks.createAdminCampaign.mock.calls[0][0];
    const retryRequest = mocks.createAdminCampaign.mock.calls[1][0];
    expect(retryRequest.request_key).toBe(firstRequest.request_key);
  });
});

afterEach(cleanup);

describe("account-wide communication preferences", () => {
  it("explains that one WhatsApp preference applies across SashaInfinity", async () => {
    mount();

    expect(
      screen.getByRole("heading", { name: "Choose how SashaInfinity reaches you." }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(/one preference follows your account across courses/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/only you can give or withdraw permission/i)).toBeInTheDocument();
  });

  it("records the member's own number and exposes the JOIN confirmation link", async () => {
    mocks.optIn.mockResolvedValue({
      status: "pending",
      click_to_chat_url: "https://wa.me/15550001111?text=JOIN%20ABC123",
      expires_at: "2026-09-10T12:30:00Z",
      consent_at: null,
    });
    mount();

    fireEvent.change(await screen.findByLabelText("My WhatsApp number"), {
      target: { value: "+919876543210" },
    });
    fireEvent.click(
      screen.getByLabelText(/I agree to receive useful SashaInfinity updates/i),
    );
    fireEvent.click(screen.getByRole("button", { name: /continue with WhatsApp/i }));

    await waitFor(() =>
      expect(mocks.optIn).toHaveBeenCalledWith("+919876543210"),
    );
    expect(
      await screen.findByRole("link", { name: /open WhatsApp to confirm/i }),
    ).toHaveAttribute(
      "href",
      "https://wa.me/15550001111?text=JOIN%20ABC123",
    );
  });

  it("keeps opt-in unavailable until the official provider connection is ready", async () => {
    mocks.status.mockResolvedValue({
      ...baseStatus,
      configured: false,
      business_phone_configured: false,
      webhook_ready: false,
      missing_fields: ["WHATSAPP_ACCESS_TOKEN"],
    });
    mount();

    expect(
      await screen.findByText(/WhatsApp updates are being connected/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /continue with WhatsApp/i }),
    ).toBeDisabled();
    expect(screen.queryByText(/WHATSAPP_ACCESS_TOKEN/)).not.toBeInTheDocument();
  });

  it("lets a confirmed member withdraw their permission", async () => {
    mocks.status.mockResolvedValue({
      ...baseStatus,
      opted_in: true,
      contact_status: "confirmed",
      phone: "+919876543210",
      consent_at: "2026-09-10T10:00:00Z",
    });
    mocks.optOut.mockResolvedValue({ status: "revoked" });
    mount();

    fireEvent.click(
      await screen.findByRole("button", { name: /turn off WhatsApp updates/i }),
    );

    await waitFor(() => expect(mocks.optOut).toHaveBeenCalledTimes(1));
  });
});
