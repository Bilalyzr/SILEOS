/**
 * Virtual labs + admin content libraries client (2026-09-05).
 * Mirrors backend/app/routers/virtual_labs.py and content_library_admin.py.
 * Every path here is declared WITHOUT a trailing slash on the backend.
 */
import { api } from './axios'
import type { ConceptConfig } from './lab-studio'

export type LabProvider = 'phet' | 'embed' | 'native'
export type LabTemplate = 'reaction_lab' | 'identify_lab' | 'concept_lab'

export interface ReactionSpecies { formula: string; name: string }
export interface Reaction {
  reactants: ReactionSpecies[]
  products: ReactionSpecies[]
  coefficients: number[]
  hint?: string | null
  description?: string | null
}
export interface ReactionLabConfig { reactions: Reaction[]; intro?: string | null }

export interface Hotspot { id: string; label: string; x: number; y: number; description?: string | null }
export interface IdentifyLabConfig { diagram: string; hotspots: Hotspot[]; intro?: string | null }

export interface LabSummary {
  chapter_ids?: string[]
  grades?: number[]
  slug: string
  /** legacy alias of slug kept for older pickers */
  sim: string
  title: string
  subject: string
  provider: LabProvider
  embed_url: string | null
  source: string
  attribution?: string | null
  description?: string | null
  native_template?: LabTemplate | null
  thumbnail_url?: string | null
  max_score?: number
  is_builtin?: boolean
  is_published?: boolean
  catalog_id?: number
}

export interface LabDetail extends LabSummary {
  revision?: string
  config?: ReactionLabConfig | IdentifyLabConfig | ConceptConfig | null
  best_score?: number | null
}

export async function listLabs(subject?: string): Promise<LabSummary[]> {
  const { data } = await api.get<{ labs: LabSummary[] }>('/virtual-labs', { params: subject ? { subject } : undefined })
  return data.labs
}

export async function getLab(slug: string): Promise<LabDetail> {
  const { data } = await api.get<LabDetail>(`/virtual-labs/${encodeURIComponent(slug)}`)
  return data
}

export async function submitLabResult(slug: string, score: number, duration_s: number) {
  const { data } = await api.post<{ id: number; score: number; max_score: number; best_score: number }>(
    `/virtual-labs/${encodeURIComponent(slug)}/results`,
    { score, duration_s },
  )
  return data
}

// ---------------------------------------------------------------- admin

export interface LabCatalogEntryIn {
  slug: string
  title: string
  subject: string
  description?: string | null
  provider: LabProvider
  embed_url?: string | null
  native_template?: LabTemplate | null
  config?: Record<string, unknown> | null
  attribution?: string | null
  thumbnail_url?: string | null
  is_published: boolean
}

export interface AdminLabRow extends LabCatalogEntryIn {
  catalog_id: number
  config?: any
}

export interface BuiltinLabRow { slug: string; title: string; subject: string; provider: LabProvider; overridden: boolean }

const ADMIN = '/admin/content-library'

export const contentLibraryAdmin = {
  listLabs: async () => (await api.get<{ labs: AdminLabRow[]; builtin: BuiltinLabRow[] }>(`${ADMIN}/labs`)).data,
  createLab: async (entry: LabCatalogEntryIn) => (await api.post<AdminLabRow>(`${ADMIN}/labs`, entry)).data,
  updateLab: async (id: number, entry: LabCatalogEntryIn) => (await api.put<AdminLabRow>(`${ADMIN}/labs/${id}`, entry)).data,
  deleteLab: async (id: number) => (await api.delete(`${ADMIN}/labs/${id}`)).data,
  importLabs: async (labs: LabCatalogEntryIn[]) =>
    (await api.post<{ created: number; updated: number; slugs: string[] }>(`${ADMIN}/labs/import`, { labs })).data,

  listPrebuiltGames: async () =>
    (await api.get<{ games: { id: number; title: string; template: string; status: string; item_count: number; max_score: number; is_listed: boolean }[] }>(`${ADMIN}/games`)).data,
  importGames: async (games: { title: string; template: string; config: Record<string, unknown> }[]) =>
    (await api.post<{ created: { id: number; title: string }[]; skipped: { id: number; title: string }[] }>(`${ADMIN}/games/import`, { games })).data,
  importDefaultGames: async () =>
    (await api.post<{ created: { id: number; title: string }[]; skipped: { id: number; title: string }[] }>(`${ADMIN}/games/import-defaults`)).data,

  listLibraryModels: async () =>
    (await api.get<{ models: LibraryModel[] }>(`${ADMIN}/three-d`)).data,
  importModels: async (files: File[]) => {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    // The axios interceptor strips Content-Type for FormData bodies — never set it here.
    return (await api.post<{ models: LibraryModel[] }>(`${ADMIN}/three-d/import`, form)).data
  },
  patchModel: async (id: number, patch: { is_library?: boolean; title?: string }) =>
    (await api.patch<LibraryModel>(`${ADMIN}/three-d/${id}`, patch)).data,
  deleteModel: async (id: number) => (await api.delete(`${ADMIN}/three-d/${id}`)).data,
}

export interface LibraryModel {
  id: number
  title: string
  format: string
  file_size_bytes: number
  created_at: string
  owner_id: number
  is_library: boolean
}
