import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * SuperAdmin — Instructors monitoring.
 * Per-instructor productivity (rating, revenue) + work progress (courses,
 * students, pending approvals). Each row has an "Impersonate" action.
 */
import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Download, User } from "lucide-react";
import { superadminApi, type SuperadminInstructorRow } from "@/api/superadmin";
import toast from "react-hot-toast";
import { useSuperadminImpersonate } from "./use-impersonate";
import { api } from "@/api/axios";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

const fmtMoney = (n: number) =>
  `₹${Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const fmtRating = (n: number) => Number(n || 0).toFixed(2);
const fmtDate = (s: string | null) =>
  s
    ? new Date(s).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "—";

export const SuperAdminInstructors: React.FC = () => {
  const [search, setSearch] = useState("");
  // One request after typing stops, not one per keystroke.
  const debouncedSearch = useDebouncedValue(search, 300);
  const [page, setPage] = useState(0);
  const limit = 50;

  const { data, isLoading, isError, error, isFetching } = useQuery({
    queryKey: ["superadmin", "instructors", debouncedSearch, page],
    queryFn: () =>
      superadminApi.listInstructors({
        search: debouncedSearch.trim() || undefined,
        limit,
        offset: page * limit,
      }),
    placeholderData: (prev) => prev,
  });
  const { impersonate, busyId } = useSuperadminImpersonate();

  const exportCsv = async () => {
    try {
      const res = await api.get("/superadmin/instructors/export", {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "superadmin-instructors.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Export failed. Please try again.");
    }
  };

  const items: SuperadminInstructorRow[] = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Instructors</h1>
            <p className="text-sm text-neutral-500">
              {total.toLocaleString()} instructor{total === 1 ? "" : "s"} ·
              productivity &amp; progress
            </p>
          </div>
          <button
            onClick={exportCsv}
            className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-sm font-medium text-neutral-700 shadow-sm hover:bg-neutral-50"
          >
            <Download className="h-4 w-4" /> Export CSV
          </button>
        </PageHeader>
      }
      className="rd-screen rd-screen-superadmin-instructors"
    >
      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(0);
          }}
          placeholder="Search by name or email…"
          className="w-full rounded-lg border border-neutral-300 bg-white py-2 pl-9 pr-3 text-sm shadow-sm focus:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-400"
        />
      </div>
      <div
        className="overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm"
        data-glass="work"
      >
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-neutral-200 text-sm">
            <thead className="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="px-4 py-3">Instructor</th>
                <th className="px-4 py-3">Courses</th>
                <th className="px-4 py-3">Students</th>
                <th className="px-4 py-3">Avg rating</th>
                <th className="px-4 py-3">Pending</th>
                <th className="px-4 py-3">Revenue</th>
                <th className="px-4 py-3">Last active</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {isLoading ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-10 text-center text-neutral-400"
                  >
                    Loading…
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-10 text-center text-red-600"
                  >
                    Failed to load: {(error as Error)?.message}
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-10 text-center text-neutral-400"
                  >
                    No instructors found.
                  </td>
                </tr>
              ) : (
                items.map((s) => (
                  <tr key={s.id} className="hover:bg-neutral-50">
                    <td className="px-4 py-3">
                      <div className="font-medium text-neutral-900">
                        {s.display_name}
                      </div>
                      <div className="text-xs text-neutral-500">{s.email}</div>
                    </td>
                    <td className="px-4 py-3 text-neutral-700">
                      {s.courses_published}
                    </td>
                    <td className="px-4 py-3 text-neutral-700">
                      {s.students_enrolled}
                    </td>
                    <td className="px-4 py-3 text-neutral-700">
                      {fmtRating(s.avg_rating)} ★
                    </td>
                    <td className="px-4 py-3">
                      {s.pending_approvals > 0 ? (
                        <span className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                          {s.pending_approvals} pending
                        </span>
                      ) : (
                        <span className="text-neutral-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-neutral-700">
                      {fmtMoney(s.revenue_attributed)}
                    </td>
                    <td className="px-4 py-3 text-neutral-700">
                      {fmtDate(s.last_active)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() =>
                          impersonate({
                            id: s.id,
                            display_name: s.display_name,
                            email: s.email,
                            role: "instructor",
                          })
                        }
                        disabled={busyId === s.id}
                        className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 bg-white px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-100 disabled:opacity-50"
                      >
                        <User className="h-3.5 w-3.5" />
                        {busyId === s.id ? "Starting…" : "View as"}
                      </button>
                    </td>
                  </tr>
                ))
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

export default SuperAdminInstructors;
