import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback } from "react";
import React, { useState, useEffect } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Mail,
  Ban,
  CheckCircle,
  BookOpen,
  Calendar,
  TrendingUp,
  Trash2,
  GraduationCap,
  Eye,
  Phone,
} from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/api/axios";
import { adminApi } from "@/api/admin";
import { useAuthStore } from "@/store/auth";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";
import { TableScrollArea } from "@/components/admin/TableScrollArea";
import { PasswordResetLinkAction } from "@/components/admin/PasswordResetLinkAction";
import { Pagination } from "@/components/ui/pagination";

const PER_PAGE = 50;

interface Student {
  id: number;
  username: string;
  email: string;
  display_name: string;
  role: string;
  status: string;
  is_verified?: boolean;
  joined_date: string;
  last_login: string | null;
  total_courses: number;
  profile_complete: boolean;
  phone?: string;
}

export const AdminStudents: React.FC = () => {
  const navigate = useNavigate();
  const startStudentImpersonation = useAuthStore(
    (s) => s.startStudentImpersonation,
  );
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterVerification, setFilterVerification] = useState<
    "all" | "verified" | "unverified"
  >("all");
  const [impersonatingId, setImpersonatingId] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  const fetchStudents = useCallback(async () => {
    try {
      setLoading(true);
      const statusParam =
        filterStatus !== "all" ? `&status=${filterStatus}` : "";
      const r = await api.get(
        `/admin/users?role=student&limit=2000${statusParam}`,
      );
      const data = r.data;
      setStudents(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error fetching students:", error);
      setStudents([]);
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);
  useEffect(() => {
    fetchStudents();
  }, [fetchStudents, filterStatus]);

  // Reset to the first page whenever the visible set changes.
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, filterStatus, filterVerification]);

  const updateStudentStatus = async (studentId: number, newStatus: string) => {
    try {
      // Backend reads the status from the query string, not the body.
      await api.put(
        `/admin/users/${studentId}/status?status=${encodeURIComponent(newStatus)}`,
      );
      toast.success(
        `Student ${newStatus === "active" ? "activated" : newStatus}`,
      );
      fetchStudents();
    } catch (error: any) {
      console.error("Error updating student status:", error);
      toast.error(error?.response?.data?.detail || "Failed to update status");
    }
  };

  const deleteStudent = async (studentId: number, studentName: string) => {
    const confirmed = await confirmDialog(
      `Delete ${studentName}? This wipes their account, enrollments, progress, and cert records. This cannot be undone.`,
    );
    if (!confirmed) return;
    try {
      await api.delete(`/admin/users/${studentId}`);
      toast.success(`${studentName} deleted`);
      fetchStudents();
    } catch (error: any) {
      console.error("Error deleting student:", error);
      toast.error(error?.response?.data?.detail || "Failed to delete student");
    }
  };

  const resendVerification = async (email: string) => {
    try {
      await api.post(`/auth/resend-verification`, { email });
      toast.success("Verification email resent");
    } catch (error: any) {
      console.error("Error resending verification:", error);
      toast.error(
        error?.response?.data?.detail || "Failed to resend verification",
      );
    }
  };

  const promoteToInstructor = async (
    studentId: number,
    studentName: string,
  ) => {
    const confirmed = await confirmDialog(
      `Promote ${studentName} to Instructor?\n\nThis will grant them instructor privileges including the ability to create and manage courses.`,
    );
    if (!confirmed) return;

    try {
      await api.put(`/admin/users/${studentId}/role`, { role: "instructor" });
      toast.success(`${studentName} has been promoted to Instructor`);
      fetchStudents();
    } catch (error: any) {
      console.error("Error promoting to instructor:", error);
      toast.error(
        error?.response?.data?.detail || "Failed to promote to instructor",
      );
    }
  };

  const viewAsStudent = async (studentId: number, studentName: string) => {
    const confirmed = await confirmDialog(
      `Start a 30-minute "View as Student" session as ${studentName}?\n\nYou'll be able to see and interact with the LMS exactly as this student sees it. The session expires in 30 minutes.`,
    );
    if (!confirmed) return;

    try {
      setImpersonatingId(studentId);
      const res = await adminApi.impersonateStudent(studentId);
      await startStudentImpersonation(
        res.target.id,
        res.target.display_name,
        res.target.email,
        res.access_token,
      );
      navigate("/dashboard");
      toast.success(`Viewing as ${studentName}. Session ends in 30 minutes.`);
    } catch (error: any) {
      console.error("Error starting student impersonation:", error);
      toast.error(
        error?.response?.data?.detail || "Failed to start impersonation",
      );
      setImpersonatingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    // Static class strings — Tailwind can't generate `bg-${x}-100` at runtime.
    const badges = {
      active: {
        classes: "bg-green-100 text-green-800",
        text: "Active",
        icon: CheckCircle,
      },
      inactive: {
        classes: "bg-gray-100 text-gray-800",
        text: "Inactive",
        icon: Ban,
      },
      suspended: {
        classes: "bg-red-100 text-red-800",
        text: "Suspended",
        icon: Ban,
      },
    };
    const badge = badges[status as keyof typeof badges] || badges.active;
    const Icon = badge.icon;
    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badge.classes}`}
      >
        <Icon className="w-3 h-3 mr-1" />
        {badge.text}
      </span>
    );
  };

  const filteredStudents = students.filter((student) => {
    // Search filter
    const matchesSearch =
      student.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      student.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      student.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (student.phone || "").toLowerCase().includes(searchTerm.toLowerCase());

    // Verification filter
    const matchesVerification =
      filterVerification === "all" ||
      (filterVerification === "verified" && student.is_verified !== false) ||
      (filterVerification === "unverified" && student.is_verified === false);

    return matchesSearch && matchesVerification;
  });

  const totalPages = Math.ceil(filteredStudents.length / PER_PAGE);
  const paginatedStudents = filteredStudents.slice(
    (currentPage - 1) * PER_PAGE,
    currentPage * PER_PAGE,
  );

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Students</h1>
            <p className="text-gray-600 mt-1">
              Manage all students in your LMS
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <div className="text-sm text-gray-600">
              <span className="font-semibold">{filteredStudents.length}</span>{" "}
              students
            </div>
            <ExportImportPanel
              section="students"
              onImportComplete={fetchStudents}
            />
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-students"
    >
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-4">
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Students</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {students.length}
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
              <p className="text-sm text-gray-600">Active</p>
              <p className="text-2xl font-bold text-green-600 mt-1">
                {students.filter((s) => s.status === "active").length}
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
              <p className="text-sm text-gray-600">Suspended</p>
              <p className="text-2xl font-bold text-red-600 mt-1">
                {students.filter((s) => s.status === "suspended").length}
              </p>
            </div>
            <Ban className="w-8 h-8 text-red-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Verified</p>
              <p className="text-2xl font-bold text-emerald-600 mt-1">
                {students.filter((s) => s.is_verified !== false).length}
              </p>
            </div>
            <CheckCircle className="w-8 h-8 text-emerald-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Unverified</p>
              <p className="text-2xl font-bold text-amber-600 mt-1">
                {students.filter((s) => s.is_verified === false).length}
              </p>
            </div>
            <Mail className="w-8 h-8 text-amber-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">New (30 days)</p>
              <p className="text-2xl font-bold text-purple-600 mt-1">
                {
                  students.filter((s) => {
                    const joinDate = new Date(s.joined_date);
                    const thirtyDaysAgo = new Date();
                    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
                    return joinDate >= thirtyDaysAgo;
                  }).length
                }
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
                placeholder="Search students..."
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
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="suspended">Suspended</option>
            </select>
            <select
              value={filterVerification}
              onChange={(e) =>
                setFilterVerification(
                  e.target.value as "all" | "verified" | "unverified",
                )
              }
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Verification</option>
              <option value="verified">Verified</option>
              <option value="unverified">Unverified</option>
            </select>
          </div>
        </div>
      </div>
      <div
        className="bg-white rounded-lg border border-gray-200 overflow-hidden"
        data-glass="work"
      >
        <TableScrollArea>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Student
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Phone
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Enrolled Courses
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Join Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Login
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
                    colSpan={8}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    Loading students...
                  </td>
                </tr>
              ) : filteredStudents.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    No students found
                  </td>
                </tr>
              ) : (
                paginatedStudents.map((student) => (
                  <tr key={student.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold">
                          {student.display_name.charAt(0)}
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {student.display_name}
                          </div>
                          <div className="text-sm text-gray-500">
                            @{student.username}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900">
                        <Mail className="w-4 h-4 mr-2 text-gray-400" />
                        {student.email}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900">
                        <Phone className="w-4 h-4 mr-2 text-gray-400" />
                        {student.phone || "-"}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900">
                        <BookOpen className="w-4 h-4 mr-2 text-gray-400" />
                        {student.total_courses}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-500">
                        <Calendar className="w-4 h-4 mr-2" />
                        {formatDate(student.joined_date)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {student.last_login
                        ? formatDate(student.last_login)
                        : "Never"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex flex-col gap-1">
                        {getStatusBadge(student.status)}
                        {student.is_verified === false && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                            Unverified
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-1">
                        {student.is_verified === false && (
                          <button
                            onClick={() => resendVerification(student.email)}
                            className="p-2 rounded-lg text-amber-600 hover:bg-amber-50 transition-colors"
                            title="Resend verification email"
                          >
                            <Mail className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() =>
                            viewAsStudent(student.id, student.display_name)
                          }
                          disabled={impersonatingId === student.id}
                          className="p-2 rounded-lg text-purple-600 hover:bg-purple-50 transition-colors disabled:opacity-50"
                          title="View as Student (30-min session)"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() =>
                            promoteToInstructor(
                              student.id,
                              student.display_name,
                            )
                          }
                          className="p-2 rounded-lg text-indigo-600 hover:bg-indigo-50 transition-colors"
                          title="Promote to Instructor"
                        >
                          <GraduationCap className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() =>
                            updateStudentStatus(
                              student.id,
                              student.status === "active"
                                ? "suspended"
                                : "active",
                            )
                          }
                          className={`p-2 rounded-lg transition-colors ${
                            student.status === "active"
                              ? "text-red-600 hover:bg-red-50"
                              : "text-green-600 hover:bg-green-50"
                          }`}
                          title={
                            student.status === "active"
                              ? "Suspend student"
                              : "Activate student"
                          }
                        >
                          {student.status === "active" ? (
                            <Ban className="w-4 h-4" />
                          ) : (
                            <CheckCircle className="w-4 h-4" />
                          )}
                        </button>
                        {/* A-H3: one-time reset link (admin never sets a password directly) */}
                        <PasswordResetLinkAction
                          userId={student.id}
                          userName={student.display_name}
                          compact
                        />
                        <button
                          onClick={() =>
                            deleteStudent(student.id, student.display_name)
                          }
                          className="p-2 rounded-lg text-red-600 hover:bg-red-50 transition-colors"
                          title="Delete user permanently"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </TableScrollArea>
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={setCurrentPage}
          totalItems={filteredStudents.length}
          pageSize={PER_PAGE}
        />
      </div>
    </PageLayout>
  );
};
