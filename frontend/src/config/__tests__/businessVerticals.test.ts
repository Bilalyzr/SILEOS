import { describe, expect, it } from "vitest";
import {
  BUSINESS_VERTICALS,
  normalizeBusinessVertical,
  verticalFromHostname,
  verticalPublicHref,
} from "../businessVerticals";

describe("business vertical routing", () => {
  it("maps each production subdomain to its pillar", () => {
    expect(verticalFromHostname("meiporul.sashainfinity.com")).toBe("meiporul");
    expect(verticalFromHostname("seyappaduporul.sashainfinity.com")).toBe("seyappaduporul");
    expect(verticalFromHostname("utporul.sashainfinity.com")).toBe("utporul");
    expect(verticalFromHostname("sashainfinity.com")).toBeNull();
  });

  it("keeps the blueprint spelling as an alias without changing the public name", () => {
    expect(normalizeBusinessVertical("Upporul")).toBe("utporul");
    expect(normalizeBusinessVertical("seyappadu_porul")).toBe("seyappaduporul");
    expect(BUSINESS_VERTICALS.utporul.label).toBe("Utporul");
  });

  it("uses real subdomains in production and local routes during development", () => {
    expect(verticalPublicHref("meiporul", "sashainfinity.com")).toBe(
      "https://meiporul.sashainfinity.com",
    );
    expect(verticalPublicHref("utporul", "localhost")).toBe("/utporul");
  });
});
