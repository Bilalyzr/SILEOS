import { api } from './axios'

/**
 * SS3 — Company + candidate marketplace API client.
 * Backend root: /api/v1/companies
 */

export interface Company {
  id: number
  owner_user_id: number
  name: string
  slug: string
  website: string
  industry: string
  team_size: string
  description: string
  logo_url: string
  contact_email: string
  contact_phone: string
  is_approved: boolean
  approval_source: 'self_serve' | 'admin_invite'
  approved_at: string | null
  created_at: string | null
  updated_at: string | null
}

export type AdminCompanyStatus = 'invited' | 'pending' | 'active' | 'rejected'

export interface AdminCompanyRow {
  id: number
  name: string
  slug: string
  contact_email: string
  contact_phone: string
  website: string
  industry: string
  team_size: string
  description: string
  logo_url: string
  approval_source: 'self_serve' | 'admin_invite'
  is_approved: boolean
  approved_at: string | null
  rejected_at: string | null
  rejection_reason: string
  created_at: string | null
  updated_at: string | null
  status: AdminCompanyStatus
  owner: {
    id: number | null
    display_name: string | null
    is_verified: boolean
    last_login: string | null
  }
  interests_sent: number
}

export interface CompanySignupPayload {
  name: string
  contact_email: string
  password: string
  contact_phone?: string
  website?: string
  industry?: string
  team_size?: string
  description?: string
}

export interface CompanyInvitePayload {
  name: string
  contact_email: string
  contact_phone?: string
  website?: string
  industry?: string
  team_size?: string
  description?: string
}

export interface CompanyUpdatePayload {
  name?: string
  contact_email?: string
  contact_phone?: string
  website?: string
  industry?: string
  team_size?: string
  description?: string
  logo_url?: string
}

export interface CandidateBrowseItem {
  user_id: number
  display_name: string
  headline?: string | null
  skills: string[]
  preferred_roles: string[]
  availability_date?: string | null
  resume_url?: string | null
  linkedin_url?: string | null
  github_url?: string | null
  portfolio_url?: string | null
}

export interface CandidateBrowseResponse {
  items: CandidateBrowseItem[]
  total: number
  page: number
  page_size: number
}

export interface InterestCompanyView {
  id: number
  candidate_user_id: number
  candidate_name: string | null
  status: 'interested' | 'accepted' | 'declined' | 'withdrawn'
  company_message: string
  responded_at: string | null
  created_at: string | null
  candidate_email?: string | null
  candidate_phone?: string | null
}

export interface InterestCandidateView {
  id: number
  company_id: number
  company_name: string | null
  company_logo_url: string | null
  company_industry: string | null
  company_website: string | null
  status: 'interested' | 'accepted' | 'declined' | 'withdrawn'
  company_message: string
  responded_at: string | null
  created_at: string | null
}

export const companyAPI = {
  // Signup / setup
  signup: async (payload: CompanySignupPayload): Promise<Company> => {
    const { data } = await api.post('/companies/signup', payload)
    return data
  },
  completeSetup: async (token: string, password: string): Promise<Company> => {
    const { data } = await api.post('/companies/complete-setup', { token, password })
    return data
  },

  // Admin
  adminInvite: async (payload: CompanyInvitePayload): Promise<Company> => {
    const { data } = await api.post('/companies/admin/invite', payload)
    return data
  },
  bulkInvite: async (
    entries: { name: string; email: string }[],
    send_setup_email: boolean = true
  ): Promise<{
    total: number
    invited: number
    skipped: number
    errors: number
    results: {
      name: string
      email: string
      status: 'invited' | 'skipped_existing_user' | 'error'
      message: string
      company_id?: number
    }[]
  }> => {
    const { data } = await api.post('/companies/admin/bulk-invite', {
      entries,
      send_setup_email,
    })
    return data
  },
  adminListPending: async (): Promise<Company[]> => {
    const { data } = await api.get('/companies/admin/pending')
    return data
  },
  adminListAll: async (params: {
    status?: 'all' | 'invited' | 'pending' | 'active' | 'rejected'
    search?: string
    limit?: number
    skip?: number
  } = {}): Promise<{
    total: number
    limit: number
    skip: number
    items: AdminCompanyRow[]
  }> => {
    const { data } = await api.get('/companies/admin/all', { params })
    return data
  },
  adminResendInvite: async (
    id: number
  ): Promise<{ ok: boolean; sent_to: string }> => {
    const { data } = await api.post(`/companies/admin/${id}/resend-invite`, {})
    return data
  },
  adminApprove: async (id: number): Promise<Company> => {
    const { data } = await api.patch(`/companies/admin/${id}/approve`, {})
    return data
  },
  adminReject: async (id: number, reason?: string): Promise<Company> => {
    const { data } = await api.patch(`/companies/admin/${id}/reject`, {
      reason: reason || '',
    })
    return data
  },

  // Self-service
  getMe: async (): Promise<Company> => {
    const { data } = await api.get('/companies/me')
    return data
  },
  updateMe: async (payload: CompanyUpdatePayload): Promise<Company> => {
    const { data } = await api.put('/companies/me', payload)
    return data
  },

  // Browse + interest
  browseCandidates: async (params: {
    skills?: string
    roles?: string
    availability_before?: string
    page?: number
    page_size?: number
  }): Promise<CandidateBrowseResponse> => {
    const { data } = await api.get('/companies/candidates/browse', { params })
    return data
  },
  expressInterest: async (
    candidateUserId: number,
    message: string
  ): Promise<InterestCompanyView> => {
    const { data } = await api.post(
      `/companies/candidates/${candidateUserId}/interest`,
      { message }
    )
    return data
  },
  myPipeline: async (): Promise<InterestCompanyView[]> => {
    const { data } = await api.get('/companies/me/interests')
    return data
  },

  // Candidate inbox
  myInbox: async (): Promise<InterestCandidateView[]> => {
    const { data } = await api.get('/companies/me/candidate-inbox')
    return data
  },
  acceptInterest: async (interestId: number): Promise<InterestCandidateView> => {
    const { data } = await api.post(`/companies/interests/${interestId}/accept`, {})
    return data
  },
  declineInterest: async (interestId: number): Promise<InterestCandidateView> => {
    const { data } = await api.post(`/companies/interests/${interestId}/decline`, {})
    return data
  },
  withdrawInterest: async (interestId: number): Promise<InterestCompanyView> => {
    const { data } = await api.post(`/companies/interests/${interestId}/withdraw`, {})
    return data
  },
}

export default companyAPI
