import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React from "react";
import {
  Box,
  AlertTriangle,
  Search,
  ChevronLeft,
  ChevronRight,
  X,
} from "lucide-react";
import { SplitHeading, SymphoCtaBanner } from "@/components/sympho/SymphoSystem";

interface ARModel {
  name: string;
  file: string;
  description: string;
  category: "Surfaces" | "Solids" | "Fractals & Curves" | "Theorems & Vectors";
}

const models: ARModel[] = [
  {
    name: "Rough Work (Interactive VR Demo)",
    file: "Rough-Work-For-Website.glb",
    category: "Theorems & Vectors",
    description:
      "A sandbox scene for getting used to the controls — orbit, zoom and pan before exploring the mathematical models.",
  },
  {
    name: "Pythagorean Theorem",
    file: "Pythagorean-Theorem-Animated-For-Website-Done.glb",
    category: "Theorems & Vectors",
    description:
      "The squares built on the two shorter sides of a right triangle have exactly the same total area as the square on the hypotenuse: a² + b² = c².",
  },
  {
    name: "Rhombic Dodecahedron",
    file: "Rhombic-Dodecahedron-Animated-For-Website-Done.glb",
    category: "Solids",
    description:
      "A solid with twelve identical rhombus faces. Copies of it fill space with no gaps, which is why it appears in crystal structures and honeycomb packing.",
  },
  {
    name: "Pascal Pyramid",
    file: "pascals_pyramid.glb",
    category: "Solids",
    description:
      "The three-dimensional counterpart of Pascal's triangle. Each layer holds the coefficients you get when expanding a trinomial (a + b + c)ⁿ.",
  },
  {
    name: "Ordinary Helicoid",
    file: "ordinary_helicoid.glb",
    category: "Surfaces",
    description:
      "The surface swept by a straight line turning steadily as it travels along an axis — a spiral ramp. It is a minimal surface, like the film a soap bubble forms.",
  },
  {
    name: "Hyperboloid",
    file: "hyperboloid.glb",
    category: "Surfaces",
    description:
      "A curved quadric surface that can nevertheless be built entirely from straight lines. Cooling towers use this shape for exactly that reason.",
  },
  {
    name: "Hyperbolic Paraboloid",
    file: "hypar_approximately.glb",
    category: "Surfaces",
    description:
      "The saddle shape z = x² − y², curving up in one direction and down in the other. Like the hyperboloid, it is ruled: made of straight lines.",
  },
  {
    name: "Extruded Sine Waves",
    file: "extruded_sine_waves_inside_a_cuboid.glb",
    category: "Surfaces",
    description:
      "Sine curves swept through a solid block, showing how a simple periodic function becomes a rippling three-dimensional form.",
  },
  {
    name: "Catenoide",
    file: "catenoide.glb",
    category: "Surfaces",
    description:
      "The surface formed by spinning a hanging-chain curve (a catenary) about an axis — the shape soap film takes between two rings.",
  },
  {
    name: "3D Lattice",
    file: "3d_lattice.glb",
    category: "Solids",
    description:
      "A repeating three-dimensional grid of points and struts, the framework used to describe how atoms are arranged in a crystal.",
  },
  {
    name: "Stereomatria",
    file: "stereomatria.glb",
    category: "Solids",
    description:
      "A solid-geometry study piece for examining how volumes, cross-sections and symmetry behave in three dimensions.",
  },
  {
    name: "Sierpinski Triangle",
    file: "Sierpinski-Animation-For-Website-Done.glb",
    category: "Fractals & Curves",
    description:
      "A fractal made by repeatedly removing the middle triangle from every remaining triangle. Every zoom level looks like the whole.",
  },
  {
    name: "Saddle Wires",
    file: "saddle_wires.glb",
    category: "Surfaces",
    description:
      "A saddle surface drawn as bare wires, making it easy to see the straight lines hidden inside a doubly curved shape.",
  },
  {
    name: "Catenoid",
    file: "catenoid.glb",
    category: "Surfaces",
    description:
      "A classical minimal surface — the smallest-area film that can span two parallel circular rings.",
  },
  {
    name: "Menger Sponge",
    file: "menger_sponge.glb",
    category: "Fractals & Curves",
    description:
      "A fractal built by boring square holes through a cube and repeating forever. Its surface area grows without limit while its volume shrinks to zero.",
  },
  {
    name: "Boys Surface",
    file: "boys_surface.glb",
    category: "Surfaces",
    description:
      "A way of placing the real projective plane in three dimensions smoothly, with no creases or sharp points — only self-intersections.",
  },
  {
    name: "Borromean Rings",
    file: "borromean_rings.glb",
    category: "Fractals & Curves",
    description:
      "Three rings locked together as a set, yet no two of them are linked. Remove any one ring and the other two fall apart.",
  },
  {
    name: "3D Hilbert Curve",
    file: "3d_hilbert_curve_3rd_iteration.glb",
    category: "Fractals & Curves",
    description:
      "A continuous line that folds through a cube, eventually passing near every point in it. Shown here at its third iteration.",
  },
  {
    name: "Snub Cube",
    file: "snub_cube.glb",
    category: "Solids",
    description:
      "An Archimedean solid with 38 faces — squares and triangles. It is chiral: its mirror image cannot be rotated to match it.",
  },
  {
    name: "Scherks Minimal Surface",
    file: "scherks_minimal_surface_scherk.glb",
    category: "Surfaces",
    description:
      "A minimal surface that repeats in two directions, weaving between a grid of vertical columns.",
  },
  {
    name: "Penrose Triangle",
    file: "penrose_triangle-large.glb",
    category: "Solids",
    description:
      "An impossible object: it reads as a solid triangle from one viewpoint only. Rotate it and the illusion breaks apart.",
  },
  {
    name: "Octahedron",
    file: "octahedron.glb",
    category: "Solids",
    description:
      "One of the five Platonic solids — eight equilateral triangles, like two square pyramids joined base to base.",
  },
  {
    name: "Klein Bottle",
    file: "klein_bottle_2.glb",
    category: "Surfaces",
    description:
      "A surface with no inside or outside and no edge at all. It cannot exist in three dimensions without passing through itself.",
  },
  {
    name: "Julia Quaternion",
    file: "julia_quaternion.glb",
    category: "Fractals & Curves",
    description:
      "A Julia set fractal computed in four-dimensional quaternion numbers, then sliced to produce this three-dimensional form.",
  },
  {
    name: "Gyroid",
    file: "gyroid.glb",
    category: "Surfaces",
    description:
      "A minimal surface repeating in all three directions that divides space into two interlocking halves. It occurs naturally in butterfly wing scales.",
  },
  {
    name: "Enneper Surface",
    file: "enneper_surface.glb",
    category: "Surfaces",
    description:
      "A minimal surface that curls back through itself — one of the earliest examples studied, and still a standard illustration of self-intersection.",
  },
  {
    name: "Dodecahedron",
    file: "dodecahedron.glb",
    category: "Solids",
    description:
      "A Platonic solid with twelve regular pentagonal faces, twenty vertices and thirty edges.",
  },
  {
    name: "Mobius Strip",
    file: "mobius-strip-model.glb",
    category: "Surfaces",
    description:
      "A loop with a half twist, giving it a single surface and a single edge. Trace it with a finger and you return having covered 'both' sides.",
  },
  {
    name: "Alexander Horned Sphere",
    file: "Alexander-Horned-Sphere.glb",
    category: "Fractals & Curves",
    description:
      "A sphere deformed into endlessly interlocking horns. It shows that a shape can be a sphere in principle while tangling the space around it.",
  },
  {
    name: "Cross Cap",
    file: "Cross-Production-Animated-For-Website-Done.glb",
    category: "Surfaces",
    description:
      "Another rendering of the projective plane in three dimensions, this time with a line where the surface crosses itself.",
  },
  {
    name: "Oloid",
    file: "Oloid.glb",
    category: "Solids",
    description:
      "Formed from two perpendicular circles through each other's centres. As it rolls, every point of its surface touches the ground.",
  },
  {
    name: "Sphericon",
    file: "Sphericon.glb",
    category: "Solids",
    description:
      "A solid made by slicing a double cone and rotating one half. It rolls forward in a steady meandering wobble.",
  },
  {
    name: "Costas Minimal Surface",
    file: "Costas-Minimal-Surface-Animation-For-Website-Done.glb",
    category: "Surfaces",
    description:
      "A minimal surface that extends forever without ever crossing itself — its 1982 discovery overturned what mathematicians believed was possible.",
  },
  {
    name: "Dinis Surface",
    file: "Dinis-Surface-Animated-For-Website-Done.glb",
    category: "Surfaces",
    description:
      "A twisted spiral of constant negative curvature, sometimes called the twisted pseudosphere. Every point on it is saddle-shaped.",
  },
  {
    name: "Divergence",
    file: "Divergence-Animated-Animated-For-Website-Done.glb",
    category: "Theorems & Vectors",
    description:
      "A vector-calculus visual showing whether a field flows outward from a point or into it — the mathematics behind sources and sinks.",
  },
  {
    name: "Dot Product",
    file: "Dot-Product-Animated-For-Website-Done.glb",
    category: "Theorems & Vectors",
    description:
      "How far one vector reaches along another. The result peaks when they align and vanishes when they meet at a right angle.",
  },
  {
    name: "Barth Sextic",
    file: "barth-sextic-Animation-For-Website-Done.glb",
    category: "Surfaces",
    description:
      "A degree-six algebraic surface carrying 65 singular points — the largest number possible at that degree.",
  },
  {
    name: "Riemann Surfaces",
    file: "Riemann-Surfaces-AAnimation-For-Website-Done.glb",
    category: "Surfaces",
    description:
      "Layered sheets that give functions like the square root a single consistent value, by letting the input travel between levels.",
  },
];

const CATEGORIES = [
  "All",
  "Surfaces",
  "Solids",
  "Fractals & Curves",
  "Theorems & Vectors",
] as const;

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace -- JSX augmentation for the <model-viewer> web component
  namespace JSX {
    interface IntrinsicElements {
      "model-viewer": any;
    }
  }
}

type ViewerStatus = "idle" | "loading" | "ready" | "error";
const MODEL_VIEWER_SRC = "/vendor/model-viewer.min.js";

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
      setVisible(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setVisible(true);
          io.disconnect();
        }
      },
      { rootMargin: "200px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className="relative h-56 overflow-hidden border-b border-ink-900/10 bg-ink-900 blueprint-grid"
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
            background: "radial-gradient(circle at 50% 40%, #1f2225, #0e1011)",
          }}
        />
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-copper-300">
          <Box className="size-12 stroke-[1.2]" />
          <span className="font-mono text-[0.65rem] tracking-widest uppercase text-limestone-400">
            GLB SPATIAL MESH
          </span>
        </div>
      )}
    </div>
  );
}

export function MeiporulARPage() {
  const [search, setSearch] = React.useState("");
  const [activeCategory, setActiveCategory] =
    React.useState<(typeof CATEGORIES)[number]>("All");
  const [selectedIndex, setSelectedIndex] = React.useState<number | null>(null);
  const [viewerStatus, setViewerStatus] = React.useState<ViewerStatus>("idle");

  const ensureViewerLoaded = React.useCallback(() => {
    if (
      typeof window !== "undefined" &&
      (window as any).customElements?.get("model-viewer")
    ) {
      setViewerStatus("ready");
      return;
    }
    const existing = document.querySelector<HTMLScriptElement>(
      "script[data-model-viewer]"
    );
    if (existing) {
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

  React.useEffect(() => {
    ensureViewerLoaded();
  }, [ensureViewerLoaded]);

  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    return models.filter((m) => {
      const catMatch =
        activeCategory === "All" || m.category === activeCategory;
      const textMatch =
        !q ||
        m.name.toLowerCase().includes(q) ||
        m.description.toLowerCase().includes(q);
      return catMatch && textMatch;
    });
  }, [search, activeCategory]);

  const selected =
    selectedIndex != null && filtered[selectedIndex]
      ? filtered[selectedIndex]
      : null;

  const openModelAt = (idx: number) => {
    setSelectedIndex(idx);
    ensureViewerLoaded();
  };

  const stepModel = React.useCallback(
    (delta: number) => {
      setSelectedIndex((prev) => {
        if (prev == null || filtered.length === 0) return prev;
        return (prev + delta + filtered.length) % filtered.length;
      });
    },
    [filtered.length]
  );

  React.useEffect(() => {
    if (selectedIndex == null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelectedIndex(null);
      else if (e.key === "ArrowRight") stepModel(1);
      else if (e.key === "ArrowLeft") stepModel(-1);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [selectedIndex, stepModel]);

  return (
    <PageLayout
      header={
        <PageHeader>
          <div className="sympho-scope on-dark relative overflow-hidden border-b border-limestone-100/10 bg-ink-900 py-14 text-limestone-50 blueprint-grid">
            <div className="container-page">
              <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-limestone-100/10 pb-4">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-label text-copper-300">
                    SI—MAR
                  </span>
                  <span className="sheet-label">
                    Meiporul Spatial AR Studio
                  </span>
                </div>
                <span className="font-mono text-label text-limestone-300">
                  {models.length} Interactive 3D Models — AR Ready
                </span>
              </div>
              <SplitHeading
                as="h1"
                text="Meiporul AR Gallery — Spatial Mathematical Truth"
                className="text-display-xl tracking-tight text-limestone-50"
                italicLast={2}
              />
              <p className="mt-4 max-w-2xl text-lede text-limestone-200">
                Inspect minimal surfaces, Platonic solids, fractals, and vector
                fields in real-time 3D WebGL or project them directly into your
                room using WebXR and mobile Augmented Reality.
              </p>
            </div>
          </div>
        </PageHeader>
      }
      className="sympho-scope bg-limestone-100 text-ink-900"
    >
      <div className="container-page py-12">
        {/* Filter & Search Ledger */}
        <div className="sheet-frame mb-10 flex flex-col gap-5 rounded-lg border border-ink-900/15 bg-limestone-50 p-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((cat) => {
              const isActive = activeCategory === cat;
              const count =
                cat === "All"
                  ? models.length
                  : models.filter((m) => m.category === cat).length;
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => {
                    setActiveCategory(cat);
                    setSelectedIndex(null);
                  }}
                  className={`rounded-pill border px-4 py-2 font-mono text-xs uppercase tracking-wider transition-colors ${
                    isActive
                      ? "border-ink-900 bg-ink-900 text-limestone-50"
                      : "border-ink-900/20 bg-limestone-100 text-ink-700 hover:border-ink-900"
                  }`}
                >
                  {cat} ({count})
                </button>
              );
            })}
          </div>

          <div className="relative w-full lg:w-80">
            <Search className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-ink-500" />
            <input
              type="text"
              placeholder="Search models..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setSelectedIndex(null);
              }}
              className="field-input pl-10"
            />
          </div>
        </div>

        <div className="mb-6 flex items-center justify-between border-b border-ink-900/10 pb-3 font-mono text-xs text-ink-600">
          <span>
            Showing {filtered.length} of {models.length} spatial models
          </span>
          <span>GLTF / GLB 2.0 · WEBXR READY</span>
        </div>

        {filtered.length === 0 ? (
          <div className="sheet-frame rounded-lg border border-ink-900/15 bg-limestone-50 py-14 text-center">
            <p className="font-display text-2xl text-ink-900">
              No models match &ldquo;{search}&rdquo;.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {filtered.map((model, i) => (
              <button
                key={model.file}
                type="button"
                onClick={() => openModelAt(i)}
                className="sheet-frame group flex flex-col justify-between overflow-hidden rounded-lg border border-ink-900/15 bg-limestone-50 text-left transition-all duration-300 hover:-translate-y-1 hover:border-ink-900/40 hover:shadow-lift"
              >
                <div className="w-full">
                  <div className="relative">
                    <LazyModelPreview
                      file={model.file}
                      name={model.name}
                      ready={viewerStatus === "ready"}
                    />
                    <div className="absolute top-3 right-3 flex gap-1.5">
                      <span className="rounded-pill bg-copper-500 px-2.5 py-0.5 font-mono text-[0.65rem] font-medium uppercase text-limestone-50">
                        AR
                      </span>
                      <span className="rounded-pill bg-limestone-50/90 px-2.5 py-0.5 font-mono text-[0.65rem] font-medium uppercase text-ink-900">
                        3D
                      </span>
                    </div>
                  </div>
                  <div className="p-5">
                    <span className="font-mono text-[0.65rem] uppercase tracking-widest text-copper-600">
                      {model.category}
                    </span>
                    <h3 className="mt-1 font-display text-xl font-normal text-ink-900 group-hover:text-copper-600">
                      {model.name}
                    </h3>
                    <p className="mt-2 text-xs leading-relaxed text-ink-600 line-clamp-3">
                      {model.description}
                    </p>
                  </div>
                </div>
                <div className="w-full border-t border-ink-900/10 px-5 py-3 font-mono text-[0.68rem] uppercase tracking-wider text-ink-500 group-hover:text-copper-600">
                  Tap to view in 3D / AR →
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={selected.name}
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/85 p-4 backdrop-blur-sm"
        >
          <div className="sheet-frame on-dark w-full max-w-4xl overflow-hidden rounded-xl border border-limestone-100/20 bg-ink-900 text-limestone-50 shadow-lift">
            <div className="flex items-start justify-between gap-4 border-b border-limestone-100/15 p-6">
              <div className="min-w-0">
                <span className="font-mono text-label text-copper-300">
                  {selected.category}
                </span>
                <h2 className="mt-1 font-display text-2xl font-normal text-limestone-50">
                  {selected.name}
                </h2>
                <p className="mt-1 text-sm text-limestone-300">
                  {selected.description}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  aria-label="Previous model"
                  onClick={() => stepModel(-1)}
                  className="grid size-9 place-items-center rounded-pill border border-limestone-100/25 text-limestone-200 hover:bg-limestone-50 hover:text-ink-900"
                >
                  <ChevronLeft size={16} />
                </button>
                <button
                  type="button"
                  aria-label="Next model"
                  onClick={() => stepModel(1)}
                  className="grid size-9 place-items-center rounded-pill border border-limestone-100/25 text-limestone-200 hover:bg-limestone-50 hover:text-ink-900"
                >
                  <ChevronRight size={16} />
                </button>
                <button
                  type="button"
                  aria-label="Close"
                  onClick={() => setSelectedIndex(null)}
                  className="inline-flex items-center gap-1 rounded-pill border border-limestone-100/25 px-3 py-1.5 font-mono text-xs uppercase text-limestone-200 hover:bg-limestone-50 hover:text-ink-900"
                >
                  <X size={14} /> Close
                </button>
              </div>
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
                  background: "#0e1011",
                }}
              />
            ) : viewerStatus === "error" ? (
              <div
                className="flex flex-col items-center justify-center gap-3 px-6 text-center"
                style={{ height: 500 }}
              >
                <AlertTriangle className="size-10 text-copper-400" />
                <p className="font-display text-2xl">
                  The 3D viewer couldn&apos;t load
                </p>
                <p className="max-w-md text-sm text-limestone-300">
                  You can still download the .glb mesh file and inspect it in
                  any 3D or AR viewer.
                </p>
                <a
                  href={`/models/ar/${selected.file}`}
                  className="mt-2 rounded-pill bg-copper-500 px-5 py-2.5 font-mono text-xs uppercase text-limestone-50"
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
                <div className="size-10 animate-spin rounded-pill border-2 border-copper-400 border-t-transparent" />
                <p className="font-mono text-xs uppercase text-limestone-300">
                  Loading 3D viewer…
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      <SymphoCtaBanner
        eyebrow="Pair Spatial Models With Theory"
        title="Ready to study the mathematics behind these 3D forms?"
        description="Explore our Meiporul courses and interactive browser labs to master multivariable calculus, topology, and solid geometry."
        primaryText="Explore Meiporul Courses"
        primaryTo="/meiporul"
        secondaryText="Open Learning Labs"
        secondaryTo="/labs"
      />
    </PageLayout>
  );
}
