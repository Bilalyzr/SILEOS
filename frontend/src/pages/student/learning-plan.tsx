import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarDays, CheckCircle2, Clock3, Target } from "lucide-react";
import { GlassDialog } from "@/components/ui/dialog";
import {
  plannerAPI,
  plannerError,
  interventionLabels,
  type PlannerData,
  type PlanGoal,
  type PlanTask,
  type GoalInput,
  type PlanOutcome,
} from "@/api/planner";
import type { AdaptiveBuild } from "@/api/signals";

const inputClass = "si-input w-full mt-1";
const dayLabel = (date: string) =>
  new Date(`${date}T12:00:00`).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
const defaultDate = () => {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export default function LearningPlanPage() {
  const [data, setData] = useState<PlannerData | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<GoalInput | null>(null);
  const [check, setCheck] = useState<PlanTask | null>(null);
  const load = useCallback(async () => {
    try {
      setError("");
      setData(await plannerAPI.me());
    } catch (e) {
      setError(plannerError(e));
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  const replace = (goal: PlanGoal) =>
    setData((d) =>
      d
        ? {
            ...d,
            goals: [...d.goals.filter((g) => g.id !== goal.id), goal].sort(
              (a, b) => a.id - b.id,
            ),
          }
        : d,
    );
  const run = async (action: () => Promise<PlanGoal>) => {
    setBusy(true);
    setError("");
    try {
      replace(await action());
    } catch (e) {
      setError(plannerError(e));
    } finally {
      setBusy(false);
    }
  };
  const create = () =>
    setEditing({
      course_id: data?.courses[0]?.id ?? 0,
      title: "",
      target_date: defaultDate(),
      daily_minutes: 30,
      timezone:
        Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Kolkata",
      status: "active",
    });
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing) return;
    setBusy(true);
    setError("");
    try {
      replace(await plannerAPI.save(editing));
      setEditing(null);
    } catch (err) {
      setError(plannerError(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-orange-600">
              Your next step
            </p>
            <h1 className="dash-h1 mt-1">My learning plan</h1>
            <p className="text-slate-600 mt-2 max-w-2xl">
              A manageable plan for your goals, with understanding checks and
              time to revisit what you learn.
            </p>
          </div>
          <button
            className="si-btn-primary"
            onClick={create}
            disabled={!data?.courses.length || busy}
          >
            <Target className="w-4 h-4" /> Set a goal
          </button>
        </PageHeader>
      }
      className="rd-screen rd-screen-student-learning-plan"
    >
      {error && (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800"
        >
          {error}{" "}
          {!data && (
            <button className="underline ml-2" onClick={() => void load()}>
              Retry
            </button>
          )}
        </div>
      )}
      {!data && !error && <p role="status">Loading your learning plan…</p>}
      {data && !data.courses.length && (
        <div className="glass-panel rounded-2xl p-8">
          <h2 className="text-lg font-semibold">Start with a course</h2>
          <p className="mt-2 text-slate-600">
            Enroll in a course to create a learning goal and daily plan.
          </p>
          <Link className="si-btn-primary inline-flex mt-4" to="/courses">
            Browse courses
          </Link>
        </div>
      )}
      {data && data.courses.length > 0 && data.goals.length === 0 && (
        <div className="glass-panel rounded-2xl p-8">
          <CalendarDays className="w-10 h-10 text-orange-500 mb-3" />
          <h2 className="text-xl font-semibold">Make room for progress</h2>
          <p className="text-slate-600 mt-2">
            Choose a course, a target date, and the minutes you can spend each
            day. We will explain why each task is suggested.
          </p>
          <button className="si-btn-primary mt-5" onClick={create}>
            Create my first plan
          </button>
        </div>
      )}
      {data && data.goals.length > 1 && (
        <p className="text-sm text-slate-600">
          Your active course budgets total{" "}
          {data.goals
            .filter((g) => g.status === "active")
            .reduce((n, g) => n + g.daily_minutes, 0)}{" "}
          minutes per day. Each course has its own budget.
        </p>
      )}
      {data?.goals.map((goal) => {
        const pending = goal.tasks.filter((t) => t.status === "pending");
        const today = pending.filter((t) => t.due_date <= goal.today);
        const upcoming = pending.filter((t) => t.due_date > goal.today);
        const done = goal.tasks.filter((t) => t.status === "done");
        return (
          <section
            key={goal.id}
            className="glass-panel rounded-2xl p-5 sm:p-6 space-y-5"
          >
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm text-orange-700">
                  {data.courses.find((c) => c.id === goal.course_id)?.title}
                </p>
                <h2 className="text-xl font-semibold mt-1">{goal.title}</h2>
                <p className="text-sm text-slate-500 mt-2">
                  {goal.daily_minutes} min/day · Target{" "}
                  {dayLabel(goal.target_date)} · {goal.timezone}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  className="si-btn-ghost"
                  onClick={() =>
                    setEditing({
                      course_id: goal.course_id,
                      title: goal.title,
                      target_date: goal.target_date,
                      daily_minutes: goal.daily_minutes,
                      timezone: goal.timezone,
                      status: goal.status,
                    })
                  }
                >
                  Edit goal
                </button>
                <button
                  className="si-btn-ghost"
                  disabled={busy || goal.status === "paused"}
                  onClick={() => void run(() => plannerAPI.refresh(goal.id))}
                >
                  Replan
                </button>
              </div>
            </div>
            {goal.warnings.map((w) => (
              <p
                key={w}
                className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900"
              >
                {w}
              </p>
            ))}
            {goal.status === "paused" ? (
              <p className="rounded-lg bg-slate-100 p-4">
                This goal is paused. Edit the goal to resume it.
              </p>
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <Clock3 className="w-4 h-4 text-orange-600" />
                  <h3 className="font-semibold">
                    Today · {today.reduce((n, t) => n + t.minutes, 0)} minutes
                  </h3>
                  <span className="text-sm text-slate-500">
                    {done.length} tasks studied or checked
                  </span>
                </div>
                {!today.length && (
                  <p className="text-sm text-slate-600">
                    Nothing scheduled today.
                    {upcoming.length
                      ? ` Your next task is ${dayLabel(upcoming[0].due_date)}.`
                      : " Replan to check for new course work or assessment evidence."}
                  </p>
                )}
                <div className="space-y-3">
                  {today.map((task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      busy={busy}
                      onCheck={() => setCheck(task)}
                      onAction={(action) =>
                        void run(() => plannerAPI.action(task.id, action))
                      }
                    />
                  ))}
                </div>
                {upcoming.length > 0 && (
                  <details>
                    <summary className="cursor-pointer font-medium">
                      Upcoming · {upcoming.length} tasks · estimated finish{" "}
                      {dayLabel(goal.estimated_finish)}
                    </summary>
                    <ol className="mt-3 space-y-2">
                      {upcoming.map((task) => (
                        <li
                          key={task.id}
                          className="flex justify-between gap-3 rounded-lg border border-slate-200 p-3 text-sm"
                        >
                          <span>
                            {task.title}
                            <span className="block text-xs text-slate-500">
                              {task.reason}
                            </span>
                          </span>
                          <span className="shrink-0 text-slate-600">
                            {dayLabel(task.due_date)} · {task.minutes} min
                          </span>
                        </li>
                      ))}
                    </ol>
                  </details>
                )}
              </>
            )}
            {goal.interventions.length > 0 && (
              <details>
                <summary className="cursor-pointer font-medium">
                  Understanding and follow-up · {goal.interventions.length}
                </summary>
                <ul className="mt-3 space-y-3">
                  {goal.interventions.map((i) => (
                    <li
                      key={i.id}
                      className="border border-slate-200 rounded-xl p-4 text-sm"
                    >
                      <strong className="capitalize">{i.concept}</strong>
                      <span className="ml-3 text-orange-700">
                        {interventionLabels[i.status]}
                      </span>
                      <p className="mt-2 text-slate-600">{i.reason}</p>
                      <p className="mt-2">
                        Baseline {i.baseline_score ?? "Unknown"}
                        {i.baseline_score !== null ? "%" : ""} · Practice{" "}
                        {i.latest_score === null
                          ? "Not checked"
                          : `${i.latest_score}%`}{" "}
                        · Delayed check{" "}
                        {i.followup_score === null
                          ? "Not checked"
                          : `${i.followup_score}%`}
                      </p>
                      {i.instructor_note && (
                        <p className="mt-2 rounded-lg bg-orange-50 p-3">
                          Instructor: {i.instructor_note}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </details>
            )}
            {done.length > 0 && (
              <details>
                <summary className="cursor-pointer text-sm font-medium">
                  Completed tasks ({done.length})
                </summary>
                <ul className="mt-3 space-y-2">
                  {done.map((t) => (
                    <li key={t.id} className="text-sm">
                      <CheckCircle2 className="inline w-4 h-4 text-emerald-600 mr-2" />
                      {t.title}
                      <p className="ml-6 text-slate-500">{t.outcome?.note}</p>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </section>
        );
      })}
      <GlassDialog
        open={!!editing}
        onOpenChange={(open) => {
          if (!open && !busy) setEditing(null);
        }}
        title="Your learning goal"
        description="The daily time budget applies to this course. Goals guide your schedule; they do not guarantee mastery."
      >
        {editing && (
          <form className="p-5 space-y-4" onSubmit={save}>
            <label className="block text-sm font-medium">
              Course
              <select
                className={inputClass}
                value={editing.course_id}
                onChange={(e) =>
                  setEditing({ ...editing, course_id: Number(e.target.value) })
                }
              >
                {data?.courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium">
              What do you want to achieve?
              <input
                className={inputClass}
                required
                minLength={3}
                maxLength={200}
                value={editing.title}
                onChange={(e) =>
                  setEditing({ ...editing, title: e.target.value })
                }
                placeholder="Understand the core concepts and practise confidently"
              />
            </label>
            <div className="grid grid-cols-2 gap-4">
              <label className="block text-sm font-medium">
                Target date
                <input
                  type="date"
                  className={inputClass}
                  required
                  value={editing.target_date}
                  onChange={(e) =>
                    setEditing({ ...editing, target_date: e.target.value })
                  }
                />
              </label>
              <label className="block text-sm font-medium">
                Minutes per day
                <input
                  type="number"
                  className={inputClass}
                  required
                  min={5}
                  max={180}
                  value={editing.daily_minutes}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      daily_minutes: Number(e.target.value),
                    })
                  }
                />
              </label>
            </div>
            <label className="block text-sm font-medium">
              Time zone
              <input
                className={inputClass}
                required
                value={editing.timezone}
                onChange={(e) =>
                  setEditing({ ...editing, timezone: e.target.value })
                }
              />
            </label>
            <label className="block text-sm font-medium">
              Plan status
              <select
                className={inputClass}
                value={editing.status}
                onChange={(e) =>
                  setEditing({
                    ...editing,
                    status: e.target.value as "active" | "paused",
                  })
                }
              >
                <option value="active">Active</option>
                <option value="paused">Paused</option>
              </select>
            </label>
            {error && (
              <p role="alert" className="text-sm text-red-700">
                {error}
              </p>
            )}
            <button className="si-btn-primary" type="submit" disabled={busy}>
              {busy ? "Building your plan…" : "Save learning goal"}
            </button>
          </form>
        )}
      </GlassDialog>
      <GlassDialog
        open={!!check}
        onOpenChange={(open) => {
          if (!open) {
            setCheck(null);
            void load();
          }
        }}
        title={check?.title}
        description="These checks support your learning. They do not change your graded quiz results."
        size="lg"
      >
        {check && <PlanCheck key={check.id} task={check} onUpdate={replace} />}
      </GlassDialog>
    </PageLayout>
  );
}

function TaskCard({
  task,
  busy,
  onCheck,
  onAction,
}: {
  task: PlanTask;
  busy: boolean;
  onCheck: () => void;
  onAction: (action: "done" | "snooze") => void;
}) {
  return (
    <article
      className="rounded-xl border border-slate-200 bg-white/60 p-4"
      data-glass="content"
    >
      <div className="flex justify-between gap-3">
        <h4 className="font-semibold">{task.title}</h4>
        <span className="text-sm text-slate-500 shrink-0">
          {task.minutes} min
        </span>
      </div>
      <p className="text-sm text-slate-600 mt-1">{task.reason}</p>
      {task.outcome?.note && (
        <p className="text-sm text-amber-800 mt-2">{task.outcome.note}</p>
      )}
      <div className="flex flex-wrap gap-2 mt-3">
        {task.lesson_url ? (
          <>
            <Link className="si-btn-primary" to={task.lesson_url}>
              Open lesson
            </Link>
            <button
              className="si-btn-ghost"
              disabled={busy}
              onClick={() => onAction("done")}
            >
              Mark studied
            </button>
          </>
        ) : task.kind === "review" ? (
          <button
            className="si-btn-primary"
            disabled={busy}
            onClick={() => onAction("done")}
          >
            Mark reviewed
          </button>
        ) : (
          <button className="si-btn-primary" disabled={busy} onClick={onCheck}>
            {task.session_id ? "Resume check" : "Start check"}
          </button>
        )}
        <button
          className="si-btn-ghost"
          disabled={busy}
          onClick={() => onAction("snooze")}
        >
          Move to tomorrow
        </button>
      </div>
    </article>
  );
}

function PlanCheck({
  task,
  onUpdate,
}: {
  task: PlanTask;
  onUpdate: (g: PlanGoal) => void;
}) {
  const [build, setBuild] = useState<AdaptiveBuild | null>(null);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [outcome, setOutcome] = useState<PlanOutcome | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setError("");
    plannerAPI
      .start(task.id)
      .then((b) => {
        if (active) setBuild(b);
      })
      .catch((e) => {
        if (active) setError(plannerError(e));
      });
    return () => {
      active = false;
    };
  }, [task.id, retry]);
  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      const r = await plannerAPI.submit(task.id, answers);
      setOutcome(r.outcome);
      onUpdate(r.goal);
    } catch (e) {
      setError(plannerError(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="p-5 space-y-4">
      {error && (
        <p role="alert" className="text-red-700">
          {error}{" "}
          {!build && (
            <button
              className="underline ml-2"
              onClick={() => setRetry((n) => n + 1)}
            >
              Retry
            </button>
          )}
        </p>
      )}
      {!build && !error && <p role="status">Preparing your concept check…</p>}
      {outcome ? (
        <div role="status">
          <h3 className="text-xl font-semibold">
            {outcome.score}% on this check
          </h3>
          <p className="mt-2">{outcome.note}</p>
          {outcome.freshness_note && (
            <p className="mt-2 text-sm text-slate-600">
              {outcome.freshness_note}
            </p>
          )}
          <ul className="mt-4 space-y-2">
            {outcome.results?.map((r) => (
              <li key={r.question_id} className="text-sm">
                {
                  build?.questions.find((q) => q.question_id === r.question_id)
                    ?.title
                }
                : {r.correct ? "Correct" : `Review: ${r.expected.join(", ")}`}
                {r.explanation && (
                  <p className="mt-1 text-slate-600">{r.explanation}</p>
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        build && (
          <>
            {build.questions.map((q, index) => (
              <fieldset
                className="border border-slate-200 rounded-xl p-4"
                key={q.question_id}
              >
                <legend className="font-medium px-1">
                  {index + 1}. {q.title}
                </legend>
                {q.options.length ? (
                  q.options.map((option, oi) => {
                    const selected = answers[String(q.question_id)];
                    const multi = q.type === "multiple_select";
                    return (
                      <label
                        className="flex gap-3 items-start py-2 text-sm"
                        key={`${oi}-${option}`}
                      >
                        <input
                          className="mt-1"
                          type={multi ? "checkbox" : "radio"}
                          name={`question-${q.question_id}`}
                          checked={
                            multi
                              ? Array.isArray(selected) &&
                                selected.includes(option)
                              : selected === option
                          }
                          onChange={() =>
                            setAnswers((a) => {
                              const before = a[String(q.question_id)];
                              const list = Array.isArray(before) ? before : [];
                              return {
                                ...a,
                                [String(q.question_id)]: multi
                                  ? list.includes(option)
                                    ? list.filter((v) => v !== option)
                                    : [...list, option]
                                  : option,
                              };
                            })
                          }
                        />
                        {option}
                      </label>
                    );
                  })
                ) : (
                  <input
                    aria-label={`Answer to question ${index + 1}`}
                    className={inputClass}
                    value={String(answers[String(q.question_id)] || "")}
                    onChange={(e) =>
                      setAnswers((a) => ({
                        ...a,
                        [String(q.question_id)]: e.target.value,
                      }))
                    }
                  />
                )}
              </fieldset>
            ))}
            <button
              className="si-btn-primary"
              disabled={
                busy ||
                !build.questions.every((q) => {
                  const a = answers[String(q.question_id)];
                  return Array.isArray(a) ? a.length > 0 : !!a?.trim();
                })
              }
              onClick={() => void submit()}
            >
              {busy ? "Checking…" : "Check my understanding"}
            </button>
          </>
        )
      )}
    </div>
  );
}
