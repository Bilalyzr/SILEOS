import { PageLayout } from "@/components/design-system/PageLayout";
import { PageBanner } from "@/components/design-system/PageBanner";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Layers, Loader2, BookOpen } from "lucide-react";
import { Card } from "@/components/ui/card";
import { fetchBundles, BundleSummary } from "@/api/bundle";

const savingsPercent = (bundle: BundleSummary): number => {
  if (bundle.combined_price <= 0) return 0;
  const savings = bundle.combined_price - bundle.bundle_price;
  if (savings <= 0) return 0;
  return Math.round((savings / bundle.combined_price) * 100);
};

export default function BundlesPage() {
  const [bundles, setBundles] = useState<BundleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    fetchBundles()
      .then(setBundles)
      .catch(() => setError("Could not load bundles"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <PageLayout
        header={
          <PageBanner
            eyebrow="Curated course bundles"
            title="More learning, brought together"
            description="Choose a thoughtfully grouped set of courses, pay once and keep every included course in your learning library."
            share
            shareTitle="Explore course bundles on SashaInfinity"
          />
        }
        className="rd-screen rd-screen-bundles"
      >
        {error && (
          <div className="mb-6 max-w-xl mx-auto bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3 text-center">
            {error}
          </div>
        )}
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
          </div>
        ) : bundles.length === 0 ? (
          <div className="text-center text-gray-500 py-16">
            No bundles are available right now.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {bundles.map((bundle) => {
              const pct = savingsPercent(bundle);
              return (
                <Link
                  key={bundle.id}
                  to={`/bundles/${bundle.slug}`}
                  className="block h-full"
                >
                  <Card className="p-6 flex flex-col h-full hover:shadow-medium hover:-translate-y-1 transition-all duration-300">
                    <div className="flex items-center gap-2 mb-2">
                      <Layers className="h-5 w-5 text-orange-500" />
                      <h2 className="text-lg font-semibold text-gray-900">
                        {bundle.name}
                      </h2>
                    </div>
                    <p className="text-sm text-gray-600 mb-4 flex-1 line-clamp-3">
                      {bundle.description}
                    </p>

                    <div className="flex items-center gap-2 text-sm text-gray-700 mb-4">
                      <BookOpen className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      {bundle.courses.length} course
                      {bundle.courses.length !== 1 ? "s" : ""} included
                    </div>

                    <div className="mb-2 flex items-baseline gap-2 flex-wrap">
                      <span className="text-2xl font-bold text-gray-900">
                        ₹{bundle.bundle_price}
                      </span>
                      {bundle.combined_price > bundle.bundle_price && (
                        <span className="text-sm text-gray-500 line-through">
                          ₹{bundle.combined_price}
                        </span>
                      )}
                      {pct > 0 && (
                        <span className="text-xs font-semibold text-emerald-700 bg-emerald-100 rounded-full px-2 py-0.5">
                          Save {pct}%
                        </span>
                      )}
                    </div>

                    <span className="mt-2 text-sm font-medium text-orange-600">
                      View bundle →
                    </span>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </PageLayout>
    </div>
  );
}
