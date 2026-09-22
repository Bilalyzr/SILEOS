import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { BrowserRouter, Link, useLocation } from "react-router-dom";
import { PageGuide } from "./PageGuide";
import { PageBackButton } from './PageBackButton';
import { pageGuide, safeBackFallback, needsPageBack } from "./page-guides";
vi.mock("@/store/auth", () => ({
  useAuthStore: (select: (s: { user: { role: string } }) => unknown) =>
    select({ user: { role: "instructor" } }),
}));
afterEach(() => {
  cleanup();
  window.history.replaceState(null, "", "/");
});
function Location() {
  const l = useLocation();
  return (
    <output data-testid="location">{l.pathname + l.search + l.hash}</output>
  );
}
it("returns to the preceding route including filters and hash", async () => {
  window.history.replaceState(
    { idx: 0 },
    "",
    "/labs?subject=physics#experiments",
  );
  render(
    <BrowserRouter>
      <PageGuide />
      <Link to="/instructor/lab-studio?chapter=physics">Create lab</Link>
      <Location />
    </BrowserRouter>,
  );
  fireEvent.click(screen.getByText("Create lab"));
  expect(screen.getByTestId("location")).toHaveTextContent(
    "/instructor/lab-studio",
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Go back to previous page" }),
  );
  await waitFor(() =>
    expect(screen.getByTestId("location")).toHaveTextContent(
      "/labs?subject=physics#experiments",
    ),
  );
});
it("gives direct entries a usable parent destination", () => {
  window.history.replaceState({ idx: 0 }, "", "/courses/12");
  render(
    <BrowserRouter>
      <PageGuide />
      <Location />
    </BrowserRouter>,
  );
  expect(
    screen.getByRole("button", { name: "Go back to previous page" }),
  ).toBeVisible();
  fireEvent.click(
    screen.getByRole("button", { name: "Go back to previous page" }),
  );
  expect(screen.getByTestId("location")).toHaveTextContent("/courses");
});
it("keeps direct-entry fallbacks within the user role and covers unknown pages", () => {
  expect(safeBackFallback("/instructor/lab-studio", "student")).not.toContain(
    "/instructor",
  );
  expect(safeBackFallback("/", "student")).not.toBe("/");
  expect(pageGuide("/new-feature").steps).toHaveLength(3);
  expect(pageGuide("/exam-papers").purpose.length).toBeGreaterThan(30);
});
it.each([
  "/",
  '/courses/12/learn',
  '/courses/12/lessons/4',
  '/instructor/courses/12/edit',
  '/instructor/courses/12/quiz-builder',
  '/labs/own-1',
])("keeps page %s free of the shared Back control (home or self-managed)", (path) => {
  expect(needsPageBack(path)).toBe(false);
});
it.each([
  "/courses",
  "/labs",
  "/dashboard",
  "/instructor/dashboard",
  "/admin/courses",
  "/admin/exam-pricing",
  "/instructor/lab-studio",
  "/courses/12",
  "/student/live-classes/8/join",
  "/login",
])("shows the shared Back control on page %s", (path) =>
  expect(needsPageBack(path)).toBe(true),
);
it('reuses the lab header return control without a duplicate banner',()=>{
  window.history.replaceState({idx:0},'', '/labs/own-1');
  render(<BrowserRouter><PageGuide/><PageBackButton/><Location/></BrowserRouter>);
  expect(screen.getAllByRole('button',{name:'Go back to previous page'})).toHaveLength(1);
  fireEvent.click(screen.getByRole('button',{name:'Go back to previous page'}));
  expect(screen.getByTestId('location')).toHaveTextContent('/labs');
});
