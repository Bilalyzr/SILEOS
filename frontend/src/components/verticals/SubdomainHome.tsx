import { HomePage } from "@/pages/Home";
import { verticalFromHostname } from "@/config/businessVerticals";
import { BusinessVerticalPage } from "./BusinessVerticalPage";

export function SubdomainHome() {
  const vertical = typeof window === "undefined" ? null : verticalFromHostname(window.location.hostname);
  return vertical ? <BusinessVerticalPage verticalKey={vertical} /> : <HomePage />;
}

