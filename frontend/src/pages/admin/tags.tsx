import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { getAuthToken } from "@/utils/auth-helper";
import { confirmDialog } from "@/components/ui/confirm";
import React, { useState, useEffect } from "react";
import { TagClustersPanel } from "@/components/admin/TagClustersPanel";
import {
  Plus,
  Search,
  Edit,
  Trash2,
  Tag as TagIcon,
  BookOpen,
} from "lucide-react";

const API_BASE_URL = "/api/v1";

interface Tag {
  id: number;
  name: string;
  slug: string;
  description: string;
  course_count: number;
  created_at: string;
}

export const AdminTags: React.FC = () => {
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [formData, setFormData] = useState({ name: "", description: "" });

  useEffect(() => {
    fetchTags();
  }, []);

  const fetchTags = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/admin/tags`, {
        headers: {
          Authorization: `Bearer ${getAuthToken()}`,
        },
      });
      const data = await response.json();
      setTags(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error fetching tags:", error);
      setTags([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const url = editingTag
        ? `${API_BASE_URL}/admin/tags/${editingTag.id}`
        : `${API_BASE_URL}/admin/tags`;

      const response = await fetch(url, {
        method: editingTag ? "PUT" : "POST",
        headers: {
          Authorization: `Bearer ${getAuthToken()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        fetchTags();
        setShowModal(false);
        setEditingTag(null);
        setFormData({ name: "", description: "" });
      }
    } catch (error) {
      console.error("Error saving tag:", error);
    }
  };

  const handleDelete = async (tagId: number) => {
    if (!(await confirmDialog("Are you sure you want to delete this tag?")))
      return;

    try {
      const response = await fetch(`${API_BASE_URL}/admin/tags/${tagId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${getAuthToken()}`,
        },
      });

      if (response.ok) {
        fetchTags();
      }
    } catch (error) {
      console.error("Error deleting tag:", error);
    }
  };

  const handleEdit = (tag: Tag) => {
    setEditingTag(tag);
    setFormData({ name: tag.name, description: tag.description });
    setShowModal(true);
  };

  const filteredTags = tags.filter((tag) =>
    tag.name.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Course Tags</h1>
            <p className="text-gray-600 mt-1">
              Tag your courses for better organization
            </p>
          </div>
          <button
            onClick={() => {
              setEditingTag(null);
              setFormData({ name: "", description: "" });
              setShowModal(true);
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Add Tag</span>
          </button>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-tags"
    >
      <TagClustersPanel />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Tags</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {tags.length}
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
                {tags.reduce((sum, tag) => sum + tag.course_count, 0)}
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
              <p className="text-sm text-gray-600">Avg Courses/Tag</p>
              <p className="text-2xl font-bold text-purple-600 mt-1">
                {tags.length > 0
                  ? Math.round(
                      tags.reduce((sum, tag) => sum + tag.course_count, 0) /
                        tags.length,
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
            placeholder="Search tags..."
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
                    Loading tags...
                  </td>
                </tr>
              ) : filteredTags.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    No tags found
                  </td>
                </tr>
              ) : (
                filteredTags.map((tag) => (
                  <tr key={tag.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                          <TagIcon className="w-4 h-4 text-blue-600" />
                        </div>
                        <div className="text-sm font-medium text-gray-900">
                          {tag.name}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">{tag.slug}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-500 line-clamp-2">
                        {tag.description || "-"}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900">
                        <BookOpen className="w-4 h-4 mr-2 text-gray-400" />
                        {tag.course_count}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handleEdit(tag)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(tag.id)}
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
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div
            className="bg-white rounded-lg p-6 w-full max-w-md"
            data-glass="work"
          >
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              {editingTag ? "Edit Tag" : "Add New Tag"}
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
                    setEditingTag(null);
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
                  {editingTag ? "Update" : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </PageLayout>
  );
};
