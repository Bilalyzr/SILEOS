import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, BookOpen, Search } from "lucide-react";
import { EBOOK_CATEGORY_LABELS, libraryAPI, type Ebook } from "@/api/library";
import {
  SymphoButton,
  SymphoCtaBanner,
  SymphoPageHero,
} from "@/components/sympho/SymphoSystem";

const TABS = [
  { value: "", label: "All Volumes" },
  { value: "book", label: EBOOK_CATEGORY_LABELS.book },
  { value: "guide", label: EBOOK_CATEGORY_LABELS.guide },
  { value: "lecture_notes", label: EBOOK_CATEGORY_LABELS.lecture_notes },
];

export default function LibraryPage() {
  const [ebooks, setEbooks] = useState<Ebook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState("");
  const [q, setQ] = useState("");

  useEffect(() => {
    const t = setTimeout(
      () => {
        setLoading(true);
        libraryAPI
          .listPublished({
            category: category || undefined,
            q: q.trim() || undefined,
          })
          .then((d) => {
            setEbooks(d.ebooks);
            setError(null);
          })
          .catch((e) =>
            setError(e?.response?.data?.detail ?? "Failed to load the library")
          )
          .finally(() => setLoading(false));
      },
      q ? 300 : 0
    );
    return () => clearTimeout(t);
  }, [category, q]);

  const grouped = useMemo(() => ebooks, [ebooks]);

  return (
    <div className="sympho-scope min-h-screen bg-limestone-100 text-ink-900">
      <SymphoPageHero
        index="SI—LIB"
        eyebrow="Digital Library & Monographs"
        title="Technical volumes, guides & annotated lecture notes"
        lede="Explore peer-reviewed e-books, engineering playbooks, and instructor-authored monographs. Acquire once and retain permanent access inside your personal reading room."
        drawingCode="SHEET SI—LIB · ARCHIVE"
        badge={`${grouped.length || 0} Volumes Indexed`}
        specs={[
          { label: "Formats", value: "PDF / Interactive" },
          { label: "Categories", value: "Books · Guides · Notes" },
          { label: "Access", value: "Permanent Library" },
          { label: "Authorship", value: "Faculty & Fellows" },
        ]}
        primaryAction={
          <SymphoButton to="/courses" variant="on-dark" arrow>
            Browse paired courses
          </SymphoButton>
        }
        secondaryAction={
          <SymphoButton to="/my-library" variant="outline-dark">
            My reading room
          </SymphoButton>
        }
      />

      <section className="py-section-sm">
        <div className="container-page">
          {/* Architectural Search & Category Bar */}
          <div className="sheet-frame mb-12 flex flex-col gap-5 rounded-lg border border-ink-900/15 bg-limestone-50 p-6 lg:flex-row lg:items-center lg:justify-between">
            <div
              className="flex flex-wrap gap-2"
              role="tablist"
              aria-label="Ebook categories"
            >
              {TABS.map((t) => {
                const active = category === t.value;
                return (
                  <button
                    key={t.value}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    onClick={() => setCategory(t.value)}
                    className={`rounded-pill border px-4 py-2 font-mono text-xs uppercase tracking-wider transition-colors ${
                      active
                        ? "border-ink-900 bg-ink-900 text-limestone-50"
                        : "border-ink-900/20 bg-limestone-100 text-ink-700 hover:border-ink-900"
                    }`}
                  >
                    {t.label}
                  </button>
                );
              })}
            </div>

            <label className="relative block w-full lg:w-80">
              <span className="sr-only">Search ebooks</span>
              <Search className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-ink-500" />
              <input
                type="search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search titles…"
                aria-label="Search ebooks"
                className="field-input pl-10"
              />
            </label>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div
                  key={i}
                  className="h-72 animate-pulse rounded-lg border border-ink-900/10 bg-limestone-50"
                />
              ))}
            </div>
          ) : error ? (
            <p
              role="alert"
              className="rounded-lg border border-copper-500/40 bg-copper-200/20 p-6 text-sm text-ink-900"
            >
              {error}
            </p>
          ) : grouped.length === 0 ? (
            <div className="sheet-frame rounded-lg border border-ink-900/15 bg-limestone-50 p-12 text-center">
              <BookOpen className="mx-auto mb-4 size-10 text-copper-500" />
              <h3 className="font-display text-2xl font-normal text-ink-900">
                No ebooks here yet — instructors are writing!
              </h3>
              <p className="mx-auto mt-2 max-w-md text-sm text-ink-600">
                New engineering monographs, study guides, and annotated lecture
                compendiums are being prepared for publication.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
              {grouped.map((e, idx) => (
                <Link
                  key={e.id}
                  to={`/library/${e.slug}`}
                  className="sheet-frame group flex flex-col justify-between overflow-hidden rounded-lg border border-ink-900/15 bg-limestone-50 transition-all duration-300 hover:-translate-y-1 hover:shadow-lift"
                >
                  <div>
                    <div className="relative flex h-48 items-center justify-center overflow-hidden border-b border-ink-900/10 bg-ink-900 text-limestone-100 blueprint-grid">
                      {e.cover_image ? (
                        <img
                          src={e.cover_image}
                          alt=""
                          className="h-full w-full object-cover transition-transform duration-700 ease-out-expo group-hover:scale-105"
                        />
                      ) : (
                        <div className="flex flex-col items-center gap-2 text-copper-300">
                          <BookOpen className="size-10 stroke-[1.3]" aria-hidden />
                          <span className="font-mono text-[0.65rem] tracking-widest uppercase text-limestone-300">
                            VOL. {String(idx + 1).padStart(2, "0")}
                          </span>
                        </div>
                      )}
                      <span className="absolute top-3 right-3 rounded-pill bg-limestone-50/92 px-3 py-1 font-mono text-[0.65rem] uppercase tracking-wider text-ink-900">
                        {EBOOK_CATEGORY_LABELS[e.category] ?? e.category}
                      </span>
                    </div>

                    <div className="p-6">
                      {e.course_title && (
                        <p className="mb-2 font-mono text-label text-copper-600">
                          {e.course_title}
                        </p>
                      )}
                      <h3 className="font-display text-2xl font-normal text-ink-900 transition-colors group-hover:text-copper-600 line-clamp-2">
                        {e.title}
                      </h3>
                      <p className="mt-2.5 text-sm leading-relaxed text-ink-600 line-clamp-3">
                        {e.description}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between border-t border-ink-900/10 px-6 py-4">
                    <PriceTag ebook={e} />
                    <div className="flex items-center gap-3 font-mono text-xs text-ink-500">
                      {e.page_count ? <span>{e.page_count} pages</span> : null}
                      <ArrowUpRight className="size-4 text-ink-900 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-copper-600" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      <SymphoCtaBanner
        eyebrow="Continuous Access"
        title="Want unlimited access to courses, labs & publications?"
        description="Unlock our entire catalog of courses and learning tracks with a SashaInfinity Membership pass."
        primaryText="Explore membership"
        primaryTo="/membership"
        secondaryText="View course bundles"
        secondaryTo="/bundles"
      />
    </div>
  );
}

export function PriceTag({ ebook }: { ebook: Ebook }) {
  if (ebook.effective_price_inr === 0) {
    return (
      <span className="font-mono text-xs font-semibold uppercase tracking-wider text-sage-700">
        FREE
      </span>
    );
  }
  return (
    <span className="flex items-baseline gap-2">
      <span className="font-display text-xl font-normal text-ink-900">
        ₹{ebook.effective_price_inr}
      </span>
      {ebook.discount_price_inr != null &&
        ebook.discount_price_inr < ebook.price_inr && (
          <span className="font-mono text-xs text-ink-400 line-through">
            ₹{ebook.price_inr}
          </span>
        )}
    </span>
  );
}
