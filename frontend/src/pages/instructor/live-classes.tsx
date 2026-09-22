import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Instructor Live Classes dashboard — Upcoming / Live / Past tabs with a
 * prominent Start button, per the plan's binding behavior. No page-level
 * shell: this route renders inside InstructorLayout (see courses.tsx for
 * the same convention).
 *
 * I-H1 (Batch 2): edit/cancel actions for scheduled classes — the backend
 * PATCH/DELETE always existed but had zero UI callers.
 * M-11 (Batch 2): "Add to calendar" .ics download button — the endpoint
 * requires the bearer token, so this fetches the .ics as a blob rather
 * than using a plain <a href>.
 */
import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import {
  Video,
  Plus,
  Radio,
  Pencil,
  Ban,
  CalendarPlus,
  X,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LiveStatusBadge } from "@/components/live/LiveStatusBadge";
import { joinButtonState } from "@/components/live/joinButtonState";
import {
  listLiveClasses,
  startLiveClass,
  updateLiveClass,
  cancelLiveClass,
  fetchCalendarIcs,
  type LiveClassOut,
  type LiveClassScope,
  type LiveClassUpdateIn,
} from "@/api/liveClasses";

type TabKey = "upcoming" | "live" | "past";

const TABS: { key: TabKey; label: string; scope: LiveClassScope }[] = [
  { key: "upcoming", label: "Upcoming", scope: "upcoming" },
  { key: "live", label: "Live", scope: "live" },
  { key: "past", label: "Past", scope: "past" },
];

const TIMEZONES = [
  "Asia/Kolkata",
  "Asia/Dubai",
  "Asia/Singapore",
  "Europe/London",
  "America/New_York",
  "America/Los_Angeles",
  "UTC",
];

function formatScheduled(iso: string, timezone: string): string {
  try {
    return new Intl.DateTimeFormat("en-IN", {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZone: timezone,
    }).format(new Date(iso));
  } catch {
    return new Date(iso).toLocaleString();
  }
}

/** Converts a <input type="datetime-local"> value (no timezone, interpreted
 * in the selected `timezone`) into an ISO-8601 instant. Mirrors
 * live-class-new.tsx's localDateTimeToIso exactly. */
function localDateTimeToIso(localValue: string, timezone: string): string {
  const dtf = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  const asUtc = new Date(localValue + "Z");
  const parts = dtf.formatToParts(asUtc);
  const get = (type: string) =>
    parts.find((p) => p.type === type)?.value || "0";
  const readsAs = Date.UTC(
    Number(get("year")),
    Number(get("month")) - 1,
    Number(get("day")),
    Number(get("hour")),
    Number(get("minute")),
    Number(get("second")),
  );
  const offsetMs = readsAs - asUtc.getTime();
  const correctedUtcMs = asUtc.getTime() - offsetMs;
  return new Date(correctedUtcMs).toISOString();
}

/** Inverse of localDateTimeToIso — renders an ISO instant as the
 * datetime-local wall-clock string it reads as in `timezone`, so the edit
 * form pre-fills with the class's existing scheduled time. */
function isoToLocalDateTimeInput(iso: string, timezone: string): string {
  const dtf = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
  const parts = dtf.formatToParts(new Date(iso));
  const get = (type: string) =>
    parts.find((p) => p.type === type)?.value || "00";
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
}

function minutesBetween(startIso: string, endIso: string): number {
  return Math.max(
    15,
    Math.round(
      (new Date(endIso).getTime() - new Date(startIso).getTime()) / 60000,
    ),
  );
}

// ---------------------------------------------------------------------------
// Edit modal
// ---------------------------------------------------------------------------

function EditClassModal({
  cls,
  onClose,
  onSaved,
}: {
  cls: LiveClassOut;
  onClose: () => void;
  onSaved: (updated: LiveClassOut) => void;
}) {
  const [title, setTitle] = React.useState(cls.title);
  const [description, setDescription] = React.useState(cls.description || "");
  const [timezone, setTimezone] = React.useState(cls.timezone);
  const [scheduledStartLocal, setScheduledStartLocal] = React.useState(() =>
    isoToLocalDateTimeInput(cls.scheduled_start, cls.timezone),
  );
  const [durationMinutes, setDurationMinutes] = React.useState(() =>
    minutesBetween(cls.scheduled_start, cls.scheduled_end),
  );
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!title.trim()) {
      setError("Please enter a title");
      return;
    }
    if (!scheduledStartLocal) {
      setError("Please choose a date and time");
      return;
    }
    setSubmitting(true);
    try {
      const payload: LiveClassUpdateIn = {
        title: title.trim(),
        description: description.trim() || null,
        scheduled_start: localDateTimeToIso(scheduledStartLocal, timezone),
        duration_minutes: durationMinutes,
        timezone,
      };
      const updated = await updateLiveClass(cls.id, payload);
      toast.success("Class updated");
      onSaved(updated);
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail || err?.message || "Failed to update class";
      setError(detail);
      toast.error(detail);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        data-glass="work"
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 sticky top-0 bg-white">
          <p className="font-semibold text-gray-900">Edit class</p>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="text-gray-400 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <p className="text-sm text-danger-600 bg-danger-50 border border-danger-200 rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Date &amp; time
              </label>
              <input
                type="datetime-local"
                value={scheduledStartLocal}
                onChange={(e) => setScheduledStartLocal(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Timezone
              </label>
              <select
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>
                    {tz}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Duration (minutes)
            </label>
            <input
              type="number"
              min={15}
              max={480}
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(Number(e.target.value))}
              className="w-full sm:w-40 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Saving…" : "Save changes"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Cancel confirm modal
// ---------------------------------------------------------------------------

function CancelClassModal({
  cls,
  onClose,
  onCancelled,
}: {
  cls: LiveClassOut;
  onClose: () => void;
  onCancelled: (id: number) => void;
}) {
  const [submitting, setSubmitting] = React.useState(false);

  const handleConfirm = async () => {
    setSubmitting(true);
    try {
      await cancelLiveClass(cls.id);
      toast.success("Class cancelled");
      onCancelled(cls.id);
    } catch (err: any) {
      toast.error(
        err?.response?.data?.detail || err?.message || "Failed to cancel class",
      );
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        data-glass="content"
      >
        <div className="flex items-center gap-2 text-amber-600 mb-3">
          <AlertTriangle className="w-5 h-5" />
          <p className="font-semibold text-gray-900">Cancel this class?</p>
        </div>
        <p className="text-sm text-gray-600 mb-5">
          &ldquo;{cls.title}&rdquo; will be cancelled and removed from the
          schedule. Enrolled students will no longer be able to join. This
          cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Keep class
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={submitting}
          >
            {submitting ? "Cancelling…" : "Cancel class"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function InstructorLiveClassesPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = React.useState<TabKey>("upcoming");
  const [classes, setClasses] = React.useState<LiveClassOut[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [startingId, setStartingId] = React.useState<number | null>(null);
  const [editingClass, setEditingClass] = React.useState<LiveClassOut | null>(
    null,
  );
  const [cancellingClass, setCancellingClass] =
    React.useState<LiveClassOut | null>(null);
  const [icsDownloadingId, setIcsDownloadingId] = React.useState<number | null>(
    null,
  );

  const load = React.useCallback(async (tab: TabKey) => {
    const scope = TABS.find((t) => t.key === tab)!.scope;
    try {
      setLoading(true);
      setError(null);
      const res = await listLiveClasses({ scope, page_size: 50 });
      setClasses(res.items);
    } catch (err: any) {
      setError(err?.message || "Failed to load your live classes");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    load(activeTab);
  }, [activeTab, load]);

  const handleStart = async (cls: LiveClassOut) => {
    setStartingId(cls.id);
    try {
      await startLiveClass(cls.id);
      navigate(`/instructor/live-classes/${cls.id}/console`);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail || err?.message || "Failed to start class",
      );
      setStartingId(null);
    }
  };

  const handleDownloadIcs = async (cls: LiveClassOut) => {
    setIcsDownloadingId(cls.id);
    try {
      const blob = await fetchCalendarIcs(cls.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${cls.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase() || "live-class"}.ics`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      toast.error(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to download calendar invite",
      );
    } finally {
      setIcsDownloadingId(null);
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="dash-h1 mb-1">Live Classes</h1>
            <p className="text-slate-600 text-sm">
              Schedule and run interactive live sessions for your courses
            </p>
          </div>
          <Link to="/instructor/live-classes/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Schedule class
            </Button>
          </Link>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-live-classes"
    >
      <div className="flex gap-1 mb-6 border-b border-slate-200">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
              activeTab === key
                ? "border-primary-500 text-primary-700"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {label}
            {key === "live" && classes.length > 0 && activeTab === "live" && (
              <Radio className="inline h-3 w-3 ml-1.5 text-danger-500" />
            )}
          </button>
        ))}
      </div>
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-4 space-y-3">
              <div className="h-4 w-3/4 dash-skeleton" />
              <div className="h-3 w-1/2 dash-skeleton" />
              <div className="h-8 w-full dash-skeleton" />
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card className="p-8 text-center">
          <p className="text-sm text-danger-600 mb-3">{error}</p>
          <Button variant="outline" onClick={() => load(activeTab)}>
            Try again
          </Button>
        </Card>
      ) : classes.length === 0 ? (
        <Card className="p-12 text-center">
          <Video className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {activeTab === "upcoming" && "No upcoming classes"}
            {activeTab === "live" && "No classes live right now"}
            {activeTab === "past" && "No past classes yet"}
          </h3>
          {activeTab !== "live" && (
            <p className="text-gray-600 mb-6">
              Schedule a live class to get started.
            </p>
          )}
          {activeTab === "upcoming" && (
            <Link to="/instructor/live-classes/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Schedule class
              </Button>
            </Link>
          )}
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {classes.map((cls) => {
            const state = joinButtonState(cls, new Date(), true);
            const isScheduled = cls.status === "scheduled";
            return (
              <Card key={cls.id} className="p-4 flex flex-col gap-3">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-base font-semibold text-secondary-900 line-clamp-2">
                    {cls.title}
                  </h3>
                  <LiveStatusBadge status={cls.status} />
                </div>
                <p className="text-xs text-slate-500">
                  {formatScheduled(cls.scheduled_start, cls.timezone)}
                </p>

                {isScheduled && (
                  <div className="flex gap-1.5 -mt-1">
                    <button
                      type="button"
                      onClick={() => setEditingClass(cls)}
                      className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-primary-700 px-2 py-1 rounded hover:bg-slate-50"
                    >
                      <Pencil className="h-3 w-3" /> Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => setCancellingClass(cls)}
                      className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-danger-700 px-2 py-1 rounded hover:bg-slate-50"
                    >
                      <Ban className="h-3 w-3" /> Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDownloadIcs(cls)}
                      disabled={icsDownloadingId === cls.id}
                      className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-primary-700 px-2 py-1 rounded hover:bg-slate-50 disabled:opacity-50"
                    >
                      <CalendarPlus className="h-3 w-3" />
                      {icsDownloadingId === cls.id
                        ? "Downloading…"
                        : "Add to calendar"}
                    </button>
                  </div>
                )}

                <div className="mt-auto pt-2 flex gap-2">
                  {cls.status === "scheduled" && (
                    <Button
                      className="flex-1"
                      onClick={() => handleStart(cls)}
                      disabled={startingId === cls.id}
                    >
                      <Video className="h-4 w-4 mr-1.5" />
                      {startingId === cls.id ? "Starting…" : "Start class"}
                    </Button>
                  )}
                  {cls.status === "live" && (
                    <Link
                      to={`/instructor/live-classes/${cls.id}/console`}
                      className="flex-1"
                    >
                      <Button className="w-full" variant="destructive">
                        <Radio className="h-4 w-4 mr-1.5" />
                        Rejoin — LIVE
                      </Button>
                    </Link>
                  )}
                  {cls.status === "ended" && (
                    <Link
                      to={`/instructor/live-classes/${cls.id}/report`}
                      className="flex-1"
                    >
                      <Button className="w-full" variant="outline">
                        View report
                      </Button>
                    </Link>
                  )}
                  {cls.status === "cancelled" && (
                    <Button className="flex-1" disabled variant="ghost">
                      {state.label}
                    </Button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
      {editingClass && (
        <EditClassModal
          cls={editingClass}
          onClose={() => setEditingClass(null)}
          onSaved={(updated) => {
            setClasses((prev) =>
              prev.map((c) => (c.id === updated.id ? updated : c)),
            );
            setEditingClass(null);
          }}
        />
      )}
      {cancellingClass && (
        <CancelClassModal
          cls={cancellingClass}
          onClose={() => setCancellingClass(null)}
          onCancelled={(id) => {
            setClasses((prev) => prev.filter((c) => c.id !== id));
            setCancellingClass(null);
          }}
        />
      )}
    </PageLayout>
  );
}

export default InstructorLiveClassesPage;
