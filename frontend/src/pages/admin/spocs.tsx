import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useEffect, useState } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import { useNavigate } from "react-router-dom";
import { api } from "@/api/axios";
import { adminApi } from "@/api/admin";
import toast from "react-hot-toast";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";
import { useAuthStore } from "@/store/auth";

interface Spoc {
  id: number;
  email: string;
  display_name: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

const BLANK = { email: "", password: "", display_name: "", phone: "" };

export function AdminSpocs() {
  const navigate = useNavigate();
  const startImpersonation = useAuthStore((s) => s.startSpocImpersonation);
  const [impersonatingId, setImpersonatingId] = useState<number | null>(null);
  const [spocs, setSpocs] = useState<Spoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(BLANK);
  const [submitting, setSubmitting] = useState(false);
  const [editTarget, setEditTarget] = useState<Spoc | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get("/admin/spocs");
      setSpocs(res.data);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed to load SPOCs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.email || !form.password || !form.display_name) {
      toast.error("Email, password, and name are required");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/admin/spocs", form);
      toast.success("SPOC created — they can log in now");
      setShowModal(false);
      setForm(BLANK);
      load();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed to create SPOC");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (s: Spoc) => {
    if (
      !(await confirmDialog(
        `Delete SPOC "${s.display_name}" (${s.email})? This cannot be undone.`,
      ))
    ) {
      return;
    }
    try {
      await api.delete(`/admin/spocs/${s.id}`);
      toast.success("SPOC deleted");
      setSpocs((prev) => prev.filter((x) => x.id !== s.id));
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed to delete SPOC");
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-2xl font-semibold">SPOC Management</h1>
            <p className="text-sm text-gray-500">
              Single Point of Contact accounts for college cohorts. Create one
              here before assigning them to a cohort in{" "}
              <a className="underline" href="/admin/cohorts">
                Cohorts
              </a>
              .
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              + Create SPOC
            </button>
            <ExportImportPanel section="spocs" onImportComplete={load} />
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-spocs"
    >
      <div className="bg-white rounded-lg shadow" data-glass="work">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : spocs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No SPOCs yet. Click "Create SPOC" to add one.
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-semibold">
                  ID
                </th>
                <th className="text-left px-4 py-3 text-sm font-semibold">
                  Name
                </th>
                <th className="text-left px-4 py-3 text-sm font-semibold">
                  Email
                </th>
                <th className="text-left px-4 py-3 text-sm font-semibold">
                  Status
                </th>
                <th className="text-left px-4 py-3 text-sm font-semibold">
                  Created
                </th>
                <th className="text-right px-4 py-3 text-sm font-semibold">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {spocs.map((s) => (
                <tr key={s.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm">{s.id}</td>
                  <td className="px-4 py-3 text-sm font-medium">
                    {s.display_name}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{s.email}</td>
                  <td className="px-4 py-3 text-sm">
                    <span
                      className={`px-2 py-1 text-xs rounded ${
                        s.is_active
                          ? "bg-green-100 text-green-700"
                          : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {s.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(s.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-sm text-right space-x-2">
                    <button
                      onClick={() => setEditTarget(s)}
                      className="px-3 py-1 text-xs border border-slate-300 rounded hover:bg-slate-50"
                    >
                      Edit
                    </button>
                    <button
                      onClick={async () => {
                        const confirmed = await confirmDialog(
                          `Start an impersonated session as ${s.display_name}? ` +
                            `Your admin session will be restored when you exit.`,
                        );
                        if (!confirmed) return;

                        try {
                          setImpersonatingId(s.id);
                          const res = await adminApi.impersonateSpoc(s.id);
                          await startImpersonation(
                            res.target.id,
                            res.target.display_name,
                            res.access_token,
                            res.target.email,
                          );
                          toast.success(
                            `Now viewing as ${res.target.display_name}`,
                          );
                          navigate("/spoc/dashboard");
                        } catch (err: any) {
                          const detail =
                            err?.response?.data?.detail ||
                            "Failed to start impersonation";
                          toast.error(detail);
                        } finally {
                          setImpersonatingId(null);
                        }
                      }}
                      disabled={impersonatingId === s.id}
                      className="px-3 py-1 text-xs bg-indigo-600 hover:bg-indigo-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed"
                      title="View the SPOC dashboard as if you were this SPOC"
                    >
                      {impersonatingId === s.id ? "Starting…" : "View as SPOC"}
                    </button>
                    <button
                      onClick={() => handleDelete(s)}
                      className="px-3 py-1 text-xs border border-rose-300 text-rose-700 rounded hover:bg-rose-50"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-modal">
          <div
            className="bg-white rounded-lg shadow-xl w-full max-w-md p-6"
            data-glass="work"
          >
            <h2 className="text-lg font-semibold mb-4">Create SPOC account</h2>
            <form onSubmit={submit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Full name
                </label>
                <input
                  className="w-full border rounded px-3 py-2"
                  value={form.display_name}
                  onChange={(e) =>
                    setForm({ ...form, display_name: e.target.value })
                  }
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Email</label>
                <input
                  type="email"
                  className="w-full border rounded px-3 py-2"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Temporary password{" "}
                  <span className="text-xs text-gray-500">(min 8 chars)</span>
                </label>
                <input
                  type="text"
                  className="w-full border rounded px-3 py-2 font-mono"
                  value={form.password}
                  onChange={(e) =>
                    setForm({ ...form, password: e.target.value })
                  }
                  minLength={8}
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  Share this with the SPOC. They can change it after first
                  login.
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Phone (optional)
                </label>
                <input
                  className="w-full border rounded px-3 py-2"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                />
              </div>
              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {submitting ? "Creating..." : "Create SPOC"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {editTarget && (
        <EditSpocModal
          spoc={editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={(updated) => {
            setSpocs((prev) =>
              prev.map((x) => (x.id === updated.id ? { ...x, ...updated } : x)),
            );
            setEditTarget(null);
          }}
        />
      )}
    </PageLayout>
  );
}

function EditSpocModal({
  spoc,
  onClose,
  onSaved,
}: {
  spoc: Spoc;
  onClose: () => void;
  onSaved: (s: Spoc) => void;
}) {
  const [form, setForm] = useState({
    display_name: spoc.display_name || "",
    email: spoc.email || "",
    phone: "",
    is_active: spoc.is_active,
  });
  const [saving, setSaving] = useState(false);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.display_name.trim() || !form.email.trim()) {
      toast.error("Name and email are required");
      return;
    }
    setSaving(true);
    try {
      const res = await api.put(`/admin/spocs/${spoc.id}`, form);
      toast.success("SPOC updated");
      onSaved(res.data);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed to update SPOC");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-modal px-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
        data-glass="work"
      >
        <h2 className="text-lg font-semibold mb-4">Edit SPOC</h2>
        <form onSubmit={save} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Full name</label>
            <input
              className="w-full border rounded px-3 py-2"
              value={form.display_name}
              onChange={(e) =>
                setForm({ ...form, display_name: e.target.value })
              }
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              className="w-full border rounded px-3 py-2"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Phone</label>
            <input
              className="w-full border rounded px-3 py-2"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              placeholder="(unchanged if blank)"
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) =>
                setForm({ ...form, is_active: e.target.checked })
              }
            />
            Active
          </label>
          <div className="flex gap-2 justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
