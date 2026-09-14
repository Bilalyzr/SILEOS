/**
 * Learning Games API client — typed wrapper around /api/v1/games/*
 * (backend/app/routers/games.py). '/games' is in axios.ts's
 * noSlashEndpoints: the backend runs redirect_slashes=False and no games
 * route declares a trailing slash.
 */
import { api } from './axios'

export type GameTemplate =
  | 'quiz_rush'
  | 'match_pairs'
  | 'drag_sort'
  | 'word_builder'
  | 'sequence'

export type GameStatus = 'draft' | 'published'

export interface QuizRushConfig {
  items: { prompt: string; options: string[]; answer_index: number }[]
  settings: { seconds_per_question: number; shuffle: boolean }
}
export interface MatchPairsConfig {
  items: { left: string; right: string }[]
  settings: { time_limit_s: number }
}
export interface DragSortConfig {
  categories: { name: string }[]
  items: { text: string; category_index: number }[]
  settings: { time_limit_s: number }
}
export interface WordBuilderConfig {
  items: { clue: string; answer: string }[]
  settings: { hints_allowed: number }
}
export interface SequenceConfig {
  items: { text: string }[]
  settings: { time_limit_s: number; shuffle: true }
}
export type GameConfig =
  | QuizRushConfig
  | MatchPairsConfig
  | DragSortConfig
  | WordBuilderConfig
  | SequenceConfig

/**
 * The backend config JSON is validated with `extra="forbid"` at every
 * nesting level (see Global Constraint 1), so it can never carry a
 * `template` tag of its own — the tag lives only on the OUTER row. A
 * `Game { template: GameTemplate; config: GameConfig }` shape (union on
 * the inner field, tag on the same field as everything else) does NOT
 * narrow: TS can't correlate `game.template` with `game.config`'s member
 * without a cast. Tagging the union on the OUTER type instead — one
 * variant per template, each pairing the literal `template` with its own
 * config type — lets `game.template === 'quiz_rush'` narrow
 * `game.config` to `QuizRushConfig` with zero casts.
 */
interface GameBase {
  id: number
  owner_id: number
  title: string
  status: GameStatus
  item_count: number
  max_score: number
  created_at: string
  updated_at: string
}

export type Game = GameBase &
  (
    | { template: 'quiz_rush'; config: QuizRushConfig }
    | { template: 'match_pairs'; config: MatchPairsConfig }
    | { template: 'drag_sort'; config: DragSortConfig }
    | { template: 'word_builder'; config: WordBuilderConfig }
    | { template: 'sequence'; config: SequenceConfig }
  )

/** GET /games/mine row (no config). */
export interface GameSummary {
  id: number
  owner_id: number
  title: string
  template: GameTemplate
  status: GameStatus
  item_count: number
  max_score: number
  attached_lesson_count: number
  created_at: string
  updated_at: string
}

interface GamePlayPayloadBase {
  id: number
  title: string
  max_score: number
  preview: boolean
}

export type GamePlayPayload = GamePlayPayloadBase &
  (
    | { template: 'quiz_rush'; config: QuizRushConfig }
    | { template: 'match_pairs'; config: MatchPairsConfig }
    | { template: 'drag_sort'; config: DragSortConfig }
    | { template: 'word_builder'; config: WordBuilderConfig }
    | { template: 'sequence'; config: SequenceConfig }
  )

export interface SubmitGameResultPayload {
  score: number
  max_score: number
  duration_s: number
}

export interface GameResultResponse {
  game_id: number
  user_id: number
  score: number
  max_score: number
  duration_s: number
  best_score: number
  created_at: string
}

/** Rollup row returned by GET /games/{id}/results (owner/admin). */
export interface RollupRow {
  user_id: number
  user_name: string
  best_score: number
  max_score: number
  attempts: number
  last_played: string
}

export async function listMyGames(): Promise<{ games: GameSummary[]; count: number }> {
  const response = await api.get<{ games: GameSummary[]; count: number }>('/games/mine')
  return response.data
}

export async function getGame(gameId: number): Promise<Game> {
  const response = await api.get<Game>(`/games/${gameId}`)
  return response.data
}

export async function createGame(payload: {
  title: string
  template: GameTemplate
  config: GameConfig
}): Promise<Game> {
  const response = await api.post<Game>('/games', payload)
  return response.data
}

export async function updateGame(
  gameId: number,
  payload: { title?: string; config?: GameConfig }
): Promise<Game> {
  const response = await api.put<Game>(`/games/${gameId}`, payload)
  return response.data
}

export async function publishGame(gameId: number): Promise<Game> {
  const response = await api.post<Game>(`/games/${gameId}/publish`)
  return response.data
}

export async function unpublishGame(gameId: number): Promise<Game> {
  const response = await api.post<Game>(`/games/${gameId}/unpublish`)
  return response.data
}

export async function deleteGame(gameId: number): Promise<{ success: boolean; id: number }> {
  const response = await api.delete<{ success: boolean; id: number }>(`/games/${gameId}`)
  return response.data
}

export async function getGamePlay(gameId: number): Promise<GamePlayPayload> {
  const response = await api.get<GamePlayPayload>(`/games/${gameId}/play`)
  return response.data
}

/** Alias for getGamePlay — matches the plan's function-name list verbatim. */
export const getPlayPayload = getGamePlay

/** Owner/admin preview POSTs come back as {preview: true} with nothing written. */
export async function submitGameResult(
  gameId: number,
  payload: SubmitGameResultPayload
): Promise<GameResultResponse | { preview: true }> {
  const response = await api.post<GameResultResponse | { preview: true }>(
    `/games/${gameId}/results`,
    payload
  )
  return response.data
}

export async function listGameResults(
  gameId: number
): Promise<{ game_id: number; results: RollupRow[]; count: number }> {
  const response = await api.get<{ game_id: number; results: RollupRow[]; count: number }>(
    `/games/${gameId}/results`
  )
  return response.data
}

/** Alias for listGameResults — matches the plan's function-name list verbatim. */
export const getGameResults = listGameResults


export interface MarketplaceGame {
  id: number
  title: string
  template: string
  owner_id: number
  source: string
}

export async function listMarketplaceGames(): Promise<MarketplaceGame[]> {
  const { data } = await api.get('/games/marketplace')
  return data.games || []
}
