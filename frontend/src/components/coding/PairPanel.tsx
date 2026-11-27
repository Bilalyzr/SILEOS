import { lazy, Suspense, useState } from 'react'
import { codingCollabAPI, type CollabRoom } from '@/api/codingCollab'
import type { CodingLanguage } from '@/api/coding'
import { plannerError } from '@/api/planner'

const CollabEditor = lazy(() => import('./CollabEditor'))

interface PairPanelProps {
  slug: string
  language: CodingLanguage
  starterCode: string
}

/**
 * Pair coding on one challenge. A learner starts a room and shares the invite
 * code, or joins one with a code. Both see the same editor.
 */
export function PairPanel({ slug, language, starterCode }: PairPanelProps) {
  const [room, setRoom] = useState<CollabRoom | null>(null)
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  const start = async () => {
    setBusy(true)
    setError('')
    try {
      setRoom(await codingCollabAPI.create(slug, language))
    } catch (reason) {
      setError(plannerError(reason))
    } finally {
      setBusy(false)
    }
  }

  const join = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!code.trim()) return
    setBusy(true)
    setError('')
    try {
      setRoom(await codingCollabAPI.join(code.trim()))
    } catch (reason) {
      setError(plannerError(reason))
    } finally {
      setBusy(false)
    }
  }

  const copyCode = async () => {
    if (!room) return
    try {
      await navigator.clipboard.writeText(room.invite_code)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  if (!room) {
    return (
      <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-slate-100">
        <h3 className="font-semibold">Pair on this challenge</h3>
        <p className="mt-1 text-xs text-slate-300">Start a shared editor and send the invite code to a classmate, or join one they sent you.</p>
        {error && <p role="alert" className="mt-2 text-xs text-red-300">{error}</p>}
        <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-end">
          <button type="button" disabled={busy} onClick={() => void start()} className="rounded-lg bg-violet-600 px-4 py-2 font-semibold text-white disabled:opacity-50">Start a pair room</button>
          <form onSubmit={(event) => void join(event)} className="flex flex-1 gap-2">
            <input aria-label="Invite code" value={code} onChange={(event) => setCode(event.target.value)} placeholder="Invite code" className="min-w-0 flex-1 rounded-lg border border-white/10 bg-[#0d111a] px-3 py-2 text-slate-100" />
            <button type="submit" disabled={busy || !code.trim()} className="rounded-lg border border-violet-400/40 px-4 py-2 font-semibold text-violet-100 disabled:opacity-50">Join</button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-4 space-y-3 rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-slate-100">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">Pair room · {room.challenge_title}</h3>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-300">Invite code</span>
          <code className="rounded bg-[#0d111a] px-2 py-1 font-mono text-violet-200">{room.invite_code}</code>
          <button type="button" onClick={() => void copyCode()} className="rounded border border-white/10 px-2 py-1 text-slate-200">{copied ? 'Copied' : 'Copy'}</button>
        </div>
      </div>
      <p className="text-xs text-slate-300">Members: {room.members.map((member) => member.name || 'Learner').join(', ')} ({room.members.length} of {room.max_members})</p>
      <Suspense fallback={<p className="text-xs text-slate-300">Loading shared editor…</p>}>
        <CollabEditor room={room} starterCode={starterCode} />
      </Suspense>
      <p className="text-xs text-slate-400">The shared code is for pairing. To submit it, copy it into the editor above and run it there.</p>
    </div>
  )
}

export default PairPanel
