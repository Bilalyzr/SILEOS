import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Video, BookOpen, CheckCircle2 } from "lucide-react";
import {
  recordingAPI,
  type RecordingWork,
  type RecordingClass,
  type LocalTranscription,
} from "@/api/recording-lessons";
import { plannerError } from "@/api/planner";
import RecordingTranscript from "@/components/live/RecordingTranscript";

export default function RecordingLessons() {
  const [params, setParams] = useSearchParams();
  const selected = Number(params.get("class_id")) || 0;
  const [classes, setClasses] = useState<RecordingClass[]>([]);
  const [work, setWork] = useState<RecordingWork | null>(null);
  const [config, setConfig] = useState<LocalTranscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [language, setLanguage] = useState("auto");
  const [dirty, setDirty] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const current = useRef(selected);
  current.current = selected;
  useEffect(() => {
    let alive = true;
    recordingAPI
      .list()
      .then((r) => {
        if (alive) {
          setClasses(r.classes);
          setConfig(r.transcription);
        }
      })
      .catch((e) => {
        if (alive) setError(plannerError(e));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);
  const refresh = useCallback(async () => {
    const r = await recordingAPI.detail(selected);
    if (current.current === selected) {
      setWork(r.work);
      setConfig(r.transcription);
      setClasses((rows) =>
        rows.map((c) =>
          c.class_id === selected && r.work
            ? { ...c, status: r.work.status, lesson_id: r.work.lesson_id }
            : c,
        ),
      );
    }
  }, [selected]);
  useEffect(() => {
    setWork(null);
    setError("");
    setNotice("");
    setDirty(false);
    setReviewed(false);
    if (selected) {
      setLoading(true);
      refresh()
        .catch((e) => {
          if (current.current === selected) setError(plannerError(e));
        })
        .finally(() => {
          if (current.current === selected) setLoading(false);
        });
    }
  }, [selected, refresh]);
  useEffect(() => {
    if (!selected || !work || !["queued", "processing"].includes(work.status))
      return;
    const timer = setInterval(
      () => refresh().catch((e) => setError(plannerError(e))),
      4000,
    );
    return () => clearInterval(timer);
  }, [selected, work, refresh]);
  async function perform(
    action: () => Promise<RecordingWork>,
    message: string,
  ) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await action();
      if (current.current === selected) {
        setWork(result);
        setClasses((rows) =>
          rows.map((c) =>
            c.class_id === selected
              ? { ...c, status: result.status, lesson_id: result.lesson_id }
              : c,
          ),
        );
        setDirty(false);
        setReviewed(false);
        setNotice(message);
      }
    } catch (e) {
      if (current.current === selected) setError(plannerError(e));
    } finally {
      setBusy(false);
    }
  }
  function change(next: Partial<RecordingWork>) {
    if (work) {
      setWork({ ...work, ...next });
      setDirty(true);
      setReviewed(false);
    }
  }
  const editable = work?.status === "draft";
  const field =
    "mt-1 w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm";
  const button =
    "rounded-lg border px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-40";
  return (
    <PageLayout
      header={
        <PageHeader>
          <p className="text-xs font-semibold uppercase tracking-widest text-orange-700">
            Content Studio
          </p>
          <h1 className="mt-2 flex items-center gap-3 text-3xl font-bold">
            <Video className="text-orange-600" /> Recording Lessons
          </h1>
          <p className="mt-2 text-slate-600">
            Turn a completed class into searchable chapters, reviewed notes and
            practice drafts.
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-recording-lessons"
    >
      <div className="flex flex-wrap gap-3 text-sm text-slate-600">
        {[
          "1 · Transcribe locally",
          "2 · Review & correct",
          "3 · Create draft lesson",
          "4 · Publish in course",
        ].map((s) => (
          <span className="rounded-full border bg-white px-3 py-1.5" key={s}>
            {s}
          </span>
        ))}
      </div>
      {config && !config.configured && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          Self-hosted transcription needs setup. {config.note}
        </p>
      )}
      <label className="block max-w-2xl text-sm font-medium">
        Completed class
        <select
          className={field}
          value={selected || ""}
          disabled={busy || dirty}
          onChange={(e) => setParams({ class_id: e.target.value })}
        >
          <option value="">Choose a recording…</option>
          {classes.map((c) => (
            <option key={c.class_id} value={c.class_id}>
              {c.title} · {c.status.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </label>
      {error && (
        <p role="alert" className="rounded-lg bg-rose-50 p-4 text-rose-800">
          {error}
          <button
            className="ml-3 underline"
            onClick={() => {
              setDirty(false);
              refresh()
                .then(() => setError(""))
                .catch((e) => setError(plannerError(e)));
            }}
          >
            Refresh
          </button>
        </p>
      )}
      {notice && (
        <p
          role="status"
          className="rounded-lg bg-emerald-50 p-3 text-emerald-900"
        >
          {notice}
        </p>
      )}
      {loading ? (
        <p role="status">Loading recordings…</p>
      ) : !selected ? (
        <div
          className="rounded-xl border border-dashed bg-white p-10 text-center text-slate-600"
          data-glass="content"
        >
          {classes.length
            ? "Choose a completed class to begin."
            : "No completed classes yet. End a recorded live class to create its lesson here."}
          <Link
            to="/instructor/live-classes"
            className="mt-3 block text-orange-700 underline"
          >
            Open live classes
          </Link>
        </div>
      ) : (
        <>
          {(!work ||
            ["failed", "queued", "processing"].includes(work.status)) && (
            <section
              className="space-y-4 rounded-xl border bg-white p-6"
              data-glass="work"
            >
              <h2 className="text-lg font-semibold">
                {work?.status === "processing"
                  ? "Transcribing on this server…"
                  : work?.status === "queued"
                    ? "Queued for local transcription"
                    : "Create a transcript"}
              </h2>
              <p className="text-sm text-slate-600">
                English, Tamil or automatic detection. Recording uploads
                continue independently. Attempts: {work?.attempts || 0}.
              </p>
              {work?.error && (
                <p role="alert" className="text-sm text-rose-700">
                  {work.error}
                </p>
              )}
              {work?.status !== "processing" && (
                <div className="flex flex-wrap items-end gap-3">
                  <label className="text-sm">
                    Recording language
                    <select
                      className={field}
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                    >
                      <option value="auto">Detect automatically</option>
                      <option value="en">English</option>
                      <option value="ta">Tamil</option>
                    </select>
                  </label>
                  <button
                    className={button + " bg-orange-600 text-white"}
                    disabled={busy || !config?.configured}
                    onClick={() =>
                      perform(
                        () =>
                          recordingAPI.transcribe(
                            selected,
                            language,
                            work?.version,
                          ),
                        "Queued. You can leave this page while transcription runs.",
                      )
                    }
                  >
                    {work?.status === "failed"
                      ? "Retry transcription"
                      : work?.status === "queued"
                        ? "Update language"
                        : "Transcribe recording"}
                  </button>
                </div>
              )}
              {work?.status === "queued" && (
                <p className="text-xs text-slate-500">
                  The local worker picks up queued recordings. If this state
                  persists, check that the recording worker is running.
                </p>
              )}
            </section>
          )}
          {work && ["draft", "lesson_created"].includes(work.status) && (
            <>
              <div
                className="flex flex-wrap items-center gap-3 rounded-xl border bg-white p-4"
                data-glass="content"
              >
                <CheckCircle2 className="text-emerald-600" />
                <span className="font-medium">
                  Transcript ready · {work.language} · {work.segments.length}{" "}
                  segments
                </span>
                <span className="text-sm text-slate-500">
                  {work.lesson_id
                    ? `Lesson ${work.lesson_id} · ${work.lesson_status}`
                    : "Private draft"}
                </span>
              </div>
              <div className="grid gap-6 xl:grid-cols-2">
                <div>
                  <h2 className="mb-3 text-lg font-semibold">
                    Transcript & playback
                  </h2>
                  <RecordingTranscript
                    classId={selected}
                    segments={work.segments}
                    chapters={work.chapters}
                    onEdit={
                      editable && !busy
                        ? (index, text) =>
                            change({
                              segments: work.segments.map((s, i) =>
                                i === index ? { ...s, text } : s,
                              ),
                            })
                        : undefined
                    }
                  />
                </div>
                <section
                  className="space-y-4 rounded-xl border bg-white p-5"
                  data-glass="work"
                >
                  <h2 className="flex items-center gap-2 text-lg font-semibold">
                    <BookOpen size={20} /> Lesson draft
                  </h2>
                  <p className="text-sm text-slate-500">
                    Notes begin as transcript excerpts. Correct transcription
                    errors, write the summary and verify chapter titles before
                    creating a lesson.
                  </p>
                  <label className="block text-sm font-medium">
                    Lesson title
                    <input
                      className={field}
                      disabled={!editable || busy}
                      value={work.title}
                      onChange={(e) => change({ title: e.target.value })}
                      maxLength={200}
                    />
                  </label>
                  <label className="block text-sm font-medium">
                    Reviewed notes
                    <textarea
                      className={field + " min-h-52"}
                      disabled={!editable || busy}
                      value={work.notes}
                      onChange={(e) => change({ notes: e.target.value })}
                      maxLength={20000}
                    />
                  </label>
                  <label className="block text-sm font-medium">
                    Concepts (comma separated)
                    <input
                      className={field}
                      disabled={!editable || busy}
                      value={work.concepts.join(",")}
                      onChange={(e) =>
                        change({ concepts: e.target.value.split(",") })
                      }
                    />
                    <span className="mt-1 block text-xs font-normal text-slate-500">
                      Suggestions match existing course concepts in the
                      transcript. Add or correct them to connect this lesson to
                      Assessment Studio and the learning planner.
                    </span>
                  </label>
                  <h3 className="font-medium">Chapter titles & timestamps</h3>
                  <p className="text-xs text-slate-500">
                    Initial chapters divide the transcript into roughly
                    three-minute sections. Review the topic boundaries.
                  </p>
                  {work.chapters.map((chapter, index) => (
                    <div className="flex gap-2" key={index}>
                      <input
                        aria-label={`Chapter ${index + 1} seconds`}
                        type="number"
                        min={0}
                        step="0.1"
                        className={field + " !w-24"}
                        disabled={!editable || busy}
                        value={chapter.start}
                        onChange={(e) =>
                          change({
                            chapters: work.chapters.map((c, i) =>
                              i === index
                                ? { ...c, start: Number(e.target.value) }
                                : c,
                            ),
                          })
                        }
                      />
                      <input
                        aria-label={`Chapter ${index + 1} title`}
                        className={field}
                        disabled={!editable || busy}
                        value={chapter.title}
                        maxLength={100}
                        onChange={(e) =>
                          change({
                            chapters: work.chapters.map((c, i) =>
                              i === index ? { ...c, title: e.target.value } : c,
                            ),
                          })
                        }
                      />
                      {editable && work.chapters.length > 1 && (
                        <button
                          aria-label={`Remove chapter ${index + 1}`}
                          disabled={busy}
                          onClick={() =>
                            change({
                              chapters: work.chapters.filter(
                                (_, i) => i !== index,
                              ),
                            })
                          }
                        >
                          ×
                        </button>
                      )}
                    </div>
                  ))}
                  {editable && (
                    <button
                      className={button}
                      disabled={busy || work.chapters.length >= 500}
                      onClick={() =>
                        change({
                          chapters: [
                            ...work.chapters,
                            {
                              start: Math.min(
                                work.segments.at(-1)?.end || 0,
                                (work.chapters.at(-1)?.start || 0) + 60,
                              ),
                              title: "New chapter",
                            },
                          ],
                        })
                      }
                    >
                      Add chapter
                    </button>
                  )}
                  {editable && (
                    <div className="space-y-3 border-t pt-4">
                      <button
                        className={button}
                        disabled={busy || !dirty}
                        onClick={() =>
                          perform(
                            () =>
                              recordingAPI.save({
                                ...work,
                                concepts: work.concepts
                                  .map((c) => c.trim())
                                  .filter(Boolean),
                              }),
                            "Draft saved. Review it before creating the lesson.",
                          )
                        }
                      >
                        Save corrections
                      </button>
                      {dirty && (
                        <span className="ml-3 text-xs text-amber-700">
                          Unsaved changes
                        </span>
                      )}
                      <label className="flex items-start gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={reviewed}
                          disabled={dirty || busy}
                          onChange={(e) => setReviewed(e.target.checked)}
                        />
                        I reviewed the transcript, notes, chapters and concepts.
                      </label>
                      <button
                        className={button + " bg-orange-600 text-white"}
                        disabled={busy || dirty || !reviewed}
                        onClick={() =>
                          perform(
                            () =>
                              recordingAPI.action(
                                selected,
                                work.version,
                                "create-lesson",
                              ),
                            "Draft lesson created. Publish it from the course editor when ready.",
                          )
                        }
                      >
                        Create draft lesson
                      </button>
                    </div>
                  )}
                  {work.lesson_id && (
                    <div className="rounded-lg bg-emerald-50 p-4 text-sm">
                      <p>
                        The lesson is in your course curriculum. Publish it
                        there to make it available to enrolled learners and
                        their learning plans.
                      </p>
                      <Link
                        className="mt-2 inline-block font-medium text-emerald-800 underline"
                        to={`/instructor/courses/${work.course_id}/edit`}
                      >
                        Open course editor
                      </Link>
                    </div>
                  )}
                </section>
              </div>
              <section
                className="space-y-4 rounded-xl border bg-white p-5"
                data-glass="content"
              >
                <h2 className="text-lg font-semibold">Practice suggestions</h2>
                <p className="text-sm text-slate-600">
                  These are simple fill-the-gap questions from the transcript.
                  Review their educational value and accepted answers in
                  Assessment Studio before publishing.
                </p>
                {work.suggestions.map((s) => (
                  <div
                    key={s.concept}
                    className="rounded-lg bg-slate-50 p-3 text-sm"
                  >
                    <p className="font-medium">{s.title}</p>
                    <p className="mt-1 text-slate-600">
                      Draft answer: {s.answer}
                    </p>
                  </div>
                ))}
                {!work.suggestions.length && (
                  <p className="text-sm text-slate-500">
                    Save a concept that appears in the transcript to generate an
                    excerpt question.
                  </p>
                )}
                <div className="flex flex-wrap gap-3">
                  <button
                    className={button}
                    disabled={
                      busy ||
                      dirty ||
                      !work.suggestions.length ||
                      !!work.question_ids.length
                    }
                    onClick={() =>
                      perform(
                        () =>
                          recordingAPI.action(
                            selected,
                            work.version,
                            "assessment-drafts",
                          ),
                        "Unpublished practice drafts created in Assessment Studio.",
                      )
                    }
                  >
                    {work.question_ids.length
                      ? `${work.question_ids.length} assessment ${work.question_ids.length === 1 ? "draft" : "drafts"} created`
                      : "Create assessment drafts"}
                  </button>
                  <Link
                    className={button}
                    to={`/instructor/assessment-studio?course_id=${work.course_id}`}
                  >
                    Open Assessment Studio
                  </Link>
                </div>
              </section>
            </>
          )}
        </>
      )}
    </PageLayout>
  );
}
