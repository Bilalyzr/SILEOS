import { api } from './axios'

export interface MembershipPlan {
  id: number
  name: string
  description: string
  all_access: boolean
  period: string
  interval: number
  price: number
  covered_courses: number
}

export interface MyMembership {
  plan_id: number
  plan_name: string
  status: string
  current_period_end: string | null
  grace_until: string | null
  cancel_at_period_end: boolean
}

export const fetchMembershipPlans = async (): Promise<MembershipPlan[]> => {
  const { data } = await api.get('/memberships/plans')
  return data
}

export const subscribeToPlan = async (planId: number, couponCode?: string): Promise<{ subscription_id: string; razorpay_key: string }> => {
  const { data } = await api.post('/memberships/subscribe', { plan_id: planId, coupon_code: couponCode || undefined })
  return data
}

export const fetchMyMembership = async (): Promise<MyMembership | null> => {
  try {
    const { data } = await api.get('/memberships/me')
    return data
  } catch (err: any) {
    // 404 means "no membership" — a legitimate, expected response. Any
    // other failure (500, network error, etc.) must NOT be swallowed as
    // "no membership": that would show a paying member the no-membership
    // empty state and re-enable the subscribe button during an outage.
    if (err?.response?.status === 404) {
      return null
    }
    throw err
  }
}

export const cancelMembership = async (): Promise<void> => {
  await api.post('/memberships/cancel')
}
