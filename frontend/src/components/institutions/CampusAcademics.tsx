import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { campusApi, type AcademicData } from "@/api/campus";
import type { InstitutionOverview } from "@/api/institutions";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { GlassDialog } from "@/components/ui/dialog";
import { apiError } from "./InstitutionDialog";
import { BrandBanner } from "@/components/design-system/BrandBanner";
import toast from "react-hot-toast";

export function CampusAcademics({ data }: { data: InstitutionOverview }) {
  const { institution: inst, batches } = data;
  const user = useAuthStore((s) => s.user);
  const [batch, setBatch] = useState(batches[0]?.id || 0);
  const [day, setDay] = useState(new Date().toLocaleDateString("en-CA"));
  const [dialog, setDialog] = useState<"term" | "assessment" | null>(null);
  const [selected, setSelected] = useState<number>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const staff = ["owner", "admin", "teacher"].includes(inst.role);
  const manager = ["owner", "admin"].includes(inst.role);
  const query = useQuery({
    queryKey: ["campus-academics", user?.id, inst.id, batch, day],
    queryFn: () => campusApi.academics(inst.id, batch || undefined, day),
  });
  async function command(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await query.refetch();
      setDialog(null);
      toast.success("Saved to your campus");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <BrandBanner
        compact
        title="Every lesson. Every little breakthrough."
        description="Plan your term, record attendance and make assessment feedback part of each learner’s next step."
      />
      <div className="campus-panel">
        <div className="campus-toolbar">
          <h2>Academic calendar</h2>
          {manager && (
            <Button onClick={() => setDialog("term")}>
              Add term / semester
            </Button>
          )}
        </div>
        <div className="campus-actions mt-4">
          {query.data?.terms.map((t) => (
            <span className="campus-chip" key={t.id}>
              {t.name} · {t.starts_on} – {t.ends_on}
            </span>
          ))}
          {query.data?.terms.length === 0 && (
            <p className="campus-muted">
              Add your first academic term to organize assessments.
            </p>
          )}
        </div>
      </div>
      <div className="campus-toolbar">
        <label className="campus-form">
          Academic batch
          <select
            className="campus-select"
            value={batch}
            onChange={(e) => {
              setBatch(Number(e.target.value));
              setSelected(undefined);
            }}
          >
            {!batches.length && <option value={0}>Create a batch first</option>}
            {batches.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </label>
        <label className="campus-form">
          Attendance date
          <input
            aria-label="Attendance date"
            className="campus-select"
            type="date"
            value={day}
            onChange={(e) => setDay(e.target.value)}
            max={new Date().toLocaleDateString("en-CA")}
          />
        </label>
      </div>
      {error && (
        <p role="alert" className="campus-error">
          {error}
        </p>
      )}
      {query.isError && (
        <div className="campus-error">
          Academics could not be loaded.{" "}
          <Button variant="outline" onClick={() => query.refetch()}>
            Retry
          </Button>
        </div>
      )}
      {query.isLoading ? (
        <div className="campus-skeleton" />
      ) : (
        query.data &&
        batch > 0 && (
          <>
            <Attendance
              key={`${batch}-${day}-${query.dataUpdatedAt}`}
              data={query.data}
              editable={staff}
              busy={busy}
              save={(entries) =>
                command(() =>
                  campusApi.attendance(inst.id, {
                    batch_id: batch,
                    day,
                    entries,
                  }),
                )
              }
            />
            <div className="campus-panel">
              <div className="campus-toolbar">
                <h2>Batch gradebook</h2>
                {staff && (
                  <Button onClick={() => setDialog("assessment")}>
                    Add assessment
                  </Button>
                )}
              </div>
              <p className="campus-muted my-3">
                Record classroom assessments here. Online course quizzes and
                submissions remain in the course gradebook.
              </p>
              <select
                aria-label="Assessment"
                className="campus-select"
                value={selected || ""}
                onChange={(e) => setSelected(Number(e.target.value))}
              >
                <option value="">Choose an assessment</option>
                {query.data.assessments.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.title} · {a.max_score} marks
                  </option>
                ))}
              </select>
              {query.data.assessments.find((a) => a.id === selected) && (
                <Scores
                  key={`${selected}-${query.dataUpdatedAt}`}
                  data={query.data}
                  selected={selected!}
                  editable={staff}
                  busy={busy}
                  save={(entries) =>
                    command(() => campusApi.scores(inst.id, selected!, entries))
                  }
                />
              )}
            </div>
          </>
        )
      )}
      <GlassDialog
        open={!!dialog}
        onOpenChange={(v) => {
          if (!v) setDialog(null);
        }}
        title={
          dialog === "term"
            ? "Add a term or semester"
            : "Create a classroom assessment"
        }
      >
        <form
          className="campus-form"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            if (dialog === "term")
              command(() =>
                campusApi.term(inst.id, {
                  name: String(f.get("name")),
                  starts_on: String(f.get("starts")),
                  ends_on: String(f.get("ends")),
                }),
              );
            else
              command(() =>
                campusApi.assessment(inst.id, {
                  batch_id: batch,
                  title: String(f.get("name")),
                  max_score: Number(f.get("max")),
                  term_id: Number(f.get("term")) || null,
                  due_on: String(f.get("due")) || null,
                }),
              );
          }}
        >
          {error && (
            <p role="alert" className="campus-error">
              {error}
            </p>
          )}
          <label>
            {dialog === "term" ? "Term name" : "Assessment title"}
            <input
              name="name"
              required
              maxLength={dialog === "term" ? 100 : 160}
            />
          </label>
          {dialog === "term" ? (
            <div className="campus-form-grid">
              <label>
                Starts on
                <input type="date" name="starts" required />
              </label>
              <label>
                Ends on
                <input type="date" name="ends" required />
              </label>
            </div>
          ) : (
            <>
              <label>
                Maximum score
                <input
                  type="number"
                  name="max"
                  min={1}
                  max={10000}
                  required
                  defaultValue={100}
                />
              </label>
              <label>
                Term
                <select name="term">
                  <option value="">No term</option>
                  {query.data?.terms.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Due date
                <input type="date" name="due" />
              </label>
            </>
          )}
          <Button disabled={busy} type="submit">
            {busy ? "Saving…" : "Save"}
          </Button>
        </form>
      </GlassDialog>
    </>
  );
}
function Attendance({
  data,
  editable,
  busy,
  save,
}: {
  data: AcademicData;
  editable: boolean;
  busy: boolean;
  save: (entries: { member_id: number; status: string }[]) => void;
}) {
  const [marks, setMarks] = useState<Record<number, string>>(
    Object.fromEntries(data.attendance.map((a) => [a.member_id, a.status])),
  );
  return (
    <section className="campus-panel">
      <div className="campus-toolbar">
        <h2>Daily attendance</h2>
        {editable && data.students.length > 0 && (
          <Button
            variant="outline"
            onClick={() =>
              setMarks(
                Object.fromEntries(data.students.map((s) => [s.id, "present"])),
              )
            }
          >
            Mark all present
          </Button>
        )}
      </div>
      <div className="campus-table-wrap">
        <table className="campus-table">
          <thead>
            <tr>
              <th>Student</th>
              <th>Attendance</th>
            </tr>
          </thead>
          <tbody>
            {data.students.map((s) => (
              <tr key={s.id}>
                <td>{s.name}</td>
                <td>
                  {editable ? (
                    <select
                      className="campus-select"
                      aria-label={`Attendance for ${s.name}`}
                      value={marks[s.id] || ""}
                      onChange={(e) =>
                        setMarks({ ...marks, [s.id]: e.target.value })
                      }
                    >
                      <option value="">Not recorded</option>
                      {["present", "absent", "late", "excused"].map((v) => (
                        <option key={v} value={v}>
                          {v}
                        </option>
                      ))}
                    </select>
                  ) : (
                    marks[s.id] || "Not recorded"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!data.students.length && (
        <p className="campus-muted py-5">
          Add active students to this batch to record attendance.
        </p>
      )}
      {editable && (
        <Button
          className="mt-4"
          disabled={busy || !Object.values(marks).some(Boolean)}
          onClick={() =>
            save(
              Object.entries(marks)
                .filter(([, v]) => v)
                .map(([id, status]) => ({ member_id: Number(id), status })),
            )
          }
        >
          Save attendance
        </Button>
      )}
    </section>
  );
}
function Scores({
  data,
  selected,
  editable,
  busy,
  save,
}: {
  data: AcademicData;
  selected: number;
  editable: boolean;
  busy: boolean;
  save: (
    entries: { member_id: number; score: number; feedback: string }[],
  ) => void;
}) {
  const assessment = data.assessments.find((a) => a.id === selected)!;
  const [values, setValues] = useState<Record<number, string>>(
    Object.fromEntries(
      assessment.scores.map((s) => [s.member_id, String(s.score)]),
    ),
  );
  const [feedback, setFeedback] = useState<Record<number, string>>(
    Object.fromEntries(assessment.scores.map((s) => [s.member_id, s.feedback])),
  );
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        save(
          Object.entries(values)
            .filter(([, v]) => v !== "")
            .map(([id, score]) => ({
              member_id: Number(id),
              score: Number(score),
              feedback: feedback[Number(id)] || "",
            })),
        );
      }}
    >
      <div className="campus-table-wrap">
        <table className="campus-table">
          <thead>
            <tr>
              <th>Student</th>
              <th>Score / {assessment.max_score}</th>
              <th>Feedback</th>
            </tr>
          </thead>
          <tbody>
            {data.students.map((s) => (
              <tr key={s.id}>
                <td>{s.name}</td>
                <td>
                  {editable ? (
                    <input
                      className="campus-select"
                      type="number"
                      min={0}
                      max={assessment.max_score}
                      step="any"
                      aria-label={`Score for ${s.name}`}
                      value={values[s.id] ?? ""}
                      onChange={(e) =>
                        setValues({ ...values, [s.id]: e.target.value })
                      }
                    />
                  ) : (
                    (values[s.id] ?? "Not graded")
                  )}
                </td>
                <td>
                  {editable ? (
                    <input
                      className="campus-select"
                      aria-label={`Feedback for ${s.name}`}
                      maxLength={1000}
                      value={feedback[s.id] || ""}
                      onChange={(e) =>
                        setFeedback({ ...feedback, [s.id]: e.target.value })
                      }
                    />
                  ) : (
                    feedback[s.id] || "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editable && (
        <Button
          className="mt-4"
          disabled={busy || !Object.values(values).some((v) => v !== "")}
          type="submit"
        >
          Save grades
        </Button>
      )}
    </form>
  );
}
