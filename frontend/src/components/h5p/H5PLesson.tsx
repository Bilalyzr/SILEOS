/**
 * H5PLesson — renders one H5P interactive-content item inside a sandboxed
 * iframe pointed at the static player page (public/h5p-player.html).
 *
 * Security model (spec B3, BINDING): the iframe sandbox is
 * "allow-scripts" ONLY — allow-same-origin must NEVER be added, since that
 * combination would let instructor-supplied H5P JS read this app's cookies/
 * localStorage/DOM. This file has one test asserting the exact sandbox
 * attribute value to catch a regression that widens it.
 *
 * Message verification deviates from the spec's literal wording
 * ("event.origin === window.origin"): a sandboxed iframe without
 * allow-same-origin is an opaque origin, so event.origin arrives as the
 * string "null" on every real browser — comparing it to window.location.origin
 * would never match and the player would be unusable. Instead we verify
 * `event.source === iframeRef.current?.contentWindow` (a live window
 * reference the browser sets, not attacker-spoofable) AND validate the
 * message payload shape before trusting it. See h5p-player.html's own
 * comment and the Task 5 report for the same note.
 */
import * as React from 'react'
import { Loader2, AlertTriangle } from 'lucide-react'
import { submitH5PResult } from '@/api/h5p'

export interface H5PResultMessage {
  type: 'h5p-result'
  score: number | null
  maxScore: number | null
  completed: boolean
}

export interface H5PErrorMessage {
  type: 'h5p-error'
  message: string
  detail?: string
}

/** Narrow an arbitrary postMessage payload down to a well-formed H5P result message. */
export function isValidH5PResultMessage(data: unknown): data is H5PResultMessage {
  if (!data || typeof data !== 'object') return false
  const d = data as Record<string, unknown>
  if (d.type !== 'h5p-result') return false
  if (typeof d.completed !== 'boolean') return false
  if (d.score !== null && d.score !== undefined && typeof d.score !== 'number') return false
  if (d.maxScore !== null && d.maxScore !== undefined && typeof d.maxScore !== 'number') return false
  return true
}

export function isValidH5PErrorMessage(data: unknown): data is H5PErrorMessage {
  if (!data || typeof data !== 'object') return false
  const d = data as Record<string, unknown>
  return d.type === 'h5p-error' && typeof d.message === 'string'
}

/**
 * A result is treated as "completed" for the purposes of calling the
 * lesson-complete endpoint when either:
 *  - there is no score at all (pure interactive content with no scoring), or
 *  - score/maxScore achieves at least 50% (spec B6's threshold).
 * The player-reported `completed` flag must also be true — a mid-content
 * xAPI "answered" event with a passing sub-score must not trigger this.
 */
export function meetsCompletionThreshold(message: H5PResultMessage): boolean {
  if (!message.completed) return false
  if (message.score === null || message.score === undefined) return true
  if (message.maxScore === null || message.maxScore === undefined || message.maxScore <= 0) return true
  return message.score / message.maxScore >= 0.5
}

export interface H5PLessonProps {
  /** The H5P content's public_id (validated ^[a-f0-9]{32}$ before use). */
  contentId: string
  title?: string
  /** Called once, after a completed result clears the completion threshold. */
  onCompleted?: () => void
  className?: string
  /**
   * Preview mode (instructor "Preview" button, spec B7): the sandbox and
   * message-handling wiring are identical, but result-POST and completion
   * side effects are suppressed — a preview play-through must never write
   * an advisory result or mark a real lesson complete.
   */
  previewOnly?: boolean
}

const PUBLIC_ID_RE = /^[a-f0-9]{32}$/

/**
 * Validates an H5P content public_id: exactly 32 lowercase hex characters,
 * matching h5p_service.generate_public_id's secrets.token_hex(16) output.
 * Mirrors the same check in public/h5p-player.html (the static player page
 * cannot import this module, so the regex is duplicated there — keep both
 * in sync if this ever changes).
 */
export function isValidH5PPublicId(value: string): boolean {
  return PUBLIC_ID_RE.test(value)
}

export const H5PLesson: React.FC<H5PLessonProps> = ({ contentId, title, onCompleted, className = '', previewOnly = false }) => {
  const iframeRef = React.useRef<HTMLIFrameElement>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const reportedCompletionRef = React.useRef(false)
  // Guards only the POST — never gates the completion/onCompleted path (see
  // handleMessage below). `pendingRef` holds the most recent terminal
  // message received WHILE a POST is already in flight, so it can be
  // re-submitted once that POST resolves instead of being silently dropped
  // (fix for a real bug: Question Set fires answered->completed
  // back-to-back, and dropping the second message's POST meant the
  // completed result never reached the server even though onCompleted
  // fired correctly from it).
  const submittingRef = React.useRef(false)
  const pendingRef = React.useRef<H5PResultMessage | null>(null)

  const isValidContentId = isValidH5PPublicId(contentId)

  React.useEffect(() => {
    // Reset per-content-id so navigating between two H5P lessons doesn't
    // carry over a stale "already completed" guard.
    reportedCompletionRef.current = false
    submittingRef.current = false
    pendingRef.current = null
    setLoading(true)
    setError(null)
  }, [contentId])

  React.useEffect(() => {
    if (!isValidContentId) {
      setError('This interactive content could not be loaded (invalid id).')
      setLoading(false)
      return
    }

    // Submits one result message, then re-submits whatever landed in
    // pendingRef while this POST was in flight (drops intermediate
    // messages — only the LATEST pending one is ever kept — and keeps
    // submitting until the queue is empty). previewOnly skips the network
    // call entirely; the caller never wants advisory data recorded for a
    // preview play-through.
    const submitResult = async (message: H5PResultMessage) => {
      if (previewOnly) return
      if (submittingRef.current) {
        pendingRef.current = message
        return
      }
      submittingRef.current = true
      try {
        await submitH5PResult(contentId, {
          score: message.score,
          max_score: message.maxScore,
          completed: message.completed,
        })
      } catch {
        // Advisory data (spec B6/B8) — a failed POST must not break playback.
      } finally {
        submittingRef.current = false
      }
      const next = pendingRef.current
      if (next) {
        pendingRef.current = null
        await submitResult(next)
      }
    }

    const handleMessage = (event: MessageEvent) => {
      // Verify by SOURCE, not origin (see file header comment) — a
      // sandboxed iframe without allow-same-origin reports event.origin as
      // "null", so source identity is the only reliable check available.
      if (!iframeRef.current || event.source !== iframeRef.current.contentWindow) {
        return
      }

      const data: unknown = event.data

      if (isValidH5PErrorMessage(data)) {
        setError('This interactive content could not be loaded.')
        setLoading(false)
        return
      }

      if (!isValidH5PResultMessage(data)) {
        // Unrecognized/malformed payload from our own iframe — ignore
        // silently rather than acting on it.
        return
      }

      // The player having sent ANY well-formed message means it booted.
      setLoading(false)

      // Completion is evaluated synchronously from EVERY terminal message,
      // independent of the POST's in-flight state — a rapid
      // answered->completed pair (Question Set) must still mark the lesson
      // complete even if the first message's POST hasn't resolved yet.
      if (!previewOnly && !reportedCompletionRef.current && meetsCompletionThreshold(data)) {
        reportedCompletionRef.current = true
        onCompleted?.()
      }

      void submitResult(data)
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [contentId, isValidContentId, onCompleted, previewOnly])

  if (!isValidContentId) {
    return (
      <div className={`h-full w-full flex items-center justify-center bg-neutral-950 text-red-300 ${className}`}>
        <div className="text-center px-6">
          <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
          <p className="text-sm">This interactive content could not be loaded.</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`relative h-full w-full bg-neutral-950 ${className}`}>
      {loading && !error && (
        <div className="absolute inset-0 flex items-center justify-center bg-neutral-950 z-10">
          <div className="text-center">
            <Loader2 className="w-8 h-8 mx-auto mb-2 text-primary-500 animate-spin" />
            <p className="text-sm text-neutral-400">Loading interactive content&hellip;</p>
          </div>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-neutral-950 z-10">
          <div className="text-center px-6">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-red-400" />
            <p className="text-sm text-red-300">{error}</p>
          </div>
        </div>
      )}
      <iframe
        ref={iframeRef}
        src={`/h5p-player.html?content=${encodeURIComponent(contentId)}`}
        // BINDING (spec B3): allow-scripts ONLY. Never add allow-same-origin —
        // that would let instructor-supplied H5P JS read this app's cookies/
        // storage/DOM. See H5PLesson.test.tsx's exact-value assertion.
        sandbox="allow-scripts"
        title={title || 'Interactive content'}
        allow="fullscreen"
        allowFullScreen
        className="w-full h-full border-0"
        // The iframe DOCUMENT loading is not the same as the H5P player
        // having booted — the loading state is only cleared by a real
        // message arriving (handleMessage above), not by this element's
        // own load event.
      />
    </div>
  )
}

export default H5PLesson
