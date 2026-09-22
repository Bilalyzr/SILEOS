import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Instructor Insights — surfaces the analytics that had no UI:
 * At-Risk students (explainable flags) + Question Bank item analysis
 * (facility/discrimination). One page, two tabs.
 */
import { useEffect, useState } from "react";
import {
  InsightCards,
  NextClassAgenda,
} from "@/components/flywheel/FlywheelPanel";
import { FunnelPanel } from "@/components/flywheel/FunnelPanel";
import { EarningsPanel } from "@/components/flywheel/EarningsPanel";
import { BarChart3, AlertTriangle } from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/api/axios";
import { signalsAPI, type CourseHotspots } from "@/api/signals";

interface RiskResult {
  user_id: number;
  risk_score: number;
  severity: "low" | "medium" | "high";
  reasons: string[];
}

interface BankItem {
  bank_question_id: number;
  question_title: string;
  difficulty: string;
  attempts: number;
  facility: number | null;
  discrimination: number | null;
  flag: string;
}

export default function InsightsPage() {
  const [tab, setTab] = useState<
    "risk" | "items" | "flywheel" | "funnel" | "earnings" | "hotspots"
  >(() =>
    new URLSearchParams(window.location.search).get("tab") === "hotspots"
      ? "hotspots"
      : "risk",
  );
  const [courses, setCourses] = useState<{ id: number; title: string }[]>([]);
  const [courseId, setCourseId] = useState<number | null>(null);
  const [risk, setRisk] = useState<RiskResult[]>([]);
  const [banks, setBanks] = useState<{ id: number; title: string }[]>([]);
  const [bankId, setBankId] = useState<number | null>(null);
  const [items, setItems] = useState<BankItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api
      .get("/courses/my-courses", { params: { page: 1, page_size: 50 } })
      .then((r) => {
        const list = (r.data.courses || []).map(
          (c: { id: number; post_title: string }) => ({
            id: c.id,
            title: c.post_title,
          }),
        );
        setCourses(list);
        const requested = Number(
          new URLSearchParams(window.location.search).get("course_id"),
        );
        if (list[0])
          setCourseId(
            list.some((c: { id: number }) => c.id === requested)
              ? requested
              : list[0].id,
          );
      })
      .catch(() => toast.error("Failed to load courses"));
    api
      .get("/question-banks")
      .then((r) => {
        const list = r.data.banks || [];
        setBanks(list);
        if (list[0]) setBankId(list[0].id);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (courseId == null) return;
    setLoading(true);
    api
      .get(`/analytics/courses/${courseId}/at-risk`)
      .then((r) => setRisk(r.data.results || []))
      .catch(() => toast.error("Failed to compute at-risk"))
      .finally(() => setLoading(false));
  }, [courseId]);

  useEffect(() => {
    if (bankId == null) return;
    setLoading(true);
    api
      .get(`/question-banks/${bankId}/analysis`)
      .then((r) => setItems(r.data.items || []))
      .catch(() => toast.error("Failed to load item analysis"))
      .finally(() => setLoading(false));
  }, [bankId]);

  const sevColor = {
    high: "bg-red-100 text-red-700",
    medium: "bg-amber-100 text-amber-700",
    low: "bg-gray-100 text-gray-600",
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="dash-h1 flex items-center gap-2">
              <BarChart3 className="h-7 w-7 text-primary" /> Insights
            </h1>
            <p className="text-slate-600 text-sm mt-1 mb-6">
              Who needs help, and which questions are broken.
            </p>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-insights"
    >
      <div className="flex gap-2 mb-6">
        {(
          [
            ["risk", "At-Risk Students"],
            ["items", "Item Analysis"],
            ["flywheel", "Next Class & 3D Insights"],
            ["funnel", "Funnel"],
            ["earnings", "Earnings"],
            ["hotspots", "Hotspots"],
          ] as const
        ).map(([v, label]) => (
          <button
            key={v}
            onClick={() => setTab(v)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium border ${tab === v ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-700 border-gray-300"}`}
          >
            {v === "risk" ? (
              <AlertTriangle className="inline h-3.5 w-3.5 mr-1" />
            ) : null}
            {label}
          </button>
        ))}
      </div>
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 rounded-xl bg-gray-100 animate-pulse"
            />
          ))}
        </div>
      ) : tab === "hotspots" ? (
        <>
          <label className="block mb-4">
            Course
            <select
              aria-label="Hotspots course"
              value={courseId ?? ""}
              onChange={(e) => setCourseId(Number(e.target.value))}
              className="ml-3 px-3 py-2 border rounded-lg"
            >
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          </label>
          {courseId == null ? (
            <p>No courses available.</p>
          ) : (
            <HotspotsTable courseId={courseId} />
          )}
        </>
      ) : tab === "earnings" ? (
        <EarningsPanel />
      ) : tab === "funnel" ? (
        <FunnelPanel />
      ) : tab === "flywheel" ? (
        <>
          <select
            value={courseId ?? ""}
            onChange={(e) => setCourseId(Number(e.target.value))}
            className="mb-4 px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
          >
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>
          {courseId != null && (
            <div className="space-y-4">
              <NextClassAgenda courseId={courseId} />
              <div>
                <h2 className="font-semibold text-gray-900 mb-2">
                  3D evidence × question outcomes
                </h2>
                <InsightCards courseId={courseId} />
              </div>
            </div>
          )}
        </>
      ) : tab === "risk" ? (
        <>
          <select
            value={courseId ?? ""}
            onChange={(e) => setCourseId(Number(e.target.value))}
            className="mb-4 px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
          >
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>
          {risk.length === 0 ? (
            <p className="text-gray-500 text-sm border border-dashed border-gray-300 rounded-xl p-6 text-center">
              No at-risk students <AstraSymbol value="🎉" />
            </p>
          ) : (
            <ul className="space-y-3">
              {risk.map((r) => (
                <li
                  key={r.user_id}
                  className="border border-gray-200 rounded-xl bg-white p-4"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span
                      className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${sevColor[r.severity]}`}
                    >
                      {r.severity.toUpperCase()} · {r.risk_score}
                    </span>
                    <span className="text-sm font-medium text-gray-900">
                      Student #{r.user_id}
                    </span>
                  </div>
                  <ul className="text-xs text-gray-600 space-y-1">
                    {r.reasons.map((reason, i) => (
                      <li key={i}>• {reason}</li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <>
          <select
            value={bankId ?? ""}
            onChange={(e) => setBankId(Number(e.target.value))}
            className="mb-4 px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
          >
            {banks.map((b) => (
              <option key={b.id} value={b.id}>
                {b.title}
              </option>
            ))}
          </select>
          {banks.length === 0 ? (
            <p className="text-gray-500 text-sm border border-dashed border-gray-300 rounded-xl p-6 text-center">
              No question banks yet — create one under Quizzes.
            </p>
          ) : (
            <div
              className="overflow-x-auto border border-gray-200 rounded-xl bg-white"
              data-glass="work"
            >
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="text-left px-4 py-2">Question</th>
                    <th className="px-3 py-2">Attempts</th>
                    <th className="px-3 py-2">Facility</th>
                    <th className="px-3 py-2">Discrim.</th>
                    <th className="px-3 py-2">Flag</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <tr
                      key={it.bank_question_id}
                      className="border-t border-gray-100"
                    >
                      <td className="px-4 py-2 max-w-xs truncate">
                        {it.question_title}
                      </td>
                      <td className="text-center px-3 py-2">{it.attempts}</td>
                      <td className="text-center px-3 py-2">
                        {it.facility ?? "—"}
                      </td>
                      <td className="text-center px-3 py-2">
                        {it.discrimination ?? "—"}
                      </td>
                      <td className="text-center px-3 py-2">
                        <span
                          className={`text-[11px] px-2 py-0.5 rounded-full ${it.flag === "ok" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}
                        >
                          {it.flag}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </PageLayout>
  );
}

function HotspotsTable({ courseId }: { courseId: number }) {
  const [data, setData] = useState<CourseHotspots | null>(null);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setData(null);
    setError(false);
    signalsAPI
      .courseHotspots(courseId)
      .then((result) => {
        if (active) setData(result);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, [courseId, retry]);
  const time = (s: number) =>
    `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  if (error)
    return (
      <p role="alert">
        Could not load hotspots.{" "}
        <button onClick={() => setRetry((n) => n + 1)} className="underline">
          Retry
        </button>
      </p>
    );
  if (!data) return <p role="status">Loading hotspots…</p>;
  if (!data.hotspots.length) return <p>No hotspots in the last 30 days.</p>;
  return (
    <div className="overflow-x-auto">
      <p className="text-sm mb-3">
        Segments needing attention in the last 30 days. Scores reflect learning
        behaviour.
      </p>
      <table className="w-full text-sm text-left">
        <thead>
          <tr>
            {[
              "Lesson",
              "Time",
              "Concepts",
              "Score",
              "Learners",
              "Rewinds",
              "Replays",
              "Early exits",
            ].map((label) => (
              <th className="p-2" scope="col" key={label}>
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.hotspots.map((s) => (
            <tr className="border-t" key={`${s.lesson_id}-${s.segment}`}>
              <td className="p-2">{s.lesson_title}</td>
              <td className="p-2 whitespace-nowrap">
                {time(s.start_s)}–{time(s.end_s)}
              </td>
              <td className="p-2">{s.concepts.join(", ") || "Unmapped"}</td>
              <td className="p-2">{s.score}</td>
              <td className="p-2">{s.learners}</td>
              <td className="p-2">{s.rewinds}</td>
              <td className="p-2">{s.replays}</td>
              <td className="p-2">{s.early_quits}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
