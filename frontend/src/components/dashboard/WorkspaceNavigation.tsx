import { Link, useLocation } from "react-router-dom";
import type { SidebarItem, SidebarLink } from "./DashboardSidebar";

export function activeWorkspaceLink(items: SidebarItem[], pathname: string) {
  const matches: { link: SidebarLink; section: string }[] = [];
  for (const item of items) {
    const links = item.kind === "group" ? item.children : [item];
    for (const link of links) {
      const prefix = link.matchPrefix || link.to;
      if (link.exact && pathname !== link.to) continue;
      if (
        pathname === link.to ||
        pathname === prefix ||
        pathname.startsWith(prefix + "/")
      )
        matches.push({
          link,
          section: item.kind === "group" ? item.label : "Overview",
        });
    }
  }
  return matches.sort((a, b) => b.link.to.length - a.link.to.length)[0];
}

/** Local navigation keeps related tasks one click away. */
export function WorkspaceNavigation({ items }: { items: SidebarItem[] }) {
  const { pathname } = useLocation();
  const active = activeWorkspaceLink(items, pathname);
  const group = items.find(
    (i) => i.kind === "group" && i.label === active?.section,
  );
  if (!group || group.kind !== "group") return null;
  return (
    <nav className="rd-section-nav" aria-label={`${group.label} pages`}>
      <span>{group.label}</span>
      <div>
        {group.children.map((link) => (
          <Link
            key={link.to}
            to={link.to}
            aria-current={active?.link.to === link.to ? "page" : undefined}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
