import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Review Queue (v2.0 §9.4 — WP7): the instructor's single inbox for the AI
 * layer's safeguards. Four lanes, all derived server-side:
 *   1. AI-drafted questions (tagged ai-draft) → approve (becomes "reviewed") / reject (deleted)
 *   2. Auto-flagged items by item statistics (facility / discrimination) — explainable reasons
 *   3. Learner-reported content errors → resolve / dismiss with a note
 *   4. Tutor escalations (Engine C hand-offs) → reply in-app, learner is notified
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { aiLayerAPI, errDetail, type ReviewQueue } from "@/api/aiLayer";
import { api } from "@/api/axios";

type Lane = "drafts" | "flags" | "errors" | "escalations" | "integrity";

export default function ReviewQueuePage() {
  const [data, setData] = useState<ReviewQueue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lane, setLane] = useState<Lane>("escalations");
  const [busy, setBusy] = useState<number | null>(null);
  const [replyText, setReplyText] = useState<Record<number, string>>({});
  const [resolution, setResolution] = useState<Record<number, string>>({});
  const [integrity, setIntegrity] = useState<any[] | null>(null);
  useEffect(() => {
    if (lane === "integrity" && integrity === null)
      api
        .get("/ai/review-queue/integrity")
        .then((r) => setIntegrity(r.data.attempts))
        .catch(() => setIntegrity([]));
  }, [lane, integrity]);

  const load = useCallback(() => {
    aiLayerAPI
      .reviewQueue()
      .then(setData)
      .catch((e) =>
        setError(errDetail(e, "Could not load the review queue").detail),
      );
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  const act = async (id: number, fn: () => Promise<unknown>, ok: string) => {
    setBusy(id);
    try {
      await fn();
      toast.success(ok);
      load();
    } catch (e) {
      toast.error(errDetail(e, "Action failed").detail);
    } finally {
      setBusy(null);
    }
  };

  if (error)
    return (
      <div className="p-6 astra-work" role="alert">
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      </div>
    );
  if (!data)
    return (
      <div className="p-6 text-sm text-gray-500 astra-work" role="status">
        Loading review queue…
      </div>
    );

  const lanes: { id: Lane; label: string; count: number | string }[] = [
    {
      id: "escalations",
      label: "Learner questions",
      count: data.counts.escalations,
    },
    { id: "errors", label: "Error reports", count: data.counts.error_reports },
    { id: "drafts", label: "AI drafts", count: data.counts.ai_drafts },
    { id: "flags", label: "Flagged items", count: data.counts.flagged_items },
    {
      id: "integrity",
      label: "Quiz integrity",
      count: integrity ? integrity.length : "…",
    },
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-4" data-testid="review-queue">
      <PageLayout
        header={
          <PageHeader>
            <h1 className="text-2xl font-bold text-gray-900">Review queue</h1>
            <p className="text-sm text-gray-500">
              Nothing the AI produces reaches learners as truth until you
              approve it here. Flags are computed from live answer statistics.
            </p>
          </PageHeader>
        }
        className="rd-screen rd-screen-instructor-review-queue"
      >
        {!data.llm_configured && (
          <span className="text-xs px-2 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
            AI drafting is unavailable. Learner questions, reports and flags
            still work.
          </span>
        )}
      </PageLayout>

      <div className="astra-review-body" data-glass="work">
        <div className="astra-lanes" aria-label="Review categories">
          {lanes.map((l) => (
            <button
              key={l.id}
              type="button"
              aria-pressed={lane === l.id}
              onClick={() => setLane(l.id)}
              className="astra-lane text-sm"
            >
              {l.label} <span className="text-xs">{l.count}</span>
            </button>
          ))}
        </div>

        {lane === "escalations" && (
          <div className="space-y-3">
            {data.escalations.length === 0 && (
              <p className="text-sm text-gray-500">
                No open learner questions.
              </p>
            )}
            {data.escalations.map((e) => (
              <div
                key={e.id}
                className="rounded-xl border border-gray-200 bg-white p-4"
                data-glass="work"
              >
                <p className="text-xs text-gray-500">
                  Course {e.course_id} · learner #{e.student_id} ·{" "}
                  {e.created_at ? new Date(e.created_at).toLocaleString() : ""}
                </p>
                <p className="text-sm text-gray-900 font-medium mt-1">
                  {e.question}
                </p>
                {e.context.weak_concepts &&
                  e.context.weak_concepts.length > 0 && (
                    <p className="text-xs text-amber-700 mt-1">
                      Weak concepts: {e.context.weak_concepts.join(", ")}
                    </p>
                  )}
                {e.context.history && e.context.history.length > 0 && (
                  <details className="mt-1 text-xs text-gray-600">
                    <summary className="cursor-pointer">
                      Tutor conversation ({e.context.history.length} turns)
                    </summary>
                    <ul className="mt-1 space-y-0.5">
                      {e.context.history.map((h, i) => (
                        <li key={i}>
                          <span className="font-medium">
                            {h.role === "user" ? "Learner" : "Tutor"}:
                          </span>{" "}
                          {h.content}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
                <div className="mt-2 flex gap-2">
                  <input
                    value={replyText[e.id] || ""}
                    onChange={(ev) =>
                      setReplyText((t) => ({ ...t, [e.id]: ev.target.value }))
                    }
                    placeholder="Reply to the learner…"
                    className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                    aria-label="Reply"
                  />
                  <button
                    type="button"
                    disabled={busy === e.id || !(replyText[e.id] || "").trim()}
                    onClick={() =>
                      act(
                        e.id,
                        () => aiLayerAPI.reply(e.id, replyText[e.id].trim()),
                        "Reply sent",
                      )
                    }
                    className="px-3 py-1.5 text-sm rounded-lg bg-gray-900 text-white disabled:opacity-40"
                  >
                    Send
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {lane === "errors" && (
          <div className="space-y-3">
            {data.error_reports.length === 0 && (
              <p className="text-sm text-gray-500">No open error reports.</p>
            )}
            {data.error_reports.map((r) => (
              <div
                key={r.id}
                className="rounded-xl border border-gray-200 bg-white p-4"
                data-glass="work"
              >
                <p className="text-xs text-gray-500">
                  {r.kind.replace("_", " ")}
                  {r.ref_id ? ` #${r.ref_id}` : ""} · course {r.course_id} ·
                  learner #{r.reporter_id}
                </p>
                <p className="text-sm text-gray-900 mt-1">{r.message}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <input
                    value={resolution[r.id] || ""}
                    onChange={(ev) =>
                      setResolution((t) => ({ ...t, [r.id]: ev.target.value }))
                    }
                    placeholder="What you changed (optional)"
                    className="flex-1 min-w-[12rem] px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                    aria-label="Resolution"
                  />
                  <button
                    type="button"
                    disabled={busy === r.id}
                    onClick={() =>
                      act(
                        r.id,
                        () =>
                          aiLayerAPI.resolveReport(
                            r.id,
                            "resolved",
                            resolution[r.id],
                          ),
                        "Marked resolved",
                      )
                    }
                    className="px-3 py-1.5 text-sm rounded-lg bg-emerald-600 text-white disabled:opacity-40"
                  >
                    Resolved
                  </button>
                  <button
                    type="button"
                    disabled={busy === r.id}
                    onClick={() =>
                      act(
                        r.id,
                        () =>
                          aiLayerAPI.resolveReport(
                            r.id,
                            "dismissed",
                            resolution[r.id],
                          ),
                        "Dismissed",
                      )
                    }
                    className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 disabled:opacity-40"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {lane === "drafts" && (
          <div className="space-y-3">
            {data.ai_drafts.length === 0 && (
              <p className="text-sm text-gray-500">
                No AI drafts waiting. Generate some from{" "}
                <Link
                  to="/instructor/insights"
                  className="text-blue-600 underline"
                >
                  Insights
                </Link>
                .
              </p>
            )}
            {data.ai_drafts.map((d) => (
              <div
                key={d.question_id}
                className="rounded-xl border border-gray-200 bg-white p-4"
                data-glass="content"
              >
                <p className="text-xs text-gray-500">
                  {d.bank_title} · {d.question_type} · {d.difficulty}
                </p>
                <p className="text-sm text-gray-900 font-medium mt-1">
                  {d.question_title}
                </p>
                {Array.isArray(d.options) && d.options.length > 0 && (
                  <ol className="text-xs text-gray-700 list-decimal pl-5 mt-1">
                    {d.options.map((o, i) => (
                      <li
                        key={i}
                        className={
                          i === d.correct_answer
                            ? "font-semibold text-emerald-700"
                            : ""
                        }
                      >
                        {o}
                      </li>
                    ))}
                  </ol>
                )}
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    disabled={busy === d.question_id}
                    onClick={() =>
                      act(
                        d.question_id,
                        () => aiLayerAPI.approveDraft(d.question_id),
                        "Approved — tagged reviewed",
                      )
                    }
                    className="px-3 py-1.5 text-sm rounded-lg bg-emerald-600 text-white disabled:opacity-40"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={busy === d.question_id}
                    onClick={() =>
                      act(
                        d.question_id,
                        () => aiLayerAPI.rejectDraft(d.question_id),
                        "Draft deleted",
                      )
                    }
                    className="px-3 py-1.5 text-sm rounded-lg border border-red-200 text-red-700 disabled:opacity-40"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {lane === "integrity" && (
          <div className="space-y-3" data-testid="integrity-lane">
            {integrity === null ? (
              <p className="text-sm text-gray-500">Loading…</p>
            ) : integrity.length === 0 ? (
              <p className="text-sm text-gray-500">
                No attempts with integrity flags in the last 30 days. Tab
                switches, pastes and full-screen exits during a quiz land here.
              </p>
            ) : (
              integrity.map((a) => (
                <div
                  key={a.attempt_id}
                  className="rounded-xl border border-gray-200 bg-white p-4 text-sm"
                  data-glass="content"
                >
                  <p className="font-medium text-gray-900">
                    {a.name} · {a.quiz_title}{" "}
                    <span className="text-xs text-gray-500">
                      · {a.course_title} · {a.earned}/{a.total}
                    </span>
                  </p>
                  <p className="text-xs text-amber-800 mt-1">
                    left the tab {a.tab_hidden}× · pasted {a.paste}× · exited
                    full screen {a.fullscreen_exit}×
                  </p>
                </div>
              ))
            )}
          </div>
        )}

        {lane === "flags" && (
          <div className="space-y-3">
            {data.flagged_items.length === 0 && (
              <p className="text-sm text-gray-500">
                No items flagged. Flags need at least 6–10 graded attempts per
                question.
              </p>
            )}
            {data.flagged_items.map((f) => (
              <div
                key={f.question_id}
                className="rounded-xl border border-gray-200 bg-white p-4"
                data-glass="content"
              >
                <p className="text-xs text-gray-500">
                  {f.quiz_title} · {f.attempts} attempts · facility{" "}
                  {f.facility ?? "—"} · discrimination {f.discrimination ?? "—"}
                </p>
                <p className="text-sm text-gray-900 font-medium mt-1">
                  {f.question_title}
                </p>
                <ul className="text-xs text-amber-800 list-disc pl-5 mt-1">
                  {f.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
                <div className="mt-2 flex items-center gap-3">
                  <Link
                    to={`/instructor/courses/${f.course_id}/edit?tab=curriculum`}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    Open the course →
                  </Link>
                  {(f as any).is_retired ? (
                    <button
                      type="button"
                      disabled={busy === f.question_id}
                      onClick={() =>
                        act(
                          f.question_id,
                          () =>
                            api.post(
                              `/ai/review-queue/items/${f.question_id}/unretire`,
                            ),
                          "Question back in play",
                        )
                      }
                      className="text-xs px-2 py-1 rounded border border-gray-300"
                    >
                      Retired — bring back
                    </button>
                  ) : (
                    <button
                      type="button"
                      disabled={busy === f.question_id}
                      onClick={() =>
                        act(
                          f.question_id,
                          () =>
                            api.post(
                              `/ai/review-queue/items/${f.question_id}/retire`,
                            ),
                          "Question retired from new attempts",
                        )
                      }
                      className="text-xs px-2 py-1 rounded bg-red-600 text-white"
                    >
                      Retire from new attempts
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
