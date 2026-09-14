import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useState, useEffect } from "react";
import { Users, BookOpen, Star, ShoppingCart, BarChart3 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { PurchasesByCourseChart } from "@/components/instructor/PurchasesByCourseChart";
import { api } from "@/api/axios";

/**
 * Instructor analytics.
 *
 * This page deliberately reads from the SAME `/dashboard/instructor` endpoint
 * as the instructor dashboard so the headline numbers always match what the
 * dashboard shows. Earlier versions fabricated revenue trends, daily-active
 * users, watch time and conversion rates (all hard-coded zeros / random data);
 * those have been removed in favour of the real figures the backend actually
 * exposes: students, courses, purchases (enrollments) and ratings.
 */

interface CoursePerformance {
  courseId: number;
  title: string;
  enrollments: number;
  rating: number;
}

interface AnalyticsData {
  totalStudents: number;
  totalCourses: number;
  totalPurchases: number;
  averageRating: number;
  coursePerformance: CoursePerformance[];
}

const emptyAnalytics: AnalyticsData = {
  totalStudents: 0,
  totalCourses: 0,
  totalPurchases: 0,
  averageRating: 0,
  coursePerformance: [],
};

export function InstructorAnalytics() {
  const [analytics, setAnalytics] = useState<AnalyticsData>(emptyAnalytics);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const res = await api.get("/dashboard/instructor");
      const data = res.data;

      const courses = (data.courses || []).map((course: any) => ({
        courseId: course.id,
        title: course.title,
        enrollments: course.total_enrollments ?? course.students ?? 0,
        rating: course.average_rating ?? course.rating ?? 0,
      }));

      // Prefer the aggregate the dashboard uses; fall back to summing per-course
      // enrollments so the two screens never disagree.
      const totalPurchases =
        data.stats?.total_purchases ??
        courses.reduce(
          (s: number, c: CoursePerformance) => s + c.enrollments,
          0,
        );

      setAnalytics({
        totalStudents: data.stats?.total_students || 0,
        totalCourses: data.stats?.total_courses || 0,
        totalPurchases,
        averageRating: data.stats?.average_rating || 0,
        coursePerformance: courses.sort(
          (a: CoursePerformance, b: CoursePerformance) =>
            b.enrollments - a.enrollments,
        ),
      });
    } catch (err) {
      console.error("Error fetching analytics:", err);
      setAnalytics(emptyAnalytics);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-48 mb-4"></div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  const hasData = analytics.totalStudents > 0 || analytics.totalCourses > 0;

  const overviewCards = [
    {
      label: "Total Students",
      value: analytics.totalStudents.toLocaleString(),
      icon: Users,
      tint: "bg-blue-100 text-blue-600",
    },
    {
      label: "Course Purchases",
      value: analytics.totalPurchases.toLocaleString(),
      icon: ShoppingCart,
      tint: "bg-green-100 text-green-600",
    },
    {
      label: "Active Courses",
      value: analytics.totalCourses.toLocaleString(),
      icon: BookOpen,
      tint: "bg-purple-100 text-purple-600",
    },
    {
      label: "Avg Rating",
      value: `${analytics.averageRating.toFixed(1)}/5`,
      icon: Star,
      tint: "bg-yellow-100 text-yellow-600",
    },
  ];

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="dash-h1 mb-1">Analytics</h1>
          <p className="text-slate-600 text-sm">
            Real performance across your courses — these figures match your
            dashboard.
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-analytics"
    >
      {!hasData ? (
        <Card className="p-12 text-center">
          <BarChart3 className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No analytics data yet
          </h3>
          <p className="text-gray-600">
            Your analytics will appear here once you have students and
            enrollments.
          </p>
        </Card>
      ) : (
        <>
          {/* Overview Stats — aligned with the instructor dashboard */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {overviewCards.map((card) => (
              <Card key={card.label} className="p-6">
                <div className="flex items-center">
                  <div className={`p-2 rounded-lg ${card.tint}`}>
                    <card.icon className="h-6 w-6" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">
                      {card.label}
                    </p>
                    <p className="text-2xl font-semibold text-gray-900">
                      {card.value}
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>

          {/* Enrollments by course + course performance breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Purchases by course — ranked horizontal bar chart */}
            <div className="lg:col-span-2">
              <Card className="p-6">
                <PurchasesByCourseChart
                  courses={analytics.coursePerformance}
                  totalPurchases={analytics.totalPurchases}
                />
              </Card>
            </div>

            {/* Course performance list */}
            <div>
              <Card className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-6">
                  Course Performance
                </h3>
                {analytics.coursePerformance.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No course data available yet
                  </div>
                ) : (
                  <div className="space-y-4">
                    {analytics.coursePerformance.map((course, index) => (
                      <div
                        key={course.courseId}
                        className="border border-gray-200 rounded-lg p-4"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium text-gray-900 text-sm line-clamp-1">
                            {course.title}
                          </h4>
                          <span className="text-xs text-gray-500">
                            #{index + 1}
                          </span>
                        </div>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-600">Purchases:</span>
                            <span className="font-medium">
                              {course.enrollments}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-600">Rating:</span>
                            <span className="font-medium">
                              {course.rating
                                ? `${course.rating.toFixed(1)}/5`
                                : "—"}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          </div>
        </>
      )}
    </PageLayout>
  );
}
