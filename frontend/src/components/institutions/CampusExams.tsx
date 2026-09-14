import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { campusApi } from "@/api/campus";
import {
  examsApi,
  openBlob,
  type Exam,
  type ExamKind,
  type ExamPaper,
  type MarkEntry,
  type MyResult,
  type RosterRow,
} from "@/api/campus-exams";
import type { InstitutionOverview } from "@/api/institutions";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { GlassDialog } from "@/components/ui/dialog";
import { BrandBanner } from "@/components/design-system/BrandBanner";
import { apiError } from "./InstitutionDialog";
import { CampusOsBadge, CampusOsEmpty, formatDate, formatTime } from "./CampusOsPrimitives";

const KINDS: { value: ExamKind; label: string }[] = [
  { value: "unit", label: "Unit test" },
  { value: "midterm", label: "Mid-term" },
  { value: "final", label: "Final" },
  { value: "practical", label: "Practical" },
  { value: "other", label: "Other" },
];

const STATUS_TONE: Record<Exam["status"], "neutral" | "orange" | "success"> = {
  draft: "neutral",
  scheduled: "orange",
  published: "success",
};

export function CampusExams({
  data,
  studentUserId,
}: {
  data: InstitutionOverview;
  studentUserId?: number;
}) {
  const { institution: inst, batches } = data;
  const user = useAuthStore((s) => s.user);
  const staff = ["owner", "admin", "teacher"].includes(inst.role);
  const manager = ["owner", "admin"].includes(inst.role);
  const [term, setTerm] = useState<number>(0);
  const [selected, setSelected] = useState<number>();
  const [dialog, setDialog] = useState<"exam" | "paper" | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const academics = useQuery({
    queryKey: ["campus-exams-terms", user?.id, inst.id],
    queryFn: () => campusApi.academics(inst.id),
    enabled: staff,
  });
  const terms = useMemo(() => academics.data?.terms ?? [], [academics.data]);
  useEffect(() => {
    if (!term && terms.length) setTerm(terms[terms.length - 1].id);
  }, [terms, term]);

  const exams = useQuery({
    queryKey: ["campus-exams", user?.id, inst.id, staff ? term : "mine"],
    queryFn: () =>
      examsApi.list(inst.id, staff && term ? term : undefined, staff ? undefined : studentUserId),
    enabled: !staff || term > 0,
  });
  const current = exams.data?.find((e) => e.id === selected) ?? exams.data?.[0];

  async function command(fn: () => Promise<unknown>, message = "Saved to your campus") {
    setBusy(true);
    setError("");
    try {
      await fn();
      await exams.refetch();
      setDialog(null);
      toast.success(message);
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
        title="Every exam, from schedule to results."
        description={
          staff
            ? "Schedule papers on the timetable, enter marks, issue hall tickets and publish results when you are ready."
            : "Your hall tickets and published results live here."
        }
      />
      {staff && (
        <div className="campus-panel">
          <div className="campus-toolbar">
            <label className="campus-form">
              Academic term
              <select
                className="campus-select"
                aria-label="Academic term"
                value={term}
                onChange={(e) => {
                  setTerm(Number(e.target.value));
                  setSelected(undefined);
                }}
              >
                {!terms.length && <option value={0}>Create a term first</option>}
                {terms.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <Button disabled={!term} onClick={() => setDialog("exam")}>
              New exam
            </Button>
          </div>
        </div>
      )}
      {error && (
        <p role="alert" className="campus-error">
          {error}
        </p>
      )}
      {exams.isError && (
        <div className="campus-error">
          Exams could not be loaded.{" "}
          <Button variant="outline" onClick={() => exams.refetch()}>
            Retry
          </Button>
        </div>
      )}
      {exams.isLoading && <div className="campus-skeleton" />}
      {exams.data && exams.data.length === 0 && (
        <CampusOsEmpty
          title={staff ? "No exams scheduled in this term" : "No exams yet"}
          description={
            staff
              ? "Create an exam, then add one paper per batch and subject."
              : "Your hall tickets and results will appear once an exam is scheduled."
          }
        />
      )}
      {exams.data && exams.data.length > 0 && (
        <div className="campus-columns">
          <section className="campus-panel">
            <h2>Exams</h2>
            <ul className="campus-activity" aria-label="Exam list">
              {exams.data.map((exam) => (
                <li key={exam.id}>
                  <button
                    type="button"
                    className="campus-chip"
                    aria-pressed={current?.id === exam.id}
                    onClick={() => setSelected(exam.id)}
                  >
                    {exam.name}
                  </button>{" "}
                  <CampusOsBadge tone={STATUS_TONE[exam.status]}>{exam.status}</CampusOsBadge>
                </li>
              ))}
            </ul>
          </section>
          {current && staff && (
            <StaffExam
              institutionId={inst.id}
              exam={current}
              batches={batches}
              manager={manager}
              busy={busy}
              command={command}
              onAddPaper={() => setDialog("paper")}
            />
          )}
          {current && !staff && (
            <LearnerExam institutionId={inst.id} exam={current} studentUserId={studentUserId} />
          )}
        </div>
      )}
      <GlassDialog
        open={!!dialog}
        onOpenChange={(v) => {
          if (!v) setDialog(null);
        }}
        title={dialog === "exam" ? "New exam" : "Add paper"}
      >
        {dialog === "exam" && (
          <form
            className="campus-form-grid"
            onSubmit={(e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              void command(() =>
                examsApi.create(inst.id, {
                  term_id: term,
                  name: String(form.get("name") || "").trim(),
                  kind: String(form.get("kind") || "other") as ExamKind,
                }),
              );
            }}
          >
            <label className="campus-form">
              Exam name
              <input className="campus-select" name="name" required maxLength={160} placeholder="Mid-term 2026" />
            </label>
            <label className="campus-form">
              Kind
              <select className="campus-select" name="kind" defaultValue="other">
                {KINDS.map((k) => (
                  <option key={k.value} value={k.value}>
                    {k.label}
                  </option>
                ))}
              </select>
            </label>
            <Button type="submit" disabled={busy}>
              Create exam
            </Button>
          </form>
        )}
        {dialog === "paper" && current && (
          <form
            className="campus-form-grid"
            onSubmit={(e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              const startsLocal = String(form.get("starts_at") || "");
              void command(() =>
                examsApi.createPaper(inst.id, current.id, {
                  batch_id: Number(form.get("batch_id")),
                  subject: String(form.get("subject") || "").trim(),
                  max_marks: Number(form.get("max_marks")),
                  pass_marks: Number(form.get("pass_marks")),
                  starts_at: new Date(startsLocal).toISOString(),
                  duration_minutes: Number(form.get("duration_minutes")),
                  room: String(form.get("room") || "").trim(),
                }),
              );
            }}
          >
            <label className="campus-form">
              Batch
              <select className="campus-select" name="batch_id" required defaultValue={batches[0]?.id}>
                {batches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="campus-form">
              Subject
              <input className="campus-select" name="subject" required maxLength={120} placeholder="Physics" />
            </label>
            <label className="campus-form">
              Maximum marks
              <input className="campus-select" name="max_marks" type="number" min={1} max={1000} step="any" defaultValue={100} required />
            </label>
            <label className="campus-form">
              Pass marks
              <input className="campus-select" name="pass_marks" type="number" min={0} step="any" defaultValue={35} required />
            </label>
            <label className="campus-form">
              Starts at
              <input className="campus-select" name="starts_at" type="datetime-local" required />
            </label>
            <label className="campus-form">
              Duration (minutes)
              <input className="campus-select" name="duration_minutes" type="number" min={15} max={600} defaultValue={120} required />
            </label>
            <label className="campus-form">
              Room
              <input className="campus-select" name="room" maxLength={80} placeholder="Hall A" />
            </label>
            <Button type="submit" disabled={busy}>
              Add paper
            </Button>
          </form>
        )}
      </GlassDialog>
    </>
  );
}

function StaffExam({
  institutionId,
  exam,
  batches,
  manager,
  busy,
  command,
  onAddPaper,
}: {
  institutionId: number;
  exam: Exam;
  batches: InstitutionOverview["batches"];
  manager: boolean;
  busy: boolean;
  command: (fn: () => Promise<unknown>, message?: string) => Promise<void>;
  onAddPaper: () => void;
}) {
  const [tab, setTab] = useState<"papers" | "marks" | "tickets" | "results">("papers");
  const [paper, setPaper] = useState<number>();
  const [batch, setBatch] = useState<number>(batches[0]?.id || 0);
  const locked = exam.status === "published";
  const currentPaper = exam.papers.find((p) => p.id === paper) ?? exam.papers[0];
  return (
    <section className="campus-panel">
      <div className="campus-panel-heading">
        <div>
          <h2>{exam.name}</h2>
          <p className="campus-muted">
            {exam.term_name} · {KINDS.find((k) => k.value === exam.kind)?.label}
          </p>
        </div>
        {manager && (
          <Button
            variant={locked ? "outline" : "default"}
            disabled={busy || exam.papers.length === 0}
            onClick={() =>
              command(
                () => (locked ? examsApi.unpublish(institutionId, exam.id) : examsApi.publish(institutionId, exam.id)),
                locked ? "Results withdrawn" : "Results published",
              )
            }
          >
            {locked ? "Unpublish results" : "Publish results"}
          </Button>
        )}
      </div>
      <div className="campus-tabs" role="tablist">
        {(["papers", "marks", "tickets", "results"] as const).map((key) => (
          <button
            key={key}
            role="tab"
            type="button"
            aria-selected={tab === key}
            className="campus-chip"
            onClick={() => setTab(key)}
          >
            {{ papers: "Papers", marks: "Marks", tickets: "Hall tickets", results: "Results" }[key]}
          </button>
        ))}
      </div>
      {tab === "papers" && (
        <>
          <div className="campus-toolbar mt-4">
            <p className="campus-muted">One paper per batch and subject. Each paper is placed on the timetable.</p>
            <Button disabled={busy || locked} onClick={onAddPaper}>
              Add paper
            </Button>
          </div>
          {exam.papers.length === 0 ? (
            <p className="campus-muted mt-4">No papers yet.</p>
          ) : (
            <div className="campus-table-wrap">
              <table className="campus-table">
                <thead>
                  <tr>
                    <th>Subject</th>
                    <th>Batch</th>
                    <th>When</th>
                    <th>Room</th>
                    <th>Marks</th>
                    <th>Entered</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {exam.papers.map((p) => (
                    <tr key={p.id}>
                      <td>{p.subject}</td>
                      <td>{p.batch_name}</td>
                      <td>
                        {formatDate(p.starts_at)} · {formatTime(p.starts_at)} – {formatTime(p.ends_at)}
                      </td>
                      <td>{p.room || "—"}</td>
                      <td>
                        {p.max_marks} (pass {p.pass_marks})
                      </td>
                      <td>
                        {p.marks_entered} / {p.students}
                      </td>
                      <td>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={busy || locked || p.marks_entered > 0}
                          onClick={() =>
                            command(() => examsApi.deletePaper(institutionId, exam.id, p.id), "Paper removed")
                          }
                        >
                          Remove
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
      {tab === "marks" && (
        <>
          <label className="campus-form mt-4">
            Paper
            <select
              className="campus-select"
              aria-label="Paper"
              value={currentPaper?.id ?? ""}
              onChange={(e) => setPaper(Number(e.target.value))}
            >
              {exam.papers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.subject} · {p.batch_name}
                </option>
              ))}
            </select>
          </label>
          {currentPaper ? (
            <MarksGrid
              key={currentPaper.id}
              institutionId={institutionId}
              exam={exam}
              paper={currentPaper}
              locked={locked}
              busy={busy}
              command={command}
            />
          ) : (
            <p className="campus-muted mt-4">Add a paper before entering marks.</p>
          )}
        </>
      )}
      {tab === "tickets" && <HallTickets institutionId={institutionId} exam={exam} />}
      {tab === "results" && (
        <>
          <label className="campus-form mt-4">
            Batch
            <select className="campus-select" aria-label="Results batch" value={batch} onChange={(e) => setBatch(Number(e.target.value))}>
              {batches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </label>
          {batch > 0 && <ResultsTable institutionId={institutionId} exam={exam} batchId={batch} />}
        </>
      )}
    </section>
  );
}

function MarksGrid({
  institutionId,
  exam,
  paper,
  locked,
  busy,
  command,
}: {
  institutionId: number;
  exam: Exam;
  paper: ExamPaper;
  locked: boolean;
  busy: boolean;
  command: (fn: () => Promise<unknown>, message?: string) => Promise<void>;
}) {
  const roster = useQuery({
    queryKey: ["campus-exam-roster", institutionId, exam.id, paper.id],
    queryFn: () => examsApi.roster(institutionId, exam.id, paper.id),
  });
  const [rows, setRows] = useState<Record<number, MarkEntry>>({});
  useEffect(() => {
    if (roster.data) {
      setRows(
        Object.fromEntries(
          roster.data.map((r) => [
            r.member_id,
            { member_id: r.member_id, marks: r.marks, absent: r.absent, remarks: r.remarks },
          ]),
        ),
      );
    }
  }, [roster.data]);
  const list: RosterRow[] = roster.data ?? [];
  if (roster.isLoading) return <div className="campus-skeleton" />;
  if (roster.isError)
    return (
      <div className="campus-error">
        Roster could not be loaded.{" "}
        <Button variant="outline" onClick={() => roster.refetch()}>
          Retry
        </Button>
      </div>
    );
  if (!list.length) return <p className="campus-muted mt-4">No active students in this batch.</p>;
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const entries = Object.values(rows).filter((r) => r.absent || r.marks !== null);
        void command(
          () => examsApi.putMarks(institutionId, exam.id, paper.id, entries).then(() => roster.refetch()),
          "Marks saved",
        );
      }}
    >
      <div className="campus-table-wrap">
        <table className="campus-table">
          <thead>
            <tr>
              <th>Roll no.</th>
              <th>Student</th>
              <th>Marks / {paper.max_marks}</th>
              <th>Absent</th>
              <th>Remarks</th>
            </tr>
          </thead>
          <tbody>
            {list.map((s) => {
              const row = rows[s.member_id] ?? { member_id: s.member_id, marks: null, absent: false, remarks: "" };
              return (
                <tr key={s.member_id}>
                  <td>{s.roll_number}</td>
                  <td>{s.name}</td>
                  <td>
                    <input
                      className="campus-select"
                      type="number"
                      min={0}
                      max={paper.max_marks}
                      step="any"
                      disabled={locked || row.absent}
                      aria-label={`Marks for ${s.name}`}
                      value={row.marks ?? ""}
                      onChange={(e) =>
                        setRows({
                          ...rows,
                          [s.member_id]: { ...row, marks: e.target.value === "" ? null : Number(e.target.value) },
                        })
                      }
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      className="campus-check"
                      disabled={locked}
                      aria-label={`Absent ${s.name}`}
                      checked={row.absent}
                      onChange={(e) =>
                        setRows({
                          ...rows,
                          [s.member_id]: { ...row, absent: e.target.checked, marks: e.target.checked ? null : row.marks },
                        })
                      }
                    />
                  </td>
                  <td>
                    <input
                      className="campus-select"
                      maxLength={500}
                      disabled={locked}
                      aria-label={`Remarks for ${s.name}`}
                      value={row.remarks}
                      onChange={(e) => setRows({ ...rows, [s.member_id]: { ...row, remarks: e.target.value } })}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {locked ? (
        <p className="campus-muted mt-4">Results are published. Unpublish to change marks.</p>
      ) : (
        <Button className="mt-4" type="submit" disabled={busy}>
          Save marks
        </Button>
      )}
    </form>
  );
}

function HallTickets({ institutionId, exam }: { institutionId: number; exam: Exam }) {
  const tickets = useQuery({
    queryKey: ["campus-hall-tickets", institutionId, exam.id],
    queryFn: () => examsApi.hallTickets(institutionId, exam.id),
    enabled: exam.papers.length > 0,
  });
  if (!exam.papers.length) return <p className="campus-muted mt-4">Add a paper to issue hall tickets.</p>;
  if (tickets.isLoading) return <div className="campus-skeleton" />;
  if (tickets.isError)
    return (
      <div className="campus-error">
        Hall tickets could not be issued.{" "}
        <Button variant="outline" onClick={() => tickets.refetch()}>
          Retry
        </Button>
      </div>
    );
  return (
    <div className="campus-table-wrap">
      <table className="campus-table">
        <thead>
          <tr>
            <th>Roll no.</th>
            <th>Student</th>
            <th>Issued</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {(tickets.data ?? []).map((t) => (
            <tr key={t.id}>
              <td>{t.roll_number}</td>
              <td>{t.name}</td>
              <td>{t.issued_at ? formatDate(t.issued_at) : "—"}</td>
              <td>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    examsApi
                      .hallTicketPdf(institutionId, exam.id, t.member_id)
                      .then((blob) => openBlob(blob, `hall-ticket-${t.roll_number}.pdf`))
                      .catch((e) => toast.error(apiError(e)))
                  }
                >
                  Download
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResultsTable({ institutionId, exam, batchId }: { institutionId: number; exam: Exam; batchId: number }) {
  const results = useQuery({
    queryKey: ["campus-exam-results", institutionId, exam.id, batchId, exam.status],
    queryFn: () => examsApi.results(institutionId, exam.id, batchId),
  });
  if (results.isLoading) return <div className="campus-skeleton" />;
  if (results.isError)
    return (
      <div className="campus-error">
        Results could not be loaded.{" "}
        <Button variant="outline" onClick={() => results.refetch()}>
          Retry
        </Button>
      </div>
    );
  const table = results.data;
  if (!table || !table.papers.length) return <p className="campus-muted mt-4">No papers for this batch.</p>;
  return (
    <div className="campus-table-wrap">
      <table className="campus-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Roll no.</th>
            <th>Student</th>
            {table.papers.map((p) => (
              <th key={p.id}>{p.subject}</th>
            ))}
            <th>Total</th>
            <th>%</th>
            <th>Result</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {table.rows.map((r) => (
            <tr key={r.member_id}>
              <td>{r.rank}</td>
              <td>{r.roll_number}</td>
              <td>{r.name}</td>
              {table.papers.map((p) => {
                const m = r.marks[p.id];
                return <td key={p.id}>{m?.absent ? "Absent" : (m?.marks ?? "—")}</td>;
              })}
              <td>
                {r.total} / {r.max_total}
              </td>
              <td>{r.percent ?? "—"}</td>
              <td>
                <CampusOsBadge tone={r.passed ? "success" : "warning"}>{r.passed ? "Pass" : "Fail"}</CampusOsBadge>
              </td>
              <td>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    examsApi
                      .marksheetPdf(institutionId, exam.id, r.member_id)
                      .then((blob) => openBlob(blob, `marksheet-${r.roll_number}.pdf`))
                      .catch((e) => toast.error(apiError(e)))
                  }
                >
                  Mark sheet
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LearnerExam({
  institutionId,
  exam,
  studentUserId,
}: {
  institutionId: number;
  exam: Exam;
  studentUserId?: number;
}) {
  const user = useAuthStore((s) => s.user);
  const parent = user?.role === "parent";
  const sid = parent ? studentUserId : undefined;
  const published = exam.status === "published";
  const result = useQuery<MyResult>({
    queryKey: ["campus-my-result", institutionId, exam.id, sid],
    queryFn: () => examsApi.myResults(institutionId, exam.id, sid),
    enabled: published,
  });
  const memberId = useMemo(() => result.data?.member_id, [result.data]);
  return (
    <section className="campus-panel">
      <div className="campus-panel-heading">
        <div>
          <h2>{exam.name}</h2>
          <p className="campus-muted">{exam.term_name}</p>
        </div>
        <CampusOsBadge tone={STATUS_TONE[exam.status]}>{published ? "Results published" : "Scheduled"}</CampusOsBadge>
      </div>
      <h3 className="mt-4">Timetable</h3>
      <div className="campus-table-wrap">
        <table className="campus-table">
          <thead>
            <tr>
              <th>Subject</th>
              <th>When</th>
              <th>Room</th>
              <th>Max marks</th>
            </tr>
          </thead>
          <tbody>
            {exam.papers.map((p) => (
              <tr key={p.id}>
                <td>{p.subject}</td>
                <td>
                  {formatDate(p.starts_at)} · {formatTime(p.starts_at)} – {formatTime(p.ends_at)}
                </td>
                <td>{p.room || "—"}</td>
                <td>{p.max_marks}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {published && result.isLoading && <div className="campus-skeleton" />}
      {published && result.data && (
        <>
          <h3 className="mt-4">Results</h3>
          <div className="campus-table-wrap">
            <table className="campus-table">
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Marks</th>
                  <th>Pass marks</th>
                  <th>Remarks</th>
                </tr>
              </thead>
              <tbody>
                {result.data.papers.map((p) => {
                  const m = result.data!.marks[p.id];
                  return (
                    <tr key={p.id}>
                      <td>{p.subject}</td>
                      <td>
                        {m?.absent ? "Absent" : (m?.marks ?? "Pending")} / {p.max_marks}
                      </td>
                      <td>{p.pass_marks}</td>
                      <td>{m?.remarks || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="mt-4">
            Total {result.data.total} / {result.data.max_total} ({result.data.percent ?? "—"}%) · Rank {result.data.rank} of{" "}
            {result.data.students} ·{" "}
            <CampusOsBadge tone={result.data.passed ? "success" : "warning"}>{result.data.passed ? "Pass" : "Fail"}</CampusOsBadge>
          </p>
        </>
      )}
      {published && result.isError && (
        <div className="campus-error">
          Results could not be loaded.{" "}
          <Button variant="outline" onClick={() => result.refetch()}>
            Retry
          </Button>
        </div>
      )}
      <div className="campus-actions mt-4">
        <Button
          variant="outline"
          onClick={() =>
            examsApi
              .myHallTicketPdf(institutionId, exam.id, sid)
              .then((blob) => openBlob(blob, `hall-ticket-${exam.id}.pdf`))
              .catch((e) => toast.error(apiError(e)))
          }
        >
          Download hall ticket
        </Button>
        {published && memberId && (
          <Button
            onClick={() =>
              examsApi
                .marksheetPdf(institutionId, exam.id, memberId, sid)
                .then((blob) => openBlob(blob, `marksheet-${exam.id}.pdf`))
                .catch((e) => toast.error(apiError(e)))
            }
          >
            Download mark sheet
          </Button>
        )}
      </div>
    </section>
  );
}
