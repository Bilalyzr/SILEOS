import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/axios";
import { campusApi } from "@/api/campus";
import type { InstitutionOverview } from "@/api/institutions";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { GlassDialog } from "@/components/ui/dialog";
import { BrandBanner } from "@/components/design-system/BrandBanner";
import { apiError } from "./InstitutionDialog";
import { BookOpen, LockKeyhole, CheckCircle2 } from "lucide-react";
import toast from "react-hot-toast";
interface Lesson {
  id: number;
  title: string;
  body: string;
  resource_id: number | null;
  completed: boolean;
}
interface Course {
  id: number;
  title: string;
  summary: string;
  batch_id: number | null;
  published: boolean;
  can_edit: boolean;
  lessons: number;
  completed: number;
  content?: Lesson[];
}
export function CampusLearning({ data }: { data: InstitutionOverview }) {
  const inst = data.institution;
  const user = useAuthStore((s) => s.user);
  const staff = ["owner", "admin", "teacher"].includes(inst.role);
  const root = `/institutions/${inst.id}/learning-courses`;
  const [selected, setSelected] = useState<number>();
  const [create, setCreate] = useState(false);
  const [editing, setEditing] = useState<Lesson | "new">();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showProgress, setShowProgress] = useState(false);
  const list = useQuery({
    queryKey: ["campus-learning", user?.id, inst.id],
    queryFn: async () => (await api.get<Course[]>(root)).data,
  });
  const detail = useQuery({
    queryKey: ["campus-learning-course", user?.id, inst.id, selected],
    queryFn: async () => (await api.get<Course>(`${root}/${selected}`)).data,
    enabled: !!selected,
  });
  const resources = useQuery({
    queryKey: ["campus-resources", user?.id, inst.id],
    queryFn: () => campusApi.resources(inst.id),
    enabled: staff && !!selected,
  });
  const progress = useQuery({
    queryKey: ["campus-learning-progress", user?.id, inst.id, selected],
    queryFn: async () =>
      (
        await api.get<
          {
            member_id: number;
            name: string;
            completed: number;
            lessons: number;
          }[]
        >(`${root}/${selected}/progress`)
      ).data,
    enabled: staff && !!selected && showProgress,
  });
  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await list.refetch();
      if (selected) await detail.refetch();
      toast.success("Campus course saved");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setBusy(false);
    }
  }
  async function download(resource: number) {
    try {
      const blob = await campusApi.resource(inst.id, resource);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "lesson-resource";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(apiError(e));
    }
  }
  return (
    <section className="campus-panel">
      <div className="campus-toolbar">
        <div>
          <h2 className="flex items-center gap-2">
            <LockKeyhole size={18} />
            Private campus courses
          </h2>
          <p className="campus-muted mt-2">
            Lessons, resources and progress stay within your institution and
            assigned batch.
          </p>
        </div>
        {staff && (
          <Button
            onClick={() => {
              setCreate(true);
              setError("");
            }}
          >
            Create campus course
          </Button>
        )}
      </div>
      {list.isError && (
        <Button onClick={() => list.refetch()}>Retry campus courses</Button>
      )}
      {error && !selected && !create && (
        <p role="alert" className="campus-error">
          {error}
        </p>
      )}
      <div className="campus-grid mt-5">
        {list.data?.map((c) => (
          <article className="campus-panel campus-plan-featured" key={c.id}>
            <span className="campus-icon">
              <BookOpen size={21} />
            </span>
            <h3>{c.title}</h3>
            <p className="campus-muted">{c.summary}</p>
            <p className="campus-chip my-3">
              {c.published ? "Published" : "Draft"} · {c.lessons} lessons
            </p>
            <div>
              <Button
                variant="outline"
                onClick={() => {
                  setSelected(c.id);
                  setEditing(undefined);
                  setShowProgress(false);
                  setError("");
                }}
              >
                {c.can_edit
                  ? "Open course studio"
                  : c.completed
                    ? "Continue learning"
                    : "Start learning"}
              </Button>
            </div>
          </article>
        ))}
      </div>
      {list.data?.length === 0 && (
        <p className="campus-muted py-5">
          {staff
            ? "Create a private course, add lessons and publish it to your campus or a specific batch."
            : "Your published campus courses will appear here."}
        </p>
      )}
      <GlassDialog
        open={create}
        onOpenChange={setCreate}
        title="Create a private campus course"
      >
        <form
          className="campus-form"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            run(async () => {
              const r = await api.post<{ id: number }>(root, {
                title: String(f.get("title")),
                summary: String(f.get("summary")),
                batch_id: Number(f.get("batch")) || null,
              });
              setCreate(false);
              setSelected(r.data.id);
            });
          }}
        >
          <label>
            Course title
            <input name="title" required minLength={2} maxLength={160} />
          </label>
          <label>
            Course introduction
            <textarea name="summary" maxLength={1000} />
          </label>
          <label>
            Who can learn
            <select name="batch">
              <option value="">All active institution members</option>
              {data.batches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </label>
          <p className="campus-notice">
            Starts as a private draft. Learners see it after you publish. It
            never appears in the public course catalog.
          </p>
          {error && (
            <p role="alert" className="campus-error">
              {error}
            </p>
          )}
          <Button type="submit" disabled={busy}>
            Create private draft
          </Button>
        </form>
      </GlassDialog>
      <GlassDialog
        open={!!selected}
        onOpenChange={(v) => {
          if (!v) {
            setSelected(undefined);
            setEditing(undefined);
          }
        }}
        title={detail.data?.title || "Campus course"}
        size="xl"
      >
        {detail.isError && (
          <Button onClick={() => detail.refetch()}>Retry course</Button>
        )}
        {detail.isLoading && <p>Loading your course…</p>}
        {detail.data && (
          <>
            <BrandBanner
              compact
              title={detail.data.title}
              description={
                detail.data.summary ||
                "One lesson closer to your next possibility."
              }
            />
            <div className="campus-toolbar my-5">
              <span className="campus-chip">
                {detail.data.completed} / {detail.data.lessons} lessons
                completed
              </span>
              {detail.data.can_edit && (
                <div className="campus-actions">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setEditing("new");
                      setError("");
                    }}
                  >
                    Add lesson
                  </Button>
                  <Button
                    disabled={busy}
                    onClick={() =>
                      run(() =>
                        api.put(`${root}/${selected}/publish`, {
                          published: !detail.data!.published,
                        }),
                      )
                    }
                  >
                    {detail.data.published ? "Unpublish" : "Publish to campus"}
                  </Button>
                </div>
              )}
              {staff && (
                <Button
                  variant="ghost"
                  onClick={() => setShowProgress((v) => !v)}
                >
                  Learner progress
                </Button>
              )}
            </div>
            {error && (
              <p role="alert" className="campus-error">
                {error}
              </p>
            )}
            {showProgress && (
              <div className="campus-table-wrap">
                <table className="campus-table">
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>Completed lessons</th>
                    </tr>
                  </thead>
                  <tbody>
                    {progress.data?.map((p) => (
                      <tr key={p.member_id}>
                        <td>{p.name}</td>
                        <td>
                          {p.completed} / {p.lessons}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {progress.isError && (
                  <Button onClick={() => progress.refetch()}>
                    Retry learner progress
                  </Button>
                )}
              </div>
            )}
            {editing && (
              <form
                key={editing === "new" ? "new" : editing.id}
                className="campus-panel campus-form my-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  const body = {
                    title: String(f.get("title")),
                    body: String(f.get("body")),
                    resource_id: Number(f.get("resource")) || null,
                  };
                  run(async () => {
                    if (editing === "new")
                      await api.post(`${root}/${selected}/lessons`, body);
                    else
                      await api.put(
                        `${root}/${selected}/lessons/${editing.id}`,
                        body,
                      );
                    setEditing(undefined);
                  });
                }}
              >
                <h3>{editing === "new" ? "Add a lesson" : "Edit lesson"}</h3>
                <label>
                  Lesson title
                  <input
                    required
                    minLength={2}
                    maxLength={160}
                    name="title"
                    defaultValue={editing === "new" ? "" : editing.title}
                  />
                </label>
                <label>
                  Lesson content
                  <textarea
                    required
                    rows={8}
                    maxLength={32000}
                    name="body"
                    defaultValue={editing === "new" ? "" : editing.body}
                  />
                </label>
                <label>
                  Private resource
                  <select
                    name="resource"
                    defaultValue={
                      editing === "new" ? "" : editing.resource_id || ""
                    }
                  >
                    <option value="">No attachment</option>
                    {resources.data
                      ?.filter(
                        (r) =>
                          !r.batch_id || r.batch_id === detail.data?.batch_id,
                      )
                      .map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.title}
                        </option>
                      ))}
                  </select>
                </label>
                <div className="campus-actions">
                  <Button type="submit" disabled={busy}>
                    Save lesson
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => setEditing(undefined)}
                    type="button"
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            )}
            {detail.data.content?.map((l, index) => (
              <details
                className="campus-panel my-4"
                key={l.id}
                open={detail.data?.content?.length === 1 || undefined}
              >
                <summary className="cursor-pointer font-semibold">
                  {index + 1}. {l.title}
                  {l.completed && (
                    <CheckCircle2
                      size={16}
                      className="inline ml-2 text-green-700"
                    />
                  )}
                </summary>
                <div className="whitespace-pre-wrap break-words my-5 text-sm leading-7">
                  {l.body}
                </div>
                <div className="campus-actions">
                  {l.resource_id && (
                    <Button
                      variant="outline"
                      onClick={() => download(l.resource_id!)}
                    >
                      Download lesson resource
                    </Button>
                  )}
                  {detail.data?.can_edit && (
                    <Button variant="ghost" onClick={() => setEditing(l)}>
                      Edit lesson
                    </Button>
                  )}
                  {detail.data?.published && (
                    <Button
                      disabled={busy || l.completed}
                      onClick={() =>
                        run(() =>
                          api.put(
                            `${root}/${selected}/lessons/${l.id}/complete`,
                          ),
                        )
                      }
                    >
                      {l.completed ? "Completed" : "Mark lesson complete"}
                    </Button>
                  )}
                </div>
              </details>
            ))}
            {detail.data.content?.length === 0 && (
              <p className="campus-notice">
                Add your first lesson, then publish the course to your selected
                audience.
              </p>
            )}
          </>
        )}
      </GlassDialog>
    </section>
  );
}
