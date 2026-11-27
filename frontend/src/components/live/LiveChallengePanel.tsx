import * as React from 'react'
import { codingAPI, type CodingLanguage, type CodingSubmission, type EditorChallenge } from '@/api/coding'
import { plannerError } from '@/api/planner'
import { liveCodingAPI, type LiveBoard, type LiveCodingChallenge } from '@/api/liveCoding'
import { CodingWorkspace } from '@/components/coding/CodingWorkspace'

const BOARD_POLL_MS = 5_000

export interface LiveChallengePanelProps {
  classId: number
  /** Instructor console: push, close, reveal and watch the board. */
  isStaff?: boolean
  /** Required for staff, to list the course's published challenges. */
  courseId?: number
  className?: string
}

/**
 * Live coding exercises for a class session.
 * Staff push a published challenge, watch the results board and reveal the
 * model solution after closing. Learners work on the open challenge inside
 * the live view; their submissions go through the live endpoint.
 */
export const LiveChallengePanel: React.FC<LiveChallengePanelProps> = ({ classId, isStaff = false, courseId, className = '' }) => {
  const [items, setItems] = React.useState<LiveCodingChallenge[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState('')
  const [message, setMessage] = React.useState('')
  const [busy, setBusy] = React.useState(false)

  const load = React.useCallback(async () => {
    try {
      setItems(await liveCodingAPI.list(classId))
      setError('')
    } catch (reason) {
      setError(plannerError(reason))
    } finally {
      setLoading(false)
    }
  }, [classId])

  React.useEffect(() => {
    void load()
    const id = window.setInterval(() => void load(), BOARD_POLL_MS)
    return () => window.clearInterval(id)
  }, [load])

  const open = items.find((item) => item.status === 'open') || null
  // Learners see nothing in the live view until there is something to work on.
  const hasLearnerContent = Boolean(open) || items.some((item) => item.solution_revealed && item.model_solution)
  if (!isStaff && (loading || !hasLearnerContent)) return null

  const run = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      await action()
      setMessage(success)
      await load()
      return true
    } catch (reason) {
      setError(plannerError(reason))
      return false
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className={`space-y-4 ${className}`} aria-label="Live coding challenges">
      {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {message && <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}

      {isStaff ? (
        <StaffView
          items={items}
          open={open}
          loading={loading}
          busy={busy}
          courseId={courseId}
          onPush={(body) => run(() => liveCodingAPI.push(classId, body), 'Challenge pushed to learners.')}
          onClose={(item) => run(() => liveCodingAPI.close(item.id), 'Challenge closed. Learners can no longer submit.')}
          onReveal={(item) => run(() => liveCodingAPI.reveal(item.id), 'Model solution revealed to learners.')}
        />
      ) : (
        <LearnerView items={items} open={open} loading={loading} />
      )}
    </section>
  )
}

function StaffView({
  items, open, loading, busy, courseId, onPush, onClose, onReveal,
}: {
  items: LiveCodingChallenge[]
  open: LiveCodingChallenge | null
  loading: boolean
  busy: boolean
  courseId?: number
  onPush: (body: { challenge_id: number; graded: boolean; instructions: string; model_solution: string }) => Promise<boolean>
  onClose: (item: LiveCodingChallenge) => Promise<boolean>
  onReveal: (item: LiveCodingChallenge) => Promise<boolean>
}) {
  const [published, setPublished] = React.useState<EditorChallenge[]>([])
  const [challengeId, setChallengeId] = React.useState(0)
  const [graded, setGraded] = React.useState(false)
  const [instructions, setInstructions] = React.useState('')
  const [solution, setSolution] = React.useState('')

  React.useEffect(() => {
    if (!courseId) return
    codingAPI.editorChallenges(courseId)
      .then((rows) => setPublished(rows.filter((row) => row.status === 'published')))
      .catch(() => setPublished([]))
  }, [courseId])

  const push = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!challengeId) return
    const ok = await onPush({ challenge_id: challengeId, graded, instructions, model_solution: solution })
    if (ok) { setInstructions(''); setSolution('') }
  }

  return (
    <>
      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <h3 className="font-semibold text-slate-900">Push a coding challenge</h3>
        {open ? (
          <p className="mt-2 text-sm text-slate-600">“{open.challenge_title}” is open. Close it before pushing another.</p>
        ) : (
          <form onSubmit={(event) => void push(event)} className="mt-3 space-y-3">
            <label className="block text-sm font-medium text-slate-800">Challenge
              <select value={challengeId} onChange={(event) => setChallengeId(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <option value={0}>{published.length ? 'Choose a published challenge' : 'No published challenges in this course'}</option>
                {published.map((row) => <option key={row.id} value={row.id}>{row.title}</option>)}
              </select>
            </label>
            <label className="block text-sm font-medium text-slate-800">Instructions for learners
              <textarea rows={2} maxLength={2000} value={instructions} onChange={(event) => setInstructions(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
            </label>
            <label className="block text-sm font-medium text-slate-800">Model solution (revealed after you close)
              <textarea rows={4} maxLength={65536} spellCheck={false} value={solution} onChange={(event) => setSolution(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-xs" />
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={graded} onChange={(event) => setGraded(event.target.checked)} />
              Graded session (practice runs otherwise)
            </label>
            <button type="submit" disabled={busy || !challengeId} className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Push to learners</button>
          </form>
        )}
      </div>

      {open && <Board liveId={open.id} />}

      <div className="space-y-2">
        <h3 className="font-semibold text-slate-900">This session</h3>
        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        {!loading && items.length === 0 && <p className="text-sm text-slate-500">Nothing pushed yet.</p>}
        {items.map((item) => (
          <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white p-3 text-sm">
            <div>
              <span className="font-medium text-slate-900">{item.challenge_title}</span>
              <span className="ml-2 text-xs text-slate-500">{item.status === 'open' ? 'Open' : 'Closed'} · {item.graded ? 'Graded' : 'Practice'}</span>
            </div>
            <div className="flex gap-2">
              {item.status === 'open' && <button type="button" disabled={busy} onClick={() => void onClose(item)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium">Close</button>}
              {item.status === 'closed' && !item.solution_revealed && item.model_solution && <button type="button" disabled={busy} onClick={() => void onReveal(item)} className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white">Reveal solution</button>}
              {item.solution_revealed && <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-700">Solution shared</span>}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

function LearnerView({ items, open, loading }: { items: LiveCodingChallenge[]; open: LiveCodingChallenge | null; loading: boolean }) {
  const [submitted, setSubmitted] = React.useState<CodingSubmission | null>(null)
  const revealed = items.filter((item) => item.solution_revealed && item.model_solution)

  const submit = React.useCallback(
    async (language: CodingLanguage, source: string, key: string) => {
      if (!open) throw new Error('This challenge is no longer open.')
      const result = await liveCodingAPI.submit(open.id, language, source, key)
      setSubmitted(result.submission)
      return result.submission
    },
    [open],
  )

  if (loading) return null
  if (!open && revealed.length === 0) return null

  return (
    <>
      {open ? (
        <div className="space-y-3 rounded-2xl border border-violet-200 bg-white p-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-violet-600">Live challenge · {open.graded ? 'Graded' : 'Practice'}</p>
            <h3 className="font-semibold text-slate-900">{open.challenge_title}</h3>
            {open.instructions && <p className="mt-1 text-sm text-slate-600">{open.instructions}</p>}
          </div>
          <CodingWorkspace slug={open.challenge_slug} embedded submitOverride={submit} />
          {submitted && <p className="text-xs text-slate-500">Last submission: {submitted.status.replace(/_/g, ' ')}</p>}
          <Board liveId={open.id} learner />
        </div>
      ) : null}

      {revealed.map((item) => (
        <div key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4">
          <h3 className="font-semibold text-slate-900">Model solution · {item.challenge_title}</h3>
          <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">{item.model_solution}</pre>
        </div>
      ))}
    </>
  )
}

function Board({ liveId, learner = false }: { liveId: number; learner?: boolean }) {
  const [board, setBoard] = React.useState<LiveBoard | null>(null)

  React.useEffect(() => {
    let active = true
    const fetchBoard = () => liveCodingAPI.board(liveId).then((data) => active && setBoard(data)).catch(() => undefined)
    void fetchBoard()
    const id = window.setInterval(() => void fetchBoard(), BOARD_POLL_MS)
    return () => { active = false; window.clearInterval(id) }
  }, [liveId])

  if (!board) return null

  if (learner) {
    const mine = board.my_row
    return (
      <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700" data-testid="live-my-result">
        {mine
          ? <>Your best: <strong>{mine.best_score}</strong> pts · {mine.passed ? 'passed' : 'not passed yet'} · {mine.attempts} attempt{mine.attempts === 1 ? '' : 's'}</>
          : 'No submission yet.'}
        <span className="ml-2 text-xs text-slate-500">{board.summary.learners_passed} of {board.summary.learners_submitted} learners have passed</span>
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4" data-testid="live-board">
      <div className="flex items-center justify-between text-sm">
        <h3 className="font-semibold text-slate-900">Results board</h3>
        <span className="text-slate-500">{board.summary.learners_passed} passed · {board.summary.learners_submitted} submitted{board.pending_submissions ? ` · ${board.pending_submissions} running` : ''}</span>
      </div>
      {(board.rows || []).length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">No finished submissions yet.</p>
      ) : (
        <ol className="mt-3 divide-y divide-slate-100 text-sm">
          {(board.rows || []).map((row) => (
            <li key={row.user_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span className="font-medium text-slate-900">{row.rank}. {row.learner_name || `Learner ${row.user_id}`}</span>
              <span className="text-slate-600">{row.best_score} pts · {row.passed ? 'passed' : 'not passed'} · {row.attempts} attempt{row.attempts === 1 ? '' : 's'}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

export default LiveChallengePanel
