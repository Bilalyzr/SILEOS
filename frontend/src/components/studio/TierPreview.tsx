/**
 * TierPreview (v2.0 §4.2 — WP6): lets an MP/UP instructor see how a 3D lesson
 * degrades down the tier ladder before publishing.
 *   T1 interactive 3D · T3 auto-rotating turntable (what a low-power device
 *   gets) · T4 still image + text equivalent (what a T4/T5 learner gets).
 * A performance meter (fps, triangles, draw calls) runs while the 3D tiers
 * are visible; the GLB budget line comes from the file size.
 */
import * as React from 'react'
import { ThreeDViewer, type ViewerStats } from '@/components/three-d/ThreeDViewer'
import { threeDAPI } from '@/api/threeD'

type Tier = 'T1' | 'T3' | 'T4'
const TIERS: { id: Tier; label: string; hint: string }[] = [
  { id: 'T1', label: 'T1 · Interactive 3D', hint: 'Full orbit / zoom on capable devices' },
  { id: 'T3', label: 'T3 · Turntable', hint: 'Auto-rotate only — low-power phones, no WebGL input' },
  { id: 'T4', label: 'T4 · Still + text', hint: 'Snapshot + text equivalent — the parity floor' },
]
const GLB_BUDGET_MB = 25

export function TierPreview({ modelId, description }: { modelId: number; description?: string }) {
  const [tier, setTier] = React.useState<Tier>('T1')
  const [stats, setStats] = React.useState<ViewerStats | null>(null)
  const [still, setStill] = React.useState<string | null>(null)
  const [sizeMb, setSizeMb] = React.useState<number | null>(null)
  const captureRef = React.useRef<(() => string | null) | null>(null)

  React.useEffect(() => {
    threeDAPI.list().then((d) => {
      const m = [...d.models, ...(d.library || [])].find((x) => x.id === modelId)
      if (m) setSizeMb(Math.round((m.file_size_bytes / 1048576) * 10) / 10)
    }).catch(() => {})
  }, [modelId])

  const pick = (t: Tier) => {
    if (t === 'T4') setStill(captureRef.current?.() ?? null)
    setTier(t)
  }
  const fpsTone = !stats ? 'text-gray-500' : stats.fps >= 45 ? 'text-emerald-700' : stats.fps >= 25 ? 'text-amber-700' : 'text-red-700'

  return (
    <div className="mt-3 rounded-xl border border-indigo-100 bg-indigo-50/40 p-3" data-testid="tier-preview">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-indigo-900">Tier preview</span>
        {TIERS.map((t) => (
          <button key={t.id} type="button" onClick={() => pick(t.id)} title={t.hint}
            className={`px-2.5 py-1 rounded-full text-xs border ${tier === t.id ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}>
            {t.label}
          </button>
        ))}
        <span className="ml-auto text-[11px] text-gray-500">{TIERS.find((t) => t.id === tier)?.hint}</span>
      </div>

      {tier !== 'T4' ? (
        <ThreeDViewer modelId={modelId} height={300} description={description} autoRotate={tier === 'T3'} interactive={tier === 'T1'}
          onStats={setStats} captureRef={captureRef} />
      ) : (
        <div className="grid sm:grid-cols-2 gap-3">
          <div className="rounded-lg border border-gray-200 bg-white grid place-items-center min-h-[180px] overflow-hidden">
            {still ? <img src={still} alt={description || '3D model snapshot'} className="max-h-[300px]" />
              : <p className="text-xs text-gray-500 p-4 text-center">Open T1 or T3 first so a frame can be captured, then come back to T4.</p>}
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm">
            <p className="text-xs font-semibold text-gray-700 mb-1">Text equivalent (what a T4/T5 learner reads)</p>
            {description ? <p className="text-gray-800 whitespace-pre-wrap">{description}</p>
              : <p className="text-amber-700 text-xs">No text description on this lesson yet — add one in the lesson description so the T4 experience teaches the same idea (§10.11 parity rule).</p>}
          </div>
        </div>
      )}

      <div className="mt-2 flex flex-wrap gap-3 text-[11px]">
        <span className={fpsTone}>{stats ? `${stats.fps} fps` : 'fps —'}</span>
        <span className="text-gray-600">{stats ? `${stats.triangles.toLocaleString()} triangles · ${stats.drawCalls} draw calls` : 'scene —'}</span>
        {sizeMb != null && (
          <span className={sizeMb > GLB_BUDGET_MB ? 'text-red-700' : 'text-gray-600'}>
            {sizeMb} MB GLB{sizeMb > GLB_BUDGET_MB ? ` · over the ${GLB_BUDGET_MB} MB mobile budget` : ''}
          </span>
        )}
        {stats && stats.fps < 25 && <span className="text-red-700">Below 25 fps on this machine — lower-end phones will fall to T3/T4.</span>}
      </div>
    </div>
  )
}

export default TierPreview
