import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Download, Upload, Plus, Save, Eye, FlaskConical } from "lucide-react";
import toast from "react-hot-toast";
import {
  labStudio,
  downloadLabFile,
  type LabDraft,
  type LabDraftInput,
  type LabEngine,
  type Chapter,
} from "@/api/lab-studio";
import { getLab } from "@/api/labs";
import type { ConceptConfig } from "@/api/lab-studio";
import { ConceptLabPlayer } from "@/components/labs/ConceptLabPlayer";
import { ThreeDModelPicker } from "@/components/three-d/ThreeDModelPicker";
import { GuidedLabAuthor } from "@/components/labs/GuidedLabAuthor";
import { SuppliedLabPack } from "@/components/labs/SuppliedLabPack";
import { engines, templateConfig } from "@/components/labs/concept-templates";

const initial = (): LabDraftInput => ({
  title: "My guided lab investigation",
  subject: "mathematics",
  description: "",
  config: templateConfig("supplied"),
});
export default function LabStudioPage() {
  const [params] = useSearchParams(),
    chapter = params.get("chapter"),
    template = params.get("template");
  const [draft, setDraft] = useState<LabDraftInput>(initial),
    [saved, setSaved] = useState<LabDraft | null>(null);
  const [library, setLibrary] = useState<LabDraft[]>([]),
    [chapters, setChapters] = useState<Chapter[]>([]);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [preview, setPreview] = useState(false);
  const [supplied, setSupplied] = useState<{ slug: string; title: string }[]>(
    [],
  );
  const upload = useRef<HTMLInputElement>(null);
  useEffect(() => {
    let live = true;
    Promise.all([
      labStudio.drafts(),
      labStudio.curriculum(),
      template ? getLab(template) : Promise.resolve(null),
    ])
      .then(([labs, c, source]) => {
        if (!live) return;
        setLibrary(labs);
        setChapters(c.chapters);
        setSupplied(c.labs);
        const selected = c.chapters.find((x) => x.id === chapter);
        if (source?.native_template === "concept_lab")
          setDraft({
            title: source.title,
            subject: source.subject,
            description: source.description || "",
            config: source.config as ConceptConfig,
          });
        else if (selected)
          setDraft((d) => ({
            ...d,
            title: selected.title,
            subject: selected.subject,
            config: { ...d.config, chapter_ids: [selected.id] },
          }));
      })
      .catch(() => {
        if (live) setError("Could not load your drafts. Reload to retry.");
      });
    return () => {
      live = false;
    };
  }, [chapter, template]);
  const patchConfig = (patch: Partial<LabDraftInput["config"]>) => {
    setDraft((d) => ({ ...d, config: { ...d.config, ...patch } }));
    setPreview(false);
  };
  const merge = (row: LabDraft) => {
    setSaved(row);
    setLibrary((l) => [row, ...l.filter((x) => x.slug !== row.slug)]);
  };
  async function save(publish = false) {
    setBusy(true);
    setError("");
    try {
      let row = saved
        ? await labStudio.update(saved.slug, draft)
        : await labStudio.create(draft);
      merge(row);
      if (publish) {
        row = await labStudio.publish(row.slug, true);
        merge(row);
      }
      toast.success(
        publish ? "Lab published to the lesson picker" : "Lab saved",
      );
    } catch {
      setError(
        "Could not save. Check the objective, prediction, investigation steps and classification groups. Your edits remain here.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function importFile(file?: File) {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const labs = await labStudio.import(file);
      setLibrary((l) => [...labs, ...l]);
      toast.success(`${labs.length} labs imported as new drafts`);
    } catch {
      setError(
        "Import failed. Use a Sasha lab JSON pack under 1 MB or GLB ZIP backup under 52 MB. No partial import was kept.",
      );
    } finally {
      setBusy(false);
      if (upload.current) upload.current.value = "";
    }
  }
  async function exportFile() {
    if (!saved) return;
    try {
      downloadLabFile(
        await labStudio.export(saved.slug),
        `${saved.slug}.sasha-labs.${saved.config.model_id ? "zip" : "json"}`,
      );
    } catch {
      toast.error("Could not export the saved lab");
    }
  }
  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <span className="sf-eyebrow">Content studio / Learning labs</span>
            <h1>Build a place to discover.</h1>
            <p className="sf-muted">
              Choose a tested model, write an investigation, and connect it to
              your curriculum.
            </p>
          </div>
          <Link className="sf-secondary" to="/labs">
            Explore library
          </Link>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-lab-studio"
    >
      <SuppliedLabPack />
      <div className="sf-studio-grid">
        <aside className="sf-surface lab-draft-list">
          <div className="sf-section-heading">
            <h2>Your labs</h2>
            <button
              className="sf-icon-button"
              disabled={busy}
              aria-label="New lab"
              onClick={() => {
                setSaved(null);
                setDraft(initial());
                setPreview(false);
              }}
            >
              <Plus size={18} />
            </button>
          </div>
          <button
            className="sf-secondary"
            disabled={busy}
            onClick={() => upload.current?.click()}
          >
            <Upload size={16} /> Import lab pack
          </button>

          <input
            ref={upload}
            type="file"
            accept=".json,.zip,application/json,application/zip"
            hidden
            onChange={(e) => importFile(e.target.files?.[0])}
          />
          {library.map((l) => (
            <button
              key={l.slug}
              aria-pressed={saved?.slug === l.slug}
              className="lab-draft"
              disabled={busy}
              onClick={() => {
                setSaved(l);
                setDraft({
                  title: l.title,
                  subject: l.subject,
                  description: l.description || "",
                  config: l.config,
                });
                setPreview(false);
              }}
            >
              <FlaskConical size={17} />
              <span>
                {l.title}
                <small>{l.is_published ? "Published" : "Draft"}</small>
              </span>
            </button>
          ))}
          {!library.length && (
            <p className="sf-muted">
              Your saved and imported experiments appear here.
            </p>
          )}
        </aside>
        <section className="sf-surface">
          <div className="sf-section-heading">
            <h2>{saved ? "Edit experiment" : "New experiment"}</h2>
            <span className="sf-chip">
              {saved?.is_published
                ? "Published · saves update the live lab"
                : "Private draft"}
            </span>
          </div>
          {error && (
            <p role="alert" className="sf-alert">
              {error}
            </p>
          )}
          <fieldset disabled={busy} className="sf-form-fields">
            <label className="sf-field">
              <span>Lab title</span>
              <input
                value={draft.title}
                maxLength={200}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, title: e.target.value }))
                }
              />
            </label>
            <div className="sf-two-columns">
              <label className="sf-field">
                <span>Subject</span>
                <select
                  value={draft.subject}
                  onChange={(e) =>
                    setDraft((d) => ({ ...d, subject: e.target.value }))
                  }
                >
                  {[
                    "science",
                    "mathematics",
                    "physics",
                    "chemistry",
                    "biology",
                    "general",
                  ].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
              <label className="sf-field">
                <span>Experiment model</span>
                <select
                  value={draft.config.engine}
                  onChange={(e) =>
                    patchConfig({
                      ...templateConfig(e.target.value as LabEngine),
                      chapter_ids: draft.config.chapter_ids,
                    })
                  }
                >
                  {engines
                    .filter(
                      (e) =>
                        e.id === "supplied" || e.id === draft.config.engine,
                    )
                    .map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.label}
                      </option>
                    ))}
                </select>
              </label>
            </div>
            {draft.config.engine === "supplied" && (
              <label className="sf-field">
                Your simulation
                <select
                  value={draft.config.source_slug || ""}
                  onChange={(e) => patchConfig({ source_slug: e.target.value })}
                >
                  {supplied.map((l) => (
                    <option key={l.slug} value={l.slug}>
                      {l.title}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="sf-field">
              <span>Curriculum chapter (optional)</span>
              <select
                value={draft.config.chapter_ids[0] || ""}
                onChange={(e) =>
                  patchConfig({
                    chapter_ids: e.target.value ? [e.target.value] : [],
                  })
                }
              >
                <option value="">Independent concept</option>
                {chapters.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.edition === "legacy"
                      ? "Earlier curriculum"
                      : "Updated curriculum"}{" "}
                    · Class {c.grade} · {c.subject} · {c.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="sf-field">
              <span>Library description</span>
              <textarea
                value={draft.description}
                maxLength={2000}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, description: e.target.value }))
                }
              />
            </label>
            <label className="sf-field">
              <span>Learning objective</span>
              <textarea
                value={draft.config.objective}
                maxLength={1200}
                onChange={(e) => patchConfig({ objective: e.target.value })}
              />
            </label>
            <label className="sf-field">
              <span>Prediction prompt</span>
              <input
                value={draft.config.prediction}
                maxLength={600}
                onChange={(e) => patchConfig({ prediction: e.target.value })}
              />
            </label>
            <label className="sf-field">
              <span>Investigation steps (one per line, up to 8)</span>
              <textarea
                value={draft.config.investigation.join("\n")}
                onChange={(e) =>
                  patchConfig({ investigation: e.target.value.split("\n") })
                }
              />
            </label>
            <label className="sf-field">
              <span>Explanation and model limitations</span>
              <textarea
                value={draft.config.explanation}
                maxLength={3000}
                onChange={(e) => patchConfig({ explanation: e.target.value })}
              />
            </label>
            {draft.config.engine === "classification" && (
              <div>
                <h3>Classification cards</h3>
                <p className="sf-muted">
                  At least 3 examples and 2 groups. Each card must have a unique
                  label.
                </p>
                {draft.config.cards.map((card, i) => (
                  <div className="lab-card-editor" key={i}>
                    <input
                      aria-label={`Card ${i + 1} label`}
                      placeholder="Example"
                      value={card.label}
                      onChange={(e) =>
                        patchConfig({
                          cards: draft.config.cards.map((c, j) =>
                            j === i ? { ...c, label: e.target.value } : c,
                          ),
                        })
                      }
                    />
                    <input
                      aria-label={`Card ${i + 1} group`}
                      placeholder="Group"
                      value={card.group}
                      onChange={(e) =>
                        patchConfig({
                          cards: draft.config.cards.map((c, j) =>
                            j === i ? { ...c, group: e.target.value } : c,
                          ),
                        })
                      }
                    />
                    <input
                      aria-label={`Card ${i + 1} explanation`}
                      placeholder="Why it belongs here"
                      value={card.explanation}
                      onChange={(e) =>
                        patchConfig({
                          cards: draft.config.cards.map((c, j) =>
                            j === i ? { ...c, explanation: e.target.value } : c,
                          ),
                        })
                      }
                    />
                    <button
                      className="sf-icon-button"
                      aria-label={`Remove card ${i + 1}`}
                      onClick={() =>
                        patchConfig({
                          cards: draft.config.cards.filter((_, j) => i !== j),
                        })
                      }
                    >
                      ×
                    </button>
                  </div>
                ))}
                <button
                  className="sf-secondary"
                  disabled={draft.config.cards.length >= 30}
                  onClick={() =>
                    patchConfig({
                      cards: [
                        ...draft.config.cards,
                        { label: "", group: "", explanation: "" },
                      ],
                    })
                  }
                >
                  Add card
                </button>
              </div>
            )}
            <section className="astra-model-guide" aria-label="Lab 3D model">
              <h3>Add a 3D model to this investigation</h3>
              <p>
                Upload a self-contained GLB with embedded textures, or choose a
                library model. Save to attach it; publishing makes the model
                available with this lab. ZIP backups include the model.
              </p>
              <ThreeDModelPicker
                title={draft.title}
                attachedId={draft.config.model_id ?? null}
                onAttach={(id) =>
                  patchConfig({
                    model_id: id || null,
                    ...(!id
                      ? {
                          hotspots: [],
                          guided_steps: (
                            draft.config.guided_steps || []
                          ).filter(
                            (s) => !["visit", "parameter"].includes(s.kind),
                          ),
                          assessment_enabled: false,
                        }
                      : {}),
                  })
                }
              />
            </section>
            <GuidedLabAuthor
              config={draft.config}
              patch={patchConfig}
              slug={saved?.slug}
            />
            <div className="sf-actions">
              <button className="sf-primary" onClick={() => save()}>
                <Save size={16} /> Save lab
              </button>
              <button
                className="sf-secondary"
                onClick={() => setPreview((p) => !p)}
              >
                <Eye size={16} />{" "}
                {preview ? "Close preview" : "Preview experiment"}
              </button>
              <button className="sf-secondary" onClick={() => save(true)}>
                Save & publish
              </button>
              {saved && (
                <button className="sf-secondary" onClick={exportFile}>
                  <Download size={16} /> Export saved lab
                </button>
              )}
              {saved?.is_published && (
                <button
                  className="sf-secondary"
                  onClick={async () => {
                    setBusy(true);
                    try {
                      merge(await labStudio.publish(saved.slug, false));
                    } catch {
                      toast.error("Could not unpublish");
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Unpublish
                </button>
              )}
            </div>
          </fieldset>
          <p className="sf-muted">
            Publish makes this lab available in the shared catalog and course
            lesson picker. Saving a published lab updates its current content.
            Exports contain the last saved version.
          </p>
        </section>
      </div>
      {preview && (
        <section className="sf-surface">
          <ConceptLabPlayer title={draft.title} config={draft.config} />
        </section>
      )}
    </PageLayout>
  );
}
