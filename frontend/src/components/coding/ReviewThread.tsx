import { useEffect, useMemo, useState } from 'react'
import { codingReviewAPI, type ReviewComment } from '@/api/codingReview'
import { plannerError } from '@/api/planner'

interface ReviewThreadProps {
  submissionId: number
  source: string
  /** Course editors can resolve comments. */
  isEditor?: boolean
}

/**
 * Submitted code with line-anchored comments. Anyone who can see the
 * submission (its owner or course staff) can comment on a line.
 */
export function ReviewThread({ submissionId, source, isEditor = false }: ReviewThreadProps) {
  const [comments, setComments] = useState<ReviewComment[]>([])
  const [line, setLine] = useState(1)
  const [body, setBody] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const lines = useMemo(() => source.split('\n'), [source])

  useEffect(() => {
    let active = true
    codingReviewAPI.comments(submissionId)
      .then((rows) => active && setComments(rows))
      .catch((reason) => active && setError(plannerError(reason)))
    return () => { active = false }
  }, [submissionId])

  const byLine = useMemo(() => {
    const map = new Map<number, ReviewComment[]>()
    for (const comment of comments) map.set(comment.line, [...(map.get(comment.line) || []), comment])
    return map
  }, [comments])

  const add = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!body.trim()) return
    setBusy(true)
    setError('')
    try {
      const created = await codingReviewAPI.addComment(submissionId, line, body.trim())
      setComments((current) => [...current, created])
      setBody('')
    } catch (reason) {
      setError(plannerError(reason))
    } finally {
      setBusy(false)
    }
  }

  const resolve = async (comment: ReviewComment) => {
    try {
      const updated = await codingReviewAPI.resolve(comment.id)
      setComments((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (reason) {
      setError(plannerError(reason))
    }
  }

  return (
    <div className="space-y-3 text-sm text-slate-100">
      {error && <p role="alert" className="rounded-lg bg-red-950/60 p-2 text-red-200">{error}</p>}
      <div className="overflow-x-auto rounded-xl border border-white/10 bg-[#0d111a] font-mono text-xs leading-6">
        {lines.map((text, index) => {
          const number = index + 1
          const threads = byLine.get(number) || []
          return (
            <div key={number}>
              <button
                type="button"
                onClick={() => setLine(number)}
                className={`flex w-full gap-3 px-3 text-left hover:bg-white/5 ${line === number ? 'bg-violet-500/10' : ''}`}
                aria-label={`Comment on line ${number}`}
              >
                <span className="w-8 select-none text-right text-slate-500">{number}</span>
                <span className="whitespace-pre">{text || ' '}</span>
              </button>
              {threads.map((comment) => (
                <div key={comment.id} className={`ml-11 mr-3 mb-1 rounded-lg border px-3 py-2 font-sans text-xs ${comment.status === 'resolved' ? 'border-white/10 text-slate-400' : 'border-violet-400/40 bg-violet-500/10 text-slate-100'}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold">{comment.author_name || 'Member'}{comment.author_is_staff ? ' · staff' : ''}</span>
                    {comment.status === 'open' && isEditor && (
                      <button type="button" onClick={() => void resolve(comment)} className="text-violet-200 underline">Resolve</button>
                    )}
                    {comment.status === 'resolved' && <span className="text-slate-400">Resolved</span>}
                  </div>
                  <p className="mt-1 whitespace-pre-wrap">{comment.body}</p>
                </div>
              ))}
            </div>
          )
        })}
      </div>

      <form onSubmit={(event) => void add(event)} className="flex flex-col gap-2 sm:flex-row sm:items-start">
        <label className="text-xs text-slate-300">Line
          <input type="number" min={1} max={lines.length} value={line} onChange={(event) => setLine(Number(event.target.value))} className="mt-1 w-20 rounded-lg border border-white/10 bg-[#0d111a] px-2 py-1.5 text-slate-100" />
        </label>
        <textarea aria-label="Comment" rows={2} maxLength={2000} value={body} onChange={(event) => setBody(event.target.value)} placeholder="Comment on this line" className="flex-1 rounded-lg border border-white/10 bg-[#0d111a] px-3 py-2 text-slate-100" />
        <button type="submit" disabled={busy || !body.trim()} className="rounded-lg bg-violet-600 px-4 py-2 font-semibold text-white disabled:opacity-50">Add comment</button>
      </form>
    </div>
  )
}

export default ReviewThread
