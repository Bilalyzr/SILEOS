/**
 * LeaderboardTable — rank/name/level/XP rows (plan Task 10, spec D5/D6).
 *
 * Entries come from GET /api/v1/gamification/leaderboard — display_name +
 * level + XP only (the backend never leaks email, see gamification.py's
 * module docstring). The caller's own row is highlighted when present in
 * `entries`; when the caller is outside the top-N, `myRank` (the same
 * response's `my_rank`) renders as a footer row instead.
 */
import * as React from 'react'
import { Crown, Medal } from 'lucide-react'
import type { LeaderboardEntry, MyRank } from '@/api/gamification'

export interface LeaderboardTableProps {
  entries: LeaderboardEntry[]
  myRank?: MyRank | null
  /** Current user's id, to highlight their own row when present in `entries`. */
  currentUserId?: number | null
  className?: string
}

function rankBadge(rank: number) {
  if (rank === 1) return <Crown className="w-4 h-4 text-amber-500" aria-label="Rank 1" />
  if (rank === 2) return <Medal className="w-4 h-4 text-slate-400" aria-label="Rank 2" />
  if (rank === 3) return <Medal className="w-4 h-4 text-orange-400" aria-label="Rank 3" />
  return <span className="text-sm font-semibold text-slate-500">#{rank}</span>
}

export const LeaderboardTable: React.FC<LeaderboardTableProps> = ({
  entries, myRank, currentUserId, className = '',
}) => {
  const selfInList = currentUserId != null && entries.some((e) => e.user_id === currentUserId)

  if (entries.length === 0) {
    return (
      <div className={`text-center py-10 text-sm text-slate-500 ${className}`}>
        No leaderboard entries yet — be the first to earn XP here.
      </div>
    )
  }

  return (
    <div className={className}>
      <table className="w-full text-sm" role="table">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-wide text-slate-400 border-b border-slate-100">
            <th className="py-2 pr-2 w-12">Rank</th>
            <th className="py-2 pr-2">Student</th>
            <th className="py-2 pr-2 text-right">Level</th>
            <th className="py-2 pl-2 text-right">XP</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => {
            const isSelf = currentUserId != null && entry.user_id === currentUserId
            return (
              <tr
                key={entry.user_id}
                data-testid={`leaderboard-row-${entry.user_id}`}
                data-self={isSelf}
                className={`border-b border-slate-50 last:border-b-0 ${isSelf ? 'bg-orange-50/70 font-semibold' : ''}`}
              >
                <td className="py-2.5 pr-2">{rankBadge(entry.rank)}</td>
                <td className="py-2.5 pr-2 text-secondary-900 truncate max-w-[220px]">
                  {entry.display_name}
                  {isSelf && <span className="ml-1.5 text-[10px] text-orange-600 font-semibold">(you)</span>}
                </td>
                <td className="py-2.5 pr-2 text-right text-slate-600">{entry.level}</td>
                <td className="py-2.5 pl-2 text-right font-semibold text-secondary-900">{entry.total_xp.toLocaleString()}</td>
              </tr>
            )
          })}
        </tbody>
      </table>

      {myRank && !selfInList && (
        <div
          data-testid="leaderboard-my-rank-footer"
          className="mt-3 pt-3 border-t border-dashed border-slate-200 flex items-center justify-between text-sm bg-orange-50/50 -mx-2 px-2 py-2 rounded-lg"
        >
          <span className="font-semibold text-secondary-900">
            #{myRank.rank} <span className="text-slate-500 font-normal">(you)</span>
          </span>
          <span className="flex items-center gap-4 text-slate-600">
            <span>Level {myRank.level}</span>
            <span className="font-semibold text-secondary-900">{myRank.total_xp.toLocaleString()} XP</span>
          </span>
        </div>
      )}
    </div>
  )
}

export default LeaderboardTable
