import {
  act,
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, it, expect, vi } from "vitest";
import OperationsCenter from "../operations";
const mocks = vi.hoisted(() => ({
  summary: vi.fn(),
  rows: vi.fn(),
  csv: vi.fn(),
  revenue: vi.fn(),
  portfolio: vi.fn(),
  download: vi.fn(),
}));
vi.mock("@/api/operations", () => ({
  operationsAPI: mocks,
  downloadBlob: mocks.download,
}));
vi.mock("@/api/planner", () => ({ plannerError: (e: Error) => e.message }));
beforeEach(() => {
  vi.resetAllMocks();
  mocks.summary.mockResolvedValue({
    queues: [],
    outcomes: {
      courses: [],
      struggling_concepts: [],
      paired_interventions: 0,
      mean_delayed_change: null,
    },
  });
  mocks.rows.mockResolvedValue({
    items: [{ id: 1, name: "Course", status: "draft", href: "/course" }],
    total: 26,
    page: 1,
    page_size: 25,
  });
  mocks.csv.mockResolvedValue(new Blob(["csv"]));
  mocks.portfolio.mockResolvedValue({
    from: "2026-08-12",
    to: "2026-09-12",
    as_of: "2026-09-12T00:00:00Z",
    verticals: [
      {
        key: "meiporul",
        code: "MA1",
        label: "Meiporul",
        tamil: "மெய்ப்பொருள்",
        subdomain: "meiporul",
        mission: "Immersive learning",
        business_model: "Experiences",
        inventory: [{ key: "courses", label: "Courses", value: 3 }],
        revenue: {
          currencies: [{ currency: "INR", captured: 100, refunded: 0, net_cash: 100 }],
          streams: [{ key: "immersive_courses", label: "Immersive course sales", currencies: [{ currency: "INR", captured: 100, refunded: 0, net_cash: 100 }] }],
        },
      },
    ],
    unallocated: {
      payment_count: 1,
      course_count: 0,
      currencies: [{ currency: "INR", captured: 20, refunded: 0, net_cash: 20 }],
    },
    resilience: [{ currency: "INR", leader: "meiporul", largest_share_percent: 100, remaining_if_leader_pauses: 0, status: "concentrated" }],
    reporting_contract: { operating_sources: ["commerce payments"], rule: "Sources stay authoritative." },
  });
});
afterEach(cleanup);
it("uses the same search and status filters for pages and CSV", async () => {
  render(
    <MemoryRouter initialEntries={["/?view=tables"]}>
      <OperationsCenter />
    </MemoryRouter>,
  );
  await screen.findByText("Course");
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() =>
    expect(mocks.rows).toHaveBeenLastCalledWith(
      "courses",
      expect.objectContaining({ page: 2 }),
    ),
  );
  fireEvent.change(screen.getByLabelText("Search records"), {
    target: { value: "fractions" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Search" }));
  fireEvent.change(screen.getByLabelText("Status filter"), {
    target: { value: "draft" },
  });
  await waitFor(() =>
    expect(mocks.rows).toHaveBeenLastCalledWith(
      "courses",
      expect.objectContaining({ q: "fractions", status: "draft", page: 1 }),
    ),
  );
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Export filtered CSV" }),
    ).toBeEnabled(),
  );
  fireEvent.click(screen.getByRole("button", { name: "Export filtered CSV" }));
  await waitFor(() =>
    expect(mocks.csv).toHaveBeenCalledWith(
      "courses",
      expect.objectContaining({ q: "fractions", status: "draft" }),
    ),
  );
});
it("shows unknown learning evidence instead of an invented gain", async () => {
  render(
    <MemoryRouter initialEntries={["/?view=outcomes"]}>
      <OperationsCenter />
    </MemoryRouter>,
  );
  expect(await screen.findByText("Not enough evidence")).toBeInTheDocument();
});

it("uses the consolidated business portfolio as the default control view", async () => {
  render(
    <MemoryRouter>
      <OperationsCenter />
    </MemoryRouter>,
  );
  expect(await screen.findByText("Pillar revenue concentration")).toBeInTheDocument();
  expect(screen.getByText(/1 payment need a pillar classification/)).toBeInTheDocument();
  expect(mocks.portfolio).toHaveBeenCalled();
});

it('keeps the latest date-window report when an older request finishes later', async () => {
  const report = (note: string) => ({currencies: [], estimated_active_mrr_inr: 0, failed_payments: 0, refunds_needing_attention: 0, refunds_missing_timestamp: 0, note});
  let finishOld!: (data: ReturnType<typeof report>) => void;
  mocks.revenue.mockReturnValueOnce(new Promise(resolve => { finishOld = resolve })).mockResolvedValue(report('Latest window'));
  render(<MemoryRouter initialEntries={['/?view=revenue']}><OperationsCenter/></MemoryRouter>);
  await waitFor(() => expect(mocks.revenue).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByLabelText('From'), {target: {value: '2026-01-01'}});
  expect(await screen.findByText('Latest window')).toBeInTheDocument();
  await act(async () => {finishOld(report('Obsolete window'))});
  expect(screen.queryByText('Obsolete window')).not.toBeInTheDocument();
  expect(screen.getByText('Latest window')).toBeInTheDocument();
});
