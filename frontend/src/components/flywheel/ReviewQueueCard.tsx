/**
 * ReviewQueueCard (roadmap R2): the instructor dashboard's "today" card —
 * what is waiting in the review queue, with one click to go handle it.
 * Zero-state says so plainly instead of hiding.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Inbox } from 'lucide-react'
import { api } from '@/api/axios'

interface Counts { escalations: number; error_reports: number; ai_drafts: number; total: number }

export function ReviewQueueCard() {
  const [c, setC] = useState<Counts | null>(null)
  useEffect(() => { api.get('/ai/review-queue/counts').then((r) => setC(r.data)).catch(() => setC({ escalations: 0, error_reports: 0, ai_drafts: 0, total: 0 })) }, [])
  const items = c ? [
    { n: c.escalations, label: 'learner question' },
    { n: c.error_reports, label: 'error report' },
    { n: c.ai_drafts, label: 'AI draft to review' },
  ].filter((i) => i.n > 0) : []
  return (
    <div className="glass-panel rounded-2xl p-5 mb-6 flex items-center gap-4 flex-wrap" data-testid="review-queue-card">
      <div className={`h-11 w-11 rounded-xl grid place-items-center ${c && c.total > 0 ? 'si-gradient text-white' : 'bg-emerald-100 text-emerald-700'}`}><Inbox className="h-5 w-5" /></div>
      <div className="flex-1 min-w-[14rem]">
        <p className="text-[11px] uppercase tracking-wide text-orange-700 font-semibold">Today's review queue</p>
        {!c ? <p className="text-sm text-gray-500">Checking…</p> : c.total === 0 ? (
          <p className="text-sm text-gray-700">Nothing waiting — learner questions, error reports and AI drafts land here.</p>
        ) : (
          <p className="text-sm text-gray-900 font-medium">{items.map((i) => `${i.n} ${i.label}${i.n === 1 ? '' : 's'}`).join(' · ')}</p>
        )}
      </div>
      <Link to="/instructor/review-queue" className={c && c.total > 0 ? 'si-btn-primary' : 'si-btn-secondary'}>Open review queue</Link>
    </div>
  )
}

export default ReviewQueueCard
