import { PageLayout } from "@/components/design-system/PageLayout";
/**
 * SuperAdmin overview dashboard — rebuilt to match the admin panel's chart
 * style (recharts + brand-themed primitives) with real-time polling.
 *
 * What changed vs. the original minimal version:
 *  - Uses the shared StatCard/SectionCard/Skeleton system from primitives
 *  - recharts AreaChartCard / BarChartCard / DonutCard instead of a raw SVG
 *  - Real-time: polls every 30s + refreshes on tab visibility (silent,
 *    no skeleton flicker), matching the admin dashboard pattern
 *  - Mobile-first responsive grids
 *
 * Real-data-only policy: charts fall back to a zero baseline when there's
 * no data — never fabricated/random numbers.
 */
import React, { useEffect, useState } from "react";
import {
  Users,
  GraduationCap,
  ShieldCheck,
  BookOpen,
  FolderOpen,
  Activity,
  Timer,
  RefreshCw,
  ArrowUpRight,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { superadminApi, type SuperadminOverview } from "@/api/superadmin";
import {
  StatCard,
  SkeletonStatCard,
  SkeletonChart,
  SectionCard,
  Greeting,
  StaggerGrid,
  FadeUp,
  EmptyState,
  ErrorState,
} from "@/components/dashboard/primitives";
import {
  AreaChartCard,
  BarChartCard,
  DonutCard,
  ChartLegend,
  CHART_COLORS,
  CHART_PALETTE,
} from "@/components/dashboard/charts";

const REFRESH_MS = 30_000; // poll cadence — matches the admin dashboard

const fmtInt = (n: number | null | undefined): number =>
  n == null ? 0 : Number(n);
const fmtMoney = (n: number | null | undefined): string =>
  n == null
    ? "₹0"
    : `₹${Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

/** Short "Aug 3" label from an ISO date string. */
const dayLabel = (iso: string): string => {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
};

export const SuperAdminDashboard: React.FC = () => {
  // --- Data: react-query with real-time polling -------------------------
  // staleTime 0 so the interval always pulls fresh; the backend caches 5min
  // server-side so this stays cheap. refetchInterval + visibilitychange give
  // near-realtime updates without the skeleton flicker on every tick.
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
    dataUpdatedAt,
  } = useQuery<SuperadminOverview>({
    queryKey: ["superadmin", "overview"],
    queryFn: () => superadminApi.overview(),
    staleTime: 0,
    refetchInterval: REFRESH_MS,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });

  // A live "last updated" clock for the header, updated both by react-query
  // and by a 1s ticker so the seconds tick visibly.
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);
  const updatedAt = dataUpdatedAt ? new Date(dataUpdatedAt) : now;

  const d = data;
  const hasData = !!d;

  // --- Derived chart data ----------------------------------------------
  // Activity area chart: revenue + enrollments on a shared axis.
  const activitySeries = [
    { key: "revenue", label: "Revenue (₹)", color: CHART_COLORS.emerald },
    {
      key: "enrollments",
      label: "New enrollments",
      color: CHART_COLORS.orange,
    },
  ];
  const activityData = React.useMemo(() => {
    if (!d?.activity_trend?.length) return [];
    return d.activity_trend.map((p) => ({
      x: dayLabel(p.day),
      revenue: Math.round(p.revenue),
      enrollments: p.enrollments,
    }));
  }, [d?.activity_trend]);

  // Active-users bar chart (distinct visitors per day).
  const dauSeries = React.useMemo(() => {
    if (!d?.activity_trend?.length) return [];
    return d.activity_trend.map((p) => ({
      x: dayLabel(p.day),
      visitors: p.active_users,
    }));
  }, [d?.activity_trend]);

  // Role distribution donut.
  const roleSlices = d?.role_distribution ?? [];

  return (
    <PageLayout
      header={
        <FadeUp>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <Greeting
              name="Commander"
              chip="SUPERADMIN"
              subtitle="Platform-wide monitoring across students, instructors, admins and revenue."
              className="flex-1"
            />
            <div className="flex items-center gap-3 text-xs text-neutral-500">
              <span className="inline-flex items-center gap-1.5">
                <span
                  className={`h-2 w-2 rounded-full ${isFetching ? "animate-pulse bg-amber-500" : "bg-emerald-500"}`}
                />
                {isFetching ? "Syncing…" : "Live"}
              </span>
              <span className="hidden sm:inline">
                Updated{" "}
                {updatedAt.toLocaleTimeString(undefined, {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
                {d?.cached ? " · (server cached)" : ""}
              </span>
              <button
                onClick={() => refetch()}
                disabled={isFetching}
                className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-300 bg-white px-2.5 py-1.5 font-medium text-neutral-700 shadow-sm hover:bg-neutral-50 disabled:opacity-50"
              >
                <RefreshCw
                  className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`}
                />
              </button>
            </div>
          </div>
        </FadeUp>
      }
    >
      {isError ? (
        <ErrorState
          title="Couldn't load overview"
          description={(error as Error)?.message ?? "Unknown error"}
          onRetry={() => refetch()}
        />
      ) : null}
      <StaggerGrid className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
        {isLoading || !hasData ? (
          Array.from({ length: 8 }).map((_, i) => <SkeletonStatCard key={i} />)
        ) : (
          <>
            <StatCard
              title="Students"
              value={fmtInt(d!.totals.students)}
              icon={Users}
              tone="orange"
              to="/superadmin/students"
            />
            <StatCard
              title="Instructors"
              value={fmtInt(d!.totals.instructors)}
              icon={GraduationCap}
              tone="purple"
              to="/superadmin/instructors"
            />
            <StatCard
              title="Admins"
              value={fmtInt(d!.totals.admins)}
              icon={ShieldCheck}
              tone="navy"
              to="/superadmin/admins"
            />
            <StatCard
              title="Courses"
              value={fmtInt(d!.totals.courses)}
              icon={BookOpen}
              tone="sky"
            />
            <StatCard
              title="Enrollments"
              value={fmtInt(d!.totals.enrollments)}
              icon={FolderOpen}
              tone="emerald"
            />
            <StatCard
              title="Daily active"
              value={fmtInt(d!.dau)}
              icon={Activity}
              tone="amber"
              delta="Last 24h visitors"
            />
            <StatCard
              title="Weekly active"
              value={fmtInt(d!.wau)}
              icon={Users}
              tone="slate"
              delta="Last 7d visitors"
            />
            <StatCard
              title="Active sessions"
              value={fmtInt(d!.open_impersonation_sessions)}
              icon={Timer}
              tone="rose"
              to="/superadmin/audit"
              delta={
                d!.stale_impersonation_sessions
                  ? `${fmtInt(d!.stale_impersonation_sessions)} never closed`
                  : "Live impersonations"
              }
            />
          </>
        )}
      </StaggerGrid>
      <StaggerGrid className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Activity trend — spans 2 cols on large screens */}
        <div className="lg:col-span-2">
          {isLoading || !hasData ? (
            <SkeletonChart className="h-[300px]" />
          ) : activityData.length === 0 ? (
            <SectionCard
              title="Revenue & enrollments"
              icon={Activity}
              description="Last 30 days"
            >
              <EmptyState
                title="No activity yet"
                description="Revenue and enrollment data will appear here once orders are placed."
              />
            </SectionCard>
          ) : (
            <SectionCard
              title="Revenue & enrollments"
              icon={Activity}
              description={`${activityData.length}-day trend · live`}
              action={{ label: "Audit", to: "/superadmin/audit" }}
            >
              <div className="h-[280px] w-full">
                <AreaChartCard
                  data={activityData}
                  series={activitySeries}
                  xKey="x"
                  height={280}
                />
              </div>
            </SectionCard>
          )}
        </div>

        {/* Role distribution donut */}
        <div>
          {isLoading || !hasData ? (
            <SkeletonChart className="h-[300px]" />
          ) : roleSlices.length === 0 ? (
            <SectionCard title="Users by role" icon={Users}>
              <EmptyState
                title="No users yet"
                description="Role distribution appears once users register."
              />
            </SectionCard>
          ) : (
            <SectionCard
              title="Users by role"
              icon={Users}
              description="All registered accounts"
            >
              <div className="h-[200px] w-full">
                <DonutCard
                  data={roleSlices}
                  centerLabel="Users"
                  centerValue={roleSlices
                    .reduce((s, r) => s + r.value, 0)
                    .toLocaleString("en-IN")}
                  height={200}
                />
              </div>
              <div className="mt-3">
                <ChartLegend
                  items={roleSlices.map((r, i) => ({
                    name: r.name,
                    value: r.value,
                    color: CHART_PALETTE[i % CHART_PALETTE.length],
                  }))}
                />
              </div>
            </SectionCard>
          )}
        </div>
      </StaggerGrid>
      <StaggerGrid className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        <div className="lg:col-span-2">
          {isLoading || !hasData ? (
            <SkeletonChart className="h-[260px]" />
          ) : dauSeries.length === 0 ? (
            <SectionCard title="Daily active visitors" icon={Activity}>
              <EmptyState
                title="No traffic yet"
                description="Visitor counts appear once pages are viewed."
              />
            </SectionCard>
          ) : (
            <SectionCard
              title="Daily active visitors"
              icon={Activity}
              description="Distinct users + anonymous visitors"
            >
              <div className="h-[240px] w-full">
                <BarChartCard
                  data={dauSeries}
                  series={[
                    {
                      key: "visitors",
                      label: "Visitors",
                      color: CHART_COLORS.sky,
                    },
                  ]}
                  xKey="x"
                  height={240}
                />
              </div>
            </SectionCard>
          )}
        </div>

        {/* Revenue headline card */}
        <div>
          <SectionCard
            title="Revenue (30d)"
            icon={ArrowUpRight}
            description="Completed orders"
          >
            {isLoading || !hasData ? (
              <div className="h-[140px] animate-pulse rounded-xl bg-neutral-100" />
            ) : (
              <div className="flex flex-col gap-2 p-1">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                    Total
                  </p>
                  <p className="text-3xl font-bold text-emerald-600">
                    {fmtMoney(
                      d!.revenue_trend.reduce((s, p) => s + p.revenue, 0),
                    )}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <p className="text-xs text-neutral-500">Orders</p>
                    <p className="font-semibold text-neutral-900">
                      {d!.revenue_trend
                        .reduce((s, p) => s + p.orders, 0)
                        .toLocaleString("en-IN")}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500">Avg / order</p>
                    <p className="font-semibold text-neutral-900">
                      {(() => {
                        const tot = d!.revenue_trend.reduce(
                          (s, p) => s + p.revenue,
                          0,
                        );
                        const cnt = d!.revenue_trend.reduce(
                          (s, p) => s + p.orders,
                          0,
                        );
                        return cnt ? fmtMoney(tot / cnt) : "—";
                      })()}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </SectionCard>
        </div>
      </StaggerGrid>
      <p className="text-center text-xs text-neutral-400">
        {hasData && d!.generated_at
          ? `Generated ${new Date(d!.generated_at).toLocaleString()}${d!.cached ? " · served from cache" : ""}`
          : null}
      </p>
    </PageLayout>
  );
};

export default SuperAdminDashboard;
