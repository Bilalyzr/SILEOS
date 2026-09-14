import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Grading course picker — the "Grading" nav destination (plan Task 3).
 * Gradebook + grading queue are per-course pages, so this lightweight
 * picker lists the instructor's courses with direct links into both —
 * simplest discoverable path that still gives "Grading" its own nav
 * highlight (distinct from "My courses").
 */
import * as React from "react";
import { Link } from "react-router-dom";
import { ClipboardList, Inbox, BookOpen } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/api/axios";

interface CourseSummary {
  id: number;
  title: string;
}

export default function InstructorGradingPickerPage() {
  const [courses, setCourses] = React.useState<CourseSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await api.get("/courses/my-courses", {
          params: { page: 1, page_size: 100 },
        });
        if (cancelled) return;
        const list = (response.data.courses || []).map((c: any) => ({
          id: c.id,
          title: c.post_title || c.title || "Untitled course",
        }));
        setCourses(list);
      } catch (err: any) {
        if (!cancelled)
          setError(
            err?.response?.data?.detail ||
              err?.message ||
              "Failed to load your courses",
          );
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="dash-h1 mb-1">Grading</h1>
          <p className="text-slate-600 text-sm">
            Pick a course to open its gradebook or grading queue
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-grading"
    >
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-4">
              <div className="h-4 w-2/3 dash-skeleton mb-3" />
              <div className="h-8 w-full dash-skeleton" />
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card className="p-8 text-center">
          <p className="text-sm text-danger-600">{error}</p>
        </Card>
      ) : courses.length === 0 ? (
        <Card className="p-12 text-center">
          <BookOpen className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No courses yet
          </h3>
          <p className="text-gray-600">
            Create a course to start grading student work.
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {courses.map((course) => (
            <Card key={course.id} className="p-4">
              <h3 className="font-semibold text-slate-900 mb-3 line-clamp-2">
                {course.title}
              </h3>
              <div className="flex gap-2">
                <Link
                  to={`/instructor/courses/${course.id}/gradebook`}
                  className="flex-1"
                >
                  <Button variant="outline" size="sm" className="w-full">
                    <ClipboardList className="h-4 w-4 mr-1" />
                    Gradebook
                  </Button>
                </Link>
                <Link
                  to={`/instructor/courses/${course.id}/grading-queue`}
                  className="flex-1"
                >
                  <Button variant="outline" size="sm" className="w-full">
                    <Inbox className="h-4 w-4 mr-1" />
                    Queue
                  </Button>
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}
    </PageLayout>
  );
}
