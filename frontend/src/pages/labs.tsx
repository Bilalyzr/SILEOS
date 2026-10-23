import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Box,
  FlaskConical,
  Search,
  Layers,
  Plus,
  BookOpen,
} from "lucide-react";
import { labStudio, type Curriculum } from "@/api/lab-studio";
import { listLabs, type LabSummary } from "@/api/labs";
import { useAuthStore } from "@/store/auth";
import { ShareButton } from "@/components/ui/share-button";
import {
  SplitHeading,
  SymphoButton,
  SymphoCtaBanner,
  SymphoDimensionLine,
} from "@/components/sympho/SymphoSystem";

export default function LabsPage() {
  const [data, setData] = useState<Curriculum | null>(null);
  const [catalog, setCatalog] = useState<LabSummary[]>([]);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [subject, setSubject] = useState("");
  const [grade, setGrade] = useState("");
  const [view, setView] = useState<"labs" | "curriculum">("labs");
  const [edition, setEdition] = useState("ncert-2024");
  const user = useAuthStore((s) => s.user);
  const author = ["instructor", "admin", "superadmin"].includes(
    user?.role || ""
  );
  const studio =
    user?.role === "admin" || user?.role === "superadmin"
      ? "/admin/lab-studio"
      : "/instructor/lab-studio";

  useEffect(() => {
    let live = true;
    Promise.allSettled([labStudio.curriculum(), listLabs()]).then(
      ([d, c]) => {
        if (!live) return;
        if (d.status === "fulfilled") setData(d.value);
        if (c.status === "fulfilled") setCatalog(c.value);
        if (d.status === "rejected" || c.status === "rejected")
          setError(
            "Part of the lab library could not be loaded — some sections may be missing."
          );
      }
    );
    return () => {
      live = false;
    };
  }, []);

  const labs = useMemo(
    () =>
      catalog.filter(
        (l) =>
          (!subject || l.subject === subject) &&
          (!grade ||
            (
              l.grades ||
              data?.labs.find((b) => b.slug === l.slug)?.grades ||
              l.chapter_ids?.map(
                (id) => data?.chapters.find((c) => c.id === id)?.grade
              )
            )?.includes(Number(grade))) &&
          `${l.title} ${l.description}`
            .toLowerCase()
            .includes(query.toLowerCase())
      ),
    [catalog, data, grade, query, subject]
  );

  const chapters = useMemo(
    () =>
      data?.chapters.filter(
        (c) =>
          (!c.edition || c.edition === edition) &&
          (!subject || c.subject === subject) &&
          (!grade || c.grade === Number(grade)) &&
          c.title.toLowerCase().includes(query.toLowerCase())
      ) || [],
    [data, edition, grade, query, subject]
  );

  const chapterCount =
    data?.chapters.filter((c) => !c.edition || c.edition === edition).length ??
    "—";

  return (
    <div className="sympho-scope min-h-screen bg-limestone-100 text-ink-900">
      {/* Sympho Architectural Dark Hero */}
      <header className="on-dark relative overflow-hidden border-b border-limestone-100/10 bg-ink-900 text-limestone-50 blueprint-grid">
        <div className="container-page relative z-10 pt-12 pb-16 lg:pt-16 lg:pb-20">
          <div className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b border-limestone-100/10 pb-5">
            <div className="flex items-center gap-4">
              <span className="font-mono text-label text-copper-300">
                SI—LABS
              </span>
              <span className="sheet-label">Sasha learning labs</span>
            </div>
            <span className="font-mono text-label text-limestone-300">
              Explore · predict · investigate
            </span>
          </div>

          <div className="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:items-end">
            <div className="lg:col-span-8">
              <SplitHeading
                as="h1"
                text="Make a prediction. See what happens."
                className="text-display-xl tracking-tight text-limestone-50"
                italicLast={2}
              />
              <p className="mt-6 max-w-2xl text-lede text-limestone-200">
                Your experiments, connected to your curriculum. Explore in the
                browser, step into VR, or bring a model into your room.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-4">
                <SymphoButton
                  variant="on-dark"
                  size="lg"
                  arrow
                  onClick={() =>
                    document
                      .getElementById("lab-results")
                      ?.scrollIntoView({ behavior: "smooth" })
                  }
                >
                  Explore the labs
                </SymphoButton>
                {author && (
                  <SymphoButton to={studio} variant="outline-dark" size="lg">
                    <span className="inline-flex items-center gap-2">
                      <Plus size={16} /> Create a lab
                    </span>
                  </SymphoButton>
                )}
                <ShareButton
                  title="Make a prediction. See what happens."
                  description="Explore interactive curriculum-connected learning labs on SashaInfinity."
                  variant="outline"
                  className="rounded-pill border-limestone-100/25 text-limestone-50 hover:bg-limestone-50 hover:text-ink-900"
                />
              </div>
            </div>

            <div className="lg:col-span-4">
              <div className="sheet-frame rounded-lg border border-limestone-100/15 bg-ink-950/70 p-6 backdrop-blur-md">
                <div className="flex items-center justify-between border-b border-limestone-100/10 pb-3 font-mono text-label text-limestone-300">
                  <span>LABORATORY TELEMETRY</span>
                  <span className="text-copper-300">LIVE</span>
                </div>
                <div className="mt-5 flex items-center gap-4">
                  <div className="grid size-14 place-items-center rounded-lg border border-copper-400/40 bg-copper-500/15 text-copper-300">
                    <FlaskConical size={28} strokeWidth={1.3} />
                  </div>
                  <div>
                    <div className="font-display text-2xl font-light text-limestone-50">
                      Screen · AR · VR
                    </div>
                    <div className="text-xs text-limestone-300">
                      Capabilities vary by device and lab
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Dimension-Line Figures Bar */}
      <section className="border-b border-ink-900/10 py-12">
        <div className="container-page">
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            <div className="pr-6 sm:border-r sm:border-ink-900/10">
              <div className="flex items-center gap-2 font-mono text-label text-copper-600">
                <FlaskConical size={14} />
                <span>SIMULATIONS</span>
              </div>
              <div className="mt-2 font-display text-display-lg font-light text-ink-900">
                {data?.labs.length ?? "—"}
              </div>
              <SymphoDimensionLine />
              <p className="mt-2 text-sm text-ink-600">
                Your imported simulations
              </p>
            </div>

            <div className="sm:border-r sm:border-ink-900/10 sm:px-6">
              <div className="flex items-center gap-2 font-mono text-label text-copper-600">
                <BookOpen size={14} />
                <span>CURRICULUM CHAPTERS</span>
              </div>
              <div className="mt-2 font-display text-display-lg font-light text-ink-900">
                {chapterCount}
              </div>
              <SymphoDimensionLine />
              <p className="mt-2 text-sm text-ink-600">
                Chapters in selected curriculum
              </p>
            </div>

            <div className="sm:pl-6">
              <div className="flex items-center gap-2 font-mono text-label text-copper-600">
                <Box size={14} />
                <span>SPATIAL MODES</span>
              </div>
              <div className="mt-2 font-display text-display-md font-light text-ink-900">
                Screen · AR · VR
              </div>
              <SymphoDimensionLine />
              <p className="mt-2 text-sm text-ink-600">
                Capabilities vary by device and lab
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Experiment Library & Curriculum Matrix */}
      <section className="py-section-sm" id="lab-results">
        <div className="container-page">
          <div className="flex flex-col gap-6 border-b border-ink-900/10 pb-8 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="mb-3 flex items-center gap-3">
                <span className="font-mono text-label text-copper-500">
                  SI—EXP
                </span>
                <span className="sheet-label">The experiment library</span>
              </div>
              <SplitHeading
                as="h2"
                text="Find your next discovery"
                className="text-display-lg tracking-tight text-ink-900"
                italicLast={2}
              />
            </div>

            <div
              className="inline-flex rounded-pill border border-ink-900/20 bg-limestone-50 p-1"
              aria-label="Library view"
            >
              <button
                type="button"
                aria-pressed={view === "labs"}
                onClick={() => setView("labs")}
                className={`rounded-pill px-5 py-2 font-mono text-xs uppercase tracking-wider transition-colors ${
                  view === "labs"
                    ? "bg-ink-900 text-limestone-50"
                    : "text-ink-600 hover:text-ink-900"
                }`}
              >
                Labs
              </button>
              <button
                type="button"
                aria-pressed={view === "curriculum"}
                onClick={() => setView("curriculum")}
                className={`rounded-pill px-5 py-2 font-mono text-xs uppercase tracking-wider transition-colors ${
                  view === "curriculum"
                    ? "bg-ink-900 text-limestone-50"
                    : "text-ink-600 hover:text-ink-900"
                }`}
              >
                Curriculum
              </button>
            </div>
          </div>

          {/* Filter Row */}
          <div className="sheet-frame mt-8 grid grid-cols-1 gap-4 rounded-lg border border-ink-900/15 bg-limestone-50 p-5 md:grid-cols-12">
            {view === "curriculum" && data?.editions && (
              <div className="md:col-span-3">
                <select
                  aria-label="Curriculum edition"
                  value={edition}
                  onChange={(e) => setEdition(e.target.value)}
                  className="field-input"
                >
                  {data.editions.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <label
              className={`relative block ${
                view === "curriculum" && data?.editions
                  ? "md:col-span-5"
                  : "md:col-span-6"
              }`}
            >
              <Search
                size={16}
                className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-ink-500"
              />
              <input
                aria-label="Search labs or chapters"
                placeholder="Search a concept, chapter or experiment…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="field-input pl-10"
              />
            </label>

            <div
              className={
                view === "curriculum" && data?.editions
                  ? "md:col-span-2"
                  : "md:col-span-3"
              }
            >
              <select
                aria-label="Subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="field-input"
              >
                <option value="">Every subject</option>
                {[
                  "science",
                  "mathematics",
                  "physics",
                  "chemistry",
                  "biology",
                  "general",
                ].map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div
              className={
                view === "curriculum" && data?.editions
                  ? "md:col-span-2"
                  : "md:col-span-3"
              }
            >
              <select
                aria-label="Class"
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
                className="field-input"
              >
                <option value="">Every class</option>
                {[6, 7, 8, 9, 10, 11, 12].map((g) => (
                  <option value={g} key={g}>
                    Class {g}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {error && (
            <p
              role="alert"
              className="mt-6 rounded-md border border-copper-500/40 bg-copper-200/20 p-4 text-sm text-ink-900"
            >
              {error}
            </p>
          )}
          {!data && !error && (
            <p role="status" className="mt-8 font-mono text-sm text-ink-600">
              Loading your lab library…
            </p>
          )}

          {view === "labs" ? (
            <div className="mt-8">
              <p className="mb-6 font-mono text-xs uppercase tracking-wider text-ink-500">
                {labs.length} experiments · shared curriculum and
                instructor-published labs
              </p>

              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {labs.map((l, idx) => {
                  const bundle = data?.labs.find((b) => b.slug === l.slug);
                  return (
                    <Link
                      key={l.slug}
                      to={`/labs/${l.slug}`}
                      className="sheet-frame group flex flex-col justify-between rounded-lg border border-ink-900/15 bg-limestone-50 p-6 transition-all duration-300 hover:-translate-y-1 hover:border-ink-900/40 hover:shadow-lift"
                    >
                      <div>
                        <div className="flex items-center justify-between border-b border-ink-900/10 pb-4">
                          <span className="inline-flex items-center gap-2 font-mono text-label text-copper-600">
                            <span>
                              LAB {String(idx + 1).padStart(2, "0")}
                            </span>
                            <span>·</span>
                            <span>{l.subject}</span>
                          </span>
                          <span className="grid size-9 place-items-center rounded-md border border-ink-900/15 bg-limestone-100 text-ink-800 group-hover:border-ink-900 group-hover:bg-ink-900 group-hover:text-limestone-50">
                            <FlaskConical size={17} strokeWidth={1.4} />
                          </span>
                        </div>

                        <div className="mt-4">
                          <span className="inline-block rounded-pill border border-ink-900/15 bg-limestone-100 px-3 py-0.5 font-mono text-[0.65rem] uppercase text-ink-600">
                            {bundle
                              ? bundle.spatial === "scene"
                                ? "3D scene · AR / VR"
                                : "Interactive panel · AR / VR"
                              : l.native_template === "concept_lab"
                              ? "Concept experiment · AR / VR"
                              : l.provider === "native"
                              ? "Interactive exercise"
                              : "External simulation"}
                          </span>
                          {bundle && (
                            <span className="ml-2 font-mono text-xs text-ink-500">
                              Classes {bundle.grades.join(", ")}
                            </span>
                          )}
                        </div>

                        <h3 className="mt-4 font-display text-2xl font-normal text-ink-900 group-hover:text-copper-600">
                          {l.title}
                        </h3>
                        <p className="mt-2 text-sm leading-relaxed text-ink-600">
                          {l.description ||
                            "Open the lab to explore its learning activities."}
                        </p>
                      </div>

                      <div className="mt-6 flex items-center justify-between border-t border-ink-900/10 pt-4 font-mono text-label text-ink-900 group-hover:text-copper-600">
                        <span>Enter lab</span>
                        <ArrowUpRight size={15} />
                      </div>
                    </Link>
                  );
                })}
              </div>

              {data && !labs.length && (
                <p className="mt-8 rounded-lg border border-ink-900/10 bg-limestone-50 p-8 text-center text-sm text-ink-600">
                  No experiments match these filters.
                </p>
              )}
            </div>
          ) : (
            <div className="mt-8">
              <p className="mb-6 text-sm text-ink-600">
                {chapters.filter((c) => c.lab_slug).length} of {chapters.length}{" "}
                matching chapters have a linked activity. Each activity explores
                part of a chapter. Chapters without a link are available for
                instructor authoring.
              </p>

              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {chapters.map((c) => (
                  <article
                    key={c.id}
                    className="sheet-frame flex flex-col justify-between rounded-lg border border-ink-900/15 bg-limestone-50 p-6"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="rounded-pill border border-ink-900/15 bg-limestone-100 px-3 py-1 font-mono text-label text-ink-700">
                          Class {c.grade} · {c.subject}
                        </span>
                        <span className="font-mono text-xs text-copper-600">
                          {["", "Foundation", "Core", "Advanced"][c.difficulty]}
                        </span>
                      </div>

                      <h3 className="mt-4 font-display text-2xl font-normal text-ink-900">
                        {c.title}
                      </h3>
                    </div>

                    <div className="mt-6 space-y-2 border-t border-ink-900/10 pt-4 text-sm">
                      {c.lab_slug ? (
                        <Link
                          to={`/labs/${c.lab_slug}`}
                          className="inline-flex items-center gap-1.5 font-medium text-copper-600 hover:underline"
                        >
                          {c.activity_kind === "classification"
                            ? "Open concept investigation"
                            : "Open linked simulation"}{" "}
                          <ArrowUpRight size={15} />
                        </Link>
                      ) : author ? (
                        <Link
                          to={`${studio}?chapter=${encodeURIComponent(c.id)}`}
                          className="inline-flex items-center gap-1.5 font-medium text-ink-900 hover:text-copper-600"
                        >
                          Build this concept lab <Plus size={15} />
                        </Link>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-xs text-ink-500">
                          <Layers size={14} /> Awaiting a purpose-built lab
                        </span>
                      )}

                      {catalog
                        .filter(
                          (l) => !l.is_builtin && l.chapter_ids?.includes(c.id)
                        )
                        .map((l) => (
                          <div key={l.slug}>
                            <Link
                              to={`/labs/${l.slug}`}
                              className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-800 hover:text-copper-600"
                            >
                              Instructor lab: {l.title}{" "}
                              <ArrowUpRight size={14} />
                            </Link>
                          </div>
                        ))}

                      {author && c.lab_slug && (
                        <div>
                          <Link
                            to={`${studio}?chapter=${encodeURIComponent(c.id)}`}
                            className="inline-flex items-center gap-1.5 text-xs text-ink-600 hover:text-copper-600"
                          >
                            Create another activity <Plus size={14} />
                          </Link>
                        </div>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            </div>
          )}

          {data?.source && (
            <p className="mt-10 font-mono text-xs text-ink-500">
              {data.source}
            </p>
          )}
        </div>
      </section>

      <SymphoCtaBanner
        eyebrow="Spatial & Interactive Pedagogy"
        title="Want to experience 3D models in Augmented Reality?"
        description="Step into the Meiporul AR studio to project mathematical surfaces, physics apparatus, and anatomical structures directly into your space."
        primaryText="Open Meiporul AR"
        primaryTo="/meiporul-ar"
        secondaryText="Explore full courses"
        secondaryTo="/courses"
      />
    </div>
  );
}
