import { api } from './axios'

/**
 * Cart API wrapper — talks to the FastAPI backend for coupon validation
 * and order creation. Replaces the previous client-side hardcoded promo
 * dict in cartStore.
 *
 * Backend contracts (see backend/app/routers/coupons.py and
 * backend/app/routers/orders.py):
 *
 *   POST /api/v1/coupons/validate
 *     body: { code, course_ids, total_amount }
 *     resp: { valid, message, discount_amount?, final_amount?,
 *             coupon_id?, discount_type?, discount_value? }
 *
 *   POST /api/v1/orders/
 *     body: { course_ids: number[], coupon_code?: string | null }
 *     resp: { id, total_amount, discount_amount, status,
 *             created_at, items: [{course_id, price_at_purchase}],
 *             coupon_code }
 *
 * NOTE: The backend `/orders/` endpoint currently executes a *mock*
 * payment — it marks the order COMPLETED and enrolls the student
 * synchronously. It does NOT return a Razorpay order_id/key. Until
 * the backend wires Razorpay for multi-course cart checkout (see
 * course-detail.tsx single-course flow for reference), the frontend
 * cart checkout cannot open the Razorpay modal. TODO below.
 */

export interface CouponValidationRequest {
  code: string
  course_ids: number[]
  total_amount: number
}

export interface CouponValidationResponse {
  valid: boolean
  message: string
  discount_amount?: number
  final_amount?: number
  coupon_id?: number
  discount_type?: 'percentage' | 'fixed'
  discount_value?: number
}

export interface OrderItem {
  course_id: number
  price_at_purchase: number
}

export interface OrderResponse {
  id: number
  total_amount: number
  discount_amount: number
  status: string
  created_at: string
  items: OrderItem[]
  coupon_code: string | null
  // TODO: backend does not yet return these for cart checkout. When the
  // backend is extended to create a Razorpay order for multi-course
  // carts, surface these fields so the UI can open the Razorpay modal
  // the same way course-detail.tsx does for single-course purchases.
  razorpay_order_id?: string
  razorpay_key?: string
}

/**
 * Validate a coupon code against the server. Returns the parsed response.
 * Does NOT throw on `valid: false` — the caller decides how to surface
 * `message`.
 */
export async function validateCoupon(
  code: string,
  course_ids: number[],
  total_amount: number
): Promise<CouponValidationResponse> {
  const response = await api.post<CouponValidationResponse>('/coupons/validate', {
    code: code.trim().toUpperCase(),
    course_ids,
    total_amount,
  } satisfies CouponValidationRequest)
  return response.data
}

/**
 * Create an order for the given course IDs and optional coupon code.
 * The backend validates the coupon again server-side (see orders.py),
 * so a stale/invalid code will fail here even if it passed `validate`.
 */
export async function checkout(
  course_ids: number[],
  coupon_code?: string | null
): Promise<OrderResponse> {
  const body: { course_ids: number[]; coupon_code?: string } = { course_ids }
  if (coupon_code) {
    body.coupon_code = coupon_code
  }
  const response = await api.post<OrderResponse>('/orders/', body)
  return response.data
}
