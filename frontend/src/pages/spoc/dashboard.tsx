import { PageLayout } from "@/components/design-system/PageLayout";
/**
 * SPOC dashboard — v3 redesign matching the public hero brand.
 *
 * Layout:
 *   - Greeting + chip
 *   - 4 stat cards (sparklines): My internships / Published / Vouchers issued / Vouchers redeemed
 *   - Voucher redemption funnel chart + Internships donut by status
 *   - Internships card grid with hover lift + "Open roster" CTA
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Briefcase,
  IndianRupee,
  Ticket,
  Users,
  CheckCircle,
  Activity,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import toast from "react-hot-toast";
import { internshipApi, AdminInternshipRow } from "@/api/internship";
import { useAuth } from "@/hooks/use-auth";
import {
  StatCard,
  SkeletonStatCard,
  SkeletonChart,
  EmptyState,
  ErrorState,
  SectionCard,
  Greeting,
  StaggerGrid,
  FadeUp,
} from "@/components/dashboard/primitives";
import {
  BarChartCard,
  DonutCard,
  ChartLegend,
  CHART_COLORS,
} from "@/components/dashboard/charts";
import { ViewAsSpocBanner } from "@/components/spoc/ViewAsSpocBanner";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";

export const SpocDashboard: React.FC = () => {
  const { fullName } = useAuth();
  const [rawItems, setItems] = useState<AdminInternshipRow[]>([]);
  const items = rawItems;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setItems(await internshipApi.spocMyInternships());
    } catch (e: any) {
      const msg = e?.response?.data?.detail || "Failed to load internships";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const totalIssued = items.reduce((s, i) => s + (i.vouchers_issued ?? 0), 0);
  const totalRedeemed = items.reduce(
    (s, i) => s + (i.vouchers_redeemed ?? 0),
    0,
  );
  const published = items.filter((i) => i.is_published).length;
  const drafts = items.length - published;

  // No sparklines on the stat cards — they were genTrend() random walks seeded
  // off the current totals, so they invented a 14-day history the voucher data
  // does not have. The per-internship chart below is real.

  // Per-internship voucher chart: top 6 internships by issued, side-by-side issued/redeemed
  const voucherRows = useMemo(() => {
    return items
      .slice()
      .sort((a, b) => (b.vouchers_issued ?? 0) - (a.vouchers_issued ?? 0))
      .slice(0, 6)
      .map((i) => ({
        x: i.title.length > 18 ? i.title.slice(0, 18) + "…" : i.title,
        issued: i.vouchers_issued ?? 0,
        redeemed: i.vouchers_redeemed ?? 0,
      }));
  }, [items]);

  const statusSlices = [
    { name: "Published", value: published, color: CHART_COLORS.emerald },
    { name: "Draft", value: drafts, color: CHART_COLORS.amber },
  ];

  return (
    <PageLayout
      header={
        <Greeting
          name={fullName}
          chip="SPOC WORKSPACE"
          subtitle="Here's what's happening across your internship cohorts."
          className="mb-6"
        />
      }
    >
      <ViewAsSpocBanner />
      {error && (
        <FadeUp>
          <ErrorState
            title="Couldn't load your internships"
            description={error}
            onRetry={load}
            className="dash-card mb-6"
          />
        </FadeUp>
      )}
      <StaggerGrid className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {loading ? (
          <>
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
          </>
        ) : (
          <>
            <StatCard
              title="My internships"
              value={items.length}
              icon={Briefcase}
              tone="orange"
            />
            <StatCard
              title="Published"
              value={published}
              icon={CheckCircle}
              tone="emerald"
            />
            <StatCard
              title="Vouchers issued"
              value={totalIssued}
              icon={Ticket}
              tone="amber"
            />
            <StatCard
              title="Vouchers redeemed"
              value={totalRedeemed}
              icon={Users}
              tone="purple"
              delta={
                totalIssued > 0
                  ? `${Math.round((totalRedeemed / totalIssued) * 100)}% redemption`
                  : undefined
              }
              deltaDirection="up"
            />
          </>
        )}
      </StaggerGrid>
      <StaggerGrid className="grid grid-cols-1">
        <SectionCard
          title="My internships"
          description="Click into one to see roster, attendance, and certificates."
          icon={Briefcase}
        >
          {loading ? (
            <div className="grid md:grid-cols-2 gap-4">
              <div className="h-32 dash-skeleton" />
              <div className="h-32 dash-skeleton" />
              <div className="h-32 dash-skeleton" />
              <div className="h-32 dash-skeleton" />
            </div>
          ) : items.length === 0 ? (
            <EmptyState
              icon={Briefcase}
              title="No internships assigned yet"
              description="An admin will assign you to internship cohorts. They'll appear here as soon as they do."
            />
          ) : (
            <div className="grid md:grid-cols-2 gap-4">
              {items.map((i) => {
                const redemption = i.vouchers_issued
                  ? Math.round(
                      ((i.vouchers_redeemed ?? 0) / i.vouchers_issued) * 100,
                    )
                  : 0;
                return (
                  <Link
                    key={i.id}
                    to={`/spoc/internship/${i.id}`}
                    className="group rounded-xl border border-slate-200 p-5 bg-white hover:shadow-lg hover:-translate-y-0.5 hover:border-orange-200 transition block"
                  >
                    <div className="flex items-start justify-between mb-2 gap-3">
                      <h3 className="font-semibold text-secondary-900 line-clamp-2 group-hover:text-orange-600 transition">
                        {i.title}
                      </h3>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider flex-shrink-0 ${
                          i.is_published
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {i.is_published ? "Published" : "Draft"}
                      </span>
                    </div>
                    {i.description && (
                      <p className="text-sm text-slate-600 line-clamp-2 mb-3">
                        {i.description}
                      </p>
                    )}
                    <div className="flex items-center gap-4 text-sm text-slate-700">
                      <span className="flex items-center gap-1 font-medium">
                        <IndianRupee className="h-4 w-4 text-slate-400" />
                        {(i.price || 0).toLocaleString("en-IN")}
                      </span>
                      <span className="flex items-center gap-1">
                        <Ticket className="h-4 w-4 text-slate-400" />
                        <b className="tabular-nums">
                          {i.vouchers_redeemed ?? 0}/{i.vouchers_issued ?? 0}
                        </b>
                        <span className="text-xs text-slate-500">redeemed</span>
                      </span>
                    </div>
                    {(i.vouchers_issued ?? 0) > 0 && (
                      <div className="mt-3">
                        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-orange-400 to-orange-600 transition-all"
                            style={{ width: `${redemption}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-[10px] text-slate-500 mt-1">
                          <span>Redemption</span>
                          <span className="font-semibold text-orange-600">
                            {redemption}%
                          </span>
                        </div>
                      </div>
                    )}
                    <div className="mt-3 text-orange-600 group-hover:text-orange-700 text-sm font-semibold flex items-center gap-1">
                      Open roster{" "}
                      <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition" />
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </SectionCard>
      </StaggerGrid>
      <StaggerGrid className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <SectionCard
          title="Voucher activity"
          description="Issued vs redeemed for top internships"
          icon={Activity}
          className="lg:col-span-2"
          bodyClassName="px-2 pb-3"
        >
          {loading ? (
            <SkeletonChart />
          ) : voucherRows.length === 0 ? (
            <EmptyState
              icon={Ticket}
              title="No vouchers yet"
              description="Vouchers appear once students start purchasing internships."
            />
          ) : (
            <BarChartCard
              data={voucherRows}
              series={[
                { key: "issued", label: "Issued", color: CHART_COLORS.orange },
                { key: "redeemed", label: "Redeemed", color: CHART_COLORS.sky },
              ]}
              xKey="x"
              height={260}
            />
          )}
        </SectionCard>

        <SectionCard title="Internships by status" icon={Sparkles}>
          {loading ? (
            <SkeletonChart />
          ) : items.length === 0 ? (
            <EmptyState
              icon={Briefcase}
              title="None yet"
              description="Admin will assign you to cohorts."
            />
          ) : (
            <>
              <DonutCard
                data={statusSlices}
                centerLabel="Programs"
                height={200}
              />
              <ChartLegend items={statusSlices} className="mt-4" />
            </>
          )}
        </SectionCard>
      </StaggerGrid>
      <div className="mt-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Export College Data
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-lg border" data-glass="content">
            <ExportImportPanel section="spoc_students" role="spoc" />
          </div>
          <div className="bg-white p-4 rounded-lg border" data-glass="content">
            <ExportImportPanel section="spoc_internships" role="spoc" />
          </div>
          <div className="bg-white p-4 rounded-lg border" data-glass="content">
            <ExportImportPanel section="spoc_placements" role="spoc" />
          </div>
        </div>
      </div>
    </PageLayout>
  );
};

export default SpocDashboard;
