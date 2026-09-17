import { PageLayout } from "@/components/design-system/PageLayout";
/**
 * Instructor dashboard — v3 redesign matching the public hero brand.
 *
 * Layout:
 *   - Greeting + chip + CTA (create new course)
 *   - Slim profile card (avatar, name, email, designation, edit links)
 *   - 5 stat cards with sparklines: Active courses / Students / Course purchases / Pending reviews / Avg rating
 *   - Pending assignments list with grade-now CTA
 *   - Courses overview list
 *
 * Note: the earnings section (nav link, page and dashboard charts) has been
 * removed from the instructor dashboard.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Users,
  BookOpen,
  Star,
  FileText,
  Clock,
  CheckCircle,
  ArrowUpRight,
  PenSquare,
  Edit3,
  Award,
  ShoppingCart,
} from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { dashboardAPI, InstructorDashboardData } from "@/api/dashboard";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";
import { ReviewQueueCard } from "@/components/flywheel/ReviewQueueCard";
import type { ExportSection } from "@/api/admin";
import { api } from "@/api/axios";
import { useAuth } from "@/hooks/use-auth";
import {
  StatCard,
  SkeletonStatCard,
  SkeletonRow,
  EmptyState,
  ErrorState,
  SectionCard,
  Greeting,
  StaggerGrid,
  FadeUp,
} from "@/components/dashboard/primitives";

interface AssignmentWithSubmissions {
  id: number;
  title: string;
  course_title: string;
  course_id: number;
  total_submissions: number;
  ungraded_submissions: number;
  graded_submissions: number;
  due_date?: string;
}

/**
 * The four instructor exports. Each panel renders one button, so without an
 * explicit label all four read "Export" and can't be told apart.
 */
const EXPORT_SECTIONS: {
  section: ExportSection;
  label: string;
  description: string;
}[] = [
  {
    section: "instructor_courses",
    label: "Export Courses",
    description: "Your courses with price, status and enrollment counts.",
  },
  {
    section: "instructor_students",
    label: "Export Students",
    description: "Students enrolled across your courses.",
  },
  {
    section: "instructor_quiz_results",
    label: "Export Quiz Results",
    description: "Quiz attempts and scores per student.",
  },
  {
    section: "instructor_assignment_results",
    label: "Export Assignment Results",
    description: "Assignment submissions and grades.",
  },
];

export function InstructorDashboard() {
  const navigate = useNavigate();
  const { user, fullName } = useAuth();
  const [data, setData] = useState<InstructorDashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assignments, setAssignments] = useState<AssignmentWithSubmissions[]>(
    [],
  );
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [profile, setProfile] = useState<any>(null);

  const fetchDashboard = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      setData(await dashboardAPI.getInstructorDashboard());
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
    api
      .get("/users/profile")
      .then((r) => setProfile(r.data))
      .catch(() => {});
  }, [fetchDashboard]);

  // Pull pending assignments — same logic as before
  useEffect(() => {
    const fetchAssignments = async () => {
      try {
        const courses = data?.courses || [];
        const assignmentsData: AssignmentWithSubmissions[] = [];
        for (const course of courses) {
          try {
            const res = await api.get(`/courses/${course.id}/assignments`);
            const courseAssignments = res.data.assignments || [];
            for (const assignment of courseAssignments) {
              try {
                const subRes = await api.get(
                  `/assignments/${assignment.id}/submissions`,
                );
                const submissions = subRes.data.submissions || [];
                assignmentsData.push({
                  id: assignment.id,
                  title: assignment.title,
                  course_title: course.title,
                  course_id: course.id,
                  total_submissions: submissions.length,
                  ungraded_submissions: submissions.filter(
                    (s: any) => s.status === "submitted",
                  ).length,
                  graded_submissions: submissions.filter(
                    (s: any) => s.status === "graded",
                  ).length,
                  due_date: assignment.dueDate,
                });
              } catch {}
            }
          } catch {}
        }
        setAssignments(assignmentsData);
      } finally {
        setLoadingAssignments(false);
      }
    };
    if (data?.courses?.length) fetchAssignments();
    else if (!isLoading) setLoadingAssignments(false);
  }, [data, isLoading]);

  // Derived stats from the real API.
  const courses = ((data as any)?.courses ?? []) as any[];
  const liveAssignments = (assignments ?? []) as any[];
  const totalCourses = Number(data?.stats?.total_courses ?? 0);
  const totalStudents = Number(data?.stats?.total_students ?? 0);
  // Total courses purchased by students across all of this instructor's courses
  // (every enrollment = one purchase). Falls back to summing per-course
  // enrollments if the backend hasn't sent the aggregate yet.
  const totalPurchases = Number(
    data?.stats?.total_purchases ??
      courses.reduce(
        (s: number, c: any) => s + (c.total_enrollments ?? c.students ?? 0),
        0,
      ),
  );
  const avgRating = Number(data?.stats?.average_rating ?? 0);
  const pendingTotal = liveAssignments.reduce(
    (s: number, a: any) => s + (a.ungraded_submissions || 0),
    0,
  );

  // No sparklines on the stat cards — they were genTrend() random walks, not
  // this instructor's history, so five cards drew five confident trends off
  // seeds. The deltas below are real counts.

  const sortedAssignments = [...liveAssignments].sort(
    (a: any, b: any) => b.ungraded_submissions - a.ungraded_submissions,
  );

  return (
    <PageLayout
      header={
        <Greeting
          name={fullName}
          chip="INSTRUCTOR WORKSPACE"
          subtitle="Manage your courses, review submissions, and track student outcomes."
          cta={{ label: "Create New Course", to: "/instructor/courses/create" }}
          className="mb-6"
        />
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
      <StaggerGrid className="grid grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4 mb-6">
        {isLoading ? (
          <>
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
          </>
        ) : (
          <>
            <StatCard
              title="Active Courses"
              value={totalCourses}
              icon={BookOpen}
              tone="orange"
            />
            <StatCard
              title="Total Students"
              value={totalStudents}
              icon={Users}
              tone="sky"
              delta="unique learners"
              deltaDirection="flat"
            />
            <StatCard
              title="Course Purchases"
              value={totalPurchases}
              icon={ShoppingCart}
              tone="emerald"
              delta="total enrollments"
              deltaDirection="flat"
            />
            <StatCard
              title="Pending Reviews"
              value={pendingTotal}
              icon={FileText}
              tone={pendingTotal > 0 ? "amber" : "emerald"}
              delta={`${liveAssignments.filter((a: any) => a.ungraded_submissions > 0).length} assignments`}
              deltaDirection={pendingTotal > 0 ? "up" : "flat"}
            />
            <StatCard
              title="Avg Rating"
              value={avgRating}
              format={(n) => n.toFixed(1)}
              icon={Star}
              tone="purple"
              delta={avgRating >= 4 ? "great" : "overall"}
              deltaDirection={avgRating >= 4 ? "up" : "flat"}
            />
          </>
        )}
      </StaggerGrid>
      <div className="rd-dashboard-grid">
        <div>
          <StaggerGrid className="grid grid-cols-1 mb-6">
            <SectionCard
              title="Pending grading"
              description={
                pendingTotal > 0
                  ? `${pendingTotal} submission${pendingTotal === 1 ? "" : "s"} waiting on you`
                  : "You're all caught up"
              }
              icon={FileText}
              bodyClassName="space-y-3"
            >
              {loadingAssignments ? (
                <>
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                </>
              ) : sortedAssignments.length === 0 ? (
                <EmptyState
                  icon={CheckCircle}
                  title="No assignments yet"
                  description="Create assignments in your courses to see them here."
                  action={{ label: "My courses", to: "/instructor/courses" }}
                />
              ) : (
                sortedAssignments.slice(0, 6).map((assignment) => (
                  <div
                    key={assignment.id}
                    className="group flex items-center justify-between p-4 rounded-xl border border-slate-200 hover:border-orange-200 hover:shadow-md transition gap-4"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <h3 className="font-semibold text-secondary-900 group-hover:text-orange-600 transition">
                          {assignment.title}
                        </h3>
                        {assignment.ungraded_submissions > 0 && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 uppercase tracking-wider">
                            {assignment.ungraded_submissions} pending
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 flex items-center gap-1.5">
                        <BookOpen className="w-3 h-3" />{" "}
                        {assignment.course_title}
                      </p>
                      <div className="flex items-center gap-x-4 gap-y-1 mt-2 text-xs text-slate-600 flex-wrap">
                        <span className="flex items-center gap-1">
                          <FileText className="w-3 h-3" />{" "}
                          {assignment.total_submissions} total
                        </span>
                        <span className="flex items-center gap-1 text-emerald-600">
                          <CheckCircle className="w-3 h-3" />{" "}
                          {assignment.graded_submissions} graded
                        </span>
                        {assignment.due_date && (
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" /> due{" "}
                            {new Date(assignment.due_date).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                    <Link
                      to={`/instructor/assignments/${assignment.id}/grade`}
                      className={
                        assignment.ungraded_submissions > 0
                          ? "dash-cta text-xs"
                          : "dash-cta-ghost text-xs"
                      }
                    >
                      {assignment.ungraded_submissions > 0
                        ? "Review now"
                        : "View"}
                      <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </div>
                ))
              )}
            </SectionCard>
          </StaggerGrid>
          <StaggerGrid className="grid grid-cols-1 mb-6">
            <SectionCard
              title="My courses"
              description={
                courses.length
                  ? `${courses.length} active course${courses.length === 1 ? "" : "s"}`
                  : undefined
              }
              icon={Award}
              action={{ label: "All courses", to: "/instructor/courses" }}
            >
              {isLoading ? (
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="h-24 dash-skeleton" />
                  <div className="h-24 dash-skeleton" />
                </div>
              ) : courses.length === 0 ? (
                <EmptyState
                  icon={BookOpen}
                  title="No courses yet"
                  description="Create your first course to start teaching."
                  action={{
                    label: "Create course",
                    to: "/instructor/courses/create",
                  }}
                />
              ) : (
                <div className="grid md:grid-cols-2 gap-4">
                  {courses.slice(0, 4).map((c: any) => (
                    <Link
                      key={c.id}
                      to={`/instructor/courses/${c.id}/edit`}
                      className="group p-4 rounded-xl border border-slate-200 hover:border-orange-200 hover:shadow-md transition flex gap-3"
                    >
                      {c.thumbnail ? (
                        <img
                          src={c.thumbnail}
                          alt={c.title}
                          className="w-16 h-12 object-cover rounded-md flex-shrink-0"
                        />
                      ) : (
                        <div className="w-16 h-12 rounded-md bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center flex-shrink-0">
                          <BookOpen className="w-5 h-5 text-white" />
                        </div>
                      )}
                      <div className="min-w-0 flex-1">
                        <h3 className="font-semibold text-secondary-900 truncate group-hover:text-orange-600 transition">
                          {c.title}
                        </h3>
                        <div className="flex items-center gap-x-3 gap-y-1 mt-1 text-xs text-slate-500 flex-wrap">
                          <span className="flex items-center gap-1">
                            <Users className="w-3 h-3" /> {c.students || 0}
                          </span>
                          <span className="flex items-center gap-1">
                            <Star className="w-3 h-3 text-amber-400" />{" "}
                            {c.rating?.toFixed(1) || "—"}
                          </span>
                          <span>{c.lessons || 0} lessons</span>
                          {/* Price with additional (discounted) price when on sale */}
                          {c.course_sale_price > 0 &&
                          c.course_sale_price < c.course_price ? (
                            <span className="flex items-center gap-1 font-semibold text-secondary-900">
                              ₹{c.course_sale_price}
                              <span className="text-slate-400 line-through font-normal">
                                ₹{c.course_price}
                              </span>
                            </span>
                          ) : (
                            <span className="font-semibold text-secondary-900">
                              {c.course_price > 0
                                ? `₹${c.course_price}`
                                : "Free"}
                            </span>
                          )}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </SectionCard>
          </StaggerGrid>
        </div>
        <aside className="rd-dashboard-secondary">
          <ReviewQueueCard />
          <FadeUp className="mb-6">
            <div className="dash-card p-5 flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-4">
                <div className="relative">
                  <Avatar className="w-16 h-16 ring-4 ring-orange-100/60">
                    {profile?.profile_photo ? (
                      <img
                        src={profile.profile_photo}
                        alt={fullName || "Instructor"}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <AvatarFallback className="bg-gradient-to-br from-orange-400 to-orange-600 text-white text-xl font-bold">
                        {fullName?.charAt(0) || "I"}
                      </AvatarFallback>
                    )}
                  </Avatar>
                  <div className="absolute -bottom-1 -right-1 bg-orange-500 text-white rounded-full p-1 border-2 border-white">
                    <PenSquare className="w-3 h-3" />
                  </div>
                </div>
                <div>
                  <h2 className="text-lg font-bold text-secondary-900">
                    {fullName || "Instructor"}
                  </h2>
                  <p className="text-sm text-slate-500">{user?.email}</p>
                  {profile?.designation && (
                    <p className="text-xs text-orange-600 font-semibold uppercase tracking-wider mt-0.5">
                      {profile.designation}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate("/profile")}
                  className="dash-cta-ghost text-xs"
                >
                  <Edit3 className="w-3.5 h-3.5" /> Edit Profile
                </button>
                <Link to="/instructor/blog" className="dash-cta-ghost text-xs">
                  <PenSquare className="w-3.5 h-3.5" /> Blog
                </Link>
              </div>
            </div>
          </FadeUp>
          <StaggerGrid className="grid grid-cols-1 mb-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Export Your Data
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
                {EXPORT_SECTIONS.map(({ section, label, description }) => (
                  <div
                    key={section}
                    className="bg-white p-4 rounded-lg border flex flex-col gap-2"
                    data-glass="content"
                  >
                    <ExportImportPanel
                      section={section}
                      role="instructor"
                      label={label}
                    />
                    <p className="text-xs text-slate-500">{description}</p>
                  </div>
                ))}
              </div>
            </div>
          </StaggerGrid>
        </aside>
      </div>
    </PageLayout>
  );
}

export default InstructorDashboard;
