import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * SuperAdmin — Students monitoring.
 * Per-student performance (pass rate) + work progress (completion, certs,
 * streak, last-active). Each row has an "Impersonate" action.
 */
import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Download, User } from "lucide-react";
import { superadminApi, type SuperadminStudentRow } from "@/api/superadmin";
import toast from "react-hot-toast";
import { useSuperadminImpersonate } from "./use-impersonate";
import { api } from "@/api/axios";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

const fmtPct = (n: number) => `${Number(n || 0).toFixed(1)}%`;
const fmtDate = (s: string | null) =>
  s
    ? new Date(s).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "—";

export const SuperAdminStudents: React.FC = () => {
  const [search, setSearch] = useState("");
  // One request after typing stops, not one per keystroke.
  const debouncedSearch = useDebouncedValue(search, 300);
  const [page, setPage] = useState(0);
  const limit = 50;

  const { data, isLoading, isError, error, isFetching } = useQuery({
    queryKey: ["superadmin", "students", debouncedSearch, page],
    queryFn: () =>
      superadminApi.listStudents({
        search: debouncedSearch.trim() || undefined,
        limit,
        offset: page * limit,
      }),
    placeholderData: (prev) => prev,
  });
  const { impersonate, busyId } = useSuperadminImpersonate();

  const exportCsv = async () => {
    try {
      const res = await api.get("/superadmin/students/export", {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "superadmin-students.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Export failed. Please try again.");
    }
  };

  const items: SuperadminStudentRow[] = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Students</h1>
            <p className="text-sm text-neutral-500">
              {total.toLocaleString()} student{total === 1 ? "" : "s"} ·
              progress &amp; performance
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
      className="rd-screen rd-screen-superadmin-students"
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
                <th className="px-4 py-3">Student</th>
                <th className="px-4 py-3">Enrollments</th>
                <th className="px-4 py-3">Completion</th>
                <th className="px-4 py-3">Pass rate</th>
                <th className="px-4 py-3">Certificates</th>
                <th className="px-4 py-3">Streak (30d)</th>
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
                    No students found.
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
                      {s.enrollments}
                    </td>
                    <td className="px-4 py-3 text-neutral-700">
                      {fmtPct(s.completion_pct)}
                    </td>
                    <td className="px-4 py-3 text-neutral-700">
                      {fmtPct(s.pass_rate)}
                    </td>
                    <td className="px-4 py-3 text-neutral-700">
                      {s.certificates}
                    </td>
                    <td className="px-4 py-3 text-neutral-700">
                      {s.streak_days} day{s.streak_days === 1 ? "" : "s"}
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
                            role: "student",
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
      <Pagination
        page={page}
        pageCount={Math.max(1, Math.ceil(total / limit))}
        onChange={setPage}
        loading={isFetching}
      />
    </PageLayout>
  );
};

// Tiny inline pager to avoid coupling to a specific shared Pagination shape.
const Pagination: React.FC<{
  page: number;
  pageCount: number;
  onChange: (p: number) => void;
  loading?: boolean;
}> = ({ page, pageCount, onChange, loading }) => (
  <div className="flex items-center justify-between text-sm text-neutral-600">
    <span>
      Page {page + 1} of {pageCount}
      {loading ? " · loading…" : ""}
    </span>
    <div className="flex gap-2">
      <button
        onClick={() => onChange(Math.max(0, page - 1))}
        disabled={page === 0}
        className="rounded-md border border-neutral-300 bg-white px-3 py-1 font-medium disabled:opacity-40"
      >
        Prev
      </button>
      <button
        onClick={() => onChange(Math.min(pageCount - 1, page + 1))}
        disabled={page >= pageCount - 1}
        className="rounded-md border border-neutral-300 bg-white px-3 py-1 font-medium disabled:opacity-40"
      >
        Next
      </button>
    </div>
  </div>
);

export default SuperAdminStudents;
