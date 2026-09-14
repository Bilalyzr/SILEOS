import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import toast from 'react-hot-toast'
import {
  validateCoupon as apiValidateCoupon,
  checkout as apiCheckout,
  type OrderResponse,
} from '@/api/cart'

interface CartItem {
  courseId: number
  title: string
  instructor: string
  price: number
  salePrice?: number
  thumbnail: string
  level: string
  rating?: number
}

interface AppliedCoupon {
  code: string
  discountAmount: number
  discountType: 'percentage' | 'fixed'
  discountValue: number
}

interface CartContextType {
  items: CartItem[]
  appliedCoupon: AppliedCoupon | null
  addToCart: (item: CartItem) => void
  removeFromCart: (courseId: number) => void
  clearCart: () => void
  getCartTotal: () => number
  getItemCount: () => number
  isInCart: (courseId: number) => boolean
  setAppliedCoupon: (coupon: AppliedCoupon | null) => void
  getFinalTotal: () => number
  // Server-backed coupon + checkout. Throw on failure with the
  // server's error message so UI can surface it directly.
  applyCoupon: (code: string) => Promise<AppliedCoupon>
  checkout: () => Promise<OrderResponse>
}

const CartContext = createContext<CartContextType | undefined>(undefined)

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([])
  const [appliedCoupon, setAppliedCoupon] = useState<AppliedCoupon | null>(null)
  const [isLoaded, setIsLoaded] = useState(false)

  // Load cart from localStorage on mount
  useEffect(() => {
    const savedCart = localStorage.getItem('cart')
    if (savedCart) {
      try {
        setItems(JSON.parse(savedCart))
      } catch (error) {
        console.error('Error loading cart from localStorage:', error)
      }
    }

    const savedCoupon = localStorage.getItem('appliedCoupon')
    if (savedCoupon) {
      try {
        const parsed = JSON.parse(savedCoupon)
        // Expire coupon after 60 seconds of inactivity
        if (parsed && parsed.savedAt && Date.now() - parsed.savedAt < 60000) {
          setAppliedCoupon(parsed.coupon)
        } else {
          localStorage.removeItem('appliedCoupon')
        }
      } catch (error) {
        console.error('Error loading coupon from localStorage:', error)
        localStorage.removeItem('appliedCoupon')
      }
    }

    setIsLoaded(true)
  }, [])

  // Save cart to localStorage whenever it changes (after initial load)
  useEffect(() => {
    if (isLoaded) {
      localStorage.setItem('cart', JSON.stringify(items))
    }
  }, [items, isLoaded])

  // Save coupon to localStorage whenever it changes (after initial load)
  useEffect(() => {
    if (isLoaded) {
      if (appliedCoupon) {
        localStorage.setItem(
          'appliedCoupon',
          JSON.stringify({ coupon: appliedCoupon, savedAt: Date.now() })
        )
      } else {
        localStorage.removeItem('appliedCoupon')
      }
    }
  }, [appliedCoupon, isLoaded])

  const addToCart = (item: CartItem) => {
    setItems(prev => {
      // Check if item already exists in cart
      const exists = prev.find(i => i.courseId === item.courseId)
      if (exists) {
        toast('Course already in cart')
        return prev
      }
      toast.success('Added to cart')
      return [...prev, item]
    })
  }

  const removeFromCart = (courseId: number) => {
    setItems(prev => prev.filter(item => item.courseId !== courseId))
    toast.success('Removed from cart')
  }

  const clearCart = () => {
    setItems([])
    setAppliedCoupon(null)
    localStorage.removeItem('cart')
    localStorage.removeItem('appliedCoupon')
  }

  const getCartTotal = () => {
    return items.reduce((sum, item) => {
      const price = item.salePrice ?? item.price
      return sum + price
    }, 0)
  }

  const getFinalTotal = () => {
    const subtotal = getCartTotal()
    const discount = appliedCoupon ? appliedCoupon.discountAmount : 0
    return Math.max(0, subtotal - discount)
  }

  const getItemCount = () => {
    return items.length
  }

  const isInCart = (courseId: number) => {
    return items.some(item => item.courseId === courseId)
  }

  const applyCoupon = async (code: string): Promise<AppliedCoupon> => {
    const courseIds = items.map(i => i.courseId)
    if (courseIds.length === 0) {
      throw new Error('Your cart is empty')
    }
    const subtotal = items.reduce((sum, item) => {
      const price = item.salePrice ?? item.price
      return sum + price
    }, 0)

    const result = await apiValidateCoupon(code, courseIds, subtotal)
    if (!result.valid) {
      // Throw the server-provided reason so the UI can display it.
      throw new Error(result.message || 'Invalid coupon code')
    }

    const applied: AppliedCoupon = {
      code: code.trim().toUpperCase(),
      discountAmount: result.discount_amount ?? 0,
      discountType: (result.discount_type ?? 'percentage') as 'percentage' | 'fixed',
      discountValue: result.discount_value ?? 0,
    }
    setAppliedCoupon(applied)
    return applied
  }

  const checkout = async (): Promise<OrderResponse> => {
    const courseIds = items.map(i => i.courseId)
    if (courseIds.length === 0) {
      throw new Error('Your cart is empty')
    }
    const order = await apiCheckout(courseIds, appliedCoupon?.code ?? null)
    // This path is intentionally only used for zero-value carts. Paid carts
    // are created and verified through /payments by CheckoutPage, then clear
    // the cart only after the server confirms fulfillment.
    clearCart()
    return order
  }

  return (
    <CartContext.Provider
      value={{
        items,
        appliedCoupon,
        addToCart,
        removeFromCart,
        clearCart,
        getCartTotal,
        getItemCount,
        isInCart,
        setAppliedCoupon,
        getFinalTotal,
        applyCoupon,
        checkout,
      }}
    >
      {children}
    </CartContext.Provider>
  )
}

export function useCart() {
  const context = useContext(CartContext)
  if (context === undefined) {
    throw new Error('useCart must be used within a CartProvider')
  }
  return context
}
