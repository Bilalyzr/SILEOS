/**
 * ScheduleBuilder (v2.0 §4.2 — WP6): the SP term view. Live classes grouped
 * by week, counts of live vs recorded vs assessed material, and "clone
 * week" (copy every class of one week into another at the same weekday and
 * time). Data from /api/v1/studio/courses/{id}/schedule.
 */
import * as React from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { studioAPI, type TermSchedule } from '@/api/studio'

const fmtTime = (iso: string) => new Date(iso).toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' })
const mondayOf = (d: Date) => { const x = new Date(d); x.setDate(x.getDate() - ((x.getDay() + 6) % 7)); return x.toISOString().slice(0, 10) }
const addDays = (iso: string, n: number) => { const x = new Date(iso + 'T00:00:00Z'); x.setUTCDate(x.getUTCDate() + n); return x.toISOString().slice(0, 10) }

export function ScheduleBuilder({ courseId }: { courseId: number }) {
  const [data, setData] = React.useState<TermSchedule | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [busy, setBusy] = React.useState(false)
  const [target, setTarget] = React.useState<Record<string, string>>({})

  const load = React.useCallback(() => {
    studioAPI.schedule(courseId).then(setData).catch((e) => setError(e?.response?.data?.detail || 'Could not load the schedule'))
  }, [courseId])
  React.useEffect(() => { load() }, [load])

  const clone = async (from: string) => {
    const to = target[from] || addDays(from, 7)
    setBusy(true)
    try {
      const r = await studioAPI.cloneWeek(courseId, from, to)
      setData(r.schedule)
      toast.success(`Copied ${r.created.length} class${r.created.length === 1 ? '' : 'es'} to the week of ${to}`)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Clone failed')
    } finally { setBusy(false) }
  }

  if (error) return <p className="text-sm text-red-600" role="alert">{error}</p>
  if (!data) return <p className="text-sm text-gray-500">Loading schedule…</p>

  return (
    <div className="space-y-3" data-testid="schedule-builder">
      <div className="grid grid-cols-3 gap-2 text-sm">
        {[['Live classes', data.live_classes], ['Recorded lessons', data.recorded_lessons], ['Assessments', data.assessments]].map(([k, v]) => (
          <div key={String(k)} className="rounded-lg bg-white border border-gray-200 p-2.5"><p className="text-[11px] text-gray-500">{k}</p><p className="font-semibold text-gray-900">{v}</p></div>
        ))}
      </div>
      {data.weeks.length === 0 && (
        <p className="text-sm text-gray-600">No live classes scheduled yet. <Link to={`/instructor/live-classes/new?course_id=${courseId}`} className="text-blue-600 underline">Schedule the first class</Link>, then clone the week across the term.</p>
      )}
      {data.weeks.map((w) => (
        <div key={w.week_start} className="rounded-lg border border-gray-200 bg-white p-3">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <p className="text-sm font-semibold text-gray-900">Week of {w.week_start}{w.week_start === mondayOf(new Date()) ? ' · this week' : ''}</p>
            <div className="ml-auto flex items-center gap-1 text-xs">
              <span className="text-gray-500">copy to week of</span>
              <input type="date" value={target[w.week_start] || addDays(w.week_start, 7)} onChange={(e) => setTarget((t) => ({ ...t, [w.week_start]: e.target.value }))} className="border border-gray-300 rounded px-1.5 py-1" />
              <button type="button" disabled={busy} onClick={() => clone(w.week_start)} className="px-2 py-1 rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-40">Clone week</button>
            </div>
          </div>
          <ul className="text-sm divide-y divide-gray-100">
            {w.sessions.map((s) => (
              <li key={s.class_id} className="py-1.5 flex flex-wrap items-center gap-2">
                <span className="text-gray-500 w-32">{fmtTime(s.start)}</span>
                <span className="text-gray-900 flex-1">{s.title}</span>
                {s.purpose && <span className="text-[11px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">{s.purpose.replace('_', ' ')}</span>}
                <span className={`text-[11px] px-1.5 py-0.5 rounded ${s.status === 'ended' ? 'bg-emerald-50 text-emerald-700' : s.status === 'live' ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700'}`}>{s.status || 'scheduled'}</span>
                {s.has_recording && <span className="text-[11px] text-gray-500">recording</span>}
              </li>
            ))}
          </ul>
        </div>
      ))}
      <Link to={`/instructor/live-classes/new?course_id=${courseId}`} className="inline-block text-sm text-blue-600 hover:underline">+ Schedule another live class</Link>
    </div>
  )
}

export default ScheduleBuilder
