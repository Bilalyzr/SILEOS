import { PageHeading } from "@/components/design-system/PageLayout";
/**
 * Dashboard primitives — fully rebuilt v2.
 *
 * Tied to the public hero section's color scheme via theme.css. Adds:
 *   - DashboardShell: gradient bg + decorative blurred shapes + container
 *   - Animated entrance (framer-motion) + staggered grids
 *   - Animated count-up for stat values
 *   - Sparkline support inside StatCard
 *
 * No dynamic Tailwind class strings — Tailwind JIT cannot resolve
 * template-literal classes, so all tone variants are mapped statically.
 */
import * as React from "react";
import { Link } from "react-router-dom";
import {
  motion,
  type Variants,
} from "framer-motion";
import {
  ArrowUpRight,
  ArrowDownRight,
  AlertCircle,
  RefreshCw,
  type LucideIcon,
} from "lucide-react";
import "./theme.css";

// ===========================================================================
// Tone palette — statically mapped (no string templates so JIT works)
// ===========================================================================

export type StatTone =
  | "orange"
  | "navy"
  | "sky"
  | "emerald"
  | "purple"
  | "rose"
  | "amber"
  | "slate";

const TONES: Record<
  StatTone,
  { iconBg: string; iconFg: string; ring: string; chartHex: string }
> = {
  orange: {
    iconBg: "bg-orange-100",
    iconFg: "text-orange-700",
    ring: "ring-orange-200/40",
    chartHex: "#f97316",
  },
  navy: {
    iconBg: "bg-secondary-100",
    iconFg: "text-secondary-800",
    ring: "ring-secondary-200/40",
    chartHex: "#20345b",
  },
  sky: {
    iconBg: "bg-sky-100",
    iconFg: "text-sky-700",
    ring: "ring-sky-200/40",
    chartHex: "#0ea5e9",
  },
  emerald: {
    iconBg: "bg-emerald-100",
    iconFg: "text-emerald-700",
    ring: "ring-emerald-200/40",
    chartHex: "#10b981",
  },
  purple: {
    iconBg: "bg-purple-100",
    iconFg: "text-purple-700",
    ring: "ring-purple-200/40",
    chartHex: "#a855f7",
  },
  rose: {
    iconBg: "bg-rose-100",
    iconFg: "text-rose-700",
    ring: "ring-rose-200/40",
    chartHex: "#f43f5e",
  },
  amber: {
    iconBg: "bg-amber-100",
    iconFg: "text-amber-700",
    ring: "ring-amber-200/40",
    chartHex: "#f59e0b",
  },
  slate: {
    iconBg: "bg-slate-100",
    iconFg: "text-slate-700",
    ring: "ring-slate-200/40",
    chartHex: "#64748b",
  },
};

export const TONE_HEX: Record<StatTone, string> = Object.fromEntries(
  Object.entries(TONES).map(([k, v]) => [k, v.chartHex]),
) as Record<StatTone, string>;

// ===========================================================================
// DashboardShell — gradient bg + decorative shapes + content container.
// Optionally renders the unified DashboardNavbar at the top.
// ===========================================================================

export const DashboardShell: React.FC<{
  children: React.ReactNode;
  /** When true, renders without bg/shapes — for routes already inside an
   *  admin layout that has its own chrome. */
  bare?: boolean;
  /** When true, renders the unified DashboardNavbar at the top.
   *  Default true; pass false from inside layouts that already have a
   *  navbar (e.g. AdminLayout, CompanyDashboardPage). */
  navbar?: boolean;
  /** Forwarded to DashboardNavbar. */
  navbarRole?: import("./DashboardNavbar").Role;
  navbarHomeTo?: string;
  className?: string;
}> = ({
  children,
  bare = false,
  navbar = true,
  navbarRole,
  navbarHomeTo,
  className = "",
}) => {
  // Lazy require to avoid circular import at module top
  const NavbarLazy = navbar
    ? React.lazy(() =>
        import("./DashboardNavbar").then((m) => ({
          default: m.DashboardNavbar,
        })),
      )
    : null;
  const innerContent = (
    <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {children}
    </div>
  );

  if (bare) {
    return (
      <div className={`relative ${className}`}>
        {NavbarLazy && (
          <React.Suspense
            fallback={
              <div className="h-16 bg-white border-b border-slate-200/70" />
            }
          >
            <NavbarLazy role={navbarRole} homeTo={navbarHomeTo} />
          </React.Suspense>
        )}
        {children}
      </div>
    );
  }
  return (
    <div className={`dash-bg relative ${className}`}>
      {NavbarLazy && (
        <React.Suspense
          fallback={
            <div className="h-16 bg-white border-b border-slate-200/70" />
          }
        >
          <NavbarLazy role={navbarRole} homeTo={navbarHomeTo} />
        </React.Suspense>
      )}
      <div className="dash-bg-shape dash-bg-shape-1" aria-hidden />
      <div className="dash-bg-shape dash-bg-shape-2" aria-hidden />
      <div className="dash-bg-shape dash-bg-shape-3" aria-hidden />
      {innerContent}
    </div>
  );
};

// ===========================================================================
// Animation helpers
// ===========================================================================

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.16, ease: [0.2, 0.7, 0.3, 1] },
  },
};

export const staggerContainer: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.04 } },
};

export const StaggerGrid: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = "",
  ...rest
}) => (
  <motion.div
    variants={staggerContainer}
    initial="hidden"
    animate="show"
    className={className}
    {...(rest as any)}
  >
    {children}
  </motion.div>
);

export const FadeUp: React.FC<{
  children: React.ReactNode;
  className?: string;
  delay?: number;
}> = ({ children, className = "", delay = 0 }) => (
  <motion.div
    variants={fadeUp}
    initial="hidden"
    animate="show"
    transition={{ delay }}
    className={className}
  >
    {children}
  </motion.div>
);

// ===========================================================================
// AnimatedNumber — count-up for stat values
// ===========================================================================

export const AnimatedNumber: React.FC<{
  value: number;
  format?: (n: number) => string;
  duration?: number;
  className?: string;
}> = ({ value, format, className = "" }) => (
  <span className={className}>{format ? format(value) : Math.round(value).toString()}</span>
);

// ===========================================================================
// StatCard — centerpiece tile
// ===========================================================================

export interface StatCardProps {
  title: string;
  value: number;
  /** Optional formatter — e.g. (n) => `₹${n.toLocaleString('en-IN')}`. */
  format?: (n: number) => string;
  icon: LucideIcon;
  tone?: StatTone;
  /** When provided, the card becomes a link with a subtle arrow. */
  to?: string;
  /** Small text next to the value, e.g. "+12% this month". */
  delta?: string;
  deltaDirection?: "up" | "down" | "flat";
  /** Optional small chart drawn at the bottom — pass an array of numbers. */
  spark?: number[];
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  format,
  icon: Icon,
  tone = "orange",
  to,
  delta,
  deltaDirection = "up",
  spark,
  className = "",
}) => {
  const t = TONES[tone];

  const inner = (
    <>
      <div className="rd-stat-label">{title}</div>
      <div className="rd-stat-value">
        <AnimatedNumber value={value} format={format} />
      </div>
      <div className="rd-stat-icon">
        <Icon size={18} />
      </div>
      <div className="rd-stat-footer">
        {delta && (
          <span
            className={
              deltaDirection === "down"
                ? "text-rose-600"
                : deltaDirection === "up"
                  ? "text-emerald-700"
                  : ""
            }
          >
            {deltaDirection === "down" ? (
              <ArrowDownRight size={12} className="inline" />
            ) : deltaDirection === "up" ? (
              <ArrowUpRight size={12} className="inline" />
            ) : null}
            {delta}
          </span>
        )}
        {to && <span>View details</span>}
        {spark && spark.length > 1 && (
          <Sparkline data={spark} stroke={t.chartHex} />
        )}
      </div>
    </>
  );

  // h-full on both the grid item and the card: the item stretches to the row
  // height by default, but the card inside only grew to its own content, so
  // cards without a sparkline ended up visibly shorter than their neighbours.
  const baseClass = `dash-card rd-stat astra-work group p-5 h-full ${to ? "cursor-pointer block" : ""} ${className}`;

  return (
    <motion.div variants={fadeUp} className="h-full">
      {to ? (
        <Link to={to} className={baseClass}>
          {inner}
        </Link>
      ) : (
        <div className={baseClass}>{inner}</div>
      )}
    </motion.div>
  );
};

// ===========================================================================
// Sparkline — minimal SVG line chart for inside cards
// ===========================================================================

export const Sparkline: React.FC<{
  data: number[];
  stroke: string;
  className?: string;
}> = ({ data, stroke, className = "" }) => {
  // Hooks must run unconditionally — keep useId above the early return.
  const id = React.useId();
  if (!data.length) return null;
  const w = 100;
  const h = 30;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const step = data.length > 1 ? w / (data.length - 1) : 0;
  const pts = data.map((d, i) => {
    const x = i * step;
    const y = h - ((d - min) / span) * (h - 4) - 2;
    return `${x},${y}`;
  });
  const linePath = `M${pts.join(" L")}`;
  const fillPath = `${linePath} L${w},${h} L0,${h} Z`;
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className={className}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={`spark-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity={0.3} />
          <stop offset="100%" stopColor={stroke} stopOpacity={0.0} />
        </linearGradient>
      </defs>
      <path d={fillPath} fill={`url(#spark-${id})`} />
      <path
        d={linePath}
        fill="none"
        stroke={stroke}
        strokeWidth={1.6}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
};

// ===========================================================================
// Skeletons
// ===========================================================================

export const SkeletonStatCard: React.FC = () => (
  <div className="dash-card p-5">
    <div className="flex items-start justify-between mb-3">
      <div className="w-11 h-11 rounded-xl dash-skeleton" />
      <div className="w-12 h-4 dash-skeleton" />
    </div>
    <div className="w-24 h-3 dash-skeleton" />
    <div className="w-16 h-8 dash-skeleton mt-2" />
    <div className="w-full h-10 dash-skeleton mt-3" />
  </div>
);

export const SkeletonRow: React.FC<{ withAvatar?: boolean }> = ({
  withAvatar,
}) => (
  <div className="flex items-center gap-3 p-3">
    {withAvatar && (
      <div className="w-10 h-10 rounded-full dash-skeleton flex-shrink-0" />
    )}
    <div className="flex-1 space-y-2">
      <div className="h-3.5 dash-skeleton w-3/4" />
      <div className="h-3 dash-skeleton w-1/2" />
    </div>
  </div>
);

export const SkeletonChart: React.FC<{ className?: string }> = ({
  className = "h-64",
}) => (
  <div className={`dash-card p-5 ${className}`}>
    <div className="w-32 h-4 dash-skeleton mb-4" />
    <div className="w-full h-full dash-skeleton" />
  </div>
);

// ===========================================================================
// Section card
// ===========================================================================

export interface SectionCardProps {
  title: string;
  description?: string;
  action?: { label: string; to?: string; onClick?: () => void };
  icon?: LucideIcon;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}

export const SectionCard: React.FC<SectionCardProps> = ({
  title,
  description,
  action,
  icon: Icon,
  children,
  className = "",
  bodyClassName = "",
}) => (
  <motion.section
    variants={fadeUp}
    className={`dash-card overflow-hidden ${className}`}
  >
    <header className="flex items-start justify-between gap-4 px-5 py-4 border-b border-slate-100">
      <div className="min-w-0">
        <h2 className="dash-h2 flex items-center gap-2">
          {Icon && <Icon className="w-4 h-4 text-orange-500 flex-shrink-0" />}
          {title}
        </h2>
        {description && (
          <p className="text-xs text-slate-500 mt-0.5">{description}</p>
        )}
      </div>
      {action &&
        (action.to ? (
          <Link
            to={action.to}
            className="text-sm text-orange-600 hover:text-orange-700 font-semibold flex-shrink-0 flex items-center gap-1"
          >
            {action.label} <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        ) : (
          <button
            onClick={action.onClick}
            className="text-sm text-orange-600 hover:text-orange-700 font-semibold flex-shrink-0 flex items-center gap-1"
          >
            {action.label} <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        ))}
    </header>
    <div className={`p-5 ${bodyClassName}`}>{children}</div>
  </motion.section>
);

// ===========================================================================
// EmptyState
// ===========================================================================

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: { label: string; to?: string; onClick?: () => void };
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  action,
  className = "",
}) => (
  <div
    className={`flex flex-col items-center justify-center text-center py-10 px-6 ${className}`}
  >
    {Icon && (
      <motion.div
        initial={{ scale: 0.6, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 240, damping: 18 }}
        className="w-16 h-16 rounded-full si-gradient text-white flex items-center justify-center mb-3 ring-4 ring-orange-200/60 shadow-lg shadow-orange-500/25"
      >
        <Icon className="w-7 h-7" />
      </motion.div>
    )}
    <h3 className="font-semibold text-secondary-900 text-base">{title}</h3>
    {description && (
      <p className="text-sm text-slate-500 mt-1 max-w-md">{description}</p>
    )}
    {action &&
      (action.to ? (
        <Link to={action.to} className="dash-cta mt-4">
          {action.label}
        </Link>
      ) : (
        <button onClick={action.onClick} className="dash-cta mt-4">
          {action.label}
        </button>
      ))}
  </div>
);

// ===========================================================================
// ErrorState
// ===========================================================================

export interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Something went wrong",
  description = "We couldn't load this section. Try again or refresh the page.",
  onRetry,
  className = "",
}) => (
  <div
    className={`flex flex-col items-center justify-center text-center py-10 px-6 ${className}`}
  >
    <motion.div
      initial={{ scale: 0.6, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", stiffness: 240, damping: 18 }}
      className="w-14 h-14 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mb-3"
    >
      <AlertCircle className="w-7 h-7" />
    </motion.div>
    <h3 className="font-semibold text-secondary-900 text-base">{title}</h3>
    <p className="text-sm text-slate-500 mt-1 max-w-md">{description}</p>
    {onRetry && (
      <button onClick={onRetry} className="dash-cta-ghost mt-4">
        <RefreshCw className="w-4 h-4" /> Try again
      </button>
    )}
  </div>
);

// ===========================================================================
// Greeting — time-aware welcome
// ===========================================================================

export const Greeting: React.FC<{
  name?: string | null;
  subtitle?: string;
  chip?: string;
  cta?: { label: string; to?: string; onClick?: () => void };
  className?: string;
}> = ({ name, subtitle, chip, cta, className = "" }) => {
  const titles: Record<string, string> = {
    "INSTRUCTOR WORKSPACE": "Teaching overview",
    "MY LEARNING": "Your learning overview",
    "ADMIN WORKSPACE": "Platform overview",
    SUPERADMIN: "Platform control center",
    "SPOC WORKSPACE": "College overview",
    "MY PROFILE": "Your profile",
  };
  return (
    <div className={className}>
      <PageHeading
        eyebrow={chip}
        title={titles[chip || ""] || (name ? name : "Your workspace")}
        description={subtitle}
        actions={
          cta ? (
            cta.to ? (
              <Link to={cta.to} className="dash-cta">
                {cta.label}
              </Link>
            ) : (
              <button onClick={cta.onClick} className="dash-cta">
                {cta.label}
              </button>
            )
          ) : undefined
        }
      />
    </div>
  );
};

// ===========================================================================
// Spinner — small inline
// ===========================================================================

export const Spinner: React.FC<{ size?: "sm" | "md"; className?: string }> = ({
  size = "sm",
  className = "",
}) => {
  const px = size === "sm" ? "h-4 w-4" : "h-6 w-6";
  return (
    <div
      className={`inline-block animate-spin rounded-full ${px} border-2 border-orange-200 border-t-orange-500 ${className}`}
    />
  );
};
