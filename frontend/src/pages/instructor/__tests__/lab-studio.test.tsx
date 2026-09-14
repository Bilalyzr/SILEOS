import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import LabStudioPage from "../lab-studio";
import { templateConfig } from "@/components/labs/concept-templates";

const mocks = vi.hoisted(() => ({
  drafts: vi.fn(),
  curriculum: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  publish: vi.fn(),
  import: vi.fn(),
  export: vi.fn(),
}));
vi.mock("@/api/lab-studio", () => ({
  labStudio: mocks,
  downloadLabFile: vi.fn(),
}));
vi.mock("@/components/labs/ConceptLabPlayer", () => ({
  ConceptLabPlayer: () => <div>Live preview</div>,
}));
vi.mock('@/components/three-d/ThreeDModelPicker', () => ({
  ThreeDModelPicker: ({onAttach}: {onAttach:(id:number)=>void}) => <button onClick={() => onAttach(42)}>Attach fixture GLB</button>,
}));
afterEach(cleanup);
beforeEach(() => {
  vi.resetAllMocks();
  mocks.drafts.mockResolvedValue([]);
  mocks.curriculum.mockResolvedValue({ chapters: [], labs: [] });
});
it("saves before publication and does not publish when validation fails", async () => {
  mocks.create.mockRejectedValue(new Error("validation"));
  render(
    <MemoryRouter>
      <LabStudioPage />
    </MemoryRouter>,
  );
  await waitFor(() => expect(mocks.drafts).toHaveBeenCalled());
  fireEvent.click(screen.getByRole("button", { name: "Save & publish" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Could not save");
  expect(mocks.publish).not.toHaveBeenCalled();
  expect(screen.getByLabelText("Lab title")).toHaveValue(
    "My guided lab investigation",
  );
});
it("publishes the saved identifier instead of creating another draft", async () => {
  const saved = {
    slug: "own-123",
    title: "Saved lab",
    subject: "mathematics",
    description: "",
    config: templateConfig("linear"),
    is_published: false,
  };
  mocks.drafts.mockResolvedValue([saved]);
  mocks.update.mockResolvedValue(saved);
  mocks.publish.mockResolvedValue({ ...saved, is_published: true });
  render(
    <MemoryRouter>
      <LabStudioPage />
    </MemoryRouter>,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: /Saved lab Draft/ }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Save & publish" }));
  await waitFor(() =>
    expect(mocks.publish).toHaveBeenCalledWith("own-123", true),
  );
  expect(mocks.create).not.toHaveBeenCalled();
});
