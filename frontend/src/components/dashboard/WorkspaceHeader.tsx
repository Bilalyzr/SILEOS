import { AccessibilityMenu } from "@/components/a11y/AccessibilityMenu";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Search,
  FlaskConical,
  Menu,
  ChevronRight,
  ArrowUpRight,
  Building2,
} from "lucide-react";
import { activeWorkspaceLink } from "./WorkspaceNavigation";
import type { SidebarItem } from "./DashboardSidebar";

export function WorkspaceHeader({
  role,
  items,
  onMenu,
  mobileOpen,
}: {
  role?: string;
  items: SidebarItem[];
  onMenu?: () => void;
  mobileOpen?: boolean;
}) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const active = activeWorkspaceLink(items, pathname);
  return (
    <header className="rd-workspace-header">
      {onMenu && (
        <button
          className="rd-icon-button"
          onClick={onMenu}
          aria-label="Open menu"
          aria-expanded={mobileOpen}
          aria-controls="workspace-sidebar"
        >
          <Menu size={20} />
        </button>
      )}
      <nav aria-label="Breadcrumb" className="rd-breadcrumb">
        <span className="capitalize">{role || "Learning"}</span>
        <ChevronRight size={13} />
        <strong>
          {active?.section === "Overview"
            ? active.link.label
            : active?.section || "Workspace"}
        </strong>
      </nav>
      <form
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          if (query.trim())
            navigate(`/search?q=${encodeURIComponent(query.trim())}`);
        }}
      >
        <Search size={16} />
        <input
          aria-label="Search learning content"
          placeholder="Search learning content..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button aria-label="Search">
          <ArrowUpRight size={16} />
        </button>
      </form>
      <AccessibilityMenu />
      <Link to="/institutions" className="rd-labs-link" aria-label="Institution workspaces">
        <Building2 size={17} />
        <span>Campus</span>
      </Link>
      <Link to="/labs" className="rd-labs-link">
        <FlaskConical size={17} />
        <span>Learning labs</span>
      </Link>
    </header>
  );
}
