import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { InstitutionOverview } from "@/api/institutions";

const exams = vi.hoisted(() => ({
  list: vi.fn(),
  create: vi.fn(),
  publish: vi.fn(),
  unpublish: vi.fn(),
  createPaper: vi.fn(),
  deletePaper: vi.fn(),
  roster: vi.fn(),
  putMarks: vi.fn(),
  hallTickets: vi.fn(),
  hallTicketPdf: vi.fn(),
  myHallTicketPdf: vi.fn(),
  results: vi.fn(),
  myResults: vi.fn(),
  marksheetPdf: vi.fn(),
}));
const campus = vi.hoisted(() => ({ academics: vi.fn() }));
const auth = vi.hoisted(() => ({ user: { id: 7, role: "instructor" } as { id: number; role: string } }));

vi.mock("@/api/campus-exams", () => ({ examsApi: exams, openBlob: vi.fn() }));
vi.mock("@/api/campus", () => ({ campusApi: campus }));
vi.mock("@/store/auth", () => ({
  useAuthStore: (fn: (s: unknown) => unknown) => fn({ user: auth.user }),
}));
vi.mock("react-hot-toast", () => ({ default: { success: vi.fn(), error: vi.fn() } }));

import { CampusExams } from "../CampusExams";

const paper = {
  id: 11,
  exam_id: 5,
  batch_id: 2,
  batch_name: "Class A",
  subject: "Physics",
  max_marks: 100,
  pass_marks: 35,
  starts_at: "2026-10-05T09:00:00+00:00",
  ends_at: "2026-10-05T11:00:00+00:00",
  duration_minutes: 120,
  room: "Hall A",
  event_id: 9,
  marks_entered: 0,
  students: 2,
};
const exam = {
  id: 5,
  term_id: 1,
  term_name: "Term 1",
  name: "Mid-term",
  kind: "midterm",
  status: "scheduled",
  published_at: null,
  papers: [paper],
};

function mount(role: string) {
  const data = {
    institution: { id: 3, role },
    batches: [{ id: 2, name: "Class A" }],
  } as InstitutionOverview;
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <CampusExams data={data} studentUserId={7} />
    </QueryClientProvider>,
  );
}

afterEach(cleanup);
beforeEach(() => {
  vi.resetAllMocks();
  auth.user = { id: 7, role: "instructor" };
  campus.academics.mockResolvedValue({ terms: [{ id: 1, name: "Term 1", starts_on: "2026-06-01", ends_on: "2026-12-20" }], students: [], attendance: [], assessments: [] });
  exams.list.mockResolvedValue([exam]);
  exams.roster.mockResolvedValue([
    { member_id: 21, name: "Asha", roll_number: "02-0021", marks: null, absent: false, remarks: "" },
    { member_id: 22, name: "Ravi", roll_number: "02-0022", marks: null, absent: false, remarks: "" },
  ]);
  exams.putMarks.mockResolvedValue([]);
  exams.create.mockResolvedValue({ ...exam, id: 6, name: "Finals", status: "draft", papers: [] });
  exams.publish.mockResolvedValue({ ...exam, status: "published" });
});

describe("campus exams", () => {
  it("lets staff create an exam in the selected term", async () => {
    mount("teacher");
    await screen.findByRole("heading", { name: "Mid-term" });
    fireEvent.click(screen.getByRole("button", { name: "New exam" }));
    fireEvent.change(await screen.findByPlaceholderText("Mid-term 2026"), { target: { value: "Finals" } });
    fireEvent.click(screen.getByRole("button", { name: "Create exam" }));
    await waitFor(() => expect(exams.create).toHaveBeenCalledWith(3, { term_id: 1, name: "Finals", kind: "other" }));
  });

  it("saves marks with absent handling and publishes as manager", async () => {
    mount("owner");
    await screen.findByRole("heading", { name: "Mid-term" });
    fireEvent.click(screen.getByRole("tab", { name: "Marks" }));
    fireEvent.change(await screen.findByLabelText("Marks for Asha"), { target: { value: "88" } });
    fireEvent.click(screen.getByLabelText("Absent Ravi"));
    fireEvent.click(screen.getByRole("button", { name: "Save marks" }));
    await waitFor(() =>
      expect(exams.putMarks).toHaveBeenCalledWith(3, 5, 11, [
        { member_id: 21, marks: 88, absent: false, remarks: "" },
        { member_id: 22, marks: null, absent: true, remarks: "" },
      ]),
    );
    fireEvent.click(screen.getByRole("button", { name: "Publish results" }));
    await waitFor(() => expect(exams.publish).toHaveBeenCalledWith(3, 5));
  });

  it("hides publishing from teachers", async () => {
    mount("teacher");
    await screen.findByRole("heading", { name: "Mid-term" });
    expect(screen.queryByRole("button", { name: "Publish results" })).toBeNull();
  });

  it("shows a learner the timetable, and results only when published", async () => {
    auth.user = { id: 7, role: "student" };
    mount("student");
    await screen.findByText("Physics");
    expect(exams.myResults).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Download hall ticket" })).toBeTruthy();
    cleanup();
    exams.list.mockResolvedValue([{ ...exam, status: "published" }]);
    exams.myResults.mockResolvedValue({
      exam: { id: 5, name: "Mid-term", status: "published" },
      batch_id: 2,
      batch_name: "Class A",
      papers: [{ id: 11, subject: "Physics", max_marks: 100, pass_marks: 35 }],
      students: 2,
      member_id: 21,
      name: "Asha",
      roll_number: "02-0021",
      marks: { 11: { marks: 88, absent: false, remarks: "Good" } },
      total: 88,
      max_total: 100,
      percent: 88,
      passed: true,
      rank: 1,
    });
    mount("student");
    await screen.findByText(/Rank 1 of 2/);
    expect(exams.myResults).toHaveBeenCalledWith(3, 5, undefined);
    expect(screen.getByRole("button", { name: "Download mark sheet" })).toBeTruthy();
  });
});
