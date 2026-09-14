import { api, apiRequest } from './axios'
import { Course, CourseFilters, PaginatedResponse, CourseCategory, CourseTag } from '@/types'

export const courseAPI = {
  // Get all courses with filters
  getCourses: async (filters: CourseFilters = {}): Promise<PaginatedResponse<Course>> => {
    const params = new URLSearchParams()

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, value.toString())
      }
    })

    return apiRequest(
      api.get(`/courses/?${params.toString()}`)
    )
  },

  // Get single course by numeric id OR slug. Backend accepts both forms at
  // GET /courses/{course_ref} — numeric → id lookup, otherwise slug lookup.
  getCourse: async (idOrSlug: number | string): Promise<Course> => {
    return apiRequest(
      api.get(`/courses/${idOrSlug}`)
    )
  },

  // Get featured courses
  getFeaturedCourses: async (): Promise<Course[]> => {
    return apiRequest(
      api.get('/courses/featured')
    )
  },

  // Get popular courses
  getPopularCourses: async (): Promise<Course[]> => {
    return apiRequest(
      api.get('/courses/popular')
    )
  },

  // Get enrolled courses for current user
  getEnrolledCourses: async (): Promise<Course[]> => {
    return apiRequest(
      api.get('/users/my-courses')
    )
  },

  // Get course progress for enrolled course
  getCourseProgress: async (courseId: number): Promise<{
    overall_progress: number
    completed_lessons: number
    total_lessons: number
    completed_quizzes: number
    total_quizzes: number
  }> => {
    return apiRequest(
      api.get(`/courses/${courseId}/progress`)
    )
  },

  // Record that the student opened a lesson video. Increments the course's
  // video view counter surfaced in Admin -> Courses (Issue 1: video view count).
  recordLessonView: async (courseId: number, lessonId: number): Promise<void> => {
    try {
      await apiRequest(
        api.post(`/courses/${courseId}/lessons/${lessonId}/view`)
      )
    } catch {
      // View tracking is best-effort — never block the player on a failure.
    }
  },

  // Issue 2: course-level statistics for the admin Activity Panel — quiz
  // attempts/pass-rate, struggles (failed attempts), revisits, averages.
  getCourseStatistics: async (courseId: number): Promise<{
    course: { id: number; title: string }
    enrolled_students: number
    quiz: {
      total_quizzes: number
      total_attempts: number
      passed: number
      failed: number
      pass_rate: number
      average_score: number
    }
    struggles: {
      total_failed_attempts: number
      top_strugglers: Array<{ user_id: number; student_name: string; failed_attempts: number }>
    }
    revisits: {
      total_revisits: number
      most_revisited_lessons: Array<{ lesson_id: number; title: string; revisits: number }>
    }
    averages: {
      progress: number
      watch_sessions_per_student: number
      time_spent_per_student_seconds: number
    }
  }> => {
    return apiRequest(
      api.get(`/analytics/courses/${courseId}/statistics`)
    )
  },

  // Issue 8: per-course Student Activity panel (time spent, watch sessions,
  // last active, currently-watching flag) for every enrolled student.
  getCourseStudentActivity: async (courseId: number): Promise<{
    course: { id: number; title: string }
    students: Array<{
      user_id: number
      student_name: string
      email: string
      progress: number
      time_spent_seconds: number
      watch_sessions: number
      last_active: string | null
      currently_watching: boolean
      enrollment_status: string
      completion_date: string | null
    }>
  }> => {
    return apiRequest(
      api.get(`/analytics/courses/${courseId}/student-activity`)
    )
  },

  // Issue 8: full viewing history (watch events + discrete activities) for a
  // single student in a single course.
  getStudentViewingHistory: async (courseId: number, userId: number): Promise<{
    user_id: number
    course_id: number
    watch_history: Array<{
      lesson_id: number
      event: string
      duration_seconds: number
      position_seconds: number
      at: string
    }>
    activities: Array<{
      type: string
      lesson_id: number | null
      quiz_id: number | null
      at: string
    }>
  }> => {
    return apiRequest(
      api.get(`/analytics/students/${userId}/courses/${courseId}/history`)
    )
  },

  // Enroll in a course
  enrollInCourse: async (courseId: number): Promise<void> => {
    return apiRequest(
      api.post(`/courses/${courseId}/enroll`)
    )
  },

  // Get course categories
  getCategories: async (): Promise<CourseCategory[]> => {
    return apiRequest(
      api.get('/categories')
    )
  },

  // Get course tags
  getTags: async (): Promise<CourseTag[]> => {
    return apiRequest(
      api.get('/tags')
    )
  },

  // Get courses by category
  getCoursesByCategory: async (categoryId: number): Promise<Course[]> => {
    return apiRequest(
      api.get(`/categories/${categoryId}/courses`)
    )
  },

  // Get courses by instructor
  getCoursesByInstructor: async (instructorId: number): Promise<Course[]> => {
    return apiRequest(
      api.get(`/instructors/${instructorId}/courses`)
    )
  },

  // Search courses
  searchCourses: async (query: string, filters: Partial<CourseFilters> = {}): Promise<PaginatedResponse<Course>> => {
    const params = new URLSearchParams({ search: query })

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, value.toString())
      }
    })

    return apiRequest(
      api.get(`/courses/search/?${params.toString()}`)
    )
  },

  // Wishlist operations
  getWishlist: async (): Promise<Course[]> => {
    return apiRequest(
      api.get('/wishlist')
    )
  },

  addToWishlist: async (courseId: number): Promise<void> => {
    return apiRequest(
      api.post('/wishlist', { course_id: courseId })
    )
  },

  removeFromWishlist: async (courseId: number): Promise<void> => {
    return apiRequest(
      api.delete(`/wishlist/${courseId}`)
    )
  },

  // Course reviews
  getCourseReviews: async (courseId: number): Promise<{
    reviews: any[]
    average_rating: number
    total_reviews: number
    rating_breakdown: Record<number, number>
  }> => {
    return apiRequest(
      api.get(`/courses/${courseId}/reviews`)
    )
  },

  addCourseReview: async (courseId: number, review: {
    rating: number
    review_title: string
    review_content: string
  }): Promise<void> => {
    return apiRequest(
      api.post(`/courses/${courseId}/reviews`, review)
    )
  },

  // Course curriculum
  getCourseCurriculum: async (courseId: number): Promise<{
    lessons: any[]
    quizzes: any[]
    total_duration: string
  }> => {
    return apiRequest(
      api.get(`/courses/${courseId}/curriculum`)
    )
  },

  // Course announcements
  getCourseAnnouncements: async (courseId: number): Promise<any[]> => {
    return apiRequest(
      api.get(`/courses/${courseId}/announcements`)
    )
  },

  // Course certificates
  getCourseCertificate: async (courseId: number): Promise<{
    certificate_url: string
    completion_date: string
    certificate_id: string
  }> => {
    return apiRequest(
      api.get(`/courses/${courseId}/certificate`)
    )
  },

  // Create course
  createCourse: async (courseData: any): Promise<Course> => {
    return apiRequest(
      api.post('/courses', courseData)
    )
  },

  // Update course
  updateCourse: async (courseId: number, courseData: any): Promise<Course> => {
    return apiRequest(
      api.put(`/courses/${courseId}`, courseData)
    )
  },

  // Delete course
  deleteCourse: async (courseId: number): Promise<{ message: string }> => {
    return apiRequest(
      api.delete(`/courses/${courseId}`)
    )
  },

  // Get checkout info for a course
  getCheckoutInfo: async (courseId: number): Promise<{
    course_id: number
    title: string
    thumbnail: string
    price: number
    sale_price: number | null
    is_free: boolean
    level: string
    duration: string
    is_enrolled: boolean
    instructor?: {
      id: number
      name: string
    }
  }> => {
    return apiRequest(
      // Backend exposes this at /api/v1/checkout/course-info?course_id=N
      // (not as a nested /courses/{id}/checkout-info path).
      api.get(`/checkout/course-info`, { params: { course_id: courseId } })
    )
  },

  // Publish course
  publishCourse: async (courseId: number): Promise<{ message: string; course_id: number; status: string }> => {
    return apiRequest(
      api.patch(`/courses/${courseId}/publish`)
    )
  },

  // Unpublish course (set to draft)
  unpublishCourse: async (courseId: number): Promise<{ message: string; course_id: number; status: string }> => {
    return apiRequest(
      api.patch(`/courses/${courseId}/unpublish`)
    )
  },

  // Create lesson for a course
  createLesson: async (courseId: number, lessonData: {
    title: string
    content?: string
    video_url?: string
    video_duration?: number
    is_preview?: boolean
    youtube_url?: string
  }): Promise<any> => {
    return apiRequest(
      api.post(`/courses/${courseId}/lessons`, lessonData)
    )
  },

  // Instructor-specific endpoints
  instructor: {
    // Get instructor courses
    getCourses: async (): Promise<Course[]> => {
      return apiRequest(
        api.get('/instructor/courses')
      )
    },

    // Get course students
    getCourseStudents: async (courseId: number): Promise<any[]> => {
      return apiRequest(
        api.get(`/instructor/courses/${courseId}/students`)
      )
    },

    // Get course analytics
    getCourseAnalytics: async (courseId: number): Promise<{
      total_enrollments: number
      completion_rate: number
      average_rating: number
      revenue: number
      student_activity: any[]
    }> => {
      return apiRequest(
        api.get(`/instructor/courses/${courseId}/analytics`)
      )
    },

    // Upload course materials
    uploadCourseMaterial: async (courseId: number, file: File, type: string): Promise<{
      url: string
      filename: string
    }> => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('type', type)

      return apiRequest(
        api.post(`/instructor/courses/${courseId}/materials`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })
      )
    },
  },
}