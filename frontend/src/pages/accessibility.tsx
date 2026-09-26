import { useEffect, useState } from "react";
import PageHeader from "@/components/public/PageHeader";

const breadcrumbs = [
  { name: "Home", path: "/" },
  { name: "Accessibility", path: "/accessibility" },
];

/**
 * Accessibility statement + the same preference switches the floating corner
 * widget controls. Both write the identical `si.*` localStorage keys and body
 * data attributes, so a change here is reflected everywhere immediately.
 */
export function AccessibilityPage() {
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
    localStorage.setItem("si.learningLanguage", language);
    window.dispatchEvent(new Event("learning-preferences"));
  }, [contrast, large, motion, language]);

  return (
    <>
      <PageHeader title="Accessibility" breadcrumbs={breadcrumbs} />
      <div className="container-custom py-16">
        <div className="max-w-4xl mx-auto prose prose-lg">
          <div
            className="bg-white rounded-lg shadow-md p-8"
            data-glass="content"
          >
            <h2 className="text-3xl font-bold mb-6 text-neutral-900">
              Accessibility at SashaInfinity
            </h2>
            <p className="text-neutral-600 mb-6">
              Last updated:{" "}
              {new Date().toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </p>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                Our commitment
              </h3>
              <p className="mb-4 text-neutral-700">
                SashaInfinity is built to be usable by everyone, including
                learners who rely on assistive technology. We target the WCAG
                2.1 AA guidelines: keyboard-operable navigation, readable
                contrast, respect for reduced-motion preferences, and text
                alternatives for meaningful images.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                Your display preferences
              </h3>
              <p className="mb-4 text-neutral-700">
                These choices apply across SashaInfinity immediately and are
                remembered on this device. The same switches are available from
                the accessibility button in the bottom-right corner of any
                page.
              </p>

              <div className="not-prose space-y-4">
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={contrast}
                    onChange={(e) => setContrast(e.target.checked)}
                    className="h-5 w-5"
                  />
                  <span className="font-semibold text-neutral-800">
                    High contrast
                  </span>
                </label>
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={large}
                    onChange={(e) => setLarge(e.target.checked)}
                    className="h-5 w-5"
                  />
                  <span className="font-semibold text-neutral-800">
                    Larger text
                  </span>
                </label>
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={motion}
                    onChange={(e) => setMotion(e.target.checked)}
                    className="h-5 w-5"
                  />
                  <span className="font-semibold text-neutral-800">
                    Reduce motion
                  </span>
                </label>
                <label className="flex items-center gap-3">
                  <span className="font-semibold text-neutral-800">
                    Lab &amp; offline language
                  </span>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="border border-neutral-300 rounded-md px-3 py-2"
                  >
                    <option value="en">English</option>
                    <option value="ta">தமிழ்</option>
                  </select>
                </label>
              </div>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                Keyboard navigation
              </h3>
              <p className="mb-4 text-neutral-700">
                Every interactive control can be reached with Tab and operated
                with Enter, Space, or the arrow keys. Menus and dialogs close
                with Escape. Focus indicators are always visible.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                Report a barrier
              </h3>
              <p className="mb-4 text-neutral-700">
                If any part of SashaInfinity is hard or impossible for you to
                use, tell us and we will fix it. Write to{" "}
                <a
                  href="mailto:support@sashainfinity.com"
                  className="text-orange-700 underline"
                >
                  support@sashainfinity.com
                </a>{" "}
                with the page you were on and what happened; we aim to respond
                within two working days.
              </p>
            </section>
          </div>
        </div>
      </div>
    </>
  );
}

export default AccessibilityPage;
