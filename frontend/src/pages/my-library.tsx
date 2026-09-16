import { PageLayout } from "@/components/design-system/PageLayout";
import { PageBanner } from "@/components/design-system/PageBanner";
/**
 * My Library — the signed-in student's purchased/granted ebooks with
 * download availability (GET /library/me). Grants survive unpublishing by
 * design (spec §4), so the list is the source of truth — not store status.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, Download } from "lucide-react";
import { libraryAPI, type Ebook } from "@/api/library";
import { PriceTag } from "./library";

export default function MyLibraryPage() {
  const [items, setItems] = useState<Ebook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    libraryAPI
      .myLibrary()
      .then((d) => setItems(Array.isArray(d?.items) ? d.items : []))
      .catch((e) =>
        setError(e?.response?.data?.detail ?? "Failed to load your library"),
      )
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <PageLayout
      header={
        <PageBanner
          eyebrow="Your reading shelf"
          title="My Library"
          description="Return to your ebooks and study material. Your available downloads stay with you even when a title leaves the storefront."
          actions={
            <Link className="brand-text-link" to="/library">
              Discover more titles →
            </Link>
          }
        />
      }
      className="rd-screen rd-screen-my-library"
    >
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 rounded-xl bg-gray-100 animate-pulse"
            />
          ))}
        </div>
      ) : error ? (
        <div role="alert" className="text-sm text-red-600">
          <p>{error}</p>
          <button
            onClick={load}
            className="mt-2 px-4 py-1.5 rounded-lg bg-gray-900 text-white text-xs font-semibold hover:bg-gray-700"
          >
            Try again
          </button>
        </div>
      ) : items.length === 0 ? (
        <div className="border border-dashed border-gray-300 rounded-xl p-10 text-center">
          <p className="text-gray-500 text-sm">Nothing here yet.</p>
          <Link
            to="/library"
            className="text-blue-600 text-sm hover:underline mt-1 inline-block"
          >
            Browse the Digital Library →
          </Link>
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((e) => (
            <li
              key={e.id}
              className="border border-gray-200 rounded-xl bg-white p-4 flex flex-wrap items-center gap-4"
            >
              <div className="h-14 w-14 rounded-lg bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center shrink-0">
                <BookOpen className="h-6 w-6 text-blue-400" aria-hidden />
              </div>
              <div className="flex-1 min-w-0">
                <Link
                  to={`/library/${e.slug}`}
                  className="font-semibold text-gray-900 hover:text-blue-700 line-clamp-1"
                >
                  {e.title}
                </Link>
                <p className="text-xs text-gray-500 mt-0.5">
                  added{" "}
                  {e.granted_at
                    ? new Date(e.granted_at).toLocaleDateString()
                    : "—"}{" "}
                  · <PriceTag ebook={e} />
                </p>
              </div>
              <button
                onClick={() => libraryAPI.download(e.id)}
                disabled={!e.downloadable}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Download className="h-4 w-4" />
                {e.downloadable ? "Download" : "File coming soon"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </PageLayout>
  );
}
