import * as React from 'react'

export interface RemainingTime {
  /** Milliseconds remaining until target, clamped to >= 0. */
  totalMs: number
  /** True once the target has been reached/passed (totalMs === 0). */
  isPast: boolean
  days: number
  hours: number
  minutes: number
  seconds: number
}

/**
 * Pure countdown math, exported for tests (per the plan's binding
 * behavior for ClassCountdown).
 *
 * The server and the browser clock can disagree (server_ts is the backend's
 * `now` at the moment the class payload was fetched). We compute the offset
 * between the server's clock and the local clock at fetch time, then apply
 * that same offset to "now" on every re-render — so a countdown stays
 * accurate even if the viewer's system clock is skewed, without polling the
 * server every tick.
 *
 *   offset = serverTs - fetchedAtLocal   (server ahead of local => positive)
 *   correctedNow = nowLocal + offset
 *   remaining = target - correctedNow
 */
export function computeRemaining(
  serverTs: Date | string,
  fetchedAtLocal: Date | string,
  target: Date | string,
  nowLocal: Date | string
): RemainingTime {
  const serverMs = new Date(serverTs).getTime()
  const fetchedMs = new Date(fetchedAtLocal).getTime()
  const targetMs = new Date(target).getTime()
  const nowMs = new Date(nowLocal).getTime()

  const offsetMs = serverMs - fetchedMs
  const correctedNowMs = nowMs + offsetMs
  const rawRemaining = targetMs - correctedNowMs
  const totalMs = Math.max(0, rawRemaining)

  const totalSeconds = Math.floor(totalMs / 1000)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  return {
    totalMs,
    isPast: rawRemaining <= 0,
    days,
    hours,
    minutes,
    seconds,
  }
}

/** Short human label, e.g. "in 2h 14m", "in 45s", "starting now". */
export function formatRemaining(remaining: RemainingTime): string {
  if (remaining.isPast) return 'starting now'
  if (remaining.days > 0) return `in ${remaining.days}d ${remaining.hours}h`
  if (remaining.hours > 0) return `in ${remaining.hours}h ${remaining.minutes}m`
  if (remaining.minutes > 0) return `in ${remaining.minutes}m`
  return `in ${remaining.seconds}s`
}

export interface ClassCountdownProps {
  /** Server's clock at the time this data was fetched (LiveClassOut.server_ts). */
  serverTs: string
  /** Local clock at the moment `serverTs` was received — set once when the
   * class payload is fetched, not re-set on every render. */
  fetchedAtLocal: Date
  /** The instant being counted down to (e.g. scheduled_start or join_opens_at). */
  target: string
  className?: string
  /** Called once when the countdown reaches zero. */
  onComplete?: () => void
}

export const ClassCountdown: React.FC<ClassCountdownProps> = ({
  serverTs,
  fetchedAtLocal,
  target,
  className = '',
  onComplete,
}) => {
  const [now, setNow] = React.useState<Date>(() => new Date())
  const firedRef = React.useRef(false)

  React.useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(id)
  }, [])

  const remaining = computeRemaining(serverTs, fetchedAtLocal, target, now)

  React.useEffect(() => {
    if (remaining.isPast && !firedRef.current) {
      firedRef.current = true
      onComplete?.()
    }
  }, [remaining.isPast, onComplete])

  return (
    <span className={className} data-testid="class-countdown">
      {formatRemaining(remaining)}
    </span>
  )
}
