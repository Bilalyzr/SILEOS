import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { GlassDialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  institutionApi,
  type InstitutionOverview,
  type InstitutionBatch,
  type InstitutionMember,
  type Institution,
} from "@/api/institutions";

export type InstitutionDialogState = {
  kind:
    | "create"
    | "invite"
    | "batch"
    | "connect"
    | "assign"
    | "students"
    | "member"
    | "plan";
  batch?: InstitutionBatch;
  member?: InstitutionMember;
  plan?: string;
};
const titles = {
  create: "Create your institution",
  invite: "Invite a member",
  batch: "Create a batch",
  connect: "Connect a course",
  assign: "Assign a course",
  students: "Manage batch students",
  member: "Manage member access",
  plan: "Request a plan",
};
const labels = {
  create: "Create institution",
  invite: "Create invitation",
  batch: "Create batch",
  connect: "Connect course",
  assign: "Assign course",
  students: "Add selected students",
  member: "Save access",
  plan: "Save request",
};
export function apiError(error: unknown) {
  const detail = (error as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail;
  return typeof detail === "string"
    ? detail
    : "We couldn’t save this change. Please check your connection and try again.";
}

export function InstitutionDialog({
  state,
  data,
  accountId,
  close,
  changed,
}: {
  state: InstitutionDialogState;
  data?: InstitutionOverview;
  accountId?: number;
  close: () => void;
  changed: (created?: Institution) => Promise<void>;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const id = data?.institution.id || 0;
  const currentYear = new Date().getFullYear();
  const year =
    data?.institution.academic_year || `${currentYear}–${currentYear + 1}`;
  const available = useQuery({
    queryKey: ["institution-courses", accountId, id],
    queryFn: () => institutionApi.available(id),
    enabled: state.kind === "connect" && !!id,
  });
  const courses =
    available.data?.filter(
      (c) => !data?.courses.some((existing) => existing.course_id === c.id),
    ) || [];
  const students =
    data?.members.filter(
      (m) => m.role === "student" && m.status === "active",
    ) || [];
  const unassigned = students.filter(
    (m) => !state.batch?.member_ids.includes(m.id),
  );
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const text = (name: string) => String(form.get(name) || "").trim();
    setError("");
    setPending(true);
    try {
      let created: Institution | undefined;
      switch (state.kind) {
        case "create":
          created = await institutionApi.create({
            name: text("name"),
            kind: text("kind") as "school" | "college",
            academic_year: text("academic_year"),
            timezone: text("timezone"),
            description: text("description"),
          });
          break;
        case "invite":
          await institutionApi.invite(id, {
            email: text("email"),
            role: text("role"),
            department: text("department"),
          });
          break;
        case "batch":
          await institutionApi.batch(id, {
            name: text("name"),
            department: text("department"),
            academic_year: text("academic_year"),
          });
          break;
        case "connect":
          await institutionApi.connect(id, Number(text("course_id")));
          break;
        case "assign":
          await institutionApi.assign(
            id,
            state.batch!.id,
            Number(text("course_id")),
            text("due_date") || null,
          );
          break;
        case "students":
          await institutionApi.addStudents(id, state.batch!.id, selected);
          break;
        case "member":
          await institutionApi.updateMember(id, state.member!.id, {
            role: text("role"),
            status: text("status"),
            department: text("department"),
          });
          break;
        case "plan":
          await institutionApi.requestPlan(
            id,
            state.plan || "campus",
            text("note"),
          );
          break;
      }
      await changed(created);
      close();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setPending(false);
    }
  }
  const cannotSubmit =
    pending ||
    (state.kind === "connect" && !courses.length) ||
    (state.kind === "students" && !selected.length) ||
    (state.kind === "assign" &&
      !data?.courses.some((c) => c.status === "published" || c.status === "publish"));
  return (
    <GlassDialog
      open
      onOpenChange={(open) => {
        if (!open && !pending) close();
      }}
      title={titles[state.kind]}
      description={
        state.batch ? state.batch.name : "Your institution. Connected learning."
      }
      eyebrow="SashaInfinity Campus"
      size="md"
    >
      <form className="campus-form" onSubmit={submit}>
        {error && (
          <p role="alert" className="campus-error">
            {error}
          </p>
        )}
        {state.kind === "create" && (
          <>
            <label>
              Institution name
              <input
                name="name"
                required
                minLength={2}
                maxLength={160}
                placeholder="e.g. Greenwood College"
                autoFocus
              />
            </label>
            <div className="campus-form-grid">
              <label>
                Institution type
                <select name="kind">
                  <option value="school">School</option>
                  <option value="college">College</option>
                </select>
              </label>
              <label>
                Academic year
                <input
                  name="academic_year"
                  required
                  minLength={4}
                  maxLength={32}
                  defaultValue={year}
                />
              </label>
            </div>
            <label>
              Timezone
              <select name="timezone">
                <option value="Asia/Kolkata">India · Asia/Kolkata</option>
                <option value="UTC">UTC</option>
                <option value="Europe/London">Europe/London</option>
                <option value="America/New_York">America/New_York</option>
                <option value="Asia/Dubai">Asia/Dubai</option>
              </select>
            </label>
            <label>
              About your institution
              <textarea
                name="description"
                maxLength={1000}
                placeholder="What makes your learning community special?"
              />
            </label>
            <p className="campus-notice">
              Start with space for 100 members, 10 batches and 20 connected
              courses. You’ll become this institution’s owner.
            </p>
          </>
        )}
        {state.kind === "invite" && (
          <>
            <label>
              Email address
              <input
                type="email"
                name="email"
                required
                maxLength={254}
                placeholder="name@school.edu"
                autoFocus
              />
            </label>
            <label>
              Institution role
              <select name="role" defaultValue="student">
                <option value="student">
                  Student · own batches and progress
                </option>
                <option value="teacher">
                  Teacher · courses and learning reports
                </option>
                {data?.institution.role === "owner" && (
                  <option value="admin">
                    Administrator · people and academic setup
                  </option>
                )}
              </select>
            </label>
            <label>
              Department
              <input
                name="department"
                maxLength={100}
                placeholder="e.g. Science"
              />
            </label>
            <p className="campus-notice">
              The invitation appears in the recipient’s Campus inbox after they
              sign in with this verified email. It expires in seven days. No
              email is sent automatically.
            </p>
          </>
        )}
        {state.kind === "batch" && (
          <>
            <label>
              Batch or class name
              <input
                name="name"
                required
                minLength={2}
                maxLength={100}
                placeholder="e.g. Grade 11 · Section A"
                autoFocus
              />
            </label>
            <label>
              Department
              <input
                name="department"
                maxLength={100}
                placeholder="e.g. Higher secondary"
              />
            </label>
            <label>
              Academic year
              <input
                name="academic_year"
                required
                minLength={4}
                maxLength={32}
                defaultValue={year}
              />
            </label>
          </>
        )}
        {state.kind === "connect" && (
          <>
            {available.isPending ? (
              <p role="status">Loading your courses…</p>
            ) : available.isError ? (
              <div role="alert" className="campus-error">
                Couldn’t load courses.{" "}
                <button type="button" onClick={() => void available.refetch()}>
                  Retry
                </button>
              </div>
            ) : (
              <label>
                Choose an existing course
                <select name="course_id" required defaultValue="">
                  <option value="" disabled>
                    Select a course
                  </option>
                  {courses.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.title} · {c.status}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {!available.isPending && !available.isError && !courses.length && (
              <p className="campus-notice">
                No new editable courses are available. A teacher can connect a
                course they own or collaborate on.
              </p>
            )}
            <p className="campus-muted">
              Connecting a course keeps its current catalog visibility and
              teaching permissions.
            </p>
          </>
        )}
        {state.kind === "assign" && (
          <>
            <label>
              Published course
              <select name="course_id" required defaultValue="">
                <option value="" disabled>
                  Select a course
                </option>
                {data?.courses
                  .filter((c) => c.status === "published" || c.status === "publish")
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.title}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Due date (optional)
              <input type="date" name="due_date" />
            </label>
            <p className="campus-notice">
              Adds the course to this batch’s learning plan. Students still need
              course enrollment; this action does not purchase or unlock paid
              content. Reassigning updates the due date.
            </p>
          </>
        )}
        {state.kind === "students" && (
          <>
            <p className="campus-muted">
              Choose active students to add to {state.batch?.name}.
            </p>
            {!unassigned.length && (
              <p className="campus-notice">
                Every available student is already in this batch, or no student
                has joined yet.
              </p>
            )}
            {unassigned.map((m) => (
              <label className="campus-check" key={m.id}>
                <input
                  type="checkbox"
                  checked={selected.includes(m.id)}
                  onChange={(e) =>
                    setSelected((prev) =>
                      e.target.checked
                        ? [...prev, m.id]
                        : prev.filter((v) => v !== m.id),
                    )
                  }
                />
                {m.name} <span className="campus-muted">{m.email}</span>
              </label>
            ))}
            {!!state.batch?.member_ids.length && (
              <div>
                <p className="campus-muted">
                  {state.batch.student_count} students already in this batch.
                </p>
                {students
                  .filter((m) => state.batch?.member_ids.includes(m.id))
                  .map((m) => (
                    <div className="campus-step" key={m.id}>
                      <span className="campus-step-copy">{m.name}</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        disabled={pending}
                        onClick={async () => {
                          setPending(true);
                          setError("");
                          try {
                            await institutionApi.removeStudent(
                              id,
                              state.batch!.id,
                              m.id,
                            );
                            await changed();
                            close();
                          } catch (err) {
                            setError(apiError(err));
                          } finally {
                            setPending(false);
                          }
                        }}
                      >
                        Remove
                        <span className="sr-only">
                          {" "}
                          {m.name} from this batch
                        </span>
                      </Button>
                    </div>
                  ))}
              </div>
            )}
          </>
        )}
        {state.kind === "member" && (
          <>
            <p className="campus-muted">
              {state.member?.name} · {state.member?.email}
            </p>
            <label>
              Institution role
              <select name="role" defaultValue={state.member?.role}>
                <option value="student">Student</option>
                <option value="teacher">Teacher</option>
                {data?.institution.role === "owner" && (
                  <option value="admin">Administrator</option>
                )}
              </select>
            </label>
            <label>
              Department
              <input
                name="department"
                defaultValue={state.member?.department}
                maxLength={100}
              />
            </label>
            <label>
              Workspace access
              <select name="status" defaultValue={state.member?.status}>
                <option value="active">Active</option>
                <option value="suspended">Suspended</option>
              </select>
            </label>
            <p className="campus-notice">
              Suspension removes access to this institution. The member’s
              personal LMS account and separately purchased courses remain
              available.
            </p>
          </>
        )}
        {state.kind === "plan" && (
          <>
            <p className="campus-notice">
              Request the {state.plan} plan for your institution. This saves a
              request for platform review; it does not charge you or change your
              current limits.
            </p>
            <label>
              Your requirements
              <textarea
                name="note"
                maxLength={1000}
                placeholder="Expected students, campuses, integrations and your preferred start date…"
                autoFocus
              />
            </label>
          </>
        )}
        <div
          className="campus-actions"
          style={{ justifyContent: "flex-end", marginTop: 6 }}
        >
          <Button
            type="button"
            variant="outline"
            disabled={pending}
            onClick={close}
          >
            Cancel
          </Button>
          <Button type="submit" loading={pending} disabled={cannotSubmit}>
            {labels[state.kind]}
          </Button>
        </div>
      </form>
    </GlassDialog>
  );
}
