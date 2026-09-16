import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useEffect, useState } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import { Plus, Edit, Trash2, Building2 } from "lucide-react";
import toast from "react-hot-toast";
import { collegeApi, College } from "@/api/cohort";

export const AdminColleges: React.FC = () => {
  const [rows, setRows] = useState<College[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<College | null>(null);
  const [form, setForm] = useState({
    name: "",
    slug: "",
    city: "",
    state: "",
    contact_name: "",
    contact_email: "",
  });

  const load = async () => {
    try {
      setLoading(true);
      setRows(await collegeApi.list());
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load colleges");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openNew = () => {
    setEditing(null);
    setForm({
      name: "",
      slug: "",
      city: "",
      state: "",
      contact_name: "",
      contact_email: "",
    });
    setModalOpen(true);
  };

  const openEdit = (c: College) => {
    setEditing(c);
    setForm({
      name: c.name,
      slug: c.slug,
      city: c.city,
      state: c.state,
      contact_name: c.contact_name,
      contact_email: c.contact_email,
    });
    setModalOpen(true);
  };

  const submit = async () => {
    if (!form.name.trim()) {
      toast.error("Name required");
      return;
    }
    try {
      if (editing) {
        await collegeApi.update(editing.id, form);
        toast.success("College updated");
      } else {
        await collegeApi.create(form);
        toast.success("College created");
      }
      setModalOpen(false);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Save failed");
    }
  };

  const remove = async (c: College) => {
    if (
      !(await confirmDialog(
        `Delete "${c.name}"? This also deletes its cohorts.`,
      ))
    )
      return;
    try {
      await collegeApi.remove(c.id);
      toast.success("Deleted");
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Delete failed");
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Building2 className="h-6 w-6" /> Colleges
            </h1>
            <p className="text-sm text-gray-500">
              Manage partner colleges for cohort programs
            </p>
          </div>
          <button
            onClick={openNew}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" /> New College
          </button>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-colleges"
    >
      <div
        className="bg-white rounded-lg shadow overflow-hidden"
        data-glass="work"
      >
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Name
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Slug
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Location
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Contact
              </th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-gray-400">
                  Loading…
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-gray-400">
                  No colleges yet
                </td>
              </tr>
            ) : (
              rows.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{c.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{c.slug}</td>
                  <td className="px-4 py-3 text-sm">
                    {[c.city, c.state].filter(Boolean).join(", ") || "—"}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {c.contact_name && <div>{c.contact_name}</div>}
                    {c.contact_email && (
                      <div className="text-gray-500">{c.contact_email}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => openEdit(c)}
                      className="text-indigo-600 hover:text-indigo-900 mr-3"
                    >
                      <Edit className="h-4 w-4 inline" />
                    </button>
                    <button
                      onClick={() => remove(c)}
                      className="text-red-600 hover:text-red-800"
                    >
                      <Trash2 className="h-4 w-4 inline" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {modalOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div
            className="bg-white rounded-lg max-w-lg w-full p-6"
            data-glass="work"
          >
            <h2 className="text-lg font-bold mb-4">
              {editing ? "Edit College" : "New College"}
            </h2>
            <div className="space-y-3">
              <input
                className="w-full border rounded px-3 py-2"
                placeholder="Name *"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
              <input
                className="w-full border rounded px-3 py-2"
                placeholder="Slug (optional — auto from name)"
                value={form.slug}
                onChange={(e) => setForm({ ...form, slug: e.target.value })}
              />
              <div className="grid grid-cols-2 gap-3">
                <input
                  className="border rounded px-3 py-2"
                  placeholder="City"
                  value={form.city}
                  onChange={(e) => setForm({ ...form, city: e.target.value })}
                />
                <input
                  className="border rounded px-3 py-2"
                  placeholder="State"
                  value={form.state}
                  onChange={(e) => setForm({ ...form, state: e.target.value })}
                />
              </div>
              <input
                className="w-full border rounded px-3 py-2"
                placeholder="Contact name"
                value={form.contact_name}
                onChange={(e) =>
                  setForm({ ...form, contact_name: e.target.value })
                }
              />
              <input
                className="w-full border rounded px-3 py-2"
                placeholder="Contact email"
                value={form.contact_email}
                onChange={(e) =>
                  setForm({ ...form, contact_email: e.target.value })
                }
              />
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button
                className="px-4 py-2 border rounded"
                onClick={() => setModalOpen(false)}
              >
                Cancel
              </button>
              <button
                className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
                onClick={submit}
              >
                {editing ? "Save" : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  );
};

export default AdminColleges;
