import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { GlassDialog } from "@/components/ui/dialog";
import {
  plannerAPI,
  plannerError,
  interventionLabels,
  type QueueIntervention,
} from "@/api/planner";

export default function InterventionsPage() {
  const [items, setItems] = useState<QueueIntervention[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("active");
  const [selected, setSelected] = useState<QueueIntervention | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setItems((await plannerAPI.queue()).interventions);
    } catch (e) {
      setError(plannerError(e));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  const review = async (action: "dismiss" | "request_check") => {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      await plannerAPI.review(selected.id, action, note);
      setSelected(null);
      await load();
    } catch (e) {
      setError(plannerError(e));
    } finally {
      setBusy(false);
    }
  };
  const visible = items.filter(
    (i) =>
      filter === "all" ||
      (filter === "active"
        ? !["resolved", "dismissed"].includes(i.status)
        : i.status === filter),
  );
  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <p className="text-xs uppercase tracking-widest font-semibold text-orange-600">
              Turn evidence into support
            </p>
            <h1 className="dash-h1 mt-1">Learning interventions</h1>
            <p className="text-slate-600 mt-2">
              Review suggested checks, help learners who need support, and see
              what changed after practice.
            </p>
          </div>
          <button
            className="si-btn-ghost self-start"
            disabled={loading}
            onClick={() => void load()}
          >
            Refresh
          </button>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-interventions"
    >
      <div className="grid sm:grid-cols-3 gap-3">
        {[
          [
            "Needs your support",
            items.filter((i) => i.status === "needs_instructor").length,
          ],
          [
            "Waiting for follow-up",
            items.filter((i) => i.status === "monitoring").length,
          ],
          [
            "Retention checks passed",
            items.filter((i) => i.status === "resolved").length,
          ],
        ].map(([label, count]) => (
          <div key={label} className="glass-panel p-5 rounded-xl">
            <div className="text-3xl font-bold">{count}</div>
            <div className="text-sm text-slate-600 mt-1">{label}</div>
          </div>
        ))}
      </div>
      <p className="text-sm text-slate-500">
        Showing up to 300 interventions, prioritising learners who need support.
        Counts reflect this queue. Behaviour prompts a diagnostic check; it is
        not proof of a misconception. Assessment averages and practice scores
        describe different evidence and should be interpreted together.
      </p>
      <label className="text-sm font-medium block">
        Show
        <select
          className="si-input ml-3"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="active">Active interventions</option>
          <option value="needs_instructor">Needs instructor</option>
          <option value="monitoring">Follow-up scheduled</option>
          <option value="all">All interventions</option>
        </select>
      </label>
      {error && (
        <p role="alert" className="text-red-700">
          {error}
        </p>
      )}
      {loading ? (
        <p role="status">Loading learner evidence…</p>
      ) : !visible.length ? (
        <div className="glass-panel rounded-xl p-8">
          <h2 className="font-semibold">No interventions in this view</h2>
          <p className="text-sm text-slate-600 mt-2">
            Interventions appear when enrolled learners create a plan and course
            evidence suggests a check may help.
          </p>
          <Link
            to="/instructor/insights"
            className="underline text-orange-700 inline-block mt-3"
          >
            Review course hotspots
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {visible.map((i) => (
            <article key={i.id} className="glass-panel rounded-xl p-5">
              <div className="flex flex-wrap justify-between gap-3">
                <div>
                  <h2 className="font-semibold text-lg">
                    {i.learner_name} ·{" "}
                    <span className="capitalize">{i.concept}</span>
                  </h2>
                  <p className="text-sm text-slate-500">{i.course_title}</p>
                </div>
                <span className="text-sm text-orange-700">
                  {interventionLabels[i.status]}
                  {i.goal_status === "paused" ? " · Goal paused" : ""}
                </span>
              </div>
              <p className="text-sm text-slate-600 mt-3">{i.reason}</p>
              <div className="flex flex-wrap gap-5 text-sm mt-3">
                <span>
                  Baseline:{" "}
                  {i.baseline_score === null
                    ? "Unknown"
                    : `${i.baseline_score}%`}
                </span>
                <span>
                  Practice:{" "}
                  {i.latest_score === null
                    ? "Not checked"
                    : `${i.latest_score}%`}
                </span>
                <span>
                  Delayed check:{" "}
                  {i.followup_score === null
                    ? "Not checked"
                    : `${i.followup_score}%`}
                </span>
              </div>
              {i.instructor_note && (
                <p className="mt-3 bg-orange-50 rounded-lg p-3 text-sm">
                  Instructor note: {i.instructor_note}
                </p>
              )}
              <Link
                className="si-btn-ghost inline-flex mt-4 mr-2"
                to={`/instructor/assessment-studio?course_id=${i.course_id}&concept=${encodeURIComponent(i.concept)}`}
              >
                Fix assessment gap
              </Link>
              <button
                className="si-btn-primary mt-4"
                disabled={i.goal_status === "paused"}
                onClick={() => {
                  setSelected(i);
                  setNote(i.instructor_note || "");
                  setError("");
                }}
              >
                Review intervention
              </button>
            </article>
          ))}
        </div>
      )}
      <GlassDialog
        open={!!selected}
        onOpenChange={(open) => {
          if (!open && !busy) setSelected(null);
        }}
        title="Review intervention"
        description={
          selected
            ? `${selected.learner_name} · ${selected.concept}`
            : undefined
        }
      >
        <div className="p-5 space-y-4">
          <label className="block text-sm font-medium">
            Note for the learner
            <textarea
              className="si-input w-full mt-2"
              rows={4}
              maxLength={2000}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Explain the next step or why this intervention can be closed."
            />
          </label>
          <p className="text-sm text-slate-500">
            Closing an intervention does not change the learner's mastery.
            Requesting a check uses published questions linked to this concept.
          </p>
          {error && (
            <p role="alert" className="text-red-700">
              {error}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <button
              className="si-btn-primary"
              disabled={busy || note.trim().length < 3}
              onClick={() => void review("request_check")}
            >
              Request understanding check
            </button>
            <button
              className="si-btn-ghost"
              disabled={busy || note.trim().length < 3}
              onClick={() => void review("dismiss")}
            >
              Close with note
            </button>
          </div>
        </div>
      </GlassDialog>
    </PageLayout>
  );
}
