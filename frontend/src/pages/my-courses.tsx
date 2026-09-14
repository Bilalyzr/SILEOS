/**
 * My Courses — student's enrolled courses, redesigned to match the dashboard
 * theme. Shows an empty state when the student has no enrollments.
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Play, BookOpen, Award, Download } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { courseAPI } from '@/api/course'
import { toast } from 'react-hot-toast'
import { formatDistanceToNow } from 'date-fns'
import { getCourseThumbnailUrl } from '@/utils/media'
import { useAuth } from '@/hooks/use-auth'
import {
  Greeting, SectionCard, EmptyState, FadeUp, StaggerGrid, fadeUp,
} from '@/components/dashboard/primitives'
import { motion } from 'framer-motion'

interface EnrolledCourse {
  id: number
  title: string
  thumbnail?: string
  progress: number
  enrolled_at?: string
  last_accessed?: string
  completion_date?: string | null
  /** The enrollment's state: enrolled | completed | cancelled. */
  enrollment_status?: string | null
  /** The COURSE's publish state, not the enrollment's. */
  status?: string
  instructor?: string | { id: number; name: string }
  completedLessons?: number
  totalLessons?: number
  nextLesson?: string
}

const filters = ['All Courses', 'In Progress', 'Completed', 'Not Started'] as const
type Filter = typeof filters[number]

export function MyCoursesPage() {
  const { fullName } = useAuth()
  const [enrolledCourses, setEnrolledCourses] = useState<EnrolledCourse[]>([])
  const [loading, setLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState<Filter>('All Courses')

  useEffect(() => {
    fetchEnrolledCourses()
  }, [])

  const fetchEnrolledCourses = async () => {
    try {
      setLoading(true)
      // courseAPI types this as Course[], but /users/my-courses returns the
      // formatted shape (title/progress/instructor), not the WordPress-shaped
      // Course (post_title/post_status). EnrolledCourse below is the accurate
      // description of what actually arrives.
      const data = (await courseAPI.getEnrolledCourses()) as unknown as EnrolledCourse[]
      setEnrolledCourses(data || [])
    } catch (error: any) {
      console.error('Error fetching enrolled courses:', error)
      toast.error('Failed to load enrolled courses')
    } finally {
      setLoading(false)
    }
  }

  const courses = enrolledCourses

  // Order matters. The enrollment's own status is authoritative when the
  // backend sets one — the stored percentage lags behind it (quizzes and
  // assignments are weighted in, admins can release a course early, imported
  // rows carry a completion date they never earned). Falling through to the
  // percentage alone is what put finished courses under "In Progress".
  // A cancelled enrollment is never "completed", whatever date it carries.
  const getCourseStatus = (course: EnrolledCourse): 'completed' | 'in-progress' | 'not-started' => {
    const enrollmentStatus = (course.enrollment_status || '').toLowerCase()
    if (enrollmentStatus === 'completed') return 'completed'
    if (enrollmentStatus !== 'cancelled' && course.completion_date) return 'completed'
    if (course.progress === 100) return 'completed'
    if ((course.progress || 0) > 0) return 'in-progress'
    return 'not-started'
  }

  const formatLastAccessed = (dateString?: string) => {
    if (!dateString) return null
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true })
    } catch {
      return null
    }
  }

  const getInstructorName = (course: EnrolledCourse): string => {
    if (!course.instructor) return ''
    return typeof course.instructor === 'string' ? course.instructor : course.instructor.name
  }

  const filteredCourses = courses.filter(course => {
    const courseStatus = getCourseStatus(course)
    return activeFilter === 'All Courses' ||
      (activeFilter === 'In Progress' && courseStatus === 'in-progress') ||
      (activeFilter === 'Completed' && courseStatus === 'completed') ||
      (activeFilter === 'Not Started' && courseStatus === 'not-started')
  })

  const realDataEmpty = !loading && enrolledCourses.length === 0

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
          subtitle="All the courses you've enrolled in. Resume any lesson, check progress, or download certificates."
          className="mb-6"
        />

        <FadeUp className="mb-6">
          <div className="flex flex-wrap gap-2">
            {filters.map((filter) => (
              <button
                key={filter}
                onClick={() => setActiveFilter(filter)}
                className={`px-4 py-1.5 rounded-full text-sm font-semibold transition ${
                  activeFilter === filter
                    ? 'bg-orange-500 text-white shadow-sm'
                    : 'bg-white/70 text-secondary-800 ring-1 ring-slate-200 hover:bg-white'
                }`}
              >
                {filter}
              </button>
            ))}
          </div>
        </FadeUp>

        <SectionCard
          title="My courses"
          description={`${courses.length} active enrollment${courses.length === 1 ? '' : 's'}`}
          icon={BookOpen}
        >
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {[1, 2, 3].map(i => (
                <div key={i} className="dash-card p-0 overflow-hidden">
                  <div className="h-40 dash-skeleton" />
                  <div className="p-4 space-y-3">
                    <div className="h-4 w-3/4 dash-skeleton" />
                    <div className="h-3 w-1/2 dash-skeleton" />
                    <div className="h-2 w-full dash-skeleton" />
                  </div>
                </div>
              ))}
            </div>
          ) : realDataEmpty ? (
            <EmptyState
              icon={BookOpen}
              title="No courses yet"
              description="Browse the catalog and enroll in your first course to start learning."
              action={{ label: 'Browse courses', to: '/courses' }}
            />
          ) : filteredCourses.length === 0 ? (
            <EmptyState
              icon={BookOpen}
              title="No courses match this filter"
              description={`Try a different filter — you have ${courses.length} enrolled course${courses.length === 1 ? '' : 's'}.`}
            />
          ) : (
            <StaggerGrid className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {filteredCourses.map((course) => {
                const status = getCourseStatus(course)
                const progress = course.progress || 0
                const instructor = getInstructorName(course)
                const lastAccessed = formatLastAccessed(course.last_accessed)
                const completedLessons = course.completedLessons
                const totalLessons = course.totalLessons
                return (
                  <motion.div
                    key={course.id}
                    variants={fadeUp}
                    className="dash-card dash-card-hoverable p-0 overflow-hidden flex flex-col"
                  >
                    <div className="relative">
                      <img
                        src={getCourseThumbnailUrl(course.thumbnail || '')}
                        alt={course.title}
                        className="w-full h-40 object-cover"
                      />
                      {status === 'completed' && (
                        <div className="absolute top-2 left-2">
                          <Badge className="bg-emerald-600 text-white border-none">
                            <Award className="h-3 w-3 mr-1" />
                            Completed
                          </Badge>
                        </div>
                      )}
                    </div>

                    <div className="p-4 flex-1 flex flex-col">
                      <h3 className="text-base font-semibold text-secondary-900 line-clamp-2">
                        {course.title}
                      </h3>
                      {instructor && (
                        <p className="text-xs text-slate-500 mt-1">By {instructor}</p>
                      )}

                      <div className="mt-3 space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-500 font-medium">Progress</span>
                          <span className="font-semibold text-secondary-900">{progress}%</span>
                        </div>
                        <Progress value={progress} className="h-2" />
                        {(completedLessons != null && totalLessons != null) && (
                          <p className="text-[11px] text-slate-500">
                            {completedLessons} / {totalLessons} lessons completed
                          </p>
                        )}
                      </div>

                      <div className="mt-4 flex items-center justify-between gap-2 pt-3 border-t border-slate-100">
                        <Link
                          to={`/courses/${course.id}/learn`}
                          className="dash-cta px-3 py-1.5 text-xs"
                        >
                          <Play className="h-3.5 w-3.5" />
                          {status === 'not-started' ? 'Start' : 'Continue'}
                        </Link>
                        {status === 'completed' && (
                          <Link to={`/certificates/${course.id}`}>
                            <Button variant="outline" size="sm" className="text-xs">
                              <Download className="h-3.5 w-3.5 mr-1" />
                              Certificate
                            </Button>
                          </Link>
                        )}
                      </div>

                      {lastAccessed && (
                        <p className="text-[11px] text-slate-400 mt-3">
                          Last accessed {lastAccessed}
                        </p>
                      )}
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
