/**
 * S-H3 — paid multi-course cart checkout was a broken promise: the UI
 * offered "Complete Order" while orders.py hard-402s "Cart checkout cannot
 * process paid orders yet". RULING: hide the CTA when the cart total > 0
 * and route buyers to each course's own checkout; free carts (total == 0)
 * keep the existing cartCheckout flow unchanged.
 */
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockCart = vi.hoisted(() => ({
  items: [] as any[],
  appliedCoupon: null as any,
  getFinalTotal: vi.fn(() => 0),
  checkout: vi.fn(),
}))
vi.mock('@/contexts/CartContext', () => ({ useCart: () => mockCart }))

vi.mock('@/store/auth', () => ({
  useAuthStore: (selector: any) => selector({ user: { id: 1, user_email: 'a@b.c' } }),
}))

vi.mock('@/api/axios', () => ({ api: { post: vi.fn(), get: vi.fn() } }))
vi.mock('@/api/course', () => ({ courseAPI: { getCheckoutInfo: vi.fn() } }))
vi.mock('@/api/cart', () => ({ validateCoupon: vi.fn() }))
vi.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: vi.fn(), error: vi.fn() },
}))

import { CheckoutPage } from '../checkout'

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

describe('CheckoutPage — S-H3 paid cart CTA', () => {
  beforeEach(() => {
    mockCart.items = paidItems
    mockCart.appliedCoupon = null
    mockCart.getFinalTotal.mockReset()
    mockCart.checkout.mockReset()
  })

  it('hides "Complete Order" and shows the buy-individually note with per-course links when total > 0', async () => {
    mockCart.getFinalTotal.mockReturnValue(2198)
    renderCartCheckout()

    await waitFor(() => expect(screen.getByTestId('paid-cart-notice')).toBeInTheDocument())
    expect(screen.getByText(/purchased individually/i)).toBeInTheDocument()
    expect(screen.queryByText(/Complete Order/)).not.toBeInTheDocument()

    const links = screen.getAllByText('Open course →') as HTMLAnchorElement[]
    expect(links).toHaveLength(2)
    expect(links[0].getAttribute('href')).toBe('/courses/11')
    expect(links[1].getAttribute('href')).toBe('/courses/12')
  })

  it('keeps the existing checkout CTA for a free cart (total == 0)', async () => {
    mockCart.items = [{ courseId: 21, title: 'Free Intro', instructor: 'C', price: 0, thumbnail: '', level: 'beginner' }]
    mockCart.getFinalTotal.mockReturnValue(0)
    renderCartCheckout()

    await waitFor(() => expect(screen.getByText('Enroll for Free')).toBeInTheDocument())
    expect(screen.queryByTestId('paid-cart-notice')).not.toBeInTheDocument()
  })
})
