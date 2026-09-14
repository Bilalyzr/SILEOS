/**
 * GeoGebra authoring card for the course wizard (free courses only — the
 * backend enforces the same rule, this UI just mirrors it). Two modes:
 *   - paste a GeoGebra Materials URL (embeds that resource), or
 *   - pick an app type for a blank interactive students explore.
 * Creates the applet via the API, then hands the id up for the atomic
 * (lesson_content_type='geogebra', geogebra_applet_id) pair.
 */
import { useState } from 'react'
import toast from 'react-hot-toast'
import { GEOGEBRA_APP_TYPES, geogebraAPI } from '@/api/geogebra'

export function GeoGebraAuthorCard({
  title,
  attachedId,
  onAttach,
}: {
  title: string
  attachedId: number | null
  onAttach: (appletId: number) => void
}) {
  const [mode, setMode] = useState<'material' | 'blank'>('material')
  const [materialUrl, setMaterialUrl] = useState('')
  const [appType, setAppType] = useState<string>('graphing')
  const [busy, setBusy] = useState(false)
  const [attachedTitle, setAttachedTitle] = useState<string | null>(null)

  async function create() {
    setBusy(true)
    try {
      const applet = await geogebraAPI.create({
        title: title || 'Interactive',
        app_type: appType,
        ...(mode === 'material' ? { material_id: materialUrl.trim() } : {}),
      })
      setAttachedTitle(applet.title)
      onAttach(applet.id)
      toast.success('GeoGebra interactive created & attached')
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : 'Failed to create applet')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-3 p-4 bg-violet-50 border border-violet-200 rounded-lg">
      <h5 className="font-medium text-gray-900 mb-1">📐 GeoGebra interactive</h5>
      {attachedId ? (
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-emerald-700">
            ✓ Attached (applet #{attachedId}{attachedTitle ? ` — ${attachedTitle}` : ''})
          </span>
          <button
            type="button"
            onClick={() => { setAttachedTitle(null); }}
            className="text-sm text-violet-600 hover:underline"
            disabled={busy}
          >
            Create another
          </button>
        </div>
      ) : (
        <>
          <p className="text-xs text-gray-500 mb-3">
            Free-course exclusive — add an interactive graph or geometry canvas students can manipulate.
          </p>
          <div className="flex gap-2 mb-3">
            <button
              type="button"
              onClick={() => setMode('material')}
              className={`px-3 py-1.5 text-xs font-medium rounded-full border ${mode === 'material' ? 'bg-violet-600 text-white border-violet-600' : 'bg-white text-gray-700 border-gray-300'}`}
            >
              From GeoGebra link
            </button>
            <button
              type="button"
              onClick={() => setMode('blank')}
              className={`px-3 py-1.5 text-xs font-medium rounded-full border ${mode === 'blank' ? 'bg-violet-600 text-white border-violet-600' : 'bg-white text-gray-700 border-gray-300'}`}
            >
              Blank interactive
            </button>
          </div>
          {mode === 'material' ? (
            <input
              type="url"
              value={materialUrl}
              onChange={(e) => setMaterialUrl(e.target.value)}
              placeholder="https://www.geogebra.org/m/…"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          ) : (
            <select
              value={appType}
              onChange={(e) => setAppType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
            >
              {GEOGEBRA_APP_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          )}
          <button
            type="button"
            onClick={create}
            disabled={busy || (mode === 'material' && !materialUrl.trim())}
            className="mt-3 px-4 py-2 bg-violet-600 text-white rounded-lg text-sm font-medium hover:bg-violet-700 disabled:opacity-40"
          >
            {busy ? 'Creating…' : 'Create & attach'}
          </button>
        </>
      )}
    </div>
  )
}

export default GeoGebraAuthorCard
