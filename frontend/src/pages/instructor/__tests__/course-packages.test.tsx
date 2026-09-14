import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, it, expect, vi } from "vitest";
import CoursePackages from "../course-packages";
const mocks = vi.hoisted(() => ({
  courses: vi.fn(),
  previews: vi.fn(),
  inspect: vi.fn(),
  restore: vi.fn(),
  discard: vi.fn(),
  backup: vi.fn(),
}));
vi.mock("@/api/course-packages", () => ({ coursePackagesAPI: mocks }));
vi.mock("@/api/planner", () => ({ plannerError: (e: Error) => e.message }));
const preview = {
  id: "preview-1",
  kind: "backup",
  filename: "backup.zip",
  status: "preview",
  course_id: null,
  expires_at: "2026-09-07",
  warnings: ["External video links require the provider."],
  preview: {
    title: "Fractions",
    lessons: 2,
    quizzes: 1,
    assignments: 0,
    assessment_drafts: 0,
    dependencies: {},
    lesson_titles: ["Parts", "Equivalent fractions"],
  },
};
beforeEach(() => {
  vi.resetAllMocks();
  mocks.courses.mockResolvedValue([]);
  mocks.previews.mockResolvedValue([]);
  mocks.inspect.mockResolvedValue(preview);
  mocks.restore.mockResolvedValue({ course_id: 42, status: "draft" });
});
afterEach(cleanup);
it("detects a backup and requires preview before restoring a new draft", async () => {
  render(
    <MemoryRouter>
      <CoursePackages />
    </MemoryRouter>,
  );
  fireEvent.change(screen.getByLabelText("Course files"), {
    target: { files: [new File(["bytes"], "renamed.dat")] },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Detect and preview upload" }),
  );
  expect(
    await screen.findByRole("heading", { name: "Recognized course backup" }),
  ).toBeInTheDocument();
  expect(mocks.restore).not.toHaveBeenCalled();
  expect(
    screen.getByText("External video links require the provider."),
  ).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Restored course title"), {
    target: { value: "Reviewed course" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Restore as new draft course" }),
  );
  await waitFor(() =>
    expect(mocks.restore).toHaveBeenCalledWith("preview-1", "Reviewed course"),
  );
  expect(
    await screen.findByRole("link", { name: "Open restored course" }),
  ).toHaveAttribute("href", "/instructor/courses/42/edit");
  fireEvent.click(screen.getByRole("button", { name: "Fractions · backup" }));
  expect(
    screen.queryByRole("button", { name: "Restore as new draft course" }),
  ).not.toBeInTheDocument();
});
it("keeps a failed restore available for correction and retry", async () => {
  mocks.previews.mockResolvedValue([preview]);
  mocks.restore.mockRejectedValue(new Error("Asset checksum failed"));
  render(
    <MemoryRouter>
      <CoursePackages />
    </MemoryRouter>,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Fractions · backup" }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Restore as new draft course" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Asset checksum failed",
  );
  expect(
    screen.getByRole("button", { name: "Restore as new draft course" }),
  ).toBeEnabled();
});
