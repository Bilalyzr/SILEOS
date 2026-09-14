/**
 * VirtualLabPlayer — fetches a catalog entry by slug and renders it:
 *   native → NativeLabPlayer (Reaction / Identify engines, advisory scores)
 *   phet / embed → iframe with loading state + "open in full screen" fallback
 * Attribution always rendered (PhET is CC-BY; admin embeds carry their own).
 */
import * as React from 'react'
import { ConceptLabPlayer } from './ConceptLabPlayer'
import type { ConceptConfig } from '@/api/lab-studio'
import { getLab, type LabDetail } from '@/api/labs'
// WP9 progressive loading: the native engines (+ SVG diagrams) are a separate chunk
const NativeLabPlayer = React.lazy(() => import('./NativeLabPlayer').then((m) => ({ default: m.NativeLabPlayer })))

interface Props {
  slug: string
  title?: string
  height?: number
  previewOnly?: boolean
  onLessonComplete?: () => void
}

export function VirtualLabPlayer({ slug, title, height = 560, previewOnly = false, onLessonComplete }: Props) {
  const [lab, setLab] = React.useState<LabDetail | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [loaded, setLoaded] = React.useState(false)

  React.useEffect(() => {
    let cancelled = false
    setLab(null)
    setError(null)
    setLoaded(false)
    getLab(slug)
      .then((d) => { if (!cancelled) setLab(d) })
      .catch((err: any) => {
        if (!cancelled) setError(err?.response?.status === 404 ? 'This lab is no longer in the catalog.' : 'Could not load the lab.')
      })
    return () => { cancelled = true }
  }, [slug])

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</div>
    )
  }
  if (!lab) {
    return (
      <div className="grid place-items-center rounded-xl border border-gray-200 bg-gray-50" style={{ height: Math.min(height, 240) }}>
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-2" />
          <p className="text-sm text-gray-500">Loading lab…</p>
        </div>
      </div>
    )
  }

  if (lab.native_template === 'concept_lab') return <ConceptLabPlayer slug={slug} revision={lab.revision} previewOnly={previewOnly} config={lab.config as ConceptConfig} title={title || lab.title} height={height} />

  if (lab.provider === 'native') {
    return (
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-gray-900">{title || lab.title}</h3>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">Gradeable lab · {lab.max_score} pts</span>
        </div>
        <React.Suspense fallback={<p className="text-sm text-gray-500 p-4">Loading the lab…</p>}>
          <NativeLabPlayer lab={lab} previewOnly={previewOnly} onLessonComplete={onLessonComplete} />
        </React.Suspense>
        <p className="text-[11px] text-gray-400 mt-2">{lab.source}</p>
      </div>
    )
  }

  const src = lab.embed_url || ''
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold text-gray-900">{title || lab.title}</h3>
        <a href={src} target="_blank" rel="noreferrer" className="text-xs font-medium text-blue-600 hover:underline">
          Open in full screen ↗
        </a>
      </div>
      <div className="relative rounded-xl overflow-hidden border border-gray-200 bg-white" style={{ height }}>
        {!loaded && (
          <div className="absolute inset-0 grid place-items-center bg-gray-50">
            <div className="text-center">
              <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-2" />
              <p className="text-sm text-gray-500">Loading simulation… (a few MB, first time only)</p>
              <p className="text-xs text-gray-400 mt-1">If it stays blank, use “Open in full screen”.</p>
            </div>
          </div>
        )}
        {/* Curated, admin-allowlisted content: no sandbox — these sims need
            WebGL/storage APIs that sandboxes restrict (same as before). */}
        <iframe
          src={src}
          title={title || lab.title}
          className="w-full h-full border-0"
          onLoad={() => setLoaded(true)}
          allow="fullscreen; xr-spatial-tracking"
          allowFullScreen
        />
      </div>
      {lab.source && <p className="text-[11px] text-gray-400 mt-1">{lab.source}</p>}
    </div>
  )
}

export default VirtualLabPlayer
