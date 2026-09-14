import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Admin queue for company-submitted internship requests.
 *
 * Wired to real API:
 *   GET  /api/v1/admin/internship-requests
 *   POST /api/v1/admin/internship-requests/{id}/approve
 *   POST /api/v1/admin/internship-requests/{id}/reject
 */
import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  Search,
  Check,
  X,
  FileText,
  Clock3,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";
import {
  listInternshipRequests,
  approveInternshipRequest,
  rejectInternshipRequest,
  deleteInternshipRequest,
  listInstructorOptions,
  type AdminInternshipRequestItem,
  type AdminInstructorOption,
} from "@/api/admin";

type StatusFilter = "all" | "pending" | "approved" | "rejected";

const FILTERS: { key: StatusFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "pending", label: "Pending" },
  { key: "approved", label: "Approved" },
  { key: "rejected", label: "Rejected" },
];

export const AdminInternshipRequests: React.FC = () => {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<StatusFilter>("pending");
  const [search, setSearch] = useState("");
  const [approving, setApproving] = useState<AdminInternshipRequestItem | null>(
    null,
  );
  const [rejecting, setRejecting] = useState<AdminInternshipRequestItem | null>(
    null,
  );
  const [deleting, setDeleting] = useState<AdminInternshipRequestItem | null>(
    null,
  );
  const [openRow, setOpenRow] = useState<AdminInternshipRequestItem | null>(
    null,
  );

  const {
    data: rows = [],
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["admin-internship-requests"],
    queryFn: () => listInternshipRequests(),
  });

  const approveMut = useMutation({
    mutationFn: (vars: { id: number; spoc_user_id: number; price: number }) =>
      approveInternshipRequest(vars.id, {
        spoc_user_id: vars.spoc_user_id,
        price: vars.price,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-internship-requests"] });
      toast.success("Approved & published — company notified");
      setApproving(null);
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail || "Approval failed"),
  });

  const rejectMut = useMutation({
    mutationFn: (vars: { id: number; reason: string }) =>
      rejectInternshipRequest(vars.id, vars.reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-internship-requests"] });
      toast.success("Returned to company with reason");
      setRejecting(null);
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail || "Reject failed"),
  });

  const deleteMut = useMutation({
    mutationFn: (vars: { id: number }) => deleteInternshipRequest(vars.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-internship-requests"] });
      toast.success("Request deleted");
      setDeleting(null);
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail || "Delete failed"),
  });

  const visible = rows
    .filter((r) => filter === "all" || r.status === filter)
    .filter((r) =>
      !search.trim()
        ? true
        : `${r.company_name} ${r.title} ${r.requester_name}`
            .toLowerCase()
            .includes(search.toLowerCase()),
    );

  const counts = {
    pending: rows.filter((r) => r.status === "pending").length,
    approved: rows.filter((r) => r.status === "approved").length,
    rejected: rows.filter((r) => r.status === "rejected").length,
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              Internship requests
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Companies request new internships here. You assign a SPOC + price
              and publish them, or send them back with a reason.
            </p>
          </div>
          <ExportImportPanel section="internship_requests" />
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-internship-requests"
    >
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex gap-1 bg-slate-100 rounded-md p-1">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-3 py-1 rounded text-sm font-medium ${
                filter === f.key
                  ? "bg-white shadow text-indigo-700"
                  : "text-slate-600"
              }`}
            >
              {f.label}
              {f.key !== "all" && (
                <span className="ml-1.5 text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded-full">
                  {counts[f.key as Exclude<StatusFilter, "all">]}
                </span>
              )}
            </button>
          ))}
        </div>
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="w-4 h-4 absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by company, title, or requester…"
            className="w-full rounded-md border border-slate-300 pl-8 pr-3 py-2 text-sm"
          />
        </div>
      </div>
      {isLoading ? (
        <div
          className="text-center py-16 text-slate-500 text-sm bg-white rounded-xl border border-slate-200"
          data-glass="content"
        >
          Loading requests…
        </div>
      ) : isError ? (
        <div
          className="text-center py-16 text-rose-600 text-sm bg-white rounded-xl border border-rose-200"
          data-glass="content"
        >
          Failed to load requests.
          <button onClick={() => refetch()} className="ml-2 underline">
            Retry
          </button>
        </div>
      ) : visible.length === 0 ? (
        <div
          className="text-center py-16 text-slate-500 text-sm bg-white rounded-xl border border-dashed border-slate-300"
          data-glass="content"
        >
          No requests match the current filter.
        </div>
      ) : (
        <div
          className="bg-white rounded-xl border border-slate-200 overflow-hidden"
          data-glass="work"
        >
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-4 py-3">Company</th>
                <th className="text-left px-4 py-3">Title</th>
                <th className="text-left px-4 py-3">Dates</th>
                <th className="text-left px-4 py-3">Interns</th>
                <th className="text-left px-4 py-3">Submitted</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-right px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {visible.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">
                      {r.company_name}
                    </div>
                    <div className="text-xs text-slate-500">
                      {r.requester_name}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-700 max-w-xs">
                    <button
                      onClick={() => setOpenRow(r)}
                      className="text-left hover:text-indigo-700 font-medium"
                    >
                      {r.title}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-600 whitespace-nowrap">
                    {r.start_date}
                    <br />→ {r.end_date}
                  </td>
                  <td className="px-4 py-3 text-slate-700">{r.intern_count}</td>
                  <td className="px-4 py-3 text-xs text-slate-500 whitespace-nowrap">
                    {new Date(r.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() => setOpenRow(r)}
                        className="px-2 py-1 rounded text-xs bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-semibold flex items-center gap-1"
                      >
                        <FileText className="w-3 h-3" /> View
                      </button>
                      {r.status === "pending" && (
                        <>
                          <button
                            onClick={() => setApproving(r)}
                            className="px-2 py-1 rounded text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-semibold flex items-center gap-1"
                          >
                            <Check className="w-3 h-3" /> Approve
                          </button>
                          <button
                            onClick={() => setRejecting(r)}
                            className="px-2 py-1 rounded text-xs bg-rose-100 hover:bg-rose-200 text-rose-700 font-semibold flex items-center gap-1"
                          >
                            <X className="w-3 h-3" /> Reject
                          </button>
                        </>
                      )}
                      {r.status !== "approved" && (
                        <button
                          onClick={() => setDeleting(r)}
                          className="px-2 py-1 rounded text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold flex items-center gap-1"
                          title="Delete this request"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {openRow && (
        <DetailDrawer row={openRow} onClose={() => setOpenRow(null)} />
      )}
      {approving && (
        <ApproveModal
          row={approving}
          submitting={approveMut.isPending}
          onCancel={() => setApproving(null)}
          onConfirm={(spoc_user_id, price) =>
            approveMut.mutate({ id: approving.id, spoc_user_id, price })
          }
        />
      )}
      {rejecting && (
        <RejectModal
          row={rejecting}
          submitting={rejectMut.isPending}
          onCancel={() => setRejecting(null)}
          onConfirm={(reason) => rejectMut.mutate({ id: rejecting.id, reason })}
        />
      )}
      {deleting && (
        <DeleteModal
          row={deleting}
          submitting={deleteMut.isPending}
          onCancel={() => setDeleting(null)}
          onConfirm={() => deleteMut.mutate({ id: deleting.id })}
        />
      )}
    </PageLayout>
  );
};

function StatusBadge({ status }: { status: string }) {
  const m: Record<string, { cls: string; icon: any; label: string }> = {
    pending: {
      cls: "bg-amber-100 text-amber-700",
      icon: Clock3,
      label: "Pending",
    },
    approved: {
      cls: "bg-emerald-100 text-emerald-700",
      icon: CheckCircle2,
      label: "Approved",
    },
    rejected: {
      cls: "bg-rose-100 text-rose-700",
      icon: AlertCircle,
      label: "Rejected",
    },
  };
  const x = m[status] || m.pending;
  const I = x.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded ${x.cls}`}
    >
      <I className="w-3 h-3" /> {x.label}
    </span>
  );
}

function DetailDrawer({
  row,
  onClose,
}: {
  row: AdminInternshipRequestItem;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-modal flex justify-end" onClick={onClose}>
      <div className="bg-black/30 absolute inset-0" />
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative bg-white w-full max-w-xl h-full overflow-y-auto shadow-2xl"
      >
        <div className="border-b border-slate-200 p-5 flex items-start justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-900">{row.title}</h3>
            <p className="text-xs text-slate-500 mt-1">
              {row.company_name} · requested by {row.requester_name}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-5 space-y-4 text-sm">
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-50 rounded p-3">
              <div className="text-xs text-slate-500">Start</div>
              <div className="font-semibold">{row.start_date}</div>
            </div>
            <div className="bg-slate-50 rounded p-3">
              <div className="text-xs text-slate-500">End</div>
              <div className="font-semibold">{row.end_date}</div>
            </div>
            <div className="bg-slate-50 rounded p-3">
              <div className="text-xs text-slate-500">Intern target</div>
              <div className="font-semibold">{row.intern_count}</div>
            </div>
            <div className="bg-slate-50 rounded p-3">
              <div className="text-xs text-slate-500">Status</div>
              <div className="mt-1">
                <StatusBadge status={row.status} />
              </div>
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Brief</div>
            <p className="text-slate-700 whitespace-pre-wrap">
              {row.description || (
                <span className="italic text-slate-400">No description.</span>
              )}
            </p>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Submitted</div>
            <p className="text-slate-700 text-xs">
              {new Date(row.created_at).toLocaleString()}
            </p>
          </div>
          {row.approved_internship_id && (
            <div className="bg-emerald-50 border border-emerald-200 rounded p-3">
              <div className="text-xs font-semibold text-emerald-900 mb-1">
                Published as live internship #{row.approved_internship_id}
              </div>
              {row.reviewer_name && (
                <p className="text-xs text-emerald-800">
                  Reviewed by {row.reviewer_name}
                </p>
              )}
              {row.reviewed_at && (
                <p className="text-[10px] text-emerald-700 mt-1">
                  Reviewed {new Date(row.reviewed_at).toLocaleString()}
                </p>
              )}
            </div>
          )}
          {row.status === "rejected" && row.rejection_reason && (
            <div className="bg-rose-50 border border-rose-200 rounded p-3">
              <div className="text-xs font-semibold text-rose-900 mb-1">
                Returned with reason
              </div>
              <p className="text-xs text-rose-800 italic">
                {row.rejection_reason}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ApproveModal({
  row,
  submitting,
  onCancel,
  onConfirm,
}: {
  row: AdminInternshipRequestItem;
  submitting: boolean;
  onCancel: () => void;
  onConfirm: (spoc_user_id: number, price: number) => void;
}) {
  const [spocId, setSpocId] = useState<number | "">("");
  const [price, setPrice] = useState(15000);

  const { data: instructors = [], isLoading } = useQuery<
    AdminInstructorOption[]
  >({
    queryKey: ["admin-instructor-options"],
    queryFn: listInstructorOptions,
  });

  const valid = typeof spocId === "number" && price > 0;

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center"
      onClick={onCancel}
    >
      <div className="bg-black/40 absolute inset-0" />
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative bg-white rounded-xl shadow-2xl p-6 w-[440px] max-w-[calc(100vw-2rem)]"
        data-glass="work"
      >
        <h3 className="font-bold text-slate-900 mb-1">Approve &amp; publish</h3>
        <p className="text-xs text-slate-500 mb-4">
          {row.company_name} · {row.title}
        </p>
        <div className="space-y-3 mb-4">
          <div>
            <label className="block text-xs text-slate-500 mb-1">SPOC</label>
            <select
              value={spocId}
              onChange={(e) =>
                setSpocId(e.target.value === "" ? "" : Number(e.target.value))
              }
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white"
              disabled={isLoading}
            >
              <option value="">
                {isLoading ? "Loading instructors…" : "— Select a SPOC —"}
              </option>
              {instructors.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · {s.email}
                </option>
              ))}
            </select>
            <p className="text-[10px] text-slate-400 mt-1">
              Pulled from /admin/instructors/list (instructors + admins +
              SPOCs).
            </p>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">
              Voucher price (₹)
            </label>
            <input
              type="number"
              value={price}
              onChange={(e) => setPrice(Number(e.target.value))}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div className="flex gap-2">
          <button
            disabled={!valid || submitting}
            onClick={() => valid && onConfirm(spocId as number, price)}
            className="flex-1 px-3 py-2 rounded-md bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-semibold"
          >
            {submitting ? "Publishing…" : "Approve & publish"}
          </button>
          <button
            onClick={onCancel}
            className="px-3 py-2 rounded-md text-slate-600 text-sm"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

function RejectModal({
  row,
  submitting,
  onCancel,
  onConfirm,
}: {
  row: AdminInternshipRequestItem;
  submitting: boolean;
  onCancel: () => void;
  onConfirm: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  const valid = reason.trim().length >= 10;
  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center"
      onClick={onCancel}
    >
      <div className="bg-black/40 absolute inset-0" />
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative bg-white rounded-xl shadow-2xl p-6 w-[480px] max-w-[calc(100vw-2rem)]"
        data-glass="work"
      >
        <h3 className="font-bold text-slate-900 mb-1">Return to company</h3>
        <p className="text-xs text-slate-500 mb-4">
          {row.company_name} · {row.title}
        </p>
        <label className="block text-xs text-slate-500 mb-1">
          Reason — shown to the company in their dashboard
        </label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="What needs to change? (min 10 chars)"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm min-h-[100px]"
        />
        <div className="flex gap-2 mt-4">
          <button
            disabled={!valid || submitting}
            onClick={() => onConfirm(reason)}
            className="flex-1 px-3 py-2 rounded-md bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white text-sm font-semibold"
          >
            {submitting ? "Sending…" : "Send back with reason"}
          </button>
          <button
            onClick={onCancel}
            className="px-3 py-2 rounded-md text-slate-600 text-sm"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

function DeleteModal({
  row,
  submitting,
  onCancel,
  onConfirm,
}: {
  row: AdminInternshipRequestItem;
  submitting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center"
      onClick={onCancel}
    >
      <div className="bg-black/40 absolute inset-0" />
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative bg-white rounded-xl shadow-2xl p-6 w-[420px] max-w-[calc(100vw-2rem)]"
        data-glass="content"
      >
        <h3 className="font-bold text-slate-900 mb-1">
          Delete internship request
        </h3>
        <p className="text-xs text-slate-500 mb-4">
          {row.company_name} · {row.title}
        </p>
        <p className="text-sm text-slate-700 mb-4">
          Are you sure you want to delete this request? This action cannot be
          undone.
          {row.status === "approved" &&
            " Note: This request has already been approved."}
        </p>
        <div className="flex gap-2">
          <button
            disabled={submitting}
            onClick={onConfirm}
            className="flex-1 px-3 py-2 rounded-md bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white text-sm font-semibold"
          >
            {submitting ? "Deleting…" : "Delete"}
          </button>
          <button
            onClick={onCancel}
            className="px-3 py-2 rounded-md text-slate-600 text-sm"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
