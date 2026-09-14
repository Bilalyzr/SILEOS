import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useState, useEffect } from "react";
import { Plus, Users, TrendingUp, Layers } from "lucide-react";
import { api } from "@/api/axios";
import toast from "react-hot-toast";

type Period = "daily" | "weekly" | "monthly" | "yearly";

interface AdminPlan {
  id: number;
  name: string;
  description: string | null;
  all_access: boolean;
  period: Period;
  interval: number;
  price: number;
  covered_courses: number;
  course_ids: number[];
  grace_days: number;
  razorpay_plan_id: string | null;
  is_active: boolean;
}

interface AdminMembership {
  id: number;
  user_id: number;
  user_email: string;
  plan_name: string;
  status: string;
  current_period_end: string | null;
}

export function MembershipsPage() {
  const [plans, setPlans] = useState<AdminPlan[]>([]);
  const [members, setMembers] = useState<AdminMembership[]>([]);
  const [loading, setLoading] = useState(true);
  const [membersLoading, setMembersLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingPlan, setEditingPlan] = useState<AdminPlan | null>(null);

  useEffect(() => {
    fetchPlans();
    fetchMembers();
  }, []);

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const response = await api.get("/admin/memberships/plans");
      setPlans(response.data || []);
    } catch (error: any) {
      console.error("Error fetching membership plans:", error);
      toast.error("Failed to fetch membership plans");
    } finally {
      setLoading(false);
    }
  };

  const fetchMembers = async () => {
    try {
      setMembersLoading(true);
      const response = await api.get("/admin/memberships");
      setMembers(response.data || []);
    } catch (error: any) {
      console.error("Error fetching memberships:", error);
      toast.error("Failed to fetch memberships");
    } finally {
      setMembersLoading(false);
    }
  };

  const togglePlanStatus = async (plan: AdminPlan) => {
    try {
      await api.patch(`/admin/memberships/plans/${plan.id}`, {
        is_active: !plan.is_active,
      });
      toast.success(`Plan ${!plan.is_active ? "activated" : "deactivated"}`);
      fetchPlans();
    } catch (error: any) {
      console.error("Error updating plan:", error);
      toast.error(
        error.response?.data?.detail || "Failed to update plan status",
      );
    }
  };

  // Explicit map: stripping "ly" turns "daily" into "dai".
  const PERIOD_UNIT: Record<Period, string> = {
    daily: "day",
    weekly: "week",
    monthly: "month",
    yearly: "year",
  };

  const formatPeriod = (plan: AdminPlan) => {
    const unit = PERIOD_UNIT[plan.period] ?? plan.period;
    return plan.interval === 1
      ? `every ${unit}`
      : `every ${plan.interval} ${unit}s`;
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "—";
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const statusChipClass = (status: string) => {
    switch (status) {
      case "active":
        return "bg-green-100 text-green-800";
      case "past_due":
      case "halted":
        return "bg-yellow-100 text-yellow-800";
      case "cancelled":
      case "expired":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <PageLayout
        header={
          <PageHeader>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Membership Management
              </h1>
              <p className="text-gray-600">
                Create and manage subscription tiers for your courses
              </p>
            </div>
          </PageHeader>
        }
        className="rd-screen rd-screen-admin-memberships"
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Tiers</p>
                <p className="text-2xl font-bold text-gray-900">
                  {plans.length}
                </p>
              </div>
              <Layers className="w-10 h-10 text-blue-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active Tiers</p>
                <p className="text-2xl font-bold text-green-600">
                  {plans.filter((p) => p.is_active).length}
                </p>
              </div>
              <TrendingUp className="w-10 h-10 text-green-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Members</p>
                <p className="text-2xl font-bold text-purple-600">
                  {members.length}
                </p>
              </div>
              <Users className="w-10 h-10 text-purple-500" />
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
              New Tier
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
              <p className="mt-4 text-gray-600">Loading plans...</p>
            </div>
          ) : plans.length === 0 ? (
            <div className="p-12 text-center">
              <Layers className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-xl text-gray-600 mb-2">
                No membership tiers found
              </p>
              <p className="text-gray-500">
                Create your first tier to get started
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tier
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Price
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Coverage
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Grace Days
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Razorpay Plan ID
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
                  {plans.map((plan) => (
                    <tr key={plan.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-bold text-gray-900">
                            {plan.name}
                          </div>
                          <div className="text-sm text-gray-500">
                            {plan.description}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          ₹{plan.price}
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatPeriod(plan)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 text-xs rounded-full ${
                            plan.all_access
                              ? "bg-purple-100 text-purple-800"
                              : "bg-blue-100 text-blue-800"
                          }`}
                        >
                          {plan.all_access
                            ? "All paid courses"
                            : `${plan.covered_courses} course(s)`}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {plan.grace_days}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                        {plan.razorpay_plan_id
                          ? `${plan.razorpay_plan_id.slice(0, 12)}…`
                          : "—"}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <button
                          onClick={() => togglePlanStatus(plan)}
                          className={`px-3 py-1 text-xs font-medium rounded-full ${
                            plan.is_active
                              ? "bg-green-100 text-green-800 hover:bg-green-200"
                              : "bg-gray-100 text-gray-800 hover:bg-gray-200"
                          }`}
                        >
                          {plan.is_active ? "Active" : "Inactive"}
                        </button>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => {
                            setEditingPlan(plan);
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
        <div className="mb-4">
          <h2 className="text-xl font-bold text-gray-900 mb-1">Members</h2>
          <p className="text-gray-600 text-sm">
            All users currently on a membership plan
          </p>
        </div>
        <div
          className="bg-white rounded-lg shadow overflow-hidden"
          data-glass="work"
        >
          {membersLoading ? (
            <div className="p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading members...</p>
            </div>
          ) : members.length === 0 ? (
            <div className="p-12 text-center">
              <Users className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-xl text-gray-600 mb-2">No members yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Email
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Plan
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Period End
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {members.map((m) => (
                    <tr key={m.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {m.user_email}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {m.plan_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 text-xs rounded-full ${statusChipClass(m.status)}`}
                        >
                          {m.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(m.current_period_end)}
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
        <PlanFormModal
          plan={editingPlan}
          onClose={() => {
            setShowCreateModal(false);
            setEditingPlan(null);
          }}
          onSuccess={() => {
            setShowCreateModal(false);
            setEditingPlan(null);
            fetchPlans();
          }}
        />
      )}
    </div>
  );
}

// Plan Form Modal Component
interface PlanFormModalProps {
  plan: AdminPlan | null;
  onClose: () => void;
  onSuccess: () => void;
}

function PlanFormModal({ plan, onClose, onSuccess }: PlanFormModalProps) {
  const [formData, setFormData] = useState({
    name: plan?.name || "",
    description: plan?.description || "",
    all_access: plan?.all_access ?? true,
    course_ids: plan?.course_ids || ([] as number[]),
    period: (plan?.period || "monthly") as Period,
    interval: plan?.interval || 1,
    price: plan?.price || 0,
    grace_days: plan?.grace_days ?? 7, // matches MembershipPlan.grace_days backend default
    is_active: plan?.is_active ?? true,
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
      if (plan) {
        // price/period/interval/name are immutable by design — only send
        // the fields the PATCH endpoint accepts.
        const payload = {
          description: formData.description,
          is_active: formData.is_active,
          course_ids: formData.all_access ? [] : formData.course_ids,
        };
        await api.patch(`/admin/memberships/plans/${plan.id}`, payload);
        toast.success("Tier updated successfully");
      } else {
        const payload = {
          name: formData.name,
          description: formData.description || undefined,
          all_access: formData.all_access,
          course_ids: formData.all_access ? [] : formData.course_ids,
          period: formData.period,
          interval: formData.interval,
          price: formData.price,
          grace_days: formData.grace_days,
        };
        await api.post("/admin/memberships/plans", payload);
        toast.success("Tier created successfully");
      }

      onSuccess();
    } catch (error: any) {
      console.error("Error saving tier:", error);
      toast.error(error.response?.data?.detail || "Failed to save tier");
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
            {plan ? "Edit Tier" : "New Tier"}
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
                disabled={!!plan}
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                placeholder="e.g., Pro Monthly"
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
                placeholder="Brief description of the tier"
              />
            </div>

            {/* Period and Interval */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Billing Period *
                </label>
                <select
                  required
                  disabled={!!plan}
                  value={formData.period}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      period: e.target.value as Period,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="yearly">Yearly</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Interval *
                </label>
                <input
                  type="number"
                  required
                  min="1"
                  max="12"
                  disabled={!!plan}
                  value={formData.interval}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      interval: parseInt(e.target.value) || 1,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Number of periods between charges (1–12)
                </p>
              </div>
            </div>

            {/* Price */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Price (₹) *
              </label>
              <input
                type="number"
                required
                min="0.01"
                step="0.01"
                disabled={!!plan}
                value={formData.price}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    price: parseFloat(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                placeholder="Amount"
              />
              <p className="text-xs text-gray-500 mt-1">
                Pricing is fixed once created — to change price, create a new
                tier and deactivate this one.
              </p>
            </div>

            {/* Grace Days */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Grace Days
              </label>
              <input
                type="number"
                min="0"
                max="90"
                disabled={!!plan}
                value={formData.grace_days}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    grace_days: parseInt(e.target.value) || 0,
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              />
              <p className="text-xs text-gray-500 mt-1">
                Days of continued access after a failed charge (0–90)
              </p>
            </div>

            {/* All Access */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="all_access"
                checked={formData.all_access}
                onChange={(e) =>
                  setFormData({ ...formData, all_access: e.target.checked })
                }
                className="rounded"
              />
              <label
                htmlFor="all_access"
                className="text-sm font-medium text-gray-700"
              >
                All-access (covers every course)
              </label>
            </div>

            {/* Course Selection */}
            {!formData.all_access && (
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

            {/* Active Status (edit only) */}
            {plan && (
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
                  Active (tier can be subscribed to)
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
                {loading ? "Saving..." : plan ? "Update Tier" : "Create Tier"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
