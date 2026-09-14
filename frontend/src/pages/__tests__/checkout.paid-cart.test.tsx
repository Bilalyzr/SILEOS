/** Paid carts use one signed Razorpay order; free carts keep /orders/. */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockCart = vi.hoisted(() => ({
  items: [] as any[],
  appliedCoupon: null as any,
  getFinalTotal: vi.fn(() => 0),
  checkout: vi.fn(),
  clearCart: vi.fn(),
}))
vi.mock('@/contexts/CartContext', () => ({ useCart: () => mockCart }))

vi.mock('@/store/auth', () => ({
  useAuthStore: (selector: any) => selector({ user: { id: 1, user_email: 'a@b.c' } }),
}))

vi.mock('@/api/axios', () => ({ api: { post: vi.fn(), get: vi.fn() } }))
vi.mock('@/api/course', () => ({ courseAPI: { getCheckoutInfo: vi.fn() } }))
vi.mock('@/api/cart', () => ({ validateCoupon: vi.fn() }))
vi.mock('@/api/funnel', () => ({ track: vi.fn() }))
vi.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: vi.fn(), error: vi.fn() },
}))

import { CheckoutPage } from '../checkout'
import { api } from '@/api/axios'

const paidItems = [
  { courseId: 11, title: 'React Mastery', instructor: 'A', price: 999, thumbnail: '', level: 'beginner' },
  { courseId: 12, title: 'Node Deep Dive', instructor: 'B', price: 1499, salePrice: 1199, thumbnail: '', level: 'advanced' },
]

function renderCartCheckout() {
  return render(
    <MemoryRouter initialEntries={['/checkout']}>
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/checkout/:courseId" element={<CheckoutPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('CheckoutPage — paid cart checkout', () => {
  beforeEach(() => {
    mockCart.items = paidItems
    mockCart.appliedCoupon = null
    mockCart.getFinalTotal.mockReset()
    mockCart.checkout.mockReset()
    mockCart.clearCart.mockReset()
    vi.mocked(api.post).mockReset()
    delete (window as any).Razorpay
  })

  it('creates and verifies one Razorpay order for every cart course', async () => {
    mockCart.getFinalTotal.mockReturnValue(2198)
    vi.mocked(api.post).mockImplementation(async (url: string) => {
      if (url === '/payments/create-order') {
        return {
          data: {
            order_id: 'order_CART1', amount: 219800,
            currency: 'INR', key_id: 'rzp_test',
          },
        } as any
      }
      return { data: { success: true } } as any
    })
    ;(window as any).Razorpay = vi.fn().mockImplementation((options: any) => ({
      on: vi.fn(),
      open: () => options.handler({
        razorpay_order_id: 'order_CART1',
        razorpay_payment_id: 'pay_CART1',
        razorpay_signature: 'signed-cart',
      }),
    }))
    renderCartCheckout()

    fireEvent.click(await screen.findByRole('button', { name: /Proceed to Pay ₹2198.00/i }))

    await waitFor(() => expect(api.post).toHaveBeenCalledWith(
      '/payments/create-order',
      { course_ids: [11, 12], coupon_code: undefined },
    ))
    await waitFor(() => expect(api.post).toHaveBeenCalledWith(
      '/payments/verify',
      expect.objectContaining({
        razorpay_order_id: 'order_CART1',
        razorpay_payment_id: 'pay_CART1',
        course_ids: [11, 12],
      }),
    ))
    expect(mockCart.clearCart).toHaveBeenCalledOnce()
  })

  it('keeps the existing checkout CTA for a free cart (total == 0)', async () => {
    mockCart.items = [{ courseId: 21, title: 'Free Intro', instructor: 'C', price: 0, thumbnail: '', level: 'beginner' }]
    mockCart.getFinalTotal.mockReturnValue(0)
    renderCartCheckout()

    await waitFor(() => expect(screen.getByText('Enroll for Free')).toBeInTheDocument())
    expect(mockCart.checkout).not.toHaveBeenCalled()
  })
})
