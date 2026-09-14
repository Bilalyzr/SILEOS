import { PageLayout } from "@/components/design-system/PageLayout";
/**
 * Admin dashboard — v3 redesign matching the public-hero brand language.
 *
 * Layout:
 *   - Greeting + chip + CTA (gradient orange button to /admin/internships)
 *   - 4 stat cards with sparklines + animated counters
 *   - Revenue area chart (30 days)
 *   - Donut: user roles distribution
 *   - Top courses + recent enrollments side-by-side
 *   - Quick actions grid
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen,
  Users,
  IndianRupee,
  TrendingUp,
  UserPlus,
  Award,
  Clock,
  Briefcase,
  Inbox,
  BarChart3,
  ArrowUpRight,
  Activity,
  Sparkles,
  AlertTriangle,
} from "lucide-react";
import {
  dashboardAPI,
  AdminDashboardData,
  RevenuePoint,
  type AiProviderUsageReport,
} from "@/api/dashboard";
import { useAuth } from "@/hooks/use-auth";
import {
  StatCard,
  SkeletonStatCard,
  SkeletonRow,
  SkeletonChart,
  EmptyState,
  ErrorState,
  SectionCard,
  Greeting,
  StaggerGrid,
  FadeUp,
} from "@/components/dashboard/primitives";
import {
  AreaChartCard,
  DonutCard,
  ChartLegend,
  lastNDayLabels,
  CHART_COLORS,
} from "@/components/dashboard/charts";

const inr = (n: number) => `₹${n.toLocaleString("en-IN")}`;

// Poll the revenue series this often so the chart tracks new orders in near-realtime.
const REVENUE_REFRESH_MS = 30_000;

// Revenue chart period filter (Week / Month / Quarter / Year). The values map
// 1:1 to what /admin/revenue-timeseries accepts.
type RevPeriod = "7d" | "30d" | "90d" | "1y";
const REV_PERIODS: { value: RevPeriod; label: string; days: number }[] = [
  { value: "7d", label: "Week", days: 7 },
  { value: "30d", label: "Month", days: 30 },
  { value: "90d", label: "Quarter", days: 90 },
  { value: "1y", label: "Year", days: 365 },
];
const AI_USAGE_WINDOW_DAYS = 14;

export const AdminDashboard: React.FC = () => {
  const { fullName } = useAuth();
  const [data, setData] = useState<AdminDashboardData | null>(null);
  const [revPoints, setRevPoints] = useState<RevenuePoint[] | null>(null);
  const [revPeriod, setRevPeriod] = useState<RevPeriod>("30d");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revUpdatedAt, setRevUpdatedAt] = useState<Date | null>(null);
  const [aiUsage, setAiUsage] = useState<AiProviderUsageReport | null>(null);
  const [aiUsageLoading, setAiUsageLoading] = useState(true);

  const periodDays = REV_PERIODS.find((p) => p.value === revPeriod)?.days ?? 30;

  // Pull the real daily net-cash series by business pillar. Silent: used for both
  // the first load and the background poll, so refreshing never flickers the
  // chart or shows a skeleton.
  const loadRevenue = useCallback(async () => {
    try {
      const ts = await dashboardAPI.getAdminRevenueTimeseries(revPeriod);
      setRevPoints(ts.points ?? []);
      setRevUpdatedAt(new Date());
    } catch {
      // On a transient failure keep whatever we already have rather than
      // blanking the chart; never substitute fabricated numbers.
      setRevPoints((prev) => prev ?? []);
    }
  }, [revPeriod]);

  const loadAiUsage = useCallback(async () => {
    setAiUsageLoading(true);
    try {
      const report = await dashboardAPI.getAiProviderUsage(AI_USAGE_WINDOW_DAYS);
      setAiUsage(report);
    } catch {
      setAiUsage((prev) => prev ?? null);
    } finally {
      setAiUsageLoading(false);
    }
  }, []);

  const fetchDashboard = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      setData(await dashboardAPI.getAdminDashboard());
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err.message ||
          "Failed to load dashboard",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    loadAiUsage();
  }, [fetchDashboard, loadAiUsage]);

  // Load the revenue series on mount and whenever the period filter changes.
  useEffect(() => {
    loadRevenue();
  }, [loadRevenue]);

  // Near-realtime: re-pull revenue (and the stat cards) on an interval and
  // whenever the admin switches back to the tab — without the loading skeleton.
  useEffect(() => {
    const refresh = () => {
      loadRevenue();
      dashboardAPI
        .getAdminDashboard()
        .then(setData)
        .catch(() => {});
      loadAiUsage();
    };
    const id = window.setInterval(refresh, REVENUE_REFRESH_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") refresh();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [loadRevenue, loadAiUsage]);

  // ----- Revenue chart: real daily series from /admin/revenue-timeseries,
  // allocated through the same reporting contract as the Control Center.
  // When there are genuinely no orders yet (or a brief API hiccup) we draw a
  // true ZERO line across the last 30 real dates — never a mock/random curve. -----
  const revRow = React.useMemo(() => {
    if (revPoints && revPoints.length > 0) {
      return revPoints.map((p) => ({
        x: p.label,
        meiporul: p.meiporul ?? 0,
        seyappaduporul: p.seyappaduporul ?? 0,
        utporul: p.utporul ?? 0,
        unallocated: p.unallocated ?? 0,
      }));
    }
    return lastNDayLabels(periodDays).map((label) => ({
      x: label,
      meiporul: 0,
      seyappaduporul: 0,
      utporul: 0,
      unallocated: 0,
    }));
  }, [revPoints, periodDays]);
  // Real API values; default to 0 when a stat is absent.
  const totalCourses = Number(data?.course_stats?.total_courses ?? 0);
  const totalStudents = Number(data?.user_stats?.students ?? 0);
  const studentsUnv = Number(data?.user_stats?.students_unverified ?? 0);
  const newUsers30 = Number(data?.user_stats?.new_users_count ?? 0);
  const monthlyRevenue = Number(data?.revenue_stats?.monthly_revenue ?? 0);
  // Falls back to the current month's name if the API didn't send a label.
  const monthlyRevenueLabel =
    data?.revenue_stats?.monthly_revenue_label ||
    new Date().toLocaleString("en-IN", { month: "long", year: "numeric" });
  const totalEnrollments = Number(
    data?.enrollment_stats?.total_enrollments ?? 0,
  );
  const newEnrol30 = Number(data?.enrollment_stats?.new_enrollments_count ?? 0);

  const roleSlices = [
    { name: "Students", value: totalStudents, color: CHART_COLORS.orange },
    {
      name: "Instructors",
      value: Number(data?.user_stats?.instructors ?? 0),
      color: CHART_COLORS.sky,
    },
    {
      name: "Companies",
      value: Number(data?.user_stats?.companies ?? 0),
      color: CHART_COLORS.purple,
    },
    {
      name: "SPOCs",
      value: Number(data?.user_stats?.spocs ?? 0),
      color: CHART_COLORS.emerald,
    },
  ];
  // No sparklines on the stat cards — they were genTrend() random walks with
  // no relation to the platform's actual history, so a flat week still drew a
  // lively line. The real revenue series is the chart below.

  // Real data only — when the API omits these, the cards render their empty
  // states (handled below) rather than fabricated sample rows.
  const recentCourses = data?.course_stats?.recent_courses ?? [];
  const recentEnrollments = data?.enrollment_stats?.recent_enrollments ?? [];

  const aiUsageSummary = {
    attempts: aiUsage?.total_attempts ?? 0,
    successRate: aiUsage?.success_rate ?? 0,
    failures: aiUsage?.total_failures ?? 0,
    totalProviders: aiUsage?.by_provider?.length ?? 0,
    recentFailures: aiUsage?.recent_failures?.length ?? 0,
  };

  const topAiProvider = aiUsage?.by_provider?.[0] ?? null;

  return (
    <PageLayout
      header={
        <div className="flex items-start justify-between gap-4 mb-6">
          <Greeting
            name={fullName}
            chip="ADMIN WORKSPACE"
            subtitle="Here's a snapshot of platform activity. Keep an eye on revenue, enrollments, and pending approvals."
            cta={{ label: "Review requests", to: "/admin/internship-requests" }}
            className="flex-1"
          />
        </div>
      }
    >
      {error && (
        <FadeUp>
          <ErrorState
            title="Couldn't load dashboard data"
            description={error}
            onRetry={fetchDashboard}
            className="dash-card mb-6"
          />
        </FadeUp>
      )}
      <StaggerGrid className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {isLoading ? (
          <>
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
          </>
        ) : (
          <>
            <StatCard
              title="Total Courses"
              value={totalCourses}
              icon={BookOpen}
              tone="orange"
              to="/admin/courses"
            />
            <StatCard
              title="Active Students"
              value={totalStudents}
              icon={Users}
              tone="sky"
              to="/admin/students"
              delta={
                studentsUnv ? `${studentsUnv} unverified` : `+${newUsers30}`
              }
              deltaDirection={studentsUnv ? "flat" : "up"}
            />
            <StatCard
              title="Monthly Revenue"
              value={monthlyRevenue}
              format={inr}
              icon={IndianRupee}
              tone="purple"
              to="/admin/orders"
              delta={monthlyRevenueLabel}
              deltaDirection="flat"
            />
            <StatCard
              title="Active Enrollments"
              value={totalEnrollments}
              icon={TrendingUp}
              tone="emerald"
              to="/admin/enrollments"
              delta={`+${newEnrol30}`}
            />
          </>
        )}
      </StaggerGrid>
      <StaggerGrid className="grid grid-cols-1">
        <SectionCard title="Quick actions" icon={Award}>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <QuickAction
              to="/admin/students"
              icon={UserPlus}
              tone="emerald"
              label="Students"
              sub="Manage roster"
            />
            <QuickAction
              to="/admin/internships"
              icon={Briefcase}
              tone="orange"
              label="Internships"
              sub="Programs & rosters"
            />
            <QuickAction
              to="/admin/internship-requests"
              icon={Inbox}
              tone="amber"
              label="Requests"
              sub="Approve/reject"
            />
            <QuickAction
              to="/admin/analytics"
              icon={BarChart3}
              tone="purple"
              label="Analytics"
              sub="Performance"
            />
            <QuickAction
              to="/admin/ai-providers"
              icon={Sparkles}
              tone="amber"
              label="AI vault"
              sub="Providers & health"
            />
          </div>
        </SectionCard>
      </StaggerGrid>
      <StaggerGrid className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <SectionCard
          title={`Revenue, last ${periodDays} days`}
          description={
            revUpdatedAt
              ? `Live net cash by pillar · updated ${revUpdatedAt.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}`
              : "Daily consolidated net cash across all business pillars"
          }
          icon={Activity}
          action={{ label: "View orders", to: "/admin/orders" }}
          className="lg:col-span-2"
          bodyClassName="px-2 pb-3"
        >
          {/* Period filter: Week / Month / Quarter / Year */}
          <div className="flex items-center gap-1 px-2 pb-2">
            {REV_PERIODS.map((p) => (
              <button
                key={p.value}
                type="button"
                onClick={() => setRevPeriod(p.value)}
                aria-pressed={revPeriod === p.value}
                className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                  revPeriod === p.value
                    ? "bg-orange-500 text-white shadow-sm"
                    : "text-slate-500 hover:bg-slate-100"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          {isLoading ? (
            <SkeletonChart />
          ) : (
            <AreaChartCard
              data={revRow}
              series={[
                {
                  key: "meiporul",
                  label: "Meiporul (₹)",
                  color: CHART_COLORS.orange,
                },
                {
                  key: "seyappaduporul",
                  label: "Seyappaduporul (₹)",
                  color: CHART_COLORS.sky,
                },
                {
                  key: "utporul",
                  label: "Utporul (₹)",
                  color: CHART_COLORS.emerald,
                },
                {
                  key: "unallocated",
                  label: "Needs classification (₹)",
                  color: CHART_COLORS.slate,
                },
              ]}
              xKey="x"
              height={260}
              stacked
            />
          )}
        </SectionCard>
      </StaggerGrid>
      <StaggerGrid className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <SectionCard
          title={`AI routing health (${AI_USAGE_WINDOW_DAYS}d)`}
          description="Live provider reliability for AI-generated tutoring, quizzes, and suggestions."
          icon={Activity}
          action={{ label: "Open vault", to: "/admin/ai-providers" }}
        >
          {aiUsageLoading ? (
            <SkeletonChart />
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-2xl font-semibold text-slate-900">
                    {aiUsageSummary.attempts}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">Attempted calls</p>
                </div>
                <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
                  <p className="text-2xl font-semibold text-emerald-700">
                    {aiUsageSummary.successRate}%
                  </p>
                  <p className="mt-1 text-xs text-emerald-700">Success rate</p>
                </div>
                <div className="rounded-xl border border-rose-100 bg-rose-50 p-4">
                  <p className="text-2xl font-semibold text-rose-700">
                    {aiUsageSummary.failures}
                  </p>
                  <p className="mt-1 text-xs text-rose-700">Failed calls</p>
                </div>
              </div>
              {aiUsageSummary.attempts > 0 ? (
                <>
                  <p className="text-sm text-slate-600">
                    Top provider in this window:{" "}
                    <span className="font-semibold text-slate-900">
                      {topAiProvider?.provider || "n/a"} · {topAiProvider?.model || "n/a"}
                    </span>{" "}
                    ({topAiProvider?.success_rate ?? 0}% success)
                  </p>
                  {aiUsageSummary.successRate < 95 ? (
                    <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Review failed provider attempts and rotate keys if needed.
                    </p>
                  ) : null}
                </>
              ) : (
                <p className="text-sm text-slate-500">
                  No attempts were recorded in the last {AI_USAGE_WINDOW_DAYS} days.
                </p>
              )}
              <div className="pt-1">
                <h4 className="text-sm font-semibold text-slate-700 mb-2">
                  Recent failures ({aiUsageSummary.recentFailures})
                </h4>
                <div className="space-y-2">
                  {(aiUsage?.recent_failures ?? []).slice(0, 4).map((failure) => (
                    <p
                      key={failure.id}
                      className="text-xs leading-5 rounded-lg bg-slate-50 border border-slate-200 p-2"
                    >
                      <span className="font-medium text-slate-700">
                        {failure.feature}
                      </span>{" "}
                      · {failure.provider} · {failure.model}
                      <span className="ml-2 text-slate-500">
                        {new Date(failure.created_at).toLocaleString("en-IN", {
                          hour: "2-digit",
                          minute: "2-digit",
                          day: "2-digit",
                          month: "short",
                        })}
                      </span>
                      <span className="block text-rose-700 mt-0.5">
                        {failure.error}
                      </span>
                    </p>
                  ))}
                  {(aiUsage?.recent_failures ?? []).length === 0 && (
                    <p className="text-sm text-slate-500">
                      No recent failures in this period.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </SectionCard>
        <SectionCard
          title="Users by role"
          description="Active accounts on the platform"
          icon={Sparkles}
        >
          {isLoading ? (
            <SkeletonChart />
          ) : (
            <>
              <DonutCard data={roleSlices} centerLabel="Users" height={200} />
              <ChartLegend items={roleSlices} className="mt-4" />
            </>
          )}
        </SectionCard>
      </StaggerGrid>
      <StaggerGrid className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <SectionCard
          title="Top performing courses"
          icon={BookOpen}
          action={{ label: "View all", to: "/admin/courses" }}
          bodyClassName="space-y-2"
        >
          {isLoading ? (
            <>
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
            </>
          ) : recentCourses.length === 0 ? (
            <EmptyState
              icon={BookOpen}
              title="No courses yet"
              description="Create your first course to start tracking performance."
              action={{ label: "Create course", to: "/admin/courses/new" }}
            />
          ) : (
            recentCourses.slice(0, 5).map((course) => (
              <div
                key={course.id}
                className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50/80 transition gap-3"
              >
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/admin/courses/${course.id}/edit`}
                    className="font-medium text-secondary-900 hover:text-orange-600 line-clamp-1"
                  >
                    {course.title}
                  </Link>
                  <div className="flex items-center flex-wrap gap-x-3 gap-y-1 mt-1 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <Users className="w-3 h-3" /> {course.students}
                    </span>
                    <span className="flex items-center gap-1">
                      <IndianRupee className="w-3 h-3" /> {course.revenue}
                    </span>
                    <span>⭐ {course.rating}</span>
                  </div>
                </div>
                <span
                  className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider flex-shrink-0 ${
                    course.status === "published"
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-slate-200 text-slate-700"
                  }`}
                >
                  {course.status}
                </span>
              </div>
            ))
          )}
        </SectionCard>

        <SectionCard
          title="Recent enrollments"
          icon={Inbox}
          action={{ label: "View all", to: "/admin/enrollments" }}
          bodyClassName="space-y-2"
        >
          {isLoading ? (
            <>
              <SkeletonRow withAvatar />
              <SkeletonRow withAvatar />
              <SkeletonRow withAvatar />
            </>
          ) : recentEnrollments.length === 0 ? (
            <EmptyState
              icon={Inbox}
              title="No enrollments yet"
              description="When students enroll in courses, you'll see them here."
            />
          ) : (
            recentEnrollments.slice(0, 5).map((enrollment, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50/80 transition gap-3"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center text-white font-semibold flex-shrink-0">
                    {enrollment.student.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium text-secondary-900 truncate">
                      {enrollment.student}
                    </p>
                    <p className="text-xs text-slate-500 truncate">
                      {enrollment.course}
                    </p>
                  </div>
                </div>
                <p className="text-xs text-slate-500 flex items-center gap-1 flex-shrink-0">
                  <Clock className="w-3 h-3" />
                  {enrollment.date}
                </p>
              </div>
            ))
          )}
        </SectionCard>
      </StaggerGrid>
    </PageLayout>
  );
};

const TONE_BORDERS = {
  emerald: "hover:border-emerald-300 hover:bg-emerald-50/50",
  orange: "hover:border-orange-300 hover:bg-orange-50/50",
  amber: "hover:border-amber-300 hover:bg-amber-50/50",
  purple: "hover:border-purple-300 hover:bg-purple-50/50",
} as const;
const TONE_ICON = {
  emerald: "text-emerald-600",
  orange: "text-orange-600",
  amber: "text-amber-600",
  purple: "text-purple-600",
} as const;

const QuickAction: React.FC<{
  to: string;
  icon: any;
  tone: keyof typeof TONE_BORDERS;
  label: string;
  sub: string;
}> = ({ to, icon: Icon, tone, label, sub }) => (
  <Link
    to={to}
    className={`flex items-center gap-3 p-4 border-2 border-dashed border-slate-200 rounded-xl transition group ${TONE_BORDERS[tone]}`}
  >
    <Icon
      className={`w-7 h-7 ${TONE_ICON[tone]} group-hover:scale-110 transition`}
    />
    <div className="min-w-0 flex-1">
      <p className="font-medium text-secondary-900">{label}</p>
      <p className="text-xs text-slate-500 truncate">{sub}</p>
    </div>
    <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-slate-700 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition" />
  </Link>
);
