import { describe, expect, it } from "vitest";
import { pageFamily } from "./AstraRouteTheme";

describe("Astra page families", () => {
  it.each([
    ["/", "dashboard"],
    ["/instructor/dashboard", "dashboard"],
    ["/courses", "catalog"],
    ["/instructor/ebooks", "catalog"],
    ["/labs/cbse-water-states-3d", "learn"],
    ["/courses/2/lessons/4", "learn"],
    ["/quiz-taking/7", "learn"],
    ["/instructor/lab-studio", "learn"],
    ["/instructor/review-queue", "admin"],
    ["/profile", "admin"],
    ["/admin/settings", "admin"],
    ["/company/dashboard", "dashboard"],
    ["/checkout/2", "billing"],
    ["/admin/payments", "billing"],
    ["/membership", "billing"],
    ["/future-page", "dashboard"],
  ])("classifies %s without affecting routing", (route, family) => {
    expect(pageFamily(route)).toBe(family);
  });
});
