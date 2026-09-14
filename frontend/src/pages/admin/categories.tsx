import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { getAuthToken } from "@/utils/auth-helper";
import { confirmDialog } from "@/components/ui/confirm";
import React, { useState, useEffect } from "react";
import {
  Plus,
  Search,
  Edit,
  Trash2,
  Tag as TagIcon,
  BookOpen,
} from "lucide-react";

const API_BASE_URL = "/api/v1";

interface Category {
  id: number;
  name: string;
  slug: string;
  description: string;
  course_count: number;
  created_at: string;
}

export const AdminCategories: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [formData, setFormData] = useState({ name: "", description: "" });

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/admin/categories`, {
        headers: {
          Authorization: `Bearer ${getAuthToken()}`,
        },
      });
      const data = await response.json();
      setCategories(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error fetching categories:", error);
      setCategories([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const url = editingCategory
        ? `${API_BASE_URL}/admin/categories/${editingCategory.id}`
        : `${API_BASE_URL}/admin/categories`;

      const response = await fetch(url, {
        method: editingCategory ? "PUT" : "POST",
        headers: {
          Authorization: `Bearer ${getAuthToken()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        fetchCategories();
        setShowModal(false);
        setEditingCategory(null);
        setFormData({ name: "", description: "" });
      }
    } catch (error) {
      console.error("Error saving category:", error);
    }
  };

  const handleDelete = async (categoryId: number) => {
    if (
      !(await confirmDialog("Are you sure you want to delete this category?"))
    )
      return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/admin/categories/${categoryId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${getAuthToken()}`,
          },
        },
      );

      if (response.ok) {
        fetchCategories();
      }
    } catch (error) {
      console.error("Error deleting category:", error);
    }
  };

  const handleEdit = (category: Category) => {
    setEditingCategory(category);
    setFormData({ name: category.name, description: category.description });
    setShowModal(true);
  };

  const filteredCategories = categories.filter((category) =>
    category.name.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Course Categories
            </h1>
            <p className="text-gray-600 mt-1">
              Organize your courses with categories
            </p>
          </div>
          <button
            onClick={() => {
              setEditingCategory(null);
              setFormData({ name: "", description: "" });
              setShowModal(true);
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Add Category</span>
          </button>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-categories"
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Categories</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {categories.length}
              </p>
            </div>
            <TagIcon className="w-8 h-8 text-blue-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Courses</p>
              <p className="text-2xl font-bold text-green-600 mt-1">
                {categories.reduce((sum, cat) => sum + cat.course_count, 0)}
              </p>
            </div>
            <BookOpen className="w-8 h-8 text-green-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Avg Courses/Category</p>
              <p className="text-2xl font-bold text-purple-600 mt-1">
                {categories.length > 0
                  ? Math.round(
                      categories.reduce(
                        (sum, cat) => sum + cat.course_count,
                        0,
                      ) / categories.length,
                    )
                  : 0}
              </p>
            </div>
            <BookOpen className="w-8 h-8 text-purple-600" />
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
            placeholder="Search categories..."
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
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Slug
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Description
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Courses
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
                    colSpan={5}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    Loading categories...
                  </td>
                </tr>
              ) : filteredCategories.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    No categories found
                  </td>
                </tr>
              ) : (
                filteredCategories.map((category) => (
                  <tr key={category.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {category.name}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">
                        {category.slug}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-500 line-clamp-2">
                        {category.description || "-"}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900">
                        <BookOpen className="w-4 h-4 mr-2 text-gray-400" />
                        {category.course_count}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handleEdit(category)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(category.id)}
                          className="text-red-600 hover:text-red-900"
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
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-modal">
          <div
            className="bg-white rounded-lg p-6 w-full max-w-md"
            data-glass="work"
          >
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              {editingCategory ? "Edit Category" : "Add New Category"}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    setEditingCategory(null);
                    setFormData({ name: "", description: "" });
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  {editingCategory ? "Update" : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </PageLayout>
  );
};
