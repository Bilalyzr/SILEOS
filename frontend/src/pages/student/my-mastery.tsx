import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * My Mastery — the learner's own concept graph (v2.0 §9.5, §10.1).
 * One graph across every course type: estimate + confidence per concept,
 * the evidence behind it (click a concept), prerequisite gaps ("recover
 * first"), and a per-course progress map of milestones with mastery state
 * (§8.3 #2). Real endpoints only: /mastery/*, /dashboard/student.
 */
import { useEffect, useState } from "react";
import { Brain, ChevronRight } from "lucide-react";
import { api } from "@/api/axios";
import {
  masteryAPI,
  type EvidenceRow,
  type LearnerGraph,
  type Milestone,
} from "@/api/mastery";
import { AdaptiveLessonPanel } from "@/components/ai/AdaptiveLessonPanel";
import { TeachBackPanel } from "@/components/flywheel/TeachBackPanel";
import StruggleProfile from "@/components/signals/StruggleProfile";
import { useAuthStore } from "@/store/auth";

interface EnrolledCourse {
  id: number;
  title: string;
}

const LEVEL_CLS: Record<string, string> = {
  novice: "bg-red-100 text-red-800",
  developing: "bg-amber-100 text-amber-800",
  proficient: "bg-blue-100 text-blue-800",
  mastered: "bg-emerald-100 text-emerald-800",
};
const SOURCE_LABEL: Record<string, string> = {
  quiz: "Quiz",
  assignment: "Assignment",
  three_d_task: "3D task",
  lab: "Lab",
  h5p: "H5P",
  game: "Game",
};

export default function MyMasteryPage() {
  const user = useAuthStore((s) => s.user);
  const uid = Number((user as any)?.id);
  const [graph, setGraph] = useState<LearnerGraph | null>(null);
  const [courses, setCourses] = useState<EnrolledCourse[]>([]);
  const [courseId, setCourseId] = useState<number | null>(null);
  const [milestones, setMilestones] = useState<Milestone[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Record<string, EvidenceRow[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      masteryAPI.me(),
      api
        .get("/dashboard/student")
        .then((r) => {
          const raw =
            r.data?.enrolled_courses ||
            r.data?.courses ||
            r.data?.enrollments ||
            [];
          return raw
            .map((c: any) => ({
              id: Number(c.course_id ?? c.id),
              title:
                c.title || c.course_title || `Course ${c.course_id ?? c.id}`,
            }))
            .filter((c: EnrolledCourse) => Number.isFinite(c.id));
        })
        .catch(() => [] as EnrolledCourse[]),
    ])
      .then(([g, cs]) => {
        if (!cancelled) {
          setGraph(g);
          setCourses(cs);
          if (cs[0]) setCourseId(cs[0].id);
        }
      })
      .catch(() => {
        if (!cancelled) setError("Could not load your mastery graph");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!courseId || !uid) return;
    let cancelled = false;
    masteryAPI
      .progressMap(courseId, uid)
      .then((pm) => {
        if (!cancelled) setMilestones(pm.milestones);
      })
      .catch(() => setMilestones([]));
    return () => {
      cancelled = true;
    };
  }, [courseId, uid]);

  const toggle = async (concept: string) => {
    if (open === concept) {
      setOpen(null);
      return;
    }
    setOpen(concept);
    if (!evidence[concept] && uid) {
      try {
        const r = await masteryAPI.evidence(uid, concept);
        setEvidence((e) => ({ ...e, [concept]: r.evidence }));
      } catch {
        /* ignore */
      }
    }
  };

  if (loading)
    return (
      <div className="p-6 text-sm text-gray-500">
        Loading your mastery graph…
      </div>
    );
  if (error || !graph)
    return (
      <div className="p-6 text-sm text-red-600" role="alert">
        {error}
      </div>
    );

  return (
    <PageLayout
      header={
        <PageHeader>
          <Brain className="w-7 h-7 text-emerald-600" />
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900">My Mastery</h1>
            <p className="text-sm text-gray-500">
              One graph across all your courses. Every quiz, lab, game and 3D
              task you do adds evidence; stronger evidence counts more.
            </p>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold text-gray-900">{graph.overall}%</p>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${LEVEL_CLS[graph.overall_level] || ""}`}
            >
              {graph.overall_level}
            </span>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-student-my-mastery"
    >
      {graph.recover_first.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="font-semibold text-amber-900 mb-1">Recover first</p>
          <ul className="text-sm text-amber-800 list-disc pl-5">
            {graph.recover_first.map((g) => (
              <li key={g.concept}>
                Before pushing <strong>{g.concept}</strong>, strengthen{" "}
                {g.recover_first.join(", ")} — they are prerequisites you have
                not held yet.
              </li>
            ))}
          </ul>
        </div>
      )}
      <div
        className="rounded-xl border border-gray-200 bg-white overflow-hidden"
        data-glass="content"
      >
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">
            Concepts ({graph.concepts.length})
          </h2>
          {graph.weak_concepts.length > 0 && (
            <span className="text-xs text-gray-500">
              Weakest: {graph.weak_concepts.slice(0, 3).join(", ")}
            </span>
          )}
        </div>
        {graph.concepts.length === 0 ? (
          <p className="p-4 text-sm text-gray-500">
            No evidence yet. Finish a quiz, lab, game or 3D task tagged with
            concepts and your graph starts here.
          </p>
        ) : (
          <ul>
            {graph.concepts.map((c) => (
              <li key={c.concept} className="border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => toggle(c.concept)}
                  aria-expanded={open === c.concept}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50"
                >
                  <ChevronRight
                    className={`w-4 h-4 text-gray-400 transition ${open === c.concept ? "rotate-90" : ""}`}
                  />
                  <span className="flex-1 min-w-0">
                    <span className="font-medium text-gray-900 capitalize">
                      {c.concept}
                    </span>
                    {c.prerequisite_gaps.length > 0 && (
                      <span className="ml-2 text-[11px] text-amber-700">
                        needs {c.prerequisite_gaps.join(", ")}
                      </span>
                    )}
                    <span className="block mt-1 h-2 w-full max-w-md bg-gray-100 rounded-full overflow-hidden">
                      <span
                        className="block h-full bg-emerald-500"
                        style={{ width: `${Math.round(c.estimate)}%` }}
                      />
                    </span>
                  </span>
                  <span className="text-sm font-semibold text-gray-800 w-14 text-right">
                    {c.estimate}%
                  </span>
                  <span
                    className={`text-[11px] px-2 py-0.5 rounded-full ${LEVEL_CLS[c.level]}`}
                  >
                    {c.level}
                  </span>
                  <span className="text-[11px] text-gray-400 w-28 text-right">
                    confidence {Math.round(c.confidence * 100)}% ·{" "}
                    {c.evidence_count} ev.
                  </span>
                </button>
                {open === c.concept && (
                  <div className="px-11 pb-3 text-xs text-gray-600">
                    <TeachBackPanel concept={c.concept} courseId={courseId} />
                    {!evidence[c.concept] ? (
                      "Loading evidence…"
                    ) : evidence[c.concept].length === 0 ? (
                      "No evidence rows."
                    ) : (
                      <ul className="space-y-0.5">
                        {evidence[c.concept].map((e, i) => (
                          <li key={i}>
                            {SOURCE_LABEL[e.source_kind] || e.source_kind} #
                            {e.source_ref}: {e.score_pct}% (weight {e.weight}
                            {e.detail && (e.detail as any).confidence
                              ? `, path ${String((e.detail as any).confidence).replace(/_/g, " ")}`
                              : ""}
                            )
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
      <StruggleProfile courseId={courseId ?? undefined} />
      {courseId && (
        <AdaptiveLessonPanel
          courseId={courseId}
          concept={graph.weak_concepts[0]}
        />
      )}
      {courses.length > 0 && (
        <div
          className="rounded-xl border border-gray-200 bg-white p-4"
          data-glass="work"
        >
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <h2 className="font-semibold text-gray-900 flex-1">Progress map</h2>
            <select
              value={courseId ?? ""}
              onChange={(e) => setCourseId(Number(e.target.value))}
              className="px-2 py-1 border border-gray-300 rounded text-sm"
              aria-label="Course"
            >
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          </div>
          {!milestones ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : milestones.length === 0 ? (
            <p className="text-sm text-gray-500">
              This course has no milestones yet.
            </p>
          ) : (
            <ol className="space-y-1">
              {milestones.map((m) => (
                <li
                  key={`${m.kind}:${m.ref_id}`}
                  className="flex items-center gap-3 text-sm border border-gray-100 rounded-lg px-3 py-2"
                >
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${m.state === "completed" ? "bg-emerald-500" : "bg-gray-300"}`}
                  />
                  <span className="flex-1 min-w-0">
                    <span className="text-gray-900">{m.title}</span>
                    <span className="ml-2 text-[11px] text-gray-400">
                      {m.kind}
                      {m.concepts.length ? ` · ${m.concepts.join(", ")}` : ""}
                    </span>
                  </span>
                  {m.score_pct !== null && (
                    <span className="text-xs text-gray-600">
                      {m.score_pct}%
                    </span>
                  )}
                  {m.mastery !== null && (
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                      mastery {m.mastery}%
                    </span>
                  )}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </PageLayout>
  );
}
