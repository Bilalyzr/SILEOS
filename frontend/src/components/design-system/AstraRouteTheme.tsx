import { useLayoutEffect } from "react";
import { useLocation } from "react-router-dom";
import { initialiseAurumPreferences } from "@/components/brand/AurumDisplayControls";

export type PageFamily =
  | "dashboard"
  | "learn"
  | "catalog"
  | "admin"
  | "billing";

/** Visual classification only; route access and page data remain with the router. */
export function pageFamily(pathname: string): PageFamily {
  if (
    /(?:^|\/)(exam-pricing|checkout|cart|billing|payments?|orders?|membership|subscriptions?|payouts?|revenue)(?:\/|$)/.test(
      pathname,
    )
  )
    return "billing";
  if (
    /(?:^|\/)(exam-papers|lesson|lessons|learn|labs|lab-studio|quizzes|quiz|quiz-taking|assignments|live|my-learning|my-grades|my-mastery)(?:\/|$)/.test(
      pathname,
    )
  )
    return "learn";
  if (
    /(?:^|\/)(admin|superadmin|settings|profile|review-queue|security|audit)(?:\/|$)/.test(
      pathname,
    )
  )
    return "admin";
  if (
    /(?:^|\/)(courses|categories|category[^/]*|library|ebooks|bundles|blog|internships|search|wishlist)(?:\/|$)/.test(
      pathname,
    )
  )
    return "catalog";
  return "dashboard";
}

export function AstraRouteTheme() {
  const { pathname } = useLocation();
  useLayoutEffect(() => {
    document.body.dataset.pageFamily = pageFamily(pathname);
    initialiseAurumPreferences();
  }, [pathname]);
  return null;
}
