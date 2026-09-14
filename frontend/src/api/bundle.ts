import { api } from './axios'

export interface BundleCourse {
  id: number
  title: string
  price: number
}

export interface BundleSummary {
  id: number
  slug: string
  name: string
  description: string
  bundle_price: number
  combined_price: number
  courses: BundleCourse[]
}

export interface BundleDetail extends BundleSummary {
  owned_course_ids: number[]
}

export const fetchBundles = async (): Promise<BundleSummary[]> => {
  const { data } = await api.get('/bundles')
  return data
}

export const fetchBundle = async (slug: string): Promise<BundleDetail> => {
  const { data } = await api.get(`/bundles/${slug}`)
  return data
}

export const createBundleOrder = async (
  bundleId: number
): Promise<{ order_id: string; amount: number; currency: string; key_id: string }> => {
  const { data } = await api.post('/payments/create-order', { bundle_id: bundleId })
  return data
}

export const verifyBundlePayment = async (p: {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
  bundle_id: number
}): Promise<{ success: boolean; message: string }> => {
  const { data } = await api.post('/payments/verify', p)
  return data
}
