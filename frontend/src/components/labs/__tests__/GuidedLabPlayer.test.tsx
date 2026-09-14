import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { GuidedLabPlayer } from "../GuidedLabPlayer";
import type { ConceptConfig } from "@/api/lab-studio";
const mocks = vi.hoisted(() => ({ post: vi.fn(), queue: vi.fn() }));
vi.mock("@/api/axios", () => ({ api: { post: mocks.post } }));
vi.mock("@/offline/storage", () => ({
  ownerId: () => 44,
  queueEvent: mocks.queue,
}));
const config: ConceptConfig = {
  engine: "supplied",
  source_slug: "cbse-fractions-explorer",
  objective: "Understand fractions",
  prediction: "Which is larger?",
  investigation: ["Compare"],
  explanation: "",
  chapter_ids: [],
  cards: [],
  assessment_enabled: true,
  guided_steps: [
    {
      id: "q",
      kind: "question",
      title: "Choose one half",
      instruction: "Pick an answer",
      options: ["1/2", "1/3"],
      points: 4,
    },
  ],
};
beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  Object.defineProperty(navigator, "onLine", {
    value: true,
    configurable: true,
  });
  mocks.post.mockResolvedValue({
    data: { score: 4, max_score: 4, feedback: [] },
  });
  mocks.queue.mockResolvedValue(undefined);
});
it("sends evidence without client scores or answer keys and shows the server result", async () => {
  render(
    <GuidedLabPlayer
      config={config}
      slug="own-test"
      revision={"a".repeat(64)}
    />,
  );
  fireEvent.click(screen.getByLabelText("1/2"));
  fireEvent.click(screen.getByRole("button", { name: "Submit investigation" }));
  await screen.findByText("Score: 4/4");
  expect(mocks.post.mock.calls[0][1].answers).toEqual({ q: 0 });
  expect(mocks.post.mock.calls[0][1]).not.toHaveProperty("score");
  expect(mocks.post.mock.calls[0][1]).not.toHaveProperty("correct_index");
});
it("queues the same versioned evidence offline without claiming a score", async () => {
  Object.defineProperty(navigator, "onLine", {
    value: false,
    configurable: true,
  });
  render(
    <GuidedLabPlayer
      config={config}
      slug="own-test"
      revision={"b".repeat(64)}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Submit investigation" }));
  await waitFor(() => expect(mocks.queue).toHaveBeenCalledOnce());
  expect(mocks.post).not.toHaveBeenCalled();
  expect(mocks.queue.mock.calls[0][1].revision).toBe("b".repeat(64));
  expect(screen.queryByText(/Score:/)).not.toBeInTheDocument();
});
it("keeps answers after a stale-version rejection", async () => {
  mocks.post.mockRejectedValue({
    response: { status: 409, data: { detail: "The activity changed." } },
  });
  render(
    <GuidedLabPlayer
      config={config}
      slug="own-test"
      revision={"c".repeat(64)}
    />,
  );
  fireEvent.click(screen.getByLabelText("1/3"));
  fireEvent.click(screen.getByRole("button", { name: "Submit investigation" }));
  await screen.findByText("The activity changed.");
  expect(screen.getByLabelText("1/3")).toBeChecked();
  expect(mocks.queue).not.toHaveBeenCalled();
});
