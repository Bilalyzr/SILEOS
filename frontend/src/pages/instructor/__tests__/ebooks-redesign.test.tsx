import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import InstructorEbooksPage from "../ebooks";

const api = vi.hoisted(() => ({
  mine: vi.fn(),
  update: vi.fn(),
  create: vi.fn(),
  publish: vi.fn(),
}));
vi.mock("@/api/library", () => ({
  libraryAPI: api,
  EBOOK_CATEGORY_LABELS: { book: "Books", guide: "Guides" },
}));
vi.mock("react-hot-toast", () => ({
  default: { success: vi.fn(), error: vi.fn() },
}));
const book = {
  id: 1,
  title: "Physics handbook",
  description: "A practical guide",
  category: "book",
  status: "published",
  effective_price_inr: 199,
  price_inr: 199,
  discount_price_inr: null,
  page_count: 50,
  cover_image: "",
  concept_tags: ["physics"],
  has_file: true,
  has_sample: false,
};
const draft = {
  ...book,
  id: 2,
  title: "Biology notes",
  status: "draft",
  has_file: false,
};
beforeEach(() => {
  vi.resetAllMocks();
  api.mine.mockResolvedValue({ ebooks: [book, draft] });
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const open = () =>
  render(
    <MemoryRouter>
      <InstructorEbooksPage />
    </MemoryRouter>,
  );

it("filters the resource list and keeps the details panel on a visible resource", async () => {
  open();
  await screen.findByRole("button", { name: /Physics handbook Books/ });
  fireEvent.click(screen.getByRole("button", { name: "Drafts" }));
  const table = screen.getByRole("table");
  expect(within(table).queryByText("Physics handbook")).not.toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Biology notes" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Publish" }),
  ).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Search your ebooks"), {
    target: { value: "missing" },
  });
  expect(screen.getByText("No matching resources")).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "Biology notes" }),
  ).not.toBeInTheDocument();
});

it("edits the selected ebook with its identifier without publishing it", async () => {
  api.update.mockResolvedValue({ ...draft, title: "Updated biology notes" });
  open();
  fireEvent.click(
    await screen.findByRole("button", { name: /Biology notes Books/ }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Edit details" }));
  fireEvent.change(screen.getByLabelText("Title *"), {
    target: { value: "Updated biology notes" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  await waitFor(() =>
    expect(api.update).toHaveBeenCalledWith(
      2,
      expect.objectContaining({ title: "Updated biology notes" }),
    ),
  );
  expect(api.create).not.toHaveBeenCalled();
  expect(api.publish).not.toHaveBeenCalled();
});

it("shows a retry action rather than an empty-library message when loading fails", async () => {
  api.mine.mockRejectedValueOnce(new Error("Unavailable"));
  open();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not be loaded",
  );
  expect(
    screen.queryByText("Your next chapter starts here"),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(
    await screen.findByRole("button", { name: /Physics handbook Books/ }),
  ).toBeInTheDocument();
});
