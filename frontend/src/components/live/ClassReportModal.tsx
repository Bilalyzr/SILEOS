/**
 * ClassReportModal — the permanent past-class report (v2.0 §7.3): attendance
 * with join/leave/duration, engagement, poll results, event log, instructor
 * notes (editable), transcript + key topics when Engine A has run, recording
 * retention state with one-click extend / restore, PDF export and "share with
 * guardians" for SP courses. Data from GET /live/classes/{id}/report.
 */
import * as React from 'react'
import toast from 'react-hot-toast'
import { api } from '@/api/axios'
import { aiLayerAPI } from '@/api/aiLayer'
import { useConfirm } from '@/components/ui/confirm'

interface Report {
  class_id: number
  title: string
  purpose: string | null
  mode: string | null
  audience: string | null
  recording_policy: string | null
  lifecycle: string
  started_at: string | null
  ended_at: string | null
  duration_s: number
  attendance: { user_id: number; name: string; joined_at: string | null; left_at: string | null; duration_s: number; present: boolean }[]
  event_log: { t: string | null; user_id: number | null; event: string; payload: unknown }[]
  poll_results: { question: string; options: string[]; tallies: number[]; total: number }[]
  engagement: { enrolled?: number; joined?: number; present?: number; present_pct?: number | null; avg_duration_s?: number; poll_votes?: number }
  instructor_notes: string
  transcript: string | null
  ai_topics: unknown[] | null
  processing_status: string
  shared_with_guardians: boolean
  recording: { exists: boolean; retention_until: string | null; deleted_at: string | null; restorable_until: string | null; days_left: number | null }
}

const hhmm = (iso: string | null) => (iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—')

export const ClassReportModal: React.FC<{ classId: number; onClose: () => void; onChanged?: () => void }> = ({ classId, onClose, onChanged }) => {
  const [report, setReport] = React.useState<Report | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [notes, setNotes] = React.useState('')
  const [busy, setBusy] = React.useState(false)
  const confirm = useConfirm()
  const [transcript, setTranscript] = React.useState('')
  const [showPaste, setShowPaste] = React.useState(false)

  const load = React.useCallback(async () => {
    try {
      const r = await api.get(`/live/classes/${classId}/report`)
      setReport(r.data)
      setNotes(r.data.instructor_notes || '')
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not load the report')
    }
  }, [classId])
  React.useEffect(() => { load() }, [load])

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true)
    try { await fn(); toast.success(ok); await load(); onChanged?.() }
    catch (err: any) { toast.error(err?.response?.data?.detail || 'Action failed') }
    finally { setBusy(false) }
  }
  const downloadPdf = async () => {
    try {
      const r = await api.get(`/live/classes/${classId}/report.pdf`, { responseType: 'blob' })
      const url = URL.createObjectURL(r.data as Blob)
      window.open(url, '_blank')
    } catch { toast.error('Could not export the PDF') }
  }

  return (
    <div className="fixed inset-0 z-modal bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[92vh] overflow-y-auto p-5 space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-900">{report?.title || 'Class report'}</h2>
            {report && (
              <p className="text-xs text-gray-500">
                {report.purpose || 'class'} · {report.mode || '—'} · {report.audience || '—'} · {hhmm(report.started_at)}–{hhmm(report.ended_at)} · {Math.round(report.duration_s / 60)} min ·
                <span className="ml-1 px-1.5 py-0.5 rounded bg-gray-100 text-gray-700">{report.lifecycle}</span>
              </p>
            )}
          </div>
          <button type="button" onClick={downloadPdf} className="px-3 py-1.5 text-xs rounded-lg border border-gray-300 hover:bg-gray-50">Export PDF</button>
          <button type="button" onClick={onClose} className="text-sm text-gray-500 hover:text-gray-900">Close</button>
        </div>

        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        {!report && !error && <p className="text-sm text-gray-500">Loading…</p>}

        {report && (
          <>
            <div className="grid sm:grid-cols-4 gap-2 text-sm">
              {[['Enrolled', report.engagement.enrolled ?? 0], ['Joined', report.engagement.joined ?? 0],
                ['Present', `${report.engagement.present ?? 0}${report.engagement.present_pct != null ? ` (${report.engagement.present_pct}%)` : ''}`],
                ['Avg. minutes', Math.round((report.engagement.avg_duration_s || 0) / 60)]].map(([k, v]) => (
                <div key={String(k)} className="rounded-lg bg-gray-50 p-3"><p className="text-xs text-gray-500">{k}</p><p className="font-semibold text-gray-900">{v as any}</p></div>
              ))}
            </div>

            <div className="rounded-xl border border-gray-200 p-3">
              <p className="text-sm font-semibold text-gray-900 mb-1">Recording</p>
              {report.recording.exists ? (
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${(report.recording.days_left ?? 99) <= 14 ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}`}>
                    kept until {report.recording.retention_until ? new Date(report.recording.retention_until).toLocaleDateString() : '—'}{report.recording.days_left != null ? ` · ${report.recording.days_left} days left` : ''}
                  </span>
                  <button type="button" disabled={busy} onClick={() => act(() => api.post(`/live/classes/${classId}/recording/extend`, { days: 30 }), 'Retention extended by 30 days')} className="px-2 py-1 text-xs rounded border border-gray-300 hover:bg-gray-50">Extend 30 days</button>
                  <button type="button" disabled={busy} onClick={async () => { const reason = await confirm.prompt({ eyebrow: 'Recording', title: 'Delete this recording?', body: 'The class report, attendance and transcript stay. The video can be restored for 30 days.', placeholder: 'Reason (optional)', confirmLabel: 'Delete recording', danger: true }); if (reason === null) return; act(() => api.delete(`/live/classes/${classId}/recording`, { params: { reason } }), 'Recording deleted — restorable for 30 days') }} className="px-2 py-1 text-xs rounded border border-red-200 text-red-600 hover:bg-red-50">Delete recording</button>
                </div>
              ) : report.recording.deleted_at ? (
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">deleted {new Date(report.recording.deleted_at).toLocaleDateString()}{report.recording.restorable_until ? ` · restorable until ${new Date(report.recording.restorable_until).toLocaleDateString()}` : ''}</span>
                  {report.lifecycle === 'deleted' && report.recording.restorable_until && (
                    <button type="button" disabled={busy} onClick={() => act(() => api.post(`/live/classes/${classId}/recording/restore`), 'Recording restored')} className="px-2 py-1 text-xs rounded border border-gray-300 hover:bg-gray-50">Restore</button>
                  )}
                </div>
              ) : <p className="text-xs text-gray-500">No recording. The report, attendance and transcript are kept regardless.</p>}
            </div>

            <div className="rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-left text-xs text-gray-500"><tr><th className="px-3 py-2">Learner</th><th className="px-3 py-2">Joined</th><th className="px-3 py-2">Left</th><th className="px-3 py-2">Minutes</th><th className="px-3 py-2">Present</th></tr></thead>
                <tbody>
                  {report.attendance.length === 0 && <tr><td colSpan={5} className="px-3 py-2 text-gray-500">Nobody joined.</td></tr>}
                  {report.attendance.map((a) => (
                    <tr key={a.user_id} className="border-t border-gray-100"><td className="px-3 py-1.5">{a.name}</td><td className="px-3 py-1.5">{hhmm(a.joined_at)}</td><td className="px-3 py-1.5">{hhmm(a.left_at)}</td><td className="px-3 py-1.5">{Math.round(a.duration_s / 60)}</td><td className="px-3 py-1.5">{a.present ? <span className="text-emerald-700">yes</span> : <span className="text-gray-400">no</span>}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>

            {report.poll_results.length > 0 && (
              <div className="rounded-xl border border-gray-200 p-3 text-sm">
                <p className="font-semibold text-gray-900 mb-1">Polls</p>
                {report.poll_results.map((p, i) => (
                  <div key={i} className="mb-2"><p className="text-gray-800">{p.question}</p>
                    <ul className="text-xs text-gray-600 pl-4 list-disc">{p.options.map((o, j) => <li key={j}>{o}: {p.tallies[j] ?? 0}</li>)}</ul></div>
                ))}
              </div>
            )}

            <div className="rounded-xl border border-gray-200 p-3">
              <p className="text-sm font-semibold text-gray-900 mb-1">Instructor notes</p>
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              <div className="flex flex-wrap items-center gap-2 mt-2">
                <button type="button" disabled={busy} onClick={() => act(() => api.put(`/live/classes/${classId}/report/notes`, { instructor_notes: notes }), 'Notes saved')} className="px-3 py-1.5 text-xs rounded-lg bg-gray-900 text-white hover:bg-black">Save notes</button>
                <label className="inline-flex items-center gap-2 text-xs text-gray-700 ml-auto">
                  <input type="checkbox" checked={report.shared_with_guardians} onChange={(e) => act(() => api.post(`/live/classes/${classId}/report/share-guardians`, { shared: e.target.checked }), e.target.checked ? 'Shared with guardians' : 'Hidden from guardians')} />
                  Share with guardians (SP)
                </label>
              </div>
            </div>

            {/* Engine A (WP7): paste a transcript → stored forever, segmented when the LLM is configured */}
            {!report.transcript && (
              <div className="rounded-xl border border-dashed border-gray-300 p-3 text-sm" data-testid="transcript-paste">
                <div className="flex items-center gap-2"><p className="font-semibold text-gray-900 flex-1">Transcript</p>
                  <button type="button" onClick={() => setShowPaste((v) => !v)} className="text-xs text-blue-600 hover:underline">{showPaste ? 'Cancel' : 'Paste transcript'}</button></div>
                {showPaste && (<>
                  <textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} rows={5} placeholder="Paste the auto-captions export or your own transcript…" className="w-full mt-2 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                  <button type="button" disabled={busy || transcript.trim().length < 20} onClick={() => act(async () => { const r = await aiLayerAPI.pasteTranscript(classId, transcript.trim()); if (r.note) toast(r.note) }, 'Transcript saved')} className="mt-2 px-3 py-1.5 text-xs rounded-lg bg-gray-900 text-white disabled:opacity-40">Save transcript</button>
                </>)}
                {!showPaste && <p className="text-xs text-gray-500 mt-1">No transcript yet. The transcription worker posts one automatically when configured; you can also paste one.</p>}
              </div>
            )}
            {(report.transcript || report.ai_topics) && (
              <div className="rounded-xl border border-gray-200 p-3 text-sm">
                <p className="font-semibold text-gray-900 mb-1">Transcript & key topics <span className="text-[10px] font-normal px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">{report.processing_status}</span></p>
                {report.processing_status === 'transcribed' && <p className="text-[11px] text-amber-700 mb-1">Topics pending — GLM_API_KEY is not set on the server.</p>}
                {report.ai_topics && <ul className="text-xs text-gray-700 list-disc pl-4 mb-2">{(report.ai_topics as any[]).map((t, i) => <li key={i}>{typeof t === 'string' ? t : t?.topic}</li>)}</ul>}
                {report.transcript && <pre className="text-xs text-gray-600 whitespace-pre-wrap max-h-48 overflow-y-auto">{report.transcript}</pre>}
              </div>
            )}

            {report.event_log.length > 0 && (
              <details className="text-xs text-gray-600"><summary className="cursor-pointer">Event log ({report.event_log.length})</summary>
                <ul className="mt-1 space-y-0.5 max-h-40 overflow-y-auto">{report.event_log.map((e, i) => <li key={i}>{hhmm(e.t)} · {e.event}{e.user_id ? ` · #${e.user_id}` : ''}</li>)}</ul>
              </details>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default ClassReportModal
