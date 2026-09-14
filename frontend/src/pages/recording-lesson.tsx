import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { recordingAPI, type RecordingReader } from "@/api/recording-lessons";
import { plannerError } from "@/api/planner";
import RecordingTranscript from "@/components/live/RecordingTranscript";

export default function RecordingLessonPage() {
  const { classId } = useParams();
  const [params] = useSearchParams();
  const [data, setData] = useState<RecordingReader | null>(null);
  const [error, setError] = useState("");
  const seconds = Number(params.get("start"));
  const start = Number.isFinite(seconds) && seconds >= 0 ? seconds : 0;
  useEffect(() => {
    let alive = true;
    setData(null);
    setError("");
    recordingAPI
      .reader(Number(classId))
      .then((r) => {
        if (alive) setData(r);
      })
      .catch((e) => {
        if (alive) setError(plannerError(e));
      });
    return () => {
      alive = false;
    };
  }, [classId]);
  return (
    <main className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      {error ? (
        <p role="alert" className="rounded-xl bg-rose-50 p-5 text-rose-800">
          {error}
        </p>
      ) : !data ? (
        <p>Loading recording lesson…</p>
      ) : (
        <>
          <Link
            to={`/courses/${data.course_id}`}
            className="text-sm text-orange-700 underline"
          >
            Back to course
          </Link>
          <h1 className="text-3xl font-bold">{data.title}</h1>
          {!data.recording_available && (
            <p className="rounded-lg bg-amber-50 p-4 text-sm">
              The recording is unavailable. Reviewed notes and transcript remain
              available.
            </p>
          )}
          <div
            className="whitespace-pre-wrap rounded-xl border bg-white p-6 leading-7"
            data-glass="content"
          >
            {data.notes}
          </div>
          <RecordingTranscript
            classId={data.class_id}
            segments={data.segments}
            chapters={data.chapters}
            initialStart={start}
          />
        </>
      )}
    </main>
  );
}
