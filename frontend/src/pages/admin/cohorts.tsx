import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useEffect, useState } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import {
  Plus,
  Edit,
  Trash2,
  Copy,
  Users,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/api/axios";
import {
  cohortApi,
  collegeApi,
  Cohort,
  College,
  CohortCreatePayload,
  CohortMember,
} from "@/api/cohort";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";

interface MiniCourse {
  id: number;
  post_title?: string;
  title?: string;
}
interface MiniUser {
  id: number;
  display_name?: string;
  user_email?: string;
  email?: string;
  role?: string;
}

export const AdminCohorts: React.FC = () => {
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [colleges, setColleges] = useState<College[]>([]);
  const [courses, setCourses] = useState<MiniCourse[]>([]);
  const [spocs, setSpocs] = useState<MiniUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Cohort | null>(null);
  // Member management modal state
  const [membersFor, setMembersFor] = useState<Cohort | null>(null);
  const [members, setMembers] = useState<CohortMember[]>([]);
  const [memberLoading, setMemberLoading] = useState(false);
  const [newMemberEmail, setNewMemberEmail] = useState("");
  const [addingMember, setAddingMember] = useState(false);
  const [form, setForm] = useState<CohortCreatePayload>({
    college_id: 0,
    course_id: 0,
    spoc_user_id: 0,
    name: "",
    max_students: 100,
    starts_on: null,
    ends_on: null,
    is_active: true,
    referral_max_uses: 100,
    referral_expires_at: null,
  });
  // Seat price is edit-only (backend CohortCreate doesn't accept it); kept as a
  // separate string field so the input can be empty without coercing to 0.
  const [seatPriceInput, setSeatPriceInput] = useState("");

  const load = async () => {
    try {
      setLoading(true);
      const [cList, cgList] = await Promise.all([
        cohortApi.list(),
        collegeApi.list(),
      ]);
      setCohorts(cList);
      setColleges(cgList);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load cohorts");
    } finally {
      setLoading(false);
    }
  };

  const loadPickers = async () => {
    try {
      const [coursesRes, spocsRes] = await Promise.all([
        api
          .get("/admin/courses")
          .then((r) => r.data)
          .catch(() => []),
        api
          .get("/admin/spocs")
          .then((r) => r.data)
          .catch(() => []),
      ]);
      setCourses(
        Array.isArray(coursesRes)
          ? coursesRes
          : coursesRes?.items || coursesRes?.data || [],
      );
      const spocsArr: any[] = Array.isArray(spocsRes)
        ? spocsRes
        : spocsRes?.items || spocsRes?.data || [];
      // Normalise to MiniUser shape the dropdown expects
      setSpocs(
        spocsArr.map((s) => ({
          id: s.id,
          email: s.email,
          display_name: s.display_name,
          role: "spoc",
        })),
      );
    } catch {
      setCourses([]);
      setSpocs([]);
    }
  };

  useEffect(() => {
    load();
    loadPickers();
  }, []);

  const openNew = () => {
    setEditing(null);
    setForm({
      college_id: colleges[0]?.id || 0,
      course_id: courses[0]?.id || 0,
      spoc_user_id: spocs[0]?.id || 0,
      name: "",
      max_students: 100,
      starts_on: null,
      ends_on: null,
      is_active: true,
      referral_max_uses: 100,
      referral_expires_at: null,
    });
    setSeatPriceInput("");
    setModalOpen(true);
  };

  const openEdit = (c: Cohort) => {
    setEditing(c);
    setForm({
      college_id: c.college_id,
      course_id: c.course_id,
      spoc_user_id: c.spoc_user_id,
      name: c.name,
      max_students: c.max_students,
      starts_on: c.starts_on || null,
      ends_on: c.ends_on || null,
      is_active: c.is_active,
    });
    setSeatPriceInput(c.seat_price != null ? String(c.seat_price) : "");
    setModalOpen(true);
  };

  const submit = async () => {
    if (!form.name.trim()) {
      toast.error("Name required");
      return;
    }
    if (!form.college_id || !form.course_id || !form.spoc_user_id) {
      toast.error("College, course, and SPOC are required");
      return;
    }
    const trimmedSeatPrice = seatPriceInput.trim();
    if (
      trimmedSeatPrice &&
      (isNaN(Number(trimmedSeatPrice)) || Number(trimmedSeatPrice) <= 0)
    ) {
      toast.error("Seat price must be a positive number");
      return;
    }
    try {
      if (editing) {
        // seat_price only accepted on update — null clears the override,
        // omitting leaves it untouched (backend uses exclude_unset).
        const payload = {
          ...form,
          seat_price: trimmedSeatPrice ? Number(trimmedSeatPrice) : null,
        };
        await cohortApi.update(editing.id, payload);
        toast.success("Cohort updated");
      } else {
        await cohortApi.create(form);
        toast.success("Cohort created — referral code generated");
      }
      setModalOpen(false);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Save failed");
    }
  };

  const remove = async (c: Cohort) => {
    if (!(await confirmDialog(`Delete cohort "${c.name}"?`))) return;
    try {
      await cohortApi.remove(c.id);
      toast.success("Deleted");
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Delete failed");
    }
  };

  const openMembers = async (c: Cohort) => {
    setMembersFor(c);
    setNewMemberEmail("");
    setMemberLoading(true);
    try {
      setMembers(await cohortApi.listMembers(c.id));
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load members");
      setMembers([]);
    } finally {
      setMemberLoading(false);
    }
  };

  const addMember = async () => {
    if (!membersFor || !newMemberEmail.trim()) return;
    setAddingMember(true);
    try {
      await cohortApi.addMember(membersFor.id, {
        email: newMemberEmail.trim(),
      });
      toast.success("Student added to cohort");
      setNewMemberEmail("");
      setMembers(await cohortApi.listMembers(membersFor.id));
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to add member");
    } finally {
      setAddingMember(false);
    }
  };

  const removeMember = async (userId: number) => {
    if (
      !membersFor ||
      !(await confirmDialog("Remove this student from the cohort?"))
    )
      return;
    try {
      await cohortApi.removeMember(membersFor.id, userId);
      toast.success("Removed");
      setMembers(await cohortApi.listMembers(membersFor.id));
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to remove member");
    }
  };

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code).then(
      () => toast.success("Copied!"),
      () => toast.error("Copy failed"),
    );
  };

  const regenerateCode = async (c: Cohort) => {
    if (
      !(await confirmDialog(
        "Regenerate referral code? The current one stops working immediately.",
      ))
    )
      return;
    try {
      const rc = await cohortApi.regenerateCode(c.id);
      toast.success(`New code: ${rc.code}`);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to regenerate code");
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Users className="h-6 w-6" /> Cohorts
            </h1>
            <p className="text-sm text-gray-500">
              Manage college cohorts and referral signup codes
            </p>
          </div>
          <div className="flex items-center gap-3">
            <ExportImportPanel section="cohorts" />
            <button
              onClick={openNew}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-indigo-700"
            >
              <Plus className="h-4 w-4" /> New Cohort
            </button>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-cohorts"
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
                College
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Referral Code
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Uses
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Seat Price
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Active
              </th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-gray-400">
                  Loading…
                </td>
              </tr>
            ) : cohorts.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-gray-400">
                  No cohorts yet
                </td>
              </tr>
            ) : (
              cohorts.map((c) => {
                const college = colleges.find((x) => x.id === c.college_id);
                const rc = c.referral_code;
                return (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{c.name}</td>
                    <td className="px-4 py-3 text-sm">
                      {college?.name || `#${c.college_id}`}
                    </td>
                    <td className="px-4 py-3">
                      {rc ? (
                        <div className="flex items-center gap-2">
                          <code className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded font-mono text-sm font-bold">
                            {rc.code}
                          </code>
                          <button
                            onClick={() => copyCode(rc.code)}
                            className="text-gray-400 hover:text-indigo-600"
                          >
                            <Copy className="h-4 w-4" />
                          </button>
                        </div>
                      ) : (
                        <span className="text-gray-400 text-sm">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {rc ? `${rc.used_count}/${rc.max_uses}` : "—"}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {c.seat_price != null ? (
                        `₹${c.seat_price}`
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {c.is_active ? (
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                      ) : (
                        <span className="text-gray-400 text-sm">off</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <button
                        onClick={() => openMembers(c)}
                        className="text-gray-600 mr-3"
                        title="Manage members"
                      >
                        <Users className="h-4 w-4 inline" />
                      </button>
                      <button
                        onClick={() => regenerateCode(c)}
                        className="text-amber-600 mr-3"
                        title="Regenerate code"
                      >
                        <RefreshCw className="h-4 w-4 inline" />
                      </button>
                      <button
                        onClick={() => openEdit(c)}
                        className="text-indigo-600 mr-3"
                        title="Edit"
                      >
                        <Edit className="h-4 w-4 inline" />
                      </button>
                      <button
                        onClick={() => remove(c)}
                        className="text-red-600"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4 inline" />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      {modalOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div
            className="bg-white rounded-lg max-w-xl w-full p-6"
            data-glass="work"
          >
            <h2 className="text-lg font-bold mb-4">
              {editing ? "Edit Cohort" : "New Cohort"}
            </h2>
            <div className="space-y-3">
              <input
                className="w-full border rounded px-3 py-2"
                placeholder="Cohort name *"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />

              <label className="block text-sm text-gray-600">College</label>
              <select
                className="w-full border rounded px-3 py-2"
                value={form.college_id}
                onChange={(e) =>
                  setForm({ ...form, college_id: Number(e.target.value) })
                }
              >
                <option value={0}>-- Select college --</option>
                {colleges.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>

              <label className="block text-sm text-gray-600">Course</label>
              <select
                className="w-full border rounded px-3 py-2"
                value={form.course_id}
                onChange={(e) =>
                  setForm({ ...form, course_id: Number(e.target.value) })
                }
              >
                <option value={0}>-- Select course --</option>
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.post_title || c.title || `#${c.id}`}
                  </option>
                ))}
              </select>

              <label className="block text-sm text-gray-600">SPOC user</label>
              <select
                className="w-full border rounded px-3 py-2"
                value={form.spoc_user_id}
                onChange={(e) =>
                  setForm({ ...form, spoc_user_id: Number(e.target.value) })
                }
              >
                <option value={0}>-- Select SPOC --</option>
                {spocs.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.display_name || u.user_email || u.email} ({u.role})
                  </option>
                ))}
              </select>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Max students
                  </label>
                  <input
                    type="number"
                    className="w-full border rounded px-3 py-2"
                    value={form.max_students}
                    onChange={(e) =>
                      setForm({ ...form, max_students: Number(e.target.value) })
                    }
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Active
                  </label>
                  <select
                    className="w-full border rounded px-3 py-2"
                    value={form.is_active ? "1" : "0"}
                    onChange={(e) =>
                      setForm({ ...form, is_active: e.target.value === "1" })
                    }
                  >
                    <option value="1">Active</option>
                    <option value="0">Inactive</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Starts on
                  </label>
                  <input
                    type="date"
                    className="w-full border rounded px-3 py-2"
                    value={form.starts_on || ""}
                    onChange={(e) =>
                      setForm({ ...form, starts_on: e.target.value || null })
                    }
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Ends on
                  </label>
                  <input
                    type="date"
                    className="w-full border rounded px-3 py-2"
                    value={form.ends_on || ""}
                    onChange={(e) =>
                      setForm({ ...form, ends_on: e.target.value || null })
                    }
                  />
                </div>
              </div>

              {editing && (
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Seat price (₹)
                  </label>
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    className="w-full border rounded px-3 py-2"
                    placeholder="Leave empty for course's normal price"
                    value={seatPriceInput}
                    onChange={(e) => setSeatPriceInput(e.target.value)}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Overrides the course price for referral checkout into this
                    cohort. Leave empty to clear the override.
                  </p>
                </div>
              )}

              {!editing && (
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Referral code — max uses
                  </label>
                  <input
                    type="number"
                    className="w-full border rounded px-3 py-2"
                    value={form.referral_max_uses}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        referral_max_uses: Number(e.target.value),
                      })
                    }
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    A referral code is auto-generated on creation.
                  </p>
                </div>
              )}
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
      {membersFor && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div
            className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col"
            data-glass="work"
          >
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <div>
                <h2 className="text-lg font-semibold">
                  Cohort members — {membersFor.name}
                </h2>
                <p className="text-xs text-gray-500">
                  Students auto-added when they use the referral code, paid via
                  a cohort coupon, or added here manually.
                </p>
              </div>
              <button
                onClick={() => setMembersFor(null)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                ×
              </button>
            </div>

            <div className="px-6 py-4 border-b bg-gray-50">
              <div className="flex gap-2">
                <input
                  type="email"
                  placeholder="student@example.com"
                  className="flex-1 border rounded px-3 py-2 text-sm"
                  value={newMemberEmail}
                  onChange={(e) => setNewMemberEmail(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addMember();
                    }
                  }}
                />
                <button
                  onClick={addMember}
                  disabled={addingMember || !newMemberEmail.trim()}
                  className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
                >
                  {addingMember ? "Adding…" : "Add"}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                The student must already have a SashaInfinity account. They'll
                be enrolled in this cohort's course automatically.
              </p>
            </div>

            <div className="overflow-y-auto flex-1 px-6 py-4">
              {memberLoading ? (
                <p className="text-sm text-gray-400 text-center py-6">
                  Loading members…
                </p>
              ) : members.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-6">
                  No members yet.
                </p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="text-xs uppercase text-gray-500 border-b">
                    <tr>
                      <th className="text-left py-2">Name</th>
                      <th className="text-left py-2">Email</th>
                      <th className="text-left py-2">Joined</th>
                      <th className="text-right py-2">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {members.map((m) => (
                      <tr
                        key={m.membership_id}
                        className="border-b hover:bg-gray-50"
                      >
                        <td className="py-2">{m.display_name}</td>
                        <td className="py-2 text-gray-600">{m.email}</td>
                        <td className="py-2 text-gray-500">
                          {new Date(m.joined_at).toLocaleDateString()}
                        </td>
                        <td className="py-2 text-right">
                          <button
                            onClick={() => removeMember(m.user_id)}
                            className="text-red-600 hover:text-red-700 text-xs"
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  );
};

export default AdminCohorts;
