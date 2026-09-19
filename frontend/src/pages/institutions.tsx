import { CampusLearning } from "@/components/institutions/CampusLearning";
import { CampusPilot } from "@/components/institutions/CampusPilot";
import { BillingRecovery } from "@/components/institutions/BillingRecovery";
import { CampusAcademics } from "@/components/institutions/CampusAcademics";
import {
  CampusResources,
  CampusBranding,
  CampusBrandedHero,
  BulkInvites,
  SendInviteEmail,
} from "@/components/institutions/CampusTools";
import { CampusBilling } from "@/components/institutions/CampusBilling";
import { CampusActionCenter } from "@/components/institutions/CampusActionCenter";
import { CampusAdmissions } from "@/components/institutions/CampusAdmissions";
import { CampusFinance } from "@/components/institutions/CampusFinance";
import { CampusExams } from "@/components/institutions/CampusExams";
import { CampusStaff } from "@/components/institutions/CampusStaff";
import { CampusTransport } from "@/components/institutions/CampusTransport";
import { CampusHostel } from "@/components/institutions/CampusHostel";
import { CampusControlPlane } from "@/components/institutions/CampusControlPlane";
import { useState } from "react";
import {
  Link,
  NavLink,
  Navigate,
  useNavigate,
  useParams,
} from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUpRight,
  ArrowRight,
  Plus,
  Building2,
  GraduationCap,
  Users,
  BookOpen,
  Layers,
  BarChart3,
  Settings,
  CreditCard,
  Check,
  CheckCircle2,
  Activity,
  Download,
  Search,
  ShieldCheck,
  CalendarDays,
  Mail,
  BellRing,
  UserPlus,
  WalletCards,
  ClipboardList,
  CalendarOff,
  Bus,
  BedDouble,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  institutionApi,
  type Institution,
  type InstitutionOverview,
} from "@/api/institutions";
import {
  InstitutionDialog,
  apiError,
  type InstitutionDialogState,
} from "@/components/institutions/InstitutionDialog";
import { InstitutionPlanQueue } from "@/components/institutions/InstitutionPlanQueue";
import { DashboardWorkspace } from "@/components/dashboard/DashboardWorkspace";
import type { Role } from "@/components/dashboard/DashboardSidebar";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth";
import { roleHomePath } from "@/utils/role-routing";
import toast from "react-hot-toast";

const sections: {
  key: string;
  label: string;
  icon: LucideIcon;
  manager?: boolean;
  staff?: boolean;
}[] = [
  { key: "overview", label: "Overview", icon: Building2 },
  { key: "today", label: "Today", icon: BellRing },
  { key: "daily", label: "Daily campus", icon: CalendarDays },
  { key: "admissions", label: "Admissions", icon: UserPlus, manager: true },
  { key: "finance", label: "Finance", icon: WalletCards },
  { key: "people", label: "People", icon: Users, staff: true },
  { key: "batches", label: "Batches", icon: Layers },
  { key: "courses", label: "Courses", icon: BookOpen },
  { key: "reports", label: "Progress", icon: BarChart3 },
  { key: "academics", label: "Academics", icon: CalendarDays },
  { key: "exams", label: "Exams", icon: ClipboardList },
  { key: "staff", label: "Staff", icon: CalendarOff, staff: true },
  { key: "transport", label: "Transport", icon: Bus },
  { key: "hostel", label: "Hostel", icon: BedDouble },
  { key: "resources", label: "Resources", icon: BookOpen },
  { key: "plan", label: "Plan & usage", icon: CreditCard, manager: true },
  { key: "settings", label: "Settings", icon: Settings, manager: true },
  { key: "trust", label: "Trust & integrations", icon: ShieldCheck, manager: true },
];
function Empty({
  title,
  text,
  action,
  icon: Icon = GraduationCap,
}: {
  title: string;
  text: string;
  action?: React.ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <div className="campus-empty">
      <span className="campus-icon">
        <Icon size={23} />
      </span>
      <h2>{title}</h2>
      <p>{text}</p>
      {action}
    </div>
  );
}
function Progress({ value }: { value: number }) {
  return (
    <div
      className="campus-progress"
      role="progressbar"
      aria-label="Completion"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <span style={{ width: `${value}%` }} />
    </div>
  );
}
function Hero({ name, action }: { name?: string; action: React.ReactNode }) {
  return (
    <section className="campus-hero">
      <div>
        <span className="campus-eyebrow">
          <GraduationCap size={15} /> Built for your learning community
        </span>
        <h2>
          {name
            ? "A clearer picture. A stronger campus."
            : "One campus. Every learning possibility."}
        </h2>
        <p>
          {name
            ? "Bring your people, teaching and progress together. Give every student a clear path forward."
            : "A thoughtful home for your school or college. Connect teachers, organize classes and make progress visible."}
        </p>
        {action}
      </div>
      <div className="campus-hero-art" aria-hidden="true">
        <div className="campus-orbit" />
        <div className="campus-emblem">
          <GraduationCap size={62} strokeWidth={1.3} />
        </div>
        <span className="campus-floating">
          <CheckCircle2 size={16} color="#a83b0b" /> Learning, connected
        </span>
        <span className="campus-floating">
          <Users size={16} color="#a83b0b" /> Your campus. Together.
        </span>
      </div>
    </section>
  );
}

export default function InstitutionsPage() {
  const { institutionId, "*": tail } = useParams();
  const id = Number(institutionId) || 0;
  const section = tail || "overview";
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const cache = useQueryClient();
  const [dialog, setDialog] = useState<InstitutionDialogState | null>(null);
  const [search, setSearch] = useState("");
  const [reportBatch, setReportBatch] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const list = useQuery({
    queryKey: ["institutions", user?.id],
    queryFn: institutionApi.list,
  });
  const inbox = useQuery({
    queryKey: ["institution-invitations", user?.id],
    queryFn: institutionApi.invitations,
  });
  const detail = useQuery({
    queryKey: ["institution", user?.id, id],
    queryFn: () => institutionApi.overview(id),
    enabled: !!id,
  });
  const data = detail.data;
  const inst = data?.institution;
  const manager = inst?.role === "owner" || inst?.role === "admin";
  const staff = manager || inst?.role === "teacher";
  const visibleSections = sections.filter(
    (s) => (!s.manager || manager) && (!s.staff || staff),
  );
  const base = `/institutions/${id}`;
  const visible = <T extends { name?: string; title?: string; email?: string }>(
    items: T[],
  ) =>
    items.filter((x) =>
      `${x.name || x.title || ""} ${x.email || ""}`
        .toLowerCase()
        .includes(search.toLowerCase()),
    );
  async function refresh(created?: Institution) {
    await Promise.all([
      cache.invalidateQueries({ queryKey: ["institutions", user?.id] }),
      cache.invalidateQueries({ queryKey: ["institution", user?.id, id] }),
      cache.invalidateQueries({
        queryKey: ["institution-invitations", user?.id],
      }),
    ]);
    if (created) navigate(`/institutions/${created.id}`);
  }
  async function action(fn: () => Promise<unknown>, message: string) {
    setBusy(true);
    setActionError("");
    try {
      await fn();
      await refresh();
      toast.success(message);
    } catch (error) {
      setActionError(apiError(error));
    } finally {
      setBusy(false);
    }
  }
  async function download() {
    await action(async () => {
      const blob = await institutionApi.export(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${inst?.slug || "campus"}-progress.csv`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }, "Progress report downloaded");
  }
  const nav = [
    {
      to: "/institutions",
      label: "My institutions",
      icon: Building2,
      exact: true,
    },
    ...(inst
      ? visibleSections.map((s) => ({
          to: `${base}/${s.key}`,
          label: s.label,
          icon: s.icon,
        }))
      : []),
    {
      to: roleHomePath(user?.role),
      label: "My LMS dashboard",
      icon: GraduationCap,
    },
  ];
  const content = () => {
    if (!id)
      return (
        <>
          <div className="campus-topline">
            <div>
              <span className="campus-eyebrow">SashaInfinity Campus</span>
              <h1>Your institutions</h1>
              <p>
                A shared home for schools, colleges and the people who make
                them.
              </p>
            </div>
            <Button
              onClick={() => setDialog({ kind: "create" })}
              leftIcon={<Plus size={16} />}
            >
              Create institution
            </Button>
          </div>
          <Hero
            action={
              <Button
                onClick={() => setDialog({ kind: "create" })}
                rightIcon={<ArrowRight size={16} />}
              >
                Set up your campus
              </Button>
            }
          />
          {(user?.role === "admin" || user?.role === "superadmin") && (
            <>
              <InstitutionPlanQueue />
              <BillingRecovery />
            </>
          )}
          {inbox.isError && (
            <p className="campus-error" role="alert">
              Couldn’t load invitations.{" "}
              <button onClick={() => void inbox.refetch()}>Retry</button>
            </p>
          )}
          {!!inbox.data?.length && (
            <section className="campus-panel">
              <div className="campus-panel-heading">
                <h2>Invitations for you</h2>
                <Mail size={19} />
              </div>
              {inbox.data.map((i) => (
                <div key={i.id} className="campus-step">
                  <span className="campus-icon">
                    <Building2 size={18} />
                  </span>
                  <div className="campus-step-copy">
                    <strong>{i.institution_name}</strong>
                    <p>
                      Join as {i.role} · expires{" "}
                      {new Date(i.expires_at).toLocaleDateString()}
                    </p>
                  </div>
                  <Button
                    disabled={busy}
                    onClick={() =>
                      void action(async () => {
                        const joined = await institutionApi.accept(i.id);
                        navigate(`/institutions/${joined.id}`);
                      }, "You joined the institution")
                    }
                  >
                    Accept invitation
                  </Button>
                </div>
              ))}
            </section>
          )}
          {list.isPending ? (
            <div
              className="campus-skeleton"
              role="status"
              aria-label="Loading institutions"
            />
          ) : list.isError ? (
            <div className="campus-error" role="alert">
              Couldn’t load your institutions.{" "}
              <button onClick={() => void list.refetch()}>Retry</button>
            </div>
          ) : list.data?.length ? (
            <div className="campus-grid">
              {list.data.map((i) => (
                <Link
                  key={i.id}
                  to={`/institutions/${i.id}`}
                  className="campus-panel"
                >
                  <div className="campus-panel-heading">
                    <span className="campus-icon">
                      <Building2 size={21} />
                    </span>
                    <ArrowUpRight size={17} />
                  </div>
                  <span className="campus-chip">
                    {i.kind} · {i.role}
                  </span>
                  <h3>{i.name}</h3>
                  <p className="campus-muted">
                    Academic year {i.academic_year}
                  </p>
                </Link>
              ))}
            </div>
          ) : (
            <section className="campus-panel">
              <Empty
                title="Your next chapter starts here"
                text="Create an institution or accept an invitation from your school. Your existing courses and personal learning stay connected."
              />
            </section>
          )}
        </>
      );
    if (detail.isPending)
      return (
        <div className="campus" role="status" aria-label="Loading institution">
          <div className="campus-skeleton" />
          <div className="campus-stats">
            {[1, 2, 3, 4].map((n) => (
              <div key={n} className="campus-skeleton" />
            ))}
          </div>
        </div>
      );
    if (detail.isError || !data || !inst)
      return (
        <section className="campus-panel">
          <Empty
            title="We couldn’t open this institution"
            text="It may be unavailable, or your account may no longer have access."
            action={
              <div className="campus-actions">
                <Button variant="outline" onClick={() => void detail.refetch()}>
                  Retry
                </Button>
                <Button asChild>
                  <Link to="/institutions">My institutions</Link>
                </Button>
              </div>
            }
          />
        </section>
      );
    const report = data.report.filter(
      (r) => !reportBatch || String(r.batch_id) === reportBatch,
    );
    const activeStudents = data.members.filter(
      (m) => m.role === "student" && m.status === "active",
    ).length;
    const completed = data.report.filter((r) => r.progress >= 100).length;
    const percent = data.report.length
      ? Math.round((completed / data.report.length) * 100)
      : 0;
    const steps = [
      {
        label: "Make it your campus",
        text: "Set your institution details and academic year.",
        done: true,
        to: "settings",
      },
      {
        label: "Bring your people together",
        text: "Invite teachers and students to join.",
        done: data.members.length > 1,
        to: "people",
      },
      {
        label: "Create your first batch",
        text: "Organize a class, section or department.",
        done: data.batches.length > 0,
        to: "batches",
      },
      {
        label: "Connect your teaching",
        text: "Add a course, then assign it to a batch.",
        done: data.batches.some((b) => b.assignments.length),
        to: "courses",
      },
    ];
    return (
      <>
        <div className="campus-topline">
          <div>
            <span className="campus-eyebrow">
              <Building2 size={14} />{" "}
              {inst.kind === "school"
                ? "School workspace"
                : "College workspace"}{" "}
              <span> / </span> {inst.academic_year}
            </span>
            <h1>{inst.name}</h1>
            <p>
              Your campus, connected. Welcome to the{" "}
              {section === "overview"
                ? "overview"
                : visibleSections
                    .find((s) => s.key === section)
                    ?.label.toLowerCase() || "workspace"}
              .
            </p>
          </div>
          <div className="campus-actions">
            <select
              aria-label="Switch institution"
              className="campus-select"
              value={id}
              onChange={(e) => {
                setSearch("");
                setReportBatch("");
                navigate(`/institutions/${e.target.value}`);
              }}
            >
              {list.data?.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name}
                </option>
              ))}
            </select>
            {manager && (
              <Button
                leftIcon={<Plus size={15} />}
                onClick={() => setDialog({ kind: "invite" })}
              >
                Invite people
              </Button>
            )}
          </div>
        </div>
        <nav className="campus-tabs" aria-label="Institution sections">
          {visibleSections.map((s) => (
            <NavLink
              key={s.key}
              to={`${base}/${s.key}`}
              className={({ isActive }) =>
                isActive || (s.key === "overview" && !tail)
                  ? "campus-tab-active"
                  : ""
              }
              aria-current={s.key === section ? "page" : undefined}
            >
              <s.icon size={15} />
              {s.label}
            </NavLink>
          ))}
        </nav>
        {[
          "people",
          "batches",
          "courses",
          "reports",
          "plan",
        ].includes(section) && <CampusBrandedHero id={inst.id} compact />}
        {section === "overview" && (
          <>
            <CampusBrandedHero id={inst.id} />
            <div className="campus-stats">
              {[
                {
                  label: staff ? "Active students" : "My batches",
                  value: staff ? activeStudents : data.batches.length,
                  icon: Users,
                  note: staff
                    ? "Members with student access"
                    : "Your learning groups",
                },
                {
                  label: "Connected courses",
                  value: data.courses.length,
                  icon: BookOpen,
                  note: "Teaching in one place",
                },
                {
                  label: "Academic batches",
                  value: data.batches.length,
                  icon: Layers,
                  note: "Across your institution",
                },
                {
                  label: "Course completion",
                  value: data.report.length ? `${percent}%` : "—",
                  icon: BarChart3,
                  note: data.report.length
                    ? `${completed} of ${data.report.length} assignments complete`
                    : "Appears as students learn",
                },
              ].map((s) => (
                <article key={s.label} className="campus-panel campus-stat">
                  <div className="campus-stat-top">
                    {s.label}
                    <span className="campus-icon">
                      <s.icon size={18} />
                    </span>
                  </div>
                  <strong>{s.value}</strong>
                  <small>{s.note}</small>
                </article>
              ))}
            </div>
            <div className="campus-columns">
              <section className="campus-panel">
                <div className="campus-panel-heading">
                  <h2>
                    {manager
                      ? "Your campus launch checklist"
                      : "Your learning community"}
                  </h2>
                  <span className="campus-chip">
                    {manager
                      ? `${steps.filter((s) => s.done).length} / 4 complete`
                      : inst.role}
                  </span>
                </div>
                {manager ? (
                  <>
                    <Progress value={steps.filter((s) => s.done).length * 25} />
                    {steps.map((s, i) => (
                      <Link
                        to={`${base}/${s.to}`}
                        className="campus-step"
                        key={s.label}
                      >
                        <span className="campus-step-number">
                          {s.done ? <Check size={15} /> : i + 1}
                        </span>
                        <div className="campus-step-copy">
                          <strong>{s.label}</strong>
                          <p>{s.text}</p>
                        </div>
                        <ArrowRight size={15} />
                      </Link>
                    ))}
                  </>
                ) : (
                  <Empty
                    title="Make your next step count"
                    text="Find the courses assigned to your batches and track your progress as you learn."
                    action={
                      <Button asChild>
                        <Link to={`${base}/courses`}>Open courses</Link>
                      </Button>
                    }
                  />
                )}
              </section>
              <section className="campus-panel">
                <div className="campus-panel-heading">
                  <h2>{manager ? "Campus activity" : "Learning snapshot"}</h2>
                  <Activity size={18} />
                </div>
                {manager ? (
                  data.activity.slice(0, 5).map((a) => (
                    <div className="campus-activity" key={a.id}>
                      <span className="campus-dot" />
                      <div>
                        <p>{a.detail}</p>
                        <small>
                          {a.action.replace(/\./g, " · ").replace(/_/g, " ")} ·{" "}
                          {new Date(a.created_at).toLocaleDateString()}
                        </small>
                      </div>
                    </div>
                  ))
                ) : (
                  <>
                    <p className="campus-muted">Completed course assignments</p>
                    <h3>
                      {completed} of {data.report.length}
                    </h3>
                    <Progress value={percent} />
                    <p className="campus-muted" style={{ marginTop: 15 }}>
                      Completion reflects course progress, not an independent
                      measure of subject mastery.
                    </p>
                  </>
                )}
              </section>
            </div>
          </>
        )}
        {section === "today" && (
          <CampusActionCenter key={inst.id} data={data} />
        )}
        {section === "daily" && <CampusPilot key={inst.id} data={data} />}
        {section === "admissions" && manager && (
          <CampusAdmissions key={inst.id} data={data} />
        )}
        {section === "finance" && (
          <CampusFinance key={inst.id} data={data} studentUserId={user?.id} />
        )}
        {section === "academics" && (
          <CampusAcademics key={inst.id} data={data} />
        )}
        {section === "exams" && (
          <CampusExams key={inst.id} data={data} studentUserId={user?.id} />
        )}
        {section === "staff" && staff && (
          <CampusStaff key={inst.id} data={data} />
        )}
        {section === "transport" && (
          <CampusTransport key={inst.id} data={data} studentUserId={user?.id} />
        )}
        {section === "hostel" && (
          <CampusHostel key={inst.id} data={data} studentUserId={user?.id} />
        )}
        {section === "resources" && (
          <CampusResources key={inst.id} data={data} />
        )}
        {section === "people" && manager && (
          <BulkInvites id={inst.id} saved={refresh} />
        )}
        {section === "people" && staff && (
          <section className="campus-panel">
            <div className="campus-panel-heading">
              <div>
                <h2>People make the campus</h2>
                <p className="campus-muted">
                  Staff and students, with the right access.
                </p>
              </div>
              <input
                className="campus-search"
                aria-label="Search people"
                placeholder="Search name or email…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="campus-table-wrap">
              <table className="campus-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Department</th>
                    <th>Status</th>
                    {manager && <th>Access</th>}
                  </tr>
                </thead>
                <tbody>
                  {visible(data.members).map((m) => (
                    <tr key={m.id}>
                      <td>
                        <strong>{m.name}</strong>
                        <small>{m.email}</small>
                      </td>
                      <td className="capitalize">{m.role}</td>
                      <td>{m.department || "—"}</td>
                      <td>
                        <span
                          className="campus-chip"
                          data-tone={
                            m.status === "active" ? "success" : "muted"
                          }
                        >
                          {m.status}
                        </span>
                      </td>
                      {manager && (
                        <td>
                          {m.role !== "owner" &&
                            m.user_id !== user?.id &&
                            (inst.role === "owner" || m.role !== "admin") && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() =>
                                  setDialog({ kind: "member", member: m })
                                }
                              >
                                Manage<span className="sr-only"> {m.name}</span>
                              </Button>
                            )}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
              {!visible(data.members).length && (
                <Empty
                  title="No matching people"
                  text="Try another name or clear your search."
                  icon={Search}
                />
              )}
            </div>
            {!!data.invites.length && (
              <>
                <div className="campus-panel-heading" style={{ marginTop: 28 }}>
                  <h2>Invitations</h2>
                  <span className="campus-chip">Account inbox delivery</span>
                </div>
                {data.invites.map((i) => (
                  <div className="campus-step" key={i.id}>
                    <Mail size={17} />
                    <div className="campus-step-copy">
                      <strong>{i.email}</strong>
                      <p>
                        {i.role} · {i.status}
                      </p>
                    </div>
                    {i.status === "pending" &&
                      manager &&
                      (inst.role === "owner" || i.role !== "admin") && (
                        <SendInviteEmail id={inst.id} invite={i.id} />
                      )}
                    {i.status === "pending" &&
                      (inst.role === "owner" || i.role !== "admin") && (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={busy}
                          onClick={() =>
                            void action(
                              () => institutionApi.revoke(id, i.id),
                              "Invitation revoked",
                            )
                          }
                        >
                          Revoke
                          <span className="sr-only">
                            {" "}
                            invitation for {i.email}
                          </span>
                        </Button>
                      )}
                  </div>
                ))}
              </>
            )}
          </section>
        )}
        {section === "batches" && (
          <>
            <div className="campus-toolbar">
              <p className="campus-muted">
                Classes, sections and cohorts for {inst.academic_year}.
              </p>
              {manager && (
                <Button
                  leftIcon={<Plus size={15} />}
                  onClick={() => setDialog({ kind: "batch" })}
                >
                  Create batch
                </Button>
              )}
            </div>
            {data.batches.length ? (
              <div className="campus-grid">
                {data.batches.map((b) => (
                  <article key={b.id} className="campus-panel">
                    <div className="campus-panel-heading">
                      <span className="campus-icon">
                        <Layers size={20} />
                      </span>
                      <span className="campus-chip">{b.academic_year}</span>
                    </div>
                    <h3>{b.name}</h3>
                    <p className="campus-muted">
                      {b.department || "General department"}
                    </p>
                    <div className="campus-step">
                      <Users size={16} />{" "}
                      <span className="campus-muted">
                        {b.student_count} students · {b.assignments.length}{" "}
                        courses
                      </span>
                    </div>
                    {b.assignments.map((a) => (
                      <p
                        className="campus-muted"
                        key={a.id}
                        style={{ marginTop: 10 }}
                      >
                        {
                          data.courses.find(
                            (c) => c.id === a.institution_course_id,
                          )?.title
                        }
                        {a.due_date ? ` · due ${a.due_date}` : ""}
                      </p>
                    ))}
                    {manager && (
                      <div className="campus-actions" style={{ marginTop: 18 }}>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            setDialog({ kind: "students", batch: b })
                          }
                        >
                          Add students
                          <span className="sr-only"> to {b.name}</span>
                        </Button>
                        <Button
                          size="sm"
                          onClick={() =>
                            setDialog({ kind: "assign", batch: b })
                          }
                        >
                          Assign course
                          <span className="sr-only"> to {b.name}</span>
                        </Button>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <section className="campus-panel">
                <Empty
                  title="A place for every class"
                  text="Group students by grade, section, semester or department. Then assign the courses they’ll learn together."
                  action={
                    manager && (
                      <Button onClick={() => setDialog({ kind: "batch" })}>
                        Create your first batch
                      </Button>
                    )
                  }
                  icon={Layers}
                />
              </section>
            )}
          </>
        )}
        {section === "courses" && <CampusLearning key={inst.id} data={data} />}
        {section === "courses" && (
          <>
            <div className="campus-toolbar">
              <p className="campus-muted">
                Your teaching, connected to your campus.
              </p>
              {staff && (
                <Button
                  leftIcon={<Plus size={15} />}
                  onClick={() => setDialog({ kind: "connect" })}
                >
                  Connect course
                </Button>
              )}
            </div>
            {data.courses.length ? (
              <div className="campus-grid">
                {data.courses.map((c) => (
                  <article key={c.id} className="campus-panel">
                    <div className="campus-panel-heading">
                      <span className="campus-icon">
                        <BookOpen size={21} />
                      </span>
                      <span
                        className="campus-chip"
                        data-tone={
                          (c.status === "published" || c.status === "publish") ? "success" : "muted"
                        }
                      >
                        {c.status}
                      </span>
                    </div>
                    <h3>{c.title}</h3>
                    <p className="campus-muted">
                      {
                        data.batches.filter((b) =>
                          b.assignments.some(
                            (a) => a.institution_course_id === c.id,
                          ),
                        ).length
                      }{" "}
                      assigned batches
                    </p>
                    <div className="campus-actions" style={{ marginTop: 20 }}>
                      {(c.status === "published" || c.status === "publish") && (
                        <Button asChild variant="outline" size="sm">
                          <Link to={`/courses/${c.course_id}`}>
                            View course
                            <ArrowUpRight size={14} className="ml-2" />
                          </Link>
                        </Button>
                      )}
                      {c.can_edit &&
                        ["instructor", "admin", "superadmin"].includes(
                          user?.role || "",
                        ) && (
                          <Button asChild size="sm">
                            <Link
                              to={`/${user?.role === "admin" || user?.role === "superadmin" ? "admin" : "instructor"}/courses/${c.course_id}/edit`}
                            >
                              Open editor
                            </Link>
                          </Button>
                        )}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <section className="campus-panel">
                <Empty
                  title="Bring your teaching together"
                  text={
                    staff
                      ? "Connect a course you teach, then assign it to a class. Existing course permissions and enrollment rules stay in place."
                      : "Courses will appear here when your institution assigns them to your batch."
                  }
                  action={
                    staff && (
                      <Button onClick={() => setDialog({ kind: "connect" })}>
                        Connect your first course
                      </Button>
                    )
                  }
                  icon={BookOpen}
                />
              </section>
            )}
          </>
        )}
        {section === "reports" && (
          <section className="campus-panel">
            <div className="campus-panel-heading">
              <div>
                <h2>Learning progress</h2>
                <p className="campus-muted">
                  Course completion across assigned batches.
                </p>
              </div>
              <div className="campus-actions">
                <select
                  aria-label="Filter report by batch"
                  className="campus-select"
                  value={reportBatch}
                  onChange={(e) => setReportBatch(e.target.value)}
                >
                  <option value="">All batches</option>
                  {data.batches.map((b) => (
                    <option value={b.id} key={b.id}>
                      {b.name}
                    </option>
                  ))}
                </select>
                {staff && (
                  <Button
                    variant="outline"
                    leftIcon={<Download size={15} />}
                    disabled={busy || !data.report.length}
                    onClick={() => void download()}
                  >
                    Export all batches
                  </Button>
                )}
              </div>
            </div>
            {report.length ? (
              <div className="campus-table-wrap">
                <table className="campus-table">
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>Course</th>
                      <th>Progress</th>
                      <th>Enrollment</th>
                      <th>Due</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.map((r) => (
                      <tr key={`${r.batch_id}-${r.user_id}-${r.course_id}`}>
                        <td>
                          <strong>{r.student}</strong>
                          <small>{r.batch}</small>
                        </td>
                        <td>{r.course}</td>
                        <td>
                          {r.progress}%<Progress value={r.progress} />
                        </td>
                        <td>
                          <span
                            className="campus-chip"
                            data-tone={r.has_access ? "success" : "muted"}
                          >
                            {r.has_access ? "Enrolled" : "Enrollment needed"}
                          </span>
                        </td>
                        <td>{r.due_date || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty
                title="Progress starts with participation"
                text="Add students to a batch and assign a course. Their existing course progress will appear here."
                icon={BarChart3}
              />
            )}
            <p className="campus-muted" style={{ marginTop: 20 }}>
              Assignment is separate from enrollment. Course completion measures
              activity; use assessments and delayed checks to evaluate
              understanding.
            </p>
          </section>
        )}
        {section === "plan" && manager && (
          <CampusBilling id={inst.id} owner={inst.role === "owner"} />
        )}
        {section === "plan" && manager && (
          <Plan
            data={data}
            request={(plan) => setDialog({ kind: "plan", plan })}
          />
        )}
        {section === "settings" && manager && <CampusBranding id={inst.id} />}
        {section === "settings" && manager && (
          <SettingsForm key={inst.id} data={data} saved={refresh} />
        )}
        {section === "trust" && manager && (
          <CampusControlPlane key={inst.id} id={inst.id} />
        )}
        {!visibleSections.some((s) => s.key === section) && (
          <section className="campus-panel">
            <Empty
              title="This section isn’t available"
              text="Choose a section available for your institution role."
              action={
                <Button asChild>
                  <Link to={base}>Back to overview</Link>
                </Button>
              }
            />
          </section>
        )}
      </>
    );
  };
  return (
    <DashboardWorkspace
      items={nav}
      role={user?.role as Role}
      homeTo="/institutions"
    >
      <div className="campus">
        {actionError && (
          <p role="alert" className="campus-error">
            {actionError}
          </p>
        )}
        {id && !tail ? <Navigate to={`${base}/overview`} replace /> : content()}
        {dialog && (
          <InstitutionDialog
            key={`${id}-${dialog.kind}-${dialog.batch?.id || dialog.member?.id || "new"}`}
            state={dialog}
            data={data}
            accountId={user?.id}
            close={() => setDialog(null)}
            changed={refresh}
          />
        )}
      </div>
    </DashboardWorkspace>
  );
}

function Plan({
  data,
  request,
}: {
  data: InstitutionOverview;
  request: (plan: string) => void;
}) {
  const pending = data.plan_requests.some((r) => r.status === "pending");
  return (
    <>
      <section className="campus-panel">
        <div className="campus-panel-heading">
          <div>
            <span className="campus-eyebrow">Your current plan</span>
            <h2 style={{ marginTop: 8 }} className="capitalize">
              {data.institution.plan}
            </h2>
          </div>
          <span className="campus-chip">
            <ShieldCheck size={13} /> Institution workspace
          </span>
        </div>
        <div className="campus-stats">
          {data.usage &&
            (["members", "batches", "courses"] as const).map((key) => (
              <div key={key}>
                <p className="campus-muted capitalize">{key}</p>
                <h3>
                  {data.usage![key]}{" "}
                  <span className="campus-muted">
                    / {data.usage!.limits[key]}
                  </span>
                </h3>
                <Progress
                  value={Math.min(
                    100,
                    (data.usage![key] / data.usage!.limits[key]) * 100,
                  )}
                />
              </div>
            ))}
        </div>
        <p className="campus-muted" style={{ marginTop: 18 }}>
          {data.usage?.reserved_seats || 0} seats reserved by pending
          invitations.
        </p>
      </section>
      <div className="campus-grid">
        {[
          {
            id: "starter",
            title: "Starter",
            subtitle: "Build your first connected campus",
            features: [
              "100 members",
              "10 academic batches",
              "20 campus or connected courses",
              "Progress reports and CSV exports",
            ],
          },
          {
            id: "campus",
            title: "Campus",
            subtitle: "Room for a growing institution",
            features: [
              "Request expanded capacity",
              "Plan your student rollout",
              "Discuss migration requirements",
              "Agree pricing before activation",
            ],
          },
          {
            id: "enterprise",
            title: "Enterprise",
            subtitle: "Plan a wider institutional rollout",
            features: [
              "Discuss multiple-campus needs",
              "Review identity integrations",
              "Agree support requirements",
              "Scope a deployment together",
            ],
          },
        ].map((p) => (
          <article
            key={p.id}
            className={`campus-panel campus-plan ${p.id === "campus" ? "campus-plan-featured" : ""}`}
          >
            <span className="campus-eyebrow">
              {p.id === data.institution.plan
                ? "Current plan"
                : "Plan a conversation"}
            </span>
            <h3 className="campus-plan-title">{p.title}</h3>
            <p className="campus-muted">{p.subtitle}</p>
            <ul>
              {p.features.map((f) => (
                <li key={f}>
                  <Check size={15} color="#a63a0b" />
                  {f}
                </li>
              ))}
            </ul>
            {p.id === "starter" ? (
              <span className="campus-chip">Included workspace</span>
            ) : (
              <Button
                variant={p.id === "campus" ? "default" : "outline"}
                disabled={pending || data.institution.role !== "owner"}
                onClick={() => request(p.id)}
              >
                {pending ? "Request pending" : `Request ${p.title}`}
              </Button>
            )}
          </article>
        ))}
      </div>
      {!!data.plan_requests.length && (
        <section className="campus-panel">
          <h2>Plan requests</h2>
          {data.plan_requests.map((r) => (
            <div key={r.id} className="campus-step">
              <CreditCard size={18} />
              <div className="campus-step-copy">
                <strong className="capitalize">{r.plan}</strong>
                <p>{new Date(r.created_at).toLocaleDateString()}</p>
              </div>
              <span className="campus-chip">{r.status}</span>
            </div>
          ))}
        </section>
      )}
      <p className="campus-notice">
        Requests are saved for platform review. No payment is collected and no
        paid subscription is activated here. Only the institution owner can
        request a plan.
      </p>
    </>
  );
}

function SettingsForm({
  data,
  saved,
}: {
  data: InstitutionOverview;
  saved: () => Promise<void>;
}) {
  const inst = data.institution;
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  return (
    <div className="campus-columns">
      <section className="campus-panel">
        <div className="campus-panel-heading">
          <h2>Institution profile</h2>
          <Settings size={18} />
        </div>
        <form
          className="campus-form"
          onSubmit={async (e) => {
            e.preventDefault();
            const form = new FormData(e.currentTarget);
            const text = (key: string) => String(form.get(key) || "").trim();
            setPending(true);
            setError("");
            try {
              await institutionApi.update(inst.id, {
                name: text("name"),
                kind: text("kind") as "school" | "college",
                academic_year: text("academic_year"),
                timezone: text("timezone"),
                description: text("description"),
              });
              await saved();
              toast.success("Institution profile saved");
            } catch (err) {
              setError(apiError(err));
            } finally {
              setPending(false);
            }
          }}
        >
          {error && (
            <p className="campus-error" role="alert">
              {error}
            </p>
          )}
          <label>
            Institution name
            <input
              name="name"
              defaultValue={inst.name}
              minLength={2}
              maxLength={160}
              required
            />
          </label>
          <div className="campus-form-grid">
            <label>
              Type
              <select name="kind" defaultValue={inst.kind}>
                <option value="school">School</option>
                <option value="college">College</option>
              </select>
            </label>
            <label>
              Academic year
              <input
                name="academic_year"
                defaultValue={inst.academic_year}
                minLength={4}
                maxLength={32}
                required
              />
            </label>
          </div>
          <label>
            Timezone
            <input
              name="timezone"
              defaultValue={inst.timezone}
              required
              maxLength={64}
            />
          </label>
          <label>
            About your institution
            <textarea
              name="description"
              defaultValue={inst.description}
              maxLength={1000}
            />
          </label>
          <Button
            loading={pending}
            type="submit"
            leftIcon={<Check size={15} />}
          >
            Save changes
          </Button>
        </form>
      </section>
      <section className="campus-panel">
        <div className="campus-panel-heading">
          <h2>Access and accountability</h2>
          <ShieldCheck size={20} />
        </div>
        <p className="campus-muted">
          Institution roles are independent of platform roles. Teachers can
          connect courses they teach. Administrators manage people and batches.
          Students see their own assigned learning.
        </p>
        <div className="campus-step">
          <span className="campus-icon">
            <Activity size={17} />
          </span>
          <div>
            <strong>Recent changes</strong>
            <p className="campus-muted">Your institution’s activity history</p>
          </div>
        </div>
        {data.activity.slice(0, 10).map((a) => (
          <div className="campus-activity" key={a.id}>
            <span className="campus-dot" />
            <div>
              <p>{a.detail}</p>
              <small>
                {a.action} · {new Date(a.created_at).toLocaleString()}
              </small>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
