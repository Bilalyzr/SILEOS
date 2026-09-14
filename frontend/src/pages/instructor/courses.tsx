import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback } from "react";
import { useState, useEffect } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import { COURSE_TYPES, courseTypeOption } from "@/config/courseTypes";
import { Link } from "react-router-dom";
import {
  BookOpen,
  Users,
  Star,
  IndianRupee,
  Eye,
  Edit,
  Trash2,
  Plus,
  Search,
  ClipboardList,
  Inbox,
  EyeOff,
  Copy,
} from "lucide-react";
import { courseOpsAPI } from "@/api/courseOps";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Pagination } from "@/components/ui/pagination";
import { api } from "@/api/axios";
import { toast } from "react-hot-toast";
import { useAuthStore } from "@/store/auth";

interface Course {
  id: number;
  title: string;
  post_title?: string;
  description: string;
  post_excerpt?: string;
  thumbnail: string;
  course_thumbnail?: string;
  status: "published" | "draft" | "pending";
  post_status?: string;
  students: number;
  total_enrollments?: number;
  rating: number;
  average_rating?: number;
  reviews: number;
  price: number;
  course_price?: number;
  salePrice?: number | null;
  course_sale_price?: number;
  createdAt: string;
  created_at?: string;
  lastUpdated: string;
  updated_at?: string;
  category: string;
  course_category?: string;
  courseType?: string;
  duration: string;
  course_duration?: string;
  instructor?: {
    id: number;
    name: string;
    avatar?: string;
  };
}

export function InstructorCourses() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("newest");
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const pageSize = 12;

  const fetchCourses = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get("/courses/my-courses", {
        params: {
          page: currentPage,
          page_size: pageSize,
        },
      });

      // Set pagination data
      setTotalPages(response.data.total_pages || 1);
      setTotalItems(response.data.total || 0);

      // Transform backend data to match frontend interface
      const transformedCourses = (response.data.courses || []).map(
        (course: any) => ({
          id: course.id,
          title: course.post_title || course.title,
          description: course.post_excerpt || course.description || "",
          thumbnail:
            course.course_thumbnail ||
            course.thumbnail ||
            "/api/placeholder/300/200",
          status:
            course.post_status === "publish"
              ? "published"
              : course.post_status || "draft",
          students: course.total_enrollments || 0,
          rating: course.average_rating || 0,
          reviews: 0, // TODO: Add reviews count from backend
          price: parseFloat(course.course_price || course.price || 0),
          // Optional discounted/sale price shown alongside the regular price.
          salePrice: course.course_sale_price
            ? parseFloat(course.course_sale_price)
            : null,
          createdAt:
            course.created_at || course.createdAt || new Date().toISOString(),
          lastUpdated: course.updated_at || course.lastUpdated || "Recently",
          category:
            course.course_category || course.category || "Uncategorized",
          courseType: course.course_type || "",
          duration: course.course_duration || course.duration || "N/A",
          instructor: course.instructor || {
            id: 0,
            name: "Unknown",
            avatar: undefined,
          },
        }),
      );

      setCourses(transformedCourses);
    } catch (error: any) {
      console.error("Failed to fetch courses:", error);
      toast.error("Failed to load your courses");
      setCourses([]);
    } finally {
      setLoading(false);
    }
  }, [currentPage]);
  useEffect(() => {
    fetchCourses();
  }, [currentPage, fetchCourses]);

  const handleRequestApproval = async (
    courseId: number,
    courseTitle: string,
  ) => {
    try {
      const response = await api.patch(`/courses/${courseId}/publish`);

      if (response.status === 200) {
        toast.success(`"${courseTitle}" submitted for approval`);
        // Refresh courses to update the status
        fetchCourses();
      } else {
        throw new Error(
          response.data?.detail || "Failed to submit for approval",
        );
      }
    } catch (error: any) {
      console.error("Failed to submit for approval:", error);
      toast.error(error.message || "Failed to submit for approval");
    }
  };

  // I-H5: unpublish own course. The backend allows the owning instructor
  // (courses.py:936-937, not just admin) to flip a published course back to
  // draft — courseApi.unpublishCourse already wraps PATCH
  // /courses/{id}/unpublish, it just had zero UI callers until now.
  const handleUnpublishCourse = async (
    courseId: number,
    courseTitle: string,
  ) => {
    if (
      !(await confirmDialog(
        `Unpublish "${courseTitle}"? It will no longer be visible to students or listed in the catalog until you republish it.`,
      ))
    ) {
      return;
    }
    try {
      await api.patch(`/courses/${courseId}/unpublish`);
      toast.success(`"${courseTitle}" unpublished`);
      setCourses((prev) =>
        prev.map((c) =>
          c.id === courseId
            ? { ...c, status: "draft", post_status: "draft" }
            : c,
        ),
      );
    } catch (error: any) {
      console.error("Failed to unpublish course:", error);
      toast.error(error.response?.data?.detail || "Failed to unpublish course");
    }
  };

  const handleDeleteCourse = async (
    courseId: number,
    courseTitle: string,
    hasEnrollments: boolean = false,
  ) => {
    const user = useAuthStore.getState().user;

    // If course has enrollments and user is admin, offer force delete
    if (hasEnrollments && user?.role === "admin") {
      const forceDelete = await confirmDialog(
        `⚠️ ADMIN FORCE DELETE\n\n` +
          `"${courseTitle}" has active enrollments.\n\n` +
          `If you proceed:\n` +
          `• All enrolled students will be unenrolled\n` +
          `• Students will receive email notifications\n` +
          `• All course content will be permanently deleted\n\n` +
          `Do you want to FORCE DELETE this course?`,
      );

      if (!forceDelete) return;

      try {
        const response = await api.delete(`/courses/${courseId}?force=true`);

        // Remove from local state
        setCourses((prev) => prev.filter((course) => course.id !== courseId));

        const data = response.data;
        toast.success(
          `Course deleted successfully!\n` +
            `${data.enrollments_removed} enrollment(s) removed\n` +
            `${data.students_notified} student(s) notified`,
          { duration: 6000 },
        );
      } catch (error: any) {
        console.error("Failed to force delete course:", error);
        const errorMessage =
          error.response?.data?.detail || "Failed to delete course";
        toast.error(errorMessage, { duration: 5000 });
      }
      return;
    }

    // Regular deletion (no enrollments or non-admin)
    if (
      !(await confirmDialog(
        `Are you sure you want to delete "${courseTitle}"? This action cannot be undone and will delete all lessons, quizzes, and assignments.\n\nNote: Courses with active enrollments cannot be deleted.`,
      ))
    ) {
      return;
    }

    try {
      await api.delete(`/courses/${courseId}`);

      // Remove from local state
      setCourses((prev) => prev.filter((course) => course.id !== courseId));
      toast.success(`Course "${courseTitle}" deleted successfully`);
    } catch (error: any) {
      console.error("Failed to delete course:", error);
      const errorMessage =
        error.response?.data?.detail || "Failed to delete course";
      toast.error(errorMessage, {
        duration: 5000, // Show error longer so users can read the full message
      });
    }
  };

  const filteredCourses = courses.filter((course) => {
    const matchesSearch =
      course.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      course.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus =
      statusFilter === "all" || course.status === statusFilter;
    const matchesType =
      typeFilter === "all" || (course.courseType || "") === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  });

  const sortedCourses = [...filteredCourses].sort((a, b) => {
    switch (sortBy) {
      case "newest":
        return (
          new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
        );
      case "oldest":
        return (
          new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
        );
      case "students":
        return b.students - a.students;
      case "price":
        return b.price - a.price;
      case "rating":
        return b.rating - a.rating;
      default:
        return 0;
    }
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case "published":
        return "bg-green-600";
      case "draft":
        return "bg-gray-600";
      case "pending":
        return "bg-yellow-600";
      default:
        return "bg-gray-600";
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="dash-h1 mb-1">My Courses</h1>
            <p className="text-slate-600 text-sm">
              Manage and track your course performance
            </p>
          </div>
          <Link
            to="/instructor/course-packages"
            className="px-4 py-2 text-sm rounded-lg border border-orange-300 text-orange-700"
          >
            Upload / Restore course
          </Link>
          <Link to="/instructor/courses/create">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create New Course
            </Button>
          </Link>
          <Link to="/exam-papers">
            <Button variant="outline">Generate practice paper</Button>
          </Link>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-courses"
    >
      <Card className="rd-course-toolbar p-4">
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="flex flex-col md:flex-row gap-4 flex-1">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                type="text"
                placeholder="Search courses..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Status</option>
              <option value="published">Published</option>
              <option value="draft">Draft</option>
              <option value="pending">Pending</option>
            </select>

            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              title="Filter by course type"
            >
              <option value="all">All Types</option>
              {COURSE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.emoji} {t.label} — {t.tagline}
                </option>
              ))}
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="students">Most Students</option>
              <option value="price">Highest Price</option>
              <option value="rating">Highest Rated</option>
            </select>
          </div>

          <div className="text-sm text-gray-600">
            {sortedCourses.length} course{sortedCourses.length !== 1 ? "s" : ""}
          </div>
        </div>
      </Card>
      <div className="rd-course-rows">
        {sortedCourses.map((course) => (
          <Card key={course.id} className="rd-managed-course">
            <div className="rd-course-summary">
              <img
                src={course.thumbnail}
                alt=""
                onError={(e) => {
                  e.currentTarget.onerror = null;
                  e.currentTarget.src = "/design/course-placeholder.svg";
                }}
              />
              <div>
                <Link to={`/instructor/courses/${course.id}/edit`}>
                  <h3>{course.title}</h3>
                </Link>
                <small>
                  {courseTypeOption(course.courseType)?.label ||
                    course.category}
                </small>
              </div>
            </div>
            <div>
              <Badge className={getStatusColor(course.status)}>
                {course.status.charAt(0).toUpperCase() + course.status.slice(1)}
              </Badge>
            </div>
            <span className="rd-course-number">
              <Users size={14} />
              {course.students}
              <small>learners</small>
            </span>
            <span className="rd-course-number">
              <Star size={14} />
              {course.rating > 0 ? course.rating.toFixed(1) : "—"}
            </span>
            <span className="rd-course-number">
              <IndianRupee size={14} />
              {course.salePrice &&
              course.salePrice > 0 &&
              course.salePrice < course.price
                ? course.salePrice
                : course.price || "Free"}
            </span>
            <details className="rd-course-manage">
              <summary>Manage</summary>
              <div className="rd-course-manage-body">
                <p>
                  {course.description ||
                    "Add a description in the course editor."}
                </p>
                <div className="flex gap-2 mb-3">
                  <Link
                    to={`/instructor/courses/${course.id}/gradebook`}
                    className="flex-1"
                  >
                    <Button variant="outline" size="sm" className="w-full">
                      <ClipboardList className="h-4 w-4 mr-1" />
                      Gradebook
                    </Button>
                  </Link>
                  <Link
                    to={`/instructor/courses/${course.id}/grading-queue`}
                    className="flex-1"
                  >
                    <Button variant="outline" size="sm" className="w-full">
                      <Inbox className="h-4 w-4 mr-1" />
                      Grading queue
                    </Button>
                  </Link>
                </div>
                <div className="flex items-center justify-between pt-4 border-t">
                  <div className="flex space-x-2">
                    <Link to={`/courses/${course.id}`}>
                      <Button variant="outline" size="sm">
                        <Eye className="h-4 w-4 mr-1" />
                        View
                      </Button>
                    </Link>
                    {(() => {
                      const currentUser = useAuthStore.getState().user;
                      const isInstructorOwnCourse =
                        course.instructor?.id === currentUser?.id;
                      const isDraftStatus =
                        course.status === "draft" ||
                        course.post_status === "draft";

                      // If course is draft and instructor ID doesn't match current user, show Approve Now button
                      if (isDraftStatus && !isInstructorOwnCourse) {
                        return (
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-green-600 border-green-300 hover:text-green-700 hover:border-green-400"
                            onClick={() =>
                              handleRequestApproval(course.id, course.title)
                            }
                          >
                            <Edit className="h-4 w-4 mr-1" />
                            Approve Now
                          </Button>
                        );
                      }

                      // Otherwise show normal Edit button, plus a
                      // Publish/Unpublish toggle for the owner's own course.
                      // "Publish" on an owner's own draft re-submits for
                      // admin approval (courses.py:889-905 — instructors
                      // never self-publish directly, only admins do); the
                      // status chip above already reflects the result.
                      return (
                        <>
                          <Link to={`/instructor/courses/${course.id}/edit`}>
                            <Button variant="outline" size="sm">
                              <Edit className="h-4 w-4 mr-1" />
                              Edit
                            </Button>
                          </Link>
                          {isInstructorOwnCourse &&
                            course.status === "published" && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="text-amber-600 border-amber-300 hover:text-amber-700 hover:border-amber-400"
                                onClick={() =>
                                  handleUnpublishCourse(course.id, course.title)
                                }
                              >
                                <EyeOff className="h-4 w-4 mr-1" />
                                Unpublish
                              </Button>
                            )}
                          {isInstructorOwnCourse && isDraftStatus && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-green-600 border-green-300 hover:text-green-700 hover:border-green-400"
                              onClick={() =>
                                handleRequestApproval(course.id, course.title)
                              }
                            >
                              <Eye className="h-4 w-4 mr-1" />
                              Publish
                            </Button>
                          )}
                        </>
                      );
                    })()}
                  </div>
                  <div className="relative group">
                    {(() => {
                      const hasEnrollments =
                        course.students > 0 ||
                        (course.total_enrollments ?? 0) > 0;
                      const user = useAuthStore.getState().user;
                      const isAdmin = user?.role === "admin";

                      return (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            className={`${
                              hasEnrollments && !isAdmin
                                ? "text-gray-400 cursor-not-allowed opacity-50"
                                : hasEnrollments && isAdmin
                                  ? "text-orange-600 hover:text-orange-700 border-orange-300"
                                  : "text-red-600 hover:text-red-700"
                            }`}
                            onClick={() => {
                              handleDeleteCourse(
                                course.id,
                                course.title,
                                hasEnrollments,
                              );
                            }}
                            disabled={hasEnrollments && !isAdmin}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            title="Clone this course into a new draft"
                            data-testid="clone-course"
                            onClick={async () => {
                              try {
                                const c = await courseOpsAPI.clone(course.id);
                                toast.success(
                                  `Cloned — ${c.copied.lessons} lessons, ${c.copied.quizzes} quizzes copied`,
                                );
                                window.location.href = `/instructor/courses/${c.id}/edit`;
                              } catch (e: any) {
                                toast.error(
                                  e?.response?.data?.detail || "Clone failed",
                                );
                              }
                            }}
                          >
                            <Copy className="h-4 w-4" />
                          </Button>
                          {hasEnrollments && (
                            <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block w-64 p-3 bg-gray-900 text-white text-xs rounded shadow-lg z-10">
                              {isAdmin ? (
                                <>
                                  <div className="font-semibold text-orange-400 mb-1">
                                    <AstraSymbol value="⚠️" /> ADMIN FORCE
                                    DELETE
                                  </div>
                                  <div>
                                    Click to force delete course with{" "}
                                    {course.students ||
                                      course.total_enrollments}{" "}
                                    enrollment(s).
                                  </div>
                                  <div className="mt-1 text-gray-300">
                                    Students will be notified via email.
                                  </div>
                                </>
                              ) : (
                                <>
                                  Cannot delete course with{" "}
                                  {course.students || course.total_enrollments}{" "}
                                  active enrollment(s)
                                </>
                              )}
                            </div>
                          )}
                        </>
                      );
                    })()}
                  </div>
                </div>
              </div>
            </details>
          </Card>
        ))}
      </div>
      {loading && (
        <Card className="p-12 text-center">
          <div className="flex flex-col items-center space-y-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <p className="text-gray-600">Loading your courses...</p>
          </div>
        </Card>
      )}
      {!loading && sortedCourses.length === 0 && (
        <Card className="p-12 text-center">
          <BookOpen className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No courses found
          </h3>
          <p className="text-gray-600 mb-6">
            {searchTerm || statusFilter !== "all"
              ? "Try adjusting your search or filters"
              : "Create your first course to get started"}
          </p>
          <Link to="/instructor/courses/create">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create New Course
            </Button>
          </Link>
        </Card>
      )}
      {!loading && totalPages > 1 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={totalItems}
          pageSize={pageSize}
          onPageChange={(page) => setCurrentPage(page)}
          showPageInfo={true}
        />
      )}
    </PageLayout>
  );
}
