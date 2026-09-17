import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useEffect, useMemo, useState } from "react";
import { promptDialog } from "@/components/ui/confirm";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { companyAPI, AdminCompanyRow, AdminCompanyStatus } from "@/api/company";
import { adminApi } from "@/api/admin";
import { useAuthStore } from "@/store/auth";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";

/**
 * SS3 — Admin companies console.
 *
 * Unified list across invited / pending / active / rejected, plus the
 * existing Bulk Invite tab.
 */

type Tab = "all" | AdminCompanyStatus | "bulk";

const TAB_ORDER: Tab[] = [
  "all",
  "invited",
  "pending",
  "active",
  "rejected",
  "bulk",
];
const TAB_LABEL: Record<Tab, string> = {
  all: "All",
  invited: "Invited",
  pending: "Pending",
  active: "Active",
  rejected: "Rejected",
  bulk: "Bulk invite",
};

function StatusBadge({ status }: { status: AdminCompanyStatus }) {
  const classes: Record<AdminCompanyStatus, string> = {
    invited: "bg-amber-100 text-amber-800",
    pending: "bg-blue-100 text-blue-800",
    active: "bg-emerald-100 text-emerald-800",
    rejected: "bg-rose-100 text-rose-800",
  };
  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-medium ${classes[status]}`}
    >
      {status}
    </span>
  );
}

function SourceBadge({ source }: { source: "self_serve" | "admin_invite" }) {
  return source === "admin_invite" ? (
    <span className="px-2 py-0.5 rounded text-xs bg-indigo-50 text-indigo-700 border border-indigo-200">
      Admin invite
    </span>
  ) : (
    <span className="px-2 py-0.5 rounded text-xs bg-slate-50 text-slate-700 border border-slate-200">
      Self-serve
    </span>
  );
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return "—";
  }
}

export function AdminCompaniesPage() {
  const navigate = useNavigate();
  const startCompanyImpersonation = useAuthStore(
    (s) => s.startCompanyImpersonation,
  );
  const [tab, setTab] = useState<Tab>("all");
  const [rows, setRows] = useState<AdminCompanyRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [showInvite, setShowInvite] = useState(false);
  const [viewRow, setViewRow] = useState<AdminCompanyRow | null>(null);
  const [recentlySent, setRecentlySent] = useState<Record<number, number>>({});

  // Debounce search input — 300ms.
  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(t);
  }, [search]);

  const listStatus =
    tab === "bulk" ? null : (tab as "all" | AdminCompanyStatus);

  const load = async () => {
    if (listStatus === null) return;
    setLoading(true);
    try {
      const res = await companyAPI.adminListAll({
        status: listStatus,
        search: debouncedSearch || undefined,
        limit: 200,
        skip: 0,
      });
      setRows(res.items);
      setTotal(res.total);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load companies");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listStatus, debouncedSearch]);

  const approve = async (id: number) => {
    try {
      await companyAPI.adminApprove(id);
      toast.success("Company approved");
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Approve failed");
    }
  };

  const reject = async (id: number) => {
    const reason =
      (await promptDialog("Reason for rejection (optional):", "")) || "";
    try {
      await companyAPI.adminReject(id, reason);
      toast.success("Company rejected");
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Reject failed");
    }
  };

  const resend = async (id: number) => {
    try {
      const res = await companyAPI.adminResendInvite(id);
      toast.success(`Invite re-sent to ${res.sent_to}`);
      setRecentlySent((m) => ({ ...m, [id]: Date.now() }));
      // clear the "Sent" hint after 10s
      window.setTimeout(() => {
        setRecentlySent((m) => {
          const next = { ...m };
          delete next[id];
          return next;
        });
      }, 10000);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Resend failed");
    }
  };

  const rowActions = (row: AdminCompanyRow) => {
    // "View as company" is an admin oversight action that should be available
    // for EVERY company (the backend impersonation endpoint enforces no
    // approval requirement — only that the company has a live owner). It used
    // to be gated behind status==='active', which silently hid the button for
    // pending / invited / rejected companies. Now it's always appended.
    const viewAsButton = (
      <button
        onClick={async () => {
          try {
            // Call the real impersonation API endpoint
            const response = await adminApi.impersonateCompany(row.id);

            // Store the impersonation token in the auth store
            await startCompanyImpersonation(
              row.id,
              row.name,
              response.access_token,
              response.owner_email,
            );

            toast.success(`Now viewing as ${row.name}`);

            // Navigate to the company dashboard
            navigate("/company/dashboard");
          } catch (error: any) {
            console.error("Failed to start company impersonation:", error);
            const errorMessage =
              error?.response?.data?.detail || "Failed to view as company";
            toast.error(errorMessage);
          }
        }}
        className="px-2.5 py-1 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold"
        title="Open the company dashboard as if you were this company"
      >
        View as company
      </button>
    );

    if (row.status === "pending") {
      return (
        <div className="flex gap-2 justify-end">
          <button
            onClick={() => approve(row.id)}
            className="px-2.5 py-1 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
          >
            Approve
          </button>
          <button
            onClick={() => reject(row.id)}
            className="px-2.5 py-1 rounded-md border border-rose-300 text-rose-700 text-xs"
          >
            Reject
          </button>
          {viewAsButton}
        </div>
      );
    }
    if (row.status === "rejected") {
      return (
        <div className="flex gap-2 justify-end">
          <button
            onClick={() => approve(row.id)}
            className="px-2.5 py-1 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
          >
            Re-approve
          </button>
          {viewAsButton}
        </div>
      );
    }
    if (row.status === "invited") {
      const sent = recentlySent[row.id] !== undefined;
      return (
        <div className="flex gap-2 justify-end">
          <button
            onClick={() => resend(row.id)}
            disabled={sent}
            className="px-2.5 py-1 rounded-md bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-xs"
          >
            {sent ? "Sent ✓" : "Resend invite"}
          </button>
          {viewAsButton}
        </div>
      );
    }
    // active
    return (
      <div className="flex gap-2 justify-end">
        <button
          onClick={() => setViewRow(row)}
          className="px-2.5 py-1 rounded-md border border-slate-300 text-slate-700 text-xs"
        >
          View
        </button>
        {viewAsButton}
      </div>
    );
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Companies</h1>
            <p className="text-sm text-slate-600">
              Review signups, manage invites, and track every company on the
              platform.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowInvite(true)}
              className="px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold"
            >
              + Invite company
            </button>
            <ExportImportPanel section="companies" onImportComplete={load} />
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-companies"
    >
      <div className="border-b border-slate-200 mb-4">
        <nav className="-mb-px flex gap-4 overflow-x-auto">
          {TAB_ORDER.map((t) => {
            const active = tab === t;
            return (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`whitespace-nowrap px-3 py-2 text-sm font-medium border-b-2 transition ${
                  active
                    ? "border-indigo-600 text-indigo-700"
                    : "border-transparent text-slate-600 hover:text-slate-900"
                }`}
              >
                {TAB_LABEL[t]}
              </button>
            );
          })}
        </nav>
      </div>
      {tab === "bulk" ? (
        <BulkInvitePanel
          onDone={() => {
            setTab("invited");
          }}
        />
      ) : (
        <>
          <div className="flex items-center gap-3 mb-4">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, email, or slug…"
              className="w-full max-w-md rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <div className="text-xs text-slate-500">
              {loading
                ? "Loading…"
                : `${total} result${total === 1 ? "" : "s"}`}
            </div>
          </div>

          <div
            className="bg-white rounded-xl border border-slate-200 overflow-hidden"
            data-glass="work"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-slate-600 text-xs uppercase">
                  <tr>
                    <th className="text-left px-3 py-2 font-semibold">
                      Company
                    </th>
                    <th className="text-left px-3 py-2 font-semibold">
                      Contact
                    </th>
                    <th className="text-left px-3 py-2 font-semibold">
                      Source
                    </th>
                    <th className="text-left px-3 py-2 font-semibold">
                      Status
                    </th>
                    <th className="text-left px-3 py-2 font-semibold">Setup</th>
                    <th className="text-right px-3 py-2 font-semibold">
                      Interests
                    </th>
                    <th className="text-left px-3 py-2 font-semibold">
                      Created
                    </th>
                    <th className="text-right px-3 py-2 font-semibold">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {loading && rows.length === 0 ? (
                    <tr>
                      <td
                        colSpan={8}
                        className="text-center py-10 text-slate-500"
                      >
                        Loading…
                      </td>
                    </tr>
                  ) : rows.length === 0 ? (
                    <tr>
                      <td
                        colSpan={8}
                        className="text-center py-10 text-slate-500"
                      >
                        No companies match this filter.
                      </td>
                    </tr>
                  ) : (
                    rows.map((row) => {
                      const isInvite = row.approval_source === "admin_invite";
                      const setupCell = isInvite ? (
                        row.owner.is_verified ? (
                          <span className="text-emerald-700 text-xs">
                            Completed
                          </span>
                        ) : (
                          <span className="text-amber-700 text-xs">
                            Pending setup
                          </span>
                        )
                      ) : (
                        <span className="text-slate-400 text-xs">—</span>
                      );
                      return (
                        <tr
                          key={row.id}
                          className="border-t border-slate-100 align-top hover:bg-slate-50/40"
                        >
                          <td className="px-3 py-2">
                            <div className="font-medium text-slate-900">
                              {row.name}
                            </div>
                            {row.website && (
                              <a
                                href={row.website}
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs text-indigo-600"
                              >
                                {row.website}
                              </a>
                            )}
                          </td>
                          <td className="px-3 py-2 text-slate-700">
                            <div>{row.contact_email}</div>
                            {row.contact_phone && (
                              <div className="text-xs text-slate-500">
                                {row.contact_phone}
                              </div>
                            )}
                          </td>
                          <td className="px-3 py-2">
                            <SourceBadge source={row.approval_source} />
                          </td>
                          <td className="px-3 py-2">
                            <StatusBadge status={row.status} />
                          </td>
                          <td className="px-3 py-2">{setupCell}</td>
                          <td className="px-3 py-2 text-right tabular-nums">
                            {row.interests_sent}
                          </td>
                          <td className="px-3 py-2 text-xs text-slate-600">
                            {fmtDate(row.created_at)}
                          </td>
                          <td className="px-3 py-2">{rowActions(row)}</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
      {showInvite && (
        <InviteModal
          onClose={() => setShowInvite(false)}
          onDone={() => {
            setShowInvite(false);
            // The new company lands in Invited; jump there so the admin sees it.
            setTab("invited");
            load();
          }}
        />
      )}
      {viewRow && (
        <ViewCompanyModal row={viewRow} onClose={() => setViewRow(null)} />
      )}
    </PageLayout>
  );
}

// ---------- View modal (read-only) ----------

function ViewCompanyModal({
  row,
  onClose,
}: {
  row: AdminCompanyRow;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-lg max-w-lg w-full p-6 space-y-3"
        onClick={(e) => e.stopPropagation()}
        data-glass="content"
      >
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xl font-bold text-slate-900">{row.name}</h3>
            <div className="text-xs text-slate-500">/{row.slug}</div>
          </div>
          <StatusBadge status={row.status} />
        </div>

        <dl className="text-sm grid grid-cols-3 gap-x-3 gap-y-2">
          <dt className="text-slate-500">Contact</dt>
          <dd className="col-span-2 text-slate-800">
            {row.contact_email}
            {row.contact_phone ? ` · ${row.contact_phone}` : ""}
          </dd>

          <dt className="text-slate-500">Website</dt>
          <dd className="col-span-2 text-slate-800">{row.website || "—"}</dd>

          <dt className="text-slate-500">Industry</dt>
          <dd className="col-span-2 text-slate-800">{row.industry || "—"}</dd>

          <dt className="text-slate-500">Team size</dt>
          <dd className="col-span-2 text-slate-800">{row.team_size || "—"}</dd>

          <dt className="text-slate-500">Source</dt>
          <dd className="col-span-2">
            <SourceBadge source={row.approval_source} />
          </dd>

          <dt className="text-slate-500">Interests sent</dt>
          <dd className="col-span-2 text-slate-800">{row.interests_sent}</dd>

          <dt className="text-slate-500">Created</dt>
          <dd className="col-span-2 text-slate-800">
            {fmtDate(row.created_at)}
          </dd>

          <dt className="text-slate-500">Approved</dt>
          <dd className="col-span-2 text-slate-800">
            {fmtDate(row.approved_at)}
          </dd>
        </dl>

        {row.description && (
          <div>
            <div className="text-xs uppercase text-slate-500 font-semibold mt-2 mb-1">
              About
            </div>
            <p className="text-sm text-slate-800 whitespace-pre-wrap">
              {row.description}
            </p>
          </div>
        )}

        <div className="flex justify-end pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-md bg-slate-800 hover:bg-slate-900 text-white font-semibold text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------- Bulk invite (unchanged logic, now rendered inline as a tab) ----------

interface ParsedRow {
  name: string;
  email: string;
}

interface BulkResult {
  name: string;
  email: string;
  status: "invited" | "skipped_existing_user" | "error";
  message: string;
  company_id?: number;
}

function parseBulkInput(raw: string): { rows: ParsedRow[]; bad: number } {
  const rows: ParsedRow[] = [];
  let bad = 0;
  const lines = raw.split(/\r?\n/);
  for (const ln of lines) {
    const line = ln.trim();
    if (!line) continue;
    let name = "";
    let email = "";
    const angle = line.match(/^(.+?)\s*<([^<>\s]+)>\s*$/);
    if (angle) {
      name = angle[1].trim();
      email = angle[2].trim().toLowerCase();
    } else if (line.includes(",")) {
      const idx = line.lastIndexOf(",");
      name = line.slice(0, idx).trim();
      email = line
        .slice(idx + 1)
        .trim()
        .toLowerCase();
    } else {
      bad += 1;
      continue;
    }
    if (!name || !email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      bad += 1;
      continue;
    }
    rows.push({ name, email });
  }
  return { rows, bad };
}

function BulkInvitePanel({ onDone }: { onDone: () => void }) {
  const [raw, setRaw] = useState("");
  const [sendEmail, setSendEmail] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [results, setResults] = useState<BulkResult[] | null>(null);

  const parsed = useMemo(() => parseBulkInput(raw), [raw]);

  const submit = async () => {
    if (parsed.rows.length === 0) {
      toast.error("No valid rows to submit");
      return;
    }
    setSubmitting(true);
    try {
      const res = await companyAPI.bulkInvite(parsed.rows, sendEmail);
      setResults(res.results);
      toast.success(
        `Bulk invite done — ${res.invited} invited, ${res.skipped} skipped, ${res.errors} errors`,
      );
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Bulk invite failed");
    } finally {
      setSubmitting(false);
    }
  };

  const badge = (s: BulkResult["status"]) => {
    if (s === "invited")
      return (
        <span className="px-2 py-0.5 rounded text-xs bg-emerald-100 text-emerald-700">
          Invited
        </span>
      );
    if (s === "skipped_existing_user")
      return (
        <span className="px-2 py-0.5 rounded text-xs bg-amber-100 text-amber-700">
          Skipped
        </span>
      );
    return (
      <span className="px-2 py-0.5 rounded text-xs bg-rose-100 text-rose-700">
        Error
      </span>
    );
  };

  if (results) {
    return (
      <div
        className="bg-white rounded-xl border border-slate-200 p-4 space-y-3"
        data-glass="work"
      >
        <div className="border border-slate-200 rounded-md overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-2 py-1">Name</th>
                <th className="text-left px-2 py-1">Email</th>
                <th className="text-left px-2 py-1">Status</th>
                <th className="text-left px-2 py-1">Message</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i} className="border-t border-slate-100 align-top">
                  <td className="px-2 py-1">{r.name}</td>
                  <td className="px-2 py-1 text-slate-600">{r.email}</td>
                  <td className="px-2 py-1">{badge(r.status)}</td>
                  <td className="px-2 py-1 text-slate-600">{r.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={() => {
              setResults(null);
              setRaw("");
            }}
            className="px-4 py-2 rounded-md border border-slate-300 text-slate-700 text-sm"
          >
            Invite more
          </button>
          <button
            onClick={onDone}
            className="px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm"
          >
            Done
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="bg-white rounded-xl border border-slate-200 p-4 space-y-4"
      data-glass="work"
    >
      <p className="text-sm text-slate-600">
        Paste one company per line. Accepted formats:
        <code className="block bg-slate-50 rounded p-2 text-xs mt-1 whitespace-pre-wrap">
          {`Acme Labs, hr@acme.com
Other Co <ops@other.com>`}
        </code>
      </p>

      <textarea
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        rows={8}
        placeholder={
          "Paste rows — one per line. Format:\n   Company Name, email@domain.com\n   Acme Labs, hr@acme.com\n   Other Co <ops@other.com>"
        }
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-mono"
      />

      <div className="text-xs text-slate-600">
        Parsed: <strong>{parsed.rows.length}</strong> valid
        {parsed.bad > 0 && (
          <span className="text-rose-600"> · {parsed.bad} unparseable</span>
        )}
      </div>

      {parsed.rows.length > 0 && (
        <div className="border border-slate-200 rounded-md overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-2 py-1">Name</th>
                <th className="text-left px-2 py-1">Email</th>
              </tr>
            </thead>
            <tbody>
              {parsed.rows.slice(0, 10).map((r, i) => (
                <tr key={i} className="border-t border-slate-100">
                  <td className="px-2 py-1">{r.name}</td>
                  <td className="px-2 py-1 text-slate-600">{r.email}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {parsed.rows.length > 10 && (
            <div className="text-xs text-slate-500 px-2 py-1 bg-slate-50">
              …and {parsed.rows.length - 10} more
            </div>
          )}
        </div>
      )}

      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={sendEmail}
          onChange={(e) => setSendEmail(e.target.checked)}
        />
        Send setup email to each company
      </label>

      <div className="flex justify-end gap-2 pt-2">
        <button
          onClick={submit}
          disabled={submitting || parsed.rows.length === 0}
          className="px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-semibold text-sm"
        >
          {submitting ? "Sending…" : `Invite ${parsed.rows.length}`}
        </button>
      </div>
    </div>
  );
}

// ---------- Single-invite modal (unchanged) ----------

function InviteModal({
  onClose,
  onDone,
}: {
  onClose: () => void;
  onDone: () => void;
}) {
  const [form, setForm] = useState({
    name: "",
    contact_email: "",
    contact_phone: "",
    website: "",
    industry: "",
    team_size: "",
    description: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!form.name || !form.contact_email) {
      toast.error("Name and email required");
      return;
    }
    setSubmitting(true);
    try {
      await companyAPI.adminInvite(form);
      toast.success("Company invited — setup email sent");
      onDone();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Invite failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-lg max-w-lg w-full p-6 space-y-3"
        onClick={(e) => e.stopPropagation()}
        data-glass="work"
      >
        <h3 className="text-xl font-bold text-slate-900 mb-1">
          Invite a company
        </h3>
        <p className="text-sm text-slate-600 mb-3">
          Pre-approves the company and emails them a setup link to choose a
          password.
        </p>

        {(
          [
            ["name", "Company name *"],
            ["contact_email", "Contact email *"],
            ["contact_phone", "Phone"],
            ["website", "Website"],
            ["industry", "Industry"],
            ["team_size", "Team size"],
          ] as const
        ).map(([k, label]) => (
          <div key={k}>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              {label}
            </label>
            <input
              value={(form as any)[k]}
              onChange={(e) => setForm((f) => ({ ...f, [k]: e.target.value }))}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
        ))}

        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">
            Description
          </label>
          <textarea
            value={form.description}
            onChange={(e) =>
              setForm((f) => ({ ...f, description: e.target.value }))
            }
            rows={3}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-md border border-slate-300 text-slate-700"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={submitting}
            className="px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-semibold"
          >
            {submitting ? "Sending…" : "Send invite"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default AdminCompaniesPage;
