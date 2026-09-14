import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import MyInternshipsPage from "../my-internships";

const mocks = vi.hoisted(() => ({ myVouchers: vi.fn() }));
vi.mock("@/api/internship", () => ({ internshipApi: mocks }));
vi.mock("@/components/dashboard/MyInternshipCharts", () => ({
  MyInternshipCharts: ({ list }: { list: Array<{ progress: number }> }) => (
    <div data-testid="progress-chart">{list[0]?.progress ?? 0}</div>
  ),
}));

beforeEach(() => {
  vi.resetAllMocks();
  mocks.myVouchers.mockResolvedValue([
    {
      id: 4,
      code: "REAL-4",
      status: "redeemed",
      internship_id: 2,
      internship_title: "Applied AI Internship",
      internship_slug: "applied-ai",
      spoc_name: "Dr. Meena",
      redeemed_course_id: 18,
      redeemed_course_title: "AI Practicum",
      company_name: null,
      attendance_count: 8,
      engagement_status: "active",
      certificate_issued: false,
      issued_certificate_id: null,
      created_at: "2026-08-01T00:00:00Z",
      redeemed_at: "2026-08-03T00:00:00Z",
      course_progress: {
        progress_percentage: 73,
        enrollment_status: "enrolled",
        is_completed: false,
        completion_date: null,
      },
    },
  ]);
});
afterEach(cleanup);

it("renders actual enrollment progress instead of an invented midpoint", async () => {
  render(
    <MemoryRouter>
      <MyInternshipsPage />
    </MemoryRouter>,
  );
  expect(await screen.findByText("Applied AI Internship")).toBeInTheDocument();
  expect(screen.getAllByText("73%").length).toBeGreaterThan(0);
  expect(screen.getByTestId("progress-chart")).toHaveTextContent("73");
  expect(screen.queryByText("50%")).not.toBeInTheDocument();
  expect(screen.getByText(/Dr\. Meena/)).toBeInTheDocument();
});
