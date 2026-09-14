import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, it, expect, vi } from "vitest";
const f = vi.hoisted(() => ({
  build: vi.fn(),
  download: vi.fn(),
  copy: vi.fn(),
  success: vi.fn(),
}));
vi.mock("@/utils/brand-artwork", () => ({
  buildBrandArtwork: f.build,
  downloadArtwork: f.download,
  readBannerFile: vi.fn(),
}));
vi.mock("@/utils/certificate-share", () => ({ copyToClipboard: f.copy }));
vi.mock("react-hot-toast", () => ({ default: { success: f.success } }));
import { ShareButton } from "../share-button";
afterEach(cleanup);
beforeEach(() => {
  vi.resetAllMocks();
});
describe("branded sharing", () => {
  it("opens an accessible preview and downloads a matching image", async () => {
    const blob = new Blob(["png"], { type: "image/png" });
    f.build.mockResolvedValue(blob);
    render(
      <ShareButton title="Physics foundations" description="Discover motion" />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Share" }));
    await screen.findByText("Physics foundations");
    fireEvent.click(screen.getByText("Download banner"));
    await waitFor(() => expect(f.download).toHaveBeenCalledWith(blob));
    expect(f.build).toHaveBeenCalledWith(
      "Physics foundations",
      "Discover motion",
      undefined,
    );
  });
  it("does not claim copy success when the clipboard fails", async () => {
    f.copy.mockResolvedValue(false);
    render(<ShareButton showLabel={false} />);
    fireEvent.click(screen.getByRole("button", { name: "Share" }));
    fireEvent.click(screen.getByText("Copy link"));
    await screen.findByRole("alert");
    expect(f.success).not.toHaveBeenCalled();
  });
  it("retains the dialog and gives an error if image generation fails", async () => {
    f.build.mockRejectedValue(new Error("canvas failure"));
    render(<ShareButton />);
    fireEvent.click(screen.getByRole("button", { name: "Share" }));
    fireEvent.click(screen.getByText("Download banner"));
    await screen.findByText(/Unable to create the banner/);
    expect(f.download).not.toHaveBeenCalled();
    expect(screen.getByText("Download banner")).not.toBeDisabled();
  });
});
