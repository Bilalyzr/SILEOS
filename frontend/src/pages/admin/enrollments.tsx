import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback } from "react";
import { getAuthToken } from "@/utils/auth-helper";
import { confirmDialog } from "@/components/ui/confirm";
import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  BookOpen,
  Users,
  CheckCircle,
  XCircle,
  TrendingUp,
  Calendar,
} from "lucide-react";
import toast from "react-hot-toast";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";

const API_BASE_URL = "/api/v1";

const BULK_STATUSES = [
  "enrolled",
  "completed",
  "cancelled",
  "suspended",
] as const;

interface Enrollment {
  id: number;
  student_name: string;
  student_email: string;
  course_title: string;
  course_id: number;
  enrollment_date: string;
  status: string;
  progress: number;
  completed_lessons: number;
  total_lessons: number;
  completion_date: string | null;
}

export const AdminEnrollments: React.FC = () => {
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  // M-2: multi-select + bulk status. PUT /admin/enrollments/bulk-update
  // (admin.py) existed with zero UI callers.
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkStatus, setBulkStatus] =
    useState<(typeof BULK_STATUSES)[number]>("enrolled");
  const [bulkBusy, setBulkBusy] = useState(false);

  const fetchEnrollments = useCallback(async () => {
    try {
      setLoading(true);
      const statusParam =
        filterStatus !== "all" ? `&status=${filterStatus}` : "";
      const response = await fetch(
        `${API_BASE_URL}/admin/enrollments?limit=100${statusParam}`,
        {
          headers: {
            Authorization: `Bearer ${getAuthToken()}`,
          },
        },
      );
      const data = await response.json();
      setEnrollments(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error fetching enrollments:", error);
      setEnrollments([]);
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);
  useEffect(() => {
    fetchEnrollments();
    setSelectedIds(new Set());
  }, [fetchEnrollments, filterStatus]);

  const updateEnrollmentStatus = async (
    enrollmentId: number,
    newStatus: string,
  ) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/admin/enrollments/${enrollmentId}/status?status=${newStatus}`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${getAuthToken()}`,
            "Content-Type": "application/json",
          },
        },
      );

      if (response.ok) {
        fetchEnrollments();
      }
    } catch (error) {
      console.error("Error updating enrollment status:", error);
    }
  };

  const toggleSelected = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAllVisible = (visibleIds: number[]) => {
    setSelectedIds((prev) => {
      const allSelected =
        visibleIds.length > 0 && visibleIds.every((id) => prev.has(id));
      if (allSelected) {
        const next = new Set(prev);
        visibleIds.forEach((id) => next.delete(id));
        return next;
      }
      return new Set([...prev, ...visibleIds]);
    });
  };

  const applyBulkStatus = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    if (
      !(await confirmDialog(
        `Set ${ids.length} enrollment(s) to "${bulkStatus}"?`,
      ))
    )
      return;
    setBulkBusy(true);
    try {
      // Body is the raw JSON array the route declares (`enrollment_ids:
      // List[int]`); the target status rides the query string.
      const response = await fetch(
        `${API_BASE_URL}/admin/enrollments/bulk-update?status=${encodeURIComponent(bulkStatus)}`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${getAuthToken()}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(ids),
        },
      );
      if (!response.ok) {
        let detail = "Bulk update failed";
        try {
          const err = await response.json();
          if (typeof err?.detail === "string") detail = err.detail;
        } catch {
          /* keep fallback */
        }
        toast.error(detail);
        return;
      }
      toast.success(`Updated ${ids.length} enrollment(s)`);
      setSelectedIds(new Set());
      fetchEnrollments();
    } catch (error) {
      console.error("Bulk update error:", error);
      toast.error("Bulk update failed");
    } finally {
      setBulkBusy(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const badges = {
      enrolled: { color: "blue", text: "Enrolled", icon: BookOpen },
      completed: { color: "green", text: "Completed", icon: CheckCircle },
      cancelled: { color: "red", text: "Cancelled", icon: XCircle },
    };
    const badge = badges[status as keyof typeof badges] || badges.enrolled;
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

  const filteredEnrollments = enrollments.filter(
    (enrollment) =>
      enrollment.student_name
        .toLowerCase()
        .includes(searchTerm.toLowerCase()) ||
      enrollment.course_title
        .toLowerCase()
        .includes(searchTerm.toLowerCase()) ||
      enrollment.student_email.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const stats = {
    total: enrollments.length,
    enrolled: enrollments.filter((e) => e.status === "enrolled").length,
    completed: enrollments.filter((e) => e.status === "completed").length,
    cancelled: enrollments.filter((e) => e.status === "cancelled").length,
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900">Enrollments</h1>
            <ExportImportPanel section="enrollments" />
          </div>
          <div className="flex items-center space-x-3">
            <div className="text-sm text-gray-600">
              <span className="font-semibold">
                {filteredEnrollments.length}
              </span>{" "}
              enrollments
            </div>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-enrollments"
    >
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Enrollments</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {stats.total}
              </p>
            </div>
            <Users className="w-8 h-8 text-blue-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Active</p>
              <p className="text-2xl font-bold text-blue-600 mt-1">
                {stats.enrolled}
              </p>
            </div>
            <BookOpen className="w-8 h-8 text-blue-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Completed</p>
              <p className="text-2xl font-bold text-green-600 mt-1">
                {stats.completed}
              </p>
            </div>
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Completion Rate</p>
              <p className="text-2xl font-bold text-purple-600 mt-1">
                {stats.total > 0
                  ? Math.round((stats.completed / stats.total) * 100)
                  : 0}
                %
              </p>
            </div>
            <TrendingUp className="w-8 h-8 text-purple-600" />
          </div>
        </div>
      </div>
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
                placeholder="Search enrollments..."
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
              <option value="enrolled">Enrolled</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>
      </div>
      {selectedIds.size > 0 && (
        <div
          className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex flex-wrap items-center gap-3"
          data-testid="bulk-action-bar"
        >
          <span className="text-sm font-medium text-blue-900">
            {selectedIds.size} selected
          </span>
          <select
            value={bulkStatus}
            onChange={(e) =>
              setBulkStatus(e.target.value as (typeof BULK_STATUSES)[number])
            }
            className="px-3 py-1.5 border border-blue-300 rounded text-sm bg-white"
            aria-label="Bulk status"
          >
            {BULK_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={applyBulkStatus}
            disabled={bulkBusy}
            className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {bulkBusy ? "Applying…" : "Apply to selected"}
          </button>
          <button
            type="button"
            onClick={() => setSelectedIds(new Set())}
            disabled={bulkBusy}
            className="text-sm text-blue-700 hover:underline disabled:opacity-50"
          >
            Clear selection
          </button>
        </div>
      )}
      <div
        className="bg-white rounded-lg border border-gray-200 overflow-hidden"
        data-glass="work"
      >
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3">
                  <input
                    type="checkbox"
                    aria-label="Select all visible enrollments"
                    checked={
                      filteredEnrollments.length > 0 &&
                      filteredEnrollments.every((e) => selectedIds.has(e.id))
                    }
                    onChange={() =>
                      toggleSelectAllVisible(
                        filteredEnrollments.map((e) => e.id),
                      )
                    }
                    disabled={loading || filteredEnrollments.length === 0}
                  />
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Student
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Course
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Progress
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Enrollment Date
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
                    colSpan={7}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    Loading enrollments...
                  </td>
                </tr>
              ) : filteredEnrollments.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    No enrollments found
                  </td>
                </tr>
              ) : (
                filteredEnrollments.map((enrollment) => (
                  <tr
                    key={enrollment.id}
                    className={`hover:bg-gray-50 ${selectedIds.has(enrollment.id) ? "bg-blue-50/40" : ""}`}
                  >
                    <td className="px-4 py-4">
                      <input
                        type="checkbox"
                        aria-label={`Select enrollment ${enrollment.id}`}
                        checked={selectedIds.has(enrollment.id)}
                        onChange={() => toggleSelected(enrollment.id)}
                      />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold">
                          {enrollment.student_name.charAt(0)}
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {enrollment.student_name}
                          </div>
                          <div className="text-sm text-gray-500">
                            {enrollment.student_email}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <Link
                        to={`/courses/${enrollment.course_id}`}
                        className="text-sm font-medium text-blue-600 hover:text-blue-800 line-clamp-2"
                      >
                        {enrollment.course_title}
                      </Link>
                      <div className="text-xs text-gray-500 mt-1">
                        {enrollment.completed_lessons} /{" "}
                        {enrollment.total_lessons} lessons
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="w-full">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-gray-700">
                            {enrollment.progress}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${enrollment.progress}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-500">
                        <Calendar className="w-4 h-4 mr-2" />
                        {formatDate(enrollment.enrollment_date)}
                      </div>
                      {enrollment.completion_date && (
                        <div className="text-xs text-green-600 mt-1">
                          Completed: {formatDate(enrollment.completion_date)}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(enrollment.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <select
                        value={enrollment.status}
                        onChange={(e) =>
                          updateEnrollmentStatus(enrollment.id, e.target.value)
                        }
                        className="px-3 py-1 border border-gray-300 rounded text-xs focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="enrolled">Enrolled</option>
                        <option value="completed">Completed</option>
                        <option value="cancelled">Cancelled</option>
                      </select>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </PageLayout>
  );
};
