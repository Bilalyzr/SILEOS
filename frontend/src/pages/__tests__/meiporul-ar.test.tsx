import type { ReactNode } from "react";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { MeiporulARPage } from "../meiporul-ar";

vi.mock("@/components/design-system/PageLayout", () => ({
  PageLayout: ({ header, children }: { header: ReactNode; children: ReactNode }) => <main>{header}{children}</main>,
  PageHeader: ({ children }: { children: ReactNode }) => <header>{children}</header>,
}));
beforeAll(() => {
  if (!customElements.get("model-viewer")) customElements.define("model-viewer", class extends HTMLElement {});
});
describe("Meiporul model gallery", () => {
  it("combines category and text search", () => {
    render(<MeiporulARPage />);
    fireEvent.click(screen.getByRole("button", { name: /^Surfaces/ }));
    expect(screen.queryByRole("button", { name: /Pythagorean Theorem/ })).not.toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Search models..."), { target: { value: "Ordinary Helicoid" } });
    expect(screen.getByRole("button", { name: /Ordinary Helicoid/ })).toBeInTheDocument();
    expect(screen.getByText(/Showing 1 of/)).toBeInTheDocument();
  });
  it("navigates models and closes the accessible dialog", () => {
    render(<MeiporulARPage />);
    fireEvent.click(screen.getByRole("button", { name: /Rough Work/ }));
    let dialog = screen.getByRole("dialog", { name: /Rough Work/ });
    fireEvent.click(within(dialog).getByRole("button", { name: "Next model" }));
    dialog = screen.getByRole("dialog", { name: "Pythagorean Theorem" });
    fireEvent.keyDown(document, { key: "ArrowLeft" });
    dialog = screen.getByRole("dialog", { name: /Rough Work/ });
    fireEvent.click(within(dialog).getByRole("button", { name: /^Close$/ }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
