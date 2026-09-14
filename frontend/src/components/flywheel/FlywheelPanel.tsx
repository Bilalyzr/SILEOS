/**
 * FlywheelPanel (v2.0 §10 — WP8): the instructor's "what next" view for one course.
 *   NextClassAgenda — derived proposal (recap → re-teach weak concepts →
 *     catch-up → open questions → fixes); optional LLM prose when configured.
 *   InsightCards — 3D path evidence (clean / mixed / trial-and-error) × quiz
 *     outcomes on the same concepts, with plain-English insights.
 */
import { useCallback, useEffect, useState } from 'react'
import { flywheelAPI, type InsightCard, type NextAgenda } from '@/api/flywheel'

const KIND_STYLE: Record<string, string> = {
  recap: 'bg-gray-100 text-gray-700', reteach: 'bg-amber-100 text-amber-800', catch_up: 'bg-sky-100 text-sky-800',
  questions: 'bg-violet-100 text-violet-800', fix: 'bg-red-100 text-red-800', advance: 'bg-emerald-100 text-emerald-800',
}

export function NextClassAgenda({ courseId }: { courseId: number }) {
  const [data, setData] = useState<NextAgenda | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [polishing, setPolishing] = useState(false)

  const load = useCallback((polish = false) => {
    if (polish) setPolishing(true)
    flywheelAPI.nextAgenda(courseId, polish ? { polish: true } : undefined).then(setData)
      .catch((e) => setError(e?.response?.data?.detail || 'Could not build the agenda'))
      .finally(() => setPolishing(false))
  }, [courseId])
  useEffect(() => { load() }, [load])

  if (error) return <p className="text-sm text-red-600" role="alert">{error}</p>
  if (!data) return <p className="text-sm text-gray-500">Building the agenda…</p>
  const total = data.agenda.reduce((s, i) => s + (i.minutes || 0), 0)
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4" data-testid="next-agenda">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <h3 className="font-semibold text-gray-900 flex-1">Next class agenda</h3>
        <span className="text-xs text-gray-500">{data.last_class_title ? `after "${data.last_class_title}"` : 'no ended class yet'} · ~{total} min</span>
        {data.llm_configured ? (
          <button type="button" disabled={polishing} onClick={() => load(true)} className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-40">{polishing ? 'Writing…' : 'Write it up (AI draft)'}</button>
        ) : <span className="text-[11px] text-gray-400">AI write-up off (no GLM_API_KEY) — the plan itself needs no AI</span>}
      </div>
      <ol className="space-y-1.5">
        {data.agenda.map((i, idx) => (
          <li key={idx} className="flex items-start gap-2 text-sm">
            <span className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded ${KIND_STYLE[i.kind] || 'bg-gray-100'}`}>{i.kind.replace('_', ' ')}</span>
            <span className="flex-1 text-gray-800">{i.text}</span>
            {i.minutes > 0 && <span className="text-xs text-gray-400">{i.minutes} min</span>}
          </li>
        ))}
      </ol>
      <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-gray-500">
        <span>absent last class: {data.absent_count}</span><span>open questions: {data.open_escalations}</span><span>open error reports: {data.open_error_reports}</span>
        {data.weak_concepts.length > 0 && <span>weakest: {data.weak_concepts.slice(0, 3).map((w) => `${w.concept} (${w.learners})`).join(', ')}</span>}
      </div>
      {data.prose && <pre className="mt-2 text-sm text-gray-800 whitespace-pre-wrap bg-violet-50 rounded-lg p-3">{data.prose}</pre>}
    </div>
  )
}

export function InsightCards({ courseId }: { courseId: number }) {
  const [cards, setCards] = useState<InsightCard[] | null>(null)
  useEffect(() => { flywheelAPI.insightCards(courseId).then(setCards).catch(() => setCards([])) }, [courseId])
  if (!cards) return <p className="text-sm text-gray-500">Reading 3D evidence…</p>
  if (cards.length === 0) return <p className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-xl p-4">No 3D task attempts in this course's quizzes yet — insight cards appear once learners work through a 3D match-and-verify task.</p>
  return (
    <div className="space-y-3" data-testid="insight-cards">
      {cards.map((c) => (
        <div key={c.task_id} className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="font-semibold text-gray-900">{c.task_title} <span className="text-xs font-normal text-gray-500">· {c.task_type} · {c.attempts} attempts{c.concepts.length ? ` · ${c.concepts.join(', ')}` : ''}</span></p>
          <div className="grid grid-cols-3 gap-2 mt-2 text-xs">
            {(['clean', 'mixed', 'trial_and_error'] as const).map((k) => (
              <div key={k} className="rounded-lg bg-gray-50 p-2">
                <p className="text-gray-500">{k.replace(/_/g, ' ')}</p>
                <p className="text-gray-900 font-semibold">{c.paths[k].share_pct}% of attempts</p>
                <p className="text-gray-600">task {c.paths[k].avg_task_score}% · quiz {c.paths[k].avg_quiz_score ?? '—'}{c.paths[k].avg_quiz_score != null ? '%' : ''}</p>
              </div>
            ))}
          </div>
          <ul className="mt-2 text-sm text-gray-800 list-disc pl-5 space-y-0.5">{c.insights.map((t, i) => <li key={i}>{t}</li>)}</ul>
        </div>
      ))}
    </div>
  )
}
