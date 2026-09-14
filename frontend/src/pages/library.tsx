import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { PageLayout } from "@/components/design-system/PageLayout";
import { PageBanner } from "@/components/design-system/PageBanner";
/**
 * Digital Library storefront — public browse of published ebooks
 * (backend: GET /api/v1/library). Category tabs mirror the three store
 * categories (Books / Guides / Lecture Notes); search hits the title
 * ilike filter server-side.
 */
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, Search } from "lucide-react";
import { EBOOK_CATEGORY_LABELS, libraryAPI, type Ebook } from "@/api/library";

const TABS = [
  { value: "", label: "All" },
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
            setError(e?.response?.data?.detail ?? "Failed to load the library"),
          )
          .finally(() => setLoading(false));
      },
      q ? 300 : 0,
    ); // debounce search only
    return () => clearTimeout(t);
  }, [category, q]);

  const grouped = useMemo(() => ebooks, [ebooks]);

  return (
    <PageLayout
      header={
        <PageBanner
          eyebrow="Digital library"
          title="Ideas worth keeping"
          description="Explore ebooks, guides and lecture notes. Buy once and keep every available download in your library."
          share
          shareTitle="Explore the SashaInfinity Digital Library"
          actions={
            <label className="relative block w-full sm:w-72">
              <span className="sr-only">Search ebooks</span>
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-orange-800 h-4 w-4" />
              <input
                type="search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search titles…"
                aria-label="Search ebooks"
                className="pl-10 pr-4 py-2 w-full border border-orange-200 bg-white/70 rounded-xl"
              />
            </label>
          }
        />
      }
      className="rd-screen rd-screen-library"
    >
      <div
        className="flex gap-2 mb-6"
        role="tablist"
        aria-label="Ebook categories"
      >
        {TABS.map((t) => (
          <button
            key={t.value}
            role="tab"
            aria-selected={category === t.value}
            onClick={() => setCategory(t.value)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${
              category === t.value
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="h-56 rounded-xl bg-gray-100 animate-pulse"
            />
          ))}
        </div>
      ) : error ? (
        <p role="alert" className="text-red-600 text-sm">
          {error}
        </p>
      ) : grouped.length === 0 ? (
        <p className="text-gray-500 text-sm border border-dashed border-gray-300 rounded-xl p-8 text-center">
          No ebooks here yet — instructors are writing!
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {grouped.map((e) => (
            <Link
              key={e.id}
              to={`/library/${e.slug}`}
              className="group border border-gray-200 rounded-xl overflow-hidden bg-white hover:shadow-md transition-shadow flex flex-col"
            >
              <div className="h-36 bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center relative">
                {e.cover_image ? (
                  <img
                    src={e.cover_image}
                    alt=""
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <BookOpen className="h-12 w-12 text-blue-400" aria-hidden />
                )}
                <span className="absolute top-2 right-2 text-[11px] font-semibold bg-white/90 text-gray-700 px-2 py-0.5 rounded-full">
                  {EBOOK_CATEGORY_LABELS[e.category] ?? e.category}
                </span>
              </div>
              <div className="p-4 flex-1 flex flex-col">
                <h3 className="font-semibold text-gray-900 line-clamp-2 group-hover:text-blue-700">
                  {e.title}
                </h3>
                {e.course_title && (
                  <p className="text-xs text-gray-500 mt-1">
                    <AstraSymbol value="📘" /> {e.course_title}
                  </p>
                )}
                <p className="text-sm text-gray-600 line-clamp-2 mt-1 flex-1">
                  {e.description}
                </p>
                <div className="mt-3 flex items-center justify-between">
                  <PriceTag ebook={e} />
                  {e.page_count ? (
                    <span className="text-xs text-gray-400">
                      {e.page_count} pages
                    </span>
                  ) : null}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </PageLayout>
  );
}

export function PriceTag({ ebook }: { ebook: Ebook }) {
  if (ebook.effective_price_inr === 0) {
    return <span className="font-bold text-emerald-600">FREE</span>;
  }
  return (
    <span className="flex items-baseline gap-2">
      <span className="font-bold text-gray-900">
        ₹{ebook.effective_price_inr}
      </span>
      {ebook.discount_price_inr != null &&
        ebook.discount_price_inr < ebook.price_inr && (
          <span className="text-xs text-gray-400 line-through">
            ₹{ebook.price_inr}
          </span>
        )}
    </span>
  );
}
