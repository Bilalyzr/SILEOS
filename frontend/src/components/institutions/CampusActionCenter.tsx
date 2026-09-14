import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BellRing,
  BookOpenCheck,
  CalendarClock,
  Check,
  CheckCircle2,
  CircleDollarSign,
  ClipboardCheck,
  Clock3,
  GraduationCap,
  Megaphone,
  MessageCircle,
  RotateCcw,
  Sparkles,
  UserCheck,
  Users,
  type LucideIcon,
} from "lucide-react";
import toast from "react-hot-toast";
import type { InstitutionOverview } from "@/api/institutions";
import {
  type CampusOsRole,
  type TodayAction,
  type TodayMetric,
  useCampusToday,
  useUpdateTodayAction,
} from "@/api/campus-os";
import { PageBanner } from "@/components/design-system/PageBanner";
import { Button } from "@/components/ui/button";
import {
  CampusOsBadge,
  CampusOsEmpty,
  CampusOsError,
  CampusOsLoading,
  errorMessage,
  formatTime,
  readable,
} from "./CampusOsPrimitives";
import "@/styles/campus-os.css";

export interface CampusActionCenterProps {
  data: InstitutionOverview;
  role?: CampusOsRole;
  demo?: boolean;
}

const roleBanner: Record<CampusOsRole, { eyebrow: string; title: string; description: string }> = {
  owner: {
    eyebrow: "Campus command centre",
    title: "One clear view of what moves your campus today.",
    description: "Bring admissions, fees, teaching and family communication into one calm, actionable workspace.",
  },
  admin: {
    eyebrow: "Today at your campus",
    title: "See what needs attention. Move the day forward.",
    description: "Priorities from every office are arranged by urgency, owner and next action.",
  },
  teacher: {
    eyebrow: "Your teaching day",
    title: "Your classes, learners and next actions—ready when you are.",
    description: "Keep attendance, grading and learner support moving from one focused view.",
  },
  student: {
    eyebrow: "Your day at SashaInfinity",
    title: "A clear path through classes, tasks and progress.",
    description: "Pick up the right task, join what is next and finish the day with momentum.",
  },
  parent: {
    eyebrow: "Family view",
    title: "The updates that matter for your learner, together.",
    description: "See attendance, upcoming work, notices and fee actions without searching across screens.",
  },
  spoc: {
    eyebrow: "Programme action centre",
    title: "Every cohort signal and follow-up in one place.",
    description: "Keep learners, mentors and programme operations moving through the day.",
  },
};

function iconForMetric(metric: TodayMetric): LucideIcon {
  const key = metric.key.toLowerCase();
  if (key.includes("fee") || key.includes("payment")) return CircleDollarSign;
  if (key.includes("admission") || key.includes("applicant")) return UserCheck;
  if (key.includes("attendance")) return ClipboardCheck;
  if (key.includes("message")) return MessageCircle;
  if (key.includes("class")) return GraduationCap;
  if (key.includes("task") || key.includes("grading")) return BookOpenCheck;
  return Sparkles;
}

function iconForAction(action: TodayAction): LucideIcon {
  const kind = action.kind.toLowerCase();
  if (kind.includes("fee") || kind.includes("payment")) return CircleDollarSign;
  if (kind.includes("admission")) return UserCheck;
  if (kind.includes("attendance")) return ClipboardCheck;
  if (kind.includes("message") || kind.includes("communication")) return Megaphone;
  if (kind.includes("class")) return GraduationCap;
  return BellRing;
}

function safeInternalHref(href?: string | null) {
  return Boolean(href && href.startsWith("/") && !href.startsWith("//"));
}

export function CampusActionCenter({
  data,
  role,
  demo = false,
}: CampusActionCenterProps) {
  const viewerRole = role ?? data.institution.role;
  const query = useCampusToday(data.institution.id, {
    demo,
    role: viewerRole,
    institutionName: data.institution.name,
  });
  const updateAction = useUpdateTodayAction(data.institution.id, demo);
  const [showDone, setShowDone] = useState(false);
  const copy = roleBanner[viewerRole];
  const actions = useMemo(
    () =>
      (query.data?.actions ?? [])
        .filter((action) => showDone || action.status !== "done")
        .sort((a, b) => {
          const order = { urgent: 0, high: 1, normal: 2, low: 3 };
          return order[a.priority] - order[b.priority];
        }),
    [query.data?.actions, showDone],
  );

  async function setActionStatus(action: TodayAction, status: TodayAction["status"]) {
    try {
      await updateAction.mutateAsync({ actionId: action.id, status });
      toast.success(status === "done" ? "Action completed" : status === "snoozed" ? "Action snoozed" : "Action reopened");
    } catch (cause) {
      toast.error(errorMessage(cause, "We couldn’t update this action."));
    }
  }

  return (
    <section className="campus-os" aria-labelledby="campus-today-title">
      <div className="campus-os-banner">
        <PageBanner
          eyebrow={copy.eyebrow}
          title={copy.title}
          description={copy.description}
          share
          shareTitle={`${data.institution.name} · Today`}
          shareDescription="A clear view of today’s campus priorities on SashaInfinity."
          actions={
            demo ? (
              <CampusOsBadge>
                <Sparkles size={13} aria-hidden="true" /> Preview with sample data
              </CampusOsBadge>
            ) : undefined
          }
        />
      </div>

      {query.isPending && <CampusOsLoading label="Loading today’s campus priorities" />}
      {query.isError && (
        <CampusOsError
          message="Today’s campus view couldn’t be loaded. Your underlying records are safe."
          retry={() => void query.refetch()}
        />
      )}

      {query.data && (
        <>
          <div className="campus-os-metric-grid" aria-label="Today’s key numbers">
            {query.data.metrics.map((metric) => {
              const Icon = iconForMetric(metric);
              return (
                <article className="campus-os-metric" data-tone={metric.tone} key={metric.key}>
                  <div className="campus-os-metric-head">
                    <span>{metric.label}</span>
                    <span className="campus-os-metric-icon">
                      <Icon size={17} aria-hidden="true" />
                    </span>
                  </div>
                  <strong>{metric.value}</strong>
                  <footer>
                    {metric.trend && <span className="campus-os-trend">{metric.trend}</span>}
                    <span>{metric.detail}</span>
                  </footer>
                </article>
              );
            })}
          </div>

          <div className="campus-os-columns">
            <section className="campus-os-panel" aria-labelledby="campus-today-actions">
              <header className="campus-os-panel-head">
                <div>
                  <span className="campus-os-section-label">Priority queue</span>
                  <h2 id="campus-today-actions">What needs your attention</h2>
                  <p>{query.data.headline}</p>
                </div>
                <label className="flex items-center gap-2 text-xs text-stone-600">
                  <input
                    type="checkbox"
                    checked={showDone}
                    onChange={(event) => setShowDone(event.target.checked)}
                  />
                  Show completed
                </label>
              </header>
              <div className="campus-os-panel-body">
                {!actions.length ? (
                  <CampusOsEmpty
                    icon={CheckCircle2}
                    title="You’re caught up"
                    description="New actions will appear here when a learner, teacher or campus workflow needs you."
                  />
                ) : (
                  actions.map((action) => {
                    const Icon = iconForAction(action);
                    const canUpdate = action.id.startsWith("task-");
                    return (
                      <article className="campus-os-action" data-status={action.status} key={action.id}>
                        <span className="campus-os-priority" data-priority={action.priority} aria-label={`${action.priority} priority`} />
                        <div>
                          <div className="campus-os-action-head">
                            <h3 className="flex items-center gap-2">
                              <Icon size={15} aria-hidden="true" /> {action.title}
                            </h3>
                            <CampusOsBadge tone={action.priority === "urgent" ? "danger" : action.priority === "high" ? "warning" : "neutral"}>
                              {action.priority}
                            </CampusOsBadge>
                          </div>
                          <p>{action.detail}</p>
                          <div className="campus-os-action-meta">
                            {action.due_at && (
                              <span><Clock3 size={12} aria-hidden="true" /> Due {formatTime(action.due_at)}</span>
                            )}
                            {action.owner_name && <span><Users size={12} aria-hidden="true" /> {action.owner_name}</span>}
                            {action.status !== "open" && <span>{readable(action.status)}</span>}
                          </div>
                        </div>
                        <div className="campus-os-action-controls">
                          {action.status === "open" ? (
                            <>
                              {safeInternalHref(action.href) && (
                                <Button asChild size="sm" variant="outline" rightIcon={<ArrowRight size={14} />}>
                                  <Link to={action.href!}>{action.cta_label || "Open"}</Link>
                                </Button>
                              )}
                              {canUpdate && (
                                <>
                                  <button
                                    type="button"
                                    className="campus-os-icon-button"
                                    aria-label={`Mark ${action.title} complete`}
                                    title="Mark complete"
                                    disabled={updateAction.isPending}
                                    onClick={() => void setActionStatus(action, "done")}
                                  >
                                    <Check size={16} aria-hidden="true" />
                                  </button>
                                  <button
                                    type="button"
                                    className="campus-os-icon-button"
                                    aria-label={`Snooze ${action.title}`}
                                    title="Snooze"
                                    disabled={updateAction.isPending}
                                    onClick={() => void setActionStatus(action, "snoozed")}
                                  >
                                    <Clock3 size={15} aria-hidden="true" />
                                  </button>
                                </>
                              )}
                            </>
                          ) : canUpdate ? (
                            <button
                              type="button"
                              className="campus-os-icon-button"
                              aria-label={`Reopen ${action.title}`}
                              title="Reopen"
                              disabled={updateAction.isPending}
                              onClick={() => void setActionStatus(action, "open")}
                            >
                              <RotateCcw size={15} aria-hidden="true" />
                            </button>
                          ) : null}
                        </div>
                      </article>
                    );
                  })
                )}
              </div>
            </section>

            <aside className="campus-os-panel" aria-labelledby="campus-today-schedule">
              <header className="campus-os-panel-head">
                <div>
                  <span className="campus-os-section-label">Up next</span>
                  <h2 id="campus-today-schedule">Today’s schedule</h2>
                </div>
                <CalendarClock size={20} color="#a9360c" aria-hidden="true" />
              </header>
              <div className="campus-os-panel-body">
                {!query.data.schedule.length ? (
                  <CampusOsEmpty
                    icon={CalendarClock}
                    title="No scheduled items"
                    description="Classes, meetings and campus events for today will appear here."
                  />
                ) : (
                  query.data.schedule.map((item) => (
                    <div className="campus-os-schedule-item" key={item.id}>
                      <time className="campus-os-time" dateTime={item.starts_at}>{formatTime(item.starts_at)}</time>
                      <div>
                        <h3>{item.title}</h3>
                        <p>{[readable(item.kind), item.location].filter(Boolean).join(" · ")}</p>
                      </div>
                    </div>
                  ))
                )}
                {query.data.notices.map((notice) => (
                  <div className="campus-os-notice" key={notice.id}>
                    <Megaphone size={17} aria-hidden="true" />
                    <div>
                      <h3>{notice.title}</h3>
                      <p>{notice.detail}</p>
                      {safeInternalHref(notice.href) && (
                        <Link className="brand-text-link mt-2 inline-flex items-center gap-1 text-xs" to={notice.href!}>
                          View update <ArrowRight size={13} aria-hidden="true" />
                        </Link>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </aside>
          </div>
        </>
      )}
    </section>
  );
}

export default CampusActionCenter;
