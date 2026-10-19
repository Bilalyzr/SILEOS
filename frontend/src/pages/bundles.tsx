import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, BookOpen, Layers, Loader2 } from "lucide-react";
import { fetchBundles, BundleSummary } from "@/api/bundle";
import {
  SymphoButton,
  SymphoCtaBanner,
  SymphoPageHero,
  SymphoSectionHeader,
} from "@/components/sympho/SymphoSystem";

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

  const totalCoursesAcrossBundles = bundles.reduce(
    (acc, b) => acc + (b.courses?.length || 0),
    0,
  );

  return (
    <div className="sympho-scope rd-screen rd-screen-bundles min-h-screen bg-limestone-100 text-ink-900">
      <SymphoPageHero
        index="SI—BND.01"
        category="CURATED TRACK PACKAGES"
        code="COMPOSITE CURRICULA"
        title="More learning, architected together."
        subtitle="Choose a thoughtfully sequenced set of courses, enroll once, and keep every included studio track permanently in your learning library."
        metrics={[
          {
            value: String(bundles.length),
            unit: "packages",
            label: "Active Course Bundles",
            code: "BND—01",
          },
          {
            value: String(totalCoursesAcrossBundles),
            unit: "modules",
            label: "Combined Tracks",
            code: "BND—02",
          },
          {
            value: "LIFETIME",
            unit: "access",
            label: "Library Retention",
            code: "BND—03",
          },
        ]}
        actions={
          <>
            <SymphoButton to="/membership" variant="copper">
              Compare with All-Access Membership
            </SymphoButton>
            <SymphoButton to="/courses" variant="ghost-dark">
              Browse Individual Courses
            </SymphoButton>
          </>
        }
      />

      <section className="py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            index="BND—01"
            category="BUNDLE SPECIFICATIONS"
            code={`${bundles.length} AVAILABLE`}
            title="Curated Course Bundles"
            subtitle="Multi-course architectural blueprints designed to take you from foundational principles to full production mastery."
          />

          {error && (
            <div
              role="alert"
              className="mt-8 sheet-frame border-red-500/40 bg-red-500/10 p-4 text-center font-mono text-xs uppercase tracking-[0.14em] text-red-700"
            >
              {error}
            </div>
          )}

          <div className="mt-12">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-copper-500" />
                <span className="mt-3 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-500">
                  Loading bundle specifications...
                </span>
              </div>
            ) : bundles.length === 0 ? (
              <div className="sheet-frame mx-auto max-w-2xl bg-limestone-50 p-12 text-center">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full border border-ink-900/15 bg-limestone-100 text-copper-500">
                  <Layers className="h-6 w-6" />
                </div>
                <span className="mt-4 block font-mono text-[10px] uppercase tracking-[0.18em] text-copper-500">
                  CATALOG LEDGER // BUNDLES
                </span>
                <p className="mt-2 font-display text-2xl font-light text-ink-900">
                  No bundles are available right now.
                </p>
                <p className="mx-auto mt-2 max-w-md text-sm text-ink-600">
                  Explore our individual courses or unlock the entire catalog with a SashaInfinity Membership plan.
                </p>
                <div className="mt-8 flex flex-wrap justify-center gap-3">
                  <SymphoButton to="/courses" variant="primary">
                    Explore Courses
                  </SymphoButton>
                  <SymphoButton to="/membership" variant="outline">
                    View Membership Plans
                  </SymphoButton>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {bundles.map((bundle, idx) => {
                  const pct = savingsPercent(bundle);
                  return (
                    <Link
                      key={bundle.id}
                      to={`/bundles/${bundle.slug}`}
                      className="group sheet-frame flex h-full flex-col justify-between bg-limestone-50 p-7 transition-all duration-300 hover:-translate-y-1 hover:border-copper-500/50 hover:shadow-lift"
                    >
                      <div>
                        <div className="flex items-center justify-between border-b border-ink-900/10 pb-4">
                          <span className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em] text-copper-500">
                            <Layers className="h-3.5 w-3.5" />
                            PKG—{String(idx + 1).padStart(2, "0")}
                          </span>
                          {pct > 0 && (
                            <span className="rounded-pill border border-sage-500/30 bg-sage-500/10 px-3 py-0.5 font-mono text-[10px] font-medium uppercase tracking-[0.14em] text-sage-700">
                              Save {pct}%
                            </span>
                          )}
                        </div>

                        <h2 className="mt-5 font-display text-2xl font-light leading-snug text-ink-900 transition-colors group-hover:text-copper-500">
                          {bundle.name}
                        </h2>

                        <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-ink-600">
                          {bundle.description}
                        </p>

                        <div className="mt-6 flex items-center gap-2 rounded-lg border border-ink-900/10 bg-limestone-100/80 px-3.5 py-2.5 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-700">
                          <BookOpen className="h-3.5 w-3.5 text-copper-500 flex-shrink-0" />
                          <span>
                            {bundle.courses.length} course
                            {bundle.courses.length !== 1 ? "s" : ""} included
                          </span>
                        </div>
                      </div>

                      <div className="mt-8 border-t border-ink-900/10 pt-5">
                        <div className="flex items-end justify-between">
                          <div>
                            <span className="block font-mono text-[10px] uppercase tracking-[0.14em] text-ink-500">
                              Bundle Tuition
                            </span>
                            <div className="mt-1 flex items-baseline gap-2.5">
                              <span className="font-display text-3xl font-light text-ink-900">
                                ₹{bundle.bundle_price}
                              </span>
                              {bundle.combined_price > bundle.bundle_price && (
                                <span className="font-mono text-xs text-ink-400 line-through">
                                  ₹{bundle.combined_price}
                                </span>
                              )}
                            </div>
                          </div>

                          <span className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-copper-500 transition-transform group-hover:translate-x-0.5">
                            View bundle
                            <ArrowUpRight className="h-4 w-4" />
                          </span>
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </section>

      <SymphoCtaBanner
        code="SI—BND // 02"
        eyebrow="CONTINUOUS SCHOLARSHIP"
        title="Want unlimited access to every course?"
        description="Compare curated bundles with our recurring All-Access Membership to unlock the entire SashaInfinity curriculum under one subscription."
        primaryLabel="Explore Membership Plans"
        primaryTo="/membership"
        secondaryLabel="Browse Individual Courses"
        secondaryTo="/courses"
      />
    </div>
  );
}
