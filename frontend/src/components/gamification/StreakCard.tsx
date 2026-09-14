/**
 * StreakCard — the REAL streak card (plan Task 10, spec D6), replacing the
 * dead stub at components/streak/streak-card.tsx (deleted alongside this
 * file — it had zero imports, grepped clean).
 *
 * current_streak/longest_streak come straight off GET /api/v1/gamification/me
 * (already staleness-corrected server-side — see gamification_service's M1
 * review fix; this component does not re-derive staleness). The last-7-days
 * dots are derived client-side from `recent_events` (any XpEvent on that
 * calendar day counts as "active" — mirrors the server's own day-granularity
 * streak math, not a guess).
 */
import * as React from 'react'
import { motion } from 'framer-motion'
import { Flame } from 'lucide-react'
import { fadeUp } from '@/components/dashboard/primitives'
import type { GamificationEvent, GamificationStats } from '@/api/gamification'

/** Pure helper — exported for vitest. Builds the last-N-days activity flags
 * (oldest first) from a list of XpEvents, using UTC calendar days to match
 * the backend's own `date` (UTC) streak semantics (see
 * UserGameStats.last_active_date). */
export function buildLastNDaysActivity(
  events: Pick<GamificationEvent, 'created_at'>[],
  days = 7,
  today: Date = new Date(),
): { date: string; active: boolean }[] {
  const activeDates = new Set(
    events
      .map((e) => e.created_at)
      .filter((iso): iso is string => Boolean(iso))
      .map((iso) => iso.slice(0, 10)), // YYYY-MM-DD (UTC, ISO strings from the backend)
  )

  const todayUtc = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()))
  const result: { date: string; active: boolean }[] = []
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(todayUtc)
    d.setUTCDate(d.getUTCDate() - i)
    const key = d.toISOString().slice(0, 10)
    result.push({ date: key, active: activeDates.has(key) })
  }
  return result
}

export interface StreakCardProps {
  stats: GamificationStats | null | undefined
  recentEvents?: GamificationEvent[]
  className?: string
}

const DAY_LABELS = ['S', 'M', 'T', 'W', 'T', 'F', 'S']

export const StreakCard: React.FC<StreakCardProps> = ({ stats, recentEvents = [], className = '' }) => {
  const current = stats?.current_streak ?? 0
  const longest = stats?.longest_streak ?? 0
  const days = React.useMemo(() => buildLastNDaysActivity(recentEvents, 7), [recentEvents])

  return (
    <motion.div variants={fadeUp} className={`dash-card p-5 h-full ${className}`}>
      <div className="flex items-center gap-4">
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center ring-4 ${
          current > 0 ? 'bg-orange-100 text-orange-600 ring-orange-200/40' : 'bg-slate-100 text-slate-400 ring-slate-200/40'
        }`}>
          <Flame className="w-5 h-5" fill={current > 0 ? 'currentColor' : 'none'} />
        </div>
        <div className="min-w-0">
          <div className="dash-stat-label">Learning streak</div>
          <div className="dash-stat-value mt-1">{current} day{current === 1 ? '' : 's'}</div>
          <p className="text-xs text-slate-500 mt-0.5">Longest: {longest} day{longest === 1 ? '' : 's'}</p>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between gap-1.5" aria-label="Last 7 days activity">
        {days.map((d, i) => (
          <div key={d.date} className="flex flex-col items-center gap-1">
            <span className="text-[9px] text-slate-400">{DAY_LABELS[new Date(d.date + 'T00:00:00Z').getUTCDay()]}</span>
            <span
              className={`w-2.5 h-2.5 rounded-full ${d.active ? 'bg-orange-500' : 'bg-slate-200'}`}
              title={d.date}
              data-testid={`streak-dot-${i}`}
              data-active={d.active}
            />
          </div>
        ))}
      </div>
    </motion.div>
  )
}

export default StreakCard
