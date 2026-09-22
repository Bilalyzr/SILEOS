import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React from "react";
import { Box, AlertTriangle } from "lucide-react";

// 3D Models list - actual files from /models/ar/
// `description` is a one-line explanation of the mathematics each model shows;
// it appears on the gallery card and in the viewer modal so a learner knows
// what they are looking at before they open it.
interface ARModel {
  name: string;
  file: string;
  description: string;
}

const models: ARModel[] = [
  {
    name: "Rough Work (Interactive VR Demo)",
    file: "Rough-Work-For-Website.glb",
    description:
      "A sandbox scene for getting used to the controls — orbit, zoom and pan before exploring the mathematical models.",
  },
  {
    name: "Pythagorean Theorem",
    file: "Pythagorean-Theorem-Animated-For-Website-Done.glb",
    description:
      "The squares built on the two shorter sides of a right triangle have exactly the same total area as the square on the hypotenuse: a² + b² = c².",
  },
  {
    name: "Rhombic Dodecahedron",
    file: "Rhombic-Dodecahedron-Animated-For-Website-Done.glb",
    description:
      "A solid with twelve identical rhombus faces. Copies of it fill space with no gaps, which is why it appears in crystal structures and honeycomb packing.",
  },
  {
    name: "Pascal Pyramid",
    file: "pascals_pyramid.glb",
    description:
      "The three-dimensional counterpart of Pascal's triangle. Each layer holds the coefficients you get when expanding a trinomial (a + b + c)ⁿ.",
  },
  {
    name: "Ordinary Helicoid",
    file: "ordinary_helicoid.glb",
    description:
      "The surface swept by a straight line turning steadily as it travels along an axis — a spiral ramp. It is a minimal surface, like the film a soap bubble forms.",
  },
  {
    name: "Hyperboloid",
    file: "hyperboloid.glb",
    description:
      "A curved quadric surface that can nevertheless be built entirely from straight lines. Cooling towers use this shape for exactly that reason.",
  },
  {
    name: "Hyperbolic Paraboloid",
    file: "hypar_approximately.glb",
    description:
      "The saddle shape z = x² − y², curving up in one direction and down in the other. Like the hyperboloid, it is ruled: made of straight lines.",
  },
  {
    name: "Extruded Sine Waves",
    file: "extruded_sine_waves_inside_a_cuboid.glb",
    description:
      "Sine curves swept through a solid block, showing how a simple periodic function becomes a rippling three-dimensional form.",
  },
  {
    name: "Catenoide",
    file: "catenoide.glb",
    description:
      "The surface formed by spinning a hanging-chain curve (a catenary) about an axis — the shape soap film takes between two rings.",
  },
  {
    name: "3D Lattice",
    file: "3d_lattice.glb",
    description:
      "A repeating three-dimensional grid of points and struts, the framework used to describe how atoms are arranged in a crystal.",
  },
  {
    name: "Stereomatria",
    file: "stereomatria.glb",
    description:
      "A solid-geometry study piece for examining how volumes, cross-sections and symmetry behave in three dimensions.",
  },
  {
    name: "Sierpinski Triangle",
    file: "Sierpinski-Animation-For-Website-Done.glb",
    description:
      "A fractal made by repeatedly removing the middle triangle from every remaining triangle. Every zoom level looks like the whole.",
  },
  {
    name: "Saddle Wires",
    file: "saddle_wires.glb",
    description:
      "A saddle surface drawn as bare wires, making it easy to see the straight lines hidden inside a doubly curved shape.",
  },
  {
    name: "Catenoid",
    file: "catenoid.glb",
    description:
      "A classical minimal surface — the smallest-area film that can span two parallel circular rings.",
  },
  {
    name: "Menger Sponge",
    file: "menger_sponge.glb",
    description:
      "A fractal built by boring square holes through a cube and repeating forever. Its surface area grows without limit while its volume shrinks to zero.",
  },
  {
    name: "Boys Surface",
    file: "boys_surface.glb",
    description:
      "A way of placing the real projective plane in three dimensions smoothly, with no creases or sharp points — only self-intersections.",
  },
  {
    name: "Borromean Rings",
    file: "borromean_rings.glb",
    description:
      "Three rings locked together as a set, yet no two of them are linked. Remove any one ring and the other two fall apart.",
  },
  {
    name: "3D Hilbert Curve",
    file: "3d_hilbert_curve_3rd_iteration.glb",
    description:
      "A continuous line that folds through a cube, eventually passing near every point in it. Shown here at its third iteration.",
  },
  {
    name: "Snub Cube",
    file: "snub_cube.glb",
    description:
      "An Archimedean solid with 38 faces — squares and triangles. It is chiral: its mirror image cannot be rotated to match it.",
  },
  {
    name: "Scherks Minimal Surface",
    file: "scherks_minimal_surface_scherk.glb",
    description:
      "A minimal surface that repeats in two directions, weaving between a grid of vertical columns.",
  },
  {
    name: "Penrose Triangle",
    file: "penrose_triangle-large.glb",
    description:
      "An impossible object: it reads as a solid triangle from one viewpoint only. Rotate it and the illusion breaks apart.",
  },
  {
    name: "Octahedron",
    file: "octahedron.glb",
    description:
      "One of the five Platonic solids — eight equilateral triangles, like two square pyramids joined base to base.",
  },
  {
    name: "Klein Bottle",
    file: "klein_bottle_2.glb",
    description:
      "A surface with no inside or outside and no edge at all. It cannot exist in three dimensions without passing through itself.",
  },
  {
    name: "Julia Quaternion",
    file: "julia_quaternion.glb",
    description:
      "A Julia set fractal computed in four-dimensional quaternion numbers, then sliced to produce this three-dimensional form.",
  },
  {
    name: "Gyroid",
    file: "gyroid.glb",
    description:
      "A minimal surface repeating in all three directions that divides space into two interlocking halves. It occurs naturally in butterfly wing scales.",
  },
  {
    name: "Enneper Surface",
    file: "enneper_surface.glb",
    description:
      "A minimal surface that curls back through itself — one of the earliest examples studied, and still a standard illustration of self-intersection.",
  },
  {
    name: "Dodecahedron",
    file: "dodecahedron.glb",
    description:
      "A Platonic solid with twelve regular pentagonal faces, twenty vertices and thirty edges.",
  },
  {
    name: "Mobius Strip",
    file: "mobius-strip-model.glb",
    description:
      "A loop with a half twist, giving it a single surface and a single edge. Trace it with a finger and you return having covered 'both' sides.",
  },
  {
    name: "Alexander Horned Sphere",
    file: "Alexander-Horned-Sphere.glb",
    description:
      "A sphere deformed into endlessly interlocking horns. It shows that a shape can be a sphere in principle while tangling the space around it.",
  },
  {
    name: "Cross Cap",
    file: "Cross-Production-Animated-For-Website-Done.glb",
    description:
      "Another rendering of the projective plane in three dimensions, this time with a line where the surface crosses itself.",
  },
  {
    name: "Oloid",
    file: "Oloid.glb",
    description:
      "Formed from two perpendicular circles through each other's centres. As it rolls, every point of its surface touches the ground.",
  },
  {
    name: "Sphericon",
    file: "Sphericon.glb",
    description:
      "A solid made by slicing a double cone and rotating one half. It rolls forward in a steady meandering wobble.",
  },
  {
    name: "Costas Minimal Surface",
    file: "Costas-Minimal-Surface-Animation-For-Website-Done.glb",
    description:
      "A minimal surface that extends forever without ever crossing itself — its 1982 discovery overturned what mathematicians believed was possible.",
  },
  {
    name: "Dinis Surface",
    file: "Dinis-Surface-Animated-For-Website-Done.glb",
    description:
      "A twisted spiral of constant negative curvature, sometimes called the twisted pseudosphere. Every point on it is saddle-shaped.",
  },
  {
    name: "Divergence",
    file: "Divergence-Animated-Animated-For-Website-Done.glb",
    description:
      "A vector-calculus visual showing whether a field flows outward from a point or into it — the mathematics behind sources and sinks.",
  },
  {
    name: "Dot Product",
    file: "Dot-Product-Animated-For-Website-Done.glb",
    description:
      "How far one vector reaches along another. The result peaks when they align and vanishes when they meet at a right angle.",
  },
  {
    name: "Barth Sextic",
    file: "barth-sextic-Animation-For-Website-Done.glb",
    description:
      "A degree-six algebraic surface carrying 65 singular points — the largest number possible at that degree.",
  },
  {
    name: "Riemann Surfaces",
    file: "Riemann-Surfaces-AAnimation-For-Website-Done.glb",
    description:
      "Layered sheets that give functions like the square root a single consistent value, by letting the input travel between levels.",
  },
];

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace -- JSX augmentation for the <model-viewer> web component
  namespace JSX {
    interface IntrinsicElements {
      "model-viewer": any;
    }
  }
}

// Script load status for the <model-viewer> web component. It is loaded lazily
// (on first gallery view) so the page itself never depends on the script
// being reachable — on devices where it somehow fails the grid still renders
// with static icon tiles, and only the live previews/modal degrade.
type ViewerStatus = "idle" | "loading" | "ready" | "error";

// Self-hosted copy of the <model-viewer> web component (Apache-2.0/BSD,
// downloaded from the official distribution). Serving it from our own origin
// instead of ajax.googleapis.com fixed the mobile gallery in India: several
// Indian mobile carriers block or throttle Google's CDN, which left every
// model open in the "couldn't load the 3D viewer" state on phones while the
// desktop (different network path) kept working.
const MODEL_VIEWER_SRC = "/vendor/model-viewer.min.js";

// Live 3D tile. Mounts a small real <model-viewer> only when the card scrolls
// into view, so a 39-model grid never spins up more WebGL contexts than the
// viewport shows (~4-8). Until then (or if the script failed to load) the
// lightweight gradient tile with the icon shows — identical to the old
// static card, so the grid remains renderable everywhere.
function LazyModelPreview({
  file,
  name,
  ready,
}: {
  file: string;
  name: string;
  ready: boolean;
}) {
  const ref = React.useRef<HTMLDivElement | null>(null);
  const [visible, setVisible] = React.useState(false);

  React.useEffect(() => {
    const el = ref.current;
    if (!el || !("IntersectionObserver" in window)) {
      setVisible(true); // no IO support (ancient browsers): show immediately
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setVisible(true);
          io.disconnect();
        }
      },
      { rootMargin: "200px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className="h-56 relative bg-gradient-to-br from-gray-800 to-gray-900"
    >
      {visible && ready ? (
        <model-viewer
          src={`/models/ar/${file}`}
          alt={`3D preview of ${name}`}
          auto-rotate
          rotation-per-second="18deg"
          interaction-prompt="none"
          camera-controls={false as any}
          disable-pan
          environment-image="neutral"
          shadow-intensity="1"
          exposure="1.1"
          style={{
            width: "100%",
            height: "100%",
            background: "radial-gradient(circle at 50% 40%, #1e293b, #0b1220)",
          }}
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center">
          <Box className="w-16 h-16 text-gray-600" />
        </div>
      )}
    </div>
  );
}

export function MeiporulARPage() {
  const [search, setSearch] = React.useState("");
  const [selected, setSelected] = React.useState<(typeof models)[0] | null>(
    null,
  );
  const [viewerStatus, setViewerStatus] = React.useState<ViewerStatus>("idle");

  // Lazily inject the model-viewer script the first time a model is opened.
  // Crucially this handles BOTH onload and onerror, so a blocked/slow CDN can
  // never leave the UI hanging — it resolves to 'ready' or 'error'.
  const ensureViewerLoaded = React.useCallback(() => {
    // Already defined (e.g. loaded by another page) → ready immediately.
    if (
      typeof window !== "undefined" &&
      (window as any).customElements?.get("model-viewer")
    ) {
      setViewerStatus("ready");
      return;
    }
    const existing = document.querySelector<HTMLScriptElement>(
      "script[data-model-viewer]",
    );
    if (existing) {
      // A previous attempt is in-flight or finished — mirror its outcome.
      setViewerStatus((s) => (s === "ready" || s === "error" ? s : "loading"));
      return;
    }
    setViewerStatus("loading");
    const script = document.createElement("script");
    script.type = "module";
    script.src = MODEL_VIEWER_SRC;
    script.setAttribute("data-model-viewer", "true");
    script.onload = () => setViewerStatus("ready");
    script.onerror = () => setViewerStatus("error");
    document.head.appendChild(script);
  }, []);

  const openModel = (model: (typeof models)[0]) => {
    setSelected(model);
    ensureViewerLoaded();
  };

  // Previews need the component too — kick the lazy load on mount so tiles
  // can go live as soon as the script registers the custom element.
  React.useEffect(() => {
    ensureViewerLoaded();
  }, [ensureViewerLoaded]);

  // Search the description as well as the title, so "minimal surface" or
  // "fractal" finds the relevant models even when the word isn't in the name.
  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return models;
    return models.filter(
      (m) =>
        m.name.toLowerCase().includes(q) ||
        m.description.toLowerCase().includes(q),
    );
  }, [search]);

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="text-4xl font-bold mb-2">Meiporul AR Gallery</h1>
          <p className="text-orange-100 text-lg">
            {models.length} Interactive 3D Models — AR Ready
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-meiporul-ar"
    >
      <div className="container mx-auto px-4 py-6 flex justify-center">
        <input
          type="text"
          placeholder="Search models..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-md px-4 py-3 rounded-xl bg-gray-800 border border-gray-700 text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
        />
      </div>
      <div className="container mx-auto px-4 pb-12">
        {filtered.length === 0 ? (
          <p className="text-center text-gray-400 py-12">
            No models match "{search}".
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {filtered.map((model, i) => (
              <button
                key={i}
                type="button"
                onClick={() => openModel(model)}
                className="text-left bg-gray-900 rounded-2xl overflow-hidden border border-gray-800 hover:border-orange-500 transition-all cursor-pointer group focus:outline-none focus:border-orange-500"
              >
                <div className="relative">
                  <LazyModelPreview
                    file={model.file}
                    name={model.name}
                    ready={viewerStatus === "ready"}
                  />
                  <div className="absolute top-2 right-2 flex gap-1">
                    <span className="bg-orange-500 text-white text-xs px-2 py-1 rounded-full font-bold">
                      AR
                    </span>
                    <span className="bg-green-500 text-white text-xs px-2 py-1 rounded-full">
                      3D
                    </span>
                  </div>
                </div>
                <div className="p-4">
                  <h3 className="font-semibold text-white group-hover:text-orange-400 transition-colors">
                    {model.name}
                  </h3>
                  <p className="text-sm text-gray-400 mt-1.5 line-clamp-3">
                    {model.description}
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    Tap to view in 3D / AR
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
      {selected && (
        <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-4xl bg-gray-900 rounded-2xl overflow-hidden">
            <div className="flex items-start justify-between gap-4 p-4 border-b border-gray-700">
              <div className="min-w-0">
                <h2 className="text-xl font-bold">{selected.name}</h2>
                <p className="text-sm text-gray-400 mt-1">
                  {selected.description}
                </p>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="text-gray-400 hover:text-white text-2xl leading-none flex-shrink-0"
                aria-label="Close model viewer"
              >
                ✕
              </button>
            </div>

            {viewerStatus === "ready" ? (
              <model-viewer
                src={`/models/ar/${selected.file}`}
                auto-rotate
                camera-controls
                ar
                ar-modes="webxr scene-viewer quick-look"
                style={{
                  width: "100%",
                  height: "500px",
                  background: "#111827",
                }}
              />
            ) : viewerStatus === "error" ? (
              <div
                className="flex flex-col items-center justify-center text-center gap-3 px-6"
                style={{ height: 500 }}
              >
                <AlertTriangle className="w-10 h-10 text-orange-400" />
                <p className="font-semibold">The 3D viewer couldn't load</p>
                <p className="text-sm text-gray-400 max-w-md">
                  This usually means the network blocked the 3D component. You
                  can still download the model file and open it in any 3D/AR
                  viewer.
                </p>
                <a
                  href={`/models/ar/${selected.file}`}
                  className="mt-2 px-4 py-2 rounded-xl bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold"
                  download
                >
                  Download model (.glb)
                </a>
              </div>
            ) : (
              <div
                className="flex flex-col items-center justify-center gap-4"
                style={{ height: 500 }}
              >
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-500" />
                <p className="text-gray-400">Loading 3D viewer…</p>
              </div>
            )}
          </div>
        </div>
      )}
    </PageLayout>
  );
}
