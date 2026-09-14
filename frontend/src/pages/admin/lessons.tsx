import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useState, useEffect, useCallback } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import {
  Search,
  Edit,
  Trash2,
  Eye,
  BookOpen,
  Video,
  FileText,
  Clock,
} from "lucide-react";
import api from "@/api/axios";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";

interface Lesson {
  id: number;
  title: string;
  course_title: string;
  course_id: number;
  type: string;
  duration: string;
  status: string;
  order: number;
  created_at: string;
}

export const AdminLessons: React.FC = () => {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const loadLessons = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get("/admin/lessons");
      setLessons(res.data?.items || []);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to load lessons");
      setLessons([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLessons();
  }, [loadLessons]);

  const handleDelete = async (lesson: Lesson) => {
    const ok = await confirmDialog(
      `Delete lesson "${lesson.title}"? This cannot be undone.`,
    );
    if (!ok) return;
    try {
      setDeletingId(lesson.id);
      await api.delete(`/admin/lessons/${lesson.id}`);
      setLessons((prev) => prev.filter((l) => l.id !== lesson.id));
      toast.success("Lesson deleted");
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  const filteredLessons = lessons.filter(
    (lesson) =>
      lesson.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lesson.course_title.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Lessons</h1>
            <p className="text-gray-600 mt-1">
              Manage all course lessons across the platform
            </p>
          </div>
          <ExportImportPanel section="lessons" />
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-lessons"
    >
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Lessons</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {lessons.length}
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
              <p className="text-sm text-gray-600">Video Lessons</p>
              <p className="text-2xl font-bold text-purple-600 mt-1">
                {lessons.filter((l) => l.type === "video").length}
              </p>
            </div>
            <Video className="w-8 h-8 text-purple-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Text Lessons</p>
              <p className="text-2xl font-bold text-green-600 mt-1">
                {lessons.filter((l) => l.type === "text").length}
              </p>
            </div>
            <FileText className="w-8 h-8 text-green-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Published</p>
              <p className="text-2xl font-bold text-orange-600 mt-1">
                {
                  lessons.filter(
                    (l) => l.status === "publish" || l.status === "published",
                  ).length
                }
              </p>
            </div>
            <Clock className="w-8 h-8 text-orange-600" />
          </div>
        </div>
      </div>
      <div
        className="bg-white rounded-lg border border-gray-200 p-4"
        data-glass="work"
      >
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="Search lessons..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Lesson
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Course
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Order
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
                    Loading lessons...
                  </td>
                </tr>
              ) : filteredLessons.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    <div className="flex flex-col items-center space-y-3">
                      <BookOpen className="w-12 h-12 text-gray-400" />
                      <p>No lessons found</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredLessons.map((lesson) => (
                  <tr key={lesson.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">
                        {lesson.title}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <Link
                        to={`/admin/courses/${lesson.course_id}/edit`}
                        className="text-sm text-blue-600 hover:text-blue-800"
                      >
                        {lesson.course_title}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900">
                        {lesson.type === "video" ? (
                          <Video className="w-4 h-4 mr-2 text-purple-600" />
                        ) : (
                          <FileText className="w-4 h-4 mr-2 text-green-600" />
                        )}
                        {lesson.type}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {lesson.duration}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      #{lesson.order}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                        {lesson.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center space-x-2">
                        <Link
                          to={`/admin/courses/${lesson.course_id}/edit`}
                          className="text-blue-600 hover:text-blue-900"
                          title="View course"
                        >
                          <Eye className="w-4 h-4" />
                        </Link>
                        <Link
                          to={`/admin/courses/${lesson.course_id}/edit`}
                          className="text-gray-600 hover:text-gray-900"
                          title="Edit in course"
                        >
                          <Edit className="w-4 h-4" />
                        </Link>
                        <button
                          type="button"
                          onClick={() => handleDelete(lesson)}
                          disabled={deletingId === lesson.id}
                          className="text-red-600 hover:text-red-900 disabled:opacity-50"
                          title="Delete lesson"
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
        </div>
      </div>
    </PageLayout>
  );
};
