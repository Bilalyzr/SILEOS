import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * My Grades — student-facing grade transparency (v2.0 §5.3).
 * Real endpoints only: GET /dashboard/student (enrolled courses + titles),
 * GET /analytics/courses/{id}/students/{uid}/cumulative-grade (numeric uid
 * from the auth store), GET /analytics/students/{uid}/mastery.
 */
import { useEffect, useState } from "react";
import { GraduationCap } from "lucide-react";
import { api } from "@/api/axios";
import { useAuthStore } from "@/store/auth";

interface EnrolledCourse {
  id: number;
  title: string;
  progress: number;
}

interface GradeBreakdownPart {
  average: number | null;
  weight: string;
}
interface GradeRow {
  course_id: number;
  cumulative_grade: number;
  letter: string;
  breakdown: {
    quizzes: GradeBreakdownPart;
    assignments: GradeBreakdownPart;
    interactive_modules: GradeBreakdownPart;
    three_d_tasks?: GradeBreakdownPart;
    live_participation?: GradeBreakdownPart;
  };
}

interface MasteryCourse {
  course_id: number;
  mastery: number;
  level: string;
  completion_percentage: number;
}

export default function MyGradesPage() {
  const user = useAuthStore((s) => s.user);
  const [courses, setCourses] = useState<EnrolledCourse[]>([]);
  const [grades, setGrades] = useState<Record<number, GradeRow>>({});
  const [mastery, setMastery] = useState<MasteryCourse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const dash = await api.get("/dashboard/student");
        const enrolled: EnrolledCourse[] = (
          dash.data?.enrolled_courses || []
        ).map((c: { id: number; title: string; progress: number }) => ({
          id: c.id,
          title: c.title,
          progress: c.progress ?? 0,
        }));
        setCourses(enrolled);

        const uid = user?.id;
        if (!uid) return;

        const gradeMap: Record<number, GradeRow> = {};
        await Promise.all(
          enrolled.slice(0, 20).map(async (c) => {
            const r = await api
              .get(
                `/analytics/courses/${c.id}/students/${uid}/cumulative-grade`,
              )
              .catch(() => null);
            if (r?.data?.cumulative_grade !== undefined)
              gradeMap[c.id] = r.data;
          }),
        );
        setGrades(gradeMap);

        const m = await api
          .get(`/analytics/students/${uid}/mastery`)
          .catch(() => null);
        if (m?.data?.courses) setMastery(m.data.courses);
      } catch {
        // dashboard endpoint failure leaves empty state below
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user?.id]);

  const gradeColor = (g: number) =>
    g >= 75 ? "text-emerald-600" : g >= 50 ? "text-amber-600" : "text-red-500";

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="dash-h1 flex items-center gap-2">
              <GraduationCap className="h-7 w-7 text-primary" /> My Grades
            </h1>
            <p className="text-slate-600 text-sm mt-1 mb-8">
              Your cumulative grade per course — exactly how it is calculated,
              nothing hidden.
            </p>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-student-my-grades"
    >
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-28 rounded-xl bg-gray-100 animate-pulse"
            />
          ))}
        </div>
      ) : courses.length === 0 ? (
        <p className="text-gray-500 text-sm border border-dashed border-gray-300 rounded-xl p-8 text-center">
          You are not enrolled in any course yet.
        </p>
      ) : (
        <ul className="space-y-4">
          {courses.map((c) => {
            const g = grades[c.id];
            const m = mastery.find((x) => x.course_id === c.id);
            return (
              <li
                key={c.id}
                className="border border-gray-200 rounded-xl bg-white p-5"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="font-semibold text-gray-900">{c.title}</span>
                  {g ? (
                    <div className="text-right">
                      <span
                        className={`text-2xl font-bold ${gradeColor(g.cumulative_grade)}`}
                      >
                        {g.cumulative_grade}
                      </span>
                      <span className="text-sm text-gray-400 ml-1">
                        {g.letter}
                      </span>
                    </div>
                  ) : (
                    <span className="text-xs text-gray-400">
                      no graded work yet · {c.progress}% complete
                    </span>
                  )}
                </div>
                {g && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-3 text-sm">
                    {(
                      [
                        ["quizzes", "Quizzes"],
                        ["assignments", "Assignments"],
                        ["interactive_modules", "Games & H5P"],
                        ["three_d_tasks", "3D & lab tasks"],
                        ["live_participation", "Live classes"],
                      ] as const
                    ).map(([k, label]) => {
                      const b = g.breakdown[k];
                      if (!b) return null;
                      return (
                        <div key={k} className="bg-gray-50 rounded-lg p-3">
                          <p className="text-xs text-gray-500">
                            {label} · {b.weight}
                          </p>
                          <p className="font-semibold text-gray-800 mt-0.5">
                            {b.average !== null ? `${b.average}%` : "—"}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
                {m && (
                  <p className="text-xs text-gray-400 mt-3">
                    Mastery:{" "}
                    <span className="font-medium text-gray-600 capitalize">
                      {m.level}
                    </span>{" "}
                    ({m.mastery}%) · {m.completion_percentage}% complete
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </PageLayout>
  );
}
