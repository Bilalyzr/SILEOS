/**
 * GuardianVisibility (v2.0 §4.2 Parent View Configurator — WP6): which
 * signals a guardian sees for this course in the parent digest. Defaults
 * come from the course type (SP: attendance + completion only). Saved via
 * PUT /api/v1/studio/courses/{id}/settings {parent_view}.
 */
import * as React from 'react'
import toast from 'react-hot-toast'
import { PARENT_VIEW_LABELS, studioAPI, type ParentViewKey, type StudioSettings } from '@/api/studio'

export function GuardianVisibility({ courseId, settings, onChange }: { courseId: number; settings: StudioSettings; onChange: (s: StudioSettings) => void }) {
  const [busy, setBusy] = React.useState<ParentViewKey | null>(null)
  const toggle = async (key: ParentViewKey) => {
    setBusy(key)
    try {
      const next = await studioAPI.update(courseId, { parent_view: { [key]: !settings.parent_view[key] } })
      onChange(next)
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Could not save') }
    finally { setBusy(null) }
  }
  return (
    <div className="border border-gray-200 rounded-xl p-6 bg-sky-50" data-testid="guardian-visibility">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 bg-sky-100 rounded-lg flex items-center justify-center"><span className="text-sky-700 text-xl">👪</span></div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Guardian visibility</h3>
          <p className="text-sm text-gray-500">What a linked parent sees for this course in their weekly digest.</p>
        </div>
      </div>
      <div className="grid sm:grid-cols-2 gap-2">
        {(Object.keys(PARENT_VIEW_LABELS) as ParentViewKey[]).map((k) => (
          <label key={k} className="flex items-center gap-2 text-sm text-gray-800 bg-white rounded-lg border border-gray-200 px-3 py-2">
            <input type="checkbox" checked={!!settings.parent_view[k]} disabled={busy === k} onChange={() => toggle(k)} />
            {PARENT_VIEW_LABELS[k]}
          </label>
        ))}
      </div>
      <p className="text-[11px] text-gray-500 mt-2">Financials are never shown to guardians. Class reports appear only when you also tick "Share with guardians" on the report itself.</p>
    </div>
  )
}

export default GuardianVisibility
