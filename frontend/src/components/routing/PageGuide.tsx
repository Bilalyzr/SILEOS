import { useLocation } from "react-router-dom";
import { needsPageBack } from "./page-guides";
import { PageBackButton } from './PageBackButton';

/**
 * App-wide back navigation. Every routed page renders this through lazyPage;
 * pages that already carry their own return control (lesson player, lab
 * workspace, course editors) opt out via needsPageBack, and the home page
 * has nothing to go back to.
 */
export function PageGuide() {
  const location = useLocation();
  if (!needsPageBack(location.pathname, location.search)) return null;
  return (
    <nav className="astra-page-back print:hidden" aria-label="Back navigation">
      <PageBackButton />
    </nav>
  );
}
