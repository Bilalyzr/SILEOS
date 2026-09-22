import { api } from './axios'

export interface DashboardStats {
  enrolled_courses?: number
  completed_courses?: number
  total_hours?: number
  certificates?: number
  total_courses?: number
  total_students?: number
  total_purchases?: number
  total_earnings?: string
  average_rating?: number
  total_revenue?: string
  active_enrollments?: number
}

export interface EnrolledCourse {
  id: number
  title: string
  thumbnail: string
  progress: number
  totalLessons: number
  completedLessons: number
  instructor: string
  rating: number
  nextLesson?: string | null
}

export interface InstructorCourse {
  id: number
  title: string
  students: number
  total_enrollments: number
  rating: number
  average_rating: number
  earnings: number
  course_price: number
  course_sale_price: number
  course_duration: string
  status: string
}

export interface AdminCourse {
  id: number
  title: string
  students: number
  revenue: string
  rating: number
  status: string
}

export interface Enrollment {
  student: string
  course: string
  date: string
  status: string
}

export interface StudentInternship {
  id: number
  title: string
  voucher_code: string
  status: string
  redeemed_course_title: string | null
  attendance_days: number
  hired_company: string | null
  created_at: string | null
}

export interface StudentDashboardData {
  stats: DashboardStats
  enrolled_courses: EnrolledCourse[]
  recent_activity: any[]
  internships?: StudentInternship[]
  weekly_goal?: {
    goal_hours: number
    completed_hours: number
    progress_percentage: number
    lessons_completed: number
  }
}

export interface InstructorDashboardData {
  stats: DashboardStats
  courses: InstructorCourse[]
  recent_activity: any[]
}

export interface AdminDashboardData {
  user_stats: {
    total_users?: number
    active_users?: number
    students: number
    students_unverified?: number
    students_total?: number
    instructors?: number
    companies?: number
    spocs?: number
    new_users_count?: number
  }
  course_stats: {
    total_courses: number
    published_courses: number
    draft_courses: number
    avg_rating: number
    recent_courses: AdminCourse[]
  }
  enrollment_stats: {
    total_enrollments: number
    completed_enrollments: number
    completion_rate: number
    new_enrollments_count: number
    recent_enrollments: Enrollment[]
  }
  revenue_stats: {
    total_revenue: number
    monthly_revenue: number        // current calendar month to date (IST)
    monthly_revenue_label: string  // e.g. "July 2026"
    avg_course_price: number
    revenue_period: number
  }
}

export interface RevenuePoint {
  date: string         // YYYY-MM-DD
  label: string        // e.g. "26 Jun"
  revenue: number      // total = courses + internships
  courses?: number     // COMPLETED orders that day
  internships?: number // internship voucher revenue that day
}

export interface RevenueTimeseries {
  period: string
  currency: string
  total: number
  points: RevenuePoint[]
}

// ---------------------------------------------------------------------------
// Student analytics report
// ---------------------------------------------------------------------------

export type AnalyticsPeriod = '7d' | '30d' | '90d' | '180d' | '1y' | 'all'

export interface StudentAnalyticsSummary {
  enrolled_courses: number
  completed_courses: number
  in_progress_courses: number
  not_started_courses: number
  completion_rate: number
  certificates_earned: number
  total_lessons: number
  completed_lessons: number
  lesson_completion_rate: number
  total_hours: number
  period_hours: number
  period_lessons: number
  avg_progress: number
  active_days: number
  current_streak: number
  longest_streak: number
  avg_session_hours: number
  quizzes_attempted: number
  quizzes_passed: number
  quiz_pass_rate: number
  avg_quiz_score: number
  assignments_submitted: number
  assignments_graded: number
  avg_assignment_score: number
}

export interface AnalyticsActivityPoint {
  date: string
  label: string
  lessons: number
  hours: number
}

export interface AnalyticsMonthlyPoint {
  month: string
  label: string
  completed: number
}

export interface AnalyticsCourseRow {
  course_id: number
  title: string
  slug: string
  thumbnail: string
  instructor: string
  progress: number
  completed_lessons: number
  total_lessons: number
  hours: number
  avg_quiz_score: number | null
  status: 'completed' | 'in_progress' | 'not_started'
  has_certificate: boolean
  enrolled_at: string | null
  completed_at: string | null
  last_activity: string | null
  days_since_activity: number | null
}

export interface AnalyticsQuizRow {
  attempt_id: number
  quiz_title: string
  course_title: string
  score: number
  passing_grade: number
  passed: boolean
  earned_marks: number
  total_marks: number
  attempted_at: string | null
}

export interface AnalyticsAssignmentRow {
  id: number
  title: string
  course_title: string
  status: string
  grade: number | null
  total_points: number
  percentage: number | null
  submitted_at: string | null
  graded_at: string | null
}

export interface AnalyticsCertificateRow {
  id: number
  course_id: number
  course_title: string
  issued_at: string | null
  completion_date: string | null
  secure_certificate_id: string
  certificate_hash: string
}

export interface AnalyticsInsight {
  tone: 'positive' | 'warning' | 'neutral'
  title: string
  detail: string
}

export interface StudentAnalyticsData {
  period: AnalyticsPeriod
  period_label: string
  generated_at: string
  student: { name: string; email: string }
  summary: StudentAnalyticsSummary
  activity_timeline: AnalyticsActivityPoint[]
  monthly_completions: AnalyticsMonthlyPoint[]
  course_breakdown: AnalyticsCourseRow[]
  quiz_history: AnalyticsQuizRow[]
  assignment_history: AnalyticsAssignmentRow[]
  certificates: AnalyticsCertificateRow[]
  insights: AnalyticsInsight[]
}

export const dashboardAPI = {
  // Get student dashboard data
  getStudentDashboard: async (): Promise<StudentDashboardData> => {
    const response = await api.get('/dashboard/student')
    return response.data
  },

  // Get the student's analytics report (progress, performance, certificates)
  getStudentAnalytics: async (
    period: AnalyticsPeriod = '90d'
  ): Promise<StudentAnalyticsData> => {
    const response = await api.get('/dashboard/student/analytics', { params: { period } })
    return response.data
  },

  // Get instructor dashboard data
  getInstructorDashboard: async (): Promise<InstructorDashboardData> => {
    const response = await api.get('/dashboard/instructor')
    return response.data
  },

  // Get admin dashboard data
  getAdminDashboard: async (): Promise<AdminDashboardData> => {
    const response = await api.get('/admin/stats')
    return response.data
  },

  // Get real daily revenue series for the admin Revenue chart
  getAdminRevenueTimeseries: async (
    period: '7d' | '30d' | '90d' | '1y' = '30d'
  ): Promise<RevenueTimeseries> => {
    const response = await api.get('/admin/revenue-timeseries', { params: { period } })
    return response.data
  },
}
