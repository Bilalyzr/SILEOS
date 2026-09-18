/**
 * AdaptiveLessonPanel (Engine B, v2.0 §9.2 — WP7): a learner asks for a
 * mini-lesson pitched at their mastery (recover / consolidate / extend) for
 * one course. Draft for this learner only — never added to the curriculum.
 * Honest 503 when GLM_API_KEY is absent.
 */
import { useEffect, useState } from 'react'
import { aiLayerAPI, errDetail, type AdaptiveLesson, type AdaptiveMode } from '@/api/aiLayer'

const MODES: { id: AdaptiveMode | ''; label: string }[] = [
  { id: '', label: 'Auto (from my mastery)' }, { id: 'recover', label: 'Recover' }, { id: 'consolidate', label: 'Consolidate' }, { id: 'extend', label: 'Extend' },
]

export function AdaptiveLessonPanel({ courseId, concept }: { courseId: number; concept?: string }) {
  const [mode, setMode] = useState<AdaptiveMode | ''>('')
  const [topic, setTopic] = useState(concept || '')
  const [busy, setBusy] = useState(false)
  const [lesson, setLesson] = useState<AdaptiveLesson | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  // null = unknown, false = deployment has no GLM_API_KEY (backend /ai/config).
  const [configured, setConfigured] = useState<boolean | null>(null)

  useEffect(() => {
    let live = true
    aiLayerAPI.config()
      .then((c) => { if (live) setConfigured(!!c.llm_configured) })
      .catch(() => { if (live) setConfigured(null) })
    return () => { live = false }
  }, [courseId])

  const go = async () => {
    setBusy(true); setMsg(null)
    try {
      setLesson(await aiLayerAPI.adaptiveLesson(courseId, { mode: mode || undefined, concept: topic.trim() || undefined }))
    } catch (e) {
      const { status, detail } = errDetail(e, 'Could not build the lesson')
      setMsg(status === 503 ? `Not available yet: ${detail}` : detail)
    } finally { setBusy(false) }
  }

  // Quiet disabled state: without a provider key the generate call can only
  // ever 503, so show why instead of a button that reliably errors.
  if (configured === false) {
    return (
      <div className="rounded-xl border border-violet-200 bg-violet-50/50 p-4" data-testid="adaptive-lesson">
        <p className="font-semibold text-gray-900">Adaptive mini-lesson</p>
        <p className="text-xs text-gray-600 mt-2">Not available yet on this deployment — ask your instructor to enable it. Your mastery graph keeps recording evidence in the meantime.</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-violet-200 bg-violet-50/50 p-4" data-testid="adaptive-lesson">
      <p className="font-semibold text-gray-900">Adaptive mini-lesson</p>
      <p className="text-xs text-gray-600 mb-2">A short lesson pitched at where you are on one concept — recover a gap, consolidate, or go a step further.</p>
      <div className="flex flex-wrap gap-2 items-center">
        <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Concept (blank = your weakest)" className="flex-1 min-w-[10rem] px-3 py-1.5 border border-gray-300 rounded-lg text-sm" aria-label="Concept" />
        <select value={mode} onChange={(e) => setMode(e.target.value as AdaptiveMode | '')} className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm" aria-label="Mode">
          {MODES.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
        </select>
        <button type="button" disabled={busy} onClick={go} className="px-3 py-1.5 text-sm rounded-lg bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-40">{busy ? 'Building…' : 'Build my lesson'}</button>
      </div>
      {msg && <p className="text-xs text-amber-800 mt-2" role="alert">{msg}</p>}
      {lesson && (
        <div className="mt-3 rounded-lg bg-white border border-gray-200 p-3 text-sm">
          <p className="text-xs text-violet-700 uppercase tracking-wide">{lesson.mode}{lesson.concept ? ` · ${lesson.concept}` : ''}{lesson.estimate != null ? ` · mastery ${Math.round(lesson.estimate)}%` : ''}</p>
          <h3 className="font-semibold text-gray-900">{lesson.lesson.title || 'Your lesson'}</h3>
          {(lesson.lesson.sections || []).map((s, i) => (
            <div key={i} className="mt-2"><p className="font-medium text-gray-800">{s.heading}</p><p className="text-gray-700 whitespace-pre-wrap">{s.body}</p></div>
          ))}
          {lesson.lesson.check && (
            <details className="mt-2 text-gray-700"><summary className="cursor-pointer font-medium">Check yourself: {lesson.lesson.check.question}</summary><p className="mt-1">{lesson.lesson.check.answer}</p></details>
          )}
          <p className="text-[11px] text-gray-400 mt-2">{lesson.note}</p>
        </div>
      )}
    </div>
  )
}

export default AdaptiveLessonPanel
