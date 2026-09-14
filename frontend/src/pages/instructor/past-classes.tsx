import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Past classes report (owner request 2026-09-04): one row per ended class —
 * schedule, title, attendance, recording availability. Actions: get the
 * signed playback link, and delete the recording (instructor owns theirs;
 * admin sees everything — enforced server-side).
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { confirmDialog } from "@/components/ui/confirm";
import { ClassReportModal } from "@/components/live/ClassReportModal";
import toast from "react-hot-toast";
import { History, Trash2 } from "lucide-react";
import { api } from "@/api/axios";

interface ReportRow {
  class_id: number;
  course_id: number;
  title: string;
  scheduled_at: string | null;
  ended: boolean | null;
  attendance_count: number;
  has_recording: boolean;
}

export default function PastClassesPage() {
  const [rows, setRows] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [reportId, setReportId] = useState<number | null>(null);

  const load = () => {
    api
      .get("/live/past-classes-report")
      .then((r) => setRows(r.data.classes))
      .catch(() => toast.error("Failed to load the report"))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  async function playLink(classId: number) {
    setBusyId(classId);
    try {
      const r = await api.get(`/live/classes/${classId}/recording-playback`);
      window.open(r.data.hls_url, "_blank");
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      toast.error(
        typeof detail === "string" ? detail : "No playback available",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function deleteRecording(classId: number) {
    if (
      !(await confirmDialog(
        "Delete this recording? Students keep attendance history; only the media link is removed. An admin can still recover it.",
      ))
    )
      return;
    setBusyId(classId);
    try {
      await api.delete(`/live/classes/${classId}/recording`);
      toast.success("Recording deleted");
      load();
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Delete failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="dash-h1 flex items-center gap-2">
              <History className="h-7 w-7 text-primary" /> Past Classes
            </h1>
            <p className="text-slate-600 text-sm mt-1 mb-8">
              Attendance and recordings for every class you have run.
            </p>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-past-classes"
    >
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 rounded-xl bg-gray-100 animate-pulse"
            />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <p className="text-gray-500 text-sm border border-dashed border-gray-300 rounded-xl p-8 text-center">
          No past classes yet.
        </p>
      ) : (
        <ul className="space-y-3">
          {rows.map((c) => (
            <li
              key={c.class_id}
              className="border border-gray-200 rounded-xl bg-white p-4 flex flex-wrap items-center gap-4"
            >
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-gray-900">{c.title}</h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  {c.scheduled_at
                    ? new Date(c.scheduled_at).toLocaleString()
                    : "—"}
                  {" · "}<AstraSymbol value="👥" /> {c.attendance_count} attended
                  {" · "}
                  {c.has_recording ? (
                    <span className="text-emerald-600">
                      recording available
                      {(c as any).days_left != null
                        ? ` · expires in ${(c as any).days_left} days`
                        : ""}
                    </span>
                  ) : (c as any).recording_deleted_at ? (
                    <span className="text-amber-600">
                      recording deleted (restorable for 30 days)
                    </span>
                  ) : (
                    <span className="text-gray-400">no recording</span>
                  )}
                  {(c as any).lifecycle && (
                    <span className="ml-2 px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">
                      {(c as any).lifecycle}
                    </span>
                  )}
                </p>
              </div>
              {(c as any).has_report && (
                <Link
                  to={`/instructor/recording-lessons?class_id=${c.class_id}`}
                  className="px-3 py-2 text-sm font-medium rounded-lg border border-orange-200 text-orange-700"
                >
                  Create lesson
                </Link>
              )}
              {(c as any).has_report && (
                <button
                  onClick={() => setReportId(c.class_id)}
                  className="px-3 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
                >
                  Report
                </button>
              )}
              {c.has_recording && (
                <div className="flex gap-2">
                  <button
                    onClick={() => playLink(c.class_id)}
                    disabled={busyId === c.class_id}
                    className="px-3 py-2 text-sm font-medium rounded-lg border border-blue-300 text-blue-700 hover:bg-blue-50 disabled:opacity-40"
                  >
                    Open recording
                  </button>
                  <button
                    onClick={() => deleteRecording(c.class_id)}
                    disabled={busyId === c.class_id}
                    className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium rounded-lg border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-40"
                  >
                    <Trash2 className="h-4 w-4" /> Delete recording
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {reportId && (
        <ClassReportModal
          classId={reportId}
          onClose={() => setReportId(null)}
          onChanged={() => {
            api
              .get("/live/past-classes-report")
              .then((r) => setRows(r.data.classes))
              .catch(() => {});
          }}
        />
      )}
    </PageLayout>
  );
}
