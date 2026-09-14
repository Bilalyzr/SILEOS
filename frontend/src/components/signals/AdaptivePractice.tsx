import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, XCircle, Sparkles } from 'lucide-react'
import { signalsAPI, signal, AdaptiveBuild, AdaptiveResult } from '@/api/signals'

interface Props { courseId: number; onClose: () => void }

/** Practice set built from the learner's struggle profile. Grading is
 *  server-side; answers feed the mastery graph. Question time + answer
 *  changes are captured as signals so the next set adapts again. */
export default function AdaptivePractice({ courseId, onClose }: Props) {
  const [build, setBuild] = useState<AdaptiveBuild | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [result, setResult] = useState<AdaptiveResult | null>(null)
  const [busy, setBusy] = useState(false)
  const changes = useRef<Record<string, number>>({})
  const started = useRef<Record<string, number>>({})

  const builtRef = useRef(false)
  useEffect(() => {
    if (builtRef.current) return   // StrictMode double-invokes effects; one session per open
    builtRef.current = true
    signalsAPI.buildAdaptive(courseId, 8)
      .then(setBuild)
      .catch((e) => setError(e?.response?.data?.detail || 'Could not build a practice set yet.'))
  }, [courseId])

  const choose = (qid: number, opt: string, quizConcepts: string[]) => {
    const key = String(qid)
    if (!started.current[key]) started.current[key] = Date.now()
    if (answers[key] !== undefined && answers[key] !== opt) changes.current[key] = (changes.current[key] || 0) + 1
    setAnswers((a) => ({ ...a, [key]: opt }))
    void quizConcepts
  }

  const submit = async () => {
    if (!build) return
    setBusy(true)
    try {
      for (const q of build.questions) {
        const key = String(q.question_id)
        const t0 = started.current[key]
        if (t0) signal({ kind: 'question_time', course_id: courseId, question_id: q.question_id, value: Math.round((Date.now() - t0) / 1000) })
        if (changes.current[key]) signal({ kind: 'answer_change', course_id: courseId, question_id: q.question_id, value: changes.current[key] })
      }
      setResult(await signalsAPI.submitAdaptive(build.session_id, answers))
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Submit failed.')
    } finally { setBusy(false) }
  }

  if (error) return <div className="rounded-xl border border-amber-300/40 bg-amber-50/40 p-3 text-sm text-amber-800">{error} <button className="underline ml-2" onClick={onClose}>close</button></div>
  if (!build) return <div className="text-sm text-gray-500">Building your practice set…</div>

  if (result) {
    const verdict = new Map(result.results.map((r) => [r.question_id, r]))
    return (
      <div className="space-y-3" data-testid="adaptive-result">
        <div className="flex items-center gap-2 text-gray-900 font-semibold">
          <Sparkles className="w-4 h-4 text-primary-600" /> You scored {result.score} / {result.max_score}
        </div>
        <ul className="grid gap-1 sm:grid-cols-2">
          {result.by_concept.map((b) => (
            <li key={b.concept} className="text-sm flex justify-between rounded-lg bg-white/40 px-3 py-1.5">
              <span className="capitalize">{b.concept}</span><span className="text-gray-500">{b.correct}/{b.total}</span>
            </li>
          ))}
        </ul>
        <ol className="space-y-2">
          {build.questions.map((q, i) => {
            const r = verdict.get(q.question_id)
            return (
              <li key={q.question_id} className="text-sm flex gap-2">
                {r?.correct ? <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" /> : <XCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />}
                <span><span className="text-gray-500">{i + 1}.</span> {q.title}{!r?.correct && r?.expected?.length ? <span className="text-gray-500"> — expected: {r.expected.join(', ')}</span> : null}</span>
              </li>
            )
          })}
        </ol>
        <div className="flex gap-2">
          <button type="button" className="si-btn-ghost text-sm" onClick={onClose}>Done</button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4" data-testid="adaptive-practice">
      <div className="rounded-xl bg-white/40 p-3 text-sm">
        <div className="font-medium text-gray-900">Why these questions</div>
        <ul className="mt-1 text-gray-500 list-disc pl-5">{build.plan.why.map((w, i) => <li key={i}>{w}</li>)}</ul>
      </div>
      <ol className="space-y-4">
        {build.questions.map((q, i) => (
          <li key={q.question_id} className="rounded-xl border border-white/20 bg-white/30 p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="font-medium text-gray-900"><span className="text-gray-500 mr-1">{i + 1}.</span>{q.title}</div>
              <span className="text-[11px] rounded-full bg-white/50 px-2 py-0.5 text-gray-500 capitalize shrink-0">{q.difficulty} · {q.concepts.join(', ')}</span>
            </div>
            {q.options.length > 0 ? (
              <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
                {q.options.map((o) => (
                  <button
                    key={o}
                    type="button"
                    onClick={() => choose(q.question_id, o, q.concepts)}
                    className={`text-left text-sm rounded-lg px-3 py-2 border transition ${answers[String(q.question_id)] === o ? 'border-primary-500 bg-orange-50/70 text-gray-900' : 'border-white/30 bg-white/40 hover:bg-white/60'}`}
                  >{o}</button>
                ))}
              </div>
            ) : (
              <input
                className="si-input mt-2 w-full"
                placeholder="Your answer"
                value={answers[String(q.question_id)] || ''}
                onFocus={() => { if (!started.current[String(q.question_id)]) started.current[String(q.question_id)] = Date.now() }}
                onChange={(e) => setAnswers((a) => ({ ...a, [String(q.question_id)]: e.target.value }))}
              />
            )}
          </li>
        ))}
      </ol>
      <div className="flex gap-2">
        <button type="button" className="si-btn-primary text-sm" disabled={busy || Object.keys(answers).length === 0} onClick={submit} data-testid="adaptive-submit">
          {busy ? 'Checking…' : 'Check my answers'}
        </button>
        <button type="button" className="si-btn-ghost text-sm" onClick={onClose}>Cancel</button>
      </div>
    </div>
  )
}
