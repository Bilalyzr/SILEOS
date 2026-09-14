/**
 * Wall of Fame API client.
 *
 * Public list: GET /hall-of-fame/ (no auth)
 * Admin CRUD:  GET /hall-of-fame/admin, POST /, PUT /{id}, DELETE /{id}, PUT /reorder
 */
import { api } from './axios'

export interface HallOfFameMember {
  id: number
  name: string
  role: string
  company: string
  photo: string | null
  tenure: string
  location: string | null
  linkedin: string | null
  blurb: string | null
  highlight: string | null
  sort_order: number
  is_published: boolean
  created_at: string | null
  updated_at: string | null
}

export interface MemberInput {
  name: string
  role?: string
  company?: string
  photo?: string | null
  tenure?: string
  location?: string | null
  linkedin?: string | null
  blurb?: string | null
  highlight?: string | null
  sort_order?: number
  is_published?: boolean
}

export const hallOfFameApi = {
  /** Public: published members only. */
  async list(): Promise<HallOfFameMember[]> {
    const res = await api.get('/hall-of-fame/')
    return res.data
  },

  /** Admin: all members (incl. unpublished). */
  async listAll(): Promise<HallOfFameMember[]> {
    const res = await api.get('/hall-of-fame/admin')
    return res.data
  },

  async create(data: MemberInput): Promise<HallOfFameMember> {
    const res = await api.post('/hall-of-fame/', data)
    return res.data
  },

  async update(id: number, data: Partial<MemberInput>): Promise<HallOfFameMember> {
    const res = await api.put(`/hall-of-fame/${id}`, data)
    return res.data
  },

  async remove(id: number): Promise<void> {
    await api.delete(`/hall-of-fame/${id}`)
  },

  async reorder(items: { id: number; sort_order: number }[]): Promise<void> {
    await api.put('/hall-of-fame/reorder', { items })
  },
}

export default hallOfFameApi
