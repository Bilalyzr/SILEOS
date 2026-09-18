import { useEffect, useRef, useState } from "react";
import { Accessibility } from "lucide-react";
import "./accessibility-menu.css";

/**
 * Header-integrated accessibility control (replaces the floating
 * LearningPreferences aside that overlapped page content). Same real
 * settings — language, high contrast, larger text, reduced motion — now
 * opened from a proper header icon button and rendered in a positioned
 * popover that never covers navigation.
 */
export function AccessibilityMenu() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const [contrast, setContrast] = useState(
    () => localStorage.getItem("si.highContrast") === "1",
  );
  const [large, setLarge] = useState(
    () => localStorage.getItem("si.largeText") === "1",
  );
  const [motion, setMotion] = useState(
    () => localStorage.getItem("si.reduceMotion") === "1",
  );
  const [language, setLanguage] = useState(
    () => (localStorage.getItem("si.learningLanguage") === "ta" ? "ta" : "en"),
  );

  useEffect(() => {
    document.body.dataset.highContrast = String(contrast);
    document.body.dataset.largeText = String(large);
    document.body.dataset.reduceMotion = String(motion);
    localStorage.setItem("si.highContrast", contrast ? "1" : "0");
    localStorage.setItem("si.largeText", large ? "1" : "0");
    localStorage.setItem("si.reduceMotion", motion ? "1" : "0");
  }, [contrast, large, motion]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  return (
    <div className="a11y-menu" ref={rootRef}>
      <button
        type="button"
        className="a11y-menu-trigger"
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label="Accessibility options / அணுகல்தன்மை"
        title="Accessibility options / அணுகல்தன்மை"
        onClick={() => setOpen((v) => !v)}
      >
        <Accessibility size={18} aria-hidden />
      </button>
      {open && (
        <div
          className="a11y-menu-panel"
          role="dialog"
          aria-label="Accessibility options"
        >
          <div className="a11y-menu-head">
            <strong>Accessibility</strong>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close accessibility options"
            >
              Close
            </button>
          </div>
          <label className="a11y-field">
            Language / மொழி
            <select
              value={language}
              onChange={(e) => {
                setLanguage(e.target.value as "en" | "ta");
                localStorage.setItem("si.learningLanguage", e.target.value);
                window.dispatchEvent(new Event("learning-preferences"));
              }}
            >
              <option value="en">English</option>
              <option value="ta">தமிழ்</option>
            </select>
          </label>
          <label className="a11y-check">
            <input
              type="checkbox"
              checked={contrast}
              onChange={(e) => setContrast(e.target.checked)}
            />
            High contrast
          </label>
          <label className="a11y-check">
            <input
              type="checkbox"
              checked={large}
              onChange={(e) => setLarge(e.target.checked)}
            />
            Larger text
          </label>
          <label className="a11y-check">
            <input
              type="checkbox"
              checked={motion}
              onChange={(e) => setMotion(e.target.checked)}
            />
            Reduce motion
          </label>
          <a className="a11y-link" href="/offline.html">
            Offline downloads
          </a>
        </div>
      )}
    </div>
  );
}
