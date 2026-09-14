/**
 * GeoGebra applets API client — mirrors backend/app/routers/geogebra.py.
 * LICENCE: GeoGebra Apps are free for non-commercial use; resolve the
 * commercial agreement with GeoGebra GmbH before selling paid seats.
 */
import { api } from './axios'

export const GEOGEBRA_APP_TYPES = [
  { value: 'graphing', label: 'Graphing calculator' },
  { value: 'geometry', label: 'Geometry' },
  { value: 'classic', label: 'Classic (all tools)' },
  { value: '3d', label: '3D calculator' },
  { value: 'cas', label: 'CAS (symbolic)' },
] as const

export interface GeoGebraApplet {
  id: number
  title: string
  app_type: string
  material_id: string | null
  config: Record<string, unknown>
  has_saved_state: boolean
  created_at: string
  updated_at: string
}

export interface AppletEmbed extends GeoGebraApplet {
  applet_parameters: Record<string, unknown>
}

export const geogebraAPI = {
  create: async (payload: { title: string; app_type?: string; material_id?: string; config?: Record<string, unknown> }) => {
    const { data } = await api.post<GeoGebraApplet>('/geogebra/applets', payload)
    return data
  },
  list: async () => {
    const { data } = await api.get<{ applets: GeoGebraApplet[] }>('/geogebra/applets')
    return data
  },
  update: async (id: number, payload: Record<string, unknown>) => {
    const { data } = await api.put<GeoGebraApplet>(`/geogebra/applets/${id}`, payload)
    return data
  },
  remove: async (id: number) => {
    const { data } = await api.delete(`/geogebra/applets/${id}`)
    return data
  },
  embed: async (id: number) => {
    const { data } = await api.get<AppletEmbed>(`/geogebra/applets/${id}/embed`)
    return data
  },
}
