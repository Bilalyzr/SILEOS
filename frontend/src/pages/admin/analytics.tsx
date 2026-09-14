import { PageLayout, PageHeading } from "@/components/design-system/PageLayout";
import { useCallback } from "react";
import React, { useEffect, useState } from "react";
import {
  TrendingUp,
  Users,
  BookOpen,
  Award,
  BarChart3,
  IndianRupee,
  GraduationCap,
  Sparkles,
  ArrowUpRight,
  Activity,
  CheckCircle2,
  FileText,
} from "lucide-react";
import { AnalyticsHeatmaps } from "@/components/admin/heatmaps";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";
import { InternshipAnalyticsCharts } from "@/components/admin/InternshipAnalyticsCharts";
import { api } from "@/api/axios";

interface AdminStats {
  user_stats: {
    total_users: number;
    active_users: number;
    students: number;
    instructors: number;
    new_users_count: number;
  };
  course_stats: {
    total_courses: number;
    published_courses: number;
    draft_courses: number;
    avg_rating: number;
  };
  enrollment_stats: {
    total_enrollments: number;
    completed_enrollments: number;
    completion_rate: number;
    new_enrollments_count: number;
  };
  revenue_stats: {
    total_revenue: number;
    avg_course_price: number;
    revenue_period: number;
  };
}

const PERIODS: { value: string; label: string }[] = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
  { value: "1y", label: "1 year" },
];

// Accent palette
type Accent =
  | "orange"
  | "blue"
  | "emerald"
  | "purple"
  | "amber"
  | "rose"
  | "sky";

const ACCENT: Record<
  Accent,
  { bg: string; text: string; soft: string; ring: string }
> = {
  orange: {
    bg: "bg-orange-500",
    text: "text-orange-600",
    soft: "bg-orange-50",
    ring: "ring-orange-200",
  },
  blue: {
    bg: "bg-blue-600",
    text: "text-blue-600",
    soft: "bg-blue-50",
    ring: "ring-blue-200",
  },
  emerald: {
    bg: "bg-emerald-500",
    text: "text-emerald-600",
    soft: "bg-emerald-50",
    ring: "ring-emerald-200",
  },
  purple: {
    bg: "bg-purple-500",
    text: "text-purple-600",
    soft: "bg-purple-50",
    ring: "ring-purple-200",
  },
  amber: {
    bg: "bg-amber-500",
    text: "text-amber-600",
    soft: "bg-amber-50",
    ring: "ring-amber-200",
  },
  rose: {
    bg: "bg-rose-500",
    text: "text-rose-600",
    soft: "bg-rose-50",
    ring: "ring-rose-200",
  },
  sky: {
    bg: "bg-sky-500",
    text: "text-sky-600",
    soft: "bg-sky-50",
    ring: "ring-sky-200",
  },
};

export const AdminAnalytics: React.FC = () => {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("30d");

  const periodLabel = PERIODS.find((p) => p.value === period)?.label || period;

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      const r = await api.get(`/admin/stats?period=${period}`);
      const data = r.data;
      if (
        data &&
        data.user_stats &&
        data.course_stats &&
        data.enrollment_stats &&
        data.revenue_stats
      ) {
        setStats(data);
      } else {
        setStats(null);
      }
    } catch (error) {
      console.error("Error fetching stats:", error);
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [period]);
  useEffect(() => {
    fetchStats();
  }, [fetchStats, period]);

  if (loading || !stats) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-orange-500" />
          <p className="text-gray-600 text-sm">Loading analytics…</p>
        </div>
      </div>
    );
  }

  // ---- Derived metrics ----
  const u = stats.user_stats;
  const c = stats.course_stats;
  const e = stats.enrollment_stats;
  const r = stats.revenue_stats;

  const activePct =
    u.total_users > 0 ? Math.round((u.active_users / u.total_users) * 100) : 0;
  const studentPct =
    u.total_users > 0 ? Math.round((u.students / u.total_users) * 100) : 0;
  const publishedPct =
    c.total_courses > 0
      ? Math.round((c.published_courses / c.total_courses) * 100)
      : 0;

  return (
    <PageLayout
      header={
        <PageHeading
          eyebrow="Insights"
          title="Platform overview"
          description={`Users, courses, enrollments and revenue over the last ${periodLabel.toLowerCase()}.`}
          actions={
            <>
              <ExportImportPanel section="dashboard" />
              <div
                className="rd-filter-tabs"
                role="group"
                aria-label="Analytics period"
              >
                {PERIODS.map((p) => (
                  <button
                    key={p.value}
                    aria-pressed={period === p.value}
                    onClick={() => setPeriod(p.value)}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </>
          }
        />
      }
      className="rd-screen rd-screen-admin-analytics"
    >
      <SectionHeader
        title="User statistics"
        icon={<Users className="w-5 h-5" />}
        hint={`${u.new_users_count} new in last ${periodLabel.toLowerCase()}`}
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          accent="blue"
          icon={<Users className="w-5 h-5" />}
          label="Total users"
          value={u.total_users.toLocaleString()}
          sub={`+${u.new_users_count} this ${periodLabel.toLowerCase()}`}
        />
        <MetricCard
          accent="emerald"
          icon={<Activity className="w-5 h-5" />}
          label="Active users"
          value={u.active_users.toLocaleString()}
          sub={`${activePct}% of total`}
          progress={activePct}
        />
        <MetricCard
          accent="purple"
          icon={<GraduationCap className="w-5 h-5" />}
          label="Students"
          value={u.students.toLocaleString()}
          sub={`${studentPct}% of users`}
          progress={studentPct}
        />
        <MetricCard
          accent="orange"
          icon={<Award className="w-5 h-5" />}
          label="Instructors"
          value={u.instructors.toLocaleString()}
          sub={`${u.total_users > 0 ? Math.round((u.instructors / u.total_users) * 100) : 0}% of users`}
        />
      </div>
      <SectionHeader
        title="Course statistics"
        icon={<BookOpen className="w-5 h-5" />}
        hint={`${c.published_courses}/${c.total_courses} published`}
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          accent="blue"
          icon={<BookOpen className="w-5 h-5" />}
          label="Total courses"
          value={c.total_courses.toString()}
        />
        <MetricCard
          accent="emerald"
          icon={<CheckCircle2 className="w-5 h-5" />}
          label="Published"
          value={c.published_courses.toString()}
          sub={`${publishedPct}% of total`}
          progress={publishedPct}
        />
        <MetricCard
          accent="amber"
          icon={<FileText className="w-5 h-5" />}
          label="Drafts"
          value={c.draft_courses.toString()}
          sub={`${c.total_courses > 0 ? Math.round((c.draft_courses / c.total_courses) * 100) : 0}% of total`}
        />
        <MetricCard
          accent="orange"
          icon={<Sparkles className="w-5 h-5" />}
          label="Avg rating"
          value={`${c.avg_rating.toFixed(1)} / 5`}
          sub={renderStars(c.avg_rating)}
        />
      </div>
      <SectionHeader
        title="Enrollment statistics"
        icon={<TrendingUp className="w-5 h-5" />}
        hint={`${e.completion_rate.toFixed(1)}% completion rate`}
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          accent="blue"
          icon={<Users className="w-5 h-5" />}
          label="Total enrollments"
          value={e.total_enrollments.toLocaleString()}
          sub={`+${e.new_enrollments_count} this ${periodLabel.toLowerCase()}`}
        />
        <MetricCard
          accent="emerald"
          icon={<Award className="w-5 h-5" />}
          label="Completed"
          value={e.completed_enrollments.toLocaleString()}
        />
        <MetricCard
          accent="purple"
          icon={<BarChart3 className="w-5 h-5" />}
          label="Completion rate"
          value={`${e.completion_rate.toFixed(1)}%`}
          progress={Math.min(100, e.completion_rate)}
        />
        <MetricCard
          accent="orange"
          icon={<ArrowUpRight className="w-5 h-5" />}
          label="New this period"
          value={e.new_enrollments_count.toString()}
        />
      </div>
      <SectionHeader
        title="Revenue"
        icon={<IndianRupee className="w-5 h-5" />}
        hint={`₹${formatShort(r.revenue_period)} in last ${periodLabel.toLowerCase()}`}
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <BigMetric
          label="Total revenue"
          value={`₹${r.total_revenue.toLocaleString()}`}
          hint="All-time"
          icon={<IndianRupee className="w-6 h-6" />}
          accent="emerald"
        />
        <BigMetric
          label={`Revenue (${periodLabel})`}
          value={`₹${r.revenue_period.toLocaleString()}`}
          hint={
            r.total_revenue > 0
              ? `${((r.revenue_period / r.total_revenue) * 100).toFixed(1)}% of total`
              : ""
          }
          icon={<TrendingUp className="w-6 h-6" />}
          accent="blue"
        />
        <BigMetric
          label="Avg course price"
          value={`₹${Math.round(r.avg_course_price).toLocaleString()}`}
          hint="Across all courses"
          icon={<BookOpen className="w-6 h-6" />}
          accent="purple"
        />
      </div>
      <InternshipAnalyticsCharts period={period} />
      <AnalyticsHeatmaps />
    </PageLayout>
  );
};

// ============================================================================
// Subcomponents
// ============================================================================

const SectionHeader: React.FC<{
  title: string;
  icon: React.ReactNode;
  hint?: string;
}> = ({ title, icon, hint }) => (
  <div className="flex items-end justify-between border-b border-gray-200 pb-2 pt-2">
    <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
      <span className="text-gray-500">{icon}</span>
      {title}
    </h2>
    {hint && <p className="text-xs text-gray-500">{hint}</p>}
  </div>
);

const MetricCard: React.FC<{
  accent: Accent;
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: React.ReactNode;
  progress?: number;
}> = ({ accent, icon, label, value, sub, progress }) => {
  const a = ACCENT[accent];
  return (
    <div
      className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-gray-300 transition-all"
      data-glass="content"
    >
      <div className="flex items-start justify-between mb-3">
        <div
          className={`w-10 h-10 rounded-lg ${a.soft} ${a.text} flex items-center justify-center`}
        >
          {icon}
        </div>
      </div>
      <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">
        {label}
      </p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-2">{sub}</p>}
      {typeof progress === "number" && (
        <div className="mt-3 h-1.5 rounded-full bg-gray-100 overflow-hidden">
          <div
            className={`h-full ${a.bg} rounded-full transition-all`}
            style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          />
        </div>
      )}
    </div>
  );
};

const BigMetric: React.FC<{
  label: string;
  value: string;
  hint?: string;
  icon: React.ReactNode;
  accent: Accent;
}> = ({ label, value, hint, icon, accent }) => {
  const a = ACCENT[accent];
  return (
    <div
      className={`rounded-xl border border-gray-200 p-5 bg-gradient-to-br from-white to-${accent}-50/40 hover:shadow-md transition-all`}
    >
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">
          {label}
        </p>
        <div
          className={`w-11 h-11 rounded-lg ${a.soft} ${a.text} flex items-center justify-center`}
        >
          {icon}
        </div>
      </div>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
      {hint && <p className="text-xs text-gray-500 mt-2">{hint}</p>}
    </div>
  );
};

// ============================================================================
// Helpers
// ============================================================================

function formatShort(n: number): string {
  if (n >= 1_00_00_000) return `${(n / 1_00_00_000).toFixed(1)}Cr`;
  if (n >= 1_00_000) return `${(n / 1_00_000).toFixed(1)}L`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toLocaleString();
}

function renderStars(rating: number): React.ReactNode {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  return (
    <span className="inline-flex items-center gap-0.5 text-amber-500">
      {Array.from({ length: 5 }, (_, i) => {
        const filled = i < full || (i === full && half);
        return (
          <span key={i} className={filled ? "text-amber-500" : "text-gray-300"}>
            ★
          </span>
        );
      })}
      <span className="text-gray-500 ml-1 text-[11px]">
        ({rating.toFixed(1)})
      </span>
    </span>
  );
}
