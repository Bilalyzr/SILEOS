import * as React from "react";
import { Layers2, Moon, Sun } from "lucide-react";

export type AurumTheme = "dark" | "light";
export type AurumSurface = "plate" | "smoked";

const THEME_KEY = "aurum_theme";
const SURFACE_KEY = "aurum_surface";

function savedTheme(): AurumTheme {
  return localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark";
}

function supportsSmokedSurface(): boolean {
  const memory = (navigator as Navigator & { deviceMemory?: number })
    .deviceMemory;
  return (
    (memory == null || memory >= 4) &&
    !window.matchMedia("(prefers-reduced-transparency: reduce)").matches
  );
}

function savedSurface(): AurumSurface {
  return localStorage.getItem(SURFACE_KEY) === "smoked" &&
    supportsSmokedSurface()
    ? "smoked"
    : "plate";
}

function applyPreferences(theme: AurumTheme, surface: AurumSurface) {
  for (const element of [document.documentElement, document.body]) {
    element.dataset.theme = theme;
    element.dataset.surface = surface;
    // Bridge every theme system so ONE toggle drives them all. Before this,
    // the toggle only flipped aurum.css's [data-theme] styles while
    // globals.css's shadcn tokens waited for a `.dark` class nothing ever
    // set and sasha-design.css's sf-* components keyed off a separate
    // data-sasha-theme — leaving light content mixed into dark chrome.
    element.classList.toggle("dark", theme === "dark");
    element.dataset.sashaTheme = theme;
  }
}

export function AurumDisplayControls() {
  const [theme, setTheme] = React.useState<AurumTheme>(savedTheme);
  const [surface, setSurface] = React.useState<AurumSurface>(savedSurface);
  const smokedAvailable = React.useMemo(supportsSmokedSurface, []);

  React.useLayoutEffect(() => {
    const safeSurface = smokedAvailable ? surface : "plate";
    applyPreferences(theme, safeSurface);
    localStorage.setItem(THEME_KEY, theme);
    localStorage.setItem(SURFACE_KEY, safeSurface);
    if (safeSurface !== surface) setSurface(safeSurface);
  }, [smokedAvailable, surface, theme]);

  return (
    <div className="aurum-display-controls" aria-label="Display preferences">
      <button
        type="button"
        className="aurum-icon-control"
        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        aria-label={`Use ${theme === "dark" ? "light" : "dark"} theme`}
        title={`Use ${theme === "dark" ? "light" : "dark"} theme`}
      >
        {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
      </button>
      <button
        type="button"
        className="aurum-surface-control"
        onClick={() => setSurface(surface === "plate" ? "smoked" : "plate")}
        aria-pressed={surface === "smoked"}
        aria-label={
          smokedAvailable
            ? `Use ${surface === "plate" ? "smoked glass" : "milled plate"} surfaces`
            : "Milled plate surfaces are enabled for this device"
        }
        title={smokedAvailable ? "Toggle surface treatment" : "Reduced transparency mode"}
        disabled={!smokedAvailable}
      >
        <Layers2 size={15} />
        <span>{surface === "plate" ? "Milled plate" : "Smoked glass"}</span>
      </button>
    </div>
  );
}

export function initialiseAurumPreferences() {
  applyPreferences(savedTheme(), savedSurface());
}
