import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useState, useEffect } from "react";
import { confirmDialog, promptDialog } from "@/components/ui/confirm";
import {
  Plus,
  Edit,
  Trash2,
  Search,
  Tag,
  Calendar,
  Users,
  TrendingUp,
} from "lucide-react";
import { api } from "@/api/axios";
import toast from "react-hot-toast";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";

interface Coupon {
  id: number;
  code: string;
  description: string;
  discount_type: string;
  discount_value: number;
  applicability: string;
  course_ids?: number[];
  usage_count: number;
  usage_limit: number | null;
  is_active: boolean;
  valid_until: string | null;
  created_at: string;
}

export function CouponsPage() {
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterActive, setFilterActive] = useState<boolean | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingCoupon, setEditingCoupon] = useState<Coupon | null>(null);

  useEffect(() => {
    // Refetch on filter change immediately, and on search after a short debounce
    // so typing in the search box actually filters (it previously did nothing).
    const t = setTimeout(fetchCoupons, searchQuery ? 300 : 0);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterActive, searchQuery]);

  const fetchCoupons = async () => {
    try {
      setLoading(true);
      const params: any = { page: 1, page_size: 100 };
      if (filterActive !== null) params.is_active = filterActive;
      if (searchQuery) params.search = searchQuery;

      const response = await api.get("/coupons/", { params });
      setCoupons(response.data.coupons || []);
    } catch (error: any) {
      console.error("Error fetching coupons:", error);
      toast.error("Failed to fetch coupons");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (couponId: number) => {
    if (!(await confirmDialog("Are you sure you want to delete this coupon?")))
      return;

    try {
      await api.delete(`/coupons/${couponId}`);
      toast.success("Coupon deleted successfully");
      fetchCoupons();
    } catch (error: any) {
      console.error("Error deleting coupon:", error);
      toast.error(error.response?.data?.detail || "Failed to delete coupon");
    }
  };

  const toggleCouponStatus = async (coupon: Coupon) => {
    try {
      await api.put(`/coupons/${coupon.id}`, {
        is_active: !coupon.is_active,
      });
      toast.success(
        `Coupon ${!coupon.is_active ? "activated" : "deactivated"}`,
      );
      fetchCoupons();
    } catch (error: any) {
      console.error("Error updating coupon:", error);
      toast.error("Failed to update coupon status");
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "No expiry";
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const getUsagePercentage = (coupon: Coupon) => {
    if (!coupon.usage_limit) return 0;
    return (coupon.usage_count / coupon.usage_limit) * 100;
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <PageLayout
        header={
          <PageHeader>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Coupon Management
              </h1>
              <p className="text-gray-600">
                Create and manage discount coupons for your courses
              </p>
            </div>
            <ExportImportPanel section="coupons" />
          </PageHeader>
        }
        className="rd-screen rd-screen-admin-coupons"
      >
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Coupons</p>
                <p className="text-2xl font-bold text-gray-900">
                  {coupons.length}
                </p>
              </div>
              <Tag className="w-10 h-10 text-blue-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active Coupons</p>
                <p className="text-2xl font-bold text-green-600">
                  {coupons.filter((c) => c.is_active).length}
                </p>
              </div>
              <TrendingUp className="w-10 h-10 text-green-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Usage</p>
                <p className="text-2xl font-bold text-purple-600">
                  {coupons.reduce((sum, c) => sum + c.usage_count, 0)}
                </p>
              </div>
              <Users className="w-10 h-10 text-purple-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Expiring Soon</p>
                <p className="text-2xl font-bold text-orange-600">
                  {
                    coupons.filter((c) => {
                      if (!c.valid_until) return false;
                      const daysUntilExpiry = Math.ceil(
                        (new Date(c.valid_until).getTime() - Date.now()) /
                          (1000 * 60 * 60 * 24),
                      );
                      return daysUntilExpiry <= 7 && daysUntilExpiry > 0;
                    }).length
                  }
                </p>
              </div>
              <Calendar className="w-10 h-10 text-orange-500" />
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6 mb-6" data-glass="work">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search coupons..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div className="flex gap-2">
              <select
                value={
                  filterActive === null
                    ? "all"
                    : filterActive
                      ? "active"
                      : "inactive"
                }
                onChange={(e) => {
                  const value = e.target.value;
                  setFilterActive(value === "all" ? null : value === "active");
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>

              <button
                onClick={() => setShowCreateModal(true)}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
              >
                <Plus className="w-5 h-5" />
                Create Coupon
              </button>
            </div>
          </div>
        </div>
        <div
          className="bg-white rounded-lg shadow overflow-hidden"
          data-glass="work"
        >
          {loading ? (
            <div className="p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading coupons...</p>
            </div>
          ) : coupons.length === 0 ? (
            <div className="p-12 text-center">
              <Tag className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-xl text-gray-600 mb-2">No coupons found</p>
              <p className="text-gray-500">
                Create your first coupon to get started
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Coupon Code
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Discount
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Applicability
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Usage
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Valid Until
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
                  {coupons.map((coupon) => (
                    <tr key={coupon.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-bold text-gray-900">
                            {coupon.code}
                          </div>
                          <div className="text-sm text-gray-500">
                            {coupon.description}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {coupon.discount_type === "percentage"
                            ? `${coupon.discount_value}%`
                            : `₹${coupon.discount_value}`}
                          <button
                            type="button"
                            title="Link a Razorpay Offer so this coupon also works on membership subscriptions"
                            className="block text-[11px] text-violet-700 hover:underline"
                            onClick={async () => {
                              const oid = await promptDialog(
                                `Razorpay Offer id for ${coupon.code} (blank removes). Offers are created in the Razorpay dashboard.`,
                                (coupon as any).razorpay_offer_id || "",
                                {
                                  placeholder: "offer_XXXXXXXXXXXXXX",
                                  confirmLabel: "Save",
                                },
                              );
                              if (oid === null) return;
                              try {
                                await api.patch(
                                  `/coupons/${coupon.id}/membership-offer`,
                                  { razorpay_offer_id: oid },
                                );
                                toast.success(
                                  oid
                                    ? "Membership offer linked"
                                    : "Membership offer removed",
                                );
                                fetchCoupons();
                              } catch (e: any) {
                                toast.error(
                                  e?.response?.data?.detail || "Could not save",
                                );
                              }
                            }}
                          >
                            {(coupon as any).razorpay_offer_id
                              ? "membership offer ✓"
                              : "+ membership offer"}
                          </button>
                        </div>
                        <div className="text-xs text-gray-500 capitalize">
                          {coupon.discount_type}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 text-xs rounded-full ${
                            coupon.applicability === "all_courses"
                              ? "bg-purple-100 text-purple-800"
                              : "bg-blue-100 text-blue-800"
                          }`}
                        >
                          {coupon.applicability === "all_courses"
                            ? "All Courses"
                            : "Specific Courses"}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <div className="flex-1">
                            <div className="text-sm text-gray-900">
                              {coupon.usage_count}{" "}
                              {coupon.usage_limit
                                ? `/ ${coupon.usage_limit}`
                                : ""}
                            </div>
                            {coupon.usage_limit && (
                              <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                                <div
                                  className={`h-2 rounded-full ${
                                    getUsagePercentage(coupon) >= 80
                                      ? "bg-red-600"
                                      : getUsagePercentage(coupon) >= 50
                                        ? "bg-yellow-600"
                                        : "bg-green-600"
                                  }`}
                                  style={{
                                    width: `${Math.min(getUsagePercentage(coupon), 100)}%`,
                                  }}
                                ></div>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(coupon.valid_until)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <button
                          onClick={() => toggleCouponStatus(coupon)}
                          className={`px-3 py-1 text-xs font-medium rounded-full ${
                            coupon.is_active
                              ? "bg-green-100 text-green-800 hover:bg-green-200"
                              : "bg-gray-100 text-gray-800 hover:bg-gray-200"
                          }`}
                        >
                          {coupon.is_active ? "Active" : "Inactive"}
                        </button>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => {
                              setEditingCoupon(coupon);
                              setShowCreateModal(true);
                            }}
                            className="text-blue-600 hover:text-blue-900"
                            title="Edit"
                          >
                            <Edit className="w-5 h-5" />
                          </button>
                          <button
                            onClick={() => handleDelete(coupon.id)}
                            className="text-red-600 hover:text-red-900"
                            title="Delete"
                          >
                            <Trash2 className="w-5 h-5" />
                          </button>
                        </div>
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
        <CouponFormModal
          coupon={editingCoupon}
          onClose={() => {
            setShowCreateModal(false);
            setEditingCoupon(null);
          }}
          onSuccess={() => {
            setShowCreateModal(false);
            setEditingCoupon(null);
            fetchCoupons();
          }}
        />
      )}
    </div>
  );
}

// Coupon Form Modal Component
interface CouponFormModalProps {
  coupon: Coupon | null;
  onClose: () => void;
  onSuccess: () => void;
}

function CouponFormModal({ coupon, onClose, onSuccess }: CouponFormModalProps) {
  const [formData, setFormData] = useState({
    code: coupon?.code || "",
    description: coupon?.description || "",
    discount_type: coupon?.discount_type || "percentage",
    discount_value: coupon?.discount_value || 0,
    applicability: coupon?.applicability || "all_courses",
    course_ids: coupon?.course_ids || ([] as number[]),
    usage_limit: coupon?.usage_limit || null,
    per_user_limit: 1,
    minimum_purchase_amount: 0,
    valid_from: new Date().toISOString().slice(0, 16),
    valid_until: "",
    is_active: coupon?.is_active ?? true,
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        ...formData,
        usage_limit: formData.usage_limit || null,
        valid_from: formData.valid_from || null,
        valid_until: formData.valid_until || null,
      };

      if (coupon) {
        await api.put(`/coupons/${coupon.id}`, payload);
        toast.success("Coupon updated successfully");
      } else {
        await api.post("/coupons/", payload);
        toast.success("Coupon created successfully");
      }

      onSuccess();
    } catch (error: any) {
      console.error("Error saving coupon:", error);
      toast.error(error.response?.data?.detail || "Failed to save coupon");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div
        className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        data-glass="work"
      >
        <div className="p-6">
          <h2 className="text-2xl font-bold mb-6">
            {coupon ? "Edit Coupon" : "Create New Coupon"}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Coupon Code */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Coupon Code *
              </label>
              <input
                type="text"
                required
                disabled={!!coupon}
                value={formData.code}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    code: e.target.value.toUpperCase(),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., SAVE20"
              />
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
                placeholder="Brief description of the coupon"
              />
            </div>

            {/* Discount Type and Value */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Discount Type *
                </label>
                <select
                  required
                  value={formData.discount_type}
                  onChange={(e) =>
                    setFormData({ ...formData, discount_type: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="percentage">Percentage (%)</option>
                  <option value="fixed">Fixed Amount (₹)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Discount Value *
                </label>
                <input
                  type="number"
                  required
                  min="0"
                  max={
                    formData.discount_type === "percentage" ? 100 : undefined
                  }
                  value={formData.discount_value}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      discount_value: parseFloat(e.target.value),
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder={
                    formData.discount_type === "percentage" ? "0-100" : "Amount"
                  }
                />
              </div>
            </div>

            {/* Applicability */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Applicability *
              </label>
              <select
                required
                value={formData.applicability}
                onChange={(e) =>
                  setFormData({ ...formData, applicability: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all_courses">All Courses</option>
                <option value="specific_courses">Specific Courses</option>
              </select>
            </div>

            {/* Course Selection */}
            {formData.applicability === "specific_courses" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Select Courses *
                </label>
                <div className="border border-gray-300 rounded-lg p-3 max-h-48 overflow-y-auto">
                  {courses.map((course) => (
                    <label
                      key={course.id}
                      className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={formData.course_ids.includes(course.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
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
                  ))}
                </div>
              </div>
            )}

            {/* Usage Limits */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Total Usage Limit
                </label>
                <input
                  type="number"
                  min="0"
                  value={formData.usage_limit || ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      usage_limit: e.target.value
                        ? parseInt(e.target.value)
                        : null,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Unlimited"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Leave empty for unlimited
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Per User Limit *
                </label>
                <input
                  type="number"
                  required
                  min="1"
                  value={formData.per_user_limit}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      per_user_limit: parseInt(e.target.value),
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Minimum Purchase */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Minimum Purchase Amount (₹)
              </label>
              <input
                type="number"
                min="0"
                value={formData.minimum_purchase_amount}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    minimum_purchase_amount: parseFloat(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="0"
              />
            </div>

            {/* Validity Dates */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Valid From
                </label>
                <input
                  type="datetime-local"
                  value={formData.valid_from}
                  onChange={(e) =>
                    setFormData({ ...formData, valid_from: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Valid Until
                </label>
                <input
                  type="datetime-local"
                  value={formData.valid_until}
                  onChange={(e) =>
                    setFormData({ ...formData, valid_until: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Leave empty for no expiry
                </p>
              </div>
            </div>

            {/* Active Status */}
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
                Active (coupon can be used)
              </label>
            </div>

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
                  : coupon
                    ? "Update Coupon"
                    : "Create Coupon"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
