/**
 * Split a newline-delimited course field into trimmed, non-empty lines.
 *
 * These fields are free text and are routinely blank. `''.split('\n')` returns
 * [''], so the Overview tab rendered a tick or bullet with no text beside it,
 * under a heading with nothing in it — the stray markers and empty sections
 * that made the layout look misaligned.
 */
const toLines = (value?: string): string[] =>
  (value || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

function ShowMoreContent({ content }: { content: string }) {
  const [expanded, setExpanded] = React.useState(false);
  if (!content) return null;
  const isLong = content.length > 400;
  return (
    <div>
      <div
        className={[
          "prose max-w-none overflow-hidden transition-all duration-300 text-justify font-[Inter] leading-relaxed text-gray-700",
          !expanded && isLong ? "max-h-32 relative" : "",
        ].join(" ")}
        style={
          !expanded && isLong
            ? {
                maskImage:
                  "linear-gradient(to bottom, black 60%, transparent 100%)",
                WebkitMaskImage:
                  "linear-gradient(to bottom, black 60%, transparent 100%)",
              }
            : {}
        }
        dangerouslySetInnerHTML={{ __html: sanitizeHtml(content) }}
      />
      {isLong && (
        <button
          onClick={() => setExpanded((e) => !e)}
          className="mt-3 text-orange-500 font-semibold text-sm hover:text-orange-600 flex items-center gap-1"
        >
          {expanded ? "Show Less" : "Show More"}
        </button>
      )}
    </div>
  );
}

import * as React from "react";
import { StudentLiveClasses } from '@/components/live/StudentLiveClasses';
import { sanitizeHtml } from "@/utils/sanitize";
import { useParams, Link, useNavigate } from "react-router-dom";
import { instructorPath } from "@/utils/slug";
import {
  Play,
  Clock,
  Users,
  Star,
  Globe,
  Award,
  Heart,
  BookOpen,
  CheckCircle,
  PlayCircle,
  Lock,
  MessageSquare,
  Eye,
  X,
  ShoppingCart,
} from "lucide-react";
import { toast } from "react-hot-toast";
import { useCart } from "@/contexts/CartContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { StarRating } from "@/components/ui/star-rating";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { ShareButton } from "@/components/ui/share-button";
import * as Tabs from "@radix-ui/react-tabs";
import { useAuth } from "@/hooks/use-auth";
import { useSEO } from "@/hooks/use-seo";
import { Course } from "@/types";
import { api } from "@/api/axios";
import { VideoPlayer } from "@/components/video/video-player";
import { LessonPreviewModal } from "@/components/course/LessonPreviewModal";
import { track } from "@/api/funnel";
import { getMediaUrl } from "@/utils/media";

export const CourseDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const { addToCart, isInCart } = useCart();
  const [isEnrolled, setIsEnrolled] = React.useState(false);
  const [isInWishlist, setIsInWishlist] = React.useState(false);
  const [course, setCourse] = React.useState<Course | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [progress, setProgress] = React.useState(0);
  const [courseStatus, setCourseStatus] = React.useState<string>("");
  const [isCompleted, setIsCompleted] = React.useState(false);
  const [certPending, setCertPending] = React.useState(false);
  const [isAdminPreview, setIsAdminPreview] = React.useState(false);
  const [isVideoModalOpen, setIsVideoModalOpen] = React.useState(false);
  // Public lesson preview (2026-09-05): any lesson type, real player, glass popup
  const [previewLesson, setPreviewLesson] = React.useState<{
    id: number;
    title: string;
  } | null>(null);
  React.useEffect(() => {
    if (course?.id) track("course_view", course.id);
  }, [course?.id]);
  const freeLessons: any[] = (course?.lessons || []).filter(
    (l: any) => l.is_preview,
  );
  const [previewVideoUrl, setPreviewVideoUrl] = React.useState("");
  const [previewVideoTitle, setPreviewVideoTitle] = React.useState("");
  const [relatedCourses, setRelatedCourses] = React.useState<any[]>([]);
  const [reviews, setReviews] = React.useState<any[]>([]);
  const [reviewsSummary, setReviewsSummary] = React.useState<{
    average_rating: number;
    total_reviews: number;
  }>({ average_rating: 0, total_reviews: 0 });
  const [reviewForm, setReviewForm] = React.useState<{
    rating: number;
    review_title: string;
    review_content: string;
  }>({ rating: 5, review_title: "", review_content: "" });
  const [submittingReview, setSubmittingReview] = React.useState(false);

  React.useEffect(() => {
    const fetchCourse = async () => {
      try {
        setLoading(true);

        const response = await api.get(`/courses/${id}`);
        const data = response.data;

        // Transform API response to match Course interface
        const transformedCourse: Course = {
          post_author: data.instructor?.id ?? 0,
          post_date: data.created_at ?? "",
          post_status: data.status ?? "draft",
          post_name: data.slug ?? "",
          post_modified: data.updated_at ?? "",
          post_parent: 0,
          menu_order: 0,
          post_type: "courses",
          course_cover_image: data.cover_image ?? "",
          course_retakes_allowed: data.retakes_allowed ?? true,
          course_auto_start_next_lesson: data.auto_start_next_lesson ?? false,
          course_content_drip_type: data.content_drip_type ?? "",
          certificate_template: data.certificate_template ?? "",

          id: data.id,
          slug: data.slug,
          post_title: data.title,
          post_content: data.content,
          post_excerpt: data.excerpt,
          course_price: data.price,
          course_sale_price: data.sale_price || 0,
          course_price_type: data.price === 0 ? "free" : "paid",
          course_level: data.level,
          course_duration: (() => {
            const totalMins = data.stats?.duration || data.duration || 0;
            if (totalMins === 0) return "0 hours";
            const hrs = Math.floor(totalMins / 60);
            const mins = totalMins % 60;
            if (hrs > 0 && mins > 0) return `${hrs}h ${mins}m`;
            if (hrs > 0) return `${hrs} hour${hrs > 1 ? "s" : ""}`;
            return `${totalMins} min`;
          })(),
          course_benefits: Array.isArray(data.benefits)
            ? data.benefits.join("\n")
            : "",
          course_requirements: Array.isArray(data.requirements)
            ? data.requirements.join("\n")
            : "",
          course_target_audience: "",
          course_material_includes: "",
          course_thumbnail: data.thumbnail,
          course_intro_video: data.intro_video || "",
          average_rating: data.rating,
          total_reviews: 0, // API doesn't provide review count in stats
          total_enrollments: data.stats?.students || 0,
          num_offline_workshops: data.num_offline_workshops || 0,
          num_hours: data.num_hours || 0,
          institution: data.institution || "",
          instructor: {
            role: "instructor",
            id: data.instructor?.id || 0,
            display_name: data.instructor?.name || "Unknown",
            avatar: data.instructor?.avatar || "",
            user_email: "",
            user_login: "",
            user_nicename: "",
            user_registered: "",
            user_status: 0,
            is_active: true,
            is_verified: true,
            created_at: "",
            updated_at: "",
            last_login: "",
          },
          categories: [],
          lessons: data.lessons || [],
          // Authoritative lesson count from the serializer. Falls back to the
          // array length so it stays correct even if `stats` is ever omitted.
          lesson_count: data.stats?.lessons ?? (data.lessons?.length || 0),
          created_at: data.created_at,
          updated_at: data.updated_at,
        };

        setCourse(transformedCourse);
        setIsEnrolled(data.is_enrolled || false);
        setCourseStatus(data.status || "publish");

        // S-H1: reflect actual wishlist membership rather than always
        // starting from "not wishlisted". Best-effort — an unauthenticated
        // viewer or a failed fetch just leaves the heart unfilled.
        if (isAuthenticated) {
          try {
            const wishlistRes = await api.get("/wishlist");
            const wishlistCourses = wishlistRes.data?.courses || [];
            setIsInWishlist(wishlistCourses.some((c: any) => c.id === data.id));
          } catch {
            // non-fatal — heart just starts unfilled
          }
        }

        // Check if admin is previewing unpublished course
        if (
          user?.role === "admin" &&
          data.status !== "publish" &&
          data.status !== "published"
        ) {
          setIsAdminPreview(true);
        }

        // Fetch progress if enrolled
        if (data.is_enrolled && isAuthenticated) {
          try {
            const progressResponse = await api.get(`/courses/${id}/progress`);
            const progressData = progressResponse.data;
            // The backend progress payload exposes `overall_progress`
            // (there is no `progress_percentage` key on this response).
            setProgress(progressData.overall_progress || 0);

            // Check if course is completed (100% progress or completion_date exists)
            setIsCompleted(
              progressData.overall_progress >= 100 ||
                !!progressData.completion_date,
            );
          } catch (err) {
            console.error("Error fetching progress:", err);
          }
        } else {
          // Reset completion status if not enrolled
          setIsCompleted(false);
        }
        // Fetch related courses by same instructor
        try {
          const allRes = await api.get("/courses?limit=20");
          const allCourses = allRes.data?.courses || allRes.data || [];
          // "More Courses by <instructor>" — keep the same instructor's other
          // courses. Exclude THIS course by numeric id (the URL param is now a
          // slug, so the old parseInt(id) was NaN and excluded nothing).
          const sameInstructor = allCourses.filter(
            (c: any) =>
              c.id !== data.id && c.instructor?.id === data.instructor?.id,
          );
          // Fall back to other courses if this instructor has no others.
          const pool =
            sameInstructor.length > 0
              ? sameInstructor
              : allCourses.filter((c: any) => c.id !== data.id);
          setRelatedCourses(pool.slice(0, 3));
        } catch {}
      } catch (error) {
        console.error("Error fetching course:", error);
        setCourse(null);
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchCourse();
    }
  }, [id, isAuthenticated, user?.role]);

  // S-H1: wishlist heart was a local-only toggle (no backend call at all).
  // POST/DELETE /wishlist already existed (wishlist.py:45,94) — the trailing
  // slash quirk on the collection routes is fixed at the axios layer
  // (api/axios.ts's trailingSlashEndpoints), not here. Optimistic UI with
  // rollback on failure, since the heart is a low-stakes, frequently
  // clicked control.
  const [wishlistBusy, setWishlistBusy] = React.useState(false);

  const handleWishlist = async () => {
    if (!isAuthenticated) {
      toast.error("Please login to use your wishlist");
      return;
    }
    if (!course || wishlistBusy) return;

    const nextState = !isInWishlist;
    setIsInWishlist(nextState);
    setWishlistBusy(true);
    try {
      if (nextState) {
        await api.post("/wishlist", { course_id: course.id });
        toast.success("Added to wishlist");
      } else {
        await api.delete(`/wishlist/${course.id}`);
        toast.success("Removed from wishlist");
      }
    } catch (error: any) {
      setIsInWishlist(!nextState); // rollback
      toast.error(error?.response?.data?.detail || "Failed to update wishlist");
    } finally {
      setWishlistBusy(false);
    }
  };

  const handleAddToCart = () => {
    if (!course) return;
    addToCart({ courseId: course.id, title: course.post_title,
      instructor: (course as any).instructor?.display_name || "SashaInfinity",
      price: course.course_price,
      salePrice: course.course_sale_price != null && course.course_sale_price > 0 && course.course_sale_price < course.course_price ? course.course_sale_price : undefined,
      thumbnail: course.course_thumbnail || "", level: course.course_level || "Beginner",
      rating: course.average_rating || undefined });
  };

  // Build share payload. `shareUrl` is always absolute & slug-based when
  // a slug is available so receivers (WhatsApp, X, …) land on the pretty
  // URL and the crawler can fetch our OG tags on that same URL.
  // SEO / Open Graph meta tags — set dynamically for social sharing
  // NOTE: Social crawlers (WhatsApp, X, LinkedIn) fetch the raw HTML; since
  // this is a Vite SPA with no SSR, external previews will fall back to the
  // static index.html meta. For full social media preview support, consider
  // implementing SSR with a solution like Next.js or adding prerendering.
  useSEO(
    course
      ? {
          title: course.post_title,
          description: (course.post_excerpt || course.post_content || "")
            .replace(/<[^>]*>/g, "")
            .slice(0, 160),
          // Convert relative URLs to absolute for social media crawlers
          image: course.course_thumbnail?.startsWith("http")
            ? course.course_thumbnail
            : course.course_thumbnail
              ? `https://sashainfinity.com${course.course_thumbnail}`
              : undefined,
          url: `${window.location.origin}/api/v1/share/courses/${course.id}`,
          type: "website",
        }
      : {},
  );

  // When the course is completed, a certificate is either issued (endpoint 200)
  // or being held for instructor/admin approval (endpoint 404) — surface that.
  React.useEffect(() => {
    const courseId = (course as any)?.id;
    if (!isCompleted || !courseId || !isAuthenticated) {
      setCertPending(false);
      return;
    }
    api
      .get(`/certificates/course/${courseId}`)
      .then(() => setCertPending(false))
      .catch((err) => setCertPending(err?.response?.status === 404));
  }, [isCompleted, course, isAuthenticated]);

  // Load reviews whenever the course changes.
  React.useEffect(() => {
    if (!course) return;
    let cancelled = false;
    (async () => {
      try {
        const resp = await api.get(`/courses/${course.id}/reviews`);
        if (cancelled) return;
        setReviews(resp.data?.reviews || []);
        setReviewsSummary({
          average_rating: resp.data?.average_rating || 0,
          total_reviews: resp.data?.total_reviews || 0,
        });
      } catch {
        if (!cancelled) {
          setReviews([]);
          setReviewsSummary({ average_rating: 0, total_reviews: 0 });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [course]);

  const submitReview = async () => {
    if (!course) return;
    if (!isAuthenticated) {
      toast.error("Please login to leave a review");
      return;
    }
    if (!isEnrolled) {
      toast.error("You must be enrolled to review this course");
      return;
    }
    if (reviewForm.rating < 1 || reviewForm.rating > 5) {
      toast.error("Please pick a rating between 1 and 5");
      return;
    }
    if (!reviewForm.review_content.trim()) {
      toast.error("Please write a review");
      return;
    }
    setSubmittingReview(true);
    try {
      await api.post(`/courses/${course.id}/reviews`, reviewForm);
      toast.success("Review submitted — pending approval");
      setReviewForm({ rating: 5, review_title: "", review_content: "" });
      // Reload reviews after submission
      const resp = await api.get(`/courses/${course.id}/reviews`);
      setReviews(resp.data?.reviews || []);
      setReviewsSummary({
        average_rating: resp.data?.average_rating || 0,
        total_reviews: resp.data?.total_reviews || 0,
      });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to submit review");
    } finally {
      setSubmittingReview(false);
    }
  };

  const formatPrice = (price: number) => {
    if (price === 0) return "Free";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(price);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading course details...</p>
        </div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Course not found
          </h2>
          <p className="text-gray-600 mb-4">
            The course you're looking for doesn't exist.
          </p>
          <Link to="/courses" className="text-brand-600 hover:underline">
            Browse all courses
          </Link>
        </div>
      </div>
    );
  }

  const hasDiscount =
    course.course_sale_price > 0 &&
    course.course_sale_price < course.course_price;
  const displayPrice = hasDiscount
    ? course.course_sale_price
    : course.course_price;

  return (
    <div className="rd-course-detail min-h-screen">
      {isEnrolled && !isAdminPreview && <div className="container-custom"><StudentLiveClasses courseId={Number(course.id)}/><a className="sf-secondary" href={`/offline.html?course=${course.id}`}>Download lessons & labs for offline learning</a></div>}
      {/* Admin Preview Banner */}
      {isAdminPreview && (
        <div className="bg-yellow-500 border-b-4 border-yellow-600">
          <div className="container-custom py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="bg-yellow-600 text-white px-3 py-1 rounded-full text-sm font-bold">
                  ADMIN PREVIEW
                </div>
                <div className="text-yellow-900 font-medium">
                  This course is currently{" "}
                  <span className="font-bold uppercase">{courseStatus}</span>{" "}
                  and not visible to students.
                </div>
              </div>
              <Link
                to="/admin/courses"
                className="bg-white text-yellow-700 hover:bg-yellow-50 px-4 py-2 rounded-lg font-medium text-sm transition-colors"
              >
                Back to Admin
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Enhanced Hero Section with Gradient */}
      <div className="relative si-hero border-b border-orange-100 overflow-hidden">
        {/* Animated background patterns */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 left-0 w-96 h-96 bg-primary-500 rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute bottom-0 right-0 w-96 h-96 bg-success-500 rounded-full blur-3xl animate-pulse delay-1000"></div>
        </div>

        <div className="container-custom py-8 relative z-10">
          <div className="grid lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2">
              {/* Breadcrumb */}
              <nav className="mb-6">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-gray-500">
                  <Link
                    to="/"
                    className="hover:text-primary-600 transition-colors"
                  >
                    Home
                  </Link>
                  <span className="text-gray-300">/</span>
                  <Link
                    to="/courses"
                    className="hover:text-primary-600 transition-colors"
                  >
                    Courses
                  </Link>
                  <span className="text-gray-300">/</span>
                  <span className="text-gray-900 font-medium line-clamp-1">
                    {course.post_title}
                  </span>
                </div>
              </nav>

              {/* Enhanced Course Info */}
              <div className="space-y-6">
                <div>
                  {/* Badge for course level */}
                  <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary-500/20 border border-primary-400/30 rounded-full mb-4">
                    <Award className="w-4 h-4 text-primary-400" />
                    <span className="text-sm font-medium text-primary-300">
                      {course.course_level} Level
                    </span>
                  </div>

                  <h1 className="text-3xl lg:text-4xl font-extrabold mb-4 text-gray-900 leading-tight tracking-tight font-[Lexend Deca]">
                    {course.post_title}
                  </h1>
                  <p className="text-base text-gray-600 mb-6 leading-relaxed text-justify">
                    {course.post_excerpt}
                  </p>
                </div>

                {/* Enhanced Meta Info Cards */}
                <div className="rd-course-facts">
                  <div className="bg-gray-50 rounded-xl p-4 border border-gray-200 hover:bg-orange-50 transition-all group">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-yellow-500/20 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                        <Star className="w-5 h-5 text-yellow-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-1 mb-1">
                          <StarRating
                            rating={course.average_rating}
                            size="sm"
                          />
                        </div>
                        <p className="text-xs text-neutral-400">
                          {course.total_reviews} reviews
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-xl p-4 border border-gray-200 hover:bg-orange-50 transition-all group">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary-500/20 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                        <Users className="w-5 h-5 text-primary-400" />
                      </div>
                      <div>
                        <p className="text-lg font-bold text-gray-900">
                          {course.total_enrollments.toLocaleString()}
                        </p>
                        <p className="text-xs text-neutral-400">Students</p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-xl p-4 border border-gray-200 hover:bg-orange-50 transition-all group">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-success-500/20 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                        <Clock className="w-5 h-5 text-success-400" />
                      </div>
                      <div>
                        <p className="text-lg font-bold text-gray-900">
                          {course.course_duration}
                        </p>
                        <p className="text-xs text-neutral-400">Duration</p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-xl p-4 border border-gray-200 hover:bg-orange-50 transition-all group">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                        <Globe className="w-5 h-5 text-blue-400" />
                      </div>
                      <div>
                        <p className="text-lg font-bold text-gray-900">
                          English
                        </p>
                        <p className="text-xs text-neutral-400">Language</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Enhanced Instructor Card */}
                <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                  <p className="text-xs text-neutral-400 mb-3 uppercase tracking-wide">
                    Taught by
                  </p>
                  <div className="flex items-center gap-4">
                    <Avatar size="lg" className="ring-2 ring-primary-500/50">
                      {getMediaUrl(course.instructor?.avatar) && (
                        <AvatarImage
                          src={getMediaUrl(course.instructor?.avatar)}
                          alt={course.instructor?.display_name}
                        />
                      )}
                      <AvatarFallback className="bg-primary-600 text-white text-lg font-bold">
                        {course.instructor?.display_name?.charAt(0) || "I"}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <p className="font-bold text-gray-900 text-lg">
                        {course.instructor?.display_name}
                      </p>
                      <p className="text-sm text-neutral-400">
                        Expert Instructor
                      </p>

                      {/* Workshop Info */}
                      {(course.num_offline_workshops ?? 0) > 0 && (
                        <div className="flex items-center gap-3 mt-2 text-sm">
                          <div className="flex items-center gap-1.5 text-orange-600">
                            <BookOpen className="w-3.5 h-3.5" />
                            <span className="font-medium">
                              {course.num_offline_workshops} Workshop
                              {(course.num_offline_workshops ?? 0) > 1
                                ? "s"
                                : ""}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-primary-500 text-primary-600 hover:bg-primary-50"
                      asChild
                    >
                      <Link
                        to={instructorPath(
                          (course.instructor as any)?.id ?? "",
                          (course.instructor as any)?.name,
                        )}
                      >
                        View Profile
                      </Link>
                    </Button>
                  </div>

                  {/* Workshops / Hours (below Taught By) */}
                  {((course.num_offline_workshops ?? 0) > 0 ||
                    (course.num_hours ?? 0) > 0) && (
                    <div className="flex flex-col gap-2 mt-4 pt-4 border-t border-gray-200 text-sm text-neutral-700">
                      {(course.num_offline_workshops ?? 0) > 0 && (
                        <div className="flex items-center gap-2">
                          <BookOpen className="w-4 h-4 text-orange-600 flex-shrink-0" />
                          <span className="text-xs font-medium text-orange-600 uppercase tracking-wide">
                            No. of Offline Workshops:
                          </span>
                          <span className="font-medium">
                            {course.num_offline_workshops}
                          </span>
                        </div>
                      )}
                      {(course.num_hours ?? 0) > 0 && (
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4 text-orange-600 flex-shrink-0" />
                          <span className="text-xs font-medium text-orange-600 uppercase tracking-wide">
                            No. of Offline Hours:
                          </span>
                          <span className="font-medium">
                            {course.num_hours}
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Enhanced Categories */}
                {course.categories && course.categories.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm text-neutral-400 mr-2">
                      Topics:
                    </span>
                    {course.categories.map((category) => (
                      <Badge
                        key={category.id}
                        className="bg-primary-500/20 text-primary-300 border-primary-400/30 hover:bg-primary-500/30"
                      >
                        {category.name}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Enhanced Course Preview Card */}
            <div className="lg:col-span-1">
              <Card className="rd-purchase-panel sticky top-8 overflow-hidden">
                <div className="aspect-video relative overflow-hidden group">
                  <img
                    src={course.course_thumbnail}
                    alt={course.post_title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  {course.course_intro_video && (
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent flex items-center justify-center group-hover:bg-black/60 transition-all">
                      <Button
                        size="lg"
                        className="bg-white text-primary-600 hover:bg-white/90 shadow-xl hover:scale-110 transition-all"
                        onClick={() => {
                          setPreviewVideoUrl(course.course_intro_video || "");
                          setPreviewVideoTitle(`Preview: ${course.post_title}`);
                          setIsVideoModalOpen(true);
                        }}
                      >
                        <Play className="w-6 h-6 mr-2" />
                        Preview Course
                      </Button>
                    </div>
                  )}
                  {/* Enrolled badge */}
                  {isEnrolled && !isAdminPreview && (
                    <div className="absolute top-4 right-4 bg-success-600 text-white px-3 py-1 rounded-full text-sm font-medium flex items-center gap-2 shadow-lg">
                      <CheckCircle className="w-4 h-4" />
                      Enrolled
                    </div>
                  )}
                  {/* Admin Preview badge on thumbnail */}
                  {isAdminPreview && (
                    <div className="absolute top-4 right-4 bg-yellow-600 text-white px-3 py-1 rounded-full text-sm font-medium flex items-center gap-2 shadow-lg">
                      <Eye className="w-4 h-4" />
                      Preview Mode
                    </div>
                  )}
                </div>

                <CardContent className="p-6 space-y-6">
                  {/* Price — hidden once enrolled (or in admin preview); an
                      enrolled student has already paid, so price is irrelevant. */}
                  {!isEnrolled && !isAdminPreview && (
                    <div className="bg-gradient-to-br from-primary-50 to-primary-100 rounded-xl p-4 border-2 border-primary-200">
                      <div className="flex items-baseline gap-3 mb-2">
                        <span className="text-4xl font-black text-primary-600">
                          {formatPrice(displayPrice)}
                        </span>
                        {hasDiscount && (
                          <span className="text-xl text-neutral-500 line-through">
                            {formatPrice(course.course_price)}
                          </span>
                        )}
                      </div>
                      {hasDiscount && (
                        <Badge className="bg-danger-600 text-white">
                          Save{" "}
                          {Math.round(
                            ((course.course_price - course.course_sale_price) /
                              course.course_price) *
                              100,
                          )}
                          %
                        </Badge>
                      )}
                      {course.course_price_type === "free" && (
                        <p className="text-sm text-primary-700 mt-2 font-medium">
                          Limited time offer!
                        </p>
                      )}
                    </div>
                  )}

                  {/* Enhanced Action Buttons */}
                  <div className="space-y-3">
                    {isEnrolled || isAdminPreview ? (
                      <>
                        {progress > 0 && !isAdminPreview && (
                          <div className="mb-3">
                            <div className="flex justify-between text-sm mb-2">
                              <span className="text-neutral-600 font-medium">
                                Your Progress
                              </span>
                              <span className="text-primary-600 font-bold">
                                {progress}%
                              </span>
                            </div>
                            <Progress value={progress} className="h-2" />
                          </div>
                        )}

                        {isCompleted ? (
                          <>
                            <div className="bg-success-50 border border-success-200 rounded-xl p-4 mb-3">
                              <div className="flex items-center gap-2 mb-2">
                                <CheckCircle className="w-5 h-5 text-success-600" />
                                <span className="font-semibold text-success-800">
                                  Course Completed!
                                </span>
                              </div>
                              <p className="text-sm text-success-700">
                                Congratulations! You have successfully completed
                                this course.
                              </p>
                            </div>
                            {certPending && (
                              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-3 text-sm text-amber-800">
                                Certificate pending instructor approval. You'll
                                be notified once your submission is approved.
                              </div>
                            )}
                            <Button
                              size="lg"
                              className="w-full bg-gradient-to-r from-success-600 to-success-700 hover:from-success-700 hover:to-success-800 shadow-lg hover:shadow-xl transition-all hover:-translate-y-0.5"
                              asChild
                            >
                              <Link
                                to={`/courses/${course.slug || course.id}/learn`}
                              >
                                <Award className="w-5 h-5 mr-2" />
                                Start Again
                              </Link>
                            </Button>
                          </>
                        ) : (
                          <Button
                            size="lg"
                            className="w-full bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 shadow-lg hover:shadow-xl transition-all hover:-translate-y-0.5"
                            asChild
                          >
                            <Link
                              to={`/courses/${course.slug || course.id}/learn`}
                            >
                              <PlayCircle className="w-5 h-5 mr-2" />
                              {isAdminPreview
                                ? "Preview Course Content"
                                : progress > 0
                                  ? "Continue Learning"
                                  : "Start Learning"}
                            </Link>
                          </Button>
                        )}
                      </>
                    ) : (
                      <>
                        {/* Unified Enroll Now button for all course types */}
                        <Button
                          size="lg"
                          className="w-full bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 shadow-lg hover:shadow-xl transition-all hover:-translate-y-0.5 text-lg font-bold"
                          onClick={() => navigate(`/checkout/${course.id}`)}
                        >
                          {course.course_price_type === "free" ? (
                            <>
                              <Award className="w-5 h-5 mr-2" />
                              Enroll Now
                            </>
                          ) : (
                            <>
                              <Play className="w-5 h-5 mr-2" />
                              Enroll Now
                            </>
                          )}
                        </Button>

                        <Button size="lg" variant="outline" className="w-full mt-2 border-orange-300 text-orange-700"
                          onClick={handleAddToCart} disabled={isInCart(course.id)}>
                          <ShoppingCart className="w-5 h-5 mr-2" />
                          {isInCart(course.id) ? "Already in Cart" : "Add to Cart"}
                        </Button>
                      </>
                    )}

                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        className="flex-1 hover:bg-red-50 hover:border-red-200 hover:text-red-600 transition-all"
                        onClick={handleWishlist}
                      >
                        <Heart
                          className={`w-4 h-4 mr-2 ${isInWishlist ? "fill-current text-red-500" : ""}`}
                        />
                        Wishlist
                      </Button>
                      <ShareButton
                        url={
                          course
                            ? `${window.location.origin}/api/v1/share/courses/${course.id}`
                            : undefined
                        }
                        title={course?.post_title}
                        description={(
                          course?.post_excerpt ||
                          course?.post_content ||
                          ""
                        )
                          .replace(/<[^>]*>/g, "")
                          .slice(0, 160)}
                        showLabel
                      />
                    </div>
                  </div>

                  {/* Course Includes */}
                  <div className="space-y-3">
                    <h4 className="font-bold text-gray-900 text-base">
                      This course includes:
                    </h4>
                    <div className="space-y-3">
                      <div className="flex items-center gap-3">
                        <PlayCircle className="w-5 h-5 text-primary-600 flex-shrink-0" />
                        <span className="text-gray-700 font-medium text-sm">
                          {course.stats?.duration
                            ? `${Math.round(course.stats.duration / 60)}h ${course.stats.duration % 60}m`
                            : "Self-paced"}{" "}
                          of content
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <BookOpen className="w-5 h-5 text-primary-600 flex-shrink-0" />
                        <span className="text-gray-700 font-medium text-sm">
                          {course.stats?.lessons ??
                            course.lesson_count ??
                            course.lessons?.length ??
                            0}{" "}
                          lessons
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <Globe className="w-5 h-5 text-primary-600 flex-shrink-0" />
                        <span className="text-gray-700 font-medium text-sm">
                          Full lifetime access
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <Award className="w-5 h-5 text-primary-600 flex-shrink-0" />
                        <span className="text-gray-700 font-medium text-sm">
                          Certificate of completion
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <Users className="w-5 h-5 text-primary-600 flex-shrink-0" />
                        <span className="text-gray-700 font-medium text-sm">
                          {course.total_enrollments} students enrolled
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container-custom py-12">
        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <Tabs.Root defaultValue="overview" className="w-full">
              <Tabs.List className="grid w-full grid-cols-2 sm:grid-cols-4 gap-1 bg-white rounded-lg p-1 shadow-soft">
                <Tabs.Trigger
                  value="overview"
                  className="px-3 sm:px-4 py-2 rounded-md font-medium text-sm text-center whitespace-nowrap data-[state=active]:bg-primary-600 data-[state=active]:text-white"
                >
                  Overview
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="curriculum"
                  className="px-3 sm:px-4 py-2 rounded-md font-medium text-sm text-center whitespace-nowrap data-[state=active]:bg-primary-600 data-[state=active]:text-white"
                >
                  Curriculum
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="instructor"
                  className="px-3 sm:px-4 py-2 rounded-md font-medium text-sm text-center whitespace-nowrap data-[state=active]:bg-primary-600 data-[state=active]:text-white"
                >
                  Instructor
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="reviews"
                  className="px-3 sm:px-4 py-2 rounded-md font-medium text-sm text-center whitespace-nowrap data-[state=active]:bg-primary-600 data-[state=active]:text-white"
                >
                  Reviews
                </Tabs.Trigger>
              </Tabs.List>

              {/* Overview Tab */}
              <Tabs.Content value="overview" className="mt-6">
                {freeLessons.length > 0 && !isEnrolled && !isAdminPreview && (
                  <div
                    className="glass-panel rounded-2xl p-4 mb-6 border-orange-200"
                    data-testid="free-lessons-strip"
                  >
                    <div className="flex flex-wrap items-center gap-3">
                      <div className="flex-1 min-w-[12rem]">
                        <p className="text-[11px] uppercase tracking-wide text-orange-700 font-semibold">
                          Try before you enrol
                        </p>
                        <p className="font-semibold text-gray-900">
                          {freeLessons.length} free lesson
                          {freeLessons.length === 1 ? "" : "s"} — no account
                          needed
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {freeLessons.slice(0, 3).map((l: any) => (
                          <button
                            key={l.id}
                            type="button"
                            className="si-btn-primary !py-1.5 !px-3 !text-xs"
                            onClick={() =>
                              setPreviewLesson({
                                id: l.id,
                                title: l.lesson_title || l.title,
                              })
                            }
                          >
                            <PlayCircle className="w-3.5 h-3.5" />{" "}
                            {(l.lesson_title || l.title || "Lesson").slice(
                              0,
                              34,
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
                <Card>
                  <CardHeader>
                    <CardTitle>About This Course</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ShowMoreContent content={course.post_content} />

                    {/* What You'll Learn — omitted entirely when the field is
                        blank, rather than printing an empty heading. */}
                    {toLines(course.course_benefits).length > 0 && (
                      <div className="mt-8">
                        <h3 className="text-lg font-semibold mb-4">
                          What you'll learn
                        </h3>
                        <div className="grid md:grid-cols-2 gap-3">
                          {toLines(course.course_benefits).map(
                            (benefit, index) => (
                              <div
                                key={index}
                                className="flex items-start gap-2"
                              >
                                <CheckCircle className="w-5 h-5 text-success-600 mt-0.5 flex-shrink-0" />
                                <span className="text-sm">{benefit}</span>
                              </div>
                            ),
                          )}
                        </div>
                      </div>
                    )}

                    {/* Requirements */}
                    {toLines(course.course_requirements).length > 0 && (
                      <div className="mt-8">
                        <h3 className="text-lg font-semibold mb-4">
                          Requirements
                        </h3>
                        <ul className="space-y-2">
                          {toLines(course.course_requirements).map(
                            (requirement, index) => (
                              <li
                                key={index}
                                className="flex items-start gap-2"
                              >
                                <div className="w-1.5 h-1.5 bg-neutral-400 rounded-full mt-2 flex-shrink-0" />
                                <span className="text-sm">{requirement}</span>
                              </li>
                            ),
                          )}
                        </ul>
                      </div>
                    )}

                    {/* Target Audience */}
                    {toLines(course.course_target_audience).length > 0 && (
                      <div className="mt-8">
                        <h3 className="text-lg font-semibold mb-4">
                          Who this course is for
                        </h3>
                        <ul className="space-y-2">
                          {toLines(course.course_target_audience).map(
                            (audience, index) => (
                              <li
                                key={index}
                                className="flex items-start gap-2"
                              >
                                <div className="w-1.5 h-1.5 bg-neutral-400 rounded-full mt-2 flex-shrink-0" />
                                <span className="text-sm">{audience}</span>
                              </li>
                            ),
                          )}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </Tabs.Content>

              {/* Curriculum Tab */}
              <Tabs.Content value="curriculum" className="mt-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Course Curriculum</CardTitle>
                    <p className="text-neutral-600">
                      {course.stats?.lessons ??
                        course.lesson_count ??
                        course.lessons?.length ??
                        0}{" "}
                      lessons
                    </p>
                  </CardHeader>
                  <CardContent>
                    {!course.lessons || course.lessons.length === 0 ? (
                      <div className="text-center py-8 text-neutral-600">
                        <BookOpen className="w-12 h-12 mx-auto mb-3 text-neutral-400" />
                        <p>No lessons available yet.</p>
                        <p className="text-sm">
                          The instructor is still building this course.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {course.lessons.map((lesson: any, index: number) => (
                          <div
                            key={lesson.id || index}
                            className={`flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 p-3 sm:p-4 rounded-xl transition ${lesson.is_preview && !isEnrolled ? "glass-panel border-orange-200" : "border border-neutral-200 bg-white/60 hover:bg-white"}`}
                            data-testid="curriculum-row"
                            data-glass="content"
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <div
                                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${lesson.is_preview && !isEnrolled ? "si-gradient text-white" : "bg-neutral-100 text-neutral-600"}`}
                              >
                                {lesson.is_locked ? (
                                  <Lock className="w-3.5 h-3.5" />
                                ) : (
                                  <PlayCircle className="w-4 h-4" />
                                )}
                              </div>
                              <span className="font-medium break-words min-w-0">
                                {lesson.lesson_title ||
                                  lesson.title ||
                                  `Lesson ${index + 1}`}
                              </span>
                            </div>
                            <div className="flex items-center gap-3 flex-shrink-0 pl-11 sm:pl-0">
                              {(lesson.duration || lesson.lesson_duration) && (
                                <span className="text-sm text-neutral-600">
                                  {lesson.duration || lesson.lesson_duration}{" "}
                                  minute
                                  {(lesson.duration ||
                                    lesson.lesson_duration) !== 1
                                    ? "s"
                                    : ""}
                                </span>
                              )}
                              {lesson.is_preview &&
                              !isEnrolled &&
                              !isAdminPreview ? (
                                <button
                                  type="button"
                                  className="si-btn-primary !py-1.5 !px-3 !text-xs"
                                  data-testid="preview-chip"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setPreviewLesson({
                                      id: lesson.id,
                                      title:
                                        lesson.lesson_title || lesson.title,
                                    });
                                  }}
                                >
                                  <PlayCircle className="w-3.5 h-3.5" /> Free
                                  preview
                                </button>
                              ) : !isEnrolled && !isAdminPreview ? (
                                <span
                                  className="glass-chip text-neutral-500"
                                  title="Enrol to unlock this lesson"
                                  data-testid="locked-chip"
                                >
                                  <Lock className="w-3.5 h-3.5" /> Locked
                                </span>
                              ) : null}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </Tabs.Content>

              {/* Instructor Tab */}
              <Tabs.Content value="instructor" className="mt-6">
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-start gap-6">
                      <Avatar size="xl">
                        <AvatarImage
                          src={
                            getMediaUrl(
                              course.instructor?.avatar ||
                                course.instructor?.profile?.profile_photo,
                            ) ||
                            `https://ui-avatars.com/api/?name=${encodeURIComponent(course.instructor?.display_name || course.instructor?.display_name || "Instructor")}`
                          }
                        />
                        <AvatarFallback>
                          {(
                            course.instructor?.display_name ||
                            course.instructor?.display_name ||
                            "IN"
                          )
                            .substring(0, 2)
                            .toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <h3 className="text-xl font-semibold mb-2">
                          {course.instructor?.display_name ||
                            course.instructor?.display_name ||
                            "Unknown Instructor"}
                        </h3>
                        <p className="text-neutral-600 mb-4">
                          Course Instructor
                        </p>

                        <div className="py-4">
                          <p className="text-neutral-700 leading-relaxed">
                            Instructor profile information will be available
                            soon.
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Tabs.Content>

              {/* Reviews Tab */}
              <Tabs.Content value="reviews" className="mt-6">
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>Student Reviews</CardTitle>
                      <div className="flex items-center gap-2">
                        <StarRating
                          rating={
                            reviewsSummary.average_rating ||
                            course.average_rating
                          }
                        />
                        <span className="font-semibold">
                          {reviewsSummary.average_rating ||
                            course.average_rating}
                        </span>
                        <span className="text-neutral-600">
                          ({reviewsSummary.total_reviews} reviews)
                        </span>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {isEnrolled && isAuthenticated && (
                      <div className="mb-6 p-4 border border-gray-200 rounded-lg">
                        <h4 className="font-semibold mb-2">Write a review</h4>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm text-gray-600">Rating:</span>
                          {[1, 2, 3, 4, 5].map((n) => (
                            <button
                              key={n}
                              type="button"
                              className={`w-7 h-7 rounded-full flex items-center justify-center ${reviewForm.rating >= n ? "text-yellow-500" : "text-gray-300"}`}
                              onClick={() =>
                                setReviewForm((f) => ({ ...f, rating: n }))
                              }
                              aria-label={`Rate ${n} stars`}
                            >
                              <Star className="w-5 h-5 fill-current" />
                            </button>
                          ))}
                        </div>
                        <input
                          type="text"
                          className="w-full border border-gray-300 rounded-md px-3 py-2 mb-2 text-sm"
                          placeholder="Title (optional)"
                          value={reviewForm.review_title}
                          onChange={(e) =>
                            setReviewForm((f) => ({
                              ...f,
                              review_title: e.target.value,
                            }))
                          }
                          maxLength={255}
                        />
                        <textarea
                          className="w-full border border-gray-300 rounded-md px-3 py-2 mb-2 text-sm"
                          rows={3}
                          placeholder="Share your experience… (required)"
                          value={reviewForm.review_content}
                          onChange={(e) =>
                            setReviewForm((f) => ({
                              ...f,
                              review_content: e.target.value,
                            }))
                          }
                          required
                        />
                        <Button
                          onClick={submitReview}
                          disabled={submittingReview}
                          size="sm"
                        >
                          {submittingReview ? "Submitting…" : "Submit review"}
                        </Button>
                      </div>
                    )}
                    {reviews.length === 0 ? (
                      <div className="text-center py-8 text-neutral-600">
                        <MessageSquare className="w-12 h-12 mx-auto mb-3 text-neutral-400" />
                        <p>No reviews yet.</p>
                        <p className="text-sm">
                          Be the first to review this course!
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {reviews.map((rv) => (
                          <div
                            key={rv.id}
                            className="p-4 border border-gray-100 rounded-lg"
                          >
                            <div className="flex items-center gap-3 mb-2">
                              <Avatar>
                                <AvatarImage
                                  src={
                                    getMediaUrl(rv.user?.avatar) ||
                                    `https://ui-avatars.com/api/?name=${encodeURIComponent(rv.user?.name || "User")}`
                                  }
                                />
                                <AvatarFallback>
                                  {(rv.user?.name || "U")
                                    .substring(0, 2)
                                    .toUpperCase()}
                                </AvatarFallback>
                              </Avatar>
                              <div className="flex-1">
                                <div className="font-semibold text-sm">
                                  {rv.user?.name}
                                </div>
                                <StarRating rating={rv.rating} size="sm" />
                              </div>
                            </div>
                            {rv.review_title && (
                              <div className="font-medium text-sm mb-1">
                                {rv.review_title}
                              </div>
                            )}
                            <p className="text-sm text-gray-700 whitespace-pre-wrap">
                              {rv.review_content}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </Tabs.Content>
            </Tabs.Root>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1">
            {/* Course Stats */}
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>Course Stats</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between">
                  <span>Skill Level</span>
                  <Badge variant="secondary">{course.course_level}</Badge>
                </div>
                <div className="flex justify-between">
                  <span>Students</span>
                  <span>{course.total_enrollments.toLocaleString()}</span>
                </div>
                {((course.num_offline_workshops ?? 0) > 0 ||
                  (course.num_hours ?? 0) > 0) && (
                  <>
                    {(course.num_offline_workshops ?? 0) > 0 && (
                      <div className="flex justify-between">
                        <span>Offline Workshops</span>
                        <span className="font-medium text-orange-600">
                          {course.num_offline_workshops}
                        </span>
                      </div>
                    )}
                    {(course.num_hours ?? 0) > 0 && (
                      <div className="flex justify-between">
                        <span>No. of Offline Hours</span>
                        <span className="font-medium text-orange-600">
                          {course.num_hours}
                        </span>
                      </div>
                    )}
                  </>
                )}
                <div className="flex justify-between">
                  <span>Languages</span>
                  <span>English</span>
                </div>
                <div className="flex justify-between">
                  <span>Captions</span>
                  <span>Yes</span>
                </div>
              </CardContent>
            </Card>

            {/* Related Courses */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg font-bold text-[#082A5E]">
                  More Courses by {course.instructor?.display_name}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {relatedCourses.length > 0 ? (
                    relatedCourses.map((rc) => (
                      <Link
                        key={rc.id}
                        to={`/courses/${rc.slug || rc.id}`}
                        className="flex gap-3 group hover:bg-orange-50 rounded-lg p-2 transition-all duration-200"
                      >
                        <img
                          src={
                            rc.featured_image ||
                            rc.course_thumbnail ||
                            "/placeholder-course.svg"
                          }
                          alt={rc.title || rc.post_title}
                          width={80}
                          height={56}
                          loading="lazy"
                          decoding="async"
                          className="w-20 h-14 object-cover rounded-lg flex-shrink-0 group-hover:opacity-90 transition-opacity"
                          onError={(e) => {
                            (e.currentTarget as HTMLImageElement).src =
                              "/placeholder-course.svg";
                          }}
                        />
                        <div className="flex-1 min-w-0">
                          <h4 className="font-semibold text-sm text-[#082A5E] mb-1 line-clamp-2 group-hover:text-[#f4911a] transition-colors">
                            {rc.title || rc.post_title}
                          </h4>
                          <div className="flex items-center gap-1 mb-1">
                            <StarRating
                              rating={rc.average_rating || 0}
                              size="sm"
                            />
                            <span className="text-xs text-gray-500">
                              ({rc.total_reviews || 0})
                            </span>
                          </div>
                          <p className="text-sm font-bold text-[#f4911a]">
                            {rc.price === 0
                              ? "Free"
                              : `₹${rc.sale_price || rc.price || 0}`}
                          </p>
                        </div>
                      </Link>
                    ))
                  ) : (
                    <p className="text-sm text-gray-500 text-center py-4">
                      No other courses available
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      <LessonPreviewModal
        courseId={course.id}
        lessonId={previewLesson?.id ?? null}
        lessonTitle={previewLesson?.title}
        open={!!previewLesson}
        onClose={() => setPreviewLesson(null)}
        isEnrolled={isEnrolled || isAdminPreview}
        enrolHref={`/checkout/${course.id}`}
      />

      {/* Video Modal */}
      {isVideoModalOpen && previewVideoUrl && (
        <div
          className="fixed inset-0 z-modal flex items-center justify-center bg-black/90 p-4"
          onClick={() => {
            setIsVideoModalOpen(false);
            setPreviewVideoUrl("");
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setIsVideoModalOpen(false);
              setPreviewVideoUrl("");
            }
          }}
        >
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-4 right-4 text-white hover:bg-white/20 z-50 rounded-full bg-black/50"
            onClick={(e) => {
              e.stopPropagation();
              setIsVideoModalOpen(false);
              setPreviewVideoUrl("");
            }}
            aria-label="Close preview"
          >
            <X className="w-6 h-6" />
          </Button>
          {/* max-h keeps the 16:9 box inside the viewport on short screens —
              a phone in landscape (e.g. 800x360) would otherwise size this to
              ~432px tall from the width alone and push the video off-screen
              under the close button. */}
          <div
            className="w-full max-w-4xl aspect-video max-h-[80vh] bg-black rounded-xl overflow-hidden shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            <VideoPlayer
              src={previewVideoUrl}
              title={previewVideoTitle}
              onEnded={() => {}}
            />
          </div>
        </div>
      )}
    </div>
  );
};
