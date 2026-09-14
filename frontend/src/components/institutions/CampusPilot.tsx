import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Bell,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  Download,
  Flag,
  GraduationCap,
  Megaphone,
  MessageCircle,
  Plus,
  Send,
  Settings2,
  ShieldCheck,
  Sparkles,
  Target,
  Trash2,
  Users,
} from "lucide-react";
import toast from "react-hot-toast";
import {
  campusApi,
  type CampusEvent,
  type CampusGoal,
  type CampusReportCard,
  type PilotStepKey,
} from "@/api/campus";
import type { InstitutionOverview } from "@/api/institutions";
import { BrandBanner } from "@/components/design-system/BrandBanner";
import { Button } from "@/components/ui/button";
import { useConfirm } from "@/components/ui/confirm";
import { GlassDialog } from "@/components/ui/dialog";
import { useAuthStore } from "@/store/auth";
import { apiError } from "./InstitutionDialog";

type Props = { data: InstitutionOverview };
type PilotView =
  | "onboarding"
  | "timetable"
  | "announcements"
  | "goals"
  | "reports"
  | "whatsapp";

const PILOT_VIEWS: { key: PilotView; label: string; icon: typeof Sparkles }[] = [
  { key: "onboarding", label: "Setup", icon: Sparkles },
  { key: "timetable", label: "Calendar", icon: CalendarDays },
  { key: "announcements", label: "Inbox", icon: Bell },
  { key: "goals", label: "Goals", icon: Target },
  { key: "reports", label: "Report cards", icon: GraduationCap },
  { key: "whatsapp", label: "WhatsApp", icon: MessageCircle },
];

const STEP_COPY: Record<PilotStepKey, string> = {
  profile: "Add the campus identity, timezone and banner your community will see.",
  branding: "Add the light-orange banner your community will recognize.",
  batches: "Create classes, years or cohorts for your learners.",
  staff: "Invite administrators and teachers with the right access.",
  students: "Import learners safely, previewing changes before they are applied.",
  term: "Confirm the academic term used across assessment and reports.",
  timetable: "Publish the first class, exam or campus event.",
  course: "Publish the first private course for your campus community.",
};

function isStaff(role: string) {
  return role === "owner" || role === "admin" || role === "teacher";
}

function isManager(role: string) {
  return role === "owner" || role === "admin";
}

function QueryState({
  loading,
  error,
  retry,
  label,
}: {
  loading: boolean;
  error: boolean;
  retry: () => void;
  label: string;
}) {
  if (loading)
    return <div className="campus-skeleton" role="status" aria-label={label} />;
  if (!error) return null;
  return (
    <div className="campus-error" role="alert">
      {label} could not be loaded. {" "}
      <button type="button" onClick={retry}>
        Retry
      </button>
    </div>
  );
}

function EmptyState({
  icon: Icon,
  title,
  text,
}: {
  icon: typeof Sparkles;
  title: string;
  text: string;
}) {
  return (
    <div className="campus-empty">
      <span className="campus-icon">
        <Icon size={22} />
      </span>
      <h2>{title}</h2>
      <p>{text}</p>
    </div>
  );
}

function friendlyDate(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleString([], {
        dateStyle: "medium",
        timeStyle: "short",
      });
}

function defaultLocalDateTime(hours: number) {
  const date = new Date(Date.now() + hours * 60 * 60 * 1000);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
}

export function CampusOnboarding({ data }: Props) {
  const { institution } = data;
  const manager = isManager(institution.role);
  const query = useQuery({
    queryKey: ["campus-pilot", institution.id],
    queryFn: () => campusApi.pilot(institution.id),
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function setDismissed(dismissed: boolean) {
    setBusy(true);
    setError("");
    try {
      await campusApi.updatePilot(institution.id, dismissed);
      await query.refetch();
      toast.success(dismissed ? "Setup guide hidden" : "Setup guide restored");
    } catch (cause) {
      setError(apiError(cause));
    } finally {
      setBusy(false);
    }
  }

  const progress = Math.max(0, Math.min(100, query.data?.progress ?? 0));
  return (
    <section className="campus space-y-5">
      <BrandBanner
        compact
        eyebrow="Campus launchpad"
        title="A confident first week starts with a clear setup."
        description="Move from campus profile to the first timetable and announcement with one guided checklist."
      />
      <QueryState
        loading={query.isLoading}
        error={query.isError}
        retry={() => void query.refetch()}
        label="Campus setup"
      />
      {error && (
        <p className="campus-error" role="alert">
          {error}
        </p>
      )}
      {query.data && (
        <div className="campus-panel">
          <div className="campus-toolbar">
            <div>
              <span className="campus-eyebrow">Pilot readiness</span>
              <h2 className="mt-2">
                {query.data.completed_steps} of {query.data.total_steps} ready
              </h2>
            </div>
            <span className="campus-chip" data-tone={progress === 100 ? "success" : undefined}>
              {progress}% complete
            </span>
          </div>
          <div className="campus-progress my-5" role="progressbar" aria-label="Campus setup progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}>
            <span style={{ width: `${progress}%` }} />
          </div>
          {!query.data.dismissed ? (
            <div>
              {query.data.steps.map((step, index) => (
                <div className="campus-step" key={step.key}>
                  <span className="campus-step-number">
                    {step.complete ? <Check size={15} /> : index + 1}
                  </span>
                  <div className="campus-step-copy">
                    <strong>{step.label}</strong>
                    <p>{STEP_COPY[step.key] || "Complete this step to keep your campus launch moving."}</p>
                  </div>
                  {step.complete ? (
                    <span className="campus-chip" data-tone="success">
                      <CheckCircle2 size={13} /> Ready
                    </span>
                  ) : step.href ? (
                    <a
                      className="brand-text-link"
                      href={
                        step.href.startsWith("/")
                          ? step.href
                          : `/institutions/${institution.id}/${step.href.replace(/^\/+/, "")}`
                      }
                    >
                      Continue <ChevronRight size={15} className="inline" />
                    </a>
                  ) : null}
                </div>
              ))}
              {manager && (
                <Button className="mt-4" variant="ghost" loading={busy} onClick={() => void setDismissed(true)}>
                  Hide setup guide
                </Button>
              )}
            </div>
          ) : (
            <div className="campus-notice">
              The setup guide is hidden. Your progress is still saved.
              {manager && (
                <Button className="ml-3" size="sm" variant="outline" loading={busy} onClick={() => void setDismissed(false)}>
                  Show guide
                </Button>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export function CampusTimetable({ data }: Props) {
  const { institution, batches, members } = data;
  const staff = isStaff(institution.role);
  const query = useQuery({
    queryKey: ["campus-events", institution.id],
    queryFn: () => campusApi.events(institution.id),
  });
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const confirm = useConfirm();
  const teachers = members.filter((member) => ["owner", "admin", "teacher"].includes(member.role));
  const events = useMemo(
    () => [...(query.data || [])].sort((a, b) => a.starts_at.localeCompare(b.starts_at)),
    [query.data],
  );

  async function create(form: HTMLFormElement) {
    const fields = new FormData(form);
    setBusy(true);
    setError("");
    try {
      const result = await campusApi.createEvent(institution.id, {
        title: String(fields.get("title")),
        kind: String(fields.get("kind")),
        starts_at: new Date(String(fields.get("starts"))).toISOString(),
        ends_at: new Date(String(fields.get("ends"))).toISOString(),
        batch_id: Number(fields.get("batch")) || null,
        teacher_member_id: Number(fields.get("teacher")) || null,
        location: String(fields.get("location") || ""),
        description: String(fields.get("description") || ""),
        recurrence: String(fields.get("recurrence")) as "none" | "daily" | "weekly",
        repeat_until: String(fields.get("repeat_until") || "") || null,
      });
      await query.refetch();
      setOpen(false);
      toast.success(`${result.created_count} calendar ${result.created_count === 1 ? "event" : "events"} added`);
    } catch (cause) {
      setError(apiError(cause));
    } finally {
      setBusy(false);
    }
  }

  async function remove(event: CampusEvent) {
    const accepted = await confirm({
      title: "Remove this calendar event?",
      body: event.series_id ? "Only this occurrence will be removed. The rest of the recurring series stays scheduled." : "The event will disappear from the campus calendar.",
      danger: true,
      confirmLabel: "Remove event",
    });
    if (!accepted) return;
    try {
      await campusApi.removeEvent(institution.id, event.id);
      await query.refetch();
      toast.success("Calendar event removed");
    } catch (cause) {
      setError(apiError(cause));
    }
  }

  return (
    <section className="campus space-y-5">
      <BrandBanner
        compact
        eyebrow="Timetable & campus calendar"
        title="Everyone knows where to be—and what comes next."
        description="Plan classes, exams, holidays and campus moments in one inviting calendar."
      >
        {staff && <Button leftIcon={<Plus size={16} />} onClick={() => setOpen(true)}>Add event</Button>}
      </BrandBanner>
      {error && <p className="campus-error" role="alert">{error}</p>}
      <QueryState loading={query.isLoading} error={query.isError} retry={() => void query.refetch()} label="Campus calendar" />
      {!query.isLoading && !events.length && <div className="campus-panel"><EmptyState icon={CalendarDays} title="Your calendar is ready for its first event" text="Add a class, examination, holiday or community event." /></div>}
      {!!events.length && (
        <div className="campus-grid">
          {events.map((event) => (
            <article className="campus-panel" key={event.id}>
              <div className="campus-toolbar">
                <span className="campus-chip">{event.kind}</span>
                {staff && event.can_edit !== false && (
                  <Button aria-label={`Remove ${event.title}`} size="icon" variant="ghost" onClick={() => void remove(event)}>
                    <Trash2 size={16} />
                  </Button>
                )}
              </div>
              <h3>{event.title}</h3>
              <p className="campus-muted">{friendlyDate(event.starts_at)} – {friendlyDate(event.ends_at)}</p>
              {event.batch_name && <p className="campus-muted mt-2"><Users size={14} className="mr-1 inline" />{event.batch_name}</p>}
              {event.location && <p className="campus-muted mt-2">{event.location}</p>}
              {event.substitute_name && <p className="campus-muted mt-2">Covered by {event.substitute_name}</p>}
              {event.description && <p className="mt-3 text-sm leading-6">{event.description}</p>}
            </article>
          ))}
        </div>
      )}
      <GlassDialog open={open} onOpenChange={setOpen} title="Add to the campus calendar" description="Schedule one event or create a short recurring series.">
        <form className="campus-form" onSubmit={(e) => { e.preventDefault(); void create(e.currentTarget); }}>
          {error && <p className="campus-error" role="alert">{error}</p>}
          <label>Event title<input name="title" required maxLength={160} /></label>
          <div className="campus-form-grid">
            <label>Type<select name="kind" defaultValue="class"><option value="class">Class</option><option value="exam">Exam</option><option value="holiday">Holiday</option><option value="event">Campus event</option></select></label>
            <label>Class or batch<select name="batch" defaultValue=""><option value="">Everyone</option>{batches.map((batch) => <option key={batch.id} value={batch.id}>{batch.name}</option>)}</select></label>
          </div>
          <div className="campus-form-grid">
            <label>Starts<input name="starts" type="datetime-local" defaultValue={defaultLocalDateTime(24)} required /></label>
            <label>Ends<input name="ends" type="datetime-local" defaultValue={defaultLocalDateTime(25)} required /></label>
          </div>
          <div className="campus-form-grid">
            <label>Teacher<select name="teacher" defaultValue=""><option value="">Not assigned</option>{teachers.map((teacher) => <option key={teacher.id} value={teacher.id}>{teacher.name}</option>)}</select></label>
            <label>Room or link<input name="location" maxLength={80} placeholder="Room 204 or meeting link" /></label>
          </div>
          <div className="campus-form-grid">
            <label>Repeats<select name="recurrence" defaultValue="none"><option value="none">Does not repeat</option><option value="daily">Every day</option><option value="weekly">Every week</option></select></label>
            <label>Repeat until<input name="repeat_until" type="date" /></label>
          </div>
          <label>Description<textarea name="description" maxLength={2000} /></label>
          <Button type="submit" loading={busy}>Add to calendar</Button>
        </form>
      </GlassDialog>
    </section>
  );
}

export function CampusAnnouncements({ data }: Props) {
  const { institution, batches } = data;
  const staff = isStaff(institution.role);
  const query = useQuery({
    queryKey: ["campus-announcements", institution.id],
    queryFn: () => campusApi.announcements(institution.id),
  });
  const attention = useQuery({
    queryKey: ["campus-notifications", institution.id],
    queryFn: () => campusApi.notifications(institution.id),
  });
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function create(form: HTMLFormElement) {
    const fields = new FormData(form);
    setBusy(true);
    setError("");
    try {
      await campusApi.createAnnouncement(institution.id, {
        title: String(fields.get("title")),
        body: String(fields.get("body")),
        batch_id: Number(fields.get("batch")) || null,
      });
      await query.refetch();
      setOpen(false);
      toast.success("Announcement published");
    } catch (cause) {
      setError(apiError(cause));
    } finally {
      setBusy(false);
    }
  }

  async function markRead(id: number) {
    try {
      await campusApi.readAnnouncement(institution.id, id);
      await query.refetch();
    } catch (cause) {
      setError(apiError(cause));
    }
  }

  return (
    <section className="campus space-y-5">
      <BrandBanner compact eyebrow="Announcements & inbox" title="The right update reaches the right people." description="Share campus news, class reminders and important notices in a calm, focused inbox.">
        {staff && <Button leftIcon={<Megaphone size={16} />} onClick={() => setOpen(true)}>New announcement</Button>}
      </BrandBanner>
      {error && <p className="campus-error" role="alert">{error}</p>}
      <section className="campus-panel">
        <div className="campus-panel-heading">
          <div>
            <h2>Needs attention</h2>
            <p className="campus-muted mt-2">Upcoming classes, deadlines, attendance signals and goals in one focused view.</p>
          </div>
          <ClipboardCheck size={20} />
        </div>
        <QueryState loading={attention.isLoading} error={attention.isError} retry={() => void attention.refetch()} label="Campus notifications" />
        {!attention.isLoading && !attention.data?.length && <p className="campus-muted">Nothing needs your attention right now.</p>}
        {attention.data?.slice(0, 8).map((item) => (
          <div className="campus-step" key={item.id}>
            <span className="campus-icon"><Bell size={16} /></span>
            <div className="campus-step-copy"><strong>{item.title}</strong><p>{item.detail}</p></div>
            <span className="campus-chip" data-tone={item.severity === "info" ? "muted" : undefined}>{item.severity}</span>
            {item.href && <a className="brand-text-link" href={item.href}>View →</a>}
          </div>
        ))}
      </section>
      <QueryState loading={query.isLoading} error={query.isError} retry={() => void query.refetch()} label="Announcements" />
      {!query.isLoading && !query.data?.length && <div className="campus-panel"><EmptyState icon={Bell} title="Your campus inbox is clear" text="New announcements will appear here with their audience and read status." /></div>}
      {!!query.data?.length && (
        <div className="space-y-4">
          {query.data.map((item) => (
            <article className="campus-panel" key={item.id}>
              <div className="campus-toolbar">
                <div className="campus-actions">
                  {!item.read_at && <span className="campus-chip"><span className="campus-dot" />New</span>}
                  <span className="campus-chip" data-tone="muted">{item.batch_name || item.audience}</span>
                </div>
                <time className="campus-muted">{friendlyDate(item.created_at)}</time>
              </div>
              <h3>{item.title}</h3>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6">{item.body}</p>
              <div className="campus-toolbar mt-4">
                <span className="campus-muted">{item.author_name ? `From ${item.author_name}` : "Campus announcement"}</span>
                {!item.read_at && <Button size="sm" variant="outline" onClick={() => void markRead(item.id)}>Mark as read</Button>}
              </div>
            </article>
          ))}
        </div>
      )}
      <GlassDialog open={open} onOpenChange={setOpen} title="Publish an announcement" description="People see this in their private campus inbox.">
        <form className="campus-form" onSubmit={(e) => { e.preventDefault(); void create(e.currentTarget); }}>
          {error && <p className="campus-error" role="alert">{error}</p>}
          <label>Headline<input name="title" required maxLength={160} /></label>
          <label>Audience<select name="batch" defaultValue=""><option value="">Everyone in the institution</option>{batches.map((batch) => <option key={batch.id} value={batch.id}>{batch.name}</option>)}</select></label>
          <label>Message<textarea name="body" required maxLength={5000} rows={6} /></label>
          <Button type="submit" loading={busy}>Publish announcement</Button>
        </form>
      </GlassDialog>
    </section>
  );
}

export function CampusGoals({ data }: Props) {
  const { institution, members } = data;
  const learner = institution.role === "student";
  const query = useQuery({ queryKey: ["campus-goals", institution.id], queryFn: () => campusApi.goals(institution.id) });
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const students = members.filter((member) => member.role === "student" && member.status === "active");

  async function create(form: HTMLFormElement) {
    const fields = new FormData(form);
    setBusy(true);
    setError("");
    try {
      await campusApi.createGoal(institution.id, {
        title: String(fields.get("title")),
        target_date: String(fields.get("target")),
        ...(learner ? {} : { member_id: Number(fields.get("student")) }),
      });
      await query.refetch();
      setOpen(false);
      toast.success("Learning goal created");
    } catch (cause) {
      setError(apiError(cause));
    } finally {
      setBusy(false);
    }
  }

  async function update(goal: CampusGoal, progress: number) {
    setError("");
    try {
      await campusApi.updateGoal(institution.id, goal.id, {
        progress,
        status: progress === 100 ? "completed" : "in_progress",
      });
      await query.refetch();
      toast.success(progress === 100 ? "Goal completed" : "Goal progress saved");
    } catch (cause) {
      setError(apiError(cause));
    }
  }

  return (
    <section className="campus space-y-5">
      <BrandBanner compact eyebrow="Learning goals" title={learner ? "Turn a big ambition into visible progress." : "Give every learner a goal worth returning to."} description={learner ? "Set a meaningful target, update it as you learn and celebrate every step forward." : "Create focused goals with learners and notice who may need a timely check-in."}>
        {(learner || isStaff(institution.role)) && <Button leftIcon={<Target size={16} />} onClick={() => setOpen(true)}>Create goal</Button>}
      </BrandBanner>
      {error && <p className="campus-error" role="alert">{error}</p>}
      <QueryState loading={query.isLoading} error={query.isError} retry={() => void query.refetch()} label="Learning goals" />
      {!query.isLoading && !query.data?.length && <div className="campus-panel"><EmptyState icon={Flag} title="A fresh goal can start here" text={learner ? "Choose one outcome that would make this term feel meaningful." : "Create a clear goal with a learner and review progress together."} /></div>}
      <div className="campus-grid">
        {query.data?.map((goal) => (
          <GoalCard key={goal.id} goal={goal} editable={learner || goal.can_edit === true} update={update} />
        ))}
      </div>
      <GlassDialog open={open} onOpenChange={setOpen} title="Create a learning goal" description="Keep it specific enough to recognize real progress.">
        <form className="campus-form" onSubmit={(e) => { e.preventDefault(); void create(e.currentTarget); }}>
          {error && <p className="campus-error" role="alert">{error}</p>}
          {!learner && <label>Learner<select name="student" required defaultValue=""><option value="" disabled>Choose a learner</option>{students.map((student) => <option key={student.id} value={student.id}>{student.name}</option>)}</select></label>}
          <label>Goal<input name="title" required maxLength={160} placeholder="Complete my algebra revision plan" /></label>
          <label>Target date<input name="target" type="date" required /></label>
          <Button type="submit" loading={busy}>Create goal</Button>
        </form>
      </GlassDialog>
    </section>
  );
}

function GoalCard({ goal, editable, update }: { goal: CampusGoal; editable: boolean; update: (goal: CampusGoal, progress: number) => Promise<void> }) {
  const [progress, setProgress] = useState(goal.progress);
  return (
    <article className="campus-panel">
      <div className="campus-toolbar">
        <span className="campus-chip" data-tone={goal.status === "completed" ? "success" : undefined}>{goal.status}</span>
        <strong>{progress}%</strong>
      </div>
      <h3>{goal.title}</h3>
      {goal.student_name && <p className="campus-muted">{goal.student_name}</p>}
      {goal.target_date && <p className="campus-muted mt-2">Target {new Date(`${goal.target_date}T00:00:00`).toLocaleDateString()}</p>}
      <div className="campus-progress my-4" role="progressbar" aria-label={`${goal.title} progress`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><span style={{ width: `${progress}%` }} /></div>
      {editable && (
        <div className="campus-form">
          <label>Update progress<input aria-label={`Progress for ${goal.title}`} type="range" min={0} max={100} step={5} value={progress} onChange={(event) => setProgress(Number(event.target.value))} /></label>
          <Button size="sm" variant="outline" disabled={progress === goal.progress} onClick={() => void update(goal, progress)}>Save progress</Button>
        </div>
      )}
    </article>
  );
}

export function CampusReportCards({ data }: Props) {
  const { institution, members } = data;
  const user = useAuthStore((state) => state.user);
  const staff = isStaff(institution.role);
  const manager = isManager(institution.role);
  const students = members.filter((member) => member.role === "student" && member.status === "active");
  const ownMember = students.find((member) => member.user_id === user?.id);
  const [memberId, setMemberId] = useState(staff ? students[0]?.id || 0 : ownMember?.id || 0);
  const [comment, setComment] = useState("");
  const [policyOpen, setPolicyOpen] = useState(false);
  const [bandsText, setBandsText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const report = useQuery({
    queryKey: ["campus-report-card", institution.id, memberId],
    queryFn: () => campusApi.reportCard(institution.id, memberId),
    enabled: memberId > 0,
  });
  const policy = useQuery({
    queryKey: ["campus-grading-policy", institution.id],
    queryFn: () => campusApi.gradingPolicy(institution.id),
    enabled: staff,
  });

  async function saveComment() {
    if (!report.data || report.data.term_id == null) return;
    setBusy(true);
    setError("");
    try {
      await campusApi.saveReportComment(institution.id, memberId, {
        term_id: report.data.term_id,
        overall_comment: comment,
      });
      await report.refetch();
      toast.success("Teacher comment saved");
    } catch (cause) {
      setError(apiError(cause));
    } finally {
      setBusy(false);
    }
  }

  async function download() {
    if (!report.data) return;
    setBusy(true);
    setError("");
    try {
      const blob = await campusApi.reportCardPdf(institution.id, memberId, report.data.term_id || undefined);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${report.data.student_name.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}-report-card.pdf`;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast.success("Report card downloaded");
    } catch (cause) {
      setError(apiError(cause));
    } finally {
      setBusy(false);
    }
  }

  function openPolicy() {
    setError("");
    setBandsText(
      (policy.data?.bands || [])
        .map((band) => `${band.label}: ${band.min_percent}`)
        .join("\n"),
    );
    setPolicyOpen(true);
  }

  async function savePolicy() {
    const bands = bandsText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const divider = line.lastIndexOf(":");
        return {
          label: divider < 1 ? "" : line.slice(0, divider).trim(),
          min_percent: Number(line.slice(divider + 1).trim()),
        };
      });
    if (
      !bands.length ||
      bands.some(
        (band) =>
          !band.label ||
          !Number.isFinite(band.min_percent) ||
          band.min_percent < 0 ||
          band.min_percent > 100,
      )
    ) {
      setError("Enter one grade per line as Label: minimum percent.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await campusApi.saveGradingPolicy(institution.id, { bands });
      await policy.refetch();
      setPolicyOpen(false);
      toast.success("Grading rules saved");
    } catch (cause) {
      setError(apiError(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="campus space-y-5">
      <BrandBanner compact eyebrow="Branded report cards" title="Make progress clear, personal and worth celebrating." description="Bring grades, attendance and thoughtful teacher feedback into one polished campus report.">
        {manager && <Button variant="outline" leftIcon={<Settings2 size={16} />} onClick={openPolicy}>Edit grading rules</Button>}
        {report.data && <Button leftIcon={<Download size={16} />} loading={busy} onClick={() => void download()}>Download PDF</Button>}
      </BrandBanner>
      <div className="campus-toolbar">
        {staff && <label className="campus-form">Learner<select className="campus-select" aria-label="Report card learner" value={memberId} onChange={(event) => { setMemberId(Number(event.target.value)); setComment(""); }}><option value={0}>Choose a learner</option>{students.map((student) => <option key={student.id} value={student.id}>{student.name}</option>)}</select></label>}
        {manager && policy.data && <div className="campus-actions" aria-label="Grading bands">{policy.data.bands.map((band) => <span className="campus-chip" key={`${band.label}-${band.min_percent}`}>{band.label} · {band.min_percent}%+</span>)}</div>}
      </div>
      {error && <p className="campus-error" role="alert">{error}</p>}
      {!memberId && <div className="campus-panel"><EmptyState icon={ClipboardCheck} title={staff ? "Choose a learner" : "No report card is available yet"} text={staff ? "Select a student to review their latest term report." : "Your term report will appear here when its assessments are ready."} /></div>}
      {memberId > 0 && <QueryState loading={report.isLoading} error={report.isError} retry={() => void report.refetch()} label="Report card" />}
      {report.data && <ReportCard report={report.data} staff={staff} comment={comment || report.data.overall_comment} setComment={setComment} save={saveComment} busy={busy} />}
      <GlassDialog open={policyOpen} onOpenChange={setPolicyOpen} title="Grading rules" description="Grades are calculated from the highest matching minimum percentage.">
        <div className="campus-form">
          {error && <p className="campus-error" role="alert">{error}</p>}
          <label>Grade bands<textarea aria-label="Grade bands" value={bandsText} onChange={(event) => setBandsText(event.target.value)} rows={8} placeholder={"A+: 90\nA: 80\nB: 70\nC: 60\nPass: 40\nNeeds support: 0"} /></label>
          <p className="campus-notice">Use one label and minimum percentage per line. The server checks the order, unique labels and complete 0–100 coverage before saving.</p>
          <Button loading={busy} onClick={() => void savePolicy()}>Save grading rules</Button>
        </div>
      </GlassDialog>
    </section>
  );
}

function ReportCard({ report, staff, comment, setComment, save, busy }: { report: CampusReportCard; staff: boolean; comment: string; setComment: (value: string) => void; save: () => Promise<void>; busy: boolean }) {
  return (
    <article className="campus-panel">
      <div className="campus-toolbar">
        <div><span className="campus-eyebrow">{report.term_name}</span><h2 className="mt-2">{report.student_name}</h2></div>
        <div className="campus-actions"><span className="campus-chip" data-tone={report.status === "complete" ? "success" : "muted"}>{report.status}</span>{report.attendance_percent != null && <span className="campus-chip">Attendance {report.attendance_percent}%</span>}</div>
      </div>
      <div className="campus-table-wrap my-5">
        <table className="campus-table"><thead><tr><th>Subject</th><th>Score</th><th>Grade</th><th>Teacher feedback</th></tr></thead><tbody>{report.rows.map((row, index) => <tr key={`${row.subject}-${index}`}><td>{row.subject}</td><td>{row.score == null ? "Not graded" : `${row.score} / ${row.max_score}`}</td><td><span className="campus-chip">{row.grade || "—"}</span></td><td>{row.comment || "—"}</td></tr>)}</tbody></table>
      </div>
      {staff ? <div className="campus-form"><label>Overall teacher comment<textarea aria-label="Overall teacher comment" maxLength={2000} value={comment} onChange={(event) => setComment(event.target.value)} /></label>{report.term_id == null && <p className="campus-notice">Create an academic term before saving a report-card comment.</p>}<Button className="justify-self-start" loading={busy} disabled={report.term_id == null} onClick={() => void save()}>Save teacher comment</Button></div> : <div className="campus-notice"><strong>Teacher comment</strong><p className="mt-2 whitespace-pre-wrap">{report.overall_comment || "Your teacher has not added an overall comment yet."}</p></div>}
    </article>
  );
}

function newCampaignRequestKey(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function CampusWhatsApp({ data }: Props) {
  const { institution, batches } = data;
  const manager = isManager(institution.role);
  const status = useQuery({ queryKey: ["campus-whatsapp-status", institution.id], queryFn: () => campusApi.whatsappStatus(institution.id) });
  const contacts = useQuery({ queryKey: ["campus-whatsapp-contacts", institution.id], queryFn: () => campusApi.whatsappContacts(institution.id), enabled: manager });
  const campaigns = useQuery({ queryKey: ["campus-whatsapp-campaigns", institution.id], queryFn: () => campusApi.whatsappCampaigns(institution.id), enabled: manager });
  const [campaign, setCampaign] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [campaignRequestKey, setCampaignRequestKey] = useState(() =>
    newCampaignRequestKey(`campus-${institution.id}`),
  );
  const canSend = Boolean(
    status.data?.configured &&
      status.data.webhook_ready &&
      status.data.approved_templates.length,
  );

  async function createCampaign(form: HTMLFormElement) {
    const fields = new FormData(form);
    const parameters = String(fields.get("parameters") || "")
      .split("\n")
      .map((value) => value.trim())
      .filter(Boolean);
    if (parameters.length > 10 || parameters.some((value) => value.length > 256)) {
      setError("Use at most 10 template parameters, with no more than 256 characters on each line.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await campusApi.createWhatsAppCampaign(institution.id, {
        request_key: campaignRequestKey,
        template: String(fields.get("template")),
        language: String(fields.get("language")),
        parameters,
        batch_id: Number(fields.get("batch")) || null,
        header_image_url: String(fields.get("banner")) || null,
      });
      setCampaignRequestKey(newCampaignRequestKey(`campus-${institution.id}`));
      await campaigns.refetch();
      setCampaign(false);
      toast.success("WhatsApp campaign queued once");
    } catch (cause) {
      setError(apiError(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="campus space-y-5">
      <BrandBanner compact eyebrow="WhatsApp communication" title="Useful campus updates, sent with consent." description="Connect the official Meta WhatsApp Cloud API, use approved templates and see delivery without turning trust into noise.">
        {manager && canSend && <Button leftIcon={<Send size={16} />} onClick={() => setCampaign(true)}>New campaign</Button>}
      </BrandBanner>
      {error && <p className="campus-error" role="alert">{error}</p>}
      <QueryState loading={status.isLoading} error={status.isError} retry={() => void status.refetch()} label="WhatsApp integration" />
      {status.data && (
        <div className="campus-stats">
          <div className="campus-panel campus-stat"><div className="campus-stat-top"><span>Provider setup</span><ShieldCheck size={17} /></div><strong>{status.data.configured ? "Ready" : "Needed"}</strong><small>Meta Cloud API {status.data.api_version}</small></div>
          <div className="campus-panel campus-stat"><div className="campus-stat-top"><span>Webhook endpoint</span><MessageCircle size={17} /></div><strong>{status.data.webhook_ready ? "Ready" : "Pending"}</strong><small>Ready means the callback is configured; Meta verification is checked during deployment</small></div>
          <div className="campus-panel campus-stat"><div className="campus-stat-top"><span>Sending number</span><Send size={17} /></div><strong>{status.data.phone_number_configured && status.data.business_phone_configured ? "Linked" : "Not linked"}</strong><small>{status.data.business_account_configured ? "Business account connected" : "Business account needed"}</small></div>
          <div className="campus-panel campus-stat"><div className="campus-stat-top"><span>Campaigns</span><Megaphone size={17} /></div><strong>{canSend ? "Enabled" : "Paused"}</strong><small>{status.data.approved_templates.length} approved templates</small></div>
        </div>
      )}
      {status.data && !canSend && <div className="campus-notice"><strong>Finish the server connection before sending.</strong><p className="mt-2">Configure the Meta access token, phone-number ID, business account ID, verify token and app secret. Then verify the webhook in Meta Business Manager.</p>{!!status.data.missing_fields.length && <p className="mt-2">Missing: {status.data.missing_fields.join(", ")}</p>}</div>}
      {status.data && <section className="campus-panel"><div className="campus-panel-heading"><div><h2>My WhatsApp preference</h2><p className="campus-muted mt-2">Your WhatsApp permission belongs to your SashaInfinity account and applies across every campus, course and service.</p></div><span className="campus-chip" data-tone={status.data.opted_in ? "success" : "muted"}>{status.data.contact_status.replace(/_/g, " ")}</span></div><div className="campus-actions mt-4"><Button asChild><Link to="/communication-preferences">Manage my account preference</Link></Button>{status.data.join_url && <a className="sf-primary" href={status.data.join_url} target="_blank" rel="noreferrer">Open WhatsApp to confirm</a>}</div><p className="campus-notice mt-4">Campus managers can review permission for their audience, but only each account owner can opt in or withdraw.</p></section>}
      {manager && (
        <>
          <section className="campus-panel">
            <div className="campus-panel-heading"><div><h2>Consent directory</h2><p className="campus-muted mt-2">A person is included only after their permission is recorded.</p></div><ShieldCheck size={20} /></div>
            <QueryState loading={contacts.isLoading} error={contacts.isError} retry={() => void contacts.refetch()} label="WhatsApp contacts" />
            <div className="campus-table-wrap"><table className="campus-table"><thead><tr><th>Person</th><th>Number</th><th>Consent</th></tr></thead><tbody>{contacts.data?.map((contact) => <tr key={contact.member_id}><td>{contact.name}<small>{contact.member_status}</small></td><td>{contact.phone || "Not added"}</td><td><span className="campus-chip" data-tone={contact.status === "confirmed" ? "success" : "muted"}>{contact.status === "confirmed" ? "Opted in" : contact.status.replace(/_/g, " ")}</span></td></tr>)}</tbody></table></div>
            <p className="campus-notice mt-4">Each member records or withdraws their own permission. Campus managers can review consent but cannot grant it for someone else.</p>
          </section>
          <section className="campus-panel">
            <div className="campus-panel-heading"><div><h2>Campaign delivery</h2><p className="campus-muted mt-2">Live counts come from signed WhatsApp webhook receipts.</p></div><Megaphone size={20} /></div>
            <QueryState loading={campaigns.isLoading} error={campaigns.isError} retry={() => void campaigns.refetch()} label="WhatsApp campaigns" />
            {!campaigns.isLoading && !campaigns.data?.length && <EmptyState icon={MessageCircle} title="No campaigns sent yet" text="Your first approved-template campaign and its delivery results will appear here." />}
            {campaigns.data?.map((item) => <div className="campus-step" key={item.id}><span className="campus-icon"><MessageCircle size={17} /></span><div className="campus-step-copy"><strong>{item.template}</strong><p>{friendlyDate(item.created_at)} · {item.status}</p></div><div className="campus-actions"><span className="campus-chip">Queued {item.queued}</span><span className="campus-chip">Sent {item.sent}</span><span className="campus-chip" data-tone="success">Delivered {item.delivered}</span><span className="campus-chip">Read {item.read}</span>{item.failed > 0 && <span className="campus-chip">Failed {item.failed}</span>}</div></div>)}
          </section>
        </>
      )}
      <GlassDialog open={campaign} onOpenChange={setCampaign} title="Create a WhatsApp campaign" description="The server sends one idempotent campaign to opted-in recipients using an approved Meta template.">
        <form className="campus-form" onSubmit={(e) => { e.preventDefault(); void createCampaign(e.currentTarget); }}>
          {error && <p className="campus-error" role="alert">{error}</p>}
          <label>Approved template name{status.data?.approved_templates?.length ? <select name="template" required defaultValue=""><option value="" disabled>Choose an approved template</option>{status.data.approved_templates.map((template) => <option key={template} value={template}>{template}</option>)}</select> : <input name="template" required maxLength={120} placeholder="campus_weekly_update" />}</label>
          <div className="campus-form-grid"><label>Template language<input name="language" required defaultValue="en" maxLength={20} /></label><label>Audience<select name="batch" defaultValue=""><option value="">All opted-in contacts</option>{batches.map((batch) => <option value={batch.id} key={batch.id}>{batch.name}</option>)}</select></label></div>
          <label>Template parameters, one per line<textarea name="parameters" maxLength={2560} placeholder={"Greenwood Campus\nFriday, 4:00 PM"} /></label>
          <label>Approved header banner URL<input name="banner" type="url" maxLength={500} placeholder="https://cdn.example.edu/campus-update.png" /></label>
          <p className="campus-notice">Use the same light-orange campus banner as the header image after it is hosted on an HTTPS address that Meta can fetch.</p>
          <Button type="submit" loading={busy} disabled={!canSend}>Queue campaign once</Button>
        </form>
      </GlassDialog>
    </section>
  );
}

export function CampusPilot({ data }: Props) {
  const manager = isManager(data.institution.role);
  const visibleViews = manager
    ? PILOT_VIEWS
    : PILOT_VIEWS.filter((item) => item.key !== "onboarding");
  const [view, setView] = useState<PilotView>(
    manager
      ? "onboarding"
      : data.institution.role === "student"
        ? "goals"
        : "announcements",
  );
  return (
    <section className="campus">
      <nav className="campus-tabs" aria-label="Campus pilot tools">
        {visibleViews.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.key}
              type="button"
              aria-current={view === item.key ? "page" : undefined}
              className={`flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-bold ${view === item.key ? "bg-orange-100 text-orange-900 shadow-sm" : "text-stone-600 hover:bg-orange-50"}`}
              onClick={() => setView(item.key)}
            >
              <Icon size={15} /> {item.label}
            </button>
          );
        })}
      </nav>
      {view === "onboarding" && <CampusOnboarding data={data} />}
      {view === "timetable" && <CampusTimetable data={data} />}
      {view === "announcements" && <CampusAnnouncements data={data} />}
      {view === "goals" && <CampusGoals data={data} />}
      {view === "reports" && <CampusReportCards data={data} />}
      {view === "whatsapp" && <CampusWhatsApp data={data} />}
    </section>
  );
}
