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

export interface NotificationTopicPreference {
  topic: string
  label: string
  description: string
  in_app_enabled: boolean
  email_enabled: boolean
  push_enabled: boolean
  whatsapp_enabled: boolean
}

export type NotificationPreferencePatch = Partial<
  Pick<
    NotificationTopicPreference,
    'in_app_enabled' | 'email_enabled' | 'push_enabled' | 'whatsapp_enabled'
  >
>

export const notificationsApi = {
  list: async (): Promise<{ unread_count: number; notifications: AppNotification[] }> =>
    (await api.get('/notifications/')).data,
  markRead: async (id: number) => (await api.patch(`/notifications/${id}/read`)).data,
  markAllRead: async () => (await api.post('/notifications/read-all')).data,
  preferences: async (): Promise<{ topics: NotificationTopicPreference[] }> =>
    (await api.get('/notifications/preferences')).data,
  updatePreference: async (topic: string, patch: NotificationPreferencePatch): Promise<NotificationTopicPreference> =>
    (await api.patch(`/notifications/preferences/${topic}`, patch)).data,
}
