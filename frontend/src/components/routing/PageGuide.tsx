import { Compass } from "lucide-react";
import { useLocation } from "react-router-dom";
import { pageGuide, needsPageBack } from "./page-guides";
import { PageBackButton } from './PageBackButton';

/** Every routed page uses this via lazyPage; no page-specific navigation drift. */
export function PageGuide() {
  const location = useLocation();
  const guide = pageGuide(location.pathname);
  if (!needsPageBack(location.pathname, location.search)) return null;
  return (
    <section className="astra-page-guide print:hidden" aria-label="Page guide">
      <div className="astra-guide-top">
        <PageBackButton/>
        <span className="astra-guide-title">
          <Compass size={16} />
          {guide.title}
        </span>
      </div>
      <p>{guide.purpose}</p>
      <details key={location.pathname} className="astra-guide-workflow">
        <summary>How this page works</summary>
        <ol>
          {guide.steps.map((step, i) => (
            <li key={step}>
              <span aria-hidden="true">{i + 1}</span>
              {step}
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}
