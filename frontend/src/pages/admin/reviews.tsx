import React from "react";
import { confirmDialog } from "@/components/ui/confirm";
import { toast } from "react-hot-toast";
import { api } from "@/api/axios";
import { Button } from "@/components/ui/button";
import { StarRating } from "@/components/ui/star-rating";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";

interface AdminReviewRow {
  id: number;
  rating: number;
  review_title: string;
  review_content: string;
  status: string;
  admin_notes: string;
  created_at: string;
  course: { id: number | null; title: string };
  user: { id: number | null; name: string; email: string; avatar: string };
}

export const AdminCourseReviews: React.FC = () => {
  const [rows, setRows] = React.useState<AdminReviewRow[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [statusFilter, setStatusFilter] = React.useState<
    "pending" | "approved" | "rejected" | "all"
  >("pending");
  const [busy, setBusy] = React.useState<Record<number, boolean>>({});

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.get("/admin/course-reviews", {
        params: { status: statusFilter },
      });
      setRows(resp.data?.reviews || []);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to load reviews");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  React.useEffect(() => {
    load();
  }, [load]);

  const setStatus = async (id: number, newStatus: "approved" | "rejected") => {
    setBusy((b) => ({ ...b, [id]: true }));
    try {
      await api.patch(`/admin/course-reviews/${id}`, { status: newStatus });
      toast.success(`Review ${newStatus}`);
      setRows((rs) => rs.filter((r) => r.id !== id || statusFilter === "all"));
      if (statusFilter === "all") await load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed");
    } finally {
      setBusy((b) => ({ ...b, [id]: false }));
    }
  };

  const remove = async (id: number) => {
    if (!(await confirmDialog("Delete this review permanently?"))) return;
    setBusy((b) => ({ ...b, [id]: true }));
    try {
      await api.delete(`/admin/course-reviews/${id}`);
      toast.success("Review deleted");
      setRows((rs) => rs.filter((r) => r.id !== id));
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to delete");
    } finally {
      setBusy((b) => ({ ...b, [id]: false }));
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm p-6" data-glass="work">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-semibold">Course Reviews</h2>
          <ExportImportPanel section="reviews" />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as any)}
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
        >
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="all">All</option>
        </select>
      </div>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="text-gray-500 text-sm">No reviews.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left">Course</th>
                <th className="px-3 py-2 text-left">Reviewer</th>
                <th className="px-3 py-2 text-left">Rating</th>
                <th className="px-3 py-2 text-left">Review</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t border-gray-100 align-top">
                  <td className="px-3 py-2 text-gray-800">{r.course.title}</td>
                  <td className="px-3 py-2 text-gray-700">
                    <div className="font-medium">{r.user.name}</div>
                    <div className="text-xs text-gray-500">{r.user.email}</div>
                  </td>
                  <td className="px-3 py-2">
                    <StarRating rating={r.rating} size="sm" />
                  </td>
                  <td className="px-3 py-2 max-w-md">
                    {r.review_title && (
                      <div className="font-medium">{r.review_title}</div>
                    )}
                    <div className="text-gray-600 whitespace-pre-wrap">
                      {r.review_content}
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs ${
                        r.status === "approved"
                          ? "bg-green-100 text-green-800"
                          : r.status === "rejected"
                            ? "bg-red-100 text-red-800"
                            : "bg-yellow-100 text-yellow-800"
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 space-x-2 whitespace-nowrap">
                    {r.status !== "approved" && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={!!busy[r.id]}
                        onClick={() => setStatus(r.id, "approved")}
                      >
                        Approve
                      </Button>
                    )}
                    {r.status !== "rejected" && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={!!busy[r.id]}
                        onClick={() => setStatus(r.id, "rejected")}
                      >
                        Reject
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={!!busy[r.id]}
                      onClick={() => remove(r.id)}
                    >
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default AdminCourseReviews;
