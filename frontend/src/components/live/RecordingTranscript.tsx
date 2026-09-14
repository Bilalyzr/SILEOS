import { useEffect, useRef, useState } from 'react'
import { api } from '@/api/axios'
import { NativeVideoPlayer, type VideoPlayerHandle } from '@/components/video/native-video-player'
import type { Segment, Chapter } from '@/api/recording-lessons'
import { plannerError } from '@/api/planner'

export const timestamp = (seconds: number) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`

export default function RecordingTranscript({classId, segments, chapters, initialStart = 0, onEdit}: {
  classId: number; segments: Segment[]; chapters: Chapter[]; initialStart?: number; onEdit?: (index: number, text: string) => void
}) {
  const [search, setSearch] = useState('')
  const [src, setSrc] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState(initialStart)
  const player = useRef<VideoPlayerHandle>(null)
  const desiredTime = useRef(initialStart)
  useEffect(() => { setSrc(''); setError(''); setSearch(''); setSelected(initialStart); desiredTime.current = initialStart }, [classId, initialStart])
  const aliveClass = useRef(classId)
  aliveClass.current = classId
  async function jump(seconds: number) {
    desiredTime.current = seconds; setSelected(seconds)
    if (src) { player.current?.seekTo(seconds); return }
    setBusy(true); setError('')
    try {
      const response = await api.get(`/live/classes/${classId}/recording-playback`)
      if (aliveClass.current === classId) setSrc(response.data.hls_url)
    } catch (e) { if (aliveClass.current === classId) setError(plannerError(e)) }
    finally { if (aliveClass.current === classId) setBusy(false) }
  }
  const matches = segments.map((segment, index) => ({...segment, index})).filter(s => s.text.toLocaleLowerCase().includes(search.toLocaleLowerCase()))
  return <section className="space-y-4">
    {src ? <NativeVideoPlayer ref={player} src={src} onDuration={() => player.current?.seekTo(desiredTime.current)} /> :
      <div className="rounded-xl bg-slate-900 p-6 text-white"><p className="mb-3">Listen alongside the transcript</p><button className="rounded-lg bg-white px-4 py-2 text-slate-900 disabled:opacity-50" disabled={busy} onClick={() => jump(selected)}>{busy ? 'Loading recording…' : `Play from ${timestamp(selected)}`}</button></div>}
    {error && <p role="alert" className="rounded-lg bg-amber-50 p-3 text-amber-900">{error} Transcript and notes remain available.</p>}
    <div className="flex flex-wrap gap-2" aria-label="Recording chapters">{chapters.map((c, i) => <button key={i} disabled={busy} onClick={() => jump(c.start)} className="max-w-full truncate rounded-lg border bg-white px-3 py-2 text-left text-sm">{timestamp(c.start)} · {c.title}</button>)}</div>
    <label className="block text-sm font-medium">Search transcript<input value={search} onChange={e => setSearch(e.target.value)} placeholder="Find a word or concept…" className="mt-1 w-full rounded-lg border p-3" /></label>
    <p className="text-xs text-slate-500">{matches.length} matching segments{matches.length > 100 ? ' · Showing the first 100; narrow your search for more.' : ''}</p>
    <div className="max-h-[480px] space-y-2 overflow-auto">{matches.slice(0, 100).map(s => <div key={s.index} className="flex items-start gap-3 rounded-lg border bg-white p-3">
      <button disabled={busy} onClick={() => jump(s.start)} className="shrink-0 text-sm font-medium text-orange-700" aria-label={`Jump to ${timestamp(s.start)}`}>{timestamp(s.start)}</button>
      {onEdit ? <textarea aria-label={`Transcript at ${timestamp(s.start)}`} value={s.text} onChange={e => onEdit(s.index, e.target.value)} className="min-h-20 w-full rounded border p-2 text-sm" /> : <p className="text-sm leading-6">{s.text}</p>}
    </div>)}{!matches.length && <p className="p-4 text-sm text-slate-500">No matching transcript segments.</p>}</div>
  </section>
}
