import { useEffect, useRef, useState } from "react";
import { Accessibility } from "lucide-react";
export type LearningLanguage = "en" | "ta";
export function useLearningLanguage() {
  const [language, setLanguage] = useState<LearningLanguage>(() =>
    localStorage.getItem("si.learningLanguage") === "ta" ? "ta" : "en",
  );
  useEffect(() => {
    const update = () =>
      setLanguage(
        localStorage.getItem("si.learningLanguage") === "ta" ? "ta" : "en",
      );
    window.addEventListener("learning-preferences", update);
    return () => window.removeEventListener("learning-preferences", update);
  }, []);
  return language;
}
export function LearningPreferences() {
  const language = useLearningLanguage();
  const [open, setOpen] = useState(false);
  const [contrast, setContrast] = useState(
    () => localStorage.getItem("si.highContrast") === "1",
  );
  const [large, setLarge] = useState(
    () => localStorage.getItem("si.largeText") === "1",
  );
  const [motion, setMotion] = useState(
    () => localStorage.getItem("si.reduceMotion") === "1",
  );
  const rootRef = useRef<HTMLElement | null>(null);

  // The panel floats over page content; an OPEN panel must never permanently
  // cover controls under it (it sat on the lesson page's "Mark as complete").
  // Clicking/tapping outside closes it.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open]);

  useEffect(() => {
    document.body.dataset.highContrast = String(contrast);
    document.body.dataset.largeText = String(large);
    document.body.dataset.reduceMotion = String(motion);
    localStorage.setItem("si.highContrast", contrast ? "1" : "0");
    localStorage.setItem("si.largeText", large ? "1" : "0");
    localStorage.setItem("si.reduceMotion", motion ? "1" : "0");
  }, [contrast, large, motion]);
  return (
    <aside className="learning-preferences" aria-label="Learning preferences" ref={rootRef}>
      {/* Compact icon toggle: the old wide text button (~200px) covered most
          of the lesson rail's Mark-as-complete control underneath it. */}
      <button
        type="button"
        className="sf-secondary learning-preferences-toggle"
        aria-expanded={open}
        aria-label="Accessibility / அணுகல்தன்மை"
        title="Accessibility / அணுகல்தன்மை"
        onClick={() => setOpen(!open)}
      >
        <Accessibility aria-hidden="true" />
      </button>
      {open && (
        <div className="sf-surface space-y-3">
          <h2>Accessibility / அணுகல்தன்மை</h2>
          <label className="sf-field">
            Lab & offline language
            <select
              value={language}
              onChange={(e) => {
                localStorage.setItem("si.learningLanguage", e.target.value);
                window.dispatchEvent(new Event("learning-preferences"));
              }}
            >
              <option value="en">English</option>
              <option value="ta">தமிழ்</option>
            </select>
          </label>
          <label className="flex gap-2">
            <input
              type="checkbox"
              checked={contrast}
              onChange={(e) => setContrast(e.target.checked)}
            />{" "}
            High contrast
          </label>
          <label className="flex gap-2">
            <input
              type="checkbox"
              checked={large}
              onChange={(e) => setLarge(e.target.checked)}
            />{" "}
            Larger text
          </label>
          <label className="flex gap-2">
            <input
              type="checkbox"
              checked={motion}
              onChange={(e) => setMotion(e.target.checked)}
            />{" "}
            Reduce motion
          </label>
          <p className="sf-muted">
            Authored Tamil explanations appear when available; source course
            content keeps its original language.
          </p>
          <a className="sf-secondary" href="/offline.html">
            Offline downloads
          </a>
          <button className="sf-secondary" onClick={() => setOpen(false)}>
            Close
          </button>
        </div>
      )}
    </aside>
  );
}
