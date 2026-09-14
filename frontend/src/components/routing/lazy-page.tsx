import { lazy, Suspense, type ComponentType } from "react";
import { PageGuide } from "./PageGuide";
import { LearningPreferences } from "@/components/labs/LearningPreferences";

/** Keep the surrounding navigation mounted while a route's code loads. */
export function lazyPage(load: () => Promise<{ default: ComponentType<any> }>) {
  const Page = lazy(load);
  return function DeferredPage(props: any) {
    return (
      <div className="astra-route-page">
        {/* Accessibility / அணுகல்தன்மை lives beside the "How this page
            works" guide at the top of every route (moved 2026-09-14 from a
            fixed bottom-left corner that overlapped page content). PageGuide
            renders null on pages without a back button — the row keeps the
            accessibility trigger present and top-aligned on those too. */}
        <div className="astra-guide-row">
          <PageGuide />
          <LearningPreferences />
        </div>
        <Suspense
          fallback={
            <div className="astra-work p-6" role="status" aria-live="polite">
              Loading this workspace…
            </div>
          }
        >
          <Page {...props} />
        </Suspense>
      </div>
    );
  };
}
