import { api } from '@/api/axios'

export interface AppNotification {
  id: number
  type: string
  title: string
  message: string
  link: string | null
  related_id: number | null
  is_read: boolean
  created_at: string
}

export const notificationsApi = {
  list: async (): Promise<{ unread_count: number; notifications: AppNotification[] }> =>
    (await api.get('/notifications/')).data,
  markRead: async (id: number) => (await api.patch(`/notifications/${id}/read`)).data,
  markAllRead: async () => (await api.post('/notifications/read-all')).data,
}
