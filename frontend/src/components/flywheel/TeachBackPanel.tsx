/**
 * TeachBackPanel (v2.0 §10 peer "teach it back" v1 — WP8): under a concept on
 * My Mastery. Read peers' explanations, vote helpful / not, write your own
 * (40–1500 chars → +XP and a small mastery signal). Never graded truth.
 */
import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { flywheelAPI, type TeachBack } from '@/api/flywheel'

export function TeachBackPanel({ concept, courseId }: { concept: string; courseId?: number | null }) {
  const [rows, setRows] = useState<TeachBack[] | null>(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [writing, setWriting] = useState(false)

  const load = useCallback(() => {
    flywheelAPI.teachBacks({ concept }).then(setRows).catch(() => setRows([]))
  }, [concept])
  useEffect(() => { load() }, [load])

  const vote = async (id: number, helpful: boolean) => {
    try { await flywheelAPI.rate(id, helpful); load() }
    catch (e: any) { toast.error(e?.response?.data?.detail || 'Could not vote') }
  }
  const submit = async () => {
    setBusy(true)
    try {
      await flywheelAPI.writeTeachBack({ concept, text: text.trim(), course_id: courseId || undefined })
      toast.success('Explanation shared (+15 XP)'); setText(''); setWriting(false); load()
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Could not share') }
    finally { setBusy(false) }
  }

  return (
    <div className="mt-2 rounded-lg border border-emerald-100 bg-emerald-50/40 p-2" data-testid="teach-back">
      <div className="flex items-center gap-2">
        <p className="text-xs font-semibold text-emerald-900 flex-1">Teach it back{rows && rows.length > 0 ? ` · ${rows.length} peer explanation${rows.length === 1 ? '' : 's'}` : ''}</p>
        <button type="button" onClick={() => setWriting((v) => !v)} className="text-[11px] text-emerald-800 underline">{writing ? 'Cancel' : 'Explain it in your words'}</button>
      </div>
      {writing && (
        <div className="mt-1">
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} maxLength={1500} placeholder={`How would you explain "${concept}" to a classmate? (40–1500 characters)`} className="w-full px-2 py-1.5 border border-gray-300 rounded text-xs" />
          <div className="flex items-center gap-2 mt-1"><span className="text-[10px] text-gray-400 flex-1">{text.trim().length}/1500</span>
            <button type="button" disabled={busy || text.trim().length < 40} onClick={submit} className="px-2 py-1 text-[11px] rounded bg-emerald-600 text-white disabled:opacity-40">Share</button></div>
        </div>
      )}
      {rows === null ? <p className="text-[11px] text-gray-500 mt-1">Loading…</p> : rows.length === 0 ? (
        !writing && <p className="text-[11px] text-gray-500 mt-1">No peer explanations yet — be the first.</p>
      ) : (
        <ul className="mt-1 space-y-1">
          {rows.map((r) => (
            <li key={r.id} className="rounded bg-white border border-gray-100 p-2 text-xs text-gray-800">
              <p className="whitespace-pre-wrap">{r.text}</p>
              <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-500">
                <span className="flex-1">{r.author || 'a learner'}</span>
                <button type="button" onClick={() => vote(r.id, true)} className={`px-1.5 py-0.5 rounded border ${r.my_vote === true ? 'bg-emerald-600 text-white border-emerald-600' : 'border-gray-300 hover:bg-gray-50'}`}>helpful · {r.helpful_count}</button>
                <button type="button" onClick={() => vote(r.id, false)} className={`px-1.5 py-0.5 rounded border ${r.my_vote === false ? 'bg-gray-700 text-white border-gray-700' : 'border-gray-300 hover:bg-gray-50'}`}>not really · {r.not_helpful_count}</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default TeachBackPanel
