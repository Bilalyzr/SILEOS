/**
 * ScorableItem contract client (v2.0 §5) — mirrors backend/app/schemas/scorable.py.
 * Items live on quiz.interactive_modules; the registry endpoint lists what the
 * instructor may insert, with derived max_score and default tier floor.
 */
import { api } from './axios'

export type ScorableKind = 'h5p' | 'game' | 'lab' | 'three_d_task'
export type Tier = 'T0' | 'T1' | 'T2' | 'T3' | 'T4' | 'T5' | 'T6' | 'T7'
export type GradingMode = 'auto' | 'auto_with_review' | 'manual'

export const TIERS: Tier[] = ['T0', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7']
export const GRADEABLE_FLOOR: Tier = 'T4'
export const TIER_LABELS: Record<Tier, string> = {
  T0: 'T0 · XR headset',
  T1: 'T1 · full 3D',
  T2: 'T2 · lite 3D',
  T3: 'T3 · turntable video',
  T4: 'T4 · still images (any phone)',
  T5: 'T5 · text / audio',
  T6: 'T6 · offline',
  T7: 'T7 · SMS',
}

export interface ScorableItem {
  kind: ScorableKind
  id: number | string
  title: string
  max_score: number
  weight: number
  attempts_allowed: number
  grading_mode: GradingMode
  practice_only: boolean
  tier_floor: Tier
  /** H5P only — what the player needs */
  public_id?: string | null
}

export interface RegistryEntry {
  kind: ScorableKind
  id: number | string
  title: string
  max_score: number
  tier_floor: Tier
  bucket: 'games_h5p' | 'three_d_tasks'
  source?: 'mine' | 'marketplace'
  template?: string
  subject?: string
  public_id?: string | null
}

export function tierRank(t: Tier): number {
  return TIERS.indexOf(t)
}

/** True when a graded item cannot be published (floor better than T4). */
export function blocksPublication(item: Pick<ScorableItem, 'tier_floor' | 'practice_only'>): boolean {
  return !item.practice_only && tierRank(item.tier_floor) < tierRank(GRADEABLE_FLOOR)
}

export function defaultsFor(entry: RegistryEntry): ScorableItem {
  return {
    kind: entry.kind,
    id: entry.id,
    title: entry.title,
    max_score: entry.max_score,
    weight: 1,
    attempts_allowed: 0,
    grading_mode: 'auto',
    practice_only: false,
    tier_floor: entry.tier_floor,
    public_id: entry.public_id ?? null,
  }
}

/** Fill defaults for legacy `{kind,id,title}` entries so the editor never shows blanks. */
export function normalizeItem(raw: Partial<ScorableItem> & { kind: ScorableKind; id: number | string }, registry: RegistryEntry[] = []): ScorableItem {
  const entry = registry.find((e) => e.kind === raw.kind && String(e.id) === String(raw.id))
  return {
    kind: raw.kind,
    id: raw.id,
    title: raw.title || entry?.title || `${raw.kind} ${raw.id}`,
    max_score: raw.max_score ?? entry?.max_score ?? 0,
    weight: raw.weight ?? 1,
    attempts_allowed: raw.attempts_allowed ?? 0,
    grading_mode: raw.grading_mode ?? 'auto',
    practice_only: raw.practice_only ?? false,
    tier_floor: raw.tier_floor ?? entry?.tier_floor ?? 'T4',
    public_id: raw.public_id ?? entry?.public_id ?? null,
  }
}

export async function listScorableItems(): Promise<{ items: RegistryEntry[]; tiers: Tier[]; gradeable_floor: Tier }> {
  const { data } = await api.get('/scorable-items')
  return data
}
