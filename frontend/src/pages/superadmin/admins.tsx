import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * SuperAdmin — Admins monitoring.
 * Per-admin work progress: logins, users managed, impersonation sessions run.
 * Admins (unlike students/instructors) are themselves a sensitive target —
 * "View as" goes through the reason-required + confirm gate in the hook.
 */
import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Download, User } from "lucide-react";
import { superadminApi, type SuperadminAdminRow } from "@/api/superadmin";
import toast from "react-hot-toast";
import { useSuperadminImpersonate } from "./use-impersonate";
import { api } from "@/api/axios";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

const fmtDate = (s: string | null) =>
  s
    ? new Date(s).toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";

export const SuperAdminAdmins: React.FC = () => {
  const [search, setSearch] = useState("");
  // One request after typing stops, not one per keystroke.
  const debouncedSearch = useDebouncedValue(search, 300);
  const [page, setPage] = useState(0);
  const limit = 50;

  const { data, isLoading, isError, error, isFetching } = useQuery({
    queryKey: ["superadmin", "admins", debouncedSearch, page],
    queryFn: () =>
      superadminApi.listAdmins({
        search: debouncedSearch.trim() || undefined,
        limit,
        offset: page * limit,
      }),
    placeholderData: (prev) => prev,
  });
  const { impersonate, busyId } = useSuperadminImpersonate();

  const exportCsv = async () => {
    try {
      const res = await api.get("/superadmin/admins/export", {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "superadmin-admins.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Export failed. Please try again.");
    }
  };

  const items: SuperadminAdminRow[] = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Admins</h1>
            <p className="text-sm text-neutral-500">
              {total.toLocaleString()} admin{total === 1 ? "" : "s"} · activity
              &amp; oversight
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
      className="rd-screen rd-screen-superadmin-admins"
    >
      <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
        <strong>Sensitive action:</strong> viewing-as an admin requires a reason
        and confirmation. Every session is logged with{" "}
        <code>actor_role=superadmin</code>.
      </div>
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
                <th className="px-4 py-3">Admin</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Last login</th>
                <th className="px-4 py-3">Impersonations run</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {isLoading ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-10 text-center text-neutral-400"
                  >
                    Loading…
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-10 text-center text-red-600"
                  >
                    Failed to load: {(error as Error)?.message}
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-10 text-center text-neutral-400"
                  >
                    No admins found.
                  </td>
                </tr>
              ) : (
                items.map((a) => (
                  <tr key={a.id} className="hover:bg-neutral-50">
                    <td className="px-4 py-3">
                      <div className="font-medium text-neutral-900">
                        {a.display_name}
                      </div>
                      <div className="text-xs text-neutral-500">{a.email}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex rounded-full bg-secondary-100 px-2 py-0.5 text-xs font-medium capitalize text-secondary-800">
                        {a.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-neutral-700">
                      {fmtDate(a.last_login)}
                    </td>
                    <td className="px-4 py-3 text-neutral-700">
                      {a.impersonations_run}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() =>
                          impersonate({
                            id: a.id,
                            display_name: a.display_name,
                            email: a.email,
                            role: "admin",
                          })
                        }
                        disabled={busyId === a.id}
                        className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 bg-white px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-100 disabled:opacity-50"
                      >
                        <User className="h-3.5 w-3.5" />
                        {busyId === a.id ? "Starting…" : "View as"}
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

export default SuperAdminAdmins;
