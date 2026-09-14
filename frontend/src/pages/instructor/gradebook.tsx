import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Instructor Gradebook — matrix of students x (quizzes, published
 * assignments) with graded/pending/missing/late cell coloring + CSV
 * download (plan Task 3 / spec A2). No page-level shell: renders inside
 * InstructorLayout, matching live-classes.tsx / courses.tsx conventions.
 */
import * as React from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Download, ClipboardList, Inbox } from "lucide-react";
import toast from "react-hot-toast";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  getGradebook,
  getGradebookCsv,
  type GradebookMatrix,
} from "@/api/gradebook";
import { cellKey, cellStatusMeta } from "@/lib/gradebook";

export default function InstructorGradebookPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const courseId = Number(id);

  const [matrix, setMatrix] = React.useState<GradebookMatrix | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [downloading, setDownloading] = React.useState(false);

  const load = React.useCallback(async () => {
    if (!Number.isFinite(courseId)) return;
    try {
      setLoading(true);
      setError(null);
      const data = await getGradebook(courseId);
      setMatrix(data);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to load the gradebook",
      );
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  React.useEffect(() => {
    load();
  }, [load]);

  const handleDownloadCsv = async () => {
    if (!Number.isFinite(courseId)) return;
    setDownloading(true);
    try {
      const blob = await getGradebookCsv(courseId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `gradebook-course-${courseId}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      toast.error(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to export the gradebook",
      );
    } finally {
      setDownloading(false);
    }
  };

  if (!Number.isFinite(courseId)) {
    return (
      <Card className="p-8 text-center">
        <p className="text-sm text-danger-600">Invalid course.</p>
      </Card>
    );
  }

  return (
    <PageLayout
      header={
        <PageHeader>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(-1)}
              className="btn btn-ghost btn-sm"
              aria-label="Back"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <h1 className="dash-h1 mb-1">Gradebook</h1>
              <p className="text-slate-600 text-sm">
                Scores across quizzes and assignments for this course
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link to={`/instructor/courses/${courseId}/grading-queue`}>
              <Button variant="outline">
                <Inbox className="h-4 w-4 mr-2" />
                Grading queue
              </Button>
            </Link>
            <Button
              onClick={handleDownloadCsv}
              disabled={downloading || loading || !matrix}
            >
              <Download className="h-4 w-4 mr-2" />
              {downloading ? "Exporting..." : "Export CSV"}
            </Button>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-gradebook"
    >
      {loading ? (
        <Card className="p-8">
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-10 w-full dash-skeleton" />
            ))}
          </div>
        </Card>
      ) : error ? (
        <Card className="p-8 text-center">
          <p className="text-sm text-danger-600 mb-3">{error}</p>
          <Button variant="outline" onClick={load}>
            Try again
          </Button>
        </Card>
      ) : !matrix || matrix.rows.length === 0 ? (
        <Card className="p-12 text-center">
          <ClipboardList className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No students yet
          </h3>
          <p className="text-gray-600">
            Once students enroll, their scores will show up here.
          </p>
        </Card>
      ) : matrix.items.length === 0 ? (
        <Card className="p-12 text-center">
          <ClipboardList className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No quizzes or published assignments yet
          </h3>
          <p className="text-gray-600">
            Add a quiz or publish an assignment to start tracking grades.
          </p>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="sticky left-0 z-10 bg-slate-50 text-left px-4 py-3 font-semibold text-slate-700 min-w-[220px]">
                    Student
                  </th>
                  {matrix.items.map((item) => (
                    <th
                      key={cellKey(item)}
                      className="text-left px-4 py-3 font-semibold text-slate-700 min-w-[140px] whitespace-nowrap"
                    >
                      <div className="flex flex-col">
                        <span
                          className="truncate max-w-[180px]"
                          title={item.title}
                        >
                          {item.title}
                        </span>
                        <span className="text-[11px] font-normal text-slate-400">
                          {item.type === "quiz" ? "Quiz" : "Assignment"}{" "}
                          &middot; {item.max} pts
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.rows.map((row) => (
                  <tr
                    key={row.student.id}
                    className="border-b border-slate-100 hover:bg-slate-50/60"
                  >
                    <td className="sticky left-0 z-10 bg-white px-4 py-3 min-w-[220px]">
                      <div className="font-medium text-slate-900">
                        {row.student.name}
                      </div>
                      {row.student.email && (
                        <div className="text-xs text-slate-500">
                          {row.student.email}
                        </div>
                      )}
                    </td>
                    {matrix.items.map((item) => {
                      const key = cellKey(item);
                      const cell = row.cells[key];
                      const meta = cellStatusMeta(cell);
                      return (
                        <td key={key} className="px-4 py-3">
                          <span
                            className={`inline-flex items-center rounded-md px-2.5 py-1 text-xs font-semibold ${meta.className}`}
                          >
                            {meta.label}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </PageLayout>
  );
}
