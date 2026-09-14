/**
 * BadgeGrid — earned + unearned badges (plan Task 10, spec D3/D6).
 *
 * GET /api/v1/gamification/me only returns EARNED badges (see
 * backend/app/routers/gamification.py's `_badge_out` / `get_my_gamification`
 * — there is no "list all badges" endpoint). To show the full catalog with
 * unearned badges grayed out + a rule hint, this component mirrors the
 * static seed catalog (backend/app/services/gamification_service.py's
 * BADGE_CATALOG — ~15 rows, slug/name/description/icon, seeded once at
 * startup and stable) as BADGE_CATALOG below, then merges in earned_at from
 * the `/me` response by slug. If the backend catalog ever changes, update
 * both lists together (documented in docs/LEARNING_EXPERIENCE.md).
 */
import * as React from 'react'
import * as LucideIcons from 'lucide-react'
import { Award as AwardIcon, type LucideIcon } from 'lucide-react'
import type { GamificationBadge } from '@/api/gamification'

export interface BadgeCatalogEntry {
  slug: string
  name: string
  description: string
  icon: string
}

/** Mirror of backend/app/services/gamification_service.py's BADGE_CATALOG —
 * see the module docstring above for why this can't just come from the API. */
export const BADGE_CATALOG: BadgeCatalogEntry[] = [
  { slug: 'first-lesson', name: 'First Steps', description: 'Complete your first lesson.', icon: 'footprints' },
  { slug: 'course-finisher', name: 'Course Finisher', description: 'Complete your first course.', icon: 'graduation-cap' },
  { slug: 'three-courses', name: 'Triple Threat', description: 'Complete 3 courses.', icon: 'trophy' },
  { slug: 'quiz-ace', name: 'Quiz Ace', description: 'Score 90%+ on 5 quizzes.', icon: 'target' },
  { slug: 'streak-7', name: 'Week Warrior', description: 'Reach a 7-day streak.', icon: 'flame' },
  { slug: 'streak-30', name: 'Month Master', description: 'Reach a 30-day streak.', icon: 'flame' },
  { slug: 'streak-100', name: 'Century Streak', description: 'Reach a 100-day streak.', icon: 'flame' },
  { slug: 'early-bird', name: 'Early Bird', description: 'Complete an activity before 7am.', icon: 'sunrise' },
  { slug: 'night-owl', name: 'Night Owl', description: 'Complete an activity after 10pm.', icon: 'moon' },
  { slug: 'live-regular', name: 'Live Regular', description: 'Attend 5 live classes.', icon: 'video' },
  { slug: 'h5p-explorer', name: 'H5P Explorer', description: 'Complete an interactive H5P activity.', icon: 'puzzle' },
  { slug: 'assignment-perfect', name: 'Perfectionist', description: 'Score a perfect grade on an assignment.', icon: 'star' },
  { slug: 'xp-level-5', name: 'Rising Star', description: 'Reach level 5.', icon: 'sparkles' },
  { slug: 'xp-level-10', name: 'XP Legend', description: 'Reach level 10.', icon: 'crown' },
  { slug: 'five-lessons', name: 'Getting Momentum', description: 'Complete 5 lessons.', icon: 'footprints' },
]

/** kebab-case badge icon name -> PascalCase lucide-react export name. */
function iconNameToComponent(icon: string): LucideIcon {
  const pascal = icon
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join('')
  const Comp = (LucideIcons as unknown as Record<string, LucideIcon>)[pascal]
  return Comp || AwardIcon
}

export interface BadgeGridEntry extends BadgeCatalogEntry {
  earned: boolean
  awardedAt: string | null
}

/** Pure helper — exported for vitest. Merges the static catalog with the
 * earned-badges list from GET /me into a single earned/unearned split. */
export function mergeBadges(earned: GamificationBadge[]): BadgeGridEntry[] {
  const earnedBySlug = new Map(earned.map((b) => [b.slug, b]))
  return BADGE_CATALOG.map((def) => {
    const e = earnedBySlug.get(def.slug)
    return {
      ...def,
      // Prefer the live name/description/icon from the API when present
      // (e.g. an admin-edited badge row) — falls back to the static mirror.
      name: e?.name ?? def.name,
      description: e?.description ?? def.description,
      icon: e?.icon ?? def.icon,
      earned: Boolean(e),
      awardedAt: e?.awarded_at ?? null,
    }
  })
}

export interface BadgeGridProps {
  badges: GamificationBadge[]
  className?: string
}

export const BadgeGrid: React.FC<BadgeGridProps> = ({ badges, className = '' }) => {
  const merged = React.useMemo(() => mergeBadges(badges), [badges])
  const earnedCount = merged.filter((b) => b.earned).length

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-500">{earnedCount} / {merged.length} earned</span>
      </div>
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
        {merged.map((badge) => {
          const Icon = iconNameToComponent(badge.icon)
          return (
            <div
              key={badge.slug}
              data-testid={`badge-${badge.slug}`}
              data-earned={badge.earned}
              title={badge.earned ? badge.description : `Locked — ${badge.description}`}
              className={`flex flex-col items-center text-center gap-1.5 p-3 rounded-xl border transition ${
                badge.earned
                  ? 'border-amber-200 bg-amber-50/60'
                  : 'border-slate-200 bg-slate-50/40 opacity-50 grayscale'
              }`}
            >
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                badge.earned ? 'bg-amber-100 text-amber-600' : 'bg-slate-200 text-slate-400'
              }`}>
                <Icon className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-semibold text-secondary-900 leading-tight">{badge.name}</span>
              {badge.earned ? (
                badge.awardedAt && (
                  <span className="text-[9px] text-slate-500">
                    {new Date(badge.awardedAt).toLocaleDateString()}
                  </span>
                )
              ) : (
                <span className="text-[9px] text-slate-400 leading-tight">{badge.description}</span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default BadgeGrid
