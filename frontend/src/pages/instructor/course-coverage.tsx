import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Instructor → Course coverage & outcome (v2.0 §4.3 assessment-first
 * coverage gap report, §8.3 #1 curriculum concept view, §9.5 concept links).
 * Route: /instructor/courses/:id/coverage
 *   - Outcome definition (UP): what the learner will be able to do + target concepts
 *   - Every curriculum element (lessons, quizzes, labs, games, 3D tasks,
 *     assignments) with an editable concept list (one PUT per element)
 *   - Coverage table: taught by / assessed by / gap, per concept
 *   - Prerequisite declarations (concept requires concept)
 */
import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import toast from "react-hot-toast";
import { ArrowLeft, Save, Target, Trash2 } from "lucide-react";
import {
  masteryAPI,
  parseConcepts,
  type Coverage,
  type LinkKind,
} from "@/api/mastery";

const GAP_LABEL: Record<string, { text: string; cls: string }> = {
  no_teaching: {
    text: "Assessed but nothing teaches it",
    cls: "bg-red-100 text-red-800",
  },
  no_assessment: {
    text: "Taught but never assessed",
    cls: "bg-amber-100 text-amber-800",
  },
  target_uncovered: {
    text: "Target with no material",
    cls: "bg-red-100 text-red-800",
  },
};

export default function CourseCoveragePage() {
  const { id } = useParams();
  const courseId = Number(id);
  const [cov, setCov] = useState<Coverage | null>(null);
  const [loading, setLoading] = useState(true);
  const [outcomeText, setOutcomeText] = useState("");
  const [targets, setTargets] = useState("");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [prereqs, setPrereqs] = useState<
    { concept: string; requires: string }[]
  >([]);
  const [newPrereq, setNewPrereq] = useState({ concept: "", requires: "" });
  const [saving, setSaving] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [c, p] = await Promise.all([
        masteryAPI.coverage(courseId),
        masteryAPI.prerequisites(),
      ]);
      setCov(c);
      setOutcomeText(c.outcome.text);
      setTargets(c.outcome.target_concepts.join(", "));
      const d: Record<string, string> = {};
      c.elements.forEach((e) => {
        d[`${e.kind}:${e.ref_id}`] = e.concepts.join(", ");
      });
      setDrafts(d);
      const mine = new Set(c.concepts.map((r) => r.concept));
      setPrereqs(p.filter((x) => mine.has(x.concept) || mine.has(x.requires)));
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Could not load coverage");
    } finally {
      setLoading(false);
    }
  }, [courseId]);
  useEffect(() => {
    load();
  }, [load]);

  const saveOutcome = async () => {
    setSaving("outcome");
    try {
      await masteryAPI.setOutcome(
        courseId,
        outcomeText,
        parseConcepts(targets),
      );
      toast.success("Outcome saved");
      load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Could not save the outcome");
    } finally {
      setSaving(null);
    }
  };
  const saveLinks = async (kind: LinkKind, ref: string) => {
    const key = `${kind}:${ref}`;
    setSaving(key);
    try {
      await masteryAPI.setLinks(
        kind,
        ref,
        parseConcepts(drafts[key] || ""),
        courseId,
      );
      toast.success("Concepts saved");
      load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Could not save concepts");
    } finally {
      setSaving(null);
    }
  };
  const addPrereq = async () => {
    try {
      await masteryAPI.addPrerequisite(newPrereq.concept, newPrereq.requires);
      setNewPrereq({ concept: "", requires: "" });
      load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Could not add prerequisite");
    }
  };
  const removePrereq = async (p: { concept: string; requires: string }) => {
    try {
      await masteryAPI.removePrerequisite(p.concept, p.requires);
      load();
    } catch {
      toast.error("Could not remove");
    }
  };

  if (loading || !cov)
    return <div className="p-6 text-sm text-gray-500">Loading coverage…</div>;

  return (
    <PageLayout
      header={
        <PageHeader>
          <Link
            to={`/instructor/courses/${courseId}/edit`}
            className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-4 h-4" /> Editor
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 flex-1">
            Coverage & outcome
          </h1>
          <span className="text-xs text-gray-500">
            {cov.summary.concepts} concepts · {cov.summary.gaps} gaps
          </span>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-course-coverage"
    >
      <div
        className="rounded-xl border border-gray-200 bg-white p-4 space-y-3"
        data-glass="work"
      >
        <h2 className="font-semibold text-gray-900 inline-flex items-center gap-2">
          <Target className="w-4 h-4 text-orange-500" /> Outcome definition
        </h2>
        <p className="text-xs text-gray-500">
          State what the learner will be able to do. Everything in the course
          maps to it; learners see progress against the outcome, not "percent of
          videos watched".
        </p>
        <textarea
          value={outcomeText}
          onChange={(e) => setOutcomeText(e.target.value)}
          rows={2}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
          placeholder="e.g. Solve JEE-level stoichiometry problems in under 3 minutes each"
        />
        <label className="block text-sm">
          <span className="text-gray-600">
            Target concepts (comma-separated)
          </span>
          <input
            value={targets}
            onChange={(e) => setTargets(e.target.value)}
            className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-lg"
            placeholder="stoichiometry, limiting reagent, gas laws"
          />
        </label>
        <button
          type="button"
          disabled={saving === "outcome"}
          onClick={saveOutcome}
          className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium rounded-lg bg-gray-900 text-white hover:bg-black disabled:opacity-50"
        >
          <Save className="w-4 h-4" /> Save outcome
        </button>
      </div>
      <div
        className="rounded-xl border border-gray-200 bg-white overflow-hidden"
        data-glass="work"
      >
        <div className="px-4 py-3 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Coverage gap report</h2>
          <p className="text-xs text-gray-500">
            Assessment-first: which assessed or target concepts have no teaching
            material behind them.
          </p>
        </div>
        {cov.concepts.length === 0 ? (
          <p className="p-4 text-sm text-gray-500">
            Tag elements with concepts below to build the report.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-500">
              <tr>
                <th className="px-4 py-2">Concept</th>
                <th className="px-4 py-2">Taught by</th>
                <th className="px-4 py-2">Assessed by</th>
                <th className="px-4 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {cov.concepts.map((r) => (
                <tr
                  key={r.concept}
                  className="border-t border-gray-100 align-top"
                >
                  <td className="px-4 py-2 font-medium text-gray-900 capitalize">
                    {r.concept}
                    {r.is_target && (
                      <span className="ml-1 text-[11px] text-orange-600">
                        target
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-gray-600">
                    {r.taught_by.join(", ") || "—"}
                  </td>
                  <td className="px-4 py-2 text-gray-600">
                    {r.assessed_by.join(", ") || "—"}
                  </td>
                  <td className="px-4 py-2">
                    {r.gap ? (
                      <span
                        className={`text-[11px] px-2 py-0.5 rounded-full ${GAP_LABEL[r.gap].cls}`}
                      >
                        {GAP_LABEL[r.gap].text}
                      </span>
                    ) : (
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                        covered
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div
        className="rounded-xl border border-gray-200 bg-white overflow-hidden"
        data-glass="work"
      >
        <div className="px-4 py-3 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">
            Curriculum elements → concepts
          </h2>
          <p className="text-xs text-gray-500">
            Every scorable element declares the concepts it teaches or assesses;
            scores then feed each learner's mastery graph.
          </p>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs text-gray-500">
            <tr>
              <th className="px-4 py-2">Element</th>
              <th className="px-4 py-2">Role</th>
              <th className="px-4 py-2">Concepts</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {cov.elements.map((e) => {
              const key = `${e.kind}:${e.ref_id}`;
              return (
                <tr key={key} className="border-t border-gray-100">
                  <td className="px-4 py-2">
                    <span className="font-medium text-gray-900">{e.title}</span>
                    <span className="block text-[11px] text-gray-400">
                      {e.kind}
                      {e.content_type ? ` · ${e.content_type}` : ""}
                      {e.practice_only ? " · practice" : ""}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-600">{e.role}</td>
                  <td className="px-4 py-2">
                    <input
                      value={drafts[key] ?? ""}
                      onChange={(ev) =>
                        setDrafts((d) => ({ ...d, [key]: ev.target.value }))
                      }
                      className="w-full px-2 py-1 border border-gray-300 rounded"
                      placeholder="comma-separated"
                      aria-label={`Concepts for ${e.title}`}
                    />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      type="button"
                      disabled={saving === key}
                      onClick={() => saveLinks(e.kind, e.ref_id)}
                      className="px-2 py-1 text-xs text-blue-600 hover:underline"
                    >
                      {saving === key ? "Saving…" : "Save"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div
        className="rounded-xl border border-gray-200 bg-white p-4"
        data-glass="work"
      >
        <h2 className="font-semibold text-gray-900 mb-1">Prerequisites</h2>
        <p className="text-xs text-gray-500 mb-2">
          "Concept requires concept" — drives the learner's "recover first"
          advice and Engine B's depth bands.
        </p>
        <ul className="text-sm space-y-1 mb-3">
          {prereqs.map((p) => (
            <li
              key={`${p.concept}>${p.requires}`}
              className="flex items-center gap-2"
            >
              <span className="capitalize">{p.concept}</span>
              <span className="text-gray-400">requires</span>
              <span className="capitalize">{p.requires}</span>
              <button
                type="button"
                onClick={() => removePrereq(p)}
                className="text-red-500 ml-2"
                aria-label="Remove prerequisite"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </li>
          ))}
          {prereqs.length === 0 && (
            <li className="text-gray-400">
              None declared for this course's concepts.
            </li>
          )}
        </ul>
        <div className="flex flex-wrap gap-2 text-sm">
          <input
            value={newPrereq.concept}
            onChange={(e) =>
              setNewPrereq({ ...newPrereq, concept: e.target.value })
            }
            placeholder="concept"
            className="px-2 py-1 border border-gray-300 rounded"
          />
          <span className="self-center text-gray-400">requires</span>
          <input
            value={newPrereq.requires}
            onChange={(e) =>
              setNewPrereq({ ...newPrereq, requires: e.target.value })
            }
            placeholder="prerequisite"
            className="px-2 py-1 border border-gray-300 rounded"
          />
          <button
            type="button"
            disabled={!newPrereq.concept || !newPrereq.requires}
            onClick={addPrereq}
            className="px-3 py-1 rounded-lg bg-gray-900 text-white disabled:opacity-40"
          >
            Add
          </button>
        </div>
      </div>
    </PageLayout>
  );
}
