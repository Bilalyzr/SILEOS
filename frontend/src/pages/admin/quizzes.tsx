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
  HelpCircle,
  CheckCircle,
  Clock,
  Award,
  Users,
} from "lucide-react";
import api from "@/api/axios";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";

interface Quiz {
  id: number;
  title: string;
  course_title: string;
  course_id: number;
  total_questions: number;
  time_limit: number;
  passing_grade: number;
  attempts: number;
  status: string;
  created_at: string;
}

export const AdminQuizzes: React.FC = () => {
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const loadQuizzes = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get("/admin/quizzes");
      setQuizzes(res.data?.items || []);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to load quizzes");
      setQuizzes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQuizzes();
  }, [loadQuizzes]);

  const handleDelete = async (quiz: Quiz) => {
    const ok = await confirmDialog(
      `Delete quiz "${quiz.title}"? This will remove all questions and attempts.`,
    );
    if (!ok) return;
    try {
      setDeletingId(quiz.id);
      await api.delete(`/admin/quizzes/${quiz.id}`);
      setQuizzes((prev) => prev.filter((q) => q.id !== quiz.id));
      toast.success("Quiz deleted");
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  const filteredQuizzes = quizzes.filter(
    (quiz) =>
      quiz.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      quiz.course_title.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Quizzes</h1>
            <p className="text-gray-600 mt-1">
              Manage all course quizzes and assessments
            </p>
          </div>
          <ExportImportPanel section="quizzes" />
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-quizzes"
    >
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Quizzes</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {quizzes.length}
              </p>
            </div>
            <HelpCircle className="w-8 h-8 text-blue-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Questions</p>
              <p className="text-2xl font-bold text-purple-600 mt-1">
                {quizzes.reduce((sum, q) => sum + q.total_questions, 0)}
              </p>
            </div>
            <CheckCircle className="w-8 h-8 text-purple-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Attempts</p>
              <p className="text-2xl font-bold text-green-600 mt-1">
                {quizzes.reduce((sum, q) => sum + q.attempts, 0)}
              </p>
            </div>
            <Users className="w-8 h-8 text-green-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Avg Pass Grade</p>
              <p className="text-2xl font-bold text-orange-600 mt-1">
                {quizzes.length > 0
                  ? Math.round(
                      quizzes.reduce((sum, q) => sum + q.passing_grade, 0) /
                        quizzes.length,
                    )
                  : 0}
                %
              </p>
            </div>
            <Award className="w-8 h-8 text-orange-600" />
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
            placeholder="Search quizzes..."
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
                  Quiz
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Course
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Questions
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Time Limit
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Pass Grade
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Attempts
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
                    Loading quizzes...
                  </td>
                </tr>
              ) : filteredQuizzes.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    <div className="flex flex-col items-center space-y-3">
                      <HelpCircle className="w-12 h-12 text-gray-400" />
                      <p>No quizzes found</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredQuizzes.map((quiz) => (
                  <tr key={quiz.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">
                        {quiz.title}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <Link
                        to={`/admin/courses/${quiz.course_id}/edit`}
                        className="text-sm text-blue-600 hover:text-blue-800"
                      >
                        {quiz.course_title}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900">
                        <CheckCircle className="w-4 h-4 mr-2 text-gray-400" />
                        {quiz.total_questions}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-500">
                        <Clock className="w-4 h-4 mr-2" />
                        {quiz.time_limit > 0
                          ? `${quiz.time_limit} min`
                          : "Unlimited"}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {quiz.passing_grade}%
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-500">
                        <Users className="w-4 h-4 mr-2" />
                        {quiz.attempts}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                        {quiz.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center space-x-2">
                        <Link
                          to={`/admin/courses/${quiz.course_id}/edit`}
                          className="text-blue-600 hover:text-blue-900"
                          title="View course"
                        >
                          <Eye className="w-4 h-4" />
                        </Link>
                        <Link
                          to={`/admin/courses/${quiz.course_id}/edit`}
                          className="text-gray-600 hover:text-gray-900"
                          title="Edit in course"
                        >
                          <Edit className="w-4 h-4" />
                        </Link>
                        <button
                          type="button"
                          onClick={() => handleDelete(quiz)}
                          disabled={deletingId === quiz.id}
                          className="text-red-600 hover:text-red-900 disabled:opacity-50"
                          title="Delete quiz"
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
