import { lazy, Suspense, useState } from "react";
import type { ConceptConfig } from "@/api/lab-studio";
import { api } from "@/api/axios";
import { queueEvent, ownerId } from "@/offline/storage";
import { useLearningLanguage } from "./LearningPreferences";
const Viewer = lazy(() =>
  import("@/components/three-d/ThreeDViewer").then((m) => ({
    default: m.ThreeDViewer,
  })),
);
export function GuidedLabPlayer({
  config,
  slug,
  revision,
  sourceUrl,
  sourceBlob,
  previewOnly = false,
}: {
  config: ConceptConfig;
  slug?: string;
  revision?: string;
  sourceUrl?: string;
  sourceBlob?: Blob;
  previewOnly?: boolean;
}) {
  const language = useLearningLanguage(),
    ta = language === "ta";
  const [visited, setVisited] = useState<string[]>([]),
    [answers, setAnswers] = useState<Record<string, number>>({}),
    [parameters, setParameters] = useState<Record<string, number>>({}),
    [observations, setObservations] = useState<Record<string, string>>({});
  const [controls, setControls] = useState({
    rotation_y: 0,
    scale: 1,
    explode: 0,
    playing: false,
  });
  const [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [result, setResult] = useState<any>(null);
  function visit(id: string) {
    setVisited((v) => (v.includes(id) ? v : [...v, id]));
  }
  async function submit() {
    if (!slug || !revision || previewOnly) return;
    if (!ownerId()) {
      setMessage(
        ta
          ? "பதிவைச் சேமிக்க உள்நுழையவும்."
          : "Sign in to save an investigation.",
      );
      return;
    }
    setBusy(true);
    setResult(null);
    const body = {
      submission_id: crypto.randomUUID(),
      revision,
      visited,
      answers,
      parameters,
      observations,
    };
    const path = `/lab-studio/labs/${encodeURIComponent(slug)}/attempts`;
    try {
      if (!navigator.onLine) {
        await queueEvent(path, body);
        setMessage(
          ta
            ? "இணையம் வந்ததும் ஒத்திசைக்கப்படும்."
            : "Saved on this device. Sync when you reconnect.",
        );
      } else {
        const { data } = await api.post(path, body);
        setResult(data);
        setMessage(ta ? "பதிவு சேமிக்கப்பட்டது." : "Investigation saved.");
      }
    } catch (e: any) {
      if (!e.response) {
        try {
          await queueEvent(path, body);
          setMessage(
            "Connection interrupted. Your submission is queued for retry.",
          );
        } catch {
          setMessage(
            "Could not save on this device. Keep this page open and retry.",
          );
        }
      } else
        setMessage(
          e.response?.data?.detail ||
            "Submission failed. Your answers remain on this page.",
        );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      lang={language}
      className="space-y-4"
      aria-label="Guided investigation"
    >
      {config.model_id && (
        <>
          <Suspense fallback={<p role="status">Loading model…</p>}>
            <Viewer
              modelId={config.model_id}
              sourceUrl={sourceUrl}
                  sourceBlob={sourceBlob}
              enableXR
              anchors={config.hotspots || []}
              selectedIds={visited}
              onAnchorClick={visit}
              modelControls={controls}
              description={
                (ta && config.model_description_ta) || config.model_description
              }
            />
          </Suspense>
          <div className="sf-actions">
            <label>
              {ta ? "சுழற்சி" : "Rotation"}
              <input
                aria-label="Model rotation"
                type="range"
                min={-180}
                max={180}
                value={controls.rotation_y}
                onChange={(e) =>
                  setControls({
                    ...controls,
                    rotation_y: Number(e.target.value),
                  })
                }
              />
              {controls.rotation_y}°
            </label>
            <label>
              {ta ? "அளவு" : "Scale"}
              <input
                aria-label="Model scale"
                type="range"
                min={0.5}
                max={2}
                step={0.1}
                value={controls.scale}
                onChange={(e) =>
                  setControls({ ...controls, scale: Number(e.target.value) })
                }
              />
              {controls.scale}×
            </label>
            <label>
              {ta ? "பாகங்களைப் பிரி" : "Separate parts"}
              <input
                aria-label="Separate model parts"
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={controls.explode}
                onChange={(e) =>
                  setControls({ ...controls, explode: Number(e.target.value) })
                }
              />
            </label>
            <button
              type="button"
              className="sf-secondary"
              aria-pressed={controls.playing}
              onClick={() =>
                setControls({ ...controls, playing: !controls.playing })
              }
            >
              {controls.playing
                ? ta
                  ? "நிறுத்து"
                  : "Pause animation"
                : ta
                  ? "இயக்கு"
                  : "Play embedded animation"}
            </button>
          </div>
        </>
      )}
      {(config.hotspots || []).map((h) => (
        <div key={h.id}>
          <button
            type="button"
            className="sf-secondary"
            aria-pressed={visited.includes(h.id)}
            onClick={() => visit(h.id)}
          >
            {(ta && h.label_ta) || h.label}
          </button>
          {visited.includes(h.id) && (
            <p>{(ta && h.explanation_ta) || h.explanation}</p>
          )}
        </div>
      ))}
      {(config.guided_steps || []).map((s, i) => (
        <fieldset key={s.id} className="sf-surface space-y-2">
          <legend>
            {i + 1}. {(ta && s.title_ta) || s.title}
          </legend>
          <p>{(ta && s.instruction_ta) || s.instruction}</p>
          {s.kind === "visit" && (
            <p>
              {visited.includes(s.hotspot_id || "")
                ? ta
                  ? "பார்வையிடப்பட்டது"
                  : "Label explored"
                : ta
                  ? "குறிப்பிட்ட லேபிளைத் தேர்ந்தெடுக்கவும்."
                  : "Select the indicated model label above."}
            </p>
          )}
          {s.kind === "question" &&
            s.options.map((o, j) => (
              <label key={j} className="flex gap-2 items-center">
                <input
                  type="radio"
                  name={s.id}
                  checked={answers[s.id] === j}
                  onChange={() => setAnswers({ ...answers, [s.id]: j })}
                />
                {o}
              </label>
            ))}
          {s.kind === "parameter" && (
            <>
              <p>
                {s.parameter}: {s.target_min}–{s.target_max}
              </p>
              <button
                type="button"
                className="sf-secondary"
                onClick={() =>
                  setParameters({
                    ...parameters,
                    [s.id]: controls[s.parameter || "rotation_y"],
                  })
                }
              >
                {ta
                  ? "தற்போதைய மதிப்பைப் பதிவு செய்"
                  : "Record current control value"}
              </button>
              <output>{parameters[s.id] ?? "—"}</output>
            </>
          )}
          {s.kind === "observation" && (
            <textarea
              aria-label={(ta && s.title_ta) || s.title}
              maxLength={3000}
              value={observations[s.id] || ""}
              onChange={(e) =>
                setObservations({ ...observations, [s.id]: e.target.value })
              }
            />
          )}
          {result?.feedback?.find((f: any) => f.step_id === s.id) && (
            <p>
              {result.feedback.find((f: any) => f.step_id === s.id).earned}/
              {s.points} ·{" "}
              {result.feedback.find((f: any) => f.step_id === s.id).status}
            </p>
          )}
        </fieldset>
      ))}
      {!!config.guided_steps?.length && (
        <>
          <p className="sf-muted">
            {ta
              ? "பயிற்சி மதிப்பீடு. குறிப்புகள் ஆசிரியர் பார்வைக்கு சேமிக்கப்படும்."
              : "Formative assessment. Observations are saved for instructor review; interaction evidence is self-reported."}
          </p>
          <button
            className="sf-primary"
            type="button"
            disabled={busy || !slug || !revision || previewOnly}
            onClick={submit}
          >
            {config.assessment_enabled ? (ta ? "சமர்ப்பி" : "Submit investigation") : (ta ? "ஆய்வைப் பதிவுசெய்" : "Save investigation")}
          </button>
        </>
      )}
      {result && result.max_score > 0 && (
        <p role="status">
          {ta ? "மதிப்பெண்" : "Score"}: {result.score}/{result.max_score}
        </p>
      )}
      <p role="status">{message}</p>
    </section>
  );
}
