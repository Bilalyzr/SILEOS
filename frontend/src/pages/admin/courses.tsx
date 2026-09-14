import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useState, useEffect } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import { Link } from "react-router-dom";
import {
  Search,
  Trash2,
  Eye,
  Users,
  Star,
  CheckCircle,
  Clock,
  XCircle,
  Archive,
  Activity,
} from "lucide-react";
import { getAuthToken } from "@/utils/auth-helper";
import { api } from "@/api/axios";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";
import { CoursesProgressChart } from "@/components/admin/CoursesProgressChart";

interface Course {
  total_enrollments?: number;
  id: number;
  title: string;
  instructor_name: string;
  status: string;
  price: number;
  enrolled_students: number;
  rating: number;
  video_view_count?: number;
  banner_url?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Course banner thumbnail for the management table. Falls back to the brand
 * gradient when a course has no banner set, or when the image 404s.
 */
const CourseBanner: React.FC<{ src?: string; title: string }> = ({
  src,
  title,
}) => {
  const [failed, setFailed] = useState(false);

  // A refetch can hand us a different (or newly working) image — clear the
  // failure so we don't keep showing the gradient for a valid banner.
  useEffect(() => {
    setFailed(false);
  }, [src]);

  if (!src || failed) {
    return (
      <div className="w-20 h-12 bg-gradient-to-br from-orange-500 to-blue-600 rounded-lg flex-shrink-0" />
    );
  }

  return (
    <img
      src={src}
      alt={`${title} banner`}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
      className="w-20 h-12 object-cover rounded-lg flex-shrink-0 border border-gray-200 bg-gray-100"
    />
  );
};

export const AdminCourses: React.FC = () => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [selectedCourses, setSelectedCourses] = useState<number[]>([]);

  useEffect(() => {
    fetchCourses();
  }, []);

  const fetchCourses = async () => {
    try {
      setLoadError(null);
      const token = getAuthToken();
      if (!token) {
        console.error("No auth token found");
        setLoadError("You are not signed in. Please log in again.");
        setLoading(false);
        return;
      }

      const response = await api.get("/admin/courses");

      const data = response.data;
      // Admin endpoint returns array directly, not wrapped in {courses: [...]}
      setCourses(Array.isArray(data) ? data : []);
    } catch (error: any) {
      console.error("Error fetching courses:", error);
      // Surface the real error instead of silently showing an empty table.
      const status = error?.response?.status;
      const detail = error?.response?.data?.detail;
      setLoadError(
        status
          ? `Failed to load courses (HTTP ${status})${detail ? `: ${detail}` : ""}`
          : error?.message || "Failed to load courses. Please try again.",
      );
      setCourses([]);
    } finally {
      setLoading(false);
    }
  };

  const handlePublishCourse = async (courseId: number, courseTitle: string) => {
    try {
      const token = getAuthToken();
      const r = await fetch(`/api/v1/admin/courses/${courseId}/force-publish`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) {
        setCourses((prev) =>
          prev.map((c) =>
            c.id === courseId ? { ...c, status: "publish" } : c,
          ),
        );
        alert(`Course "${courseTitle}" published successfully!`);
      } else {
        alert("Failed to publish course");
      }
    } catch {
      alert("Failed to publish course");
    }
  };

  const handleDeleteCourse = async (
    courseId: number,
    courseTitle: string,
    hasEnrollments: boolean = false,
  ) => {
    // Admin force delete - show warning if course has enrollments
    let confirmMessage = `Are you sure you want to delete "${courseTitle}"?`;

    if (hasEnrollments) {
      confirmMessage =
        `⚠️ ADMIN FORCE DELETE\n\n` +
        `"${courseTitle}" has active enrollments.\n\n` +
        `If you proceed:\n` +
        `• All enrolled students will be unenrolled\n` +
        `• Students will receive email notifications\n` +
        `• All course content will be permanently deleted\n\n` +
        `Do you want to FORCE DELETE this course?`;
    }

    if (!(await confirmDialog(confirmMessage))) {
      return;
    }

    try {
      // Add ?force=true for courses with enrollments
      const url = hasEnrollments
        ? `/courses/${courseId}?force=true`
        : `/courses/${courseId}`;

      const response = await api.delete(url);

      // Remove from local state
      setCourses((prev) => prev.filter((course) => course.id !== courseId));

      if (response.data.force_deleted) {
        alert(
          `Course deleted successfully!\n\n` +
            `${response.data.enrollments_removed} enrollment(s) removed\n` +
            `${response.data.students_notified} student(s) notified via email`,
        );
      } else {
        alert(`Course "${courseTitle}" deleted successfully`);
      }
    } catch (error: any) {
      console.error("Error deleting course:", error);
      alert(error.message || "Failed to delete course");
    }
  };

  const handleArchiveCourse = async (courseId: number, courseTitle: string) => {
    const confirmMessage = `Are you sure you want to archive "${courseTitle}"?\n\nArchived courses:\n• Will be hidden from students\n• Can be unarchived later\n• Retain all content and enrollments`;

    if (!(await confirmDialog(confirmMessage))) {
      return;
    }

    try {
      const response = await api.put(
        `/admin/courses/${courseId}/status?course_status=archive`,
      );

      if (response.status !== 200) {
        throw new Error(response.data?.detail || "Failed to archive course");
      }

      // Update local state to mark course as archived
      setCourses((prev) =>
        prev.map((course) =>
          course.id === courseId ? { ...course, status: "archive" } : course,
        ),
      );

      alert(`Course "${courseTitle}" has been archived successfully`);
    } catch (error: any) {
      console.error("Error archiving course:", error);
      alert(error.message || "Failed to archive course");
    }
  };

  const handleApproveCourse = async (courseId: number, courseTitle: string) => {
    try {
      const response = await api.put(
        `/admin/courses/${courseId}/status?course_status=publish`,
      );

      if (response.status !== 200) {
        throw new Error(response.data?.detail || "Failed to approve course");
      }

      // Update local state
      setCourses((prev) =>
        prev.map((course) =>
          course.id === courseId ? { ...course, status: "published" } : course,
        ),
      );
      alert(`Course "${courseTitle}" has been approved and published`);
    } catch (error) {
      console.error("Error approving course:", error);
      alert("Failed to approve course");
    }
  };

  const handleDenyCourse = async (courseId: number, courseTitle: string) => {
    if (
      !(await confirmDialog(
        `Are you sure you want to deny "${courseTitle}"? The course will be set to draft.`,
      ))
    ) {
      return;
    }

    try {
      const response = await api.put(
        `/admin/courses/${courseId}/status?course_status=draft`,
      );

      if (response.status !== 200) {
        throw new Error(response.data?.detail || "Failed to deny course");
      }

      // Update local state
      setCourses((prev) =>
        prev.map((course) =>
          course.id === courseId ? { ...course, status: "draft" } : course,
        ),
      );
      alert(`Course "${courseTitle}" has been denied and set to draft`);
    } catch (error) {
      console.error("Error denying course:", error);
      alert("Failed to deny course");
    }
  };

  const handleBulkPublish = async () => {
    if (selectedCourses.length === 0) return;

    const unpublishedCourses = selectedCourses.filter((id) => {
      const course = courses.find((c) => c.id === id);
      return (
        course && course.status !== "publish" && course.status !== "published"
      );
    });

    if (unpublishedCourses.length === 0) {
      alert("All selected courses are already published");
      return;
    }

    if (
      !(await confirmDialog(`Publish ${unpublishedCourses.length} course(s)?`))
    ) {
      return;
    }

    try {
      const promises = unpublishedCourses.map((courseId) =>
        api.put(`/admin/courses/${courseId}/status?course_status=publish`),
      );
      await Promise.all(promises);

      // Update local state
      setCourses((prev) =>
        prev.map((course) =>
          unpublishedCourses.includes(course.id)
            ? { ...course, status: "publish" }
            : course,
        ),
      );

      alert(`${unpublishedCourses.length} course(s) published successfully`);
      setSelectedCourses([]);
    } catch (error) {
      console.error("Error bulk publishing courses:", error);
      alert("Failed to publish some courses");
    }
  };

  const handleBulkDraft = async () => {
    if (selectedCourses.length === 0) return;

    const publishedCourses = selectedCourses.filter((id) => {
      const course = courses.find((c) => c.id === id);
      return (
        course && (course.status === "publish" || course.status === "published")
      );
    });

    if (publishedCourses.length === 0) {
      alert("All selected courses are already drafts");
      return;
    }

    if (
      !(await confirmDialog(
        `Set ${publishedCourses.length} course(s) to draft?`,
      ))
    ) {
      return;
    }

    try {
      const promises = publishedCourses.map((courseId) =>
        api.put(`/admin/courses/${courseId}/status?course_status=draft`),
      );
      await Promise.all(promises);

      // Update local state
      setCourses((prev) =>
        prev.map((course) =>
          publishedCourses.includes(course.id)
            ? { ...course, status: "draft" }
            : course,
        ),
      );

      alert(`${publishedCourses.length} course(s) set to draft successfully`);
      setSelectedCourses([]);
    } catch (error) {
      console.error("Error bulk drafting courses:", error);
      alert("Failed to update some courses");
    }
  };

  const handleBulkDelete = async () => {
    if (selectedCourses.length === 0) return;

    const hasEnrollments = selectedCourses.some((id) => {
      const course = courses.find((c) => c.id === id);
      return course && (course.enrolled_students || 0) > 0;
    });

    const confirmMessage = hasEnrollments
      ? `⚠️ WARNING: Some selected courses have enrollments!\n\n` +
        `Deleting will:\n` +
        `• Unenroll all students\n` +
        `• Send email notifications\n` +
        `• Permanently delete course content\n\n` +
        `Delete ${selectedCourses.length} course(s)?`
      : `Delete ${selectedCourses.length} course(s)?`;

    if (!(await confirmDialog(confirmMessage))) {
      return;
    }

    try {
      const promises = selectedCourses.map((courseId) => {
        const course = courses.find((c) => c.id === courseId);
        const hasForceFlag = (course?.enrolled_students || 0) > 0;
        return api.delete(
          `/courses/${courseId}${hasForceFlag ? "?force=true" : ""}`,
        );
      });

      await Promise.all(promises);

      // Remove from local state
      setCourses((prev) =>
        prev.filter((course) => !selectedCourses.includes(course.id)),
      );

      alert(`${selectedCourses.length} course(s) deleted successfully`);
      setSelectedCourses([]);
    } catch (error) {
      console.error("Error bulk deleting courses:", error);
      alert("Failed to delete some courses");
    }
  };

  const getStatusBadge = (status: string) => {
    const badges = {
      publish: { color: "green", icon: CheckCircle, text: "Published" },
      draft: { color: "gray", icon: Clock, text: "Draft" },
      pending: { color: "yellow", icon: Clock, text: "Pending" },
      private: { color: "red", icon: XCircle, text: "Private" },
    };
    const badge = badges[status as keyof typeof badges] || badges.draft;
    const Icon = badge.icon;
    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-${badge.color}-100 text-${badge.color}-800`}
      >
        <Icon className="w-3 h-3 mr-1" />
        {badge.text}
      </span>
    );
  };

  const filteredCourses = courses.filter((course) => {
    const matchesSearch = course.title
      .toLowerCase()
      .includes(searchTerm.toLowerCase());
    const matchesFilter =
      filterStatus === "all" || course.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  const toggleSelectCourse = (courseId: number) => {
    setSelectedCourses((prev) =>
      prev.includes(courseId)
        ? prev.filter((id) => id !== courseId)
        : [...prev, courseId],
    );
  };

  const toggleSelectAll = () => {
    if (selectedCourses.length === filteredCourses.length) {
      setSelectedCourses([]);
    } else {
      setSelectedCourses(filteredCourses.map((c) => c.id));
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Courses</h1>
            <p className="text-gray-600 mt-1">
              Review and manage courses submitted by instructors
            </p>
          </div>
          <ExportImportPanel
            section="courses"
            onImportComplete={fetchCourses}
          />
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-courses"
    >
      <CoursesProgressChart />
      <div
        className="bg-white rounded-lg border border-gray-200 p-4"
        data-glass="work"
      >
        <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
          <div className="flex-1 max-w-md">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search courses..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Status</option>
              <option value="publish">Published</option>
              <option value="draft">Draft</option>
              <option value="pending">Pending</option>
              <option value="private">Private</option>
            </select>
          </div>
        </div>
      </div>
      <div
        className="bg-white rounded-lg border border-gray-200 overflow-hidden"
        data-glass="work"
      >
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={
                      selectedCourses.length === filteredCourses.length &&
                      filteredCourses.length > 0
                    }
                    onChange={toggleSelectAll}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Course
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Instructor
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Students
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Video Views
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Price
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Rating
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td
                    colSpan={10}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    Loading courses...
                  </td>
                </tr>
              ) : loadError ? (
                <tr>
                  <td colSpan={10} className="px-6 py-12 text-center">
                    <p className="text-red-600 font-medium">{loadError}</p>
                    <button
                      onClick={fetchCourses}
                      className="mt-3 px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                    >
                      Retry
                    </button>
                  </td>
                </tr>
              ) : filteredCourses.length === 0 ? (
                <tr>
                  <td
                    colSpan={10}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    No courses found
                  </td>
                </tr>
              ) : (
                filteredCourses.map((course) => (
                  <tr key={course.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <input
                        type="checkbox"
                        checked={selectedCourses.includes(course.id)}
                        onChange={() => toggleSelectCourse(course.id)}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-start space-x-3">
                        <CourseBanner
                          src={course.banner_url}
                          title={course.title}
                        />
                        <div className="flex-1 min-w-0">
                          <Link
                            to={`/admin/courses/${course.id}/edit`}
                            className="text-sm font-medium text-gray-900 hover:text-blue-600 line-clamp-2"
                          >
                            {course.title}
                          </Link>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {course.instructor_name}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900">
                        <Users className="w-4 h-4 mr-1 text-gray-400" />
                        {(course.enrolled_students || 0).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900">
                        <Eye className="w-4 h-4 mr-1 text-gray-400" />
                        {(course.video_view_count || 0).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm">
                        <div className="text-gray-900 font-medium">
                          ₹{course.price || 0}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900">
                        <Star className="w-4 h-4 mr-1 text-yellow-400 fill-yellow-400" />
                        {course.rating || 0}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(course.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center space-x-2">
                        {course.status === "pending" ? (
                          <>
                            <Link
                              to={`/courses/${course.id}`}
                              className="px-3 py-1 bg-blue-100 text-blue-800 rounded hover:bg-blue-200 text-xs font-medium inline-flex items-center gap-1"
                              title="Preview Course (Admin Only)"
                            >
                              <Eye className="w-3 h-3" />
                              Preview
                            </Link>
                            <button
                              onClick={() =>
                                handleApproveCourse(course.id, course.title)
                              }
                              className="px-3 py-1 bg-green-100 text-green-800 rounded hover:bg-green-200 text-xs font-medium"
                              title="Approve and Publish"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() =>
                                handleDenyCourse(course.id, course.title)
                              }
                              className="px-3 py-1 bg-red-100 text-red-800 rounded hover:bg-red-200 text-xs font-medium"
                              title="Deny and set to Draft"
                            >
                              Deny
                            </button>
                          </>
                        ) : (
                          <>
                            <Link
                              to={`/courses/${course.id}`}
                              className="text-gray-400 hover:text-blue-600"
                              title="Preview Course"
                            >
                              <Eye className="w-4 h-4" />
                            </Link>
                            <Link
                              to={`/admin/courses/${course.id}/activity`}
                              className="text-gray-400 hover:text-indigo-600"
                              title="Student Activity"
                            >
                              <Activity className="w-4 h-4" />
                            </Link>
                            <button
                              onClick={() =>
                                handleArchiveCourse(course.id, course.title)
                              }
                              className="text-gray-400 hover:text-yellow-600"
                              title="Archive course"
                            >
                              <Archive className="w-4 h-4" />
                            </button>
                            {course.status !== "publish" &&
                              course.status !== "published" && (
                                <button
                                  onClick={() =>
                                    handlePublishCourse(course.id, course.title)
                                  }
                                  title="Publish Course"
                                  className="p-1.5 text-green-600 hover:text-green-800 hover:bg-green-50 rounded transition-colors"
                                >
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    className="w-4 h-4"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                  >
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M5 13l4 4L19 7"
                                    />
                                  </svg>
                                </button>
                              )}
                            <button
                              onClick={() =>
                                handleDeleteCourse(
                                  course.id,
                                  course.title,
                                  (course.total_enrollments || 0) > 0,
                                )
                              }
                              className={
                                (course.total_enrollments || 0) > 0
                                  ? "text-orange-400 hover:text-orange-600"
                                  : "text-gray-400 hover:text-red-600"
                              }
                              title={
                                (course.total_enrollments || 0) > 0
                                  ? "Force Delete (has enrollments)"
                                  : "Delete"
                              }
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {filteredCourses.length > 0 && (
          <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Showing{" "}
                <span className="font-medium">{filteredCourses.length}</span>{" "}
                course{filteredCourses.length === 1 ? "" : "s"}
              </div>
            </div>
          </div>
        )}
      </div>
      {selectedCourses.length > 0 &&
        (() => {
          // Calculate which actions are relevant based on selected courses
          const hasUnpublished = selectedCourses.some((id) => {
            const course = courses.find((c) => c.id === id);
            return (
              course &&
              course.status !== "publish" &&
              course.status !== "published"
            );
          });
          const hasPublished = selectedCourses.some((id) => {
            const course = courses.find((c) => c.id === id);
            return (
              course &&
              (course.status === "publish" || course.status === "published")
            );
          });

          return (
            <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white px-6 py-4 rounded-lg shadow-xl flex items-center space-x-4">
              <span className="text-sm font-medium">
                {selectedCourses.length} course(s) selected
              </span>
              <div className="flex space-x-2">
                {hasUnpublished && (
                  <button
                    onClick={handleBulkPublish}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm transition-colors"
                  >
                    Publish
                  </button>
                )}
                {hasPublished && (
                  <button
                    onClick={handleBulkDraft}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors"
                  >
                    Draft
                  </button>
                )}
                <button
                  onClick={handleBulkDelete}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm transition-colors"
                >
                  Delete
                </button>
                <button
                  onClick={() => setSelectedCourses([])}
                  className="px-4 py-2 bg-transparent border border-gray-600 hover:border-gray-400 rounded text-sm transition-colors"
                >
                  Clear
                </button>
              </div>
            </div>
          );
        })()}
    </PageLayout>
  );
};
