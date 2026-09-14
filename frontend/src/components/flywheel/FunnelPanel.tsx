/**
 * FunnelPanel (roadmap R1): preview → checkout → enrolment per course, all
 * derived server-side. One row per course with the four rates and the
 * preview lessons that pull people in.
 */
import { useEffect, useState } from 'react'
import { funnelAPI, type FunnelSummary } from '@/api/funnel'

const pct = (v: number | null) => (v == null ? '—' : `${v}%`)

export function FunnelPanel() {
  const [days, setDays] = useState(30)
  const [rows, setRows] = useState<FunnelSummary[] | null>(null)
  useEffect(() => { setRows(null); funnelAPI.overview(days).then(setRows).catch(() => setRows([])) }, [days])
  return (
    <div className="space-y-3" data-testid="funnel-panel">
      <div className="flex items-center gap-2">
        <h2 className="font-semibold text-gray-900 flex-1">Preview → enrol funnel</h2>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="si-input !py-1 text-xs" aria-label="Window">
          {[7, 30, 90].map((d) => <option key={d} value={d}>last {d} days</option>)}
        </select>
      </div>
      {!rows ? <p className="text-sm text-gray-500">Counting…</p> : rows.length === 0 ? (
        <p className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-xl p-4">No visits yet in this window. Share a course page — every visit, free-preview open and checkout start lands here.</p>
      ) : (
        <div className="overflow-x-auto glass-panel rounded-xl">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-gray-500"><tr>
              <th className="px-3 py-2">Course</th><th className="px-3 py-2">Visits</th><th className="px-3 py-2">Previews</th><th className="px-3 py-2">Checkouts</th><th className="px-3 py-2">Enrolled</th>
              <th className="px-3 py-2">Visit→preview</th><th className="px-3 py-2">Preview→checkout</th><th className="px-3 py-2">Checkout→enrol</th><th className="px-3 py-2">Visit→enrol</th>
            </tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.course_id} className="border-t border-white/70">
                  <td className="px-3 py-2 font-medium text-gray-900">{r.title}{r.top_preview_lessons.length > 0 && <span className="block text-[11px] text-gray-500">top preview: lesson #{r.top_preview_lessons[0].lesson_id} ({r.top_preview_lessons[0].opens} opens)</span>}</td>
                  <td className="px-3 py-2">{r.views}</td><td className="px-3 py-2">{r.preview_opens}</td><td className="px-3 py-2">{r.checkout_starts}</td><td className="px-3 py-2 font-semibold text-emerald-700">{r.enrolments}</td>
                  <td className="px-3 py-2">{pct(r.rates.view_to_preview)}</td><td className="px-3 py-2">{pct(r.rates.preview_to_checkout)}</td><td className="px-3 py-2">{pct(r.rates.checkout_to_enrol)}</td><td className="px-3 py-2 font-semibold">{pct(r.rates.view_to_enrol)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-[11px] text-gray-500">Learners who start a checkout and do not finish get one reminder after 24 hours (in-app, email when configured).</p>
    </div>
  )
}

export default FunnelPanel
