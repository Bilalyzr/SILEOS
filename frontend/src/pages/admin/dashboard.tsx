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
} from "lucide-react";
import {
  dashboardAPI,
  AdminDashboardData,
  RevenuePoint,
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

export const AdminDashboard: React.FC = () => {
  const { fullName } = useAuth();
  const [data, setData] = useState<AdminDashboardData | null>(null);
  const [revPoints, setRevPoints] = useState<RevenuePoint[] | null>(null);
  const [revPeriod, setRevPeriod] = useState<RevPeriod>("30d");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revUpdatedAt, setRevUpdatedAt] = useState<Date | null>(null);

  const periodDays = REV_PERIODS.find((p) => p.value === revPeriod)?.days ?? 30;

  // Pull the REAL daily revenue series (completed course payments + internship
  // vouchers, bucketed by the day each order was paid). Silent: used for both
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
  }, [fetchDashboard]);

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
  }, [loadRevenue]);

  // ----- Revenue chart: real daily series from /admin/revenue-timeseries,
  // allocated by source (Courses = COMPLETED orders, Internships = vouchers).
  // When there are genuinely no orders yet (or a brief API hiccup) we draw a
  // true ZERO line across the last 30 real dates — never a mock/random curve. -----
  const revRow = React.useMemo(() => {
    if (revPoints && revPoints.length > 0) {
      return revPoints.map((p) => ({
        x: p.label,
        courses: p.courses ?? 0,
        internships: p.internships ?? 0,
      }));
    }
    return lastNDayLabels(periodDays).map((label) => ({
      x: label,
      courses: 0,
      internships: 0,
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
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
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
          </div>
        </SectionCard>
      </StaggerGrid>
      <StaggerGrid className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <SectionCard
          title={`Revenue, last ${periodDays} days`}
          description={
            revUpdatedAt
              ? `Live · course + internship orders · updated ${revUpdatedAt.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}`
              : "Daily revenue trend across all courses and internships"
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
                  key: "courses",
                  label: "Courses (₹)",
                  color: CHART_COLORS.orange,
                },
                {
                  key: "internships",
                  label: "Internships (₹)",
                  color: CHART_COLORS.sky,
                },
              ]}
              xKey="x"
              height={260}
              stacked
            />
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
