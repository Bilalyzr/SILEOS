/**
 * Digital Library API client — mirrors backend/app/routers/library.py.
 * file_path/sample_path never leave the server; only has_file/has_sample
 * booleans do. Downloads stream through the authenticated axios instance
 * as blobs (never a raw URL — the endpoints require the Authorization
 * header and must not be cached by the browser).
 */
import { api } from './axios'

export interface Ebook {
  id: number
  owner_id: number
  slug: string
  title: string
  description: string
  category: 'book' | 'guide' | 'lecture_notes'
  price_inr: number
  discount_price_inr: number | null
  effective_price_inr: number
  cover_image: string
  page_count: number | null
  concept_tags: string[]
  course_id: number | null
  course_title?: string | null
  status: 'draft' | 'published'
  has_file: boolean
  has_sample: boolean
  file_size_bytes: number
  created_at: string
  updated_at: string
  // detail/my-library extras
  owned?: boolean
  granted_at?: string
  downloadable?: boolean
  sales_count?: number
}

export const EBOOK_CATEGORY_LABELS: Record<string, string> = {
  book: 'Books',
  guide: 'Guides',
  lecture_notes: 'Lecture Notes',
}

export const libraryAPI = {
  listPublished: async (params?: { category?: string; q?: string; course_id?: number; tag?: string }) => {
    const { data } = await api.get<{ ebooks: Ebook[]; count: number }>('/library', { params })
    return data
  },

  detail: async (slug: string) => {
    const { data } = await api.get<Ebook>(`/library/${slug}`)
    return data
  },

  myLibrary: async () => {
    const { data } = await api.get<{ items: Ebook[]; count: number }>('/library/me')
    return data
  },

  mine: async (limit = 100) => {
    const { data } = await api.get<{ ebooks: Ebook[]; count: number; total: number }>('/library/mine', { params: { limit } })
    return data
  },

  create: async (payload: Partial<Ebook>) => {
    const { data } = await api.post<Ebook>('/library', payload)
    return data
  },

  update: async (id: number, payload: Record<string, unknown>) => {
    const { data } = await api.put<Ebook>(`/library/${id}`, payload)
    return data
  },

  uploadFile: async (id: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post<Ebook>(`/library/${id}/file`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  uploadSample: async (id: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post<Ebook>(`/library/${id}/sample`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  publish: async (id: number) => {
    const { data } = await api.post<Ebook>(`/library/${id}/publish`)
    return data
  },

  unpublish: async (id: number) => {
    const { data } = await api.post<Ebook>(`/library/${id}/unpublish`)
    return data
  },

  remove: async (id: number) => {
    const { data } = await api.delete<{ deleted: boolean }>(`/library/${id}`)
    return data
  },

  sales: async (id: number) => {
    const { data } = await api.get(`/library/${id}/sales`)
    return data
  },

  /** Authenticated blob download — the endpoint 403s without the header. */
  download: async (id: number): Promise<void> => {
    const res = await api.get(`/library/${id}/download`, { responseType: 'blob' })
    triggerBlobDownload(res.data as Blob, filenameFromResponse(res.headers) ?? `ebook-${id}.pdf`)
  },

  downloadSample: async (id: number): Promise<void> => {
    const res = await api.get(`/library/${id}/sample`, { responseType: 'blob' })
    triggerBlobDownload(res.data as Blob, filenameFromResponse(res.headers) ?? `sample-${id}.pdf`)
  },

  /** Free ebooks claim directly (no payment order); paid ones go through
   *  payments create-order with ebook_id (same boundary as courses). */
  buy: async (ebook: Pick<Ebook, 'id' | 'effective_price_inr'>) => {
    if (ebook.effective_price_inr === 0) {
      const { data } = await api.post(`/library/${ebook.id}/claim`)
      return { granted: true, ...(data as object) } as { granted: boolean; [k: string]: unknown }
    }
    const { data } = await api.post('/payments/create-order', { ebook_id: ebook.id })
    return data as { order_id?: string; amount?: number; granted?: boolean; requires_payment?: boolean; [k: string]: unknown }
  },
}

function filenameFromResponse(headers: Record<string, unknown>): string | null {
  const cd = (headers['content-disposition'] ?? headers['Content-Disposition']) as string | undefined
  if (!cd) return null
  const m = cd.match(/filename="?([^";]+)"?/)
  return m?.[1] ?? null
}

function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
