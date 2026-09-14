import { api } from './axios'

export interface AdminMessage {
  id: number
  recipient_type: string
  recipient_id: number
  recipient_name: string
  subject: string
  body: string
  sent_at: string
  read_at: string | null
  /** Email delivery outcome; null on messages stored before emailing existed. */
  email_status: 'sent' | 'failed' | 'no_email' | null
}

export interface CompanyRecipient {
  id: number
  name: string
  industry: string
  intern_count: number
}

export interface StudentRecipient {
  id: number
  email: string
  name: string
}

export interface SendMessageParams {
  recipient_type: 'user' | 'company'
  recipient_id: number
  subject: string
  body: string
}

export interface BulkSendMessageParams {
  recipient_type: 'user' | 'company'
  recipient_ids: number[]
  subject: string
  body: string
}

export interface BulkSendResult {
  status: string
  sent_count: number
  failed_count: number
  /** Emails actually accepted by the SMTP server. */
  email_sent_count: number
  /** Recipients whose email bounced at send time or who have no address. */
  email_failed_count: number
  failed: Array<{ id: number; reason: string }>
}

export const adminMessagesAPI = {
  getSent: async () => {
    const res = await api.get<AdminMessage[]>('/admin/messages/sent')
    return res.data
  },

  send: async (params: SendMessageParams) => {
    const res = await api.post<{ status: string; id: number }>('/admin/messages/', params)
    return res.data
  },

  bulkSend: async (params: BulkSendMessageParams) => {
    const res = await api.post<BulkSendResult>('/admin/messages/bulk', params)
    return res.data
  },

  getCompanyRecipients: async () => {
    const res = await api.get<CompanyRecipient[]>('/admin/messages/recipients/company')
    return res.data
  },

  getStudentRecipients: async (params?: { internship_id?: number; company_id?: number; search?: string }) => {
    const res = await api.get<StudentRecipient[]>('/admin/messages/recipients/students', { params })
    return res.data
  },
}
