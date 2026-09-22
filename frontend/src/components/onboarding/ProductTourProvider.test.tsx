import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ProductTourProvider,
  productTourStorageKey,
  productTourVersion,
} from "./ProductTourProvider";

const { authState } = vi.hoisted(() => ({
  authState: {
    user: {
      id: 42,
      role: "student",
      display_name: "Asha Learner",
    },
    profile: {
      first_name: "Asha",
      phone: "9876543210",
    },
    isAuthenticated: true,
  },
}));

vi.mock("@/store/auth", () => ({
  isImpersonating: () => false,
  useAuthStore: (selector: (state: typeof authState) => unknown) =>
    selector(authState),
}));

function mount(path = "/dashboard") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ProductTourProvider>
        <main>Dashboard content</main>
      </ProductTourProvider>
    </MemoryRouter>,
  );
}

describe("ProductTourProvider", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    window.localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    window.localStorage.clear();
  });

  it("opens automatically for a new user with role-aware feature guidance", () => {
    mount();
    act(() => vi.advanceTimersByTime(700));

    expect(screen.getByTestId("product-tour")).toBeVisible();
    expect(screen.getByText("Welcome, Asha")).toBeVisible();
    expect(screen.getByText("Meiporul")).toBeVisible();
    expect(screen.getByText("Seyappaduporul")).toBeVisible();
    expect(screen.getByText("Utporul")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(
      screen.getByText("Know exactly what to learn next"),
    ).toBeVisible();
    expect(screen.getByText("Open my dashboard")).toBeVisible();
  });

  it("remembers dismissal per user and can always be reopened", () => {
    const key = productTourStorageKey(42, "student");
    const first = mount();
    act(() => vi.advanceTimersByTime(700));
    fireEvent.click(screen.getByRole("button", { name: "Skip for now" }));

    expect(JSON.parse(window.localStorage.getItem(key) || "{}")).toMatchObject({
      version: productTourVersion,
      status: "dismissed",
    });

    first.unmount();
    mount();
    act(() => vi.advanceTimersByTime(700));
    expect(screen.queryByTestId("product-tour")).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Open SashaInfinity product tour",
      }),
    );
    expect(screen.getByTestId("product-tour")).toBeVisible();
  });
});
