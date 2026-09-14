/**
 * Layout wrapper combining the unified DashboardSidebar with the dashboard
 * background + content container. Animated route transitions for the
 * inner content.
 */
import * as React from "react";
import { WorkspaceBanner } from "@/components/design-system/BrandBanner";
import { AmbientBrandBackground } from "@/components/brand/AmbientBrandBackground";
import { motion, AnimatePresence } from "framer-motion";
import { useLocation } from "react-router-dom";
import { WorkspaceNavigation } from "./WorkspaceNavigation";
import {
  DashboardSidebar,
  type SidebarItem,
  type Role,
} from "./DashboardSidebar";
import { ImpersonationBanner } from "@/components/admin/ImpersonationBanner";
import "./theme.css";
import { WorkspaceHeader } from "./WorkspaceHeader";

const SIDEBAR_W = 238;
const SIDEBAR_W_COLLAPSED = 68;

// Below this width the fixed side rail becomes an off-canvas drawer and the
// content offset drops to 0 — otherwise the 240px paddingLeft crushes the
// page into a sliver on phones (the cause of the overlapping dashboard text).
const MOBILE_BREAKPOINT = "(max-width: 767px)";
const COMPACT_BREAKPOINT = "(max-width: 1023px)";

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = React.useState<boolean>(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia(query).matches,
  );
  React.useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);
  return matches;
}

export interface DashboardWorkspaceProps {
  items: SidebarItem[];
  role?: Role;
  homeTo?: string;
  /** Page-level wrapper; default true wraps content in max-w container w/ padding. */
  contained?: boolean;
  children: React.ReactNode;
}

export const DashboardWorkspace: React.FC<DashboardWorkspaceProps> = ({
  items,
  role,
  homeTo,
  contained = true,
  children,
}) => {
  const { pathname } = useLocation();
  const isMobile = useMediaQuery(MOBILE_BREAKPOINT);
  const isCompact = useMediaQuery(COMPACT_BREAKPOINT);
  // Persist collapsed state in localStorage; controlled here, passed to sidebar.
  const [collapsed, setCollapsed] = React.useState<boolean>(
    () =>
      typeof window !== "undefined" &&
      localStorage.getItem("dash_sidebar_collapsed") === "1",
  );
  const handleCollapsedChange = React.useCallback((v: boolean) => {
    localStorage.setItem("dash_sidebar_collapsed", v ? "1" : "0");
    setCollapsed(v);
  }, []);

  // Mobile drawer open state — closes automatically on navigation and when
  // the viewport grows back to desktop.
  const [mobileOpen, setMobileOpen] = React.useState(false);
  React.useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);
  React.useEffect(() => {
    if (!isMobile) setMobileOpen(false);
  }, [isMobile]);

  // On mobile the rail is a full-width drawer (never the 72px collapsed rail)
  // and the content sits flush (no left offset).
  const offsetW = isMobile
    ? 0
    : isCompact || collapsed
      ? SIDEBAR_W_COLLAPSED
      : SIDEBAR_W;

  return (
    <div className="dash-bg rd-workspace relative min-h-screen">
      <AmbientBrandBackground />
      {/* Admin impersonation banner - shows on all dashboards */}
      <ImpersonationBanner />

      <div className="dash-bg-shape dash-bg-shape-1" aria-hidden />
      <div className="dash-bg-shape dash-bg-shape-2" aria-hidden />
      <div className="dash-bg-shape dash-bg-shape-3" aria-hidden />

      <DashboardSidebar
        width={SIDEBAR_W}
        items={items}
        role={role}
        homeTo={homeTo}
        collapsed={isMobile ? false : isCompact ? true : collapsed}
        onCollapsedChange={handleCollapsedChange}
        offCanvas={isMobile && !mobileOpen}
        showCollapseToggle={!isCompact}
      />

      {/* Mobile: backdrop that closes the drawer */}
      {isMobile && mobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden
        />
      )}

      <motion.main
        style={{ paddingLeft: offsetW }}
        className="relative z-10 si-page-enter"
      >
        <WorkspaceHeader
          role={role}
          items={items}
          onMenu={isMobile ? () => setMobileOpen((v) => !v) : undefined}
          mobileOpen={mobileOpen}
        />
        <WorkspaceNavigation items={items} />
        <WorkspaceBanner pathname={pathname} role={role || "student"} />
        {contained ? (
          <div className="rd-workspace-content">
            <PageTransition pathname={pathname}>{children}</PageTransition>
          </div>
        ) : (
          <PageTransition pathname={pathname}>{children}</PageTransition>
        )}
      </motion.main>
    </div>
  );
};

// Animated route-change transition wrapper
const PageTransition: React.FC<{
  pathname: string;
  children: React.ReactNode;
}> = ({ pathname, children }) => (
  <AnimatePresence mode="wait">
    <motion.div
      key={pathname}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  </AnimatePresence>
);

// ---------------------------------------------------------------------------
// Persist collapsed state — small wrapper hook used by the sidebar through
// the localStorage shim. Exporting here so any caller can read it.
// ---------------------------------------------------------------------------

export function useSidebarCollapsed(): [boolean, (v: boolean) => void] {
  const [collapsed, set] = React.useState<boolean>(
    () => localStorage.getItem("dash_sidebar_collapsed") === "1",
  );
  const toggle = React.useCallback((v: boolean) => {
    localStorage.setItem("dash_sidebar_collapsed", v ? "1" : "0");
    set(v);
  }, []);
  return [collapsed, toggle];
}

export default DashboardWorkspace;
