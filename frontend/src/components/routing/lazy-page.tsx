import { lazy, Suspense, type ComponentType } from "react";
import { PageGuide } from "./PageGuide";

/** Keep the surrounding navigation mounted while a route's code loads. */
export function lazyPage(load: () => Promise<{ default: ComponentType<any> }>) {
  const Page = lazy(load);
  return function DeferredPage(props: any) {
    return (
      <div className="astra-route-page">
        <PageGuide />
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
