import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import LabsPage from "../labs";

vi.mock("@/store/auth", () => ({
  useAuthStore: (select: (state: { user: null }) => unknown) =>
    select({ user: null }),
}));
vi.mock("@/api/lab-studio", () => ({
  labStudio: {
    curriculum: async () => ({
      labs: [],
      source: "Supplied curriculum",
      editions: [
        { id: "ncert-2024", label: "Updated curriculum" },
        { id: "legacy", label: "Earlier curriculum" },
      ],
      chapters: [
        {
          id: "ncert-2024-6-mathematics-1",
          edition: "ncert-2024",
          grade: 6,
          subject: "mathematics",
          title: "Patterns in Mathematics",
          difficulty: 1,
          lab_slug: null,
        },
        {
          id: "6-mathematics-1",
          edition: "legacy",
          grade: 6,
          subject: "mathematics",
          title: "Knowing Our Numbers",
          difficulty: 1,
          lab_slug: "concept-old",
        },
      ],
    }),
  },
}));
vi.mock("@/api/labs", () => ({
  listLabs: async () => [
    {
      slug: "own-patterns",
      title: "Pattern investigation",
      subject: "mathematics",
      description: "Explore a pattern",
      native_template: "concept_lab",
      chapter_ids: ["ncert-2024-6-mathematics-1"],
    },
  ],
}));

afterEach(cleanup);

it("keeps curriculum editions distinct and reports gaps without overstating coverage", async () => {
  render(
    <MemoryRouter>
      <LabsPage />
    </MemoryRouter>,
  );
  await screen.findByText("Pattern investigation");
  fireEvent.click(
    screen.getByRole("button", { name: "Curriculum" }),
  );
  expect(screen.getByText("Patterns in Mathematics")).toBeInTheDocument();
  expect(screen.queryByText("Knowing Our Numbers")).not.toBeInTheDocument();
  expect(screen.getByText(/0 of 1 matching chapters/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Curriculum edition"), {
    target: { value: "legacy" },
  });
  expect(screen.getByText("Knowing Our Numbers")).toBeInTheDocument();
  expect(screen.queryByText("Patterns in Mathematics")).not.toBeInTheDocument();
  expect(screen.getByText(/1 of 1 matching chapters/)).toBeInTheDocument();
  expect(
    within(
      screen.getByText("Knowing Our Numbers").closest("article")!,
    ).getByRole("link"),
  ).toHaveAttribute("href", "/labs/concept-old");
});

it("filters instructor labs by the grade of versioned chapter IDs", async () => {
  render(
    <MemoryRouter>
      <LabsPage />
    </MemoryRouter>,
  );
  await screen.findByText("Pattern investigation");
  fireEvent.change(screen.getByLabelText("Class"), { target: { value: "6" } });
  expect(screen.getByText("Pattern investigation")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Class"), { target: { value: "7" } });
  expect(screen.queryByText("Pattern investigation")).not.toBeInTheDocument();
});
