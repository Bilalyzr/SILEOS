/**
 * AwardToaster — consumes unseen award events on mount (plan Task 10,
 * spec D6/D7).
 *
 * Flow: GET /api/v1/gamification/me/unseen -> for each unseen badge/level-up/
 * streak-milestone XpEvent, fire the same celebratory pattern the lesson
 * player already uses (celebrationAnimation() confetti burst from
 * utils/animations.ts + a timed toast banner — showAchievementNotification
 * in pages/lesson-redesigned.tsx is local component state, not exported, so
 * this component reimplements the same visual pattern rather than importing
 * it) -> POST /me/unseen/mark-seen once, for every consumed event id, so a
 * remount never re-fires the same celebration.
 *
 * Mount this once per authenticated session (e.g. on the dashboard) — it
 * renders nothing but a fixed-position toast when there's something to show.
 */
import * as React from 'react'
import { Award, TrendingUp, Flame, X } from 'lucide-react'
import { celebrationAnimation } from '@/utils/animations'
import { gamificationAPI, type GamificationEvent } from '@/api/gamification'

const AUTO_DISMISS_MS = 4500

export interface AwardToast {
  id: number
  title: string
  description: string
  kind: 'badge' | 'level_up' | 'streak' | 'other'
}

/** Pure helper — exported for vitest. Maps a raw unseen XpEvent to display
 * copy; badges carry their name in meta.badge_name (see gamification.py's
 * `_evaluate_badges`), level-ups aren't currently emitted as their own
 * event_type by the backend (level is derived, not stored) so this also
 * covers the streak_milestone:N event_type the service DOES emit. */
export function eventToToast(ev: GamificationEvent): AwardToast {
  if (ev.event_type.startsWith('badge:')) {
    const name = (ev.meta?.badge_name as string) || ev.event_type.replace('badge:', '')
    return { id: ev.id, title: 'Badge earned!', description: name, kind: 'badge' }
  }
  if (ev.event_type.startsWith('streak_milestone:')) {
    const streak = (ev.meta?.streak as number) ?? ev.event_type.split(':')[1]
    return { id: ev.id, title: 'Streak milestone!', description: `${streak}-day streak — +${ev.points} XP`, kind: 'streak' }
  }
  if (ev.event_type === 'level_up') {
    return { id: ev.id, title: 'Level up!', description: `+${ev.points} XP`, kind: 'level_up' }
  }
  return { id: ev.id, title: 'Nice work!', description: `+${ev.points} XP`, kind: 'other' }
}

function toastIcon(kind: AwardToast['kind']) {
  if (kind === 'badge') return Award
  if (kind === 'streak') return Flame
  return TrendingUp
}

export const AwardToaster: React.FC = () => {
  const [queue, setQueue] = React.useState<AwardToast[]>([])
  const consumedRef = React.useRef(false)

  React.useEffect(() => {
    if (consumedRef.current) return
    consumedRef.current = true

    let cancelled = false
    ;(async () => {
      try {
        const { unseen } = await gamificationAPI.getUnseen()
        if (cancelled || unseen.length === 0) return

        const toasts = unseen.map(eventToToast)
        setQueue(toasts)
        celebrationAnimation()

        // Mark seen immediately once — even if the user navigates away
        // before the toast auto-dismisses, it must never re-fire.
        await gamificationAPI.markSeen(unseen.map((e) => e.id))
      } catch {
        // Best-effort UX flourish — never surface an error for this.
      }
    })()

    return () => { cancelled = true }
  }, [])

  const dismiss = React.useCallback((id: number) => {
    setQueue((prev) => prev.filter((t) => t.id !== id))
  }, [])

  React.useEffect(() => {
    if (queue.length === 0) return
    const timers = queue.map((t) => setTimeout(() => dismiss(t.id), AUTO_DISMISS_MS))
    return () => { timers.forEach(clearTimeout) }
  }, [queue, dismiss])

  if (queue.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-[9998] flex flex-col gap-2 pointer-events-none" data-testid="award-toaster">
      {queue.map((t) => {
        const Icon = toastIcon(t.kind)
        return (
          <div
            key={t.id}
            data-testid={`award-toast-${t.id}`}
            className="pointer-events-auto flex items-center gap-3 bg-white shadow-xl rounded-2xl border border-amber-200 px-4 py-3 min-w-[260px] max-w-sm animate-in slide-in-from-right"
          >
            <div className="w-9 h-9 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center flex-shrink-0">
              <Icon className="w-4.5 h-4.5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-secondary-900">{t.title}</p>
              <p className="text-xs text-slate-500 truncate">{t.description}</p>
            </div>
            <button
              onClick={() => dismiss(t.id)}
              className="text-slate-400 hover:text-slate-600 flex-shrink-0"
              aria-label="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )
      })}
    </div>
  )
}

export default AwardToaster
