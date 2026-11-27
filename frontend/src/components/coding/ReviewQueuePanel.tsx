import { useCallback, useEffect, useState } from 'react'
import { codingAPI, type CodingSubmission } from '@/api/coding'
import { codingReviewAPI, type ReviewQueue, type ReviewQueueItem } from '@/api/codingReview'
import { plannerError } from '@/api/planner'
import { ReviewThread } from './ReviewThread'

/** Instructor queue of learner review requests, with line comments and a done action. */
export default function ReviewQueuePanel({ courseId }: { courseId: number }) {
  const [queue, setQueue] = useState<ReviewQueue | null>(null)
  const [selected, setSelected] = useState<{ item: ReviewQueueItem; submission: CodingSubmission } | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    if (!courseId) return
    try {
      setQueue(await codingReviewAPI.queue(courseId))
      setError('')
    } catch (reason) {
      setError(plannerError(reason))
    }
  }, [courseId])

  useEffect(() => {
    setQueue(null)
    setSelected(null)
    void load()
  }, [load])

  const open = async (item: ReviewQueueItem) => {
    setBusy(true)
    setError('')
    try {
      const submission = await codingAPI.submission(item.submission_id)
      setSelected({ item, submission })
    } catch (reason) {
      setError(plannerError(reason))
    } finally {
      setBusy(false)
    }
  }

  const done = async () => {
    if (!selected) return
    setBusy(true)
    setError('')
    try {
      await codingReviewAPI.markReviewed(selected.item.submission_id)
      setSelected(null)
      await load()
    } catch (reason) {
      setError(plannerError(reason))
    } finally {
      setBusy(false)
    }
  }

  if (!courseId) return null

  return (
    <section className="glass-panel mt-5 rounded-2xl p-5 sm:p-7" aria-labelledby="review-queue-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="review-queue-heading" className="text-xl font-semibold text-slate-950">Review queue</h2>
          <p className="mt-1 text-sm text-slate-500">Learners who asked for feedback on a finished submission.</p>
        </div>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">{queue?.count ?? 0} waiting</span>
      </div>

      {error && <div role="alert" className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {queue && queue.items.length === 0 && <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Nothing waiting for review.</p>}

      {queue && queue.items.length > 0 && (
        <ul className="mt-4 divide-y divide-slate-100 text-sm">
          {queue.items.map((item) => (
            <li key={item.submission_id} className="flex flex-wrap items-center justify-between gap-2 py-3">
              <div>
                <span className="font-medium text-slate-900">{item.learner_name}</span>
                <span className="ml-2 text-slate-600">{item.challenge_title} · {item.language} · {item.status} · {item.score.toFixed(1)}%</span>
                {item.open_comments > 0 && <span className="ml-2 text-xs text-violet-700">{item.open_comments} open comment{item.open_comments === 1 ? '' : 's'}</span>}
              </div>
              <button type="button" disabled={busy} onClick={() => void open(item)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 disabled:opacity-50">Open review</button>
            </li>
          ))}
        </ul>
      )}

      {selected && (
        <div className="mt-6 rounded-2xl bg-[#080b12] p-4 text-slate-100">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold">{selected.item.learner_name} · {selected.item.challenge_title}</h3>
            <button type="button" disabled={busy} onClick={() => void done()} className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">Mark review done</button>
          </div>
          <ReviewThread submissionId={selected.submission.id} source={selected.submission.source_code} isEditor />
        </div>
      )}
    </section>
  )
}
