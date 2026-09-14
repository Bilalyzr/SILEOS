import { create } from 'zustand'
import { Course,CourseFilters } from '@/types'
import { courseAPI } from '@/api/course'

interface CourseState {
  // State
  courses: Course[]
  currentCourse: Course | null
  enrolledCourses: Course[]
  wishlist: Course[]
  isLoading: boolean
  error: string | null
  filters: CourseFilters
  pagination: {
    total: number
    page: number
    per_page: number
    last_page: number
  }

  // Actions
  fetchCourses: () => Promise<void>
  fetchCourse: (id: number) => Promise<Course>
  fetchEnrolledCourses: () => Promise<void>
  fetchWishlist: () => Promise<void>
  setFilters: (filters: Partial<CourseFilters>) => void
  clearFilters: () => void
  enrollInCourse: (courseId: number) => Promise<void>
  addToWishlist: (courseId: number) => Promise<void>
  removeFromWishlist: (courseId: number) => Promise<void>
  searchCourses: (query: string) => Promise<void>
  setCurrentCourse: (course: Course | null) => void
  clearError: () => void
  setLoading: (loading: boolean) => void
}

const initialFilters: CourseFilters = {
  search: '',
  category: '',
  level: '',
  price_type: '',
  course_type: '',
  rating: 0,
  instructor: '',
  sort: 'latest',
  page: 1,
  per_page: 12,
}

export const useCourseStore = create<CourseState>((set, get) => ({
  // Initial state
  courses: [],
  currentCourse: null,
  enrolledCourses: [],
  wishlist: [],
  isLoading: false,
  error: null,
  filters: initialFilters,
  pagination: {
    total: 0,
    page: 1,
    per_page: 12,
    last_page: 1,
  },

  // Actions
  fetchCourses: async () => {
    try {
      set({ isLoading: true, error: null })

      const { filters } = get()
      const response = await courseAPI.getCourses(filters)

      set({
        courses: response.data,
        pagination: {
          total: response.total,
          page: response.page,
          per_page: response.per_page,
          last_page: response.last_page,
        },
        isLoading: false,
      })
    } catch (error: any) {
      set({
        error: error.message || 'Failed to fetch courses',
        isLoading: false,
      })
    }
  },

  fetchCourse: async (id: number) => {
    try {
      set({ isLoading: true, error: null })

      const course = await courseAPI.getCourse(id)

      set({
        currentCourse: course,
        isLoading: false,
      })

      return course
    } catch (error: any) {
      set({
        error: error.message || 'Failed to fetch course',
        isLoading: false,
      })
      throw error
    }
  },

  fetchEnrolledCourses: async () => {
    try {
      set({ isLoading: true, error: null })

      const courses = await courseAPI.getEnrolledCourses()

      set({
        enrolledCourses: courses,
        isLoading: false,
      })
    } catch (error: any) {
      set({
        error: error.message || 'Failed to fetch enrolled courses',
        isLoading: false,
      })
    }
  },

  fetchWishlist: async () => {
    try {
      set({ isLoading: true, error: null })

      const courses = await courseAPI.getWishlist()

      set({
        wishlist: courses,
        isLoading: false,
      })
    } catch (error: any) {
      set({
        error: error.message || 'Failed to fetch wishlist',
        isLoading: false,
      })
    }
  },

  setFilters: (newFilters: Partial<CourseFilters>) => {
    const { filters } = get()
    const updatedFilters = { ...filters, ...newFilters }

    // Reset page when filters change (except when changing page)
    if (!newFilters.page) {
      updatedFilters.page = 1
    }

    set({ filters: updatedFilters })

    // Auto-fetch courses when filters change
    get().fetchCourses()
  },

  clearFilters: () => {
    set({ filters: initialFilters })
    get().fetchCourses()
  },

  enrollInCourse: async (courseId: number) => {
    try {
      set({ isLoading: true, error: null })

      await courseAPI.enrollInCourse(courseId)

      // Update enrolled courses
      await get().fetchEnrolledCourses()

      // Update current course if it's the one being enrolled in
      const { currentCourse } = get()
      if (currentCourse && currentCourse.id === courseId) {
        const updatedCourse = await get().fetchCourse(courseId)
        set({ currentCourse: updatedCourse })
      }

      set({ isLoading: false })
    } catch (error: any) {
      set({
        error: error.message || 'Failed to enroll in course',
        isLoading: false,
      })
      throw error
    }
  },

  addToWishlist: async (courseId: number) => {
    try {
      await courseAPI.addToWishlist(courseId)

      // Update wishlist
      await get().fetchWishlist()
    } catch (error: any) {
      set({
        error: error.message || 'Failed to add to wishlist',
      })
      throw error
    }
  },

  removeFromWishlist: async (courseId: number) => {
    try {
      await courseAPI.removeFromWishlist(courseId)

      // Update wishlist
      const { wishlist } = get()
      set({
        wishlist: wishlist.filter(course => course.id !== courseId),
      })
    } catch (error: any) {
      set({
        error: error.message || 'Failed to remove from wishlist',
      })
      throw error
    }
  },

  searchCourses: async (query: string) => {
    get().setFilters({ search: query })
  },

  setCurrentCourse: (course: Course | null) => {
    set({ currentCourse: course })
  },

  clearError: () => set({ error: null }),
  setLoading: (loading: boolean) => set({ isLoading: loading }),
}))

// Selectors for common use cases
export const useCourseSelectors = () => {
  const store = useCourseStore()
  const courses = store.courses || []

  return {
    // Featured courses (high rating, popular)
    featuredCourses: courses
      .filter(course => course.average_rating >= 4.5 && course.total_enrollments > 100)
      .slice(0, 6),

    // Popular courses (most enrollments)
    popularCourses: [...courses]
      .sort((a, b) => b.total_enrollments - a.total_enrollments)
      .slice(0, 8),

    // Recent courses (latest)
    recentCourses: [...courses]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 6),

    // Free courses
    freeCourses: courses.filter(course => course.course_price_type === 'free'),

    // Courses by category
    getCoursesByCategory: (categoryId: string) =>
      courses.filter(course =>
        course.categories?.some(cat => cat.id.toString() === categoryId)
      ),

    // Courses by instructor
    getCoursesByInstructor: (instructorId: number) =>
      courses.filter(course => course.post_author === instructorId),

    // Course statistics
    courseStats: {
      total: courses.length,
      free: courses.filter(c => c.course_price_type === 'free').length,
      paid: courses.filter(c => c.course_price_type === 'paid').length,
      averageRating: courses.length > 0
        ? courses.reduce((sum, c) => sum + c.average_rating, 0) / courses.length
        : 0,
    },

    // Search suggestions
    getSearchSuggestions: (query: string) => {
      if (!query.trim()) return []

      const lowercaseQuery = query.toLowerCase()
      const suggestions = new Set<string>()

      store.courses.forEach(course => {
        // Add course titles
        if (course.post_title.toLowerCase().includes(lowercaseQuery)) {
          suggestions.add(course.post_title)
        }

        // Add instructor names
        if (course.instructor?.display_name.toLowerCase().includes(lowercaseQuery)) {
          suggestions.add(course.instructor.display_name)
        }

        // Add categories
        course.categories?.forEach(category => {
          if (category.name.toLowerCase().includes(lowercaseQuery)) {
            suggestions.add(category.name)
          }
        })
      })

      return Array.from(suggestions).slice(0, 5)
    },
  }
}