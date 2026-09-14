import { Fragment } from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { PageHeading } from "@/components/design-system/PageLayout";
export default function PageHeader({
  title,
  breadcrumbs = [],
}: {
  title: string;
  breadcrumbs?: { name: string; path: string }[];
}) {
  return (
    <div className="rd-route-heading">
      <nav
        className="rd-breadcrumb rd-public-breadcrumb"
        aria-label="Breadcrumb"
      >
        {breadcrumbs.map((crumb, i) => (
          <Fragment key={crumb.path}>
            {i > 0 && <ChevronRight size={12} />}
            <Link
              to={crumb.path}
              aria-current={i === breadcrumbs.length - 1 ? "page" : undefined}
            >
              {crumb.name}
            </Link>
          </Fragment>
        ))}
      </nav>
      <PageHeading title={title} />
    </div>
  );
}
