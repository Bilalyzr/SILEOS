import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

/**
 * /accessibility — the page the footer "Accessibility" link points to.
 * Reuses the exact same preference keys as the header AccessibilityMenu
 * (si.highContrast / si.largeText / si.reduceMotion / si.learningLanguage)
 * so a change here applies site-wide instantly, and vice versa.
 */
export function AccessibilityPage() {
  const [contrast, setContrast] = useState(() => localStorage.getItem("si.highContrast") === "1");
  const [large, setLarge] = useState(() => localStorage.getItem("si.largeText") === "1");
  const [motion, setMotion] = useState(() => localStorage.getItem("si.reduceMotion") === "1");
  const [language, setLanguage] = useState(() => (localStorage.getItem("si.learningLanguage") === "ta" ? "ta" : "en"));

  useEffect(() => {
    document.body.dataset.highContrast = String(contrast);
    localStorage.setItem("si.highContrast", contrast ? "1" : "0");
  }, [contrast]);
  useEffect(() => {
    document.body.dataset.largeText = String(large);
    localStorage.setItem("si.largeText", large ? "1" : "0");
  }, [large]);
  useEffect(() => {
    document.body.dataset.reduceMotion = String(motion);
    localStorage.setItem("si.reduceMotion", motion ? "1" : "0");
  }, [motion]);

  const card = "rounded-xl border border-slate-200 bg-white p-5";
  const check = "flex items-center gap-3 text-sm text-slate-700";

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <p className="text-xs font-semibold uppercase tracking-widest text-orange-600">Accessibility</p>
      <h1 className="mt-2 text-3xl font-bold text-slate-900">Everyone can learn here.</h1>
      <p className="mt-3 text-sm leading-relaxed text-slate-600">
        SashaInfinity is built to be usable by everyone. Adjust your reading
        experience below — your choices apply across the whole site immediately
        and are remembered on this device. The same settings are available any
        time from the accessibility icon in the header.
      </p>

      <section className={`mt-8 ${card}`}>
        <h2 className="text-lg font-semibold text-slate-900">Display preferences</h2>
        <div className="mt-4 space-y-4">
          <label className={check}>
            <input
              type="checkbox"
              checked={contrast}
              onChange={(e) => setContrast(e.target.checked)}
              className="h-4 w-4 accent-orange-600"
            />
            High contrast
          </label>
          <label className={check}>
            <input
              type="checkbox"
              checked={large}
              onChange={(e) => setLarge(e.target.checked)}
              className="h-4 w-4 accent-orange-600"
            />
            Larger text
          </label>
          <label className={check}>
            <input
              type="checkbox"
              checked={motion}
              onChange={(e) => setMotion(e.target.checked)}
              className="h-4 w-4 accent-orange-600"
            />
            Reduce motion
          </label>
          <label className="block text-sm text-slate-700">
            Lab &amp; offline language / மொழி
            <select
              value={language}
              onChange={(e) => {
                setLanguage(e.target.value);
                localStorage.setItem("si.learningLanguage", e.target.value);
                window.dispatchEvent(new Event("learning-preferences"));
              }}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
            >
              <option value="en">English</option>
              <option value="ta">தமிழ்</option>
            </select>
          </label>
        </div>
      </section>

      <section className={`mt-6 ${card}`}>
        <h2 className="text-lg font-semibold text-slate-900">What we do</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-relaxed text-slate-600">
          <li>Keyboard navigation works everywhere; visible focus outlines are always kept.</li>
          <li>Screens and text meet WCAG contrast targets.</li>
          <li>Videos, labs and live classes can be used without a mouse.</li>
          <li>Your display preferences are respected on every page, in every workspace.</li>
        </ul>
        <p className="mt-4 text-sm text-slate-600">
          Need something else? <Link to="/contact" className="font-semibold text-orange-600 underline">Tell us</Link> and
          we will make it work.
        </p>
      </section>
    </div>
  );
}

export default AccessibilityPage;
