import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * SuperAdmin — Impersonation audit feed.
 * Full AdminImpersonationLog: who impersonated whom, duration, reason.
 * Surfaces open (never-ended) sessions prominently.
 */
import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Timer } from "lucide-react";
import {
  superadminApi,
  type SuperadminImpersonationAuditRow,
} from "@/api/superadmin";
import toast from "react-hot-toast";
import { api } from "@/api/axios";

const fmtDateTime = (s: string | null) =>
  s
    ? new Date(s).toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";

const fmtDuration = (seconds: number | null) => {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
};

export const SuperAdminAudit: React.FC = () => {
  const [page, setPage] = useState(0);
  const [openOnly, setOpenOnly] = useState(false);
  const limit = 100;

  const { data, isLoading, isError, error, isFetching } = useQuery({
    queryKey: ["superadmin", "audit", page, openOnly],
    queryFn: () =>
      superadminApi.auditImpersonations({
        limit,
        offset: page * limit,
        open_only: openOnly,
      }),
    placeholderData: (prev) => prev,
  });

  const exportCsv = async () => {
    try {
      const res = await api.get("/superadmin/audit/impersonations/export", {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "superadmin-impersonation-audit.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Export failed. Please try again.");
    }
  };

  const items: SuperadminImpersonationAuditRow[] = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              Impersonation audit
            </h1>
            <p className="text-sm text-neutral-500">
              {total.toLocaleString()} session{total === 1 ? "" : "s"} · who
              viewed-as whom
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="inline-flex items-center gap-2 text-sm text-neutral-700">
              <input
                type="checkbox"
                checked={openOnly}
                onChange={(e) => {
                  setOpenOnly(e.target.checked);
                  setPage(0);
                }}
                className="h-4 w-4 rounded border-neutral-300"
              />
              Open only
            </label>
            <button
              onClick={exportCsv}
              className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-sm font-medium text-neutral-700 shadow-sm hover:bg-neutral-50"
            >
              <Download className="h-4 w-4" /> Export CSV
            </button>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-superadmin-audit"
    >
      <div
        className="overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm"
        data-glass="work"
      >
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-neutral-200 text-sm">
            <thead className="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="px-4 py-3">Started</th>
                <th className="px-4 py-3">Actor</th>
                <th className="px-4 py-3">Target</th>
                <th className="px-4 py-3">Ended</th>
                <th className="px-4 py-3">Duration</th>
                <th className="px-4 py-3">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {isLoading ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-10 text-center text-neutral-400"
                  >
                    Loading…
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-10 text-center text-red-600"
                  >
                    Failed to load: {(error as Error)?.message}
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-10 text-center text-neutral-400"
                  >
                    No impersonation sessions recorded.
                  </td>
                </tr>
              ) : (
                items.map((r) => {
                  const open = r.ended_at == null;
                  return (
                    <tr
                      key={r.id}
                      className={open ? "bg-rose-50/50" : "hover:bg-neutral-50"}
                    >
                      <td className="px-4 py-3 text-neutral-700">
                        {fmtDateTime(r.started_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-neutral-900">
                          {r.actor_name}
                        </div>
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                            r.actor_role === "superadmin"
                              ? "bg-rose-100 text-rose-700"
                              : "bg-secondary-100 text-secondary-800"
                          }`}
                        >
                          {r.actor_role}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-neutral-900">
                          {r.target_name}
                        </div>
                        <span className="inline-flex rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium capitalize text-neutral-600">
                          {r.target_role}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {open ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-rose-700">
                            <Timer className="h-3.5 w-3.5" /> Open
                          </span>
                        ) : (
                          <span className="text-neutral-700">
                            {fmtDateTime(r.ended_at)}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-neutral-700">
                        {fmtDuration(r.duration_seconds)}
                      </td>
                      <td className="px-4 py-3 max-w-xs">
                        <span
                          className="block truncate text-neutral-600"
                          title={r.reason ?? ""}
                        >
                          {r.reason || (
                            <span className="text-neutral-400">—</span>
                          )}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
      <div className="flex items-center justify-between text-sm text-neutral-600">
        <span>
          Page {page + 1} of {Math.max(1, Math.ceil(total / limit))}
          {isFetching ? " · loading…" : ""}
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="rounded-md border border-neutral-300 bg-white px-3 py-1 font-medium disabled:opacity-40"
          >
            Prev
          </button>
          <button
            onClick={() =>
              setPage(Math.min(Math.ceil(total / limit) - 1, page + 1))
            }
            disabled={page >= Math.ceil(total / limit) - 1}
            className="rounded-md border border-neutral-300 bg-white px-3 py-1 font-medium disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </PageLayout>
  );
};

export default SuperAdminAudit;
