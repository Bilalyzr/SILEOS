/**
 * EarningsPanel (roadmap item 4): per-course money view for instructors —
 * paid orders, gross, refunds, net, refund rate, enrolments and the funnel
 * rates — plus a one-click PDF report to forward to a school.
 */
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '@/api/axios'

interface Row { course_id: number; title: string; orders: number; gross: number; refunds: number; net: number; refund_rate: number; enrolments: number; views: number; preview_opens: number }
interface Data { days: number; courses: Row[]; totals: { orders: number; gross: number; refunds: number; net: number; enrolments: number } }

const inr = (v: number) => `₹${Math.round(v).toLocaleString('en-IN')}`

export function EarningsPanel() {
  const [days, setDays] = useState(30)
  const [data, setData] = useState<Data | null>(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => { setData(null); api.get('/funnel/instructor/earnings', { params: { days } }).then((r) => setData(r.data)).catch(() => setData({ days, courses: [], totals: { orders: 0, gross: 0, refunds: 0, net: 0, enrolments: 0 } })) }, [days])

  const downloadPdf = async () => {
    setBusy(true)
    try {
      const r = await api.get('/funnel/instructor/report.pdf', { params: { days }, responseType: 'blob' })
      const url = URL.createObjectURL(r.data as Blob)
      window.open(url, '_blank')
    } catch { toast.error('Could not build the report') }
    finally { setBusy(false) }
  }

  return (
    <div className="space-y-3" data-testid="earnings-panel">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="font-semibold text-gray-900 flex-1">Earnings</h2>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="si-input !py-1 text-xs" aria-label="Window">
          {[7, 30, 90, 365].map((d) => <option key={d} value={d}>last {d} days</option>)}
        </select>
        <button type="button" disabled={busy} onClick={downloadPdf} className="si-btn-primary !py-1.5 !text-xs">{busy ? 'Building…' : 'Download PDF report'}</button>
      </div>
      {!data ? <p className="text-sm text-gray-500">Adding up…</p> : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {([['Net', inr(data.totals.net)], ['Gross', inr(data.totals.gross)], ['Refunds', inr(data.totals.refunds)], ['Paid orders', data.totals.orders], ['Enrolments', data.totals.enrolments]] as [string, string | number][]).map(([k, v]) => (
              <div key={k} className="glass-panel rounded-xl p-3"><p className="text-[11px] text-gray-500">{k}</p><p className={`text-lg font-semibold ${k === 'Net' ? 'text-emerald-700' : 'text-gray-900'}`}>{v}</p></div>
            ))}
          </div>
          {data.courses.length === 0 ? <p className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-xl p-4">No paid orders or visits in this window.</p> : (
            <div className="overflow-x-auto glass-panel rounded-xl">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-gray-500"><tr>
                  <th className="px-3 py-2">Course</th><th className="px-3 py-2">Visits</th><th className="px-3 py-2">Previews</th><th className="px-3 py-2">Enrolled</th><th className="px-3 py-2">Orders</th><th className="px-3 py-2">Gross</th><th className="px-3 py-2">Refunds</th><th className="px-3 py-2">Net</th>
                </tr></thead>
                <tbody>
                  {data.courses.map((r) => (
                    <tr key={r.course_id} className="border-t border-white/70">
                      <td className="px-3 py-2 font-medium text-gray-900">{r.title}</td><td className="px-3 py-2">{r.views}</td><td className="px-3 py-2">{r.preview_opens}</td><td className="px-3 py-2">{r.enrolments}</td>
                      <td className="px-3 py-2">{r.orders}</td><td className="px-3 py-2">{inr(r.gross)}</td><td className={`px-3 py-2 ${r.refund_rate >= 20 ? 'text-red-700' : ''}`}>{inr(r.refunds)}{r.refunds > 0 ? ` (${r.refund_rate}%)` : ''}</td><td className="px-3 py-2 font-semibold text-emerald-700">{inr(r.net)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default EarningsPanel
