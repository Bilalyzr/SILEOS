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

export default function LabsPage() {
  const [data, setData] = useState<Curriculum | null>(null),
    [catalog, setCatalog] = useState<LabSummary[]>([]);
  const [error, setError] = useState(""),
    [query, setQuery] = useState(""),
    [subject, setSubject] = useState(""),
    [grade, setGrade] = useState("");
  const [view, setView] = useState<"labs" | "curriculum">("labs");
  const [edition, setEdition] = useState("ncert-2024");
  const user = useAuthStore((s) => s.user);
  const author = ["instructor", "admin", "superadmin"].includes(
    user?.role || "",
  );
  const studio =
    user?.role === "admin" || user?.role === "superadmin"
      ? "/admin/lab-studio"
      : "/instructor/lab-studio";
  useEffect(() => {
    let live = true;
    Promise.all([labStudio.curriculum(), listLabs()])
      .then(([d, c]) => {
        if (live) {
          setData(d);
          setCatalog(c);
        }
      })
      .catch(() => {
        if (live)
          setError("Could not load the lab library. Please reload to retry.");
      });
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
                (id) => data?.chapters.find((c) => c.id === id)?.grade,
              )
            )?.includes(Number(grade))) &&
          `${l.title} ${l.description}`
            .toLowerCase()
            .includes(query.toLowerCase()),
      ),
    [catalog, data, grade, query, subject],
  );
  const chapters = useMemo(
    () =>
      data?.chapters.filter(
        (c) =>
          (!c.edition || c.edition === edition) &&
          (!subject || c.subject === subject) &&
          (!grade || c.grade === Number(grade)) &&
          c.title.toLowerCase().includes(query.toLowerCase()),
      ) || [],
    [data, edition, grade, query, subject],
  );
  return (
    <div className="sf-page lab-library">
      <header className="sf-hero">
        <div>
          <span className="sf-eyebrow">Sasha learning labs</span>
          <h1>
            Make a prediction.
            <br />
            <em>See what happens.</em>
          </h1>
          <p>
            Your experiments, connected to your curriculum. Explore in the
            browser, step into VR, or bring a model into your room.
          </p>
          <div className="sf-actions">
            <button
              className="sf-primary"
              onClick={() =>
                document
                  .getElementById("lab-results")
                  ?.scrollIntoView({ behavior: "smooth" })
              }
            >
              Explore the labs <ArrowUpRight size={18} />
            </button>
            {author && (
              <Link className="sf-secondary" to={studio}>
                <Plus size={17} /> Create a lab
              </Link>
            )}
            <ShareButton
              title="Make a prediction. See what happens."
              description="Explore interactive curriculum-connected learning labs on SashaInfinity."
              variant="outline"
              className="brand-banner-share"
            />
          </div>
        </div>
        <div className="lab-hero-art" aria-hidden="true">
          <div className="lab-orbit">
            <FlaskConical size={70} strokeWidth={1.2} />
            <span className="lab-orbit-dot" />
          </div>
          <span className="sf-chip">Explore · predict · investigate</span>
        </div>
      </header>
      <div className="sf-stat-grid">
        <div>
          <FlaskConical />
          <strong>{data?.labs.length ?? "—"}</strong>
          <span>Your imported simulations</span>
        </div>
        <div>
          <BookOpen />
          <strong>
            {data?.chapters.filter((c) => !c.edition || c.edition === edition)
              .length ?? "—"}
          </strong>
          <span>Chapters in selected curriculum</span>
        </div>
        <div>
          <Box />
          <strong>Screen · AR · VR</strong>
          <span>Capabilities vary by device and lab</span>
        </div>
      </div>
      <section className="sf-surface" id="lab-results">
        <div className="sf-section-heading">
          <div>
            <span className="sf-eyebrow">The experiment library</span>
            <h2>Find your next discovery</h2>
          </div>
          <div className="sf-segment" aria-label="Library view">
            <button
              aria-pressed={view === "labs"}
              onClick={() => setView("labs")}
            >
              Labs
            </button>
            <button
              aria-pressed={view === "curriculum"}
              onClick={() => setView("curriculum")}
            >
              Curriculum
            </button>
          </div>
        </div>
        <div className="sf-filter-row">
          {view === "curriculum" && data?.editions && (
            <select
              aria-label="Curriculum edition"
              value={edition}
              onChange={(e) => setEdition(e.target.value)}
            >
              {data.editions.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          )}
          <label className="sf-search">
            <Search size={18} />
            <input
              aria-label="Search labs or chapters"
              placeholder="Search a concept, chapter or experiment…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <select
            aria-label="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
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
              <option key={s}>{s}</option>
            ))}
          </select>
          <select
            aria-label="Class"
            value={grade}
            onChange={(e) => setGrade(e.target.value)}
          >
            <option value="">Every class</option>
            {[6, 7, 8, 9, 10, 11, 12].map((g) => (
              <option value={g} key={g}>
                Class {g}
              </option>
            ))}
          </select>
        </div>
        {error && <p role="alert">{error}</p>}
        {!data && !error && <p role="status">Loading your lab library…</p>}
        {view === "labs" ? (
          <>
            <p className="sf-muted">
              {labs.length} experiments · shared curriculum and
              instructor-published labs
            </p>
            <div className="lab-card-grid">
              {labs.map((l) => {
                const bundle = data?.labs.find((b) => b.slug === l.slug);
                return (
                  <Link
                    className="lab-card"
                    key={l.slug}
                    to={`/labs/${l.slug}`}
                  >
                    <div className={`lab-card-art lab-${l.subject}`}>
                      <FlaskConical size={38} strokeWidth={1.2} />
                      <span>
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
                    </div>
                    <div className="lab-card-body">
                      <span className="sf-eyebrow">
                        {l.subject}
                        {bundle && ` · Classes ${bundle.grades.join(", ")}`}
                      </span>
                      <h3>{l.title}</h3>
                      <p>
                        {l.description ||
                          "Open the lab to explore its learning activities."}
                      </p>
                      <span className="lab-card-link">
                        Enter lab <ArrowUpRight size={17} />
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
            {data && !labs.length && <p>No experiments match these filters.</p>}
          </>
        ) : (
          <>
            <p className="sf-muted">
              {chapters.filter((c) => c.lab_slug).length} of {chapters.length}{" "}
              matching chapters have a linked activity. Each activity explores
              part of a chapter. Chapters without a link are available for
              instructor authoring.
            </p>
            <div className="lab-chapters">
              {chapters.map((c) => (
                <article key={c.id}>
                  <span className="sf-chip">
                    Class {c.grade} · {c.subject}
                  </span>
                  <h3>{c.title}</h3>
                  <span className="sf-muted">
                    {["", "Foundation", "Core", "Advanced"][c.difficulty]}
                  </span>
                  {c.lab_slug ? (
                    <Link to={`/labs/${c.lab_slug}`}>
                      {c.activity_kind === "classification"
                        ? "Open concept investigation"
                        : "Open linked simulation"}{" "}
                      <ArrowUpRight size={16} />
                    </Link>
                  ) : author ? (
                    <Link to={`${studio}?chapter=${encodeURIComponent(c.id)}`}>
                      Build this concept lab <Plus size={16} />
                    </Link>
                  ) : (
                    <span className="sf-muted">
                      <Layers size={16} /> Awaiting a purpose-built lab
                    </span>
                  )}
                  {catalog
                    .filter(
                      (l) => !l.is_builtin && l.chapter_ids?.includes(c.id),
                    )
                    .map((l) => (
                      <Link key={l.slug} to={`/labs/${l.slug}`}>
                        Instructor lab: {l.title} <ArrowUpRight size={16} />
                      </Link>
                    ))}
                  {author && c.lab_slug && (
                    <Link to={`${studio}?chapter=${encodeURIComponent(c.id)}`}>
                      Create another activity <Plus size={16} />
                    </Link>
                  )}
                </article>
              ))}
            </div>
          </>
        )}
      </section>
      <p className="sf-muted">{data?.source}</p>
    </div>
  );
}
