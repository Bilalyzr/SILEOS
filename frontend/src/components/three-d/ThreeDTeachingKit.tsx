/**
 * ThreeDTeachingKit (2026-09-05): shown under a 3D lesson in the course editor.
 * Turns "I uploaded a model" into a teach-and-examine loop in four steps and
 * links every step to the tool that does it:
 *   1 Teach   — description = the T4 text equivalent (Tier Preview shows the fallback)
 *   2 Examine — build a match-and-verify task on THIS model (prefilled builder)
 *   3 Grade   — attach the task to a quiz as a scorable item (server-graded, path-aware)
 *   4 Learn   — insight cards on Insights: clean vs trial-and-error paths × quiz outcomes
 * Lists the published tasks that already exist for the model.
 */
import * as React from 'react'
import { Link } from 'react-router-dom'
import { threeDTasksAPI, TASK_TYPE_INFO, type ThreeDTask } from '@/api/threeDTasks'
import { threeDAPI } from '@/api/threeD'

export function ThreeDTeachingKit({ modelId, lessonTitle, hasDescription }: { modelId: number; lessonTitle?: string; hasDescription: boolean }) {
  const [tasks, setTasks] = React.useState<ThreeDTask[] | null>(null)
  const [building, setBuilding] = React.useState(false)
  const [tierNote, setTierNote] = React.useState<string | null>(null)
  const buildTiers = async () => {
    setBuilding(true); setTierNote(null)
    try {
      const r = await threeDAPI.buildTiers(modelId)
      const mb = (n: number) => `${(n / 1048576).toFixed(1)} MB`
      setTierNote(`Built: T1 ${mb(r.sizes.T1)} · T2 ${r.sizes.T2 ? mb(r.sizes.T2) : '—'} · T3 ${r.sizes.T3 ? mb(r.sizes.T3) : '—'} — phones now download the lighter file automatically.`)
    } catch (e: any) { setTierNote(e?.response?.data?.detail || 'Tier build failed') }
    finally { setBuilding(false) }
  }
  React.useEffect(() => { threeDTasksAPI.forModel(modelId).then(setTasks).catch(() => setTasks([])) }, [modelId])
  const builderHref = `/instructor/three-d-tasks?model_id=${modelId}&title=${encodeURIComponent((lessonTitle || 'Model') + ' — check')}`

  const steps = [
    { n: 1, title: 'Teach', text: hasDescription ? 'Description set — it doubles as the text equivalent for learners without WebGL.' : 'Write the lesson description: what to look at, in what order. It becomes the T4 text equivalent.', ok: hasDescription },
    { n: 2, title: 'Examine', text: 'Build a match / identify / measure / sequence task on this exact model. Grading is server-side and records how the learner got there (clean vs trial-and-error).', ok: (tasks?.length || 0) > 0, href: builderHref, cta: 'Create an exam task from this model' },
    { n: 3, title: 'Grade', text: 'Attach the published task to a quiz as a scorable item — it scores into the 3D bucket of the cumulative grade and feeds the mastery graph.', ok: false },
    { n: 4, title: 'Learn', text: 'Insights → "Next Class & 3D Insights" shows which learners reasoned and which clicked, against their quiz scores on the same concepts.', ok: false, href: '/instructor/insights', cta: 'Open insights' },
  ]

  return (
    <div className="mt-3 rounded-xl border border-orange-200 bg-gradient-to-br from-orange-50 via-white to-amber-50 p-4" data-testid="three-d-kit">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <p className="text-sm font-semibold text-gray-900">Teach &amp; examine with this model</p>
        <span className="text-[11px] text-gray-500">{tasks === null ? '…' : `${tasks.length} published task${tasks.length === 1 ? '' : 's'} on this model`}</span>
      </div>
      <ol className="grid sm:grid-cols-2 gap-2">
        {steps.map((s) => (
          <li key={s.n} className="glass-panel rounded-lg p-3 text-xs">
            <p className="font-semibold text-gray-900 flex items-center gap-2">
              <span className={`h-5 w-5 grid place-items-center rounded-full text-[11px] ${s.ok ? 'bg-emerald-600 text-white' : 'si-gradient text-white'}`}>{s.ok ? '✓' : s.n}</span>{s.title}
            </p>
            <p className="text-gray-600 mt-1">{s.text}</p>
            {s.href && <Link to={s.href} className="inline-block mt-1.5 text-primary-700 font-medium hover:underline">{s.cta} →</Link>}
          </li>
        ))}
      </ol>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <button type="button" disabled={building} onClick={buildTiers} className="px-2.5 py-1 rounded-lg border border-orange-300 text-orange-800 hover:bg-orange-50 disabled:opacity-40">{building ? 'Building…' : 'Pre-build lighter tiers (T2/T3)'}</button>
        {tierNote && <span className="text-gray-600">{tierNote}</span>}
      </div>
      {tasks && tasks.length > 0 && (
        <ul className="mt-2 text-xs text-gray-700 space-y-0.5">
          {tasks.map((t) => <li key={t.id}>• <span className="font-medium">{t.title}</span> · {TASK_TYPE_INFO[t.task_type]?.label || t.task_type} · {t.max_score} marks · floor {t.tier_floor}</li>)}
        </ul>
      )}
    </div>
  )
}

export default ThreeDTeachingKit
