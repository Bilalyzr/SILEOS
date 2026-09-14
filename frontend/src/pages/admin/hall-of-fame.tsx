import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Admin Wall of Fame management.
 *
 * CRUD + reorder for the staff profiles shown on the public /hall-of-fame page.
 * Accessible to admin + superadmin (route gated by require_admin).
 */
import React, { useEffect, useState } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import {
  Plus,
  Edit3,
  Trash2,
  ArrowUp,
  ArrowDown,
  X,
  Upload,
  Loader2,
  Eye,
  EyeOff,
  ImageIcon,
} from "lucide-react";
import toast from "react-hot-toast";
import {
  hallOfFameApi,
  type HallOfFameMember,
  type MemberInput,
} from "@/api/hallOfFame";
import { uploadImage } from "@/api/upload";

const emptyForm: MemberInput = {
  name: "",
  role: "",
  company: "",
  photo: null,
  tenure: "",
  location: "",
  linkedin: "",
  blurb: "",
  highlight: "",
  sort_order: 0,
  is_published: true,
};

export function AdminHallOfFame() {
  const [members, setMembers] = useState<HallOfFameMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<HallOfFameMember | null>(null);
  const [form, setForm] = useState<MemberInput>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);

  useEffect(() => {
    fetchMembers();
  }, []);

  const fetchMembers = async () => {
    try {
      setLoading(true);
      const data = await hallOfFameApi.listAll();
      setMembers(data);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load Wall of Fame");
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditing(null);
    setForm({ ...emptyForm, sort_order: members.length });
    setShowForm(true);
  };

  const openEdit = (m: HallOfFameMember) => {
    setEditing(m);
    setForm({
      name: m.name,
      role: m.role,
      company: m.company,
      photo: m.photo,
      tenure: m.tenure,
      location: m.location,
      linkedin: m.linkedin,
      blurb: m.blurb,
      highlight: m.highlight,
      sort_order: m.sort_order,
      is_published: m.is_published,
    });
    setShowForm(true);
  };

  const handlePhotoUpload = async (file: File) => {
    setUploadingPhoto(true);
    try {
      const res = await uploadImage(file);
      setForm((f) => ({ ...f, photo: res.file_url }));
      toast.success("Photo uploaded");
    } catch (e: any) {
      toast.error(e?.message || "Photo upload failed");
    } finally {
      setUploadingPhoto(false);
    }
  };

  const handleSave = async () => {
    if (!form.name.trim()) {
      toast.error("Name is required");
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        await hallOfFameApi.update(editing.id, form);
        toast.success("Member updated");
      } else {
        await hallOfFameApi.create(form);
        toast.success("Member added");
      }
      setShowForm(false);
      fetchMembers();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (m: HallOfFameMember) => {
    if (!(await confirmDialog(`Delete "${m.name}" from the Wall of Fame?`)))
      return;
    try {
      await hallOfFameApi.remove(m.id);
      toast.success("Member deleted");
      fetchMembers();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Delete failed");
    }
  };

  const togglePublished = async (m: HallOfFameMember) => {
    try {
      await hallOfFameApi.update(m.id, { is_published: !m.is_published });
      fetchMembers();
    } catch (e: any) {
      toast.error("Toggle failed");
    }
  };

  const move = async (m: HallOfFameMember, dir: -1 | 1) => {
    const idx = members.findIndex((x) => x.id === m.id);
    const swapWith = idx + dir;
    if (swapWith < 0 || swapWith >= members.length) return;
    const other = members[swapWith];
    try {
      await hallOfFameApi.reorder([
        { id: m.id, sort_order: other.sort_order },
        { id: other.id, sort_order: m.sort_order },
      ]);
      fetchMembers();
    } catch (e: any) {
      toast.error("Reorder failed");
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-2xl font-bold text-secondary-900">
              Wall of Fame
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Manage the staff profiles shown on the public Wall of Fame page.
            </p>
          </div>
          <button
            onClick={openCreate}
            className="inline-flex items-center gap-2 rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600"
          >
            <Plus className="h-4 w-4" /> Add Member
          </button>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-hall-of-fame"
    >
      <div
        className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
        data-glass="work"
      >
        {loading ? (
          <div className="flex items-center justify-center py-16 text-slate-400">
            <Loader2 className="h-6 w-6 animate-spin" />{" "}
            <span className="ml-2">Loading...</span>
          </div>
        ) : members.length === 0 ? (
          <div className="py-16 text-center text-slate-400">
            No members yet. Click <strong>Add Member</strong> to create one.
          </div>
        ) : (
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 w-16">Order</th>
                <th className="px-4 py-3">Member</th>
                <th className="px-4 py-3">Role / Company</th>
                <th className="px-4 py-3">Tenure</th>
                <th className="px-4 py-3">Visible</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {members.map((m, i) => (
                <tr key={m.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => move(m, -1)}
                        disabled={i === 0}
                        className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700 disabled:opacity-30"
                        title="Move up"
                      >
                        <ArrowUp className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => move(m, 1)}
                        disabled={i === members.length - 1}
                        className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700 disabled:opacity-30"
                        title="Move down"
                      >
                        <ArrowDown className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <AvatarThumb name={m.name} photo={m.photo} />
                      <div>
                        <div className="font-medium text-slate-900">
                          {m.name}
                        </div>
                        {m.highlight ? (
                          <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-700">
                            {m.highlight}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-slate-900">{m.role}</div>
                    <div className="text-xs text-slate-500">{m.company}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {m.tenure || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => togglePublished(m)}
                      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
                        m.is_published
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {m.is_published ? (
                        <Eye className="h-3 w-3" />
                      ) : (
                        <EyeOff className="h-3 w-3" />
                      )}
                      {m.is_published ? "Published" : "Hidden"}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() => openEdit(m)}
                        className="rounded p-2 text-slate-500 hover:bg-slate-200 hover:text-slate-800"
                        title="Edit"
                      >
                        <Edit3 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(m)}
                        className="rounded p-2 text-rose-500 hover:bg-rose-100 hover:text-rose-700"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {showForm ? (
        <MemberForm
          form={form}
          setForm={setForm}
          editing={!!editing}
          saving={saving}
          uploadingPhoto={uploadingPhoto}
          onPhotoUpload={handlePhotoUpload}
          onSave={handleSave}
          onClose={() => setShowForm(false)}
        />
      ) : null}
    </PageLayout>
  );
}

/** Small avatar thumbnail for the table. */
const AvatarThumb: React.FC<{ name: string; photo: string | null }> = ({
  name,
  photo,
}) => {
  const [broken, setBroken] = React.useState(false);
  const show = photo && !broken;
  const initials = name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <div className="h-10 w-10 flex-shrink-0 overflow-hidden rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center text-xs font-bold text-white">
      {show ? (
        <img
          src={photo!}
          alt={name}
          onError={() => setBroken(true)}
          className="h-full w-full object-cover"
        />
      ) : (
        initials
      )}
    </div>
  );
};

/** Modal form for create/edit. */
const MemberForm: React.FC<{
  form: MemberInput;
  setForm: React.Dispatch<React.SetStateAction<MemberInput>>;
  editing: boolean;
  saving: boolean;
  uploadingPhoto: boolean;
  onPhotoUpload: (file: File) => void;
  onSave: () => void;
  onClose: () => void;
}> = ({
  form,
  setForm,
  editing,
  saving,
  uploadingPhoto,
  onPhotoUpload,
  onSave,
  onClose,
}) => {
  const field = (
    label: string,
    key: keyof MemberInput,
    opts: { type?: string; placeholder?: string } = {},
  ) => (
    <label className="block">
      <span className="text-xs font-semibold text-slate-700">{label}</span>
      <input
        type={opts.type || "text"}
        value={(form[key] as string) ?? ""}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
        placeholder={opts.placeholder}
        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-orange-400 focus:outline-none focus:ring-1 focus:ring-orange-400"
      />
    </label>
  );

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        data-glass="work"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-secondary-900">
            {editing ? "Edit Member" : "Add Member"}
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Photo upload */}
          <div>
            <span className="text-xs font-semibold text-slate-700">Photo</span>
            <div className="mt-1 flex items-center gap-4">
              <div className="h-20 w-20 overflow-hidden rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center text-xl font-bold text-white">
                {form.photo ? (
                  <img
                    src={form.photo}
                    alt="preview"
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <ImageIcon className="h-6 w-6 opacity-70" />
                )}
              </div>
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
                {uploadingPhoto ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
                {uploadingPhoto ? "Uploading..." : "Upload photo"}
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  disabled={uploadingPhoto}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) onPhotoUpload(f);
                  }}
                />
              </label>
              {form.photo ? (
                <button
                  onClick={() => setForm((f) => ({ ...f, photo: null }))}
                  className="text-xs font-medium text-rose-600 hover:underline"
                >
                  Remove
                </button>
              ) : null}
            </div>
          </div>

          {field("Name *", "name", { placeholder: "Priya Sharma" })}
          <div className="grid grid-cols-2 gap-4">
            {field("Role / Title", "role", { placeholder: "Founder & CEO" })}
            {field("Company", "company", {
              placeholder: "SashaInfinity Pvt Ltd",
            })}
          </div>
          <div className="grid grid-cols-2 gap-4">
            {field("Tenure", "tenure", { placeholder: "5 years" })}
            {field("Location", "location", { placeholder: "Salem, India" })}
          </div>
          {field("LinkedIn URL", "linkedin", {
            placeholder: "https://linkedin.com/in/...",
          })}
          {field("Highlight badge (optional)", "highlight", {
            placeholder: "Top Mentor",
          })}

          <label className="block">
            <span className="text-xs font-semibold text-slate-700">
              Blurb / short bio
            </span>
            <textarea
              value={form.blurb ?? ""}
              onChange={(e) =>
                setForm((f) => ({ ...f, blurb: e.target.value }))
              }
              rows={2}
              placeholder="One-liner about this person"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-orange-400 focus:outline-none focus:ring-1 focus:ring-orange-400"
            />
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.is_published ?? true}
              onChange={(e) =>
                setForm((f) => ({ ...f, is_published: e.target.checked }))
              }
              className="h-4 w-4 rounded border-slate-300"
            />
            <span className="text-sm text-slate-700">
              Published (visible on public page)
            </span>
          </label>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            onClick={onSave}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 disabled:opacity-50"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {saving ? "Saving..." : editing ? "Save Changes" : "Add Member"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminHallOfFame;
