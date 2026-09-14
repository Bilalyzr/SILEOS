import { lazy, Suspense, useState } from "react";
import type { ConceptConfig, LabHotspot, LabStep } from "@/api/lab-studio";
import { api } from "@/api/axios";
const Viewer = lazy(() =>
  import("@/components/three-d/ThreeDViewer").then((m) => ({
    default: m.ThreeDViewer,
  })),
);

export function GuidedLabAuthor({
  config,
  patch,
  slug,
}: {
  config: ConceptConfig;
  patch: (v: Partial<ConceptConfig>) => void;
  slug?: string;
}) {
  const [placing, setPlacing] = useState(false);
  const [review, setReview] = useState<any[] | null>(null);
  const [error, setError] = useState("");
  const hotspots = config.hotspots || [],
    steps = config.guided_steps || [];
  function hotspot(id: string, value: Partial<LabHotspot>) {
    patch({
      hotspots: hotspots.map((h) => (h.id === id ? { ...h, ...value } : h)),
    });
  }
  function step(id: string, value: Partial<LabStep>) {
    patch({
      guided_steps: steps.map((s) => (s.id === id ? { ...s, ...value } : s)),
    });
  }
  return (
    <section className="space-y-4" aria-label="Guided lab authoring">
      <h2>Guided investigation & assessment</h2>
      <p>
        Labels and observation prompts work with keyboard and screen readers.
        Questions and control targets receive server-checked formative scores.
      </p>
      <label className="sf-field">
        Concept tags (comma separated)
        <input
          value={(config.concepts || []).join(", ")}
          onChange={(e) =>
            patch({
              concepts: e.target.value
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean),
            })
          }
        />
      </label>
      <label className="sf-field">
        Model text description
        <textarea
          value={config.model_description || ""}
          onChange={(e) => patch({ model_description: e.target.value })}
        />
      </label>
      <label className="sf-field">
        Model description · தமிழ்
        <textarea
          lang="ta"
          value={config.model_description_ta || ""}
          onChange={(e) => patch({ model_description_ta: e.target.value })}
        />
      </label>
      {config.model_id && (
        <>
          <button
            type="button"
            className="sf-secondary"
            onClick={() => setPlacing(!placing)}
          >
            {placing ? "Close label placer" : "Place labels on model"}
          </button>
          {placing && (
            <Suspense fallback={<p>Loading model…</p>}>
              <Viewer
                modelId={config.model_id}
                anchors={hotspots}
                onPickPoint={(position) => {
                  if (hotspots.length < 30)
                    patch({
                      hotspots: [
                        ...hotspots,
                        {
                          id: crypto.randomUUID(),
                          label: `Label ${hotspots.length + 1}`,
                          explanation: "",
                          position,
                        },
                      ],
                    });
                }}
              />
            </Suspense>
          )}
          <p>
            Click a model surface to place a label. Each label also appears as
            an accessible text button.
          </p>
        </>
      )}
      {hotspots.map((h) => (
        <fieldset key={h.id} className="sf-surface space-y-2">
          <legend>{h.label}</legend>
          <input
            aria-label="Label name"
            value={h.label}
            onChange={(e) => hotspot(h.id, { label: e.target.value })}
          />
          <input
            aria-label="Tamil label"
            lang="ta"
            placeholder="தமிழ் பெயர்"
            value={h.label_ta || ""}
            onChange={(e) => hotspot(h.id, { label_ta: e.target.value })}
          />
          <textarea
            aria-label="Label explanation"
            value={h.explanation}
            onChange={(e) => hotspot(h.id, { explanation: e.target.value })}
          />
          <textarea
            aria-label="Tamil label explanation"
            lang="ta"
            value={h.explanation_ta || ""}
            onChange={(e) => hotspot(h.id, { explanation_ta: e.target.value })}
          />
          <button
            type="button"
            className="sf-secondary"
            onClick={() =>
              patch({
                hotspots: hotspots.filter((v) => v.id !== h.id),
                guided_steps: steps.filter((s) => s.hotspot_id !== h.id),
              })
            }
          >
            Remove label & linked steps
          </button>
        </fieldset>
      ))}
      {steps.map((s, i) => (
        <fieldset key={s.id} className="sf-surface space-y-2">
          <legend>
            Step {i + 1} · {s.kind}
          </legend>
          <label className="sf-field">
            Title
            <input
              value={s.title}
              onChange={(e) => step(s.id, { title: e.target.value })}
            />
          </label>
          <label className="sf-field">
            Instructions
            <textarea
              value={s.instruction}
              onChange={(e) => step(s.id, { instruction: e.target.value })}
            />
          </label>
          <details>
            <summary>Tamil text</summary>
            <input
              aria-label="Tamil step title"
              lang="ta"
              value={s.title_ta || ""}
              onChange={(e) => step(s.id, { title_ta: e.target.value })}
            />
            <textarea
              aria-label="Tamil instructions"
              lang="ta"
              value={s.instruction_ta || ""}
              onChange={(e) => step(s.id, { instruction_ta: e.target.value })}
            />
          </details>
          {s.kind === "visit" && (
            <label className="sf-field">
              Required label
              <select
                value={s.hotspot_id || ""}
                onChange={(e) => step(s.id, { hotspot_id: e.target.value })}
              >
                <option value="">Choose label</option>
                {hotspots.map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          {s.kind === "question" && (
            <>
              <label className="sf-field">
                Options (one per line)
                <textarea
                  value={s.options.join("\n")}
                  onChange={(e) =>
                    step(s.id, {
                      options: e.target.value.split("\n").slice(0, 6),
                    })
                  }
                />
              </label>
              <label className="sf-field">
                Correct answer
                <select
                  value={s.correct_index ?? 0}
                  onChange={(e) =>
                    step(s.id, { correct_index: Number(e.target.value) })
                  }
                >
                  {s.options.map((o, j) => (
                    <option key={j} value={j}>
                      {j + 1}. {o}
                    </option>
                  ))}
                </select>
              </label>
            </>
          )}
          {s.kind === "parameter" && (
            <>
              <label>
                Control
                <select
                  value={s.parameter || "rotation_y"}
                  onChange={(e) => {
                    const v = e.target.value as
                      | "rotation_y"
                      | "scale"
                      | "explode";
                    step(s.id, {
                      parameter: v,
                      target_min: v === "scale" ? 1 : 0,
                      target_max: v === "scale" ? 1 : 0,
                    });
                  }}
                >
                  <option value="rotation_y">Rotation (degrees)</option>
                  <option value="scale">Scale</option>
                  <option value="explode">Separate parts (0–1)</option>
                </select>
              </label>
              <label>
                Target minimum
                <input
                  type="number"
                  step="0.1"
                  value={s.target_min ?? 0}
                  onChange={(e) =>
                    step(s.id, { target_min: Number(e.target.value) })
                  }
                />
              </label>
              <label>
                Target maximum
                <input
                  type="number"
                  step="0.1"
                  value={s.target_max ?? 0}
                  onChange={(e) =>
                    step(s.id, { target_max: Number(e.target.value) })
                  }
                />
              </label>
            </>
          )}
          {s.kind !== "observation" && (
            <label>
              Points
              <input
                type="number"
                min={0}
                max={20}
                value={s.points}
                onChange={(e) => step(s.id, { points: Number(e.target.value) })}
              />
            </label>
          )}
          <button
            className="sf-secondary"
            type="button"
            onClick={() =>
              patch({ guided_steps: steps.filter((v) => v.id !== s.id) })
            }
          >
            Remove step
          </button>
        </fieldset>
      ))}
      <div className="sf-actions">
        {(["visit", "parameter", "question", "observation"] as const).map(
          (kind) => (
            <button
              key={kind}
              type="button"
              className="sf-secondary"
              disabled={
                steps.length >= 30 ||
                (["visit", "parameter"].includes(kind) && !config.model_id)
              }
              onClick={() =>
                patch({
                  guided_steps: [
                    ...steps,
                    {
                      id: crypto.randomUUID(),
                      kind,
                      title: `New ${kind} step`,
                      instruction: "",
                      options:
                        kind === "question" ? ["Option A", "Option B"] : [],
                      correct_index: kind === "question" ? 0 : null,
                      points: kind === "question" ? 1 : 0,
                      ...(kind === "parameter"
                        ? {
                            parameter: "rotation_y" as const,
                            target_min: 0,
                            target_max: 0,
                          }
                        : {}),
                    },
                  ],
                })
              }
            >
              Add {kind}
            </button>
          ),
        )}
      </div>
      <label className="flex gap-2">
        <input
          type="checkbox"
          checked={!!config.assessment_enabled}
          onChange={(e) => patch({ assessment_enabled: e.target.checked })}
        />{" "}
        Enable assessment for student submissions and the quiz builder
      </label>
      {slug && (
        <button
          className="sf-secondary"
          type="button"
          onClick={async () => {
            try {
              setReview(
                (await api.get(`/lab-studio/labs/${slug}/attempts`)).data
                  .attempts,
              );
              setError("");
            } catch {
              setError("Could not load submissions.");
            }
          }}
        >
          Review latest 100 submissions
        </button>
      )}
      {error && <p role="alert">{error}</p>}
      {review && (
        <div>
          {review.length === 0 ? (
            <p>No submissions yet.</p>
          ) : (
            review.map((r) => (
              <details key={r.id}>
                <summary>
                  Student {r.user_id} · {r.score}/{r.max_score} ·{" "}
                  {new Date(r.created_at).toLocaleString()}
                </summary>
                {Object.entries(r.evidence.observations || {}).map(
                  ([id, text]) => (
                    <p key={id}>
                      {steps.find((s) => s.id === id)?.title ||
                        "Earlier activity step"}
                      : {String(text)}
                    </p>
                  ),
                )}
                <p className="sf-muted">Revision {r.revision.slice(0, 12)}</p>
              </details>
            ))
          )}
        </div>
      )}
    </section>
  );
}
