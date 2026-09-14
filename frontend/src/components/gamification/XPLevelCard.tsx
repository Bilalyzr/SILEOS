/**
 * XPLevelCard — dashboard stat card for XP/level (plan Task 10, spec D6).
 *
 * Shows the current level as a number inside an SVG progress ring (stroke-
 * dasharray, matching the fraction to the next level from
 * GET /api/v1/gamification/me's level_progress() shape) plus current/needed
 * XP text. Tone-matched to the dashboard StatCard family (components/
 * dashboard/primitives.tsx) rather than reusing StatCard directly, since the
 * ring replaces StatCard's icon+count-up layout.
 */
import * as React from 'react'
import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import { fadeUp, TONE_HEX, type StatTone } from '@/components/dashboard/primitives'
import type { GamificationStats } from '@/api/gamification'

/** Pure helper — exported for vitest. Clamps to [0, 1]; NaN and +Infinity
 * are treated as fully filled, matching the backend's own `1.0` fallback in
 * level_progress() for the span===0 case. -Infinity clamps to 0 like any
 * other out-of-range value (checked before the general non-finite case so
 * it doesn't fall into the "fully filled" branch). */
export function clampProgressFraction(fraction: number): number {
  if (fraction === -Infinity) return 0
  if (!Number.isFinite(fraction)) return 1
  if (fraction < 0) return 0
  if (fraction > 1) return 1
  return fraction
}

export interface XPLevelCardProps {
  stats: GamificationStats | null | undefined
  tone?: StatTone
  className?: string
}

const RADIUS = 30
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export const XPLevelCard: React.FC<XPLevelCardProps> = ({ stats, tone = 'purple', className = '' }) => {
  const color = TONE_HEX[tone]
  const level = stats?.level ?? 0
  const fraction = clampProgressFraction(stats?.progress_fraction ?? 0)
  const xpInto = stats?.xp_into_level ?? 0
  const xpToNext = stats?.xp_to_next_level ?? 0
  const totalXp = stats?.total_xp ?? 0
  const dashOffset = CIRCUMFERENCE * (1 - fraction)

  return (
    <motion.div variants={fadeUp} className={`dash-card p-5 h-full ${className}`}>
      <div className="flex items-center gap-4">
        <div className="relative w-20 h-20 flex-shrink-0" role="img" aria-label={`Level ${level}, ${Math.round(fraction * 100)}% to next level`}>
          <svg viewBox="0 0 72 72" className="w-20 h-20 -rotate-90">
            <circle cx="36" cy="36" r={RADIUS} fill="none" stroke="currentColor" className="text-slate-100" strokeWidth="7" />
            <circle
              cx="36" cy="36" r={RADIUS} fill="none"
              stroke={color}
              strokeWidth="7"
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={dashOffset}
              style={{ transition: 'stroke-dashoffset 0.6s cubic-bezier(0.16,1,0.3,1)' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl font-bold text-secondary-900 leading-none">{level}</span>
            <span className="text-[9px] uppercase tracking-wide text-slate-500 mt-0.5">Level</span>
          </div>
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 dash-stat-label">
            <Sparkles className="w-3.5 h-3.5" style={{ color }} />
            Experience
          </div>
          <div className="dash-stat-value mt-1">{totalXp.toLocaleString()} XP</div>
          <p className="text-xs text-slate-500 mt-1">
            {xpToNext > 0
              ? `${xpInto.toLocaleString()} / ${(xpInto + xpToNext).toLocaleString()} XP to level ${level + 1}`
              : 'Max level reached'}
          </p>
        </div>
      </div>
    </motion.div>
  )
}

export default XPLevelCard
