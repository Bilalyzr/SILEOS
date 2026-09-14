/**
 * Gamification API client (plan Task 10, spec D7) — typed wrapper around
 * /api/v1/gamification/* (see backend/app/routers/gamification.py).
 *
 * Shapes here are read directly off the router's response dicts, not
 * guessed — see _stats_out/_badge_out/_event_out and the leaderboard/
 * user_rank service functions in backend/app/services/gamification_service.py.
 */
import { api, apiRequest } from './axios'

export interface GamificationStats {
  total_xp: number
  current_streak: number
  longest_streak: number
  last_active_date: string | null
  leaderboard_visible: boolean
  badges_count: number
  // level_progress() fields, spread into the stats object server-side.
  level: number
  current_level_floor_xp: number
  next_level_xp: number
  xp_into_level: number
  xp_to_next_level: number
  progress_fraction: number
}

export interface GamificationBadge {
  slug: string
  name: string
  description: string
  /** lucide-react icon name (kebab-case, e.g. "graduation-cap"). */
  icon: string
  /** ISO datetime the badge was earned, present only on earned badges. */
  awarded_at: string | null
}

export interface GamificationEvent {
  id: number
  event_type: string
  points: number
  course_id: number | null
  meta: Record<string, unknown>
  created_at: string | null
}

export interface GamificationMeResponse {
  stats: GamificationStats
  badges: GamificationBadge[]
  recent_events: GamificationEvent[]
}

export interface UnseenAwardsResponse {
  unseen: GamificationEvent[]
}

export interface LeaderboardEntry {
  rank: number
  user_id: number
  display_name: string
  level: number
  total_xp: number
}

export interface MyRank {
  rank: number
  total_xp: number
  level: number
}

export interface LeaderboardResponse {
  scope: string
  entries: LeaderboardEntry[]
  my_rank: MyRank | null
}

export type LeaderboardScope = 'global' | `course:${number}`

export const gamificationAPI = {
  /** Stats + level progress + earned badges + recent XP events. */
  getMe: async (): Promise<GamificationMeResponse> => {
    return apiRequest(api.get('/gamification/me'))
  },

  /** Badge/level-up/streak-milestone events not yet acknowledged by the client. */
  getUnseen: async (): Promise<UnseenAwardsResponse> => {
    return apiRequest(api.get('/gamification/me/unseen'))
  },

  /** Marks the given XpEvent ids as seen (meta.seen -> true). */
  markSeen: async (eventIds: number[]): Promise<{ updated: number }> => {
    return apiRequest(api.post('/gamification/me/unseen/mark-seen', { event_ids: eventIds }))
  },

  /** scope: 'global' or 'course:{id}'. */
  getLeaderboard: async (scope: LeaderboardScope = 'global'): Promise<LeaderboardResponse> => {
    return apiRequest(api.get('/gamification/leaderboard', { params: { scope } }))
  },

  updateSettings: async (leaderboardVisible: boolean): Promise<GamificationStats> => {
    return apiRequest(api.post('/gamification/me/settings', { leaderboard_visible: leaderboardVisible }))
  },
}

export default gamificationAPI
