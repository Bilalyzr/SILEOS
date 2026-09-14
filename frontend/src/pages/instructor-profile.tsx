import * as React from "react"
import { useParams,Link } from "react-router-dom"
import { slugify } from "@/utils/slug"
import {
Star,
Users,
BookOpen,
Award,
Globe,ChevronRight,
Facebook,
Twitter,
Linkedin,
User
} from "lucide-react"
import { Card,CardContent,CardHeader,CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar,AvatarImage,AvatarFallback } from "@/components/ui/avatar"
import { StarRating } from "@/components/ui/star-rating"
import { CourseCard } from "@/components/course/course-card"
import { Course } from "@/types"
import { api } from "@/api/axios"
import { getMediaUrl } from "@/utils/media"
import { useSEO } from "@/hooks/use-seo"

interface InstructorProfile {
  id: number
  display_name: string
  email: string
  bio: string
  qualifications: string[]
  experience_years: number
  profile_photo: string
  social_links: {
    website?: string
    facebook?: string
    twitter?: string
    linkedin?: string
  }
}

interface InstructorStats {
  total_courses: number
  total_students: number
  average_rating: number
  total_reviews: number
}

export const InstructorProfilePage = () => {
  const { id } = useParams<{ id: string }>()
  // The URL carries the instructor's name-slug (or a bare id); the backend
  // resolves either form. `instructorId` is the raw ref sent to the API.
  const instructorId = id || ''
  const [instructor, setInstructor] = React.useState<InstructorProfile | null>(null)
  const [instructorCourses, setInstructorCourses] = React.useState<Course[]>([])
  const [instructorStats, setInstructorStats] = React.useState<InstructorStats | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  // SEO / Open Graph tags so shared instructor links get a proper preview
  // (title + photo). Backend prerender also handles /instructor/{id} for
  // crawlers that don't run JS.
  useSEO(
    instructor
      ? {
          title: `${instructor.display_name} | Instructor at SashaInfinity`,
          description: (instructor.bio || `Learn from ${instructor.display_name} on SashaInfinity — expert-led courses.`).replace(/<[^>]*>/g, '').slice(0, 160),
          image: getMediaUrl(instructor.profile_photo) || undefined,
          url: `${window.location.origin}/instructor/${instructorId}`,
          type: 'website',
        }
      : {}
  )

  React.useEffect(() => {
    const fetchInstructorData = async () => {
      if (!id) return

      try {
        setLoading(true)
        setError(null)

        let instructorData: any = null

        try {
          const instructorResponse = await api.get(`/users/instructors/${instructorId}`)
          instructorData = instructorResponse.data
        } catch (publicError) {
          try {
            const instructorResponse = await api.get(`/admin/users?role=instructor`)
            const instructorsList = instructorResponse.data || []
            instructorData = instructorsList.find((u: any) =>
              String(u.id) === instructorId ||
              slugify(u.display_name || u.name || '') === instructorId
            )
          } catch (adminError) {
          }
        }

        if (!instructorData) {
          // Try to get instructor data from courses as a fallback
          try {
            const coursesResponse = await api.get(`/courses?instructor_id=${instructorData?.id ?? instructorId}`)
            const coursesData = coursesResponse.data.courses || coursesResponse.data || []

            if (coursesData.length > 0) {
              // Use instructor data from the first course
              const firstCourse = coursesData[0]

              instructorData = {
                id: firstCourse.instructor.id || parseInt(instructorId),
                display_name: firstCourse.instructor.display_name || firstCourse.instructor.name || 'Unknown Instructor',
                name: firstCourse.instructor.display_name || firstCourse.instructor.name || 'Unknown Instructor',
                email: firstCourse.instructor.email || '',
                bio: firstCourse.instructor.profile?.bio || '',
                qualifications: firstCourse.instructor.profile?.qualifications || [],
                experience_years: firstCourse.instructor.profile?.experience_years || 0,
                profile_photo: firstCourse.instructor.profile?.profile_photo || firstCourse.instructor.avatar || null,
                social_links: {
                  website: firstCourse.instructor.profile?.website || '',
                  facebook: firstCourse.instructor.profile?.facebook || '',
                  twitter: firstCourse.instructor.profile?.twitter || '',
                  linkedin: firstCourse.instructor.profile?.linkedin || ''
                }
              }
            } else {
              throw new Error(`Instructor with ID ${instructorId} not found and no courses found for this instructor`)
            }
          } catch (coursesError) {
            throw new Error(`Instructor with ID ${instructorId} not found`)
          }
        }

        // Transform instructor data to match our interface
        const transformedInstructor: InstructorProfile = {
          id: instructorData.id || parseInt(instructorId),
          display_name: instructorData.display_name || instructorData.name || 'Unknown Instructor',
          email: instructorData.email || '',
          bio: instructorData.profile?.bio || instructorData.description || '',
          qualifications: instructorData.profile?.qualifications || instructorData.qualifications || [],
          experience_years: instructorData.profile?.experience_years || instructorData.experience_years || 0,
          profile_photo: instructorData.profile?.profile_photo || instructorData.avatar || instructorData.profile_photo || null,
          social_links: {
            website: instructorData.profile?.website || instructorData.website || '',
            facebook: instructorData.profile?.facebook || instructorData.facebook || '',
            twitter: instructorData.profile?.twitter || instructorData.twitter || '',
            linkedin: instructorData.profile?.linkedin || instructorData.linkedin || ''
          }
        }

        setInstructor(transformedInstructor)

        // Fetch instructor's courses
        try {
          let coursesData = []

          // Use the same endpoint that worked for the instructor data
          const coursesResponse = await api.get(`/courses?instructor_id=${instructorData?.id ?? instructorId}`)
          coursesData = coursesResponse.data.courses || coursesResponse.data || []

          // Transform courses to match Course interface
          const transformedCourses: Course[] = coursesData.map((course: any) => ({
            id: course.id,
            post_title: course.title,
            post_excerpt: course.description,
            post_content: course.content,
            course_price: course.price,
            course_sale_price: course.sale_price || 0,
            course_price_type: course.price > 0 ? "paid" : "free",
            course_level: course.level,
            course_duration: `${course.duration || 0} hours`,
            course_thumbnail: course.featured_image || course.thumbnail || course.course_thumbnail,
            course_intro_video: "",
            average_rating: course.rating || 0,
            total_reviews: 0,
            lesson_count: course.stats?.lessons ?? 0,
            total_enrollments: course.stats?.students || 0,
            num_offline_workshops: course.num_offline_workshops || 0,
            num_hours: course.num_hours || 0,
            institution: course.institution || "",
            instructor: {
              id: instructorData.id,
              display_name: instructorData.display_name,
              user_email: instructorData.email,
              user_login: "",
              user_nicename: "",
              user_registered: "",
              user_status: 0,
              is_active: true,
              is_verified: true,
              created_at: "",
              updated_at: "",
              last_login: "",
              profile: {
                profile_photo: instructorData.profile?.profile_photo,
                bio: instructorData.profile?.bio,
                qualifications: instructorData.profile?.qualifications,
                experience_years: instructorData.profile?.experience_years
              }
            },
            categories: course.category ? [{
              id: course.category_id || 0,
              name: course.category,
              slug: course.category.toLowerCase(),
              description: course.category_description || "",
              created_at: course.category_created_at || ""
            }] : [],
            lessons: Array.from({ length: course.stats?.lessons || 0 }) as any,
            created_at: course.created_at,
            updated_at: course.updated_at
          }))

          setInstructorCourses(transformedCourses)

          // Calculate instructor stats
          const stats: InstructorStats = {
            total_courses: transformedCourses.length,
            total_students: transformedCourses.reduce((sum, course) => sum + course.total_enrollments, 0),
            average_rating: transformedCourses.length > 0
              ? transformedCourses.reduce((sum, course) => sum + course.average_rating, 0) / transformedCourses.length
              : 0,
            total_reviews: transformedCourses.reduce((sum, course) => sum + course.total_reviews, 0)
          }
          setInstructorStats(stats)

        } catch (coursesError) {
          console.error('Error fetching instructor courses:', coursesError)
          setInstructorCourses([])
          setInstructorStats({
            total_courses: 0,
            total_students: 0,
            average_rating: 0,
            total_reviews: 0
          })
        }

      } catch (error) {
        console.error('Error fetching instructor data:', error)
        setError('Failed to load instructor profile')
      } finally {
        setLoading(false)
      }
    }

    fetchInstructorData()
  }, [id, instructorId])

  const formatExperience = (years: number) => {
    if (years === 0) return "New Instructor"
    if (years === 1) return "1 Year Experience"
    return `${years}+ Years Experience`
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading instructor profile...</p>
        </div>
      </div>
    )
  }

  if (error || !instructor) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <User className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Instructor Not Found</h2>
          <p className="text-gray-600 mb-6">
            {error || "The instructor you're looking for doesn't exist."}
          </p>
          <Link to="/courses" className="text-primary-600 hover:underline">
            Browse all courses
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white">
      {/* Header Section */}
      <div className="relative bg-gradient-to-br from-primary-600 to-primary-800 text-white overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 left-0 w-96 h-96 bg-white rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute bottom-0 right-0 w-96 h-96 bg-primary-400 rounded-full blur-3xl animate-pulse delay-1000"></div>
        </div>

        <div className="container-custom py-16 relative z-10">
          <div className="max-w-4xl mx-auto text-center">
            <Avatar size="xl" className="w-32 h-32 mx-auto mb-6 ring-4 ring-white/30">
              {getMediaUrl(instructor.profile_photo) && (
                <AvatarImage src={getMediaUrl(instructor.profile_photo)} />
              )}
              <AvatarFallback className="bg-primary-700 text-white text-4xl font-bold">
                {instructor.display_name.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>

            <h1 className="text-4xl font-bold mb-4">
              {instructor.display_name}
            </h1>

            <p className="text-xl text-primary-100 mb-4 max-w-2xl mx-auto">
              {instructor.bio}
            </p>

            <div className="flex items-center justify-center gap-6 mb-6">
              {instructorStats && (
                <div className="flex items-center gap-2">
                  <StarRating rating={instructorStats.average_rating} />
                  <span className="font-semibold">
                    {instructorStats.average_rating.toFixed(1)}
                  </span>
                  <span className="text-primary-200">
                    ({instructorStats.total_reviews} reviews)
                  </span>
                </div>
              )}
              <Badge className="bg-primary-700 text-white border-0">
                {formatExperience(instructor.experience_years)}
              </Badge>
            </div>

            {/* Social Links */}
            <div className="flex items-center justify-center gap-4">
              {instructor.social_links.website && (
                <a
                  href={instructor.social_links.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-white/10 hover:bg-white/20 p-3 rounded-full transition-colors"
                >
                  <Globe className="w-5 h-5" />
                </a>
              )}
              {instructor.social_links.facebook && (
                <a
                  href={instructor.social_links.facebook}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-white/10 hover:bg-white/20 p-3 rounded-full transition-colors"
                >
                  <Facebook className="w-5 h-5" />
                </a>
              )}
              {instructor.social_links.twitter && (
                <a
                  href={instructor.social_links.twitter}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-white/10 hover:bg-white/20 p-3 rounded-full transition-colors"
                >
                  <Twitter className="w-5 h-5" />
                </a>
              )}
              {instructor.social_links.linkedin && (
                <a
                  href={instructor.social_links.linkedin}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-white/10 hover:bg-white/20 p-3 rounded-full transition-colors"
                >
                  <Linkedin className="w-5 h-5" />
                </a>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Stats Section */}
      {instructorStats && (
        <div className="container-custom py-12">
          <div className="max-w-6xl mx-auto">
            <div className="grid md:grid-cols-4 gap-6">
              <Card className="text-center">
                <CardContent className="pt-6">
                  <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <BookOpen className="w-6 h-6 text-primary-600" />
                  </div>
                  <div className="text-2xl font-bold text-gray-900">
                    {instructorStats.total_courses}
                  </div>
                  <p className="text-gray-600">Courses</p>
                </CardContent>
              </Card>

              <Card className="text-center">
                <CardContent className="pt-6">
                  <div className="w-12 h-12 bg-success-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Users className="w-6 h-6 text-success-600" />
                  </div>
                  <div className="text-2xl font-bold text-gray-900">
                    {instructorStats.total_students.toLocaleString()}
                  </div>
                  <p className="text-gray-600">Students</p>
                </CardContent>
              </Card>

              <Card className="text-center">
                <CardContent className="pt-6">
                  <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Star className="w-6 h-6 text-yellow-600" />
                  </div>
                  <div className="text-2xl font-bold text-gray-900">
                    {instructorStats.average_rating.toFixed(1)}
                  </div>
                  <p className="text-gray-600">Average Rating</p>
                </CardContent>
              </Card>

              <Card className="text-center">
                <CardContent className="pt-6">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Award className="w-6 h-6 text-blue-600" />
                  </div>
                  <div className="text-2xl font-bold text-gray-900">
                    {instructorStats.total_reviews}
                  </div>
                  <p className="text-gray-600">Reviews</p>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      )}

      {/* Qualifications */}
      {instructor.qualifications.length > 0 && (
        <div className="container-custom py-12">
          <div className="max-w-6xl mx-auto">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Award className="w-5 h-5 text-primary-600" />
                  Qualifications & Expertise
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {instructor.qualifications.map((qualification, index) => (
                    <Badge key={index} variant="secondary" className="text-sm">
                      {qualification}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Courses Section */}
      <div className="container-custom py-12">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-3xl font-bold text-gray-900">
              Courses by {instructor.display_name}
            </h2>
            <Button variant="outline" asChild>
              <Link to="/courses">
                View All Courses
                <ChevronRight className="w-4 h-4 ml-2" />
              </Link>
            </Button>
          </div>

          {instructorCourses.length === 0 ? (
            <Card>
              <CardContent className="py-16 text-center">
                <BookOpen className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  No courses available yet
                </h3>
                <p className="text-gray-600 mb-6">
                  {instructor.display_name} hasn't published any courses yet.
                </p>
                <Button asChild>
                  <Link to="/courses">
                    Browse Other Courses
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {instructorCourses.map((course) => (
                <CourseCard
                  key={course.id}
                  course={course}
                  variant="default"
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}