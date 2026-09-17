import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback } from "react";
import React, { useState, useEffect } from "react";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";
import { api } from "@/api/axios";
import { promptDialog } from "@/components/ui/confirm";
import toast from "react-hot-toast";
import { VideoPlayer } from "@/components/video/video-player";
import {
  Search,
  IndianRupee,
  CheckCircle,
  Clock,
  XCircle,
  CreditCard,
  Calendar,
  TrendingUp,
  Briefcase,
  Play,
  X,
} from "lucide-react";

interface Order {
  id: number;
  order_key: string;
  user_name: string;
  user_email: string;
  course_title: string;
  course_id?: number;
  course_intro_video?: string;
  // Playable preview for the Course column. Falls back to a lesson video when
  // the course has no intro video set, so the control is never silently absent.
  course_preview_video?: string | null;
  course_preview_source?: "intro" | "lesson" | null;
  course_thumbnail?: string;
  amount: number;
  // Money breakdown. Internship vouchers only return `amount`, so everything
  // below is optional and the UI falls back to the single figure.
  subtotal_amount?: number;
  discount_amount?: number;
  total_amount?: number;
  currency?: string;
  coupon_code?: string | null;
  transaction_id?: string | null;
  gateway_payment_id?: string | null;
  gateway_order_id?: string | null;
  status: string;
  payment_method: string;
  created_at: string;
  updated_at: string;
  type?: "course" | "internship";
}

export const AdminOrders: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [activeTab, setActiveTab] = useState<"all" | "courses" | "internships">(
    "all",
  );
  const [isVideoModalOpen, setIsVideoModalOpen] = useState(false);
  const [previewVideoUrl, setPreviewVideoUrl] = useState("");
  const [previewVideoTitle, setPreviewVideoTitle] = useState("");
  // Revenue figures come from /admin/stats — the same backend source the
  // Analytics page uses — instead of summing the visible list, which changes
  // with filters/pagination and drifts from analytics when payments exist
  // without matching order rows.
  const [revenueStats, setRevenueStats] = useState<{
    total_revenue: number;
    course_revenue: number;
    internship_revenue: number;
  } | null>(null);

  const fetchOrders = useCallback(async () => {
    try {
      setLoading(true);
      const statusParam =
        filterStatus !== "all"
          ? `?status=${filterStatus}&limit=100`
          : "?limit=100";

      // Fetch course orders, internship vouchers, and the authoritative
      // revenue totals in one round-trip group
      const [ordersRes, vouchersRes, statsRes] = await Promise.all([
        api.get(`/admin/orders${statusParam}`),
        api.get(`/admin/internship-vouchers${statusParam}`),
        api.get("/admin/stats").catch(() => null),
      ]);

      const ordersData = ordersRes.data;
      const vouchersData = vouchersRes.data;
      const rs = statsRes?.data?.revenue_stats;
      if (rs) {
        setRevenueStats({
          total_revenue: Number(rs.total_revenue ?? 0),
          course_revenue: Number(rs.course_revenue ?? 0),
          internship_revenue: Number(rs.internship_revenue ?? 0),
        });
      }

      // Mark course orders with type
      const courseOrders = (Array.isArray(ordersData) ? ordersData : []).map(
        (o: Order) => ({ ...o, type: "course" as const }),
      );
      // Mark internship vouchers with type
      const internshipOrders = (
        Array.isArray(vouchersData) ? vouchersData : []
      ).map((o: Order) => ({ ...o, type: "internship" as const }));

      setOrders([...courseOrders, ...internshipOrders]);
    } catch (error) {
      console.error("Error fetching orders:", error);
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);
  useEffect(() => {
    fetchOrders();
  }, [fetchOrders, filterStatus]);

  const getStatusBadge = (status: string) => {
    const badges = {
      completed: { color: "green", text: "Completed", icon: CheckCircle },
      issued: { color: "green", text: "Paid", icon: CheckCircle },
      pending: { color: "yellow", text: "Pending", icon: Clock },
      failed: { color: "red", text: "Failed", icon: XCircle },
      refunded: { color: "gray", text: "Refunded", icon: XCircle },
      redeemed: { color: "blue", text: "Redeemed", icon: CheckCircle },
    };
    const badge = badges[status as keyof typeof badges] || badges.pending;
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

  const filteredOrders = orders.filter((order) => {
    const matchesSearch =
      order.user_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      order.user_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      order.course_title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      order.order_key.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesTab =
      activeTab === "all" ||
      (activeTab === "courses" && order.type === "course") ||
      (activeTab === "internships" && order.type === "internship");

    return matchesSearch && matchesTab;
  });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const courseOrders = orders.filter((o) => o.type === "course");
  const internshipOrders = orders.filter((o) => o.type === "internship");

  const stats = {
    total: orders.length,
    courseOrders: courseOrders.length,
    internshipOrders: internshipOrders.length,
    completed: orders.filter(
      (o) => o.status === "completed" || o.status === "issued",
    ).length,
    pending: orders.filter((o) => o.status === "pending").length,
    // Counts describe the visible list; revenue comes from the backend's
    // authoritative totals so it matches the Analytics page exactly.
    totalRevenue:
      revenueStats?.total_revenue ??
      orders.reduce((sum, o) => sum + o.amount, 0),
    courseRevenue:
      revenueStats?.course_revenue ??
      courseOrders.reduce((sum, o) => sum + o.amount, 0),
    internshipRevenue:
      revenueStats?.internship_revenue ??
      internshipOrders.reduce((sum, o) => sum + o.amount, 0),
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Orders</h1>
            <p className="text-gray-600 mt-1">
              Manage all course orders and payments
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <ExportImportPanel section="orders" />
            <div className="text-sm text-gray-600">
              <span className="font-semibold">{filteredOrders.length}</span>{" "}
              orders
            </div>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-orders"
    >
      <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Course Orders</p>
              <p className="text-2xl font-bold text-blue-600 mt-1">
                {stats.courseOrders}
              </p>
            </div>
            <CreditCard className="w-8 h-8 text-blue-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Internships</p>
              <p className="text-2xl font-bold text-orange-600 mt-1">
                {stats.internshipOrders}
              </p>
            </div>
            <Briefcase className="w-8 h-8 text-orange-600" />
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
              <p className="text-sm text-gray-600">Pending</p>
              <p className="text-2xl font-bold text-yellow-600 mt-1">
                {stats.pending}
              </p>
            </div>
            <Clock className="w-8 h-8 text-yellow-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Revenue</p>
              <p className="text-2xl font-bold text-purple-600 mt-1">
                ₹{stats.totalRevenue.toLocaleString()}
              </p>
            </div>
            <IndianRupee className="w-8 h-8 text-purple-600" />
          </div>
        </div>
        <div
          className="bg-white rounded-lg border border-gray-200 p-4"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Course + Internship</p>
              <p className="text-xs text-gray-500 mt-1">
                ₹{stats.courseRevenue.toLocaleString()} + ₹
                {stats.internshipRevenue.toLocaleString()}
              </p>
            </div>
            <TrendingUp className="w-8 h-8 text-gray-600" />
          </div>
        </div>
      </div>
      <div
        className="bg-white rounded-lg border border-gray-200 p-2"
        data-glass="content"
      >
        <div className="flex space-x-2">
          <button
            onClick={() => setActiveTab("all")}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === "all"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            All ({stats.total})
          </button>
          <button
            onClick={() => setActiveTab("courses")}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === "courses"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Courses ({stats.courseOrders})
          </button>
          <button
            onClick={() => setActiveTab("internships")}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === "internships"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Internships ({stats.internshipOrders})
          </button>
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
                placeholder="Search orders..."
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
              <option value="completed">Completed</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
              <option value="refunded">Refunded</option>
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Order ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Customer
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Course
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Amount Paid
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Payment / Transaction
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
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
                    Loading orders...
                  </td>
                </tr>
              ) : filteredOrders.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    No orders found
                  </td>
                </tr>
              ) : (
                filteredOrders.map((order) => {
                  // Prefer the course intro video; fall back to the lesson video
                  // the API resolved for courses that never had one set.
                  const previewUrl =
                    order.course_preview_video ||
                    order.course_intro_video ||
                    "";
                  const previewFromLesson =
                    order.course_preview_source === "lesson";
                  return (
                    <tr key={order.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        {order.type === "internship" ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                            <Briefcase className="w-3 h-3 mr-1" />
                            Internship
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            <CreditCard className="w-3 h-3 mr-1" />
                            Course
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {order.order_key}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {order.user_name}
                          </div>
                          <div className="text-sm text-gray-500">
                            {order.user_email}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-start space-x-3">
                          {order.course_thumbnail && (
                            <img
                              src={order.course_thumbnail}
                              alt={order.course_title}
                              className="w-12 h-12 object-cover rounded-lg flex-shrink-0"
                              onError={(e) => {
                                (
                                  e.currentTarget as HTMLImageElement
                                ).style.display = "none";
                              }}
                            />
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium text-gray-900 line-clamp-2">
                              {order.course_title}
                            </div>
                            {order.type === "course" &&
                              (previewUrl ? (
                                <button
                                  onClick={() => {
                                    setPreviewVideoUrl(previewUrl);
                                    setPreviewVideoTitle(
                                      `Preview: ${order.course_title}`,
                                    );
                                    setIsVideoModalOpen(true);
                                  }}
                                  title={
                                    previewFromLesson
                                      ? "No intro video on this course — playing its first lesson video"
                                      : "Play the course intro video"
                                  }
                                  className="mt-1 inline-flex items-center text-xs text-blue-600 hover:text-blue-800"
                                >
                                  <Play className="w-3 h-3 mr-1" />
                                  Preview Video
                                  {previewFromLesson && (
                                    <span className="ml-1 text-[10px] text-gray-400">
                                      (lesson)
                                    </span>
                                  )}
                                </button>
                              ) : (
                                <span className="mt-1 inline-flex items-center text-xs text-gray-400">
                                  <Play className="w-3 h-3 mr-1" />
                                  No preview available
                                </span>
                              ))}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center text-sm font-semibold text-gray-900 tabular-nums">
                          <IndianRupee className="w-4 h-4 mr-1 text-gray-400" />
                          {order.amount.toLocaleString("en-IN", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </div>
                        {/* Only show the breakdown when a discount was actually
                          applied — otherwise it is noise on every row. */}
                        {(order.discount_amount ?? 0) > 0 && (
                          <div className="mt-1 space-y-0.5 text-xs tabular-nums">
                            <div className="text-gray-500">
                              <span className="line-through">
                                ₹
                                {(order.subtotal_amount ?? 0).toLocaleString(
                                  "en-IN",
                                  {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                  },
                                )}
                              </span>
                              <span className="ml-1.5 text-green-700">
                                −₹
                                {(order.discount_amount ?? 0).toLocaleString(
                                  "en-IN",
                                  {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                  },
                                )}
                              </span>
                            </div>
                            {order.coupon_code && (
                              <span className="inline-flex items-center rounded bg-orange-50 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-orange-700 ring-1 ring-orange-200">
                                {order.coupon_code}
                              </span>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center text-sm text-gray-500">
                          <CreditCard className="w-4 h-4 mr-2 flex-shrink-0" />
                          {order.payment_method || "N/A"}
                        </div>
                        {(order.gateway_payment_id || order.transaction_id) && (
                          <div className="mt-1 font-mono text-[11px] text-gray-400 break-all">
                            {order.gateway_payment_id || order.transaction_id}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center text-sm text-gray-500">
                          <Calendar className="w-4 h-4 mr-2" />
                          {formatDate(order.created_at)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(order.status)}
                        {order.type === "course" &&
                          ["completed", "paid", "success", "captured"].includes(
                            String(order.status),
                          ) && (
                            <button
                              type="button"
                              data-testid="refund-btn"
                              className="block mt-1 text-xs text-red-600 hover:underline"
                              onClick={async () => {
                                const reason = await promptDialog(
                                  "Refund this order in full? Access to the course is revoked and Razorpay returns the money.",
                                  "",
                                  {
                                    placeholder: "Reason (kept on the record)",
                                    required: true,
                                    confirmLabel: "Refund",
                                    danger: true,
                                  },
                                );
                                if (reason === null) return;
                                try {
                                  await api.post(
                                    `/admin/orders/${order.id}/refund`,
                                    { reason },
                                  );
                                  toast.success(
                                    "Refund requested — the gateway confirms by webhook",
                                  );
                                  fetchOrders();
                                } catch (e: any) {
                                  toast.error(
                                    e?.response?.data?.detail ||
                                      "Refund failed",
                                  );
                                }
                              }}
                            >
                              Refund
                            </button>
                          )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
      {isVideoModalOpen && previewVideoUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4"
          onClick={() => {
            setIsVideoModalOpen(false);
            setPreviewVideoUrl("");
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setIsVideoModalOpen(false);
              setPreviewVideoUrl("");
            }
          }}
        >
          <button
            className="absolute top-4 right-4 text-white hover:bg-white/20 z-50 rounded-full bg-black/50 p-2"
            onClick={(e) => {
              e.stopPropagation();
              setIsVideoModalOpen(false);
              setPreviewVideoUrl("");
            }}
            aria-label="Close preview"
          >
            <X className="w-6 h-6" />
          </button>
          <div
            className="w-full max-w-4xl aspect-video bg-black rounded-xl overflow-hidden shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            <VideoPlayer
              src={previewVideoUrl}
              title={previewVideoTitle}
              onEnded={() => {}}
            />
          </div>
        </div>
      )}
    </PageLayout>
  );
};
