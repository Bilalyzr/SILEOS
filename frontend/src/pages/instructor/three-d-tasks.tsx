import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Instructor → 3D Tasks (v2.0 §4.1 "3D Assessment Builder" + "Annotation
 * Placer", §6). List own tasks; build one: pick a model (own or shared
 * library), a task type, place anchors by clicking the model surface (stored
 * as normalised bounding-box coordinates), fill the type's fields, save as
 * draft, preview (never stores attempts), publish (then it appears in the
 * quiz builder's Add-item palette). Attempts tab shows the §6.3 confidence
 * signal per learner. Config strings render as React text only.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import toast from "react-hot-toast";
import { Box, Plus, Trash2, Eye, Upload, ArrowLeft } from "lucide-react";
import { threeDAPI, type ThreeDModel } from "@/api/threeD";
import {
  TASK_TYPES,
  TASK_TYPE_INFO,
  threeDTasksAPI,
  type Anchor,
  type Parameter,
  type TaskConfig,
  type TaskType,
  type ThreeDTask,
} from "@/api/threeDTasks";
import { TIERS, TIER_LABELS, type Tier } from "@/api/scorable";
import { ThreeDViewer } from "@/components/three-d/ThreeDViewer";
import { ThreeDTaskPlayer } from "@/components/three-d/tasks/ThreeDTaskPlayer";

function errorDetail(err: any, fallback: string): string {
  const d = err?.response?.data?.detail;
  return typeof d === "string" ? d : fallback;
}

const slug = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40) || "item";

interface Draft {
  id?: number;
  title: string;
  model_id: number | null;
  task_type: TaskType;
  tier_floor: Tier;
  concepts: string;
  anchors: Anchor[];
  parameters: Parameter[];
  intro: string;
  // per-type
  pairs: { label: string; anchor_id: string }[];
  prompts: { condition: string; anchor_id: string }[];
  claim: string;
  claim_holds: boolean;
  expected_state: { param_id: string; min: number; max: number }[];
  must_explore: { param_id: string; min: number; max: number }[];
  slots: { id: string; label: string }[];
  parts: { id: string; label: string; slot_id: string }[];
  questions: {
    prompt: string;
    answer: number;
    tolerance: number;
    unit: string;
    anchor_a: string;
    anchor_b: string;
  }[];
  targets: { prompt: string; param_id: string; min: number; max: number }[];
  steps: { id: string; text: string }[];
}

const EMPTY: Draft = {
  title: "",
  model_id: null,
  task_type: "identify",
  tier_floor: "T4",
  concepts: "",
  anchors: [],
  parameters: [],
  intro: "",
  pairs: [],
  prompts: [],
  claim: "",
  claim_holds: true,
  expected_state: [],
  must_explore: [],
  slots: [],
  parts: [],
  questions: [],
  targets: [],
  steps: [],
};

function toConfig(d: Draft): TaskConfig {
  const intro = d.intro || null;
  const anchors = d.anchors.map((a) => ({
    id: a.id,
    label: a.label,
    region: a.region || null,
    position: a.position,
    description: a.description || null,
  }));
  switch (d.task_type) {
    case "match":
      return { anchors, pairs: d.pairs, intro };
    case "identify":
      return { anchors, prompts: d.prompts, intro };
    case "verify":
      return {
        parameters: d.parameters,
        anchors,
        claim: d.claim,
        claim_holds: d.claim_holds,
        expected_state: d.expected_state,
        must_explore: d.must_explore,
        intro,
      };
    case "assemble":
      return { slots: d.slots, parts: d.parts, intro };
    case "measure":
      return {
        anchors,
        questions: d.questions.map((q) => ({
          prompt: q.prompt,
          answer: q.answer,
          tolerance: q.tolerance,
          unit: q.unit || null,
          anchor_a: q.anchor_a || null,
          anchor_b: q.anchor_b || null,
        })),
        intro,
      };
    case "manipulate":
      return { parameters: d.parameters, anchors, targets: d.targets, intro };
    case "sequence":
      return { steps: d.steps, anchors, intro };
  }
}

function fromTask(t: ThreeDTask): Draft {
  const c = (t.config || {}) as any;
  return {
    ...EMPTY,
    id: t.id,
    title: t.title,
    model_id: t.model_id,
    task_type: t.task_type,
    tier_floor: t.tier_floor,
    concepts: (t.concepts || []).join(", "),
    anchors: c.anchors || [],
    parameters: c.parameters || [],
    intro: c.intro || "",
    pairs: c.pairs || [],
    prompts: c.prompts || [],
    claim: c.claim || "",
    claim_holds: c.claim_holds ?? true,
    expected_state: c.expected_state || [],
    must_explore: c.must_explore || [],
    slots: c.slots || [],
    parts: c.parts || [],
    questions: (c.questions || []).map((q: any) => ({
      prompt: q.prompt,
      answer: q.answer,
      tolerance: q.tolerance ?? 0,
      unit: q.unit || "",
      anchor_a: q.anchor_a || "",
      anchor_b: q.anchor_b || "",
    })),
    targets: c.targets || [],
    steps: c.steps || [],
  };
}

export function InstructorThreeDTasksPage() {
  const [tasks, setTasks] = useState<ThreeDTask[]>([]);
  const [models, setModels] = useState<ThreeDModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [saving, setSaving] = useState(false);
  const [previewId, setPreviewId] = useState<number | null>(null);
  const [attemptsFor, setAttemptsFor] = useState<{
    task: ThreeDTask;
    rows: any[];
  } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [t, m] = await Promise.all([
        threeDTasksAPI.mine(),
        threeDAPI.list(),
      ]);
      setTasks(t);
      setModels([...(m.models || []), ...((m as any).library || [])]);
    } catch (err) {
      toast.error(errorDetail(err, "Failed to load 3D tasks"));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  // Teaching kit deep-link: /instructor/three-d-tasks?model_id=X&title=… opens a new draft on that model
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const mid = Number(q.get("model_id"));
    if (mid > 0)
      setDraft(
        (d) => d ?? { ...EMPTY, model_id: mid, title: q.get("title") || "" },
      );
  }, []);

  const save = async (publish = false) => {
    if (!draft) return;
    if (!draft.model_id) {
      toast.error("Pick a 3D model first");
      return;
    }
    if (!draft.title.trim()) {
      toast.error("Give the task a title");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        title: draft.title.trim(),
        model_id: draft.model_id,
        task_type: draft.task_type,
        config: toConfig(draft),
        concepts: draft.concepts
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        tier_floor: draft.tier_floor,
      };
      let saved = draft.id
        ? await threeDTasksAPI.update(draft.id, payload)
        : await threeDTasksAPI.create(payload);
      if (publish) saved = await threeDTasksAPI.publish(saved.id);
      toast.success(
        publish
          ? "Published — it is now in the quiz Add-item palette"
          : "Saved as draft",
      );
      setDraft(null);
      load();
    } catch (err) {
      toast.error(errorDetail(err, "Could not save the task"));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (t: ThreeDTask) => {
    if (!(await confirmDialog(`Delete "${t.title}"?`))) return;
    try {
      await threeDTasksAPI.remove(t.id);
      toast.success("Deleted");
      load();
    } catch (err) {
      toast.error(errorDetail(err, "Could not delete"));
    }
  };
  const toggle = async (t: ThreeDTask) => {
    try {
      t.status === "published"
        ? await threeDTasksAPI.unpublish(t.id)
        : await threeDTasksAPI.publish(t.id);
      load();
    } catch (err) {
      toast.error(errorDetail(err, "Could not change status"));
    }
  };
  const openAttempts = async (t: ThreeDTask) => {
    try {
      setAttemptsFor({ task: t, rows: await threeDTasksAPI.attempts(t.id) });
    } catch (err) {
      toast.error(errorDetail(err, "Could not load attempts"));
    }
  };

  if (draft) {
    return (
      <Builder
        draft={draft}
        setDraft={setDraft}
        models={models}
        saving={saving}
        onSave={save}
        onCancel={() => setDraft(null)}
        onPreview={() => draft.id && setPreviewId(draft.id)}
      />
    );
  }

  return (
    <PageLayout
      header={
        <PageHeader>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900">3D Tasks</h1>
            <p className="text-sm text-gray-500">
              Match-and-verify assessments on your 3D models. Graded on state
              and parameters, so a phone in list view earns the same marks as a
              headset.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setDraft({ ...EMPTY })}
            className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium rounded-lg bg-cyan-600 text-white hover:bg-cyan-700"
          >
            <Plus className="w-4 h-4" /> New 3D task
          </button>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-three-d-tasks"
    >
      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : tasks.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-10 text-center text-sm text-gray-500">
          <Box className="w-8 h-8 mx-auto mb-2 text-gray-400" />
          No 3D tasks yet. Create one on a model from your library or the shared
          library.
        </div>
      ) : (
        <div
          className="rounded-xl border border-gray-200 bg-white overflow-hidden"
          data-glass="work"
        >
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-500">
              <tr>
                <th className="px-4 py-2">Title</th>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">Max</th>
                <th className="px-4 py-2">Tier floor</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id} className="border-t border-gray-100">
                  <td className="px-4 py-2 font-medium text-gray-900">
                    <AstraSymbol value="🧊" /> {t.title}
                    <span className="block text-[11px] text-gray-400">
                      {(t.concepts || []).join(", ")}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {TASK_TYPE_INFO[t.task_type].label}
                  </td>
                  <td className="px-4 py-2">{t.max_score}</td>
                  <td className="px-4 py-2">{t.tier_floor}</td>
                  <td className="px-4 py-2">
                    {t.status === "published" ? (
                      <span className="text-emerald-700">Published</span>
                    ) : (
                      <span className="text-gray-400">Draft</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right whitespace-nowrap">
                    <button
                      type="button"
                      title="Preview"
                      onClick={() => setPreviewId(t.id)}
                      className="p-1.5 text-gray-500 hover:text-gray-900"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={async () =>
                        setDraft(fromTask(await threeDTasksAPI.get(t.id)))
                      }
                      className="px-2 py-1 text-xs text-blue-600 hover:underline"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => toggle(t)}
                      className="px-2 py-1 text-xs text-blue-600 hover:underline"
                    >
                      {t.status === "published" ? "Unpublish" : "Publish"}
                    </button>
                    <button
                      type="button"
                      onClick={() => openAttempts(t)}
                      className="px-2 py-1 text-xs text-blue-600 hover:underline"
                    >
                      Attempts
                    </button>
                    <button
                      type="button"
                      title="Delete"
                      onClick={() => remove(t)}
                      className="p-1.5 text-red-500 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {previewId && (
        <div
          className="fixed inset-0 z-modal bg-black/70 flex items-center justify-center p-4"
          onClick={() => setPreviewId(null)}
        >
          <div
            className="bg-white rounded-2xl max-w-4xl w-full max-h-[92vh] overflow-y-auto p-5"
            onClick={(e) => e.stopPropagation()}
            data-glass="content"
          >
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setPreviewId(null)}
                className="text-sm text-gray-500 hover:text-gray-900"
              >
                Close
              </button>
            </div>
            <ThreeDTaskPlayer taskId={previewId} previewOnly />
          </div>
        </div>
      )}
      {attemptsFor && (
        <div
          className="fixed inset-0 z-modal bg-black/70 flex items-center justify-center p-4"
          onClick={() => setAttemptsFor(null)}
        >
          <div
            className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-5"
            onClick={(e) => e.stopPropagation()}
            data-glass="work"
          >
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-gray-900">
                Attempts — {attemptsFor.task.title}
              </h2>
              <button
                type="button"
                onClick={() => setAttemptsFor(null)}
                className="text-sm text-gray-500 hover:text-gray-900"
              >
                Close
              </button>
            </div>
            <p className="text-xs text-gray-500 mb-3">
              The confidence signal reads the manipulation path: a right answer
              with a fumbling path is flagged, a right answer with a clean path
              is not.
            </p>
            {attemptsFor.rows.length === 0 ? (
              <p className="text-sm text-gray-500">No attempts yet.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-gray-500">
                  <tr>
                    <th className="py-1">Learner</th>
                    <th className="py-1">Score</th>
                    <th className="py-1">View</th>
                    <th className="py-1">Confidence</th>
                    <th className="py-1">Path</th>
                    <th className="py-1">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {attemptsFor.rows.map((a) => (
                    <tr key={a.id} className="border-t border-gray-100">
                      <td className="py-1">#{a.user_id}</td>
                      <td className="py-1">
                        {a.score}/{a.max_score}
                      </td>
                      <td className="py-1">{a.mode}</td>
                      <td className="py-1">
                        <span
                          className={`text-[11px] px-2 py-0.5 rounded-full ${a.confidence === "clean" ? "bg-emerald-100 text-emerald-800" : a.confidence === "trial_and_error" ? "bg-amber-100 text-amber-800" : "bg-gray-100 text-gray-600"}`}
                        >
                          {a.confidence.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="py-1 text-xs text-gray-500">
                        {a.confidence_detail?.wrong_selections ?? 0} wrong ·{" "}
                        {a.confidence_detail?.resets ?? 0} resets ·{" "}
                        {a.confidence_detail?.parameter_changes ?? 0} param
                        changes
                      </td>
                      <td className="py-1 text-xs text-gray-500">
                        {a.duration_s}s
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </PageLayout>
  );
}

// ================================================================ builder

function Builder({
  draft,
  setDraft,
  models,
  saving,
  onSave,
  onCancel,
  onPreview,
}: {
  draft: Draft;
  setDraft: (d: Draft) => void;
  models: ThreeDModel[];
  saving: boolean;
  onSave: (publish?: boolean) => void;
  onCancel: () => void;
  onPreview: () => void;
}) {
  const d = draft;
  const set = (patch: Partial<Draft>) => setDraft({ ...d, ...patch });
  const info = TASK_TYPE_INFO[d.task_type];
  const usesAnchors = ["match", "identify", "measure"].includes(d.task_type);
  const usesParams = ["verify", "manipulate"].includes(d.task_type);
  const anchorOptions = useMemo(
    () =>
      d.anchors.map((a, i) => ({ id: a.id, label: `${i + 1}. ${a.label}` })),
    [d.anchors],
  );

  const addAnchor = (pos: [number, number, number]) => {
    const n = d.anchors.length + 1;
    const label = `Part ${n}`; // rename inline in the list below
    let id = slug(label);
    if (d.anchors.some((a) => a.id === id)) id = `${id}-${n}`;
    set({
      anchors: [
        ...d.anchors,
        {
          id,
          label,
          region: `Region ${n}`,
          position: pos.map((v) => Math.round(v * 1000) / 1000),
          description: "",
        },
      ],
    });
  };

  const rows = "grid gap-2 text-sm";
  const input = "px-2 py-1 border border-gray-300 rounded w-full";

  return (
    <PageLayout
      header={
        <PageHeader>
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <h1 className="text-xl font-bold text-gray-900 flex-1">
            {d.id ? "Edit 3D task" : "New 3D task"}
          </h1>
          {d.id && (
            <button
              type="button"
              onClick={onPreview}
              className="px-3 py-2 text-sm rounded-lg border border-gray-300"
            >
              Preview
            </button>
          )}
          <button
            type="button"
            disabled={saving}
            onClick={() => onSave(false)}
            className="px-3 py-2 text-sm rounded-lg border border-gray-300"
          >
            Save draft
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={() => onSave(true)}
            className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium rounded-lg bg-cyan-600 text-white hover:bg-cyan-700 disabled:opacity-50"
          >
            <Upload className="w-4 h-4" />{" "}
            {saving ? "Saving…" : "Save & publish"}
          </button>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-three-d-tasks"
    >
      <div className="grid lg:grid-cols-2 gap-5">
        <div className="space-y-4">
          <div
            className="rounded-xl border border-gray-200 bg-white p-4 grid sm:grid-cols-2 gap-3 text-sm"
            data-glass="work"
          >
            <label className="sm:col-span-2">
              <span className="block text-gray-600 mb-1">Title</span>
              <input
                value={d.title}
                onChange={(e) => set({ title: e.target.value })}
                className={input}
              />
            </label>
            <label>
              <span className="block text-gray-600 mb-1">3D model</span>
              <select
                value={d.model_id ?? ""}
                onChange={(e) =>
                  set({
                    model_id: e.target.value ? Number(e.target.value) : null,
                    anchors: [],
                  })
                }
                className={input}
              >
                <option value="">— choose —</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.title}
                    {m.is_library ? " (shared library)" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="block text-gray-600 mb-1">Task type</span>
              <select
                value={d.task_type}
                onChange={(e) => set({ task_type: e.target.value as TaskType })}
                className={input}
              >
                {TASK_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {TASK_TYPE_INFO[t].label}
                  </option>
                ))}
              </select>
              <span className="block text-[11px] text-gray-500 mt-1">
                {info.learner}. Graded: {info.graded}.
              </span>
            </label>
            <label>
              <span className="block text-gray-600 mb-1">
                Concepts (comma-separated, for the mastery graph)
              </span>
              <input
                value={d.concepts}
                onChange={(e) => set({ concepts: e.target.value })}
                className={input}
                placeholder="conic sections, apex"
              />
            </label>
            <label>
              <span className="block text-gray-600 mb-1">Tier floor</span>
              <select
                value={d.tier_floor}
                onChange={(e) => set({ tier_floor: e.target.value as Tier })}
                className={input}
              >
                {TIERS.map((t) => (
                  <option key={t} value={t}>
                    {TIER_LABELS[t]}
                  </option>
                ))}
              </select>
              <span className="block text-[11px] text-gray-500 mt-1">
                Every type has a list-view interface, so T4 is the honest
                default. Above T4 the quiz builder blocks graded use.
              </span>
            </label>
            <label className="sm:col-span-2">
              <span className="block text-gray-600 mb-1">
                Intro shown to the learner
              </span>
              <input
                value={d.intro}
                onChange={(e) => set({ intro: e.target.value })}
                className={input}
              />
            </label>
          </div>

          {/* ---- per-type fields */}
          <div
            className="rounded-xl border border-gray-200 bg-white p-4 space-y-3 text-sm"
            data-glass="work"
          >
            <h2 className="font-semibold text-gray-900">
              {info.label} settings
            </h2>
            {d.task_type === "match" && (
              <div className={rows}>
                {d.pairs.map((p, i) => (
                  <div key={i} className="flex gap-2 items-center">
                    <input
                      value={p.label}
                      placeholder="Label"
                      onChange={(e) =>
                        set({
                          pairs: d.pairs.map((x, j) =>
                            j === i ? { ...x, label: e.target.value } : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <select
                      value={p.anchor_id}
                      onChange={(e) =>
                        set({
                          pairs: d.pairs.map((x, j) =>
                            j === i ? { ...x, anchor_id: e.target.value } : x,
                          ),
                        })
                      }
                      className={input}
                    >
                      <option value="">— anchor —</option>
                      {anchorOptions.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.label}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() =>
                        set({ pairs: d.pairs.filter((_, j) => j !== i) })
                      }
                      className="text-red-500"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() =>
                    set({ pairs: [...d.pairs, { label: "", anchor_id: "" }] })
                  }
                  className="text-xs text-blue-600 hover:underline text-left"
                >
                  + Add label to match
                </button>
              </div>
            )}
            {d.task_type === "identify" && (
              <div className={rows}>
                {d.prompts.map((p, i) => (
                  <div key={i} className="flex gap-2 items-center">
                    <input
                      value={p.condition}
                      placeholder="Condition, e.g. the part farthest from the base"
                      onChange={(e) =>
                        set({
                          prompts: d.prompts.map((x, j) =>
                            j === i ? { ...x, condition: e.target.value } : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <select
                      value={p.anchor_id}
                      onChange={(e) =>
                        set({
                          prompts: d.prompts.map((x, j) =>
                            j === i ? { ...x, anchor_id: e.target.value } : x,
                          ),
                        })
                      }
                      className={input}
                    >
                      <option value="">— anchor —</option>
                      {anchorOptions.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.label}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() =>
                        set({ prompts: d.prompts.filter((_, j) => j !== i) })
                      }
                      className="text-red-500"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() =>
                    set({
                      prompts: [...d.prompts, { condition: "", anchor_id: "" }],
                    })
                  }
                  className="text-xs text-blue-600 hover:underline text-left"
                >
                  + Add prompt
                </button>
              </div>
            )}
            {usesParams && (
              <div className={rows}>
                <p className="text-xs text-gray-500">
                  Parameters the learner controls — named in the subject's
                  language (angle, radius, field strength), never solver terms.
                </p>
                {d.parameters.map((p, i) => (
                  <div key={i} className="grid grid-cols-6 gap-1 items-center">
                    <input
                      value={p.label}
                      placeholder="Label"
                      onChange={(e) =>
                        set({
                          parameters: d.parameters.map((x, j) =>
                            j === i
                              ? {
                                  ...x,
                                  label: e.target.value,
                                  id: x.id || slug(e.target.value),
                                }
                              : x,
                          ),
                        })
                      }
                      className={`${input} col-span-2`}
                    />
                    <input
                      type="number"
                      value={p.min}
                      placeholder="min"
                      onChange={(e) =>
                        set({
                          parameters: d.parameters.map((x, j) =>
                            j === i ? { ...x, min: Number(e.target.value) } : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <input
                      type="number"
                      value={p.max}
                      placeholder="max"
                      onChange={(e) =>
                        set({
                          parameters: d.parameters.map((x, j) =>
                            j === i ? { ...x, max: Number(e.target.value) } : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <input
                      value={p.unit || ""}
                      placeholder="unit"
                      onChange={(e) =>
                        set({
                          parameters: d.parameters.map((x, j) =>
                            j === i ? { ...x, unit: e.target.value } : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <button
                      type="button"
                      onClick={() =>
                        set({
                          parameters: d.parameters.filter((_, j) => j !== i),
                        })
                      }
                      className="text-red-500 justify-self-center"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() =>
                    set({
                      parameters: [
                        ...d.parameters,
                        {
                          id: `p${d.parameters.length + 1}`,
                          label: "",
                          min: 0,
                          max: 100,
                          unit: "",
                        },
                      ],
                    })
                  }
                  className="text-xs text-blue-600 hover:underline text-left"
                >
                  + Add parameter
                </button>
              </div>
            )}
            {d.task_type === "verify" && (
              <div className={rows}>
                <input
                  value={d.claim}
                  placeholder="The claim to test"
                  onChange={(e) => set({ claim: e.target.value })}
                  className={input}
                />
                <label className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={d.claim_holds}
                    onChange={(e) => set({ claim_holds: e.target.checked })}
                  />{" "}
                  The claim is true
                </label>
                <RangeList
                  label="Expected final state (3 pts)"
                  rows={d.expected_state}
                  params={d.parameters}
                  onChange={(r) => set({ expected_state: r })}
                />
                <RangeList
                  label="Range the path must explore to count as having tested the claim (2 pts)"
                  rows={d.must_explore}
                  params={d.parameters}
                  onChange={(r) => set({ must_explore: r })}
                />
              </div>
            )}
            {d.task_type === "manipulate" && (
              <div className={rows}>
                {d.targets.map((t, i) => (
                  <div key={i} className="grid grid-cols-6 gap-1 items-center">
                    <input
                      value={t.prompt}
                      placeholder="Prompt"
                      onChange={(e) =>
                        set({
                          targets: d.targets.map((x, j) =>
                            j === i ? { ...x, prompt: e.target.value } : x,
                          ),
                        })
                      }
                      className={`${input} col-span-2`}
                    />
                    <select
                      value={t.param_id}
                      onChange={(e) =>
                        set({
                          targets: d.targets.map((x, j) =>
                            j === i ? { ...x, param_id: e.target.value } : x,
                          ),
                        })
                      }
                      className={input}
                    >
                      <option value="">param</option>
                      {d.parameters.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.label || p.id}
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      value={t.min}
                      onChange={(e) =>
                        set({
                          targets: d.targets.map((x, j) =>
                            j === i ? { ...x, min: Number(e.target.value) } : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <input
                      type="number"
                      value={t.max}
                      onChange={(e) =>
                        set({
                          targets: d.targets.map((x, j) =>
                            j === i ? { ...x, max: Number(e.target.value) } : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <button
                      type="button"
                      onClick={() =>
                        set({ targets: d.targets.filter((_, j) => j !== i) })
                      }
                      className="text-red-500 justify-self-center"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() =>
                    set({
                      targets: [
                        ...d.targets,
                        { prompt: "", param_id: "", min: 0, max: 0 },
                      ],
                    })
                  }
                  className="text-xs text-blue-600 hover:underline text-left"
                >
                  + Add target
                </button>
              </div>
            )}
            {d.task_type === "assemble" && (
              <div className={rows}>
                <p className="text-xs text-gray-500">
                  Slots (positions) and parts; each part names its correct slot.
                </p>
                {d.slots.map((s, i) => (
                  <div key={i} className="flex gap-2">
                    <input
                      value={s.label}
                      placeholder="Slot label"
                      onChange={(e) =>
                        set({
                          slots: d.slots.map((x, j) =>
                            j === i
                              ? {
                                  ...x,
                                  label: e.target.value,
                                  id: x.id || slug(e.target.value),
                                }
                              : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <button
                      type="button"
                      onClick={() =>
                        set({ slots: d.slots.filter((_, j) => j !== i) })
                      }
                      className="text-red-500"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() =>
                    set({
                      slots: [
                        ...d.slots,
                        { id: `slot${d.slots.length + 1}`, label: "" },
                      ],
                    })
                  }
                  className="text-xs text-blue-600 hover:underline text-left"
                >
                  + Add slot
                </button>
                {d.parts.map((p, i) => (
                  <div key={i} className="flex gap-2">
                    <input
                      value={p.label}
                      placeholder="Part label"
                      onChange={(e) =>
                        set({
                          parts: d.parts.map((x, j) =>
                            j === i
                              ? {
                                  ...x,
                                  label: e.target.value,
                                  id: x.id || slug(e.target.value),
                                }
                              : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <select
                      value={p.slot_id}
                      onChange={(e) =>
                        set({
                          parts: d.parts.map((x, j) =>
                            j === i ? { ...x, slot_id: e.target.value } : x,
                          ),
                        })
                      }
                      className={input}
                    >
                      <option value="">— correct slot —</option>
                      {d.slots.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.label || s.id}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() =>
                        set({ parts: d.parts.filter((_, j) => j !== i) })
                      }
                      className="text-red-500"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() =>
                    set({
                      parts: [
                        ...d.parts,
                        {
                          id: `part${d.parts.length + 1}`,
                          label: "",
                          slot_id: "",
                        },
                      ],
                    })
                  }
                  className="text-xs text-blue-600 hover:underline text-left"
                >
                  + Add part
                </button>
              </div>
            )}
            {d.task_type === "measure" && (
              <div className={rows}>
                {d.questions.map((q, i) => (
                  <div key={i} className="grid grid-cols-6 gap-1 items-center">
                    <input
                      value={q.prompt}
                      placeholder="Prompt"
                      onChange={(e) =>
                        set({
                          questions: d.questions.map((x, j) =>
                            j === i ? { ...x, prompt: e.target.value } : x,
                          ),
                        })
                      }
                      className={`${input} col-span-2`}
                    />
                    <input
                      type="number"
                      step="any"
                      value={q.answer}
                      placeholder="answer"
                      onChange={(e) =>
                        set({
                          questions: d.questions.map((x, j) =>
                            j === i
                              ? { ...x, answer: Number(e.target.value) }
                              : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <input
                      type="number"
                      step="any"
                      value={q.tolerance}
                      placeholder="±"
                      onChange={(e) =>
                        set({
                          questions: d.questions.map((x, j) =>
                            j === i
                              ? { ...x, tolerance: Number(e.target.value) }
                              : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <input
                      value={q.unit}
                      placeholder="unit"
                      onChange={(e) =>
                        set({
                          questions: d.questions.map((x, j) =>
                            j === i ? { ...x, unit: e.target.value } : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <button
                      type="button"
                      onClick={() =>
                        set({
                          questions: d.questions.filter((_, j) => j !== i),
                        })
                      }
                      className="text-red-500 justify-self-center"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() =>
                    set({
                      questions: [
                        ...d.questions,
                        {
                          prompt: "",
                          answer: 0,
                          tolerance: 0,
                          unit: "",
                          anchor_a: "",
                          anchor_b: "",
                        },
                      ],
                    })
                  }
                  className="text-xs text-blue-600 hover:underline text-left"
                >
                  + Add measurement
                </button>
              </div>
            )}
            {d.task_type === "sequence" && (
              <div className={rows}>
                <p className="text-xs text-gray-500">
                  Enter the steps in the CORRECT order; the player shuffles
                  them.
                </p>
                {d.steps.map((s, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-gray-400 self-center">{i + 1}.</span>
                    <input
                      value={s.text}
                      placeholder="Step"
                      onChange={(e) =>
                        set({
                          steps: d.steps.map((x, j) =>
                            j === i ? { ...x, text: e.target.value } : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <button
                      type="button"
                      onClick={() =>
                        set({ steps: d.steps.filter((_, j) => j !== i) })
                      }
                      className="text-red-500"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() =>
                    set({
                      steps: [
                        ...d.steps,
                        { id: `s${d.steps.length + 1}`, text: "" },
                      ],
                    })
                  }
                  className="text-xs text-blue-600 hover:underline text-left"
                >
                  + Add step
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ---- annotation placer */}
        <div className="space-y-3">
          <div
            className="rounded-xl border border-gray-200 bg-white p-4"
            data-glass="work"
          >
            <h2 className="font-semibold text-gray-900 mb-1">
              Anchors {usesAnchors ? "(required)" : "(optional markers)"}
            </h2>
            <p className="text-xs text-gray-500 mb-2">
              Click the model surface to place an anchor. Positions are stored
              relative to the model, so they survive rescaling. Learners see
              neutral region numbers, never your labels.
            </p>
            {d.model_id ? (
              <ThreeDViewer
                modelId={d.model_id}
                height={340}
                anchors={d.anchors}
                onPickPoint={addAnchor}
              />
            ) : (
              <div className="h-40 grid place-items-center text-sm text-gray-400 border border-dashed rounded-lg">
                Choose a model to start placing anchors
              </div>
            )}
            {d.anchors.length > 0 && (
              <ul className="mt-3 space-y-1 text-sm">
                {d.anchors.map((a, i) => (
                  <li key={a.id} className="flex gap-2 items-center">
                    <span className="w-6 h-6 rounded-full bg-blue-600 text-white text-xs grid place-items-center">
                      {i + 1}
                    </span>
                    <input
                      value={a.label}
                      onChange={(e) =>
                        set({
                          anchors: d.anchors.map((x, j) =>
                            j === i ? { ...x, label: e.target.value } : x,
                          ),
                        })
                      }
                      className={`${input} w-40`}
                      aria-label="Anchor label"
                    />
                    <input
                      value={a.description || ""}
                      placeholder="Hint shown to learners (optional)"
                      onChange={(e) =>
                        set({
                          anchors: d.anchors.map((x, j) =>
                            j === i ? { ...x, description: e.target.value } : x,
                          ),
                        })
                      }
                      className={input}
                    />
                    <button
                      type="button"
                      onClick={() =>
                        set({ anchors: d.anchors.filter((_, j) => j !== i) })
                      }
                      className="text-red-500"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  );
}

function RangeList({
  label,
  rows,
  params,
  onChange,
}: {
  label: string;
  rows: { param_id: string; min: number; max: number }[];
  params: Parameter[];
  onChange: (r: { param_id: string; min: number; max: number }[]) => void;
}) {
  const input = "px-2 py-1 border border-gray-300 rounded w-full";
  return (
    <div className="space-y-1">
      <p className="text-xs text-gray-600">{label}</p>
      {rows.map((r, i) => (
        <div key={i} className="grid grid-cols-4 gap-1 items-center">
          <select
            value={r.param_id}
            onChange={(e) =>
              onChange(
                rows.map((x, j) =>
                  j === i ? { ...x, param_id: e.target.value } : x,
                ),
              )
            }
            className={input}
          >
            <option value="">param</option>
            {params.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label || p.id}
              </option>
            ))}
          </select>
          <input
            type="number"
            step="any"
            value={r.min}
            onChange={(e) =>
              onChange(
                rows.map((x, j) =>
                  j === i ? { ...x, min: Number(e.target.value) } : x,
                ),
              )
            }
            className={input}
          />
          <input
            type="number"
            step="any"
            value={r.max}
            onChange={(e) =>
              onChange(
                rows.map((x, j) =>
                  j === i ? { ...x, max: Number(e.target.value) } : x,
                ),
              )
            }
            className={input}
          />
          <button
            type="button"
            onClick={() => onChange(rows.filter((_, j) => j !== i))}
            className="text-red-500 justify-self-center"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() =>
          onChange([...rows, { param_id: params[0]?.id || "", min: 0, max: 0 }])
        }
        className="text-xs text-blue-600 hover:underline"
      >
        + Add range
      </button>
    </div>
  );
}

export default InstructorThreeDTasksPage;
