/**
 * Candidate API — SS2
 * Backend mounted at /api/v1/candidates
 */
import { api } from './axios'

export interface CandidateEligibility {
  id: number
  user_id: number
  source: 'auto_certificate' | 'spoc_approved' | string
  eligible: boolean
  reason?: string
  decided_at?: string | null
  cohort_id?: number | null
}

export interface CandidateProfile {
  id: number
  user_id: number
  is_visible: boolean
  resume_url?: string
  bio?: string
  skills: string[]
  preferred_roles: string[]
  availability_date?: string | null
  linkedin_url?: string
  github_url?: string
  portfolio_url?: string
  created_at?: string
  updated_at?: string
  completeness: number
  eligibility?: CandidateEligibility | null
}

export interface CandidateProfileUpdate {
  resume_url?: string
  bio?: string
  skills?: string[]
  preferred_roles?: string[]
  availability_date?: string | null
  linkedin_url?: string
  github_url?: string
  portfolio_url?: string
  is_visible?: boolean
}

export interface CandidateSummary {
  user_id: number
  display_name: string
  bio?: string
  skills: string[]
  preferred_roles: string[]
  availability_date?: string | null
  linkedin_url?: string
  github_url?: string
  portfolio_url?: string
  eligibility_source?: string | null
}

export interface CandidateBrowseResponse {
  total: number
  page: number
  page_size: number
  items: CandidateSummary[]
}

export const candidateAPI = {
  async getMe(): Promise<CandidateProfile> {
    const res = await api.get<CandidateProfile>('/candidates/me')
    return res.data
  },

  async updateMe(payload: CandidateProfileUpdate): Promise<CandidateProfile> {
    const res = await api.put<CandidateProfile>('/candidates/me', payload)
    return res.data
  },

  async setVisibility(is_visible: boolean): Promise<CandidateProfile> {
    const res = await api.post<CandidateProfile>('/candidates/me/visibility', {
      is_visible,
    })
    return res.data
  },

  async browse(params: {
    skills?: string
    roles?: string
    availability_before?: string
    page?: number
    page_size?: number
  } = {}): Promise<CandidateBrowseResponse> {
    const res = await api.get<CandidateBrowseResponse>('/candidates/browse', { params })
    return res.data
  },

  async getDetail(userId: number) {
    const res = await api.get(`/candidates/${userId}`)
    return res.data
  },
}

export default candidateAPI
