import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { GlassDialog } from "@/components/ui/dialog";
import { plannerError } from "@/api/planner";
import {
  studioAPI,
  type StudioData,
  type StudioQuestion,
  type DraftContent,
  type BankItem,
} from "@/api/assessment-studio";

const input = "si-input w-full mt-1";
const blank = (concept: string): DraftContent => ({
  concept,
  title: "",
  type: "multiple_choice",
  options: ["", ""],
  answer: 0,
  explanation: "",
  difficulty: "medium",
  purpose: "practice",
});
const readiness = (ready: boolean, count: number) =>
  `${count} · ${ready ? "Ready" : "Needs questions"}`;

export default function AssessmentStudio() {
  const [params, setParams] = useSearchParams();
  const courseId = Number(params.get("course_id") || 0);
  const concept = params.get("concept") || "";
  const [courses, setCourses] = useState<{ id: number; title: string }[]>([]);
  const [data, setData] = useState<StudioData | null>(null);
  const [banks, setBanks] = useState<BankItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState("coverage");
  const [draft, setDraft] = useState<DraftContent | null>(null);
  const [editId, setEditId] = useState<number | undefined>();
  const [decision, setDecision] = useState<{
    question: StudioQuestion;
    action: "review" | "publish" | "retire";
  } | null>(null);
  const [note, setNote] = useState("");
  const [linkKind, setLinkKind] = useState<"lesson" | "question">("lesson");
  const [linkId, setLinkId] = useState("");
  const [bankId, setBankId] = useState("");
  const [importPurpose, setImportPurpose] = useState("practice");
  const [message, setMessage] = useState("");
  useEffect(() => {
    let active = true;
    Promise.all([studioAPI.courses(), studioAPI.banks()])
      .then(([cs, bs]) => {
        if (active) {
          setCourses(cs);
          setBanks(bs);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (active) {
          setError(plannerError(e));
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (!courseId && courses.length)
      setParams({ course_id: String(courses[0].id) }, { replace: true });
  }, [courseId, courses, setParams]);
  useEffect(() => {
    let active = true;
    setData(null);
    setError("");
    setLinkId("");
    if (!courseId) return;
    setLoading(true);
    studioAPI
      .detail(courseId)
      .then((d) => {
        if (active) setData(d);
      })
      .catch((e) => {
        if (active) setError(plannerError(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [courseId]);
  const reload = useCallback(async () => {
    if (courseId) setData(await studioAPI.detail(courseId));
  }, [courseId]);
  const run = async (fn: () => Promise<unknown>, success: string) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await fn();
      await reload();
      setMessage(success);
      return true;
    } catch (e) {
      setError(plannerError(e));
      return false;
    } finally {
      setBusy(false);
    }
  };
  const choose = (c: string) =>
    setParams({ course_id: String(courseId), ...(c ? { concept: c } : {}) });
  const newQuestion = () => {
    setEditId(undefined);
    setDraft(blank(concept));
    setError("");
  };
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      draft &&
      (await run(
        () => studioAPI.save(courseId, draft, editId),
        "Draft saved. Review its answer and explanation before publishing.",
      ))
    )
      setDraft(null);
  };
  const act = async () => {
    if (
      decision &&
      (await run(
        () =>
          studioAPI.action(
            decision.question.id,
            decision.question.version,
            decision.action,
            note,
          ),
        decision.action === "publish"
          ? "Published. Eligible learner checks can use this question immediately."
          : "Decision saved.",
      ))
    )
      setDecision(null);
  };
  const questions =
    data?.questions.filter((q) => !concept || q.concept === concept) || [];
  const links = linkKind === "lesson" ? data?.lessons : data?.live_questions;
  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <p className="text-xs uppercase font-semibold tracking-widest text-orange-600">
              From learning gaps to useful practice
            </p>
            <h1 className="dash-h1 mt-1">Concept & Assessment Studio</h1>
            <p className="text-slate-600 mt-2 max-w-3xl">
              Connect lessons and questions to concepts. Review practice before
              publishing, and reserve fresh questions for delayed checks.
            </p>
          </div>
          <Link className="si-btn-ghost" to="/instructor/interventions">
            Interventions
          </Link>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-assessment-studio"
    >
      <div className="glass-panel rounded-xl p-4 grid sm:grid-cols-2 gap-4">
        <label className="text-sm font-medium">
          Course
          <select
            className={input}
            value={courseId || ""}
            disabled={busy}
            onChange={(e) => {
              setParams({ course_id: e.target.value });
              setMessage("");
            }}
          >
            <option value="" disabled>
              Choose a course
            </option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium">
          Focus concept
          <input
            className={input}
            maxLength={80}
            value={concept}
            onChange={(e) => choose(e.target.value.toLowerCase())}
            list="studio-concepts"
            placeholder="All concepts, or type a new concept"
          />
          <datalist id="studio-concepts">
            {data?.concepts.map((c) => (
              <option key={c.concept} value={c.concept} />
            ))}
          </datalist>
        </label>
      </div>
      {error && (
        <p
          role="alert"
          className="rounded-xl bg-red-50 border border-red-200 p-4 text-red-800"
        >
          {error}{" "}
          {!draft && !decision && (
            <button
              className="underline ml-3"
              onClick={() => void run(reload, "Coverage refreshed.")}
            >
              Retry
            </button>
          )}
        </p>
      )}
      {message && (
        <p
          role="status"
          className="rounded-xl bg-emerald-50 p-4 text-emerald-800"
        >
          {message}
        </p>
      )}
      {loading ? (
        <p role="status">Loading course coverage…</p>
      ) : !courses.length ? (
        <p>Create a course to start mapping its assessment coverage.</p>
      ) : (
        data && (
          <>
            <div className="grid sm:grid-cols-3 gap-3">
              {[
                ["Concepts mapped", data.concepts.length],
                [
                  "Practice gaps",
                  data.concepts.filter((c) => !c.practice_ready).length,
                ],
                [
                  "Follow-up reserve gaps",
                  data.concepts.filter((c) => !c.followup_ready).length,
                ],
              ].map(([label, count]) => (
                <div className="glass-panel p-5 rounded-xl" key={label}>
                  <p className="text-3xl font-bold">{count}</p>
                  <p className="text-sm text-slate-600 mt-1">{label}</p>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-2" aria-label="Studio views">
              {["coverage", "questions", "outcomes"].map((v) => (
                <button
                  key={v}
                  className={
                    view === v
                      ? "si-btn-primary capitalize"
                      : "si-btn-ghost capitalize"
                  }
                  aria-pressed={view === v}
                  onClick={() => setView(v)}
                >
                  {v}
                </button>
              ))}
              <button
                className="si-btn-primary ml-auto"
                disabled={busy}
                onClick={newQuestion}
              >
                Create question
              </button>
            </div>
            {view === "coverage" && (
              <div className="glass-panel rounded-xl p-5 space-y-4">
                <p className="text-sm text-slate-600">
                  Ready means at least two distinct usable questions. Aim for
                  three practice and three reserved follow-up questions. Only
                  published, available, auto-gradable content counts; exact
                  duplicate prompts count once.
                </p>
                {!data.concepts.length ? (
                  <p>
                    No concepts mapped yet. Type a concept above, then link a
                    lesson or create a question.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead>
                        <tr>
                          {[
                            "Concept",
                            "Lessons",
                            "Practice",
                            "Reserved follow-up",
                            "Needs support",
                            "Action",
                          ].map((h) => (
                            <th className="p-3" scope="col" key={h}>
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {data.concepts
                          .filter(
                            (c) =>
                              !concept ||
                              c.concept.includes(concept.trim().toLowerCase()),
                          )
                          .map((c) => (
                            <tr
                              key={c.concept}
                              className="border-t border-slate-200"
                            >
                              <th scope="row" className="p-3 font-medium">
                                {c.concept}
                              </th>
                              <td className="p-3">
                                {c.lessons || "Not linked"}
                              </td>
                              <td
                                className={`p-3 ${c.practice_ready ? "text-emerald-700" : "text-amber-800"}`}
                              >
                                {readiness(
                                  c.practice_ready,
                                  c.practice_questions,
                                )}
                              </td>
                              <td
                                className={`p-3 ${c.followup_ready ? "text-emerald-700" : "text-amber-800"}`}
                              >
                                {readiness(
                                  c.followup_ready,
                                  c.reserved_followups,
                                )}
                              </td>
                              <td className="p-3">{c.needs_support}</td>
                              <td className="p-3">
                                <button
                                  className="underline text-orange-700"
                                  onClick={() => {
                                    choose(c.concept);
                                    setView("questions");
                                  }}
                                >
                                  Fix this gap
                                </button>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
            {view === "questions" && (
              <div className="space-y-4">
                {!questions.length && (
                  <p className="glass-panel rounded-xl p-6">
                    No studio drafts for this selection. Create a question or
                    reuse one from your bank below.
                  </p>
                )}
                {questions.map((q) => (
                  <article className="glass-panel rounded-xl p-5" key={q.id}>
                    <div className="flex flex-wrap justify-between gap-2">
                      <h2 className="font-semibold text-lg">{q.title}</h2>
                      <span className="text-sm capitalize text-orange-700">
                        {q.status}
                      </span>
                    </div>
                    <p className="text-sm text-slate-500 mt-2">
                      {q.concept} ·{" "}
                      {q.purpose === "followup"
                        ? "Reserved delayed check"
                        : "Practice"}{" "}
                      · {q.difficulty}
                    </p>
                    <p className="text-sm mt-3">{q.explanation}</p>
                    <div className="flex gap-2 mt-4">
                      {["draft", "reviewed"].includes(q.status) && (
                        <button
                          className="si-btn-ghost"
                          disabled={busy}
                          onClick={() => {
                            setEditId(q.id);
                            setDraft(q);
                            setError("");
                          }}
                        >
                          Edit draft
                        </button>
                      )}
                      {q.status !== "retired" && (
                        <button
                          className="si-btn-primary"
                          disabled={busy}
                          onClick={() => {
                            setDecision({
                              question: q,
                              action:
                                q.status === "draft"
                                  ? "review"
                                  : q.status === "reviewed"
                                    ? "publish"
                                    : "retire",
                            });
                            setNote("");
                            setError("");
                          }}
                        >
                          {q.status === "draft"
                            ? "Review question"
                            : q.status === "reviewed"
                              ? "Publish practice"
                              : "Retire question"}
                        </button>
                      )}
                    </div>
                    <details className="mt-3 text-sm">
                      <summary className="cursor-pointer">
                        Decision history
                      </summary>
                      <ul className="mt-2 space-y-1">
                        {q.history.map((h, i) => (
                          <li key={i}>
                            {new Date(h.at).toLocaleString()} ·{" "}
                            {h.action.replace(/_/g, " ")}
                            {h.note ? ` · ${h.note}` : ""}
                          </li>
                        ))}
                      </ul>
                    </details>
                  </article>
                ))}
              </div>
            )}
            {view === "outcomes" && (
              <div className="glass-panel rounded-xl p-5 space-y-4">
                <p className="text-sm text-slate-600">
                  Observed results for currently enrolled learners with plans.
                  These are not proof that an intervention caused improvement.
                  Counts include repeated checks; paired scores use each
                  intervention's current practice and delayed result. Unknown is
                  not zero.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead>
                      <tr>
                        {[
                          "Concept",
                          "Interventions",
                          "Checks / questions",
                          "Delayed checks passed",
                          "Paired results",
                          "Practice → delayed change",
                        ].map((h) => (
                          <th key={h} scope="col" className="p-3">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {data.concepts
                        .filter((c) => !concept || c.concept === concept)
                        .map((c) => (
                          <tr key={c.concept} className="border-t">
                            <th scope="row" className="p-3">
                              {c.concept}
                            </th>
                            <td className="p-3">{c.outcomes.interventions}</td>
                            <td className="p-3">
                              {c.outcomes.completed_checks} /{" "}
                              {c.outcomes.graded_questions}
                            </td>
                            <td className="p-3">
                              {c.outcomes.followups_passed} /{" "}
                              {c.outcomes.valid_followups}
                            </td>
                            <td className="p-3">
                              {c.outcomes.paired_learners}
                            </td>
                            <td className="p-3">
                              {c.outcomes.mean_practice_to_followup_change ===
                              null
                                ? "Not enough evidence"
                                : `${c.outcomes.mean_practice_to_followup_change > 0 ? "+" : ""}${c.outcomes.mean_practice_to_followup_change} percentage points`}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            <div className="grid lg:grid-cols-2 gap-4">
              <section className="glass-panel rounded-xl p-5 space-y-3">
                <h2 className="font-semibold">Link existing course content</h2>
                <p className="text-sm text-slate-600">
                  Adds the focus concept without removing existing mappings.
                </p>
                <label className="block text-sm">
                  Content type
                  <select
                    className={input}
                    value={linkKind}
                    onChange={(e) => {
                      setLinkKind(e.target.value as "lesson" | "question");
                      setLinkId("");
                    }}
                  >
                    <option value="lesson">Lesson</option>
                    <option value="question">Quiz question</option>
                  </select>
                </label>
                <label className="block text-sm">
                  Course content
                  <select
                    className={input}
                    value={linkId}
                    onChange={(e) => setLinkId(e.target.value)}
                  >
                    <option value="">Choose content</option>
                    {links?.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.title}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="si-btn-primary"
                  disabled={busy || !concept.trim() || !linkId}
                  onClick={() =>
                    void run(
                      () =>
                        studioAPI.link(
                          courseId,
                          linkKind,
                          Number(linkId),
                          concept.trim(),
                        ),
                      "Concept linked. Coverage updated.",
                    )
                  }
                >
                  Link to {concept.trim() || "a concept"}
                </button>
              </section>
              <section className="glass-panel rounded-xl p-5 space-y-3">
                <h2 className="font-semibold">Reuse a bank question</h2>
                <p className="text-sm text-slate-600">
                  Copy one of your latest 500 bank questions into a course
                  draft. Review is required even for previously approved
                  content.
                </p>
                <label className="block text-sm">
                  Bank question
                  <select
                    className={input}
                    value={bankId}
                    onChange={(e) => setBankId(e.target.value)}
                  >
                    <option value="">Choose a question</option>
                    {banks.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.bank_title} · {b.title}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm">
                  Use for
                  <select
                    className={input}
                    value={importPurpose}
                    onChange={(e) => setImportPurpose(e.target.value)}
                  >
                    <option value="practice">Practice</option>
                    <option value="followup">Delayed check reserve</option>
                  </select>
                </label>
                <button
                  className="si-btn-primary"
                  disabled={busy || !concept.trim() || !bankId}
                  onClick={() =>
                    void run(
                      () =>
                        studioAPI.import(
                          courseId,
                          Number(bankId),
                          concept.trim(),
                          importPurpose,
                        ),
                      "Copied as a new draft. Review it before publishing.",
                    )
                  }
                >
                  Copy to {concept.trim() || "a concept"}
                </button>
              </section>
            </div>
          </>
        )
      )}
      <GlassDialog
        open={!!draft}
        onOpenChange={(open) => {
          if (!open && !busy) setDraft(null);
        }}
        title={editId ? "Edit question draft" : "Create question draft"}
        description="Review and publication are separate steps. Editing resets prior review."
        size="lg"
      >
        {draft && (
          <form className="p-5 space-y-4" onSubmit={save}>
            <div className="grid sm:grid-cols-2 gap-3">
              <label className="text-sm">
                Concept
                <input
                  className={input}
                  required
                  maxLength={80}
                  value={draft.concept}
                  onChange={(e) =>
                    setDraft({ ...draft, concept: e.target.value })
                  }
                />
              </label>
              <label className="text-sm">
                Use for
                <select
                  className={input}
                  value={draft.purpose}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      purpose: e.target.value as DraftContent["purpose"],
                    })
                  }
                >
                  <option value="practice">Practice</option>
                  <option value="followup">Delayed check reserve</option>
                </select>
              </label>
            </div>
            <label className="block text-sm">
              Question
              <textarea
                className={input}
                required
                minLength={3}
                maxLength={3000}
                value={draft.title}
                onChange={(e) => setDraft({ ...draft, title: e.target.value })}
              />
            </label>
            <div className="grid sm:grid-cols-2 gap-3">
              <label className="text-sm">
                Question type
                <select
                  className={input}
                  value={draft.type}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      type: e.target.value as DraftContent["type"],
                      answer:
                        e.target.value === "multiple_choice"
                          ? 0
                          : e.target.value === "multiple_select"
                            ? [0]
                            : e.target.value === "true_false"
                              ? "true"
                              : "",
                    })
                  }
                >
                  {[
                    ["multiple_choice", "Single choice"],
                    ["multiple_select", "Multiple correct options"],
                    ["true_false", "True / false"],
                    ["fill_in_blanks", "Fill in the blank"],
                    ["short_answer", "Short answer (exact match)"],
                  ].map(([v, label]) => (
                    <option key={v} value={v}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                Difficulty
                <select
                  className={input}
                  value={draft.difficulty}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      difficulty: e.target.value as DraftContent["difficulty"],
                    })
                  }
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </label>
            </div>
            {["multiple_choice", "multiple_select"].includes(draft.type) ? (
              <>
                <label className="block text-sm">
                  Options (one per line)
                  <textarea
                    className={input}
                    rows={4}
                    required
                    value={draft.options.join("\n")}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        options: e.target.value.split("\n"),
                      })
                    }
                  />
                </label>
                <fieldset>
                  <legend className="text-sm font-medium">
                    Correct answer{draft.type === "multiple_select" ? "s" : ""}
                  </legend>
                  {draft.options.map((o, i) => (
                    <label
                      key={i}
                      className="flex gap-2 items-center py-1 text-sm"
                    >
                      <input
                        type={
                          draft.type === "multiple_select"
                            ? "checkbox"
                            : "radio"
                        }
                        name="correct-option"
                        checked={
                          Array.isArray(draft.answer)
                            ? draft.answer.includes(i)
                            : draft.answer === i
                        }
                        onChange={() => {
                          const before = Array.isArray(draft.answer)
                            ? draft.answer
                            : [];
                          setDraft({
                            ...draft,
                            answer:
                              draft.type === "multiple_select"
                                ? before.includes(i)
                                  ? before.filter((n) => n !== i)
                                  : [...before, i]
                                : i,
                          });
                        }}
                      />
                      {i + 1}. {o || "Empty option"}
                    </label>
                  ))}
                </fieldset>
              </>
            ) : draft.type === "true_false" ? (
              <label className="block text-sm">
                Correct answer
                <select
                  className={input}
                  value={String(draft.answer)}
                  onChange={(e) =>
                    setDraft({ ...draft, answer: e.target.value })
                  }
                >
                  <option value="true">True</option>
                  <option value="false">False</option>
                </select>
              </label>
            ) : (
              <label className="block text-sm">
                Accepted answer
                <input
                  className={input}
                  required
                  maxLength={1000}
                  value={String(draft.answer)}
                  onChange={(e) =>
                    setDraft({ ...draft, answer: e.target.value })
                  }
                />
                <span className="text-xs text-slate-500">
                  Case-insensitive exact match; use a short unambiguous answer.
                </span>
              </label>
            )}
            <label className="block text-sm">
              Answer explanation
              <textarea
                className={input}
                required
                minLength={3}
                maxLength={5000}
                value={draft.explanation}
                onChange={(e) =>
                  setDraft({ ...draft, explanation: e.target.value })
                }
              />
            </label>
            {error && (
              <p role="alert" className="text-red-700">
                {error}
              </p>
            )}
            <button className="si-btn-primary" disabled={busy} type="submit">
              {busy ? "Saving…" : "Save draft"}
            </button>
          </form>
        )}
      </GlassDialog>
      <GlassDialog
        open={!!decision}
        onOpenChange={(open) => {
          if (!open && !busy) setDecision(null);
        }}
        title={
          decision?.action === "review"
            ? "Review question"
            : decision?.action === "publish"
              ? "Publish reviewed practice"
              : "Retire question"
        }
        description="Check the answer, explanation, concept and intended use before recording your decision."
        size="lg"
      >
        {decision && (
          <div className="p-5 space-y-4">
            <h2 className="font-semibold">{decision.question.title}</h2>
            <p className="text-sm">
              {decision.question.concept} · {decision.question.purpose}
            </p>
            <ul className="text-sm space-y-1">
              {decision.question.options.map((o, i) => (
                <li key={i}>
                  {i + 1}. {o}
                  {(
                    Array.isArray(decision.question.answer)
                      ? decision.question.answer.includes(i)
                      : decision.question.answer === i
                  )
                    ? " — Correct"
                    : ""}
                </li>
              ))}
            </ul>
            {!decision.question.options.length && (
              <p>Accepted answer: {String(decision.question.answer)}</p>
            )}
            <p className="text-sm bg-orange-50 rounded-lg p-3">
              {decision.question.explanation}
            </p>
            {decision.action === "retire" && (
              <p className="text-sm">
                Retired questions leave new practice sets. Existing sessions
                keep their original question and grading.
              </p>
            )}
            <label className="block text-sm">
              Decision note
              <textarea
                className={input}
                required
                minLength={3}
                maxLength={2000}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Explain what you checked or why this question should be retired."
              />
            </label>
            {error && (
              <p role="alert" className="text-red-700">
                {error}
              </p>
            )}
            <button
              className="si-btn-primary"
              disabled={busy || note.trim().length < 3}
              onClick={() => void act()}
            >
              {busy
                ? "Saving…"
                : decision.action === "review"
                  ? "Approve review"
                  : decision.action === "publish"
                    ? "Publish question"
                    : "Confirm retirement"}
            </button>
          </div>
        )}
      </GlassDialog>
    </PageLayout>
  );
}
