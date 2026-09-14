import { it, expect, vi } from "vitest";
vi.mock("@/store/auth", () => ({
  useAuthStore: { getState: () => ({ accessToken: null }) },
  isImpersonating: () => false,
}));
vi.mock("react-hot-toast", () => ({ default: { error: vi.fn() } }));
import { api } from "../axios";

it.each([
  "/exam-papers",
  "/exam-papers/pricing",
  "/exam-papers/admin/slabs",
  "/exam-papers/paper-id/verify",
  "/exam-papers/paper-id/generate",
  "/courses/slug-availability",
  "/whatsapp/status",
  "/whatsapp/opt-in",
  "/whatsapp/admin/overview",
  "/whatsapp/admin/contacts",
  "/whatsapp/admin/campaigns",
])("preserves the backend no-slash contract for %s", async (url) => {
  let actual;
  api.defaults.adapter = async (config) => {
    actual = config.url;
    return { data: {}, status: 200, statusText: "OK", headers: {}, config };
  };
  await api.get(url);
  expect(actual).toBe(url);
});
