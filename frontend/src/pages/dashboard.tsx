import { GuardianRequests } from "@/components/institutions/GuardianRequests";
import { PageLayout } from "@/components/design-system/PageLayout";
/**
 * Student dashboard — v3 redesign matching the public hero brand.
 *
 * Layout:
 *   - Greeting + chip + CTA (browse courses)
 *   - 4 stat cards: enrolled / completed / hours / certificates
 *   - Learning hours area chart (last 8 weeks)
 *   - Course progress donut
 *   - Continue Learning grid
 *   - Completed courses + InternshipEligibilityWidget
 */
import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  BookOpen,
  Clock,
  Award,
  Star,
  Play,
  GraduationCap,
  Target,
  Briefcase,
  Building2,
  CalendarCheck,
  Trophy,
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/hooks/use-auth";
import { dashboardAPI, StudentDashboardData } from "@/api/dashboard";
import { InternshipEligibilityWidget } from "@/components/candidate/InternshipEligibilityWidget";
import { StudentInternshipSummary } from "@/components/dashboard/StudentInternshipSummary";
import { MembershipCard } from "@/components/dashboard/MembershipCard";
import {
  StatCard,
  SkeletonStatCard,
  SkeletonChart,
  EmptyState,
  ErrorState,
  SectionCard,
  Greeting,
  StaggerGrid,
  FadeUp,
} from "@/components/dashboard/primitives";
import {
  DonutCard,
  ChartLegend,
  CHART_COLORS,
} from "@/components/dashboard/charts";
import { XPLevelCard } from "@/components/gamification/XPLevelCard";
import { ContinueLearning } from "@/components/dashboard/ContinueLearning";
import { StudentLiveClasses } from '@/components/live/StudentLiveClasses';
import { StreakCard } from "@/components/gamification/StreakCard";
import { BadgeGrid } from "@/components/gamification/BadgeGrid";
import { AwardToaster } from "@/components/gamification/AwardToaster";
import {
  gamificationAPI,
  type GamificationMeResponse,
} from "@/api/gamification";

export const DashboardPage = () => {
  const navigate = useNavigate();
  const { fullName } = useAuth();
  const [data, setData] = React.useState<StudentDashboardData | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [gamification, setGamification] =
    React.useState<GamificationMeResponse | null>(null);

  const fetchDashboard = React.useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      setData(await dashboardAPI.getStudentDashboard());
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

  React.useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  React.useEffect(() => {
    // Gamification widgets degrade gracefully — a failure here never blocks
    // the rest of the dashboard (mirrors the backend's own best-effort
    // award() contract).
    gamificationAPI
      .getMe()
      .then(setGamification)
      .catch(() => {});
  }, []);

  const enrolledCourses = React.useMemo(
    () => (data?.enrolled_courses ?? []) as any[],
    [data?.enrolled_courses],
  );
  const inProgress = enrolledCourses.filter((c: any) => c.progress < 100);
  const completed = enrolledCourses.filter((c: any) => c.progress === 100);

  // No sparklines on the stat cards. They used to be genTrend() output —
  // random walks with no relation to the student's activity — so a student
  // with zero hours still saw a lively line trending upward under the number.
  // The real time series lives behind /dashboard/analytics, which the
  // "Analytics report" link points at.
  const progressBuckets = React.useMemo(() => {
    const notStarted = enrolledCourses.filter((c) => c.progress === 0).length;
    const lessHalf = enrolledCourses.filter(
      (c) => c.progress > 0 && c.progress < 50,
    ).length;
    const moreHalf = enrolledCourses.filter(
      (c) => c.progress >= 50 && c.progress < 100,
    ).length;
    const done = completed.length;
    return [
      { name: "Not started", value: notStarted, color: CHART_COLORS.slate },
      { name: "In progress", value: lessHalf, color: CHART_COLORS.amber },
      { name: "Almost done", value: moreHalf, color: CHART_COLORS.sky },
      { name: "Completed", value: done, color: CHART_COLORS.emerald },
    ];
  }, [enrolledCourses, completed.length]);

  return (
    <PageLayout
      header={
        <Greeting
          name={fullName}
          chip="MY LEARNING"
          subtitle="Continue your learning journey and achieve your goals."
          cta={{ label: "Browse Courses", to: "/courses" }}
          className="mb-6"
        />
      }
    >
      <AwardToaster />
      {error && (
        <FadeUp>
          <ErrorState
            title="Couldn't load your dashboard"
            description={error}
            onRetry={fetchDashboard}
            className="dash-card mb-6"
          />
        </FadeUp>
      )}
      <StaggerGrid className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
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
              title="Enrolled Courses"
              value={Number(data?.stats?.enrolled_courses ?? 0)}
              icon={BookOpen}
              tone="orange"
            />
            <StatCard
              title="Completed"
              value={Number(data?.stats?.completed_courses ?? 0)}
              icon={Award}
              tone="emerald"
            />
            <StatCard
              title="Total Hours"
              value={Number(data?.stats?.total_hours ?? 0)}
              icon={Clock}
              tone="sky"
            />
            <StatCard
              title="Certificates"
              value={Number(data?.stats?.certificates ?? 0)}
              icon={GraduationCap}
              tone="purple"
              to="/dashboard/analytics"
            />
          </>
        )}
      </StaggerGrid>
      <ContinueLearning />
      <StudentLiveClasses />
      <StaggerGrid className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <SectionCard
          title="Continue learning"
          description={
            inProgress.length > 0
              ? `${inProgress.length} course${inProgress.length === 1 ? "" : "s"} in progress`
              : undefined
          }
          icon={Play}
          className="lg:col-span-2"
          action={
            enrolledCourses.length > 0
              ? { label: "My courses", to: "/my-courses" }
              : undefined
          }
          bodyClassName="space-y-3"
        >
          {isLoading ? (
            <div className="space-y-3">
              <div className="h-24 dash-skeleton" />
              <div className="h-24 dash-skeleton" />
            </div>
          ) : inProgress.length === 0 ? (
            <EmptyState
              icon={BookOpen}
              title="No courses in progress"
              description="Start a course to see it here."
              action={{ label: "Browse courses", to: "/courses" }}
            />
          ) : (
            inProgress.slice(0, 4).map((course) => (
              <div
                key={course.id}
                className="flex gap-3 sm:gap-4 p-3 sm:p-4 rounded-xl border border-slate-200 hover:border-orange-200 hover:shadow-md transition"
              >
                <img
                  src={course.thumbnail}
                  alt={course.title}
                  className="w-20 h-14 sm:w-24 sm:h-16 object-cover rounded-lg flex-shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-secondary-900 truncate">
                    {course.title}
                  </h3>
                  <p className="text-xs text-slate-500">
                    by {course.instructor}
                  </p>
                  <div className="mt-2 space-y-1">
                    <Progress value={course.progress} className="h-1.5" />
                    <div className="flex justify-between text-[11px] text-slate-500">
                      <span>
                        {course.completedLessons}/{course.totalLessons} lessons
                      </span>
                      <span className="font-semibold text-orange-600">
                        {course.progress}%
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex flex-col justify-between items-end flex-shrink-0">
                  <span className="text-xs flex items-center gap-1 text-slate-600">
                    <Star className="w-3 h-3 text-amber-400 fill-current" />{" "}
                    {course.rating}
                  </span>
                  <Link
                    to={`/courses/${(course as any).slug || (course as any).post_name || course.id}`}
                    className="dash-cta text-xs px-3 py-1.5"
                  >
                    Continue
                  </Link>
                </div>
              </div>
            ))
          )}
        </SectionCard>

        <div className="space-y-6">
          <MembershipCard />
          <InternshipEligibilityWidget />
        </div>
      </StaggerGrid>
      <StaggerGrid className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* "Learning rhythm" (weekly hours/lessons) chart removed — it rendered
            fabricated time-series. Re-add when the backend tracks real study
            time. "Course progress" below is computed from real enrollments. */}

        <SectionCard
          title="Course progress"
          description="Across all your enrollments"
          icon={Target}
          className="lg:col-span-2"
          action={{ label: "Analytics report", to: "/dashboard/analytics" }}
        >
          {isLoading ? (
            <SkeletonChart />
          ) : enrolledCourses.length === 0 ? (
            <EmptyState
              icon={BookOpen}
              title="No courses yet"
              action={{ label: "Browse courses", to: "/courses" }}
            />
          ) : (
            <>
              <DonutCard
                data={progressBuckets}
                centerLabel="Courses"
                height={200}
              />
              <ChartLegend items={progressBuckets} className="mt-4" />
            </>
          )}
        </SectionCard>
      </StaggerGrid>
      <StaggerGrid className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 mb-6">
        <XPLevelCard stats={gamification?.stats} />
        <StreakCard
          stats={gamification?.stats}
          recentEvents={gamification?.recent_events ?? []}
        />
      </StaggerGrid>
      {(completed.length > 0 || isLoading) && (
        <StaggerGrid className="grid grid-cols-1">
          <SectionCard
            title="Completed courses"
            description={
              completed.length > 0
                ? `${completed.length} earned ${completed.length === 1 ? "certificate" : "certificates"}`
                : undefined
            }
            icon={Award}
          >
            {isLoading ? (
              <div className="h-24 dash-skeleton" />
            ) : (
              <div className="grid md:grid-cols-2 gap-3">
                {completed.map((course) => (
                  <div
                    key={course.id}
                    className="flex gap-3 p-3 rounded-xl border border-emerald-100 bg-emerald-50/40"
                  >
                    <img
                      src={course.thumbnail}
                      alt={course.title}
                      className="w-16 h-12 object-cover rounded-md flex-shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-secondary-900 truncate text-sm">
                        {course.title}
                      </h3>
                      <p className="text-xs text-slate-500 truncate">
                        by {course.instructor}
                      </p>
                    </div>
                    <button
                      className="dash-cta-ghost text-[11px] px-2.5 py-1.5"
                      onClick={() => {
                        // Open the in-app certificate page (same design the
                        // user downloads), not the raw stored PDF file.
                        navigate(`/certificates/${course.id}`);
                      }}
                    >
                      <Award className="w-3 h-3" /> View
                    </button>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </StaggerGrid>
      )}
      {gamification && gamification.badges.length > 0 && (
        <StaggerGrid className="grid grid-cols-1 mb-6">
          <SectionCard
            title="Badges"
            description={`${gamification.badges.length} earned`}
            icon={Trophy}
            action={{ label: "Leaderboard", to: "/leaderboard" }}
          >
            <BadgeGrid badges={gamification.badges} />
          </SectionCard>
        </StaggerGrid>
      )}
      {data?.internships && data.internships.length > 0 && (
        <StaggerGrid className="grid grid-cols-1">
          <SectionCard
            title="My Internships"
            description={`${data.internships.length} internship${data.internships.length === 1 ? "" : "s"}`}
            icon={Briefcase}
            action={{
              label: "View all vouchers",
              to: "/dashboard/internship-inbox",
            }}
          >
            <StudentInternshipSummary internships={data.internships} />

            <div className="grid md:grid-cols-2 gap-3 mt-4">
              {data.internships.map((internship) => (
                <div
                  key={internship.id}
                  className="p-4 rounded-xl border border-slate-200 bg-slate-50/40"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-semibold text-secondary-900">
                        {internship.title}
                      </h3>
                      <p className="text-xs text-slate-500">
                        Code: {internship.voucher_code}
                      </p>
                    </div>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        internship.status === "redeemed"
                          ? "bg-green-100 text-green-800"
                          : "bg-yellow-100 text-yellow-800"
                      }`}
                    >
                      {internship.status}
                    </span>
                  </div>
                  <div className="space-y-1 text-xs text-slate-600">
                    {internship.redeemed_course_title && (
                      <p>Course: {internship.redeemed_course_title}</p>
                    )}
                    <div className="flex items-center gap-1">
                      <CalendarCheck className="w-3 h-3" />
                      <span>{internship.attendance_days} days attended</span>
                    </div>
                    {internship.hired_company && (
                      <div className="flex items-center gap-1">
                        <Building2 className="w-3 h-3" />
                        <span>{internship.hired_company}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>
        </StaggerGrid>
      )}
      <GuardianRequests />
    </PageLayout>
  );
};

export default DashboardPage;
