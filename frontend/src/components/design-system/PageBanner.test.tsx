import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PageBanner } from "./PageBanner";

describe("PageBanner", () => {
  it("uses the page title as the primary heading", () => {
    render(
      <PageBanner
        eyebrow="Digital library"
        title="Ideas worth keeping"
        description="Explore guides and lecture notes."
      />,
    );

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Ideas worth keeping",
      }),
    ).toBeInTheDocument();
  });

  it("opens a matching branded share preview when sharing is enabled", () => {
    render(
      <PageBanner
        title="Practice papers"
        description="Build a focused practice set."
        share
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Share" }));

    expect(
      screen.getByRole("dialog", {
        name: "Share something worth discovering",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Practice papers" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /download banner/i }),
    ).toBeInTheDocument();
  });
});
