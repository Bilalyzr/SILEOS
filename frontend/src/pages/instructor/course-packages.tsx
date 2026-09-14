import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Upload, Download, Archive, FileText } from "lucide-react";
import {
  coursePackagesAPI,
  type CoursePackagePreview,
} from "@/api/course-packages";
import { downloadBlob } from "@/api/operations";
import { plannerError } from "@/api/planner";
const button =
  "rounded-lg border px-4 py-2 text-sm font-medium disabled:opacity-40";
export default function CoursePackages() {
  const [files, setFiles] = useState<File[]>([]);
  const [preview, setPreview] = useState<CoursePackagePreview | null>(null);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [created, setCreated] = useState<number | null>(null);
  const [courses, setCourses] = useState<
    { id: number; title: string; status: string }[]
  >([]);
  const [course, setCourse] = useState(0);
  const [history, setHistory] = useState<CoursePackagePreview[]>([]);
  useEffect(() => {
    let alive = true;
    Promise.all([coursePackagesAPI.courses(), coursePackagesAPI.previews()])
      .then(([c, p]) => {
        if (alive) {
          setCourses(c);
          setHistory((existing) => [
            ...existing,
            ...p.filter(
              (item) => !existing.some((current) => current.id === item.id),
            ),
          ]);
        }
      })
      .catch((e) => {
        if (alive) setError(plannerError(e));
      });
    return () => {
      alive = false;
    };
  }, []);
  async function inspect() {
    setBusy(true);
    setError("");
    setNotice("");
    setProgress(0);
    setCreated(null);
    try {
      const p = await coursePackagesAPI.inspect(files, setProgress);
      setPreview(p);
      setTitle(p.preview.title);
      setHistory((h) => [p, ...h]);
      setNotice(
        p.kind === "backup"
          ? "Sasha course backup detected and checked."
          : "Course files detected. Review the draft course outline.",
      );
    } catch (e) {
      setError(plannerError(e));
    } finally {
      setBusy(false);
    }
  }
  async function restore() {
    if (!preview) return;
    setBusy(true);
    setError("");
    try {
      const r = await coursePackagesAPI.restore(preview.id, title);
      setCreated(r.course_id);
      setCourses((c) =>
        c.some((item) => item.id === r.course_id)
          ? c
          : [...c, { id: r.course_id, title: title.trim(), status: r.status }],
      );
      setCourse(r.course_id);
      setPreview({ ...preview, status: "restored", course_id: r.course_id });
      setHistory((h) =>
        h.map((p) =>
          p.id === preview.id
            ? { ...p, status: "restored", course_id: r.course_id }
            : p,
        ),
      );
      setNotice(
        "Draft course created. Open the course editor to review and publish its content.",
      );
    } catch (e) {
      setError(plannerError(e));
    } finally {
      setBusy(false);
    }
  }
  async function backup() {
    setBusy(true);
    setError("");
    try {
      downloadBlob(
        await coursePackagesAPI.backup(course),
        `course-${course}.sasha-course.zip`,
      );
      setNotice(
        "Course backup downloaded. Upload it here to detect and restore it later.",
      );
    } catch (e) {
      if (e && typeof e === "object" && "response" in e) {
        const response = (e as { response?: { data?: unknown } }).response;
        if (response?.data instanceof Blob) {
          try {
            setError(JSON.parse(await response.data.text()).detail);
            return;
          } catch {
            /* use generic error */
          }
        }
      }
      setError(plannerError(e));
    } finally {
      setBusy(false);
    }
  }
  async function discard(p: CoursePackagePreview) {
    setBusy(true);
    try {
      await coursePackagesAPI.discard(p.id);
      setHistory((h) => h.filter((x) => x.id !== p.id));
      if (preview?.id === p.id) setPreview(null);
    } catch (e) {
      setError(plannerError(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <PageLayout
      header={
        <PageHeader>
          <p className="text-xs font-semibold uppercase tracking-widest text-orange-700">
            Content Studio
          </p>
          <h1 className="mt-2 text-3xl font-bold">Course Upload & Backup</h1>
          <p className="mt-2 text-slate-600">
            Create a course from documents, video or audio. Upload a Sasha
            backup to restore a course.
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-course-packages"
    >
      {error && (
        <p role="alert" className="rounded-lg bg-rose-50 p-4 text-rose-800">
          {error}
        </p>
      )}
      {notice && (
        <p
          role="status"
          className="rounded-lg bg-emerald-50 p-4 text-emerald-800"
        >
          {notice}
        </p>
      )}
      <div className="grid items-start gap-6 lg:grid-cols-2">
        <section
          className="space-y-4 rounded-xl border bg-white p-6"
          data-glass="work"
        >
          <Upload className="text-orange-600" />
          <h2 className="text-xl font-semibold">
            Upload course files or a backup
          </h2>
          <p className="text-sm text-slate-600">
            PDF, Word (.docx), TXT, Markdown, MP4, WebM, MP3 or WAV: each file
            becomes a draft lesson. A Sasha backup ZIP is detected by its
            manifest, including its version and checksums.
          </p>
          <label className="block rounded-xl border-2 border-dashed p-6 text-sm font-medium">
            Select course files
            <input
              aria-label="Course files"
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.md,.mp4,.webm,.mp3,.wav,.png,.jpg,.jpeg,.webp,.gif,.glb,.zip"
              disabled={busy}
              className="mt-3 block w-full text-sm"
              onChange={(e) => {
                setFiles(Array.from(e.target.files || []));
                setPreview(null);
                setCreated(null);
              }}
            />
          </label>
          <p className="text-xs text-slate-500">
            Up to 30 files or one backup · 200 MB total · Preview retained for
            24 hours
          </p>
          <button
            className={button + " bg-orange-600 text-white"}
            disabled={busy || !files.length}
            onClick={inspect}
          >
            {busy && progress > 0
              ? `Uploading / checking ${progress}%`
              : "Detect and preview upload"}
          </button>
          <Link
            to="/instructor/courses/create"
            className="ml-3 text-sm text-orange-700 underline"
          >
            Create a course manually
          </Link>
          <p className="text-xs text-slate-500">
            Add quizzes and interactive content in the course editor after
            creating your draft.
          </p>
        </section>
        <section
          className="space-y-4 rounded-xl border bg-white p-6"
          data-glass="work"
        >
          <Archive className="text-orange-600" />
          <h2 className="text-xl font-semibold">Download a portable backup</h2>
          <p className="text-sm text-slate-600">
            Back up course content, quizzes, assignments, concepts and supported
            interactive assets. Learner accounts, grades and payment records
            stay out of the package.
          </p>
          <label className="block text-sm font-medium">
            Course to back up
            <select
              aria-label="Course to back up"
              className="mt-2 w-full rounded-lg border p-3"
              value={course || ""}
              disabled={busy}
              onChange={(e) => setCourse(Number(e.target.value))}
            >
              <option value="">Choose a course…</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title} · {c.status}
                </option>
              ))}
            </select>
          </label>
          <button
            className={button + " flex items-center gap-2"}
            disabled={!course || busy}
            onClick={backup}
          >
            <Download size={16} />
            Download course backup
          </button>
          <p className="text-xs text-slate-500">
            Local supported assets are embedded. Remote videos and CDN URLs stay
            as references and are identified during restore.
          </p>
        </section>
      </div>
      {preview && (
        <section
          className="space-y-5 rounded-xl border bg-white p-6"
          data-glass="work"
        >
          <div className="flex items-center gap-3">
            <FileText className="text-orange-600" />
            <h2 className="text-xl font-semibold">
              {preview.kind === "backup"
                ? "Recognized course backup"
                : "New course outline"}
            </h2>
          </div>
          <label className="block max-w-xl text-sm font-medium">
            Course title
            <input
              aria-label="Restored course title"
              className="mt-2 w-full rounded-lg border p-3"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
              disabled={busy || preview.status === "restored"}
            />
          </label>
          <div className="flex flex-wrap gap-3 text-sm">
            {[
              ["Lessons", preview.preview.lessons],
              ["Quizzes", preview.preview.quizzes],
              ["Assignments", preview.preview.assignments],
              ["Assessment drafts", preview.preview.assessment_drafts],
            ].map(([label, count]) => (
              <span className="rounded-lg bg-slate-100 px-3 py-2" key={label}>
                {label}: {count}
              </span>
            ))}
            {Object.entries(preview.preview.dependencies).map(([kind, n]) => (
              <span className="rounded-lg bg-slate-100 px-3 py-2" key={kind}>
                {kind}: {n}
              </span>
            ))}
          </div>
          <ul className="list-inside list-disc space-y-2 text-sm text-slate-600">
            {preview.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
          <div className="flex flex-wrap gap-2">
            {Object.entries(preview.preview.categories || {}).map(
              ([kind, count]) => (
                <span key={kind} className="astra-work px-3 py-2 rounded-lg">
                  {kind}: {count}
                </span>
              ),
            )}
          </div>
          {preview.preview.assets?.length ? (
            <ul className="text-sm space-y-2">
              {preview.preview.assets.map((asset, i) => (
                <li className="break-words" key={i}>
                  {asset.filename} · {asset.category} ·{" "}
                  {(asset.size / 1024 / 1024).toFixed(2)} MB
                </li>
              ))}
            </ul>
          ) : null}
          <details>
            <summary className="cursor-pointer text-sm font-medium">
              Lesson outline
            </summary>
            <ol className="mt-3 list-inside list-decimal space-y-2 text-sm">
              {preview.preview.lesson_titles.map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ol>
          </details>
          <p className="text-sm text-slate-600">
            This creates a new draft course. Existing courses are never
            overwritten. Review the restored lessons and assessments before
            publishing them.
          </p>
          {created || preview.course_id ? (
            <Link
              className={button + " inline-block bg-orange-600 text-white"}
              to={`/instructor/courses/${created || preview.course_id}/edit`}
            >
              Open restored course
            </Link>
          ) : (
            <button
              className={button + " bg-orange-600 text-white"}
              disabled={busy || !title.trim() || preview.status !== "preview"}
              onClick={restore}
            >
              {busy
                ? "Creating draft…"
                : preview.kind === "backup"
                  ? "Restore as new draft course"
                  : "Create draft course from files"}
            </button>
          )}
        </section>
      )}
      {history.length > 0 && (
        <section
          className="rounded-xl border bg-white p-6"
          data-glass="content"
        >
          <h2 className="text-lg font-semibold">Recent uploads</h2>
          <ul className="mt-3 divide-y">
            {history.map((p) => (
              <li
                key={p.id}
                className="flex flex-wrap items-center justify-between gap-3 py-3"
              >
                <button
                  className="text-left text-sm text-orange-700 underline"
                  disabled={busy}
                  onClick={() => {
                    setPreview(p);
                    setTitle(p.preview.title);
                    setCreated(p.course_id);
                  }}
                >
                  {p.preview.title} · {p.kind}
                </button>
                <button
                  className={button}
                  disabled={busy}
                  onClick={() => discard(p)}
                >
                  Discard uploaded file
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </PageLayout>
  );
}
