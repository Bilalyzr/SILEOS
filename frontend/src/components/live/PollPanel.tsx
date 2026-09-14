import * as React from 'react'
import { Plus, X, Radio, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  listPolls, createPoll, activatePoll, closePoll, votePoll,
  type PollOut,
} from '@/api/liveClasses'

const POLL_POLL_INTERVAL_MS = 10_000

export interface PollPanelProps {
  classId: number
  /** Instructor console passes true — shows the create form + activate/close
   * controls. Student view (not built in this task) would pass false. */
  isModerator?: boolean
  className?: string
}

function optionTally(poll: PollOut, index: number): { count: number; pct: number } {
  const tallies = poll.tallies || []
  const count = tallies[index] || 0
  const total = tallies.reduce((sum, n) => sum + n, 0)
  const pct = total > 0 ? Math.round((count / total) * 100) : 0
  return { count, pct }
}

/**
 * Instructor-facing poll dock panel: create a poll (draft), activate/close
 * it, and watch live result bars. Results refresh via a 10s poll of the
 * polls list — see liveClasses.ts's note on why SSE (pollStreamUrl) can't
 * carry the bearer token in a browser EventSource.
 */
export const PollPanel: React.FC<PollPanelProps> = ({ classId, isModerator = true, className = '' }) => {
  const [polls, setPolls] = React.useState<PollOut[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [showCreate, setShowCreate] = React.useState(false)
  const [question, setQuestion] = React.useState('')
  const [options, setOptions] = React.useState<string[]>(['', ''])
  const [submitting, setSubmitting] = React.useState(false)
  // Optimistic vote: option index the current user just tapped, keyed by
  // poll id, applied immediately (before the vote response resolves) and
  // cleared once the server confirms my_vote.
  const [optimisticVotes, setOptimisticVotes] = React.useState<Record<number, number>>({})

  const load = React.useCallback(async () => {
    try {
      setError(null)
      const data = await listPolls(classId)
      setPolls(data)
    } catch (err: any) {
      setError(err?.message || 'Failed to load polls')
    } finally {
      setLoading(false)
    }
  }, [classId])

  React.useEffect(() => {
    load()
    const id = window.setInterval(load, POLL_POLL_INTERVAL_MS)
    return () => window.clearInterval(id)
  }, [load])

  const activePoll = polls.find((p) => p.status === 'active')
  const draftPolls = polls.filter((p) => p.status === 'draft')
  const closedPolls = polls.filter((p) => p.status === 'closed')

  const handleAddOption = () => setOptions((prev) => [...prev, ''])
  const handleRemoveOption = (idx: number) =>
    setOptions((prev) => prev.filter((_, i) => i !== idx))
  const handleOptionChange = (idx: number, value: string) =>
    setOptions((prev) => prev.map((o, i) => (i === idx ? value : o)))

  const resetForm = () => {
    setQuestion('')
    setOptions(['', ''])
    setShowCreate(false)
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    const cleanOptions = options.map((o) => o.trim()).filter(Boolean)
    if (!question.trim() || cleanOptions.length < 2) return
    setSubmitting(true)
    try {
      await createPoll(classId, { question: question.trim(), options: cleanOptions })
      resetForm()
      await load()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to create poll')
    } finally {
      setSubmitting(false)
    }
  }

  const handleActivate = async (pollId: number) => {
    try {
      await activatePoll(classId, pollId)
      await load()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to activate poll')
    }
  }

  const handleClose = async (pollId: number) => {
    try {
      await closePoll(classId, pollId)
      await load()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to close poll')
    }
  }

  const handleVote = async (poll: PollOut, optionIndex: number) => {
    setOptimisticVotes((prev) => ({ ...prev, [poll.id]: optionIndex }))
    try {
      await votePoll(classId, poll.id, optionIndex)
      await load()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to submit vote')
    } finally {
      setOptimisticVotes((prev) => {
        const next = { ...prev }
        delete next[poll.id]
        return next
      })
    }
  }

  return (
    <div className={`flex flex-col gap-4 ${className}`} data-testid="poll-panel">
      {isModerator && (
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-secondary-900">Polls</h3>
          {!showCreate && (
            <Button size="sm" variant="outline" onClick={() => setShowCreate(true)}>
              <Plus className="h-3.5 w-3.5 mr-1" /> New poll
            </Button>
          )}
        </div>
      )}

      {error && (
        <p className="text-xs text-danger-600 bg-danger-50 border border-danger-200 rounded-md px-3 py-2">
          {error}
        </p>
      )}

      {isModerator && showCreate && (
        <form onSubmit={handleCreate} className="rounded-lg border border-slate-200 p-3 space-y-2 bg-slate-50">
          <input
            type="text"
            placeholder="Question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
          {options.map((opt, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <input
                type="text"
                placeholder={`Option ${idx + 1}`}
                value={opt}
                onChange={(e) => handleOptionChange(idx, e.target.value)}
                className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
              {options.length > 2 && (
                <button
                  type="button"
                  onClick={() => handleRemoveOption(idx)}
                  className="text-slate-400 hover:text-danger-500"
                  aria-label="Remove option"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              onClick={handleAddOption}
              className="text-xs text-primary-600 hover:text-primary-700 font-medium"
            >
              + Add option
            </button>
            <div className="flex gap-2">
              <Button type="button" size="sm" variant="ghost" onClick={resetForm}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={submitting}>
                Create
              </Button>
            </div>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-xs text-slate-400">Loading polls…</p>
      ) : (
        <div className="flex flex-col gap-3">
          {activePoll && (
            <PollCard
              key={activePoll.id}
              poll={activePoll}
              isModerator={isModerator}
              optimisticIndex={optimisticVotes[activePoll.id]}
              onActivate={handleActivate}
              onClose={handleClose}
              onVote={handleVote}
            />
          )}
          {draftPolls.map((poll) => (
            <PollCard
              key={poll.id}
              poll={poll}
              isModerator={isModerator}
              optimisticIndex={optimisticVotes[poll.id]}
              onActivate={handleActivate}
              onClose={handleClose}
              onVote={handleVote}
            />
          ))}
          {closedPolls.map((poll) => (
            <PollCard
              key={poll.id}
              poll={poll}
              isModerator={isModerator}
              optimisticIndex={optimisticVotes[poll.id]}
              onActivate={handleActivate}
              onClose={handleClose}
              onVote={handleVote}
            />
          ))}
          {!activePoll && draftPolls.length === 0 && closedPolls.length === 0 && (
            <p className="text-xs text-slate-400">No polls yet.</p>
          )}
        </div>
      )}
    </div>
  )
}

const STATUS_BADGE: Record<PollOut['status'], { label: string; variant: 'success' | 'secondary' | 'neutral' }> = {
  active: { label: 'Live', variant: 'success' },
  draft: { label: 'Draft', variant: 'secondary' },
  closed: { label: 'Closed', variant: 'neutral' },
}

const PollCard: React.FC<{
  poll: PollOut
  isModerator: boolean
  optimisticIndex?: number
  onActivate: (pollId: number) => void
  onClose: (pollId: number) => void
  onVote: (poll: PollOut, optionIndex: number) => void
}> = ({ poll, isModerator, optimisticIndex, onActivate, onClose, onVote }) => {
  const badge = STATUS_BADGE[poll.status]
  const selectedIndex = optimisticIndex ?? poll.my_vote ?? null
  const showResults = isModerator || poll.show_results

  return (
    <div className="rounded-lg border border-slate-200 p-3" data-testid={`poll-card-${poll.id}`}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-sm font-medium text-secondary-900 flex-1">{poll.question}</p>
        <Badge variant={badge.variant} className="flex-shrink-0">
          {poll.status === 'active' && <Radio className="h-3 w-3 mr-1 inline animate-pulse" />}
          {badge.label}
        </Badge>
      </div>

      <div className="space-y-1.5">
        {poll.options.map((opt, idx) => {
          const { count, pct } = optionTally(poll, idx)
          const isSelected = selectedIndex === idx
          return (
            <button
              key={idx}
              type="button"
              disabled={isModerator || poll.status !== 'active'}
              onClick={() => onVote(poll, idx)}
              className={`w-full text-left relative rounded-md border px-2.5 py-1.5 text-xs overflow-hidden transition-colors ${
                isSelected ? 'border-primary-400' : 'border-slate-200'
              } ${!isModerator && poll.status === 'active' ? 'hover:bg-slate-50 cursor-pointer' : 'cursor-default'}`}
            >
              {showResults && (
                <span
                  className="absolute inset-y-0 left-0 bg-primary-100"
                  style={{ width: `${pct}%` }}
                  aria-hidden
                />
              )}
              <span className="relative flex items-center justify-between gap-2">
                <span className="flex items-center gap-1.5">
                  {isSelected && <CheckCircle2 className="h-3.5 w-3.5 text-primary-600" />}
                  {opt}
                </span>
                {showResults && (
                  <span className="text-slate-500 flex-shrink-0">{count} ({pct}%)</span>
                )}
              </span>
            </button>
          )
        })}
      </div>

      {isModerator && (
        <div className="flex justify-end gap-2 mt-2">
          {poll.status === 'draft' && (
            <Button size="sm" variant="outline" onClick={() => onActivate(poll.id)}>
              Activate
            </Button>
          )}
          {poll.status === 'active' && (
            <Button size="sm" variant="outline" onClick={() => onClose(poll.id)}>
              Close
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

export default PollPanel
