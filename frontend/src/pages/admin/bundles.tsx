import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useState, useEffect } from "react";
import { Plus, Package, TrendingUp, Layers } from "lucide-react";
import { api } from "@/api/axios";
import toast from "react-hot-toast";

const MAX_BUNDLE_COURSES = 20;
const MIN_BUNDLE_COURSES = 2;
const SLUG_PATTERN = /^[a-z0-9-]+$/;

interface BundleCourse {
  id: number;
  title: string;
  price: number;
}

interface AdminBundle {
  id: number;
  slug: string;
  name: string;
  description: string;
  bundle_price: number;
  combined_price: number;
  courses: BundleCourse[];
  is_active: boolean;
  sales_count: number;
}

export function BundlesPage() {
  const [bundles, setBundles] = useState<AdminBundle[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingBundle, setEditingBundle] = useState<AdminBundle | null>(null);

  useEffect(() => {
    fetchBundles();
  }, []);

  const fetchBundles = async () => {
    try {
      setLoading(true);
      const response = await api.get("/admin/bundles");
      setBundles(response.data || []);
    } catch (error: any) {
      console.error("Error fetching bundles:", error);
      toast.error("Failed to fetch bundles");
    } finally {
      setLoading(false);
    }
  };

  const toggleBundleStatus = async (bundle: AdminBundle) => {
    try {
      await api.patch(`/admin/bundles/${bundle.id}`, {
        is_active: !bundle.is_active,
      });
      toast.success(
        `Bundle ${!bundle.is_active ? "activated" : "deactivated"}`,
      );
      fetchBundles();
    } catch (error: any) {
      console.error("Error updating bundle:", error);
      toast.error(
        error.response?.data?.detail || "Failed to update bundle status",
      );
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <PageLayout
        header={
          <PageHeader>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Bundle Management
              </h1>
              <p className="text-gray-600">
                Create and manage multi-course bundles
              </p>
            </div>
          </PageHeader>
        }
        className="rd-screen rd-screen-admin-bundles"
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Bundles</p>
                <p className="text-2xl font-bold text-gray-900">
                  {bundles.length}
                </p>
              </div>
              <Layers className="w-10 h-10 text-blue-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active Bundles</p>
                <p className="text-2xl font-bold text-green-600">
                  {bundles.filter((b) => b.is_active).length}
                </p>
              </div>
              <TrendingUp className="w-10 h-10 text-green-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Sales</p>
                <p className="text-2xl font-bold text-purple-600">
                  {bundles.reduce((sum, b) => sum + b.sales_count, 0)}
                </p>
              </div>
              <Package className="w-10 h-10 text-purple-500" />
            </div>
          </div>
        </div>
        <div
          className="bg-white rounded-lg shadow p-6 mb-6"
          data-glass="content"
        >
          <div className="flex justify-end">
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <Plus className="w-5 h-5" />
              New Bundle
            </button>
          </div>
        </div>
        <div
          className="bg-white rounded-lg shadow overflow-hidden mb-8"
          data-glass="work"
        >
          {loading ? (
            <div className="p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading bundles...</p>
            </div>
          ) : bundles.length === 0 ? (
            <div className="p-12 text-center">
              <Layers className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-xl text-gray-600 mb-2">No bundles found</p>
              <p className="text-gray-500">
                Create your first bundle to get started
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Bundle
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Price
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Courses
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Sales
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {bundles.map((bundle) => (
                    <tr key={bundle.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-bold text-gray-900">
                            {bundle.name}
                          </div>
                          <div className="text-sm text-gray-500">
                            {bundle.slug}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          ₹{bundle.bundle_price}
                        </div>
                        <div className="text-xs text-gray-500 line-through">
                          ₹{bundle.combined_price}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
                          {bundle.courses.length} course(s)
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {bundle.sales_count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <button
                          onClick={() => toggleBundleStatus(bundle)}
                          className={`px-3 py-1 text-xs font-medium rounded-full ${
                            bundle.is_active
                              ? "bg-green-100 text-green-800 hover:bg-green-200"
                              : "bg-gray-100 text-gray-800 hover:bg-gray-200"
                          }`}
                        >
                          {bundle.is_active ? "Active" : "Inactive"}
                        </button>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => {
                            setEditingBundle(bundle);
                            setShowCreateModal(true);
                          }}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </PageLayout>

      {/* Create/Edit Modal */}
      {showCreateModal && (
        <BundleFormModal
          bundle={editingBundle}
          onClose={() => {
            setShowCreateModal(false);
            setEditingBundle(null);
          }}
          onSuccess={() => {
            setShowCreateModal(false);
            setEditingBundle(null);
            fetchBundles();
          }}
        />
      )}
    </div>
  );
}

// Bundle Form Modal Component
interface BundleFormModalProps {
  bundle: AdminBundle | null;
  onClose: () => void;
  onSuccess: () => void;
}

function BundleFormModal({ bundle, onClose, onSuccess }: BundleFormModalProps) {
  const [formData, setFormData] = useState({
    name: bundle?.name || "",
    slug: bundle?.slug || "",
    description: bundle?.description || "",
    bundle_price: bundle?.bundle_price || 0,
    course_ids: bundle?.courses.map((c) => c.id) || ([] as number[]),
    is_active: bundle?.is_active ?? true,
  });
  const [loading, setLoading] = useState(false);
  const [courses, setCourses] = useState<any[]>([]);

  useEffect(() => {
    fetchCourses();
  }, []);

  const fetchCourses = async () => {
    try {
      const response = await api.get("/courses/", {
        params: { page: 1, page_size: 100 },
      });
      setCourses(response.data.courses || []);
    } catch (error) {
      console.error("Error fetching courses:", error);
    }
  };

  const slugValid = SLUG_PATTERN.test(formData.slug);
  const courseCountValid =
    formData.course_ids.length >= MIN_BUNDLE_COURSES &&
    formData.course_ids.length <= MAX_BUNDLE_COURSES;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!slugValid) {
      toast.error(
        "Slug must contain only lowercase letters, numbers, and hyphens",
      );
      return;
    }
    if (formData.course_ids.length < MIN_BUNDLE_COURSES) {
      toast.error(`Select at least ${MIN_BUNDLE_COURSES} courses`);
      return;
    }
    if (formData.course_ids.length > MAX_BUNDLE_COURSES) {
      toast.error(`Select at most ${MAX_BUNDLE_COURSES} courses`);
      return;
    }

    setLoading(true);

    try {
      if (bundle) {
        const payload = {
          name: formData.name,
          description: formData.description,
          bundle_price: formData.bundle_price,
          course_ids: formData.course_ids,
          is_active: formData.is_active,
        };
        await api.patch(`/admin/bundles/${bundle.id}`, payload);
        toast.success("Bundle updated successfully");
      } else {
        const payload = {
          name: formData.name,
          slug: formData.slug,
          description: formData.description || undefined,
          bundle_price: formData.bundle_price,
          course_ids: formData.course_ids,
        };
        await api.post("/admin/bundles", payload);
        toast.success("Bundle created successfully");
      }

      onSuccess();
    } catch (error: any) {
      console.error("Error saving bundle:", error);
      toast.error(error.response?.data?.detail || "Failed to save bundle");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-modal p-4">
      <div
        className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        data-glass="work"
      >
        <div className="p-6">
          <h2 className="text-2xl font-bold mb-6">
            {bundle ? "Edit Bundle" : "New Bundle"}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Name */}
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Full Stack Starter Pack"
              />
            </div>

            {/* Slug */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Slug *
              </label>
              <input
                type="text"
                required
                disabled={!!bundle}
                value={formData.slug}
                onChange={(e) =>
                  setFormData({ ...formData, slug: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                placeholder="e.g., full-stack-starter-pack"
              />
              {formData.slug && !slugValid && (
                <p className="text-xs text-red-600 mt-1">
                  Lowercase letters, numbers, and hyphens only.
                </p>
              )}
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                rows={2}
                placeholder="Brief description of the bundle"
              />
            </div>

            {/* Price */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Bundle Price (₹) *
              </label>
              <input
                type="number"
                required
                min="0.01"
                step="0.01"
                value={formData.bundle_price}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    bundle_price: parseFloat(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="Amount"
              />
            </div>

            {/* Course Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select Courses * ({formData.course_ids.length}/
                {MAX_BUNDLE_COURSES})
              </label>
              <div className="border border-gray-300 rounded-lg p-3 max-h-48 overflow-y-auto">
                {courses.map((course) => {
                  const checked = formData.course_ids.includes(course.id);
                  const atMax =
                    formData.course_ids.length >= MAX_BUNDLE_COURSES;
                  return (
                    <label
                      key={course.id}
                      className={`flex items-center gap-2 p-2 rounded ${
                        !checked && atMax
                          ? "opacity-50 cursor-not-allowed"
                          : "hover:bg-gray-50 cursor-pointer"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={!checked && atMax}
                        onChange={(e) => {
                          if (e.target.checked) {
                            if (
                              formData.course_ids.length >= MAX_BUNDLE_COURSES
                            )
                              return;
                            setFormData({
                              ...formData,
                              course_ids: [...formData.course_ids, course.id],
                            });
                          } else {
                            setFormData({
                              ...formData,
                              course_ids: formData.course_ids.filter(
                                (id) => id !== course.id,
                              ),
                            });
                          }
                        }}
                        className="rounded"
                      />
                      <span className="text-sm">{course.title}</span>
                    </label>
                  );
                })}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {!courseCountValid &&
                formData.course_ids.length < MIN_BUNDLE_COURSES
                  ? `Select at least ${MIN_BUNDLE_COURSES} courses.`
                  : `Maximum ${MAX_BUNDLE_COURSES} courses per bundle.`}
              </p>
            </div>

            {/* Active Status (edit only) */}
            {bundle && (
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) =>
                    setFormData({ ...formData, is_active: e.target.checked })
                  }
                  className="rounded"
                />
                <label
                  htmlFor="is_active"
                  className="text-sm font-medium text-gray-700"
                >
                  Active (bundle can be purchased)
                </label>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex justify-end gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {loading
                  ? "Saving..."
                  : bundle
                    ? "Update Bundle"
                    : "Create Bundle"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
