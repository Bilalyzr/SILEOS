import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * New live class schedule form — per spec §8: course select (reusing the
 * instructor's own-courses source from pages/instructor/courses.tsx),
 * datetime-local + timezone select (default Asia/Kolkata), weekly
 * recurrence day-chips + weeks count, and settings toggles.
 */
import * as React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Video } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/api/axios";
import { createLiveClass, type LiveClassSettings } from "@/api/liveClasses";

interface InstructorCourseOption {
  id: number;
  title: string;
}

const TIMEZONES = [
  "Asia/Kolkata",
  "Asia/Dubai",
  "Asia/Singapore",
  "Europe/London",
  "America/New_York",
  "America/Los_Angeles",
  "UTC",
];

const WEEKDAYS: { code: string; label: string }[] = [
  { code: "MO", label: "Mon" },
  { code: "TU", label: "Tue" },
  { code: "WE", label: "Wed" },
  { code: "TH", label: "Thu" },
  { code: "FR", label: "Fri" },
  { code: "SA", label: "Sat" },
  { code: "SU", label: "Sun" },
];

const DEFAULT_SETTINGS: LiveClassSettings = {
  lobby_enabled: true,
  start_muted: true,
  allow_chat: true,
  allow_share: true,
  record: false,
  attendance_threshold_pct: 60,
};

/** Converts a <input type="datetime-local"> value (no timezone, interpreted
 * in the selected `timezone`) into an ISO-8601 instant. Because the browser
 * has no reliable "parse this wall-clock time in an arbitrary IANA zone"
 * primitive, we compute the target zone's current UTC offset via
 * Intl.DateTimeFormat and apply it — good enough for the offsets in
 * TIMEZONES (none observe exotic sub-hour DST transitions mid-form-fill). */
function localDateTimeToIso(localValue: string, timezone: string): string {
  // Determine the target timezone's offset at this instant using the Intl
  // API's formatToParts trick: treat localValue as UTC, find what that
  // instant reads as in `timezone`, then correct by the difference — this
  // yields "the same wall-clock numbers, interpreted as being in `timezone`".
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

export function InstructorLiveClassNewPage() {
  const navigate = useNavigate();
  const [courses, setCourses] = React.useState<InstructorCourseOption[]>([]);
  const [coursesLoading, setCoursesLoading] = React.useState(true);

  // WP6 Schedule Builder deep-links here with ?course_id=
  const [courseId, setCourseId] = React.useState<number | "">(() => {
    const q = Number(
      new URLSearchParams(window.location.search).get("course_id"),
    );
    return q > 0 ? q : "";
  });
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [scheduledStartLocal, setScheduledStartLocal] = React.useState("");
  const [durationMinutes, setDurationMinutes] = React.useState(60);
  const [timezone, setTimezone] = React.useState("Asia/Kolkata");
  const [recurrenceEnabled, setRecurrenceEnabled] = React.useState(false);
  const [selectedDays, setSelectedDays] = React.useState<string[]>([]);
  const [weeks, setWeeks] = React.useState(4);
  const [settings, setSettings] =
    React.useState<LiveClassSettings>(DEFAULT_SETTINGS);

  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    async function loadCourses() {
      try {
        const response = await api.get("/courses/my-courses", {
          params: { page: 1, page_size: 100 },
        });
        if (cancelled) return;
        const list = (response.data.courses || []).map((c: any) => ({
          id: c.id,
          title: c.post_title || c.title || `Course #${c.id}`,
        }));
        setCourses(list);
      } catch {
        if (!cancelled) setError("Failed to load your courses");
      } finally {
        if (!cancelled) setCoursesLoading(false);
      }
    }
    loadCourses();
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleDay = (code: string) => {
    setSelectedDays((prev) =>
      prev.includes(code) ? prev.filter((d) => d !== code) : [...prev, code],
    );
  };

  const toggleSetting = (key: keyof LiveClassSettings) => {
    setSettings((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!courseId) {
      setError("Please select a course");
      return;
    }
    if (!title.trim()) {
      setError("Please enter a title");
      return;
    }
    if (!scheduledStartLocal) {
      setError("Please choose a date and time");
      return;
    }
    if (recurrenceEnabled && selectedDays.length === 0) {
      setError("Select at least one day for weekly recurrence");
      return;
    }

    setSubmitting(true);
    try {
      const scheduledStartIso = localDateTimeToIso(
        scheduledStartLocal,
        timezone,
      );
      await createLiveClass({
        course_id: Number(courseId),
        title: title.trim(),
        description: description.trim() || undefined,
        scheduled_start: scheduledStartIso,
        duration_minutes: durationMinutes,
        timezone,
        recurrence_weekly: recurrenceEnabled ? selectedDays : undefined,
        weeks: recurrenceEnabled ? weeks : undefined,
        settings,
      });
      navigate("/instructor/live-classes");
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to schedule the class",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="dash-h1 mb-1">Schedule a live class</h1>
          <p className="text-slate-600 text-sm">
            Set up a Jitsi-powered session for your students in one form.
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-live-class-new"
    >
      <button
        onClick={() => navigate("/instructor/live-classes")}
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to live classes
      </button>
      <Card className="p-6 max-w-2xl">
        <form onSubmit={handleSubmit} className="space-y-5">
          {error && (
            <p className="text-sm text-danger-600 bg-danger-50 border border-danger-200 rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Course
            </label>
            <select
              value={courseId}
              onChange={(e) =>
                setCourseId(e.target.value ? Number(e.target.value) : "")
              }
              disabled={coursesLoading}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            >
              <option value="">
                {coursesLoading ? "Loading courses…" : "Select a course"}
              </option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Week 3 live Q&A"
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

          <div className="border-t border-slate-100 pt-4">
            <label className="flex items-center gap-2 mb-3">
              <input
                type="checkbox"
                checked={recurrenceEnabled}
                onChange={(e) => setRecurrenceEnabled(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm font-medium text-gray-700">
                Repeat weekly
              </span>
            </label>

            {recurrenceEnabled && (
              <div className="space-y-3 pl-6">
                <div className="flex flex-wrap gap-2">
                  {WEEKDAYS.map(({ code, label }) => (
                    <button
                      key={code}
                      type="button"
                      onClick={() => toggleDay(code)}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                        selectedDays.includes(code)
                          ? "bg-primary-500 border-primary-500 text-white"
                          : "border-gray-300 text-gray-600 hover:border-primary-300"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Number of weeks
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={12}
                    value={weeks}
                    onChange={(e) => setWeeks(Number(e.target.value))}
                    className="w-24 px-3 py-1.5 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>
            )}
          </div>

          <div className="border-t border-slate-100 pt-4 space-y-2">
            <h3 className="text-sm font-medium text-gray-700 mb-2">
              Class settings
            </h3>
            {(
              [
                ["lobby_enabled", "Lobby (hold students until admitted)"],
                ["start_muted", "Students start muted"],
                ["allow_chat", "Allow chat"],
                ["allow_share", "Allow screen share"],
                ["record", "Record by default"],
              ] as [keyof LiveClassSettings, string][]
            ).map(([key, label]) => (
              <label key={key} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={Boolean(settings[key])}
                  onChange={() => toggleSetting(key)}
                  className="rounded"
                />
                <span className="text-sm text-gray-700">{label}</span>
              </label>
            ))}
            <div className="pt-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Attendance threshold (% of class duration to count as present)
              </label>
              <input
                type="number"
                min={0}
                max={100}
                value={settings.attendance_threshold_pct}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    attendance_threshold_pct: Number(e.target.value),
                  }))
                }
                className="w-24 px-3 py-1.5 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            {/* v2.0 §7.1 classification axes + §7.4 retention (WP5) */}
            <div className="grid sm:grid-cols-2 gap-3 pt-2">
              {(
                [
                  [
                    "purpose",
                    "Purpose",
                    [
                      ["lecture", "Lecture"],
                      ["doubt_clearing", "Doubt clearing"],
                      ["revision", "Revision"],
                      ["lab_demo", "Lab / demonstration"],
                      ["assessment_viva", "Assessment / viva"],
                      ["orientation", "Orientation"],
                      ["guest", "Guest session"],
                    ],
                  ],
                  [
                    "mode",
                    "Mode",
                    [
                      ["instructor_led", "Instructor-led"],
                      ["interactive_workshop", "Interactive workshop"],
                      ["breakout", "Breakout-based"],
                      ["one_to_one", "One-to-one"],
                    ],
                  ],
                  [
                    "audience",
                    "Audience",
                    [
                      ["full_cohort", "Full cohort"],
                      ["batch", "Batch"],
                      ["selected", "Selected learners"],
                      ["open", "Open"],
                    ],
                  ],
                  [
                    "recording_policy",
                    "Recording",
                    [
                      ["always", "Always"],
                      ["on_start", "On instructor start"],
                      ["never", "Never"],
                    ],
                  ],
                ] as [keyof LiveClassSettings, string, [string, string][]][]
              ).map(([key, label, opts]) => (
                <label key={key} className="block">
                  <span className="block text-xs font-medium text-gray-600 mb-1">
                    {label}
                  </span>
                  <select
                    value={(settings[key] as string) || ""}
                    onChange={(e) =>
                      setSettings((prev) => ({
                        ...prev,
                        [key]: e.target.value || null,
                      }))
                    }
                    className="w-full px-3 py-1.5 border border-gray-300 rounded-md text-sm"
                  >
                    <option value="">Not set</option>
                    {opts.map(([v, l]) => (
                      <option key={v} value={v}>
                        {l}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              <label className="block">
                <span className="block text-xs font-medium text-gray-600 mb-1">
                  Keep the recording for (days, max 365)
                </span>
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={settings.retention_days ?? 365}
                  onChange={(e) =>
                    setSettings((prev) => ({
                      ...prev,
                      retention_days: Number(e.target.value),
                    }))
                  }
                  className="w-32 px-3 py-1.5 border border-gray-300 rounded-md text-sm"
                />
                <span className="block text-[11px] text-gray-400 mt-1">
                  Media expires; the class report, attendance and transcript are
                  kept forever.
                </span>
              </label>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate("/instructor/live-classes")}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              <Video className="h-4 w-4 mr-1.5" />
              {submitting ? "Scheduling…" : "Schedule class"}
            </Button>
          </div>
        </form>
      </Card>
    </PageLayout>
  );
}

export default InstructorLiveClassNewPage;
