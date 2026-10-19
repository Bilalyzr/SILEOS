import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { ArrowUpRight, Briefcase, Search, User } from "lucide-react";
import { internshipApi, PublicInternship } from "@/api/internship";
import {
  SymphoButton,
  SymphoCtaBanner,
  SymphoPageHero,
  SymphoSectionHeader,
} from "@/components/sympho/SymphoSystem";

export const InternshipsPage: React.FC = () => {
  const [items, setItems] = useState<PublicInternship[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const data = await internshipApi.list();
        setItems(data || []);
      } catch (err: any) {
        toast.error(
          err?.response?.data?.detail || "Failed to load internships",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filtered = items.filter(
    (i) =>
      i.title.toLowerCase().includes(search.toLowerCase()) ||
      (i.spoc_name || "").toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="sympho-scope rd-screen rd-screen-internships min-h-screen bg-limestone-100 text-ink-900">
      <SymphoPageHero
        index="SI—INT.01"
        category="MENTOR-LED INDUSTRY COHORTS"
        code="APPRENTICESHIP LEDGER"
        title="Turn learning into production experience."
        subtitle="Explore structured internship programs led by industry mentors, log real engineering deliverables, and earn verifiable credentials plus course vouchers."
        metrics={[
          {
            value: String(items.length),
            unit: "cohorts",
            label: "Active Internship Tracks",
            code: "INT—01",
          },
          {
            value: "1:1",
            unit: "mentorship",
            label: "SPOC Guided Reviews",
            code: "INT—02",
          },
          {
            value: "100%",
            unit: "verified",
            label: "Work-Log Portfolio",
            code: "INT—03",
          },
        ]}
        actions={
          <>
            <SymphoButton href="#internship-directory" variant="copper">
              Browse Open Cohorts
            </SymphoButton>
            <SymphoButton to="/for-companies" variant="ghost-dark">
              Partner as a Hiring Company
            </SymphoButton>
          </>
        }
      />

      <section id="internship-directory" className="py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
            <div className="flex-1">
              <SymphoSectionHeader
                index="INT—01"
                category="COHORT DIRECTORY"
                code={`${filtered.length} PROGRAMS`}
                title="Available Internship Programs"
                subtitle="Filter by technical track or assigned SPOC mentor to find your next industry placement."
              />
            </div>

            {/* Search Filter */}
            <div className="sheet-frame flex w-full max-w-md items-center gap-3 bg-limestone-50 px-4 py-3">
              <Search className="h-4 w-4 flex-shrink-0 text-copper-500" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by program or mentor..."
                className="w-full bg-transparent font-mono text-xs text-ink-900 placeholder:text-ink-400 focus:outline-none"
              />
            </div>
          </div>

          <div className="mt-12">
            {loading ? (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {[1, 2, 3].map((n) => (
                  <div
                    key={n}
                    className="sheet-frame h-80 animate-pulse bg-limestone-50 p-6"
                  />
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <div className="sheet-frame mx-auto max-w-2xl bg-limestone-50 p-12 text-center">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full border border-ink-900/15 bg-limestone-100 text-copper-500">
                  <Briefcase className="h-6 w-6" />
                </div>
                <span className="mt-4 block font-mono text-[10px] uppercase tracking-[0.18em] text-copper-500">
                  COHORT LEDGER // PLACEMENTS
                </span>
                <p className="mt-2 font-display text-2xl font-light text-ink-900">
                  No internship programs available right now. Check back soon.
                </p>
                <p className="mx-auto mt-2 max-w-md text-sm text-ink-600">
                  Build your technical portfolio with our studio courses and 3D learning labs while new company cohorts are scheduled.
                </p>
                <div className="mt-8 flex flex-wrap justify-center gap-3">
                  <SymphoButton to="/courses" variant="primary">
                    Explore Courses
                  </SymphoButton>
                  <SymphoButton to="/hall-of-fame" variant="outline">
                    View Mentor Wall of Fame
                  </SymphoButton>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {filtered.map((i, idx) => (
                  <Link
                    key={i.id}
                    to={`/internships/${i.slug}`}
                    className="group sheet-frame flex flex-col overflow-hidden bg-limestone-50 transition-all duration-300 hover:-translate-y-1 hover:border-copper-500/50 hover:shadow-lift"
                  >
                    <div className="relative h-48 w-full overflow-hidden border-b border-ink-900/10 bg-ink-950">
                      {i.cover_image ? (
                        <img
                          src={i.cover_image}
                          alt={i.title}
                          className="h-full w-full object-cover opacity-90 transition-transform duration-500 group-hover:scale-105"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center bg-ink-950 blueprint-grid">
                          <Briefcase className="h-10 w-10 text-copper-400" />
                        </div>
                      )}
                      <span className="absolute left-4 top-4 rounded-pill bg-ink-950/85 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-limestone-100 backdrop-blur-sm">
                        INT—{String(idx + 1).padStart(2, "0")}
                      </span>
                    </div>

                    <div className="flex flex-1 flex-col justify-between p-6">
                      <div>
                        <h3 className="line-clamp-2 font-display text-2xl font-light text-ink-900 transition-colors group-hover:text-copper-500">
                          {i.title}
                        </h3>
                        {i.spoc_name && (
                          <div className="mt-2 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-500">
                            <User className="h-3.5 w-3.5 text-copper-500" />
                            <span>Mentor: {i.spoc_name}</span>
                          </div>
                        )}
                        {i.description && (
                          <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-ink-600">
                            {i.description}
                          </p>
                        )}
                      </div>

                      <div className="mt-6 flex items-center justify-between border-t border-ink-900/10 pt-4">
                        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-500">
                          Verified Placement Track
                        </span>
                        <span className="inline-flex items-center gap-1.5 rounded-pill bg-ink-900 px-4 py-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-limestone-100 transition-colors group-hover:bg-copper-500">
                          Enroll Now
                          <ArrowUpRight className="h-3.5 w-3.5" />
                        </span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      <SymphoCtaBanner
        code="SI—INT // 02"
        eyebrow="CORPORATE TALENT PIPELINE"
        title="Hiring pre-vetted interns or graduates?"
        description="Connect your engineering or operations team directly with course-certified SashaInfinity candidates."
        primaryLabel="Explore For Companies"
        primaryTo="/for-companies"
        secondaryLabel="Meet Our Mentors"
        secondaryTo="/hall-of-fame"
      />
    </div>
  );
};

export default InternshipsPage;
