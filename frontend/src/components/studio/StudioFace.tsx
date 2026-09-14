/**
 * StudioFace (v2.0 §4.1 — WP6): the type-specific opening state an instructor
 * sees right after creating a draft, at the top of the Curriculum tab.
 *   MP (meiporul)        → asset library: shared 3D models + labs to attach
 *   SP (seyappaduporul)  → schedule builder (term view + clone week)
 *   UP (utporul)         → outcome definition + target concepts
 * Dismissable per course (face_dismissed persists server-side); reopen from
 * the small "Studio" chip. Never blocks the ordinary curriculum editor.
 */
import * as React from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { studioAPI, type StudioSettings } from '@/api/studio'
import { masteryAPI, parseConcepts } from '@/api/mastery'
import { threeDAPI, type ThreeDModel } from '@/api/threeD'
import { listLabs, type LabSummary } from '@/api/labs'
import { ScheduleBuilder } from './ScheduleBuilder'

const FACE_TITLES: Record<string, { title: string; blurb: string }> = {
  asset_library: { title: 'Start from the asset library', blurb: 'Meiporul courses teach with things you can turn over in your hands. Pick shared 3D models and virtual labs, then add a lesson of type "3D model" or "Virtual lab" and attach them.' },
  schedule: { title: 'Lay out the term', blurb: 'Seyappaduporul courses run on a schedule. Add the first live class, then clone the week across the term. Recorded lessons and quizzes slot in between.' },
  outcome: { title: 'Define the outcome first', blurb: 'Utporul courses are built backwards from what a learner must be able to do. Write the outcome and the target concepts — the coverage report then shows which ones your curriculum teaches and assesses.' },
  curriculum: { title: 'Build the curriculum', blurb: 'Add sections and lessons below.' },
}

function AssetLibraryFace({ courseId }: { courseId: number }) {
  const [models, setModels] = React.useState<ThreeDModel[]>([])
  const [labs, setLabs] = React.useState<LabSummary[]>([])
  React.useEffect(() => {
    threeDAPI.list().then((d) => setModels([...(d.library || []), ...d.models].slice(0, 8))).catch(() => {})
    listLabs().then((l) => setLabs(l.slice(0, 8))).catch(() => {})
  }, [])
  return (
    <div className="grid md:grid-cols-2 gap-3">
      <div className="rounded-lg border border-gray-200 bg-white p-3">
        <p className="text-sm font-semibold text-gray-900 mb-1">3D models {models.length > 0 && <span className="text-gray-400 font-normal">· {models.length} available</span>}</p>
        {models.length === 0 ? <p className="text-xs text-gray-500">No models yet — upload a GLB from a "3D model" lesson, or ask the admin to import a library under Content Libraries.</p> : (
          <ul className="text-sm text-gray-800 space-y-0.5">{models.map((m) => <li key={m.id} className="flex items-center gap-2"><span className="truncate">{m.title}</span>{m.is_library && <span className="text-[10px] px-1 rounded bg-indigo-50 text-indigo-700">shared</span>}</li>)}</ul>
        )}
        <Link to="/instructor/three-d-tasks" className="inline-block mt-2 text-xs text-blue-600 hover:underline">Build a 3D match-and-verify task →</Link>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white p-3">
        <p className="text-sm font-semibold text-gray-900 mb-1">Virtual labs {labs.length > 0 && <span className="text-gray-400 font-normal">· {labs.length} in the catalog</span>}</p>
        {labs.length === 0 ? <p className="text-xs text-gray-500">No labs in the catalog.</p> : (
          <ul className="text-sm text-gray-800 space-y-0.5">{labs.map((l) => <li key={l.slug} className="flex items-center gap-2"><span className="truncate">{l.title}</span><span className="text-[10px] px-1 rounded bg-gray-100 text-gray-600">{l.provider}</span></li>)}</ul>
        )}
        <p className="text-[11px] text-gray-500 mt-2">Attach from a lesson: set its type to "Virtual lab" and pick from this catalog.</p>
      </div>
      <p className="md:col-span-2 text-[11px] text-gray-500">Course {courseId} · every 3D lesson gets a Tier Preview below its model so you can check the T3/T4 fallbacks before publishing.</p>
    </div>
  )
}

function OutcomeFace({ courseId }: { courseId: number }) {
  const [text, setText] = React.useState('')
  const [concepts, setConcepts] = React.useState('')
  const [saving, setSaving] = React.useState(false)
  React.useEffect(() => {
    masteryAPI.outcome(courseId).then((o) => { setText(o.outcome_text || ''); setConcepts((o.target_concepts || []).join(', ')) }).catch(() => {})
  }, [courseId])
  const save = async () => {
    setSaving(true)
    try { await masteryAPI.setOutcome(courseId, text, parseConcepts(concepts)); toast.success('Outcome saved') }
    catch (e: any) { toast.error(e?.response?.data?.detail || 'Could not save the outcome') }
    finally { setSaving(false) }
  }
  return (
    <div className="space-y-2">
      <label className="block">
        <span className="block text-xs font-medium text-gray-700 mb-1">By the end of this course a learner can…</span>
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} maxLength={2000} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="e.g. Solve any right-angled triangle from two known measurements and justify each step." />
      </label>
      <label className="block">
        <span className="block text-xs font-medium text-gray-700 mb-1">Target concepts (comma-separated)</span>
        <input value={concepts} onChange={(e) => setConcepts(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="trigonometric ratios, pythagoras theorem, angle of elevation" />
      </label>
      <div className="flex items-center gap-3">
        <button type="button" disabled={saving} onClick={save} className="px-3 py-1.5 text-sm rounded-lg bg-gray-900 text-white hover:bg-black disabled:opacity-40">{saving ? 'Saving…' : 'Save outcome'}</button>
        <Link to={`/instructor/courses/${courseId}/coverage`} className="text-sm text-blue-600 hover:underline">Open the coverage report →</Link>
      </div>
    </div>
  )
}

export function StudioFace({ courseId, courseType, forceOpen }: { courseId: number; courseType: string; forceOpen?: boolean }) {
  const [settings, setSettings] = React.useState<StudioSettings | null>(null)
  const [open, setOpen] = React.useState<boolean | null>(null)

  React.useEffect(() => {
    studioAPI.settings(courseId).then((s) => { setSettings(s); setOpen(forceOpen || !s.face_dismissed) }).catch(() => setSettings(null))
  }, [courseId, forceOpen, courseType])

  if (!settings) return null
  const face = settings.opening_face
  const meta = FACE_TITLES[face] || FACE_TITLES.curriculum
  const dismiss = async () => {
    setOpen(false)
    try { await studioAPI.update(courseId, { face_dismissed: true }) } catch { /* best-effort */ }
  }

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)} className="mb-4 inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs border border-indigo-200 bg-indigo-50 text-indigo-800 hover:bg-indigo-100" data-testid="studio-face-chip">
        ✦ Studio: {meta.title}
      </button>
    )
  }
  return (
    <div className="mb-6 rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white p-4" data-testid="studio-face">
      <div className="flex items-start gap-3 mb-3">
        <div className="flex-1">
          <p className="text-[11px] uppercase tracking-wide text-indigo-600 font-semibold">Studio · {face.replace('_', ' ')}</p>
          <h3 className="text-base font-semibold text-gray-900">{meta.title}</h3>
          <p className="text-sm text-gray-600">{meta.blurb}</p>
        </div>
        <button type="button" onClick={dismiss} className="text-xs text-gray-500 hover:text-gray-900">Hide</button>
      </div>
      {face === 'asset_library' && <AssetLibraryFace courseId={courseId} />}
      {face === 'schedule' && <ScheduleBuilder courseId={courseId} />}
      {face === 'outcome' && <OutcomeFace courseId={courseId} />}
    </div>
  )
}

export default StudioFace
