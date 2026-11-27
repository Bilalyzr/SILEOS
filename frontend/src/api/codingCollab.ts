import { api } from './axios'
import type { CodingLanguage } from './coding'

export interface CollabMember {
  user_id: number
  name: string
  is_owner: boolean
}

export interface CollabRoom {
  id: number
  challenge_slug: string
  challenge_title: string
  language: CodingLanguage
  invite_code: string
  is_owner: boolean
  members: CollabMember[]
  max_members: number
}

export const codingCollabAPI = {
  create: async (slug: string, language?: CodingLanguage) =>
    (await api.post<CollabRoom>(`/utporul/coding/challenges/${slug}/collab-rooms`, language ? { language } : {})).data,
  join: async (code: string) =>
    (await api.post<CollabRoom>('/utporul/coding/collab-rooms/join', { code })).data,
  get: async (roomId: number) =>
    (await api.get<CollabRoom>(`/utporul/coding/collab-rooms/${roomId}`)).data,
  ticket: async (roomId: number) =>
    (await api.post<{ ticket: string; expires_in: number }>(`/utporul/coding/collab-rooms/${roomId}/ticket`)).data,
}
