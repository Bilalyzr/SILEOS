import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StudentLiveClasses, StudentLiveProvider } from "../StudentLiveClasses";
const fixtures = vi.hoisted(() => ({
  role: "student",
  authenticated: true,
  fetch: vi.fn(),
}));
vi.mock("@/store/auth", () => ({
  useAuthStore: (select: (s: unknown) => unknown) =>
    select({
      user: { id: 1, role: fixtures.role },
      isAuthenticated: fixtures.authenticated,
    }),
}));
vi.mock("@/api/liveClasses", () => ({ fetchLiveNow: fixtures.fetch }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  fixtures.role = "student";
  fixtures.authenticated = true;
});
function mount(children: React.ReactNode) {
  const query = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  render(
    <QueryClientProvider client={query}>
      <MemoryRouter>
        <StudentLiveProvider>{children}</StudentLiveProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return query;
}
it("shares a single request and matches live notices to the enrolled course", async () => {
  fixtures.fetch.mockResolvedValue({
    classes: [
      { id: 7, course_id: 12, title: "Physics today", status: "live" },
      { id: 8, course_id: 13, title: "Ended session", status: "ended" },
    ],
  });
  mount(
    <>
      <StudentLiveClasses courseId={12} />
      <StudentLiveClasses courseId={99} />
    </>,
  );
  expect(
    await screen.findByRole("link", { name: "Join live class: Physics today" }),
  ).toHaveAttribute("href", "/student/live-classes/7/join");
  expect(screen.queryByText("Ended session")).not.toBeInTheDocument();
  expect(screen.getAllByText("Live now")).toHaveLength(1);
  expect(fixtures.fetch).toHaveBeenCalledTimes(1);
});
it.each(["instructor", "admin", "visitor"])(
  "does not show student live options to %s",
  async (role) => {
    fixtures.role = role;
    fixtures.authenticated = role !== "visitor";
    mount(<StudentLiveClasses />);
    expect(screen.queryByText("Live now")).not.toBeInTheDocument();
    expect(fixtures.fetch).not.toHaveBeenCalled();
  },
);
it("removes the live notice after the next response reports no running class", async () => {
  fixtures.fetch
    .mockResolvedValueOnce({
      classes: [
        { id: 7, course_id: 12, title: "Physics today", status: "live" },
      ],
    })
    .mockResolvedValue({ classes: [] });
  const query = mount(<StudentLiveClasses courseId={12} />);
  await screen.findByText("Physics today");
  await query.invalidateQueries({ queryKey: ["student-live-classes"] });
  await waitFor(() =>
    expect(screen.queryByText("Live now")).not.toBeInTheDocument(),
  );
});
