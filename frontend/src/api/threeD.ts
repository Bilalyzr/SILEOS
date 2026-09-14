/**
 * 3D model library client (Phase 2) — mirrors backend/app/routers/three_d.py.
 * GLB uploads are magic-byte validated server-side; files stream through
 * the authenticated axios instance as blobs (never public URLs).
 */
import { api } from './axios'

export interface ThreeDModel {
  id: number
  title: string
  format: string
  file_size_bytes: number
  created_at: string
  owner_id?: number
  is_library?: boolean
}

export const threeDAPI = {
  restoreLibrary: async () => (await api.post<{models: {model_id: number; title: string}[]}>('/three-d/models/restore-library')).data,
  upload: async (title: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post<ThreeDModel>(`/three-d/models?title=${encodeURIComponent(title)}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },
  list: async () => {
    // `library` = admin-shared models (content libraries, 2026-09-05)
    const { data } = await api.get<{ models: ThreeDModel[]; library: ThreeDModel[] }>('/three-d/models')
    return data
  },
  /** Pre-build T2/T3 GLBs on the server (gltf-transform). 503 when the tool is missing. */
  buildTiers: async (id: number) => (await api.post<{ model_id: number; tiers: Record<string, string>; sizes: Record<string, number> }>(`/three-d/models/${id}/build-tiers`)).data,
  remove: async (id: number) => {
    const { data } = await api.delete(`/three-d/models/${id}`)
    return data
  },
  /** Authenticated blob download for the viewer (three.js GLTFLoader). */
  downloadBytes: async (id: number, tier?: 'T2' | 'T3', onProgress?: (percent: number) => void): Promise<ArrayBuffer> => {
    const res = await api.get<ArrayBuffer>(`/three-d/models/${id}/file`, {
      responseType: 'arraybuffer', params: tier ? { tier } : undefined,
      onDownloadProgress: event => { if (event.total) onProgress?.(Math.min(99, Math.round(100 * event.loaded / event.total))) },
    })
    return res.data
  },
  downloadUrl: async (id: number, tier?: 'T2' | 'T3'): Promise<string> => {
    const res = await api.get(`/three-d/models/${id}/file`, { responseType: 'blob', params: tier ? { tier } : undefined })
    return URL.createObjectURL(res.data as Blob)
  },
}
