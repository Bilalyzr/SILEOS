/**
 * Wishlist — courses the student has saved to revisit later. Themed to match
 * the dashboard. Shows an empty state when nothing is saved.
 */
import { useState,useEffect } from 'react'
import { confirmDialog } from '@/components/ui/confirm'
import { Link } from 'react-router-dom'
import { Heart,Star,Users,Trash2,ShoppingCart } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { toast } from 'react-hot-toast'
import { motion } from 'framer-motion'
import { api } from '@/api/axios'
import { useAuthStore } from '@/store/auth'
import { useAuth } from '@/hooks/use-auth'
import { useCart } from '@/contexts/CartContext'
import {
Greeting,SectionCard,EmptyState,StaggerGrid,fadeUp,
} from '@/components/dashboard/primitives'

interface WishlistCourse {
  id: number
  title: string
  instructor: { id: number; name: string }
  rating: number
  students_count?: number
  stats?: { students: number; duration: number }
  price: number
  original_price?: number
  level?: string
  thumbnail: string
  wishlist_item_id?: number
}

export function WishlistPage() {
  const { fullName } = useAuth()
  const { addToCart } = useCart()
  const accessToken = useAuthStore(state => state.accessToken)
  const [courses, setCourses] = useState<WishlistCourse[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchWishlist()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchWishlist = async () => {
    try {
      setLoading(true)
      const response = await api.get(`/wishlist/`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      setCourses(response.data.courses || [])
    } catch (error: any) {
      console.error('Failed to fetch wishlist:', error)
      toast.error('Failed to load wishlist')
      setCourses([])
    } finally {
      setLoading(false)
    }
  }

  const items = courses
  const realDataEmpty = !loading && courses.length === 0

  const handleRemove = async (courseId: number, courseTitle: string) => {
    if (!await confirmDialog(`Remove "${courseTitle}" from your wishlist?`)) return
    try {
      await api.delete(`/wishlist/${courseId}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      setCourses(prev => prev.filter(c => c.id !== courseId))
      toast.success('Course removed from wishlist')
    } catch (error: any) {
      console.error('Failed to remove from wishlist:', error)
      toast.error(error.response?.data?.detail || 'Failed to remove from wishlist')
    }
  }

  const handleMoveToCart = async (course: WishlistCourse) => {
    const hasDiscount = course.original_price && course.original_price > course.price
    // addToCart shows its own toast (added / already in cart).
    addToCart({
      courseId: course.id,
      title: course.title,
      instructor: course.instructor?.name || 'Unknown Instructor',
      price: hasDiscount ? course.original_price! : course.price,
      salePrice: hasDiscount ? course.price : undefined,
      thumbnail: course.thumbnail || '',
      level: course.level || 'Beginner',
      rating: course.rating,
    })
    // Once it's in the cart, drop it from the wishlist (silent — no confirm).
    try {
      await api.delete(`/wishlist/${course.id}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      setCourses(prev => prev.filter(c => c.id !== course.id))
    } catch {
      // Leave it in the wishlist if server-side removal fails.
    }
  }

  const studentCount = (c: WishlistCourse) =>
    c.students_count ?? c.stats?.students ?? 0

  // No page-level shell here: this route already renders inside
  // StudentLayout -> DashboardWorkspace, which supplies the dash-bg,
  // the decorative shapes and the max-w-7xl padded container. Repeating
  // them nested the background inside itself and doubled the horizontal
  // padding, which cost ~32px of usable width on a phone.
  return (
    <>
        <Greeting
          name={fullName}
          chip="STUDENT WORKSPACE"
          subtitle="Courses you've saved to revisit later."
          className="mb-6"
        />

        <SectionCard
          title="Wishlist"
          description={`${items.length} saved course${items.length === 1 ? '' : 's'}`}
          icon={Heart}
        >
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="dash-card p-4 flex gap-4">
                  <div className="w-40 h-24 dash-skeleton flex-shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-3/4 dash-skeleton" />
                    <div className="h-3 w-1/2 dash-skeleton" />
                    <div className="h-3 w-1/4 dash-skeleton" />
                  </div>
                </div>
              ))}
            </div>
          ) : realDataEmpty ? (
            <EmptyState
              icon={Heart}
              title="Your wishlist is empty"
              description="Browse courses and tap the heart icon to save courses for later."
              action={{ label: 'Browse courses', to: '/courses' }}
            />
          ) : (
            <StaggerGrid className="space-y-4">
              {items.map((course) => {
                const hasDiscount = course.original_price && course.original_price > course.price
                return (
                  <motion.div
                    key={course.id}
                    variants={fadeUp}
                    className="dash-card dash-card-hoverable p-4"
                  >
                    <div className="flex flex-col sm:flex-row gap-4">
                      <Link
                        to={`/courses/${course.id}`}
                        className="flex-shrink-0 block w-full sm:w-48"
                      >
                        <img
                          src={course.thumbnail || '/api/placeholder/300/200'}
                          alt={course.title}
                          className="w-full h-28 sm:h-28 object-cover rounded-lg"
                        />
                      </Link>

                      <div className="flex-1 min-w-0 flex flex-col">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0">
                            <Link to={`/courses/${course.id}`}>
                              <h3 className="text-base font-semibold text-secondary-900 hover:text-orange-600 transition line-clamp-2">
                                {course.title}
                              </h3>
                            </Link>
                            <p className="text-xs text-slate-500 mt-1">
                              By {course.instructor?.name || 'Unknown Instructor'}
                            </p>

                            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600 mt-2">
                              <span className="flex items-center">
                                <Star className="h-3.5 w-3.5 text-amber-400 mr-1" fill="currentColor" />
                                {course.rating || 0}
                              </span>
                              <span className="flex items-center">
                                <Users className="h-3.5 w-3.5 mr-1" />
                                {studentCount(course).toLocaleString()}
                              </span>
                              {course.level && (
                                <Badge variant="outline" className="text-[10px]">
                                  {course.level}
                                </Badge>
                              )}
                            </div>
                          </div>

                          <div className="text-right flex-shrink-0">
                            <div className="text-lg font-bold text-secondary-900">
                              ₹{(course.price || 0).toLocaleString('en-IN')}
                            </div>
                            {hasDiscount && (
                              <div className="text-xs text-slate-400 line-through">
                                ₹{course.original_price!.toLocaleString('en-IN')}
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="mt-auto pt-3 flex flex-wrap items-center justify-between gap-2">
                          <button
                            onClick={() => handleMoveToCart(course)}
                            className="dash-cta px-3 py-1.5 text-xs"
                          >
                            <ShoppingCart className="h-3.5 w-3.5" />
                            Move to cart
                          </button>
                          <button
                            onClick={() => handleRemove(course.id, course.title)}
                            className="text-xs font-semibold text-rose-600 hover:text-rose-700 inline-flex items-center gap-1 px-2 py-1 rounded hover:bg-rose-50 transition"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Remove
                          </button>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </StaggerGrid>
          )}
        </SectionCard>
  </>
  )
}
