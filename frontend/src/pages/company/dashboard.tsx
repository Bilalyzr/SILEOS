import { PageHeading } from "@/components/design-system/PageLayout";
/**
 * Company dashboard — wired to the v2 backend at /api/v1/companies/me/*.
 *
 * Tabs (Overview / Students / Internships / Attendance / Announcements /
 * Reports / Managers) each call typed React Query hooks from
 * `@/api/company-dashboard`. Empty/loading/error states use the shared
 * dashboard primitives. No mock data.
 */
import React, { useMemo, useState } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Users,
  Briefcase,
  CalendarCheck,
  LayoutDashboard,
  Megaphone,
  FileBarChart,
  UserCog,
  Download,
  FileText,
  CheckCircle2,
  XCircle,
  Clock3,
  AlertCircle,
  Star,
  Search,
  X,
  Plus,
  Mail,
  Linkedin,
  Github,
  Globe,
  LogOut,
  Home,
  Receipt,
  CreditCard,
  Users2,
  Loader2,
} from "lucide-react";
import toast from "react-hot-toast";
import { useAuthStore } from "@/store/auth";
import { EmptyState, ErrorState } from "@/components/dashboard/primitives";
import { ShareButton } from "@/components/ui/share-button";
import { ImpersonationBanner } from "@/components/admin/ImpersonationBanner";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";
import { CompanyInternshipCharts } from "@/components/company/CompanyInternshipCharts";
import {
  fetchBillingProfile,
  updateBillingProfile,
  fetchInvoices,
  downloadInvoicePdf,
  createInvoiceOrder,
  verifyInvoicePayment,
  fetchSeatPools,
  assignSeat,
  fetchSeatAssignments,
  type BillingProfile,
  type Invoice,
  type SeatPool,
  type SeatAssignment,
} from "@/api/companyBilling";
import {
  useCompany,
  useOverview,
  useStudents,
  useUpdateStudent,
  useInternships,
  useAttendance,
  useUpsertAttendance,
  useWorkLogs,
  useReviewWorkLog,
  useAnnouncements,
  useCreateAnnouncement,
  useDeleteAnnouncement,
  useManagers,
  useInviteManager,
  useRevokeManager,
  useCreateReview,
  useAttendanceReport,
  downloadAttendanceReport,
  useInternshipRequests,
  useCreateInternshipRequest,
  useDeleteInternshipRequest,
  type Student as ApiStudent,
  type AttendanceEntry,
  type WorkLogItem,
  type AnnouncementItem,
  type ManagerItem,
  type CompanyInternship,
  type InternshipRequestItem,
} from "@/api/company-dashboard";
import "@/components/dashboard/theme.css";

// ============================================================================
// Tab definitions
// ============================================================================

type Tab =
  | "overview"
  | "students"
  | "internships"
  | "attendance"
  | "announcements"
  | "managers"
  | "reports"
  | "billing";

const NAV: { key: Tab; label: string; icon: any }[] = [
  { key: "overview", label: "Overview", icon: LayoutDashboard },
  { key: "students", label: "Students", icon: Users },
  { key: "internships", label: "Internships", icon: Briefcase },
  { key: "attendance", label: "Attendance", icon: CalendarCheck },
  { key: "announcements", label: "Announcements", icon: Megaphone },
  { key: "reports", label: "Reports", icon: FileBarChart },
  { key: "billing", label: "Billing", icon: Receipt },
  { key: "managers", label: "Managers", icon: UserCog },
];

// ============================================================================
// Page shell
// ============================================================================

export function CompanyDashboardPage() {
  const [tab, setTab] = useState<Tab>("overview");
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);
  const { data: company } = useCompany();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const companyName = company?.name || "Loading…";
  const companyIndustry = company?.industry || "";
  const companyApproved = company?.is_approved ?? false;

  return (
    <div className="dash-bg rd-company relative min-h-screen">
      {/* Admin impersonation banner */}
      <ImpersonationBanner />

      <div className="dash-bg-shape dash-bg-shape-1" aria-hidden />
      <div className="dash-bg-shape dash-bg-shape-2" aria-hidden />

      <header className="bg-white/80 backdrop-blur border-b border-slate-200/70 relative z-10 sticky top-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center gap-4">
          <Link to="/" className="flex items-center gap-2 flex-shrink-0 group">
            <img
              src="https://res.cloudinary.com/dkjvfskhn/image/upload/v1759753621/cropped-sasha-logo-small_ejpceq.png"
              alt="SashaInfinity"
              className="h-9 w-auto group-hover:scale-105 transition-transform"
            />
            <span className="hidden md:inline-block text-base font-bold text-secondary-900 tracking-tight">
              Sasha<span className="text-orange-500">Infinity</span>
            </span>
          </Link>

          <span className="hidden md:inline-block w-px h-6 bg-slate-200 flex-shrink-0" />

          <div className="flex items-center gap-3 min-w-0 flex-1">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-orange-500 to-orange-600 text-white font-bold text-sm flex items-center justify-center flex-shrink-0">
              {companyName.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <div className="font-bold text-secondary-900 truncate text-sm">
                {companyName}
              </div>
              <div className="text-xs text-slate-500 truncate flex items-center gap-2">
                {companyApproved ? (
                  <span className="inline-flex items-center text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0 rounded-full text-[9px] font-bold uppercase tracking-wider">
                    Approved
                  </span>
                ) : company ? (
                  <span className="inline-flex items-center text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0 rounded-full text-[9px] font-bold uppercase tracking-wider">
                    Pending
                  </span>
                ) : null}
                {companyIndustry && (
                  <span className="hidden sm:inline">{companyIndustry}</span>
                )}
                {user?.email && (
                  <span className="hidden lg:inline text-slate-400">
                    · {user.email}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <ShareButton
              url={
                typeof window !== "undefined" ? window.location.href : undefined
              }
              title={`Company: ${companyName}`}
              description={`${companyIndustry ? companyIndustry + " - " : ""}${companyApproved ? "Approved" : "Pending"} company at SashaInfinity`}
              showLabel={false}
              variant="ghost"
            />
            <Link
              to="/"
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-secondary-800 hover:bg-slate-100 transition"
              title="Public site"
            >
              <Home className="w-4 h-4" />
            </Link>
            <button onClick={handleLogout} className="dash-cta-ghost text-xs">
              <LogOut className="w-3.5 h-3.5" /> Log out
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 grid grid-cols-12 gap-6 py-6 relative z-10">
        <aside className="col-span-12 md:col-span-3 lg:col-span-2">
          <motion.nav
            initial="hidden"
            animate="show"
            variants={{
              hidden: {},
              show: {
                transition: { staggerChildren: 0.04, delayChildren: 0.05 },
              },
            }}
            className="space-y-0.5 sticky top-6 dash-card p-2"
          >
            {NAV.map((n) => {
              const Icon = n.icon;
              const active = tab === n.key;
              return (
                <motion.button
                  key={n.key}
                  variants={{
                    hidden: { opacity: 0, x: -12 },
                    show: {
                      opacity: 1,
                      x: 0,
                      transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] },
                    },
                  }}
                  onClick={() => setTab(n.key)}
                  className={`relative w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-left transition group ${
                    active
                      ? "text-orange-700 font-semibold"
                      : "text-secondary-800 hover:text-orange-700 hover:bg-orange-50/50"
                  }`}
                >
                  {active && (
                    <motion.span
                      layoutId="company-tab-active-pill"
                      className="absolute inset-0 rounded-lg bg-orange-100/70 ring-1 ring-orange-200"
                      transition={{
                        type: "spring",
                        stiffness: 380,
                        damping: 30,
                      }}
                    />
                  )}
                  <Icon
                    className={`w-4 h-4 flex-shrink-0 relative z-10 ${active ? "text-orange-600" : "text-slate-500 group-hover:text-orange-600 transition"}`}
                  />
                  <span className="relative z-10 flex-1 truncate">
                    {n.label}
                  </span>
                </motion.button>
              );
            })}
          </motion.nav>
        </aside>

        <main className="col-span-12 md:col-span-9 lg:col-span-10">
          <PageHeading
            eyebrow="Company workspace"
            title={NAV.find((n) => n.key === tab)?.label || companyName}
            description={companyName}
          />
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            >
              {tab === "overview" && <OverviewTab onGoTo={setTab} />}
              {tab === "students" && <StudentsTab />}
              {tab === "internships" && (
                <InternshipsTab companyName={companyName} />
              )}
              {tab === "attendance" && <AttendanceTab />}
              {tab === "announcements" && <AnnouncementsTab />}
              {tab === "reports" && <ReportsTab />}
              {tab === "billing" && <BillingTab />}
              {tab === "managers" && <ManagersTab />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

// ============================================================================
// Shared little components
// ============================================================================

function StatCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone?: "default" | "emerald" | "amber" | "red";
}) {
  const toneCls =
    tone === "emerald"
      ? "text-emerald-600"
      : tone === "amber"
        ? "text-amber-600"
        : tone === "red"
          ? "text-rose-600"
          : "text-slate-900";
  return (
    <div className="dash-card p-5">
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`text-3xl font-bold mt-1 ${toneCls}`}>{value}</div>
      {hint && <div className="text-xs text-slate-500 mt-1">{hint}</div>}
    </div>
  );
}

function ProgressBar({ pct }: { pct: number }) {
  const safe = Math.max(0, Math.min(100, pct || 0));
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${safe >= 80 ? "bg-emerald-500" : safe >= 50 ? "bg-amber-500" : "bg-rose-500"}`}
          style={{ width: `${safe}%` }}
        />
      </div>
      <span className="text-xs text-slate-600">{Math.round(safe)}%</span>
    </div>
  );
}

function CertBadge({ status }: { status: string }) {
  if (status === "issued") {
    return (
      <span className="inline-block text-xs font-semibold px-2 py-0.5 rounded bg-indigo-100 text-indigo-700">
        Issued
      </span>
    );
  }
  if (status === "eligible") {
    return (
      <span className="inline-block text-xs font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">
        Eligible
      </span>
    );
  }
  return (
    <span className="inline-block text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
      —
    </span>
  );
}

function ReviewBadge({ status }: { status: string }) {
  const m: Record<string, { cls: string; icon: any; label: string }> = {
    pending: {
      cls: "bg-amber-100 text-amber-700",
      icon: Clock3,
      label: "Pending",
    },
    approved: {
      cls: "bg-emerald-100 text-emerald-700",
      icon: CheckCircle2,
      label: "Approved",
    },
    flagged: {
      cls: "bg-rose-100 text-rose-700",
      icon: AlertCircle,
      label: "Flagged",
    },
    rejected: {
      cls: "bg-rose-100 text-rose-700",
      icon: XCircle,
      label: "Rejected",
    },
  };
  const x = m[status] || m.pending;
  const I = x.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded ${x.cls}`}
    >
      <I className="w-3 h-3" />
      {x.label}
    </span>
  );
}

function LoadingBlock({
  children = "Loading…",
}: {
  children?: React.ReactNode;
}) {
  return (
    <div className="dash-card p-10 text-center text-sm text-slate-500">
      {children}
    </div>
  );
}

// ============================================================================
// Overview
// ============================================================================

function OverviewTab({ onGoTo }: { onGoTo: (t: Tab) => void }) {
  const { data: o, isLoading, isError, refetch } = useOverview();

  if (isLoading) return <LoadingBlock>Loading overview…</LoadingBlock>;
  if (isError || !o) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Active interns" value={o.active_interns} />
        <StatCard label="Active internships" value={o.active_internships} />
        <StatCard
          label="Week attendance"
          value={`${Math.round(o.week_attendance_pct)}%`}
          tone="emerald"
        />
        <StatCard
          label="Pending work-log reviews"
          value={o.pending_work_log_reviews}
          tone="amber"
          hint="Click 'Attendance' to review"
        />
      </div>

      <section className="dash-card p-5">
        <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <CalendarCheck className="w-4 h-4 text-orange-600" />
          Today&apos;s attendance snapshot
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatCard label="Present" value={o.today_present} tone="emerald" />
          <StatCard label="Absent" value={o.today_absent} tone="red" />
          <StatCard label="Late" value={o.today_late} tone="amber" />
          <StatCard label="Excused" value={o.today_excused} />
          <StatCard label="Not marked" value={o.today_not_marked} />
        </div>
        <button
          onClick={() => onGoTo("attendance")}
          className="mt-4 text-sm text-orange-700 hover:text-orange-900 font-semibold"
        >
          Mark today&apos;s attendance now →
        </button>
      </section>

      <section className="dash-card p-5">
        <h2 className="font-semibold text-slate-900 mb-4">Recent activity</h2>
        {o.activity && o.activity.length > 0 ? (
          <ul className="divide-y divide-slate-100">
            {o.activity.map((a: any, i: number) => (
              <li key={i} className="py-3 flex items-start gap-3 text-sm">
                <span className="text-slate-400 text-xs w-32 flex-shrink-0 mt-0.5">
                  {a.timestamp
                    ? new Date(a.timestamp).toLocaleString()
                    : a.t || ""}
                </span>
                <span className="text-slate-700">
                  {a.text || a.message || JSON.stringify(a)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            icon={LayoutDashboard}
            title="No recent activity yet"
            description="Once your team marks attendance or interns submit work logs, you'll see updates here."
          />
        )}
      </section>

      {/* Export Section */}
      <div className="mt-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Export Company Data
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-lg border" data-glass="content">
            <ExportImportPanel section="company_positions" role="company" />
          </div>
          <div className="bg-white p-4 rounded-lg border" data-glass="content">
            <ExportImportPanel section="company_interns" role="company" />
          </div>
          <div className="bg-white p-4 rounded-lg border" data-glass="content">
            <ExportImportPanel section="company_performance" role="company" />
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Students
// ============================================================================

function StudentsTab() {
  const [search, setSearch] = useState("");
  const [internshipFilter, setInternshipFilter] = useState<number | "all">(
    "all",
  );
  const [selected, setSelected] = useState<ApiStudent | null>(null);

  const { data: internshipsData } = useInternships();
  const {
    data: studentsData,
    isLoading,
    isError,
    refetch,
  } = useStudents({
    internship_id: internshipFilter === "all" ? undefined : internshipFilter,
    search: search || undefined,
  });

  const rows = studentsData?.items || [];

  return (
    <div className="space-y-4">
      <div className="dash-card p-4 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs text-slate-500 mb-1">Search</label>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-md border border-slate-300 pl-8 pr-3 py-2 text-sm"
              placeholder="Name or email…"
            />
          </div>
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            Internship
          </label>
          <select
            value={internshipFilter}
            onChange={(e) =>
              setInternshipFilter(
                e.target.value === "all" ? "all" : Number(e.target.value),
              )
            }
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="all">All</option>
            {(internshipsData?.items || []).map((i) => (
              <option key={i.id} value={i.id}>
                {i.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading ? (
        <LoadingBlock>Loading students…</LoadingBlock>
      ) : isError ? (
        <ErrorState onRetry={() => refetch()} />
      ) : rows.length === 0 ? (
        <div className="dash-card">
          <EmptyState
            icon={Users}
            title="No students yet"
            description="Once admin publishes an internship for your company and students enroll, they'll show up here."
          />
        </div>
      ) : (
        <div className="dash-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Internship</th>
                <th className="text-left px-4 py-3">Progress</th>
                <th className="text-left px-4 py-3">Attendance</th>
                <th className="text-left px-4 py-3">Reporting to</th>
                <th className="text-left px-4 py-3">Certificate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((s) => (
                <tr
                  key={s.user_id}
                  onClick={() => setSelected(s)}
                  className="hover:bg-slate-50 cursor-pointer"
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{s.name}</div>
                    <div className="text-xs text-slate-500">{s.email}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-700 text-xs">
                    {s.internship_title}
                  </td>
                  <td className="px-4 py-3">
                    <ProgressBar pct={s.progress_pct} />
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        s.attendance_pct >= 90
                          ? "text-emerald-600 font-semibold"
                          : s.attendance_pct >= 80
                            ? "text-amber-600 font-semibold"
                            : "text-rose-600 font-semibold"
                      }
                    >
                      {Math.round(s.attendance_pct)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-700 text-xs">
                    {s.reporting_manager_name ?? (
                      <span className="text-slate-400 italic">unassigned</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <CertBadge status={s.cert_status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <StudentDrawer student={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function StudentDrawer({
  student,
  onClose,
}: {
  student: ApiStudent;
  onClose: () => void;
}) {
  const [managerId, setManagerId] = useState<number | "">(
    student.reporting_manager_user_id ?? "",
  );
  const [notes, setNotes] = useState(student.notes || "");

  const [reviewMode, setReviewMode] = useState(false);
  const [rating, setRating] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [hireRec, setHireRec] = useState<"yes" | "maybe" | "no">("maybe");

  const { data: managers } = useManagers();
  const updateMut = useUpdateStudent();
  const reviewMut = useCreateReview();

  const acceptedManagers = (managers?.items || []).filter((m) => m.accepted_at);

  return (
    <div className="fixed inset-0 z-modal flex justify-end" onClick={onClose}>
      <div className="bg-black/30 absolute inset-0" />
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative bg-white w-full max-w-2xl h-full overflow-y-auto shadow-2xl"
      >
        <div className="border-b border-slate-200 p-5 flex items-start justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-900">{student.name}</h3>
            <p className="text-sm text-slate-500">{student.email}</p>
            <p className="text-xs text-slate-500 mt-1">
              {student.internship_title}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-slate-50 rounded-lg p-3">
              <div className="text-xs text-slate-500">Progress</div>
              <div className="text-2xl font-bold text-slate-900">
                {Math.round(student.progress_pct)}%
              </div>
            </div>
            <div className="bg-slate-50 rounded-lg p-3">
              <div className="text-xs text-slate-500">Attendance</div>
              <div className="text-2xl font-bold text-slate-900">
                {Math.round(student.attendance_pct)}%
              </div>
            </div>
            <div className="bg-slate-50 rounded-lg p-3">
              <div className="text-xs text-slate-500">Certificate</div>
              <div className="text-sm font-bold text-slate-900 mt-2">
                {student.cert_status === "issued"
                  ? "Issued"
                  : student.cert_status === "eligible"
                    ? "Eligible"
                    : "Not yet"}
              </div>
            </div>
          </div>

          {/* Resume & Links */}
          {(student.resume_url ||
            student.linkedin_url ||
            student.github_url ||
            student.portfolio_url) && (
            <div>
              <label className="block text-xs text-slate-500 mb-2">
                Resume & Links
              </label>
              <div className="flex flex-wrap gap-2">
                {student.resume_url && (
                  <button
                    onClick={() => {
                      if (student.resume_url)
                        window.open(
                          student.resume_url,
                          "_blank",
                          "noopener,noreferrer",
                        );
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    View Resume
                  </button>
                )}
                {student.linkedin_url && (
                  <button
                    onClick={() => {
                      if (student.linkedin_url)
                        window.open(
                          student.linkedin_url,
                          "_blank",
                          "noopener,noreferrer",
                        );
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium"
                  >
                    <Linkedin className="w-3.5 h-3.5" />
                    LinkedIn
                  </button>
                )}
                {student.github_url && (
                  <button
                    onClick={() => {
                      if (student.github_url)
                        window.open(
                          student.github_url,
                          "_blank",
                          "noopener,noreferrer",
                        );
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium"
                  >
                    <Github className="w-3.5 h-3.5" />
                    GitHub
                  </button>
                )}
                {student.portfolio_url && (
                  <button
                    onClick={() => {
                      if (student.portfolio_url)
                        window.open(
                          student.portfolio_url,
                          "_blank",
                          "noopener,noreferrer",
                        );
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium"
                  >
                    <Globe className="w-3.5 h-3.5" />
                    Portfolio
                  </button>
                )}
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs text-slate-500 mb-1">
              Reporting manager
            </label>
            <div className="flex gap-2">
              <select
                value={managerId}
                onChange={(e) =>
                  setManagerId(
                    e.target.value === "" ? "" : Number(e.target.value),
                  )
                }
                className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">— Unassigned —</option>
                {acceptedManagers.map((m) => (
                  <option key={m.id} value={m.user_id}>
                    {m.name}
                  </option>
                ))}
              </select>
              <button
                onClick={() =>
                  updateMut.mutate({
                    userId: student.user_id,
                    data: {
                      reporting_manager_user_id:
                        managerId === "" ? undefined : managerId,
                    },
                  })
                }
                disabled={updateMut.isPending}
                className="px-3 py-2 rounded-md bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white text-sm font-semibold"
              >
                Save
              </button>
            </div>
            {acceptedManagers.length === 0 && (
              <p className="text-[11px] text-slate-400 mt-1">
                No accepted managers yet — invite them on the Managers tab.
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">
              Private notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm min-h-[80px]"
              placeholder="Notes only your team can see…"
            />
            <button
              onClick={() =>
                updateMut.mutate({ userId: student.user_id, data: { notes } })
              }
              disabled={updateMut.isPending}
              className="mt-2 px-3 py-1.5 rounded-md bg-slate-700 hover:bg-slate-900 disabled:opacity-50 text-white text-xs font-semibold"
            >
              Save notes
            </button>
          </div>

          <div className="border-t border-slate-200 pt-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-slate-900 text-sm flex items-center gap-2">
                <Star className="w-4 h-4 text-amber-500" />
                Performance review
              </h4>
              {!reviewMode && (
                <button
                  onClick={() => setReviewMode(true)}
                  className="text-xs text-orange-700 font-semibold hover:underline"
                >
                  Submit review
                </button>
              )}
            </div>
            {!reviewMode && (
              <p className="text-xs text-slate-500">
                No review submitted yet. Available once internship hits 100% or
                status is marked Completed.
              </p>
            )}
            {reviewMode && (
              <div className="space-y-3 bg-slate-50 rounded-lg p-3">
                <div>
                  <label className="block text-xs text-slate-600 mb-1">
                    Rating
                  </label>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((r) => (
                      <button
                        key={r}
                        onClick={() => setRating(r)}
                        className={`w-8 h-8 rounded-md ${rating >= r ? "bg-amber-400 text-white" : "bg-white border border-slate-300 text-slate-400"}`}
                      >
                        <Star
                          className="w-4 h-4 mx-auto"
                          fill={rating >= r ? "currentColor" : "none"}
                        />
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-slate-600 mb-1">
                    Feedback
                  </label>
                  <textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm min-h-[80px]"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 mb-1">
                    Hire recommendation
                  </label>
                  <div className="flex gap-2">
                    {(["yes", "maybe", "no"] as const).map((v) => (
                      <button
                        key={v}
                        onClick={() => setHireRec(v)}
                        className={`px-3 py-1.5 rounded-md text-xs font-semibold capitalize ${hireRec === v ? "bg-orange-600 text-white" : "bg-white border border-slate-300 text-slate-700"}`}
                      >
                        {v}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      if (rating <= 0) return;
                      reviewMut.mutate(
                        {
                          student_user_id: student.user_id,
                          internship_id: student.internship_id,
                          rating,
                          feedback,
                          hire_recommendation: hireRec,
                        },
                        {
                          onSuccess: () => setReviewMode(false),
                        },
                      );
                    }}
                    disabled={reviewMut.isPending || rating <= 0}
                    className="px-3 py-1.5 rounded-md bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white text-xs font-semibold"
                  >
                    Submit
                  </button>
                  <button
                    onClick={() => setReviewMode(false)}
                    className="px-3 py-1.5 rounded-md text-slate-600 text-xs"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Internships (live + request queue)
// ============================================================================

function InternshipsTab({ companyName }: { companyName: string }) {
  const [openId, setOpenId] = useState<number | null>(null);
  const [requestOpen, setRequestOpen] = useState(false);

  const {
    data: liveData,
    isLoading: liveLoading,
    isError: liveError,
    refetch: refetchLive,
  } = useInternships();
  const {
    data: reqData,
    isLoading: reqLoading,
    isError: reqError,
    refetch: refetchReq,
  } = useInternshipRequests();
  const createReq = useCreateInternshipRequest();
  const deleteReq = useDeleteInternshipRequest();

  const live = useMemo(() => liveData?.items || [], [liveData?.items]);
  const allRequests = reqData?.items || [];
  const pending = allRequests.filter((r) => r.status === "pending");
  const rejected = allRequests.filter((r) => r.status === "rejected");
  const newlyApproved = allRequests.filter((r) => r.status === "approved");

  const open = useMemo(
    () => live.find((i) => i.id === openId) || null,
    [live, openId],
  );

  function handleSubmit(payload: {
    title: string;
    start: string;
    end: string;
    description: string;
    intern_count: number;
  }) {
    createReq.mutate(
      {
        title: payload.title,
        start_date: payload.start,
        end_date: payload.end,
        intern_count: payload.intern_count,
        description: payload.description,
      },
      { onSuccess: () => setRequestOpen(false) },
    );
  }

  async function handleWithdraw(id: number) {
    if (
      !(await confirmDialog(
        "Withdraw this pending request? You can re-submit anytime.",
      ))
    )
      return;
    deleteReq.mutate(id);
  }

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-slate-600 max-w-3xl">
          Browse the internships you&apos;re running, and <b>request</b> a new
          one.
          <span className="block text-xs text-slate-500 mt-1">
            Internships are <b>published by admin</b> — you submit a request,
            admin reviews it, assigns a SPOC, and either approves &amp;
            publishes it or sends it back with a reason.
          </span>
        </p>
        <button
          onClick={() => setRequestOpen(true)}
          className="px-3 py-1.5 rounded-md bg-orange-600 hover:bg-orange-700 text-white text-sm font-semibold flex items-center gap-1 shrink-0"
        >
          <Plus className="w-4 h-4" /> Request internship
        </button>
      </div>

      {requestOpen && (
        <RequestInternshipForm
          submitting={createReq.isPending}
          onCancel={() => setRequestOpen(false)}
          onSubmit={handleSubmit}
        />
      )}

      {/* Charts */}
      {!liveLoading && !liveError && (
        <CompanyInternshipCharts internships={live} />
      )}

      {/* Live internships */}
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-2 mb-3">
        Live · published by admin
      </h3>
      {liveLoading ? (
        <LoadingBlock>Loading internships…</LoadingBlock>
      ) : liveError ? (
        <ErrorState onRetry={() => refetchLive()} />
      ) : live.length === 0 ? (
        <div className="dash-card mb-6">
          <EmptyState
            icon={Briefcase}
            title="No live internships yet"
            description="Submit a request below — admin will review, assign a SPOC and publish it. It then appears here."
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {live.map((i) => (
            <LiveInternshipCard
              key={i.id}
              item={i}
              onOpen={() => setOpenId(i.id)}
            />
          ))}
        </div>
      )}

      {/* Approved-just-now banner */}
      {newlyApproved.length > 0 && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 mb-4">
          <div className="font-semibold text-emerald-900 text-sm mb-1">
            ✓ Admin approved {newlyApproved.length} request
            {newlyApproved.length === 1 ? "" : "s"}
          </div>
          <ul className="text-xs text-emerald-800 space-y-0.5">
            {newlyApproved.map((r) => (
              <li key={r.id}>
                <b>{r.title}</b>
                {r.approved_internship_id != null && (
                  <> · published as #{r.approved_internship_id}</>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Pending + rejected queue */}
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-2 mb-3">
        My requests
      </h3>
      {reqLoading ? (
        <LoadingBlock>Loading requests…</LoadingBlock>
      ) : reqError ? (
        <ErrorState onRetry={() => refetchReq()} />
      ) : pending.length === 0 && rejected.length === 0 ? (
        <div
          className="text-center py-10 text-sm text-slate-500 bg-white rounded-xl border border-dashed border-slate-300"
          data-glass="content"
        >
          No pending or returned requests.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...pending, ...rejected].map((i) => (
            <RequestCard
              key={i.id}
              item={i}
              onWithdraw={() => handleWithdraw(i.id)}
              onResubmit={() => setRequestOpen(true)}
            />
          ))}
        </div>
      )}

      {open && (
        <InternshipDetailDrawer
          item={open}
          companyName={companyName}
          onClose={() => setOpenId(null)}
        />
      )}
    </>
  );
}

function LiveInternshipCard({
  item,
  onOpen,
}: {
  item: CompanyInternship;
  onOpen: () => void;
}) {
  return (
    <div className="dash-card overflow-hidden p-0">
      <div className="bg-gradient-to-br from-indigo-500 to-purple-600 h-24 relative">
        <span className="absolute top-2 left-2 text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded bg-emerald-500 text-white">
          Live
        </span>
      </div>
      <div className="p-5">
        <h3 className="font-bold text-slate-900">{item.title}</h3>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 mt-2">
          <span>
            <b className="text-slate-700">{item.student_count}</b> of our
            students
          </span>
          <span>
            Avg progress:{" "}
            <b className="text-slate-700">
              {Math.round(item.avg_progress_pct)}%
            </b>
          </span>
          {item.spoc_name && <span>SPOC: {item.spoc_name}</span>}
        </div>
        <button
          onClick={onOpen}
          className="mt-3 text-sm text-orange-700 hover:text-orange-900 font-semibold"
        >
          View students &amp; curriculum →
        </button>
      </div>
    </div>
  );
}

function RequestCard({
  item,
  onWithdraw,
  onResubmit,
}: {
  item: InternshipRequestItem;
  onWithdraw: () => void;
  onResubmit: () => void;
}) {
  return (
    <div
      className={`bg-white rounded-xl border overflow-hidden ${item.status === "rejected" ? "border-rose-200" : "border-amber-200"}`}
      data-glass="content"
    >
      <div
        className={`bg-gradient-to-br ${item.status === "rejected" ? "from-rose-400 to-rose-600" : "from-amber-400 to-orange-500"} h-20 relative opacity-90`}
      >
        <span
          className={`absolute top-2 left-2 text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded text-white ${item.status === "pending" ? "bg-amber-700" : "bg-rose-700"}`}
        >
          {item.status === "pending"
            ? "Pending admin review"
            : "Returned by admin"}
        </span>
      </div>
      <div className="p-5">
        <h3 className="font-bold text-slate-900">{item.title}</h3>
        <div className="text-xs text-slate-500 mt-1">
          {item.start_date} → {item.end_date} · {item.intern_count} interns
          target
        </div>
        {item.description && (
          <p className="text-xs text-slate-600 mt-2">{item.description}</p>
        )}
        <p className="text-[11px] text-slate-400 mt-2">
          Submitted {new Date(item.created_at).toLocaleString()}
        </p>
        {item.status === "rejected" && item.rejection_reason && (
          <div className="mt-3 bg-rose-50 border border-rose-200 rounded p-2 text-xs">
            <div className="font-semibold text-rose-800 mb-0.5">
              Admin&apos;s feedback
            </div>
            <p className="text-rose-700">{item.rejection_reason}</p>
          </div>
        )}
        <div className="flex gap-3 mt-3">
          {item.status === "pending" && (
            <button
              onClick={onWithdraw}
              className="text-sm text-slate-600 hover:text-slate-900 font-semibold"
            >
              Withdraw request
            </button>
          )}
          {item.status === "rejected" && (
            <button
              onClick={onResubmit}
              className="text-sm text-orange-700 hover:text-orange-900 font-semibold"
            >
              Re-submit with changes
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function InternshipDetailDrawer({
  item,
  companyName,
  onClose,
}: {
  item: CompanyInternship;
  companyName: string;
  onClose: () => void;
}) {
  const { data: studentsData } = useStudents({ internship_id: item.id });
  const ourStudents = studentsData?.items || [];

  return (
    <div className="fixed inset-0 z-modal flex justify-end" onClick={onClose}>
      <div className="bg-black/30 absolute inset-0" />
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative bg-white w-full max-w-3xl h-full overflow-y-auto shadow-2xl"
      >
        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 h-32" />
        <div className="p-5 border-b border-slate-200 flex items-start justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-900">{item.title}</h3>
            <p className="text-xs text-slate-500 mt-1">
              SPOC: {item.spoc_name || "—"}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              {item.student_count} of our students · Avg progress{" "}
              {Math.round(item.avg_progress_pct)}%
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-5">
          <h4 className="font-semibold text-slate-900 mb-2 text-sm">
            {companyName} students on this internship
          </h4>
          {ourStudents.length === 0 ? (
            <EmptyState
              icon={Users}
              title="No students yet"
              description="Once enrolled, your interns appear here."
            />
          ) : (
            <div
              className="bg-white border border-slate-200 rounded-lg overflow-hidden"
              data-glass="work"
            >
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-slate-600 text-xs uppercase">
                  <tr>
                    <th className="text-left px-3 py-2">Name</th>
                    <th className="text-left px-3 py-2">Progress</th>
                    <th className="text-left px-3 py-2">Attendance</th>
                    <th className="text-left px-3 py-2">Manager</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {ourStudents.map((s) => (
                    <tr key={s.user_id}>
                      <td className="px-3 py-2 font-medium text-slate-900">
                        {s.name}
                      </td>
                      <td className="px-3 py-2">
                        <ProgressBar pct={s.progress_pct} />
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-700">
                        {Math.round(s.attendance_pct)}%
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-700">
                        {s.reporting_manager_name ?? (
                          <span className="text-slate-400 italic">
                            unassigned
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RequestInternshipForm({
  submitting,
  onCancel,
  onSubmit,
}: {
  submitting: boolean;
  onCancel: () => void;
  onSubmit: (p: {
    title: string;
    start: string;
    end: string;
    description: string;
    intern_count: number;
  }) => void;
}) {
  const [title, setTitle] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [desc, setDesc] = useState("");
  const [count, setCount] = useState(5);
  const valid = title.trim() && start && end && desc.trim().length >= 20;

  return (
    <div className="dash-card p-5 mb-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-slate-900">
          Request a new internship
        </h3>
        <button
          onClick={onCancel}
          className="text-slate-400 hover:text-slate-700"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="bg-orange-50 border border-orange-200 rounded p-3 text-xs text-orange-900 mb-4">
        <div className="font-semibold mb-1 flex items-center gap-1">
          <Mail className="w-3 h-3" /> How approval works
        </div>
        <ol className="list-decimal pl-5 space-y-0.5">
          <li>
            You submit a request with title, dates, intern count, and a brief.
          </li>
          <li>
            Admin reviews it and either approves &amp; publishes it (it then
            appears under <b>Live</b>) or returns it with a written reason.
          </li>
          <li>
            Companies <b>cannot publish</b> on their own. Only admin publishes.
          </li>
        </ol>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <label className="block text-xs text-slate-500 mb-1">Title</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="e.g. Data Science Internship — Cohort 8"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            Start date
          </label>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">End date</label>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            Intern count (target)
          </label>
          <input
            type="number"
            min={1}
            max={50}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            SPOC <span className="text-slate-400">(set by admin)</span>
          </label>
          <input
            disabled
            placeholder="Assigned by admin on approval"
            className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400"
          />
        </div>
        <div className="col-span-2">
          <label className="block text-xs text-slate-500 mb-1">
            Brief — what will interns work on?{" "}
            <span className="text-slate-400">(min 20 chars)</span>
          </label>
          <textarea
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm min-h-[80px]"
            placeholder="Tooling, tech stack, deliverables, expected outcomes…"
          />
        </div>
      </div>
      <div className="flex gap-2 mt-4 items-center">
        <button
          disabled={!valid || submitting}
          onClick={() =>
            valid &&
            onSubmit({
              title,
              start,
              end,
              description: desc,
              intern_count: count,
            })
          }
          className="px-3 py-1.5 rounded-md bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white text-sm font-semibold"
        >
          {submitting ? "Submitting…" : "Submit request to admin"}
        </button>
        <button
          onClick={onCancel}
          className="px-3 py-1.5 text-slate-600 text-sm"
        >
          Cancel
        </button>
        {!valid && (
          <span className="text-xs text-slate-400">
            Fill all fields. Brief must be at least 20 characters.
          </span>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Attendance
// ============================================================================

type AttStatus = "present" | "absent" | "late" | "excused" | null;

function fmtDay(d: Date) {
  return d.toLocaleDateString(undefined, { day: "2-digit", month: "short" });
}
function fmtWeekday(d: Date) {
  return d.toLocaleDateString(undefined, { weekday: "short" });
}

function cellCls(s: AttStatus, weekend: boolean) {
  if (weekend) return "bg-slate-50 text-slate-300 cursor-default";
  if (s === "present") return "bg-emerald-500 text-white hover:bg-emerald-600";
  if (s === "absent") return "bg-rose-500 text-white hover:bg-rose-600";
  if (s === "late") return "bg-amber-500 text-white hover:bg-amber-600";
  if (s === "excused") return "bg-slate-300 text-slate-700 hover:bg-slate-400";
  return "bg-slate-100 text-slate-400 hover:bg-slate-200 border border-dashed border-slate-300";
}

function cellLabel(s: AttStatus, hours: number) {
  if (s === "present") return `P${hours ? ` ${hours}h` : ""}`;
  if (s === "absent") return "A";
  if (s === "late") return `L${hours ? ` ${hours}h` : ""}`;
  if (s === "excused") return "E";
  return "";
}

function AttendanceTab() {
  // Month-by-month calendar view (Jan 2025 - 2030)
  const today = new Date();
  const currentYear = today.getFullYear();
  const clampYear = (y: number) => Math.max(2025, Math.min(2030, y));

  const [viewYear, setViewYear] = useState(clampYear(currentYear));
  const [viewMonth, setViewMonth] = useState(today.getMonth());

  // Generate date range for the selected month
  const firstDay = new Date(viewYear, viewMonth, 1);
  const lastDay = new Date(viewYear, viewMonth + 1, 0);
  const fromStr = firstDay.toISOString().slice(0, 10);
  const toStr = lastDay.toISOString().slice(0, 10);

  const canGoPrev = viewYear > 2025 || (viewYear === 2025 && viewMonth > 0);
  const canGoNext = viewYear < 2030 || (viewYear === 2030 && viewMonth < 11);

  const {
    data: grid,
    isLoading,
    isError,
    refetch,
  } = useAttendance(fromStr, toStr);
  const { data: workLogs, isLoading: wlLoading } = useWorkLogs();
  const upsertMut = useUpsertAttendance();
  const reviewMut = useReviewWorkLog();

  const [editing, setEditing] = useState<{
    student: any;
    date: string;
    entry?: AttendanceEntry;
  } | null>(null);

  if (isLoading) return <LoadingBlock>Loading attendance…</LoadingBlock>;
  if (isError || !grid) return <ErrorState onRetry={() => refetch()} />;

  const dates = grid.dates || [];
  const dateObjs = dates.map((d) => new Date(d + "T00:00:00"));

  function saveCell(
    student: any,
    date: string,
    status: AttStatus,
    hours: number,
    internshipId: number,
  ) {
    const entry: AttendanceEntry = {
      id: null,
      student_user_id: student.user_id,
      internship_id: internshipId,
      date,
      status: status || "present",
      hours_worked: hours,
      notes: "",
    };
    upsertMut.mutate([entry], {
      onSuccess: () => setEditing(null),
    });
  }

  return (
    <div className="space-y-5">
      <div className="dash-card p-4 flex flex-wrap items-center gap-3">
        <button
          onClick={() => {
            if (viewMonth === 0) {
              setViewYear((v) => clampYear(v - 1));
              setViewMonth(11);
            } else {
              setViewMonth((v) => v - 1);
            }
          }}
          disabled={!canGoPrev}
          className="px-3 py-1 text-sm bg-slate-100 hover:bg-slate-200 disabled:opacity-30 disabled:cursor-not-allowed rounded"
        >
          ← Prev
        </button>
        <div className="text-sm text-slate-700 font-medium">
          {firstDay.toLocaleDateString("en-US", {
            month: "long",
            year: "numeric",
          })}
        </div>
        <button
          onClick={() => {
            if (viewMonth === 11) {
              setViewYear((v) => clampYear(v + 1));
              setViewMonth(0);
            } else {
              setViewMonth((v) => v + 1);
            }
          }}
          disabled={!canGoNext}
          className="px-3 py-1 text-sm bg-slate-100 hover:bg-slate-200 disabled:opacity-30 disabled:cursor-not-allowed rounded"
        >
          Next →
        </button>
      </div>

      {grid.students.length === 0 ? (
        <div className="dash-card">
          <EmptyState
            icon={CalendarCheck}
            title="No students to mark yet"
            description="Once students enroll on your internships, an editable grid for their daily attendance shows up here."
          />
        </div>
      ) : (
        <div className="dash-card overflow-x-auto p-0">
          <table className="text-xs min-w-[1100px]">
            <thead className="bg-slate-50">
              <tr>
                <th className="sticky left-0 z-10 bg-slate-50 text-left px-3 py-2 border-r border-slate-200 min-w-[200px]">
                  Student
                </th>
                {dateObjs.map((d) => {
                  const dow = d.getDay();
                  const weekend = dow === 0 || dow === 6;
                  return (
                    <th
                      key={d.toISOString()}
                      className={`px-2 py-2 text-center font-medium ${weekend ? "text-slate-400" : "text-slate-600"}`}
                    >
                      <div>{fmtWeekday(d)}</div>
                      <div className="font-semibold text-slate-900">
                        {fmtDay(d)}
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {grid.students.map((s) => (
                <tr key={s.user_id}>
                  <td className="sticky left-0 bg-white px-3 py-2 border-r border-slate-200">
                    <div className="font-medium text-slate-900">{s.name}</div>
                    <div className="text-xs text-slate-500">{s.email}</div>
                  </td>
                  {dateObjs.map((d, di) => {
                    const dateStr = dates[di];
                    const entry = s.entries.find((e) => e.date === dateStr);
                    const status = (entry?.status as AttStatus) || null;
                    const hours = entry?.hours_worked ?? 0;
                    const dow = d.getDay();
                    const weekend = dow === 0 || dow === 6;
                    return (
                      <td key={dateStr} className="px-1 py-1 text-center">
                        <button
                          onClick={() =>
                            !weekend &&
                            setEditing({ student: s, date: dateStr, entry })
                          }
                          disabled={weekend}
                          className={`w-12 h-10 rounded text-[11px] font-semibold ${cellCls(status, weekend)}`}
                          title={
                            weekend
                              ? "Weekend"
                              : status
                                ? `${status} — ${hours}h`
                                : "Not marked"
                          }
                        >
                          {weekend
                            ? "—"
                            : status
                              ? cellLabel(status, hours)
                              : "·"}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="text-xs text-slate-500 flex flex-wrap gap-4">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-emerald-500" /> Present
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-rose-500" /> Absent
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-amber-500" /> Late
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-slate-300" /> Excused
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-slate-100 border border-slate-200" />{" "}
          Not marked
        </span>
      </div>

      {/* Daily work-done section */}
      <section className="dash-card p-5">
        <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
          <FileText className="w-4 h-4 text-orange-600" />
          Daily work-done submissions
        </h3>
        {wlLoading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : !workLogs || workLogs.items.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No work logs yet"
            description="Once interns submit daily work logs, you'll review them here."
          />
        ) : (
          <ul className="divide-y divide-slate-100">
            {workLogs.items.map((w) => (
              <WorkLogItemRow
                key={w.id}
                log={w}
                onReview={(status, comment) =>
                  reviewMut.mutate({ logId: w.id, data: { status, comment } })
                }
              />
            ))}
          </ul>
        )}
      </section>

      {editing && (
        <CellEditor
          student={editing.student}
          dateKey={editing.date}
          current={
            editing.entry
              ? {
                  status: editing.entry.status as AttStatus,
                  hours: editing.entry.hours_worked,
                }
              : { status: null, hours: 0 }
          }
          submitting={upsertMut.isPending}
          onSave={(s, h, internshipId) =>
            saveCell(editing.student, editing.date, s, h, internshipId)
          }
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}

function WorkLogItemRow({
  log,
  onReview,
}: {
  log: WorkLogItem;
  onReview: (status: string, comment: string) => void;
}) {
  const [comment, setComment] = useState("");
  const [showFlag, setShowFlag] = useState(false);
  return (
    <li className="py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-semibold text-slate-900">
              {log.student_name}
            </span>
            <span className="text-slate-400">·</span>
            <span className="text-xs text-slate-500">{log.log_date}</span>
            <span className="text-slate-400">·</span>
            <span className="text-xs text-slate-500">
              {log.internship_title}
            </span>
          </div>
          <p className="text-sm text-slate-700 mt-1 whitespace-pre-wrap">
            {log.content}
          </p>
          {log.reviewer_comment && (
            <p className="text-xs text-slate-500 mt-2 italic">
              Reviewer: {log.reviewer_comment}
            </p>
          )}
        </div>
        <ReviewBadge status={log.review_status} />
      </div>
      {log.review_status === "pending" && (
        <div className="flex flex-col gap-2 mt-2">
          <div className="flex gap-2">
            <button
              onClick={() => onReview("approved", "")}
              className="px-3 py-1 rounded text-xs bg-emerald-600 text-white font-semibold hover:bg-emerald-700"
            >
              Approve
            </button>
            <button
              onClick={() => setShowFlag((s) => !s)}
              className="px-3 py-1 rounded text-xs bg-rose-100 text-rose-700 font-semibold hover:bg-rose-200"
            >
              Flag
            </button>
          </div>
          {showFlag && (
            <div className="flex gap-2">
              <input
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Reason — shown to the intern"
                className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-xs"
              />
              <button
                disabled={comment.trim().length < 3}
                onClick={() => onReview("flagged", comment)}
                className="px-3 py-1 rounded text-xs bg-rose-600 disabled:opacity-50 text-white font-semibold hover:bg-rose-700"
              >
                Send
              </button>
            </div>
          )}
        </div>
      )}
    </li>
  );
}

function CellEditor({
  student,
  dateKey,
  current,
  submitting,
  onSave,
  onClose,
}: {
  student: any;
  dateKey: string;
  current: { status: AttStatus; hours: number };
  submitting: boolean;
  onSave: (s: AttStatus, h: number, internshipId: number) => void;
  onClose: () => void;
}) {
  const [status, setStatus] = useState<AttStatus>(current.status ?? "present");
  const [hours, setHours] = useState(current.hours || 8);
  const { data: internshipsData } = useInternships();
  const internships = internshipsData?.items || [];
  const [internshipId, setInternshipId] = useState<number | "">(
    internships.length === 1 ? internships[0].id : "",
  );

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center"
      onClick={onClose}
    >
      <div className="bg-black/40 absolute inset-0" />
      <div
        className="relative bg-white rounded-xl shadow-2xl p-5 w-[400px] max-w-[calc(100vw-2rem)]"
        onClick={(e) => e.stopPropagation()}
        data-glass="work"
      >
        <h3 className="font-bold text-slate-900">Mark attendance</h3>
        <p className="text-xs text-slate-500 mb-4">
          {student?.name} · {dateKey}
        </p>

        {internships.length > 1 && (
          <div className="mb-3">
            <label className="block text-xs text-slate-600 mb-1">
              Internship
            </label>
            <select
              value={internshipId}
              onChange={(e) =>
                setInternshipId(
                  e.target.value === "" ? "" : Number(e.target.value),
                )
              }
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">— Select —</option>
              {internships.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.title}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="flex gap-2 mb-3">
          {(["present", "late", "absent", "excused"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={`flex-1 px-2 py-1.5 rounded text-xs font-semibold capitalize ${status === s ? cellCls(s, false) : "bg-slate-100 text-slate-600"}`}
            >
              {s}
            </button>
          ))}
        </div>
        <label className="block text-xs text-slate-600 mb-1">Hours</label>
        <input
          type="number"
          step={0.5}
          value={hours}
          onChange={(e) => setHours(Number(e.target.value))}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm mb-3"
        />
        <div className="flex gap-2">
          <button
            disabled={submitting || internshipId === ""}
            onClick={() =>
              internshipId !== "" && onSave(status, hours, internshipId)
            }
            className="flex-1 px-3 py-2 rounded-md bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white text-sm font-semibold"
          >
            {submitting ? "Saving…" : "Save"}
          </button>
          <button
            onClick={onClose}
            className="px-3 py-2 rounded-md text-slate-600 text-sm"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Announcements
// ============================================================================

function AnnouncementsTab() {
  const [composing, setComposing] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [internshipId, setInternshipId] = useState<number | "all">("all");

  const { data, isLoading, isError, refetch } = useAnnouncements();
  const { data: internshipsData } = useInternships();
  const createMut = useCreateAnnouncement();
  const deleteMut = useDeleteAnnouncement();

  const internships = internshipsData?.items || [];

  function handlePost() {
    if (!title.trim() || !body.trim()) return;
    createMut.mutate(
      {
        title,
        body,
        internship_id: internshipId === "all" ? undefined : internshipId,
      },
      {
        onSuccess: () => {
          setTitle("");
          setBody("");
          setInternshipId("all");
          setComposing(false);
        },
      },
    );
  }

  return (
    <div className="space-y-4">
      {!composing ? (
        <button
          onClick={() => setComposing(true)}
          className="px-3 py-2 rounded-md bg-orange-600 hover:bg-orange-700 text-white text-sm font-semibold flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> New announcement
        </button>
      ) : (
        <div className="dash-card p-5 space-y-3">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold"
            placeholder="Title…"
          />
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm min-h-[120px]"
            placeholder="What's the announcement?"
          />
          <select
            value={internshipId}
            onChange={(e) =>
              setInternshipId(
                e.target.value === "all" ? "all" : Number(e.target.value),
              )
            }
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="all">All interns</option>
            {internships.map((i) => (
              <option key={i.id} value={i.id}>
                {i.title}
              </option>
            ))}
          </select>
          <div className="flex gap-2">
            <button
              onClick={handlePost}
              disabled={createMut.isPending || !title.trim() || !body.trim()}
              className="px-3 py-1.5 rounded-md bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white text-sm font-semibold"
            >
              {createMut.isPending ? "Posting…" : "Post"}
            </button>
            <button
              onClick={() => setComposing(false)}
              className="px-3 py-1.5 rounded-md text-slate-600 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <LoadingBlock>Loading announcements…</LoadingBlock>
      ) : isError ? (
        <ErrorState onRetry={() => refetch()} />
      ) : !data || data.items.length === 0 ? (
        <div className="dash-card">
          <EmptyState
            icon={Megaphone}
            title="No announcements yet"
            description="Post updates here for all interns or for a specific internship."
          />
        </div>
      ) : (
        <ul className="space-y-3">
          {data.items.map((a: AnnouncementItem) => (
            <li key={a.id} className="dash-card p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold text-slate-900">{a.title}</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Posted {new Date(a.created_at).toLocaleString()} ·{" "}
                    {a.internship_title ?? "All interns"}
                    {a.created_by_name && <> · by {a.created_by_name}</>}
                  </p>
                </div>
                <button
                  onClick={async () => {
                    if (await confirmDialog("Delete this announcement?"))
                      deleteMut.mutate(a.id);
                  }}
                  className="text-xs text-rose-600 hover:text-rose-800 font-semibold"
                >
                  Delete
                </button>
              </div>
              <p className="text-sm text-slate-700 mt-3 whitespace-pre-wrap">
                {a.body}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ============================================================================
// Reports
// ============================================================================

function ReportsTab() {
  const today = new Date();
  const monthAgo = new Date(today);
  monthAgo.setDate(today.getDate() - 30);

  const [from, setFrom] = useState(monthAgo.toISOString().slice(0, 10));
  const [to, setTo] = useState(today.toISOString().slice(0, 10));
  const [internship, setInternship] = useState<number | "all">("all");

  const { data: internshipsData } = useInternships();
  const internships = internshipsData?.items || [];

  const params = {
    from_date: from,
    to_date: to,
    internship_id: internship === "all" ? undefined : [internship],
    format: "json" as const,
  };
  const {
    data: report,
    isLoading,
    isError,
    refetch,
  } = useAttendanceReport(params);

  async function handleDownload(fmt: "csv" | "pdf") {
    try {
      const blob = await downloadAttendanceReport(params, fmt);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `attendance-${from}-to-${to}.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      // toast handled by axios interceptor
    }
  }

  return (
    <div className="space-y-5">
      <div className="dash-card p-5">
        <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <FileBarChart className="w-4 h-4 text-orange-600" />
          Attendance report
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs text-slate-500 mb-1">From</label>
            <input
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">To</label>
            <input
              type="date"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs text-slate-500 mb-1">
              Internship
            </label>
            <select
              value={internship}
              onChange={(e) =>
                setInternship(
                  e.target.value === "all" ? "all" : Number(e.target.value),
                )
              }
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="all">All</option>
              {internships.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.title}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex gap-2 mt-4">
          <button
            onClick={() => handleDownload("csv")}
            className="px-3 py-1.5 rounded-md bg-slate-700 hover:bg-slate-900 text-white text-xs font-semibold flex items-center gap-1"
          >
            <Download className="w-3 h-3" /> Download CSV
          </button>
          <button
            onClick={() => handleDownload("pdf")}
            className="px-3 py-1.5 rounded-md bg-slate-700 hover:bg-slate-900 text-white text-xs font-semibold flex items-center gap-1"
          >
            <Download className="w-3 h-3" /> Download PDF
          </button>
        </div>
      </div>

      {isLoading ? (
        <LoadingBlock>Loading report…</LoadingBlock>
      ) : isError ? (
        <ErrorState onRetry={() => refetch()} />
      ) : !report || !report.rows || report.rows.length === 0 ? (
        <div className="dash-card">
          <EmptyState
            icon={FileBarChart}
            title="No data in this date range"
            description="Pick a wider window or mark some attendance, then refresh."
          />
        </div>
      ) : (
        <div className="dash-card overflow-hidden">
          <div className="px-4 py-2 bg-slate-50 text-xs text-slate-600 font-medium border-b border-slate-200">
            Preview · {report.rows.length} rows
          </div>
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                {[
                  "Date",
                  "Student",
                  "Email",
                  "Internship",
                  "Manager",
                  "Status",
                  "Hours",
                  "Note",
                ].map((h) => (
                  <th key={h} className="text-left px-3 py-2 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {report.rows.map((r, i) => (
                <tr key={i}>
                  <td className="px-3 py-2 text-slate-700">{r.log_date}</td>
                  <td className="px-3 py-2 text-slate-900">{r.student_name}</td>
                  <td className="px-3 py-2 text-slate-600">
                    {r.student_email}
                  </td>
                  <td className="px-3 py-2 text-slate-700">
                    {r.internship_title}
                  </td>
                  <td className="px-3 py-2 text-slate-700">
                    {r.reporting_manager}
                  </td>
                  <td className="px-3 py-2">
                    <span className="text-xs font-semibold capitalize">
                      {r.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-slate-700">{r.hours}</td>
                  <td className="px-3 py-2 text-slate-500">{r.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Managers
// ============================================================================

function ManagersTab() {
  const [inviteOpen, setInviteOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");

  const { data, isLoading, isError, refetch } = useManagers();
  const inviteMut = useInviteManager();
  const revokeMut = useRevokeManager();

  function handleInvite() {
    if (!email.trim() || !name.trim()) return;
    inviteMut.mutate(
      { email, name },
      {
        onSuccess: () => {
          setEmail("");
          setName("");
          setInviteOpen(false);
        },
      },
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600 max-w-2xl">
          Invite teammates as <b>reporting managers</b>. Each manager logs in
          with their own credentials and only sees students assigned to them.
        </p>
        <button
          onClick={() => setInviteOpen(true)}
          className="px-3 py-1.5 rounded-md bg-orange-600 hover:bg-orange-700 text-white text-sm font-semibold flex items-center gap-1"
        >
          <Plus className="w-4 h-4" /> Invite manager
        </button>
      </div>

      <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 text-sm text-orange-900">
        <div className="font-semibold mb-1 flex items-center gap-2">
          <Mail className="w-4 h-4" /> How the invite flow works
        </div>
        <ol className="list-decimal pl-5 space-y-0.5 text-xs leading-relaxed">
          <li>
            You click <b>Invite manager</b> and enter their email + name.
          </li>
          <li>
            The system creates a placeholder account for that email and sends
            them a setup link.
          </li>
          <li>
            Your teammate opens the link, picks a password, and lands on this
            dashboard — scoped to only the students you assign to them.
          </li>
          <li>
            Their row in the table flips from{" "}
            <span className="font-semibold text-amber-700">Pending invite</span>{" "}
            → <span className="font-semibold text-emerald-700">Accepted</span>.
          </li>
          <li>
            You can <b>Revoke</b> a manager any time — that disables their login
            and unassigns their students.
          </li>
        </ol>
      </div>

      {inviteOpen && (
        <div className="dash-card p-4 flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs text-slate-500 mb-1">Email</label>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="manager@example.com"
            />
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs text-slate-500 mb-1">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="Manager name"
            />
          </div>
          <button
            onClick={handleInvite}
            disabled={inviteMut.isPending || !email.trim() || !name.trim()}
            className="px-3 py-2 rounded-md bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white text-sm font-semibold flex items-center gap-1"
          >
            <Mail className="w-4 h-4" />{" "}
            {inviteMut.isPending ? "Sending…" : "Send invite"}
          </button>
          <button
            onClick={() => setInviteOpen(false)}
            className="px-3 py-2 text-slate-600 text-sm"
          >
            Cancel
          </button>
        </div>
      )}

      {isLoading ? (
        <LoadingBlock>Loading managers…</LoadingBlock>
      ) : isError ? (
        <ErrorState onRetry={() => refetch()} />
      ) : !data || data.items.length === 0 ? (
        <div className="dash-card">
          <EmptyState
            icon={UserCog}
            title="No managers invited yet"
            description="Use the button above to invite teammates who'll oversee specific interns."
          />
        </div>
      ) : (
        <div className="dash-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase">
              <tr>
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Email</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3">Invited</th>
                <th />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((m: ManagerItem) => (
                <tr key={m.id}>
                  <td className="px-4 py-3 font-medium text-slate-900">
                    {m.name}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{m.email}</td>
                  <td className="px-4 py-3">
                    {m.accepted_at ? (
                      <span className="text-xs text-emerald-700 font-semibold">
                        Accepted
                      </span>
                    ) : (
                      <span className="text-xs text-amber-700 font-semibold">
                        Pending invite
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-500 text-xs">
                    {new Date(m.invited_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={async () => {
                        if (
                          await confirmDialog(
                            `Revoke ${m.name}? This disables their login and unassigns their students.`,
                          )
                        ) {
                          revokeMut.mutate(m.id);
                        }
                      }}
                      className="text-xs text-rose-600 hover:text-rose-800 font-semibold"
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Billing — profile, invoices, seat pools
// ============================================================================

const ensureRazorpayLoaded = async (): Promise<void> => {
  if ((window as any).Razorpay) return;
  await new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      'script[src="https://checkout.razorpay.com/v1/checkout.js"]',
    );
    if (existing) {
      if ((window as any).Razorpay) return resolve();
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () =>
        reject(new Error("Failed to load Razorpay SDK")),
      );
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Razorpay SDK"));
    document.body.appendChild(script);
  });
  // Race guard: onload can fire before the global is actually attached
  // in some browsers/adblock scenarios.
  if (!(window as any).Razorpay) {
    throw new Error(
      "Razorpay SDK did not initialize. Please disable ad-blockers and retry.",
    );
  }
};

function InvoiceStatusChip({ status }: { status: string }) {
  if (status === "paid") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">
        <CheckCircle2 className="w-3 h-3" /> Paid
      </span>
    );
  }
  if (status === "cancelled") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
        <XCircle className="w-3 h-3" /> Cancelled
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-700">
      <Clock3 className="w-3 h-3" /> Issued
    </span>
  );
}

function BillingTab() {
  return (
    <div className="space-y-6">
      <BillingProfileSection />
      <InvoicesSection />
      <SeatPoolsSection />
    </div>
  );
}

function BillingProfileSection() {
  const [profile, setProfile] = useState<BillingProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [saving, setSaving] = useState(false);

  const [gstin, setGstin] = useState("");
  const [legalName, setLegalName] = useState("");
  const [billingAddress, setBillingAddress] = useState("");
  const [stateCode, setStateCode] = useState("");

  const load = () => {
    setLoading(true);
    setIsError(false);
    fetchBillingProfile()
      .then((p) => {
        setProfile(p);
        setGstin(p.gstin);
        setLegalName(p.legal_name);
        setBillingAddress(p.billing_address);
        setStateCode(p.state_code);
      })
      .catch(() => setIsError(true))
      .finally(() => setLoading(false));
  };

  React.useEffect(() => {
    load();
  }, []);

  async function handleSave() {
    setSaving(true);
    try {
      const updated = await updateBillingProfile({
        gstin,
        legal_name: legalName,
        billing_address: billingAddress,
        state_code: stateCode,
      });
      setProfile(updated);
      toast.success("Billing profile saved");
    } catch (err: any) {
      toast.error(
        err?.response?.data?.detail || "Failed to save billing profile",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingBlock>Loading billing profile…</LoadingBlock>;
  if (isError || !profile) return <ErrorState onRetry={load} />;

  return (
    <section className="dash-card p-5">
      <h2 className="font-semibold text-slate-900 mb-1 flex items-center gap-2">
        <Receipt className="w-4 h-4 text-orange-600" />
        Billing profile
      </h2>
      <p className="text-xs text-slate-500 mb-4">
        Used on invoices we issue to <b>{profile.name}</b>. GSTIN and state code
        determine whether CGST+SGST or IGST applies.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-slate-500 mb-1">GSTIN</label>
          <input
            value={gstin}
            onChange={(e) => setGstin(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="e.g. 29ABCDE1234F1Z5"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            State code
          </label>
          <input
            value={stateCode}
            onChange={(e) => setStateCode(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="2-digit, e.g. 29"
            maxLength={2}
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            Legal name
          </label>
          <input
            value={legalName}
            onChange={(e) => setLegalName(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="Registered legal name"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            Billing address
          </label>
          <input
            value={billingAddress}
            onChange={(e) => setBillingAddress(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="Street, city, PIN"
          />
        </div>
      </div>
      <button
        onClick={handleSave}
        disabled={saving}
        className="mt-4 px-3 py-2 rounded-md bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white text-sm font-semibold"
      >
        {saving ? "Saving…" : "Save profile"}
      </button>
    </section>
  );
}

function InvoicesSection() {
  const [invoices, setInvoices] = useState<Invoice[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [payingId, setPayingId] = useState<number | null>(null);
  const user = useAuthStore((s) => s.user);

  const load = () => {
    setLoading(true);
    setIsError(false);
    fetchInvoices()
      .then(setInvoices)
      .catch(() => setIsError(true))
      .finally(() => setLoading(false));
  };

  React.useEffect(() => {
    load();
  }, []);

  async function handleDownload(inv: Invoice) {
    setDownloadingId(inv.id);
    try {
      await downloadInvoicePdf(
        inv.id,
        `${inv.invoice_number || `invoice-${inv.id}`}.pdf`,
      );
    } catch (err: any) {
      toast.error(
        err?.response?.data?.detail || "Could not download invoice PDF",
      );
    } finally {
      setDownloadingId(null);
    }
  }

  async function handlePay(inv: Invoice) {
    setPayingId(inv.id);
    try {
      const order = await createInvoiceOrder(inv.id);
      await ensureRazorpayLoaded();

      const rzp = new (window as any).Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency || "INR",
        name: "SashaInfinity",
        description: inv.invoice_number || `Invoice #${inv.id}`,
        order_id: order.order_id,
        prefill: {
          name: user
            ? `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim()
            : "",
          email: user?.user_email ?? "",
        },
        theme: { color: "#f97316" },
        handler: async (response: any) => {
          try {
            await verifyInvoicePayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              invoice_id: inv.id,
            });
            toast.success("Invoice paid — seats activated");
            load();
          } catch (verifyErr: any) {
            const message =
              verifyErr?.response?.data?.detail ??
              "Payment verification failed. Please contact support before paying again.";
            toast.error(message);
          } finally {
            setPayingId(null);
          }
        },
        modal: {
          ondismiss: () => {
            toast.error("Payment cancelled");
            setPayingId(null);
          },
        },
      });
      rzp.on("payment.failed", (resp: any) => {
        toast.error(resp?.error?.description || "Payment failed");
        setPayingId(null);
      });
      rzp.open();
    } catch (e: any) {
      const message = e?.response?.data?.detail ?? "Could not start payment";
      toast.error(message);
      setPayingId(null);
    }
  }

  return (
    <section className="dash-card p-5">
      <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
        <CreditCard className="w-4 h-4 text-orange-600" />
        Invoices
      </h2>

      {loading ? (
        <LoadingBlock>Loading invoices…</LoadingBlock>
      ) : isError ? (
        <ErrorState onRetry={load} />
      ) : !invoices || invoices.length === 0 ? (
        <EmptyState
          icon={Receipt}
          title="No invoices yet"
          description="Invoices we issue to your company for seat purchases will show up here."
        />
      ) : (
        <div className="overflow-x-auto -mx-5">
          <table className="w-full text-sm min-w-[720px]">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-5 py-3">Invoice #</th>
                <th className="text-left px-5 py-3">Issued</th>
                <th className="text-left px-5 py-3">Total</th>
                <th className="text-left px-5 py-3">Status</th>
                <th className="text-right px-5 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td className="px-5 py-3 font-medium text-slate-900">
                    {inv.invoice_number || `#${inv.id}`}
                  </td>
                  <td className="px-5 py-3 text-slate-700 text-xs">
                    {inv.issued_at
                      ? new Date(inv.issued_at).toLocaleDateString()
                      : "—"}
                  </td>
                  <td className="px-5 py-3">
                    <div className="text-slate-900 font-semibold">
                      ₹{inv.total.toFixed(2)}
                    </div>
                    {inv.tax_note && (
                      <div className="text-[11px] text-slate-500">
                        {inv.tax_note}
                      </div>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <InvoiceStatusChip status={inv.status} />
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleDownload(inv)}
                        disabled={downloadingId === inv.id}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-50 text-slate-700 text-xs font-medium"
                      >
                        {downloadingId === inv.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Download className="w-3.5 h-3.5" />
                        )}
                        PDF
                      </button>
                      {inv.status === "issued" && (
                        <button
                          onClick={() => handlePay(inv)}
                          disabled={payingId === inv.id}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white text-xs font-semibold"
                        >
                          {payingId === inv.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <CreditCard className="w-3.5 h-3.5" />
                          )}
                          Pay now
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function friendlySeatAssignError(err: any): string {
  const status = err?.response?.status;
  const detail = err?.response?.data?.detail;
  if (detail) return detail;
  if (status === 404)
    return "No account with that email — ask them to sign up first";
  if (status === 409)
    return "Could not assign this seat — it may already be taken or the pool is exhausted";
  return "Failed to assign seat";
}

function SeatPoolCard({ pool }: { pool: SeatPool }) {
  const [email, setEmail] = useState("");
  const [assigning, setAssigning] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [assignments, setAssignments] = useState<SeatAssignment[] | null>(null);
  const [assignmentsLoading, setAssignmentsLoading] = useState(false);

  const [seatsUsed, setSeatsUsed] = useState(pool.used_seats);
  const remaining = pool.total_seats - seatsUsed;

  const name =
    pool.course_title ||
    pool.bundle_name ||
    (pool.course_id
      ? `Course #${pool.course_id}`
      : `Bundle #${pool.bundle_id}`);

  function loadAssignments() {
    setAssignmentsLoading(true);
    fetchSeatAssignments(pool.id)
      .then(setAssignments)
      .catch(() => toast.error("Failed to load assignments"))
      .finally(() => setAssignmentsLoading(false));
  }

  function toggleExpanded() {
    const next = !expanded;
    setExpanded(next);
    if (next && assignments === null) loadAssignments();
  }

  async function handleAssign() {
    if (!email.trim()) return;
    setAssigning(true);
    try {
      await assignSeat(pool.id, email.trim());
      toast.success(`Seat granted to ${email.trim()}`);
      setEmail("");
      setSeatsUsed((s) => s + 1);
      if (expanded) loadAssignments();
    } catch (err: any) {
      toast.error(friendlySeatAssignError(err));
    } finally {
      setAssigning(false);
    }
  }

  return (
    <div className="dash-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-900">{name}</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {pool.course_id ? "Course seat pool" : "Bundle seat pool"}
          </p>
        </div>
        <div className="text-right shrink-0">
          <div className="text-lg font-bold text-slate-900">
            {seatsUsed} / {pool.total_seats}
          </div>
          <div className="text-[11px] text-slate-500">
            {remaining > 0 ? `${remaining} left` : "Full"}
          </div>
        </div>
      </div>

      <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden mt-3">
        <div
          className={`h-full ${remaining <= 0 ? "bg-rose-500" : remaining <= pool.total_seats * 0.2 ? "bg-amber-500" : "bg-emerald-500"}`}
          style={{
            width: `${Math.min(100, (seatsUsed / Math.max(pool.total_seats, 1)) * 100)}%`,
          }}
        />
      </div>

      <div className="flex gap-2 mt-4">
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleAssign();
          }}
          placeholder="teammate@company.com"
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          onClick={handleAssign}
          disabled={assigning || !email.trim() || remaining <= 0}
          className="px-3 py-2 rounded-md bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white text-sm font-semibold whitespace-nowrap"
        >
          {assigning ? "Assigning…" : "Assign seat"}
        </button>
      </div>

      <button
        onClick={toggleExpanded}
        className="mt-3 text-xs text-orange-700 hover:text-orange-900 font-semibold"
      >
        {expanded ? "Hide assignments ▲" : "View assignments ▼"}
      </button>

      {expanded && (
        <div className="mt-2 border-t border-slate-100 pt-3">
          {assignmentsLoading ? (
            <p className="text-xs text-slate-500">Loading…</p>
          ) : !assignments || assignments.length === 0 ? (
            <p className="text-xs text-slate-400 italic">
              No seats assigned yet.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {assignments.map((a) => (
                <li
                  key={a.user_id}
                  className="py-1.5 text-xs flex items-center justify-between"
                >
                  <span className="text-slate-700">{a.email}</span>
                  <span className="text-slate-400">
                    {a.assigned_at
                      ? new Date(a.assigned_at).toLocaleDateString()
                      : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function SeatPoolsSection() {
  const [pools, setPools] = useState<SeatPool[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [isError, setIsError] = useState(false);

  const load = () => {
    setLoading(true);
    setIsError(false);
    fetchSeatPools()
      .then(setPools)
      .catch(() => setIsError(true))
      .finally(() => setLoading(false));
  };

  React.useEffect(() => {
    load();
  }, []);

  return (
    <section>
      <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
        <Users2 className="w-4 h-4 text-orange-600" />
        Seat pools
      </h2>

      {loading ? (
        <LoadingBlock>Loading seat pools…</LoadingBlock>
      ) : isError ? (
        <ErrorState onRetry={load} />
      ) : !pools || pools.length === 0 ? (
        <div className="dash-card">
          <EmptyState
            icon={Users2}
            title="No seat pools yet"
            description="Once you purchase course or bundle seats for your team, they'll appear here for you to assign by email."
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {pools.map((p) => (
            <SeatPoolCard key={p.id} pool={p} />
          ))}
        </div>
      )}
    </section>
  );
}
