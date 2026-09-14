import { useCallback } from "react";
import React, { useEffect, useState } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Plus, Trash2, CheckCircle2, XCircle } from "lucide-react";
import toast from "react-hot-toast";
import {
  spocApi,
  Cohort,
  RosterRow,
  TaskStatsRow,
  CohortSession,
  AttendanceStatus,
  AttendanceEntry,
} from "@/api/cohort";
import { ViewAsSpocBanner } from "@/components/spoc/ViewAsSpocBanner";
import { CohortMasteryPanel } from "@/components/spoc/CohortMasteryPanel";

type TabKey = "roster" | "sessions" | "tasks" | "eligibility" | "mastery";

export const SpocCohortDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const cohortId = Number(id);

  const [cohort, setCohort] = useState<Cohort | null>(null);
  const [tab, setTab] = useState<TabKey>("roster");

  const [roster, setRoster] = useState<RosterRow[]>([]);
  const [stats, setStats] = useState<TaskStatsRow[]>([]);
  const [sessions, setSessions] = useState<CohortSession[]>([]);

  const loadCohort = useCallback(async () => {
    try {
      const list = await spocApi.myCohorts();
      setCohort(list.find((c) => c.id === cohortId) || null);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load cohort");
    }
  }, [cohortId]);

  const loadRoster = useCallback(async () => {
    try {
      setRoster(await spocApi.roster(cohortId));
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load roster");
    }
  }, [cohortId]);

  const loadStats = useCallback(async () => {
    try {
      setStats(await spocApi.taskStats(cohortId));
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load stats");
    }
  }, [cohortId]);

  const loadSessions = useCallback(async () => {
    try {
      setSessions(await spocApi.listSessions(cohortId));
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load sessions");
    }
  }, [cohortId]);

  useEffect(() => {
    loadCohort();
  }, [cohortId, loadCohort]);
  useEffect(() => {
    if (tab === "roster" || tab === "eligibility") loadRoster();
    if (tab === "tasks") loadStats();
    if (tab === "sessions") {
      loadRoster();
      loadSessions();
    }
  }, [tab, cohortId, loadRoster, loadStats, loadSessions]);

  // An internship-type cohort has no associated course — students pick their
  // own course via the voucher redeemer. We hide the Sessions tab for these.
  const isInternshipCohort = cohort ? cohort.course_id == null : false;

  // Coerce the active tab away from `sessions` if we land on an internship
  // cohort (the tab list no longer contains it).
  useEffect(() => {
    if (isInternshipCohort && tab === "sessions") {
      setTab("roster");
    }
  }, [isInternshipCohort, tab]);

  if (!cohortId) return <div className="p-6">Invalid cohort.</div>;

  const tabs: [TabKey, string][] = isInternshipCohort
    ? [
        ["roster", "Roster"],
        ["tasks", "Task Stats"],
        ["eligibility", "Internship Eligibility"],
      ]
    : [
        ["roster", "Roster"],
        ["sessions", "Sessions"],
        ["tasks", "Task Stats"],
        ["eligibility", "Internship Eligibility"],
      ];

  return (
    <>
      <ViewAsSpocBanner />
      <div className="max-w-6xl mx-auto px-4 py-8">
        <Link
          to="/spoc/dashboard"
          className="text-sm text-indigo-600 flex items-center gap-1 mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back to my cohorts
        </Link>

        <h1 className="text-2xl font-bold text-gray-900">
          {cohort?.name || `Cohort #${cohortId}`}
        </h1>
        {cohort?.referral_code && (
          <p className="text-sm text-gray-500 mt-1">
            Referral code:{" "}
            <code className="bg-gray-100 px-2 py-0.5 rounded font-mono">
              {cohort.referral_code.code}
            </code>{" "}
            · {cohort.referral_code.used_count}/{cohort.referral_code.max_uses}{" "}
            used
          </p>
        )}

        {isInternshipCohort && (
          <div className="mt-4 rounded-md border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-900">
            <strong>Internship cohort</strong> — students pick their own courses
            via vouchers. Sessions are not applicable here.
          </div>
        )}

        <div className="mt-6 border-b border-gray-200 flex gap-1">
          {tabs.map(([k, lbl]) => (
            <button
              key={k}
              onClick={() => setTab(k)}
              className={`px-4 py-2 text-sm border-b-2 ${tab === k ? "border-indigo-600 text-indigo-700 font-semibold" : "border-transparent text-gray-500 hover:text-gray-700"}`}
            >
              {lbl}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setTab("mastery")}
            data-testid="tab-mastery"
            className={`px-4 py-2 text-sm border-b-2 ${tab === "mastery" ? "border-indigo-600 text-indigo-700 font-semibold" : "border-transparent text-gray-500 hover:text-gray-700"}`}
          >
            Mastery
          </button>
        </div>

        <div className="mt-6">
          {tab === "mastery" && <CohortMasteryPanel cohortId={cohortId} />}
          {tab === "roster" && (
            <>
              <RosterTab rows={roster} />
              {isInternshipCohort && (
                <p className="mt-3 text-xs text-gray-500 italic">
                  Extended stats (redeemed course, progress %, certs) coming
                  soon — view in <code>/admin/internships</code> for now.
                </p>
              )}
            </>
          )}
          {tab === "sessions" && !isInternshipCohort && (
            <SessionsTab
              cohortId={cohortId}
              roster={roster}
              sessions={sessions}
              reload={loadSessions}
            />
          )}
          {tab === "tasks" && <TasksTab rows={stats} />}
          {tab === "eligibility" && <EligibilityTab roster={roster} />}
        </div>
      </div>
    </>
  );
};

// ---------------- Roster ----------------

const RosterTab: React.FC<{ rows: RosterRow[] }> = ({ rows }) => (
  <div className="bg-white rounded-lg shadow overflow-hidden" data-glass="work">
    <table className="min-w-full divide-y divide-gray-200">
      <thead className="bg-gray-50">
        <tr>
          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
            Student
          </th>
          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
            Email
          </th>
          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
            Joined
          </th>
          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
            Active today
          </th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-200">
        {rows.length === 0 ? (
          <tr>
            <td colSpan={4} className="p-6 text-center text-gray-400">
              No students yet
            </td>
          </tr>
        ) : (
          rows.map((r) => (
            <tr key={r.user_id}>
              <td className="px-4 py-3 font-medium">{r.display_name}</td>
              <td className="px-4 py-3 text-sm text-gray-600">{r.email}</td>
              <td className="px-4 py-3 text-sm">
                {new Date(r.joined_at).toLocaleDateString()}
              </td>
              <td className="px-4 py-3">
                <span
                  title={
                    r.active_today ? "Activity today" : "No activity today"
                  }
                  className={`inline-block w-3 h-3 rounded-full ${r.active_today ? "bg-green-500" : "bg-gray-300"}`}
                />
              </td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  </div>
);

// ---------------- Sessions ----------------

const SessionsTab: React.FC<{
  cohortId: number;
  roster: RosterRow[];
  sessions: CohortSession[];
  reload: () => void;
}> = ({ cohortId, roster, sessions, reload }) => {
  const [creating, setCreating] = useState(false);
  const [newSession, setNewSession] = useState({
    scheduled_at: "",
    duration_minutes: 60,
    topic: "",
    session_type: "lecture",
  });
  const [markingSessionId, setMarkingSessionId] = useState<number | null>(null);
  const [marks, setMarks] = useState<Record<number, AttendanceStatus>>({});

  const create = async () => {
    if (!newSession.scheduled_at) {
      toast.error("Date/time required");
      return;
    }
    try {
      await spocApi.createSession(cohortId, {
        ...newSession,
        scheduled_at: new Date(newSession.scheduled_at).toISOString(),
      } as any);
      toast.success("Session created");
      setCreating(false);
      reload();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Create failed");
    }
  };

  const remove = async (s: CohortSession) => {
    if (!(await confirmDialog("Delete this session?"))) return;
    try {
      await spocApi.deleteSession(cohortId, s.id);
      toast.success("Deleted");
      reload();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Delete failed");
    }
  };

  const openMarker = (s: CohortSession) => {
    setMarkingSessionId(s.id);
    const initial: Record<number, AttendanceStatus> = {};
    roster.forEach((r) => {
      initial[r.user_id] = "absent";
    });
    setMarks(initial);
  };

  const saveMarks = async () => {
    if (!markingSessionId) return;
    const entries: AttendanceEntry[] = Object.entries(marks).map(
      ([uid, st]) => ({
        user_id: Number(uid),
        status: st,
      }),
    );
    try {
      await spocApi.bulkAttendance(markingSessionId, entries);
      toast.success("Attendance saved");
      setMarkingSessionId(null);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Save failed");
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold">Sessions</h2>
        <button
          onClick={() => setCreating(true)}
          className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm flex items-center gap-1 hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" /> New
        </button>
      </div>

      <div
        className="bg-white rounded-lg shadow overflow-hidden"
        data-glass="work"
      >
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase">
                When
              </th>
              <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase">
                Topic
              </th>
              <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase">
                Type
              </th>
              <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase">
                Mins
              </th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {sessions.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-6 text-center text-gray-400">
                  No sessions yet
                </td>
              </tr>
            ) : (
              sessions.map((s) => (
                <tr key={s.id}>
                  <td className="px-4 py-2 text-sm">
                    {new Date(s.scheduled_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-sm">{s.topic || "—"}</td>
                  <td className="px-4 py-2 text-sm">{s.session_type}</td>
                  <td className="px-4 py-2 text-sm">{s.duration_minutes}</td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => openMarker(s)}
                      className="text-indigo-600 text-sm mr-3"
                    >
                      Mark attendance
                    </button>
                    <button onClick={() => remove(s)} className="text-red-600">
                      <Trash2 className="h-4 w-4 inline" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {creating && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-modal p-4">
          <div
            className="bg-white rounded-lg max-w-md w-full p-6"
            data-glass="work"
          >
            <h3 className="text-lg font-bold mb-3">New session</h3>
            <div className="space-y-2">
              <input
                type="datetime-local"
                className="w-full border rounded px-3 py-2"
                value={newSession.scheduled_at}
                onChange={(e) =>
                  setNewSession({ ...newSession, scheduled_at: e.target.value })
                }
              />
              <input
                className="w-full border rounded px-3 py-2"
                placeholder="Topic"
                value={newSession.topic}
                onChange={(e) =>
                  setNewSession({ ...newSession, topic: e.target.value })
                }
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  className="border rounded px-3 py-2"
                  value={newSession.session_type}
                  onChange={(e) =>
                    setNewSession({
                      ...newSession,
                      session_type: e.target.value,
                    })
                  }
                >
                  <option value="lecture">Lecture</option>
                  <option value="lab">Lab</option>
                  <option value="evaluation">Evaluation</option>
                  <option value="other">Other</option>
                </select>
                <input
                  type="number"
                  className="border rounded px-3 py-2"
                  placeholder="Minutes"
                  value={newSession.duration_minutes}
                  onChange={(e) =>
                    setNewSession({
                      ...newSession,
                      duration_minutes: Number(e.target.value),
                    })
                  }
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button
                className="px-3 py-1.5 border rounded"
                onClick={() => setCreating(false)}
              >
                Cancel
              </button>
              <button
                className="px-3 py-1.5 bg-indigo-600 text-white rounded"
                onClick={create}
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {markingSessionId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-modal p-4">
          <div
            className="bg-white rounded-lg max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto"
            data-glass="work"
          >
            <h3 className="text-lg font-bold mb-3">Mark attendance</h3>
            <table className="min-w-full text-sm">
              <tbody>
                {roster.map((r) => (
                  <tr key={r.user_id} className="border-b">
                    <td className="py-2">{r.display_name}</td>
                    <td className="py-2 text-right">
                      <select
                        className="border rounded px-2 py-1"
                        value={marks[r.user_id] || "absent"}
                        onChange={(e) =>
                          setMarks({
                            ...marks,
                            [r.user_id]: e.target.value as AttendanceStatus,
                          })
                        }
                      >
                        <option value="present">Present</option>
                        <option value="absent">Absent</option>
                        <option value="late">Late</option>
                        <option value="excused">Excused</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex justify-end gap-2 mt-4">
              <button
                className="px-3 py-1.5 border rounded"
                onClick={() => setMarkingSessionId(null)}
              >
                Cancel
              </button>
              <button
                className="px-3 py-1.5 bg-indigo-600 text-white rounded"
                onClick={saveMarks}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ---------------- Task Stats ----------------

const TasksTab: React.FC<{ rows: TaskStatsRow[] }> = ({ rows }) => (
  <div className="bg-white rounded-lg shadow overflow-hidden" data-glass="work">
    <table className="min-w-full divide-y divide-gray-200">
      <thead className="bg-gray-50">
        <tr>
          <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase">
            Student
          </th>
          <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase">
            Lessons completed
          </th>
          <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase">
            Quiz attempts
          </th>
          <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase">
            Submissions
          </th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-200">
        {rows.length === 0 ? (
          <tr>
            <td colSpan={4} className="p-6 text-center text-gray-400">
              No data yet
            </td>
          </tr>
        ) : (
          rows.map((r) => (
            <tr key={r.user_id}>
              <td className="px-4 py-2 font-medium">{r.display_name}</td>
              <td className="px-4 py-2">{r.completed_lessons}</td>
              <td className="px-4 py-2">{r.quiz_attempts}</td>
              <td className="px-4 py-2">{r.assignment_submissions}</td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  </div>
);

// ---------------- Eligibility ----------------

const EligibilityTab: React.FC<{ roster: RosterRow[] }> = ({ roster }) => {
  const [state, setState] = useState<Record<number, boolean>>({});
  const [reason, setReason] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState<number | null>(null);

  const toggle = async (userId: number, newValue: boolean) => {
    setBusy(userId);
    try {
      await spocApi.setEligibility(userId, {
        eligible: newValue,
        reason: reason[userId] || "",
      });
      setState({ ...state, [userId]: newValue });
      toast.success(`Marked ${newValue ? "eligible" : "not eligible"}`);
    } catch (e: any) {
      const detail = e?.response?.data?.detail || "Failed";
      if (e?.response?.status === 503) {
        toast.error("Candidate module not deployed yet (SS2 pending)");
      } else {
        toast.error(detail);
      }
    } finally {
      setBusy(null);
    }
  };

  return (
    <div
      className="bg-white rounded-lg shadow overflow-hidden"
      data-glass="work"
    >
      <div className="p-4 border-b bg-gray-50 text-sm text-gray-600">
        Toggle a student's internship eligibility. This writes to{" "}
        <code>CandidateEligibility</code> with <code>source=spoc_approved</code>
        .
      </div>
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase">
              Student
            </th>
            <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase">
              Reason (optional)
            </th>
            <th className="px-4 py-2 text-right text-xs text-gray-500 uppercase">
              Decision
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {roster.length === 0 ? (
            <tr>
              <td colSpan={3} className="p-6 text-center text-gray-400">
                No students
              </td>
            </tr>
          ) : (
            roster.map((r) => (
              <tr key={r.user_id}>
                <td className="px-4 py-2 font-medium">{r.display_name}</td>
                <td className="px-4 py-2">
                  <input
                    className="border rounded px-2 py-1 text-sm w-full"
                    placeholder="Optional note"
                    value={reason[r.user_id] || ""}
                    onChange={(e) =>
                      setReason({ ...reason, [r.user_id]: e.target.value })
                    }
                  />
                </td>
                <td className="px-4 py-2 text-right">
                  <button
                    disabled={busy === r.user_id}
                    onClick={() => toggle(r.user_id, true)}
                    className="inline-flex items-center gap-1 text-green-600 hover:text-green-800 mr-3 text-sm disabled:opacity-50"
                  >
                    <CheckCircle2 className="h-4 w-4" /> Eligible
                  </button>
                  <button
                    disabled={busy === r.user_id}
                    onClick={() => toggle(r.user_id, false)}
                    className="inline-flex items-center gap-1 text-gray-500 hover:text-red-600 text-sm disabled:opacity-50"
                  >
                    <XCircle className="h-4 w-4" /> Not eligible
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default SpocCohortDetail;
