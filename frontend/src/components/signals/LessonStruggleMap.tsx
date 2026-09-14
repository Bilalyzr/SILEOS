import { useCallback, useEffect, useState } from 'react'
import { Flame, Plus, Trash2 } from 'lucide-react'
import { signalsAPI, Heatmap } from '@/api/signals'

interface Props { lessonId: number }

const fmt = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

/** Instructor view: where learners rewind / replay / quit inside a lesson,
 *  and the concept markers that turn timestamps into concepts. */
export default function LessonStruggleMap({ lessonId }: Props) {
  const [map, setMap] = useState<Heatmap | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [time, setTime] = useState('0:00')
  const [concept, setConcept] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    signalsAPI.heatmap(lessonId).then(setMap).catch((e) => setError(e?.response?.status === 404 ? 'hidden' : 'Struggle map unavailable.'))
  }, [lessonId])
  useEffect(() => { load() }, [load])

  const parseTime = (t: string): number | null => {
    const m = t.trim().match(/^(\d+):(\d{1,2})$/)
    if (m) return Number(m[1]) * 60 + Number(m[2])
    return /^\d+$/.test(t.trim()) ? Number(t.trim()) : null
  }

  const addMarker = async () => {
    const t = parseTime(time)
    if (t == null || !concept.trim()) return
    setBusy(true)
    try {
      const markers = await signalsAPI.addMarker(lessonId, t, concept.trim())
      setMap((m) => (m ? { ...m, markers } : m))
      setConcept('')
      load()
    } catch (e: any) { setError(e?.response?.data?.detail || 'Could not add marker.') } finally { setBusy(false) }
  }

  const removeMarker = async (id: number) => {
    try {
      const markers = await signalsAPI.removeMarker(lessonId, id)
      setMap((m) => (m ? { ...m, markers } : m))
      load()
    } catch { /* ignore */ }
  }

  if (error === 'hidden') return null
  if (error) return <div className="text-xs text-gray-500">{error}</div>
  if (!map) return null

  const max = Math.max(1, ...map.segments.map((s) => s.score))
  const hot = new Set(map.struggle_segments.map((s) => s.segment))

  return (
    <div className="glass-panel p-4 space-y-3 mt-3" data-testid="lesson-struggle-map">
      <div className="flex items-center gap-2 flex-wrap">
        <Flame className="w-4 h-4 text-primary-600" />
        <span className="font-medium text-gray-900 text-sm">Struggle map</span>
        <span className="text-xs text-gray-500">
          {map.segments.length === 0 ? 'no learner signals yet' : `${map.segments.length} active 10-second segments · ${map.early_quits} early quit${map.early_quits === 1 ? '' : 's'}`}
        </span>
      </div>

      {map.segments.length > 0 && (
        <div className="flex items-end gap-[2px] h-16 rounded-lg bg-white/30 p-1" title="Height = struggle score per 10-second segment">
          {map.segments.map((s) => (
            <div
              key={s.segment}
              className={`flex-1 rounded-sm ${hot.has(s.segment) ? 'bg-gradient-to-t from-orange-600 to-amber-400' : 'bg-primary-500/40'}`}
              style={{ height: `${Math.max(6, (s.score / max) * 100)}%` }}
              title={`${fmt(s.start_s)}–${fmt(s.end_s)} · ${s.rewinds} rewinds, ${s.replays} replays, ${s.pauses} pauses, ${s.skips} skips · ${s.learners} learner(s) · ${s.concepts.join(', ') || 'no concept'}`}
            />
          ))}
        </div>
      )}

      {map.struggle_segments.length > 0 && (
        <ul className="text-xs space-y-1">
          {map.struggle_segments.map((s) => (
            <li key={s.segment} className="flex flex-wrap gap-x-2 text-gray-500">
              <span className="font-medium text-gray-900">{fmt(s.start_s)}–{fmt(s.end_s)}</span>
              <span>{s.rewinds} rewinds · {s.replays} replays · {s.learners} learner{s.learners === 1 ? '' : 's'}</span>
              <span className="capitalize text-primary-600">{s.concepts.join(', ') || 'add a marker to name the concept'}</span>
            </li>
          ))}
        </ul>
      )}

      <div>
        <div className="text-xs font-medium text-gray-900 mb-1">Concept markers <span className="text-gray-500 font-normal">— tell the platform which concept starts at which time</span></div>
        {map.markers.length > 0 && (
          <ul className="flex flex-wrap gap-1.5 mb-2">
            {map.markers.map((m) => (
              <li key={m.id} className="flex items-center gap-1 rounded-full bg-white/50 px-2 py-0.5 text-xs">
                <span className="font-mono">{fmt(m.time_s)}</span><span className="capitalize">{m.concept}</span>
                <button type="button" aria-label={`Remove marker ${m.concept}`} onClick={() => removeMarker(m.id)} className="text-gray-500 hover:text-rose-600"><Trash2 className="w-3 h-3" /></button>
              </li>
            ))}
          </ul>
        )}
        <div className="flex gap-2">
          <input className="si-input w-20 text-sm" value={time} onChange={(e) => setTime(e.target.value)} placeholder="m:ss" aria-label="Marker time" />
          <input className="si-input flex-1 text-sm" value={concept} onChange={(e) => setConcept(e.target.value)} placeholder="Concept taught from this time" aria-label="Marker concept"
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addMarker() } }} />
          <button type="button" className="si-btn-primary text-sm" disabled={busy || !concept.trim()} onClick={addMarker} data-testid="add-marker"><Plus className="w-4 h-4" /> Add</button>
        </div>
      </div>
    </div>
  )
}
