import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Post-class report: attendance table, threshold editor + recompute, CSV
 * download (authenticated blob), recording status/player.
 */
import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Download,
  CheckCircle2,
  XCircle,
  MinusCircle,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ErrorState } from "@/components/dashboard/primitives";
import { VideoPlayer } from "@/components/video/video-player";
import {
  getLiveClass,
  fetchAttendance,
  recomputeAttendance,
  fetchAttendanceExportCsv,
  fetchRecordingPlayback,
  type LiveClassOut,
  type AttendanceSummaryOut,
  type RecordingPlaybackOut,
} from "@/api/liveClasses";

function presentIcon(present: boolean | null) {
  if (present === true)
    return <CheckCircle2 className="h-4 w-4 text-success-600" />;
  if (present === false) return <XCircle className="h-4 w-4 text-danger-500" />;
  return <MinusCircle className="h-4 w-4 text-slate-300" />;
}

export function InstructorLiveClassReportPage() {
  const { id } = useParams<{ id: string }>();
  const classId = Number(id);
  const navigate = useNavigate();

  const [liveClass, setLiveClass] = React.useState<LiveClassOut | null>(null);
  const [attendance, setAttendance] =
    React.useState<AttendanceSummaryOut | null>(null);
  const [threshold, setThreshold] = React.useState(60);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [recomputing, setRecomputing] = React.useState(false);
  const [exporting, setExporting] = React.useState(false);

  const [playback, setPlayback] = React.useState<RecordingPlaybackOut | null>(
    null,
  );
  const [playbackState, setPlaybackState] = React.useState<
    "idle" | "loading" | "ready" | "unavailable" | "error"
  >("idle");

  const load = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [cls, summary] = await Promise.all([
        getLiveClass(classId),
        fetchAttendance(classId),
      ]);
      setLiveClass(cls);
      setAttendance(summary);
      const pct = cls.settings?.attendance_threshold_pct;
      setThreshold(typeof pct === "number" ? pct : 60);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to load the report",
      );
    } finally {
      setLoading(false);
    }
  }, [classId]);

  React.useEffect(() => {
    if (Number.isFinite(classId)) load();
  }, [classId, load]);

  React.useEffect(() => {
    if (!liveClass) return;
    if (liveClass.recording_status !== "available") return;
    let cancelled = false;
    setPlaybackState("loading");
    fetchRecordingPlayback(classId)
      .then((data) => {
        if (cancelled) return;
        setPlayback(data);
        setPlaybackState("ready");
      })
      .catch((err: any) => {
        if (cancelled) return;
        if (err?.response?.status === 503) {
          setPlaybackState("unavailable");
        } else {
          setPlaybackState("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [liveClass, classId]);

  const handleRecompute = async () => {
    setRecomputing(true);
    try {
      const summary = await recomputeAttendance(classId, threshold);
      setAttendance(summary);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to recompute attendance",
      );
    } finally {
      setRecomputing(false);
    }
  };

  const handleExportCsv = async () => {
    setExporting(true);
    try {
      const blob = await fetchAttendanceExportCsv(classId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `attendance-class-${classId}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to export attendance",
      );
    } finally {
      setExporting(false);
    }
  };

  if (!Number.isFinite(classId)) {
    return (
      <ErrorState
        title="Invalid class"
        description="This live class link looks incorrect."
      />
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[320px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
      </div>
    );
  }

  if (error && !liveClass) {
    return (
      <ErrorState
        title="Couldn't load report"
        description={error}
        onRetry={load}
      />
    );
  }

  const isLive = liveClass?.status === "live";

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="dash-h1 mb-1">{liveClass?.title}</h1>
            <p className="text-slate-600 text-sm">
              Class report and attendance
            </p>
          </div>
          {liveClass && <Badge variant="neutral">{liveClass.status}</Badge>}
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-live-class-report"
    >
      <button
        onClick={() => navigate("/instructor/live-classes")}
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to live classes
      </button>
      {error && (
        <p className="text-sm text-danger-600 bg-danger-50 border border-danger-200 rounded-md px-3 py-2 mb-4">
          {error}
        </p>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-secondary-900">
              Attendance
            </h2>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportCsv}
              disabled={exporting}
            >
              <Download className="h-4 w-4 mr-1.5" />
              {exporting ? "Exporting…" : "Export CSV"}
            </Button>
          </div>

          {attendance && (
            // live_participants is a point-in-time count of who is in the room
            // right now (heartbeats within the last 2 min) — never a historical
            // peak, which the server does not track. It is therefore only
            // meaningful while the class is running; on an ended class the
            // backend returns 0 and the tile is dropped rather than shown as a
            // permanent zero.
            <div
              className={`grid ${isLive ? "grid-cols-3" : "grid-cols-2"} gap-4 mb-5`}
            >
              <div className="rounded-lg bg-slate-50 p-3 text-center">
                <p className="text-xl font-bold text-secondary-900">
                  {attendance.total_participants}
                </p>
                <p className="text-xs text-slate-500">Participants</p>
              </div>
              <div className="rounded-lg bg-success-50 p-3 text-center">
                <p className="text-xl font-bold text-success-700">
                  {attendance.present_count}
                </p>
                <p className="text-xs text-slate-500">Present</p>
              </div>
              {isLive && (
                <div className="rounded-lg bg-slate-50 p-3 text-center">
                  <p className="text-xl font-bold text-secondary-900">
                    {attendance.live_participants}
                  </p>
                  <p className="text-xs text-slate-500">Live now</p>
                </div>
              )}
            </div>
          )}

          <div className="flex items-end gap-3 mb-4 pb-4 border-b border-slate-100">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Present threshold (% of class duration)
              </label>
              <input
                type="number"
                min={0}
                max={100}
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
                className="w-28 px-3 py-1.5 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={handleRecompute}
              disabled={recomputing || liveClass?.status !== "ended"}
            >
              {recomputing ? "Recomputing…" : "Recompute"}
            </Button>
          </div>
          {liveClass && liveClass.status !== "ended" && (
            <p className="text-xs text-slate-400 -mt-3 mb-3">
              Recompute is available once the class has ended.
            </p>
          )}

          {attendance && attendance.rows.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-8">
              No one attended this class.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 uppercase tracking-wide border-b border-slate-100">
                    <th className="py-2 pr-3">Name</th>
                    <th className="py-2 pr-3">Email</th>
                    <th className="py-2 pr-3">First joined</th>
                    <th className="py-2 pr-3">Minutes</th>
                    <th className="py-2 pr-3">Present</th>
                  </tr>
                </thead>
                <tbody>
                  {attendance?.rows.map((row) => (
                    <tr key={row.user_id} className="border-b border-slate-50">
                      <td className="py-2 pr-3 font-medium text-secondary-900">
                        {row.name}
                      </td>
                      <td className="py-2 pr-3 text-slate-500">{row.email}</td>
                      <td className="py-2 pr-3 text-slate-500">
                        {row.first_joined_at
                          ? new Date(row.first_joined_at).toLocaleString()
                          : "—"}
                      </td>
                      <td className="py-2 pr-3 text-slate-500">
                        {row.accumulated_minutes}
                      </td>
                      <td className="py-2 pr-3">{presentIcon(row.present)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card className="p-6">
          <h2 className="text-base font-semibold text-secondary-900 mb-4">
            Recording
          </h2>
          {liveClass?.recording_status === "none" && (
            <p className="text-sm text-slate-400">
              This class was not recorded.
            </p>
          )}
          {(liveClass?.recording_status === "requested" ||
            liveClass?.recording_status === "processing") && (
            <p className="text-sm text-slate-500">
              Recording is being processed — check back soon.
            </p>
          )}
          {liveClass?.recording_status === "failed" && (
            <p className="text-sm text-danger-600">
              Recording failed to process.
            </p>
          )}
          {liveClass?.recording_status === "available" && (
            <>
              {playbackState === "loading" && (
                <p className="text-sm text-slate-400">Loading recording…</p>
              )}
              {playbackState === "unavailable" && (
                <p className="text-sm text-slate-400">
                  Recording playback isn't configured yet.
                </p>
              )}
              {playbackState === "error" && (
                <p className="text-sm text-danger-600">
                  Couldn't load the recording.
                </p>
              )}
              {playbackState === "ready" && playback && (
                <div className="rounded-lg overflow-hidden bg-black aspect-video">
                  <VideoPlayer src={playback.hls_url} title={liveClass.title} />
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </PageLayout>
  );
}

export default InstructorLiveClassReportPage;
