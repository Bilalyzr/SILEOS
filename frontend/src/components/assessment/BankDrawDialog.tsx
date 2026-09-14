/**
 * BankDrawDialog (roadmap item 5): draw N random questions from one of the
 * instructor's question banks into the quiz being edited, optionally with a
 * difficulty mix. Reviewed questions only — AI drafts stay in the queue.
 */
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '@/api/axios'
import { GlassDialog } from '@/components/ui/dialog'

interface Bank { id: number; title: string; question_count?: number }

export function BankDrawDialog({ quizId, onDone }: { quizId: number; onDone?: () => void }) {
  const [open, setOpen] = useState(false)
  const [banks, setBanks] = useState<Bank[]>([])
  const [bankId, setBankId] = useState<number | ''>('')
  const [count, setCount] = useState(10)
  const [mix, setMix] = useState({ easy: 0, medium: 0, hard: 0 })
  const [busy, setBusy] = useState(false)
  useEffect(() => { if (open && banks.length === 0) api.get('/question-banks').then((r) => setBanks(r.data.banks || [])).catch(() => {}) }, [open, banks.length])

  const run = async () => {
    if (!bankId) return
    setBusy(true)
    try {
      const body: any = { count }
      if (mix.easy || mix.medium || mix.hard) body.difficulty_mix = mix
      const r = await api.post(`/question-banks/${bankId}/push-to-quiz/${quizId}`, body)
      toast.success(`${r.data.added} questions added (easy ${r.data.by_difficulty.easy}, medium ${r.data.by_difficulty.medium}, hard ${r.data.by_difficulty.hard})`)
      setOpen(false); onDone?.()
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Could not draw from the bank') }
    finally { setBusy(false) }
  }

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className="px-3 py-1.5 text-sm rounded-lg border border-violet-300 text-violet-700 hover:bg-violet-50" data-testid="bank-draw-btn">🎲 Add from bank</button>
      <GlassDialog open={open} onOpenChange={setOpen} size="sm" eyebrow="Question banks" title="Draw questions into this quiz"
        description="A random draw of reviewed questions. Set 'questions per attempt' in Settings and every learner gets a different subset."
        actions={<><button type="button" className="si-btn-secondary" onClick={() => setOpen(false)}>Cancel</button><button type="button" className="si-btn-primary" disabled={busy || !bankId} onClick={run}>{busy ? 'Drawing…' : 'Draw'}</button></>}>
        <div className="space-y-3 text-sm">
          <label className="block"><span className="block text-xs font-medium text-gray-600 mb-1">Bank</span>
            <select value={bankId} onChange={(e) => setBankId(e.target.value ? Number(e.target.value) : '')} className="si-input w-full">
              <option value="">Choose a bank…</option>
              {banks.map((b) => <option key={b.id} value={b.id}>{b.title}{b.question_count != null ? ` (${b.question_count})` : ''}</option>)}
            </select></label>
          <label className="block"><span className="block text-xs font-medium text-gray-600 mb-1">How many</span>
            <input type="number" min={1} max={200} value={count} onChange={(e) => setCount(Math.max(1, Number(e.target.value) || 1))} className="si-input w-28" /></label>
          <div><span className="block text-xs font-medium text-gray-600 mb-1">Difficulty mix (optional, the rest is filled randomly)</span>
            <div className="flex gap-2">
              {(['easy', 'medium', 'hard'] as const).map((k) => (
                <label key={k} className="text-xs text-gray-600">{k}<input type="number" min={0} value={mix[k]} onChange={(e) => setMix({ ...mix, [k]: Math.max(0, Number(e.target.value) || 0) })} className="si-input w-full mt-0.5" /></label>
              ))}
            </div></div>
          {bankId && (
            <button type="button" className="text-xs text-blue-600 hover:underline"
              onClick={async () => {
                try {
                  const r = await api.get(`/question-banks/${bankId}/export.csv`, { responseType: 'blob' })
                  window.open(URL.createObjectURL(r.data as Blob), '_blank')
                } catch { toast.error('Export failed') }
              }}>Export this bank as CSV</button>
          )}
        </div>
      </GlassDialog>
    </>
  )
}

export default BankDrawDialog
