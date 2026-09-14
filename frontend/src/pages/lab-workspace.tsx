import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Download, Save } from "lucide-react";
import { PageBackButton } from '@/components/routing/PageBackButton';
import toast from "react-hot-toast";
import {
  labStudio,
  blankNotebook,
  downloadLabFile,
  type Notebook,
  type Trial,
  type ConceptConfig,
} from "@/api/lab-studio";
import { getLab, type LabDetail } from "@/api/labs";
import { ConceptLabPlayer } from "@/components/labs/ConceptLabPlayer";
import { VirtualLabPlayer } from "@/components/labs/VirtualLabPlayer";
import { useAuthStore } from "@/store/auth";

export default function LabWorkspace() {
  const { slug = "" } = useParams(),
    user = useAuthStore((s) => s.user);
  const [lab, setLab] = useState<LabDetail | null>(null),
    [error, setError] = useState("");
  const [notebook, setNotebook] = useState<Notebook>(blankNotebook),
    [ready, setReady] = useState(false),
    [saving, setSaving] = useState(false);
  useEffect(() => {
    let live = true;
    setLab(null);
    setError("");
    setReady(false);
    setNotebook(blankNotebook());
    const load = async () => {
      const curriculum = await labStudio.curriculum();
      const bundled = curriculum.labs.find((l) => l.slug === slug);
      const detail: LabDetail = bundled
        ? {
            ...bundled,
            provider: "embed",
            sim: slug,
            source: "Your CBSE Virtual Labs · hosted by SashaInfinity",
          }
        : await getLab(slug);
      if (live) setLab(detail);
      if (user) {
        const saved = await labStudio.notebook(slug);
        if (live) {
          setNotebook(saved);
          setReady(true);
        }
      }
    };
    load().catch(() => {
      if (live)
        setError(
          "Unable to load this lab or notebook. Sign in if this is an instructor-published lab, or reload to retry.",
        );
    });
    return () => {
      live = false;
    };
  }, [slug, user]);
  const capture = useCallback(
    (trial: Trial) =>
      setNotebook((n) => ({ ...n, trials: [...n.trials, trial].slice(-50) })),
    [],
  );
  async function save() {
    setSaving(true);
    try {
      await labStudio.saveNotebook(slug, notebook);
      toast.success("Investigation saved");
    } catch {
      toast.error("Could not save. Your notes are still on this page.");
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="sf-page">
      <PageBackButton className="sf-back"/>
      <header className="sf-section-heading">
        <div>
          <span className="sf-eyebrow">Experiment workspace</span>
          <h1>{lab?.title || "Loading experiment…"}</h1>
          <p className="sf-muted">
            Predict, change one variable, capture the result, then explain what
            you observed.
          </p>
        </div>
        <div className="sf-actions">
          <span className="sf-chip">Learning through investigation</span>
          {lab?.native_template === "concept_lab" &&
            ["instructor", "admin", "superadmin"].includes(
              user?.role || "",
            ) && (
              <Link
                className="sf-secondary"
                to={`${user?.role === "instructor" ? "/instructor" : "/admin"}/lab-studio?template=${encodeURIComponent(slug)}`}
              >
                Customize this activity
              </Link>
            )}
        </div>
      </header>
      {error && (
        <p role="alert" className="sf-alert">
          {error}
        </p>
      )}
      {lab && (
        <section className="sf-surface lab-player-surface">
          {lab.native_template === "concept_lab" ? (
            <ConceptLabPlayer
              slug={slug} revision={lab.revision}
              config={lab.config as ConceptConfig}
              title={lab.title}
              onTrial={capture}
            />
          ) : slug.startsWith("cbse-") ? (
            <iframe
              className="lab-frame"
              style={{ height: 760 }}
              title={lab.title}
              src={lab.embed_url || ""}
              allow="fullscreen; xr-spatial-tracking"
              allowFullScreen
            />
          ) : (
            <VirtualLabPlayer slug={slug} height={680} />
          )}
        </section>
      )}
      <section className="sf-surface">
        <div className="sf-section-heading">
          <div>
            <span className="sf-eyebrow">Your private notebook</span>
            <h2>Turn an experiment into an explanation</h2>
          </div>
          <div className="sf-actions">
            <button
              className="sf-secondary"
              onClick={() =>
                downloadLabFile(
                  new Blob(
                    [JSON.stringify({ lab: slug, ...notebook }, null, 2)],
                    { type: "application/json" },
                  ),
                  `${slug}-investigation.json`,
                )
              }
            >
              <Download size={16} /> Export notes
            </button>
            <button
              className="sf-primary"
              disabled={!user || !ready || saving}
              onClick={save}
            >
              <Save size={16} /> {saving ? "Saving…" : "Save investigation"}
            </button>
          </div>
        </div>
        {!user && (
          <p className="sf-alert">
            <Link to="/login">Sign in</Link> to save your investigation. You can
            explore the supplied labs and export notes without an account.
          </p>
        )}
        <div className="sf-three-columns">
          {(["prediction", "observation", "conclusion"] as const).map(
            (key, i) => (
              <label className="sf-field" key={key}>
                <span>
                  0{i + 1} · {key}
                </span>
                <textarea
                  disabled={!!user && !ready}
                  value={notebook[key]}
                  maxLength={key === "observation" ? 6000 : 3000}
                  placeholder={
                    [
                      "What do you expect to happen, and why?",
                      "What changed? Record measurements and comparisons.",
                      "Does the evidence support your prediction? Explain the limits.",
                    ][i]
                  }
                  onChange={(e) =>
                    setNotebook((n) => ({ ...n, [key]: e.target.value }))
                  }
                />
              </label>
            ),
          )}
        </div>
        <details className="lab-trials">
          <summary>Captured trials ({notebook.trials.length}/50)</summary>
          {notebook.trials.length ? (
            <pre>{JSON.stringify(notebook.trials, null, 2)}</pre>
          ) : (
            <p className="sf-muted">
              Concept experiments have a Capture trial button. For the imported
              simulations, record measurements in Observations.
            </p>
          )}
        </details>
        <p className="sf-muted">
          Notebook entries are learning evidence, not automatic grades.
        </p>
      </section>
    </div>
  );
}
