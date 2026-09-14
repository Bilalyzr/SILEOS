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
const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  put: vi.fn(),
  post: vi.fn(),
  resources: vi.fn(),
}));
vi.mock("@/api/axios", () => ({ api: mocks }));
vi.mock("@/api/campus", () => ({ campusApi: { resources: mocks.resources } }));
vi.mock("@/store/auth", () => ({
  useAuthStore: (fn: (s: unknown) => unknown) =>
    fn({ user: { id: 9, role: "student" } }),
}));
vi.mock("react-hot-toast", () => ({ default: { success: vi.fn() } }));
import { CampusLearning } from "../CampusLearning";
const student = {
  institution: { id: 4, role: "student" },
  batches: [],
} as unknown as InstitutionOverview;
const course = {
  id: 8,
  title: "Private physics",
  summary: "For your class",
  published: true,
  can_edit: false,
  lessons: 1,
  completed: 0,
};
function mount(data = student) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <CampusLearning data={data} />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.resetAllMocks();
  mocks.resources.mockResolvedValue([]);
  mocks.get.mockImplementation((url: string) =>
    Promise.resolve({
      data: url.endsWith("/8")
        ? {
            ...course,
            content: [
              {
                id: 12,
                title: "First lesson",
                body: "A private lesson",
                resource_id: null,
                completed: false,
              },
            ],
          }
        : [course],
    }),
  );
});
afterEach(cleanup);
describe("private campus learning", () => {
  it("lets a learner complete their lesson without showing editing controls", async () => {
    mocks.put.mockResolvedValue({ data: { completed: true } });
    mount();
    fireEvent.click(await screen.findByText("Start learning"));
    await screen.findByText("A private lesson");
    expect(screen.queryByText("Publish to campus")).not.toBeInTheDocument();
    expect(screen.queryByText("Add lesson")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Mark lesson complete"));
    await waitFor(() =>
      expect(mocks.put).toHaveBeenCalledWith(
        "/institutions/4/learning-courses/8/lessons/12/complete",
      ),
    );
  });
  it("shows a retryable failure without marking the lesson complete", async () => {
    mocks.put.mockRejectedValue({
      response: { data: { detail: "Your access has changed." } },
    });
    mount();
    fireEvent.click(await screen.findByText("Start learning"));
    fireEvent.click(await screen.findByText("Mark lesson complete"));
    await screen.findByText("Your access has changed.");
    expect(screen.queryByText("Completed")).not.toBeInTheDocument();
  });
  it("creates an institution draft with the chosen audience", async () => {
    mocks.post.mockResolvedValue({ data: { id: 8 } });
    mount({
      ...student,
      institution: { ...student.institution, role: "owner" },
    });
    fireEvent.click(screen.getByText("Create campus course"));
    fireEvent.change(screen.getByLabelText("Course title"), {
      target: { value: "A new campus course" },
    });
    fireEvent.change(screen.getByLabelText("Course introduction"), {
      target: { value: "Learning together" },
    });
    fireEvent.click(screen.getByText("Create private draft"));
    await waitFor(() =>
      expect(mocks.post).toHaveBeenCalledWith(
        "/institutions/4/learning-courses",
        {
          title: "A new campus course",
          summary: "Learning together",
          batch_id: null,
        },
      ),
    );
  });
});
