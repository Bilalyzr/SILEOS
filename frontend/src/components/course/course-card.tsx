import * as React from "react"
import { Link } from "react-router-dom"
import { Clock, Users, Star, BookOpen, Play } from "lucide-react"
import { Card, CardContent, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { StarRating } from "@/components/ui/star-rating"
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar"
import { Course } from "@/types"
import { cn } from "@/utils/cn"
import { getMediaUrl, getLocalCourseThumbnail } from "@/utils/media"
import { useStudentLiveClasses } from '@/components/live/StudentLiveClasses'

interface CourseCardProps {
  course: Course
  variant?: "default" | "enrolled" | "compact"
  showProgress?: boolean
  progress?: number
  className?: string
}

export const CourseCard: React.FC<CourseCardProps> = ({
  course,
  variant = "default",
  showProgress = false,
  progress = 0,
  className,
}) => {
  const isLive = useStudentLiveClasses().some(c => c.course_id === Number(course.id))
  const isPaid = course.course_price_type === "paid"
  const hasDiscount = course.course_sale_price > 0 && course.course_sale_price < course.course_price
  const displayPrice = hasDiscount ? course.course_sale_price : course.course_price

  const formatPrice = (price: number) => {
    if (price === 0) return "Free"
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(price)
  }

  const getLevelBadgeVariant = (level?: string) => {
    switch ((level || "").toLowerCase()) {
      case "beginner":
        return "success"
      case "intermediate":
        return "warning"
      case "advanced":
        return "danger"
      default:
        return "default"
    }
  }

  const getInstructorInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2)
  }

  const courseRef = course.slug || course.post_name || course.id
  // Prefer the DB thumbnail — it is per-course and unambiguous. The bundled
  // artwork is only a fallback for courses with no thumbnail set, because its
  // title-keyword matching cannot tell the two "Full Stack ... with AI"
  // courses apart (both satisfy the AI test, so the Advance one would get the
  // other course's image).
  const thumbSrc =
    course.course_thumbnail || getLocalCourseThumbnail(course.post_title) || "/placeholder-course.svg"

  if (variant === "compact") {
    return (
      <Link to={`/courses/${courseRef}`} className="group block">
        <Card
          className={cn(
            "overflow-hidden rounded-2xl glass-panel transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_16px_40px_rgba(249,115,22,0.16)] hover:border-orange-200",
            className
          )}
        >
          <div className="flex gap-4 p-3">
            <div className="relative w-32 h-20 flex-shrink-0 overflow-hidden rounded-xl">
              <img
                src={thumbSrc}
                alt={course.post_title}
                width={128}
                height={80}
                loading="lazy"
                decoding="async"
                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).src = "/placeholder-course.svg"
                }}
              />
              {course.course_intro_video && (
                <div className="absolute inset-0 flex items-center justify-center bg-secondary-900/40">
                  <Play className="w-4 h-4 text-white" fill="currentColor" />
                </div>
              )}
            </div>
            <div className="flex-1 min-w-0 py-0.5">
              <h3 className="font-heading font-semibold text-sm line-clamp-2 mb-1 text-secondary-900 group-hover:text-primary-600 transition-colors">
                {course.post_title}
              </h3>
              {isLive && <Badge variant="danger">Live now</Badge>}
              <div className="flex items-center gap-2 text-xs text-neutral-600 mb-2">
                <StarRating rating={course.average_rating ?? 0} size="sm" showValue />
                <span>({course.total_reviews})</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs text-neutral-500">
                  <Users className="w-3 h-3" />
                  <span>{course.total_enrollments}</span>
                </div>
                <div className="flex items-baseline gap-2">
                  {hasDiscount && (
                    <span className="text-xs text-neutral-400 line-through">
                      {formatPrice(course.course_price)}
                    </span>
                  )}
                  <div className="font-bold text-primary-600 text-sm">
                    {formatPrice(displayPrice)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </Link>
    )
  }

  return (
    <Link to={`/courses/${courseRef}`} className="group block h-full">
      <Card
        className={cn(
          "relative flex h-full flex-col overflow-hidden rounded-2xl glass-panel transition-all duration-300 hover:-translate-y-1.5 hover:shadow-[0_18px_44px_rgba(249,115,22,0.18)] hover:border-orange-200",
          className
        )}
      >
        <div className="relative">
          <div className="aspect-video overflow-hidden" style={{ aspectRatio: "16 / 9" }}>
            <img
              src={thumbSrc}
              alt={course.post_title}
              width={600}
              height={340}
              loading="lazy"
              decoding="async"
              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).src = "/placeholder-course.svg"
              }}
            />
          </div>

          {/* Gradient scrim for badge/label legibility */}
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-secondary-900/60 to-transparent" />

          {/* Video overlay */}
          {course.course_intro_video && (
            <div className="absolute inset-0 flex items-center justify-center bg-secondary-900/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
              <div className="w-14 h-14 bg-white rounded-full flex items-center justify-center shadow-large">
                <Play className="w-6 h-6 text-primary-600 ml-0.5" fill="currentColor" />
              </div>
            </div>
          )}

          {/* Badges */}
          <div className="absolute top-3 left-3 flex flex-wrap gap-2">
            {isLive && <Badge variant="danger">Live now</Badge>}
            <Badge variant={getLevelBadgeVariant(course.course_level)} className="capitalize shadow-soft">
              {course.course_level}
            </Badge>
            {!isPaid && (
              <Badge variant="success" className="shadow-soft">Free</Badge>
            )}
            {hasDiscount && (
              <Badge variant="danger" className="shadow-soft">
                Discounted · {Math.round(((course.course_price - course.course_sale_price) / course.course_price) * 100)}% OFF
              </Badge>
            )}
          </div>

          {/* Wishlist button */}
          <div className="absolute top-3 right-3 translate-y-1 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-300">
            <Button
              size="icon"
              variant="ghost"
              className="bg-white/90 hover:bg-white rounded-full shadow-soft"
              aria-label="Add to wishlist"
            >
              <Star className="w-4 h-4" />
            </Button>
          </div>

          {/* Category chip */}
          {course.categories?.[0]?.name && (
            <span className="absolute bottom-3 left-3 inline-flex items-center rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-secondary-900 backdrop-blur-sm">
              {course.categories[0].name}
            </span>
          )}
        </div>

        <CardContent className="flex flex-1 flex-col p-5">
          {/* Instructor + rating */}
          <div className="flex items-center justify-between gap-2 mb-3">
            <div className="flex items-center gap-2 min-w-0">
              <Avatar size="sm">
                <AvatarImage src={getMediaUrl(course.instructor?.avatar || course.instructor?.profile?.profile_photo)} />
                <AvatarFallback>
                  {getInstructorInitials(course.instructor?.display_name || course.instructor?.display_name || "Instructor")}
                </AvatarFallback>
              </Avatar>
              <span className="text-sm text-neutral-600 truncate">
                {course.instructor?.display_name || course.instructor?.display_name || "Instructor"}
              </span>
            </div>
            <div className="flex flex-shrink-0 items-center gap-1 rounded-full bg-warning-50 px-2.5 py-1 text-xs font-bold text-warning-700">
              <Star className="w-3 h-3 fill-current" />
              {(course.average_rating ?? 0).toFixed(1)}
            </div>
          </div>

          {/* Workshops / Hours / College (below Taught By) */}
          {((course.num_offline_workshops ?? 0) > 0 || (course.num_hours ?? 0) > 0 || course.institution) && (
            <div className="flex flex-col gap-1 mb-3 text-sm text-neutral-700 bg-primary-50/60 rounded-xl p-2.5">
              {(course.num_offline_workshops ?? 0) > 0 && (
                <div className="flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-primary-600 flex-shrink-0" />
                  <span className="text-xs font-medium text-primary-600 uppercase tracking-wide">Offline Workshops:</span>
                  <span className="font-medium">{course.num_offline_workshops}</span>
                </div>
              )}
              {(course.num_hours ?? 0) > 0 && (
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-primary-600 flex-shrink-0" />
                  <span className="text-xs font-medium text-primary-600 uppercase tracking-wide">Hours:</span>
                  <span className="font-medium">{course.num_hours}</span>
                </div>
              )}
              {course.institution && (
                <div className="flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5 text-primary-600 flex-shrink-0" />
                  <span className="text-xs font-medium text-primary-600 uppercase tracking-wide">College:</span>
                  <span className="truncate">{course.institution}</span>
                </div>
              )}
            </div>
          )}

          {/* Title */}
          <h3 className="font-heading font-bold text-lg leading-snug mb-2 line-clamp-2 text-secondary-900 group-hover:text-primary-600 transition-colors">
            {course.post_title}
          </h3>

          {/* Description */}
          <p className="text-sm text-neutral-600 mb-4 line-clamp-2">
            {course.post_excerpt || (course.post_content || "").replace(/<[^>]*>/g, "").slice(0, 100)}
          </p>

          {/* Stats (pinned to the bottom of the flexible content area) */}
          <div className="mt-auto flex items-center gap-4 text-xs text-neutral-500 border-t border-neutral-100 pt-3">
            <div className="flex items-center gap-1.5">
              <BookOpen className="w-4 h-4 text-neutral-400" />
              {/* API returns stats.lessons with count, stats.duration with total minutes */}
              <span>{course.stats?.lessons ?? course.lesson_count ?? course.lessons?.length ?? 0} lessons</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-neutral-400" />
              <span>{course.stats?.duration ? `${Math.round(course.stats.duration / 60)}h ${course.stats.duration % 60}m` : "Self-paced"}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Users className="w-4 h-4 text-neutral-400" />
              <span>{course.total_enrollments}</span>
            </div>
          </div>

          {/* Progress (if enrolled) */}
          {showProgress && variant === "enrolled" && (
            <div className="mt-3">
              <Progress
                value={progress}
                showLabel
                label="Progress"
                variant={progress === 100 ? "success" : "default"}
              />
            </div>
          )}
        </CardContent>

        <CardFooter className="px-5 pb-5 pt-0">
          <div className="flex items-center justify-between w-full">
            {!course.is_enrolled && (
              <div className="flex flex-col leading-none">
                {hasDiscount && (
                  <span className="text-xs text-neutral-400 line-through mb-0.5">
                    {formatPrice(course.course_price)}
                  </span>
                )}
                <span className="text-xl font-extrabold text-secondary-900">
                  {formatPrice(displayPrice)}
                </span>
              </div>
            )}

            {course.is_enrolled ? (
              <Button size="sm" variant="outline" className="ml-auto rounded-xl">
                {progress > 0 ? "Continue Learning" : "Start Learning"}
              </Button>
            ) : variant === "enrolled" ? (
              <Button size="sm" variant="outline" className="rounded-xl">
                Continue Learning
              </Button>
            ) : (
              <Button size="sm" className="rounded-xl shadow-soft">
                {isPaid ? "Enroll Now" : "Enroll for Free"}
              </Button>
            )}
          </div>
        </CardFooter>
      </Card>
    </Link>
  )
}
