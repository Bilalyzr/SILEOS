import type { ReactNode } from "react";

/** Page composition, independent of routing, permissions and data fetching. */
export function PageLayout({
  children,
  header,
  toolbar,
  aside,
  className = "",
}: {
  children: ReactNode;
  header?: ReactNode;
  toolbar?: ReactNode;
  aside?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rd-page ${className}`}>
      {header}
      {toolbar && <div className="rd-toolbar">{toolbar}</div>}
      <div className={aside ? "rd-workbench" : "rd-body"}>
        <div className="rd-primary">{children}</div>
        {aside && <aside className="rd-context">{aside}</aside>}
      </div>
    </div>
  );
}

export function PageHeading({
  title,
  description,
  eyebrow,
  actions,
}: {
  title: ReactNode;
  description?: ReactNode;
  eyebrow?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="rd-page-heading">
      <div>
        {eyebrow && <span className="rd-eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="rd-heading-actions">{actions}</div>}
    </header>
  );
}

/** Keeps existing page heading markup/actions when migrating a domain screen. */
export function PageHeader({ children }: { children: ReactNode }) {
  return (
    <header className="rd-page-heading rd-migrated-heading">{children}</header>
  );
}

export function MetricStrip({
  items,
}: {
  items: { label: string; value: ReactNode; note?: string }[];
}) {
  return (
    <dl className="rd-metrics" data-glass="work">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
          {item.note && <p>{item.note}</p>}
        </div>
      ))}
    </dl>
  );
}

export function WorkPanel({
  title,
  description,
  actions,
  children,
  className = "",
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rd-panel ${className}`} data-glass="work">
      <header>
        <div>
          <h2>{title}</h2>
          {description && <p>{description}</p>}
        </div>
        {actions}
      </header>
      <div className="rd-panel-body">{children}</div>
    </section>
  );
}
