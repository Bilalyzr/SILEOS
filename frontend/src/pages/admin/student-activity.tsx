import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Clock,
  PlayCircle,
  Activity,
  Users,
  Loader,
  AlertCircle,
  History,
  BarChart3,
  RotateCw,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";
import { courseAPI } from "@/api/course";

/**
 * Admin -> Courses -> Student Activity (Issue 8).
 *
 * For the selected course, lists every enrolled student with:
 *   - Time Spent (total watch seconds, from WatchSession rows)
 *   - Course Watch Sessions (count of watch segments)
 *   - Last Active (most recent watch event)
 *   - Current Activity (live "watching now" flag, event in last 5 min)
 *   - Viewing History (per-student expandable timeline of
 *     started/paused/resumed/completed events + discrete activities)
 */

interface StudentRow {
  user_id: number;
  student_name: string;
  email: string;
  progress: number;
  time_spent_seconds: number;
  watch_sessions: number;
  last_active: string | null;
  currently_watching: boolean;
  enrollment_status: string;
  completion_date: string | null;
}

interface HistoryEntry {
  lesson_id: number;
  event: string;
  duration_seconds: number;
  position_seconds: number;
  at: string;
}

interface ActivityEntry {
  type: string;
  lesson_id: number | null;
  quiz_id: number | null;
  at: string;
}

const fmtDuration = (seconds: number): string => {
  if (!seconds) return "0m";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
};

const fmtDate = (iso: string | null): string => {
  if (!iso) return "Never";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return "Never";
  }
};

const EVENT_LABELS: Record<string, string> = {
  started: "Started",
  paused: "Paused",
  resumed: "Resumed",
  completed: "Completed",
};

interface CourseStatistics {
  enrolled_students: number;
  quiz: {
    total_quizzes: number;
    total_attempts: number;
    passed: number;
    failed: number;
    pass_rate: number;
    average_score: number;
  };
  struggles: {
    total_failed_attempts: number;
    top_strugglers: Array<{
      user_id: number;
      student_name: string;
      failed_attempts: number;
    }>;
  };
  revisits: {
    total_revisits: number;
    most_revisited_lessons: Array<{
      lesson_id: number;
      title: string;
      revisits: number;
    }>;
  };
  averages: {
    progress: number;
    watch_sessions_per_student: number;
    time_spent_per_student_seconds: number;
  };
}

export const AdminStudentActivity: React.FC = () => {
  const { courseId } = useParams<{ courseId: string }>();
  const cid = Number(courseId);

  const [tab, setTab] = useState<"activity" | "statistics">("activity");
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statistics, setStatistics] = useState<CourseStatistics | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [expandedUser, setExpandedUser] = useState<number | null>(null);
  const [history, setHistory] = useState<{
    watch: HistoryEntry[];
    activities: ActivityEntry[];
  } | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  const fetchActivity = async () => {
    if (!cid) return;
    try {
      setLoading(true);
      setError(null);
      const data = await courseAPI.getCourseStudentActivity(cid);
      setStudents(data.students);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to load student activity",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivity();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cid]);

  const fetchStatistics = async () => {
    if (!cid) return;
    try {
      setStatsLoading(true);
      const data = await courseAPI.getCourseStatistics(cid);
      setStatistics(data);
    } catch {
      setStatistics(null);
    } finally {
      setStatsLoading(false);
    }
  };

  // Load statistics lazily the first time the tab is opened.
  useEffect(() => {
    if (tab === "statistics" && !statistics && !statsLoading) {
      fetchStatistics();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const toggleHistory = async (userId: number) => {
    if (expandedUser === userId) {
      setExpandedUser(null);
      setHistory(null);
      return;
    }
    setExpandedUser(userId);
    setHistory(null);
    setHistoryLoading(true);
    try {
      const data = await courseAPI.getStudentViewingHistory(cid, userId);
      setHistory({ watch: data.watch_history, activities: data.activities });
    } catch {
      setHistory({ watch: [], activities: [] });
    } finally {
      setHistoryLoading(false);
    }
  };

  const totalTime = students.reduce(
    (s, r) => s + (r.time_spent_seconds || 0),
    0,
  );
  const totalSessions = students.reduce(
    (s, r) => s + (r.watch_sessions || 0),
    0,
  );
  const activeNow = students.filter((r) => r.currently_watching).length;

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-1">
              Student Activity
            </h1>
            <p className="text-gray-500 text-sm mb-4">Course ID: {cid}</p>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-student-activity"
    >
      <Link
        to="/admin/courses"
        className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-3"
      >
        <ArrowLeft className="w-4 h-4 mr-1" /> Back to Courses
      </Link>
      <div className="flex gap-1 mb-6 border-b border-gray-200">
        <button
          onClick={() => setTab("activity")}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === "activity" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          <Activity className="w-4 h-4 inline mr-1" /> Student Activity
        </button>
        <button
          onClick={() => setTab("statistics")}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === "statistics" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          <BarChart3 className="w-4 h-4 inline mr-1" /> Statistics
        </button>
      </div>
      {tab === "activity" && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <div
              className="bg-white rounded-lg border border-gray-200 p-4"
              data-glass="content"
            >
              <div className="flex items-center text-gray-500 text-sm">
                <Users className="w-4 h-4 mr-2" /> Enrolled Students
              </div>
              <div className="text-2xl font-bold text-gray-900 mt-1">
                {students.length}
              </div>
            </div>
            <div
              className="bg-white rounded-lg border border-gray-200 p-4"
              data-glass="content"
            >
              <div className="flex items-center text-gray-500 text-sm">
                <Clock className="w-4 h-4 mr-2" /> Total Time Spent
              </div>
              <div className="text-2xl font-bold text-gray-900 mt-1">
                {fmtDuration(totalTime)}
              </div>
            </div>
            <div
              className="bg-white rounded-lg border border-gray-200 p-4"
              data-glass="content"
            >
              <div className="flex items-center text-gray-500 text-sm">
                <PlayCircle className="w-4 h-4 mr-2" /> Watch Sessions
              </div>
              <div className="text-2xl font-bold text-gray-900 mt-1">
                {totalSessions}
              </div>
            </div>
          </div>

          {activeNow > 0 && (
            <div className="mb-4 inline-flex items-center gap-2 px-3 py-1.5 bg-green-50 text-green-700 rounded-full text-sm">
              <Activity className="w-4 h-4" />
              {activeNow} student{activeNow === 1 ? "" : "s"} watching right now
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-16 text-gray-500">
              <Loader className="w-5 h-5 mr-2 animate-spin" /> Loading
              activity...
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-16 text-red-600">
              <AlertCircle className="w-5 h-5 mr-2" /> {error}
            </div>
          ) : students.length === 0 ? (
            <div className="py-16 text-center text-gray-500">
              No enrolled students yet.
            </div>
          ) : (
            <div
              className="bg-white rounded-lg border border-gray-200 overflow-hidden"
              data-glass="work"
            >
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Student
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Progress
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Time Spent
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Sessions
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Last Active
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        History
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {students.map((s) => (
                      <React.Fragment key={s.user_id}>
                        <tr className="hover:bg-gray-50">
                          <td className="px-6 py-4">
                            <div className="text-sm font-medium text-gray-900">
                              {s.student_name}
                            </div>
                            <div className="text-xs text-gray-500">
                              {s.email}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-900">
                            {s.progress}%
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-900">
                            {fmtDuration(s.time_spent_seconds)}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-900">
                            {s.watch_sessions}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">
                            {fmtDate(s.last_active)}
                          </td>
                          <td className="px-6 py-4">
                            {s.currently_watching ? (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">
                                <Activity className="w-3 h-3 mr-1" /> Active
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-600">
                                Inactive
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-4">
                            <button
                              onClick={() => toggleHistory(s.user_id)}
                              className="inline-flex items-center text-xs text-blue-600 hover:text-blue-800"
                            >
                              <History className="w-3.5 h-3.5 mr-1" />
                              {expandedUser === s.user_id ? "Hide" : "View"}
                            </button>
                          </td>
                        </tr>
                        {expandedUser === s.user_id && (
                          <tr className="bg-gray-50">
                            <td colSpan={7} className="px-6 py-4">
                              {historyLoading ? (
                                <div className="flex items-center text-sm text-gray-500">
                                  <Loader className="w-4 h-4 mr-2 animate-spin" />{" "}
                                  Loading history...
                                </div>
                              ) : history &&
                                (history.watch.length > 0 ||
                                  history.activities.length > 0) ? (
                                <div className="space-y-4">
                                  <div>
                                    <div className="text-xs font-semibold text-gray-500 uppercase mb-2">
                                      Viewing History
                                    </div>
                                    {history.watch.length === 0 ? (
                                      <div className="text-sm text-gray-400">
                                        No watch events recorded.
                                      </div>
                                    ) : (
                                      <ul className="space-y-1 max-h-60 overflow-y-auto">
                                        {history.watch.map((w, i) => (
                                          <li
                                            key={i}
                                            className="text-sm text-gray-700 flex items-center gap-3"
                                          >
                                            <span className="text-gray-400 w-40">
                                              {fmtDate(w.at)}
                                            </span>
                                            <span className="font-medium">
                                              {EVENT_LABELS[w.event] || w.event}
                                            </span>
                                            <span className="text-gray-400">
                                              lesson #{w.lesson_id}
                                            </span>
                                            {w.duration_seconds > 0 && (
                                              <span className="text-gray-400">
                                                (
                                                {fmtDuration(
                                                  w.duration_seconds,
                                                )}
                                                )
                                              </span>
                                            )}
                                          </li>
                                        ))}
                                      </ul>
                                    )}
                                  </div>
                                  {history.activities.length > 0 && (
                                    <div>
                                      <div className="text-xs font-semibold text-gray-500 uppercase mb-2">
                                        Activities
                                      </div>
                                      <ul className="space-y-1 max-h-40 overflow-y-auto">
                                        {history.activities.map((a, i) => (
                                          <li
                                            key={i}
                                            className="text-sm text-gray-700 flex items-center gap-3"
                                          >
                                            <span className="text-gray-400 w-40">
                                              {fmtDate(a.at)}
                                            </span>
                                            <span className="font-medium">
                                              {a.type.replace(/_/g, " ")}
                                            </span>
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <div className="text-sm text-gray-400">
                                  No viewing history yet.
                                </div>
                              )}
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
      {tab === "statistics" &&
        (statsLoading ? (
          <div className="flex items-center justify-center py-16 text-gray-500">
            <Loader className="w-5 h-5 mr-2 animate-spin" /> Loading
            statistics...
          </div>
        ) : statistics ? (
          <div className="space-y-6">
            {/* Quiz attempts */}
            <div
              className="bg-white rounded-lg border border-gray-200 p-5"
              data-glass="content"
            >
              <div className="flex items-center text-gray-700 font-semibold mb-4">
                <BarChart3 className="w-4 h-4 mr-2" /> Quiz Attempts
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <Stat
                  label="Quizzes"
                  value={String(statistics.quiz.total_quizzes)}
                />
                <Stat
                  label="Total Attempts"
                  value={String(statistics.quiz.total_attempts)}
                />
                <Stat
                  label="Pass Rate"
                  value={`${statistics.quiz.pass_rate.toFixed(1)}%`}
                />
                <Stat
                  label="Avg Score"
                  value={`${statistics.quiz.average_score.toFixed(1)}%`}
                />
              </div>
              <div className="mt-3 text-sm text-gray-500">
                {statistics.quiz.passed} passed / {statistics.quiz.failed}{" "}
                failed
              </div>
            </div>

            {/* Struggles */}
            <div
              className="bg-white rounded-lg border border-gray-200 p-5"
              data-glass="content"
            >
              <div className="flex items-center text-gray-700 font-semibold mb-4">
                <AlertTriangle className="w-4 h-4 mr-2 text-amber-500" />{" "}
                Struggles (failed attempts)
              </div>
              <Stat
                label="Total Failed Attempts"
                value={String(statistics.struggles.total_failed_attempts)}
              />
              {statistics.struggles.top_strugglers.length > 0 && (
                <div className="mt-4">
                  <div className="text-xs font-semibold text-gray-500 uppercase mb-2">
                    Students needing attention
                  </div>
                  <ul className="space-y-1">
                    {statistics.struggles.top_strugglers.map((s) => (
                      <li
                        key={s.user_id}
                        className="text-sm text-gray-700 flex justify-between"
                      >
                        <span>{s.student_name}</span>
                        <span className="text-amber-600">
                          {s.failed_attempts} failed
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Revisits */}
            <div
              className="bg-white rounded-lg border border-gray-200 p-5"
              data-glass="content"
            >
              <div className="flex items-center text-gray-700 font-semibold mb-4">
                <RotateCw className="w-4 h-4 mr-2 text-blue-500" /> Revisits
              </div>
              <Stat
                label="Total Repeat Views"
                value={String(statistics.revisits.total_revisits)}
              />
              {statistics.revisits.most_revisited_lessons.length > 0 && (
                <div className="mt-4">
                  <div className="text-xs font-semibold text-gray-500 uppercase mb-2">
                    Most revisited lessons
                  </div>
                  <ul className="space-y-1">
                    {statistics.revisits.most_revisited_lessons.map((l) => (
                      <li
                        key={l.lesson_id}
                        className="text-sm text-gray-700 flex justify-between"
                      >
                        <span className="truncate mr-2">{l.title}</span>
                        <span className="text-blue-600">
                          {l.revisits} revisits
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Averages */}
            <div
              className="bg-white rounded-lg border border-gray-200 p-5"
              data-glass="content"
            >
              <div className="flex items-center text-gray-700 font-semibold mb-4">
                <TrendingUp className="w-4 h-4 mr-2 text-green-500" /> Average
                Frequency / Progress
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <Stat
                  label="Avg Progress"
                  value={`${statistics.averages.progress.toFixed(1)}%`}
                />
                <Stat
                  label="Avg Sessions / Student"
                  value={statistics.averages.watch_sessions_per_student.toFixed(
                    1,
                  )}
                />
                <Stat
                  label="Avg Time / Student"
                  value={fmtDuration(
                    statistics.averages.time_spent_per_student_seconds,
                  )}
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="py-16 text-center text-gray-500">
            No statistics available.
          </div>
        ))}
    </PageLayout>
  );
};

const Stat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div>
    <div className="text-xs text-gray-500 uppercase">{label}</div>
    <div className="text-xl font-bold text-gray-900 mt-0.5">{value}</div>
  </div>
);
