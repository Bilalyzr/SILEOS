import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import {
  validateCoupon as apiValidateCoupon,
  checkout as apiCheckout,
  type OrderResponse,
} from '@/api/cart'

export interface CartItem {
  id: number
  title: string
  instructor: string
  price: number
  originalPrice?: number
  salePrice?: number
  rating: number
  duration: string
  level: string
  thumbnail: string
  discount?: number
}

export interface AppliedCoupon {
  code: string
  discount_amount: number
  final_amount: number
  discount_type?: 'percentage' | 'fixed'
  discount_value?: number
}

interface CartStore {
  items: CartItem[]
  appliedCoupon: AppliedCoupon | null

  // Actions
  addToCart: (item: CartItem) => void
  removeFromCart: (courseId: number) => void
  clearCart: () => void

  // Server-backed coupon flow. Throws with a user-facing message on
  // failure; resolves with the stored AppliedCoupon on success.
  applyCoupon: (code: string) => Promise<AppliedCoupon>
  removeCoupon: () => void

  // Server-backed checkout. Posts to /orders/ and returns the order.
  // Clears the cart on success. Throws on failure.
  checkout: () => Promise<OrderResponse>

  // Computed
  getSubtotal: () => number
  getSavings: () => number
  getTotal: () => number
  getItemCount: () => number
  isInCart: (courseId: number) => boolean
}

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],
      appliedCoupon: null,

      addToCart: (item) => {
        const state = get()
        if (state.items.find(i => i.id === item.id)) {
          return
        }
        set({ items: [...state.items, item] })
      },

      removeFromCart: (courseId) => {
        set((state) => ({
          items: state.items.filter(item => item.id !== courseId),
          // Invalidate any applied coupon when cart changes — the
          // server may recalculate differently.
          appliedCoupon: null,
        }))
      },

      clearCart: () => {
        set({ items: [], appliedCoupon: null })
      },

      applyCoupon: async (code) => {
        const state = get()
        const course_ids = state.items.map(i => i.id)
        const total_amount = state.getSubtotal()

        if (course_ids.length === 0) {
          throw new Error('Your cart is empty')
        }

        const result = await apiValidateCoupon(code, course_ids, total_amount)

        if (!result.valid) {
          throw new Error(result.message || 'Invalid coupon code')
        }

        const applied: AppliedCoupon = {
          code: code.trim().toUpperCase(),
          discount_amount: result.discount_amount ?? 0,
          final_amount: result.final_amount ?? total_amount,
          discount_type: result.discount_type,
          discount_value: result.discount_value,
        }
        set({ appliedCoupon: applied })
        return applied
      },

      removeCoupon: () => {
        set({ appliedCoupon: null })
      },

      checkout: async () => {
        const state = get()
        const course_ids = state.items.map(i => i.id)
        if (course_ids.length === 0) {
          throw new Error('Your cart is empty')
        }

        const order = await apiCheckout(
          course_ids,
          state.appliedCoupon?.code ?? null
        )

        // This legacy store action is only a zero-value checkout path. Paid
        // carts use the active CartContext and the Razorpay create/verify
        // handshake in pages/checkout.tsx.
        set({ items: [], appliedCoupon: null })
        return order
      },

      getSubtotal: () => {
        const state = get()
        return state.items.reduce((sum, item) => {
          const price = item.salePrice || item.price
          return sum + price
        }, 0)
      },

      getSavings: () => {
        const state = get()
        return state.items.reduce((sum, item) => {
          if (item.originalPrice) {
            const currentPrice = item.salePrice || item.price
            return sum + (item.originalPrice - currentPrice)
          }
          return sum
        }, 0)
      },

      getTotal: () => {
        const state = get()
        const subtotal = state.getSubtotal()
        if (state.appliedCoupon) {
          return Math.max(0, state.appliedCoupon.final_amount)
        }
        return subtotal
      },

      getItemCount: () => {
        return get().items.length
      },

      isInCart: (courseId) => {
        return get().items.some(item => item.id === courseId)
      },
    }),
    {
      name: 'cart-storage',
    }
  )
)
