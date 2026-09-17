import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useCallback, useEffect, useState } from "react";
import { confirmDialog, promptDialog } from "@/components/ui/confirm";
import { createPortal } from "react-dom";
import toast from "react-hot-toast";
import {
  Plus,
  Edit,
  Trash2,
  Briefcase,
  Users,
  Ticket,
  Copy,
  X,
  Calendar,
  Award,
  Check,
  Image as ImageIcon,
} from "lucide-react";
import { api } from "@/api/axios";
import { uploadImage } from "@/api/upload";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";
import { InternshipAnalyticsCharts } from "@/components/admin/InternshipAnalyticsCharts";
import {
  internshipApi,
  AdminInternshipRow,
  AdminInternshipCreatePayload,
  AdminVoucherRow,
  AdminRosterRow,
  AdminAttendanceRow,
  ApprovedCompanyRow,
} from "@/api/internship";

interface SpocOption {
  id: number;
  email: string;
  display_name: string;
}

type FormState = AdminInternshipCreatePayload;

const EMPTY: FormState = {
  title: "",
  description: "",
  price: 0,
  spoc_user_id: 0,
  cover_image: "",
  is_published: true,
};

export const AdminInternships: React.FC = () => {
  const [rows, setRows] = useState<AdminInternshipRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [spocs, setSpocs] = useState<SpocOption[]>([]);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [formOpen, setFormOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Modals for vouchers / roster
  const [vouchersFor, setVouchersFor] = useState<AdminInternshipRow | null>(
    null,
  );
  const [vouchersData, setVouchersData] = useState<AdminVoucherRow[] | null>(
    null,
  );
  const [vouchersLoading, setVouchersLoading] = useState(false);

  const [rosterFor, setRosterFor] = useState<AdminInternshipRow | null>(null);
  const [rosterData, setRosterData] = useState<AdminRosterRow[] | null>(null);
  const [rosterLoading, setRosterLoading] = useState(false);

  // Approved companies for the "assign company" dropdown (loaded lazily
  // when the roster opens).
  const [companies, setCompanies] = useState<ApprovedCompanyRow[]>([]);
  const [rowBusy, setRowBusy] = useState<Record<string, boolean>>({});

  // Attendance-log mini-modal state.
  const [attendanceFor, setAttendanceFor] = useState<AdminRosterRow | null>(
    null,
  );
  const [attendanceRows, setAttendanceRows] = useState<
    AdminAttendanceRow[] | null
  >(null);
  const [attendanceLoading, setAttendanceLoading] = useState(false);
  const [attForm, setAttForm] = useState<{
    attended_at: string;
    status: string;
    notes: string;
  }>({
    attended_at: new Date().toISOString().slice(0, 10),
    status: "present",
    notes: "",
  });

  // Manual voucher creation state
  const [addStudentOpen, setAddStudentOpen] = useState(false);
  const [addStudentForm, setAddStudentForm] = useState({
    user_id: 0,
    amount_paid: 0,
  });
  const [addStudentSaving, setAddStudentSaving] = useState(false);
  const [students, setStudents] = useState<
    { id: number; email: string; display_name: string }[]
  >([]);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [list, spocRes] = await Promise.all([
        internshipApi.adminList(),
        api.get<SpocOption[]>("/admin/spocs"),
      ]);
      setRows(list || []);
      setSpocs(spocRes.data || []);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to load internships");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const startCreate = () => {
    setEditingId(null);
    setForm({ ...EMPTY, spoc_user_id: spocs[0]?.id || 0 });
    setFormOpen(true);
  };

  const startEdit = (r: AdminInternshipRow) => {
    setEditingId(r.id);
    setForm({
      title: r.title,
      description: r.description,
      price: r.price,
      spoc_user_id: r.spoc_user_id,
      cover_image: r.cover_image || "",
      is_published: r.is_published,
    });
    setFormOpen(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || !form.spoc_user_id || form.price < 0) {
      toast.error("Title, SPOC, and a valid price are required");
      return;
    }
    try {
      setSaving(true);
      if (editingId) {
        await internshipApi.adminUpdate(editingId, form);
        toast.success("Internship updated");
      } else {
        await internshipApi.adminCreate(form);
        toast.success("Internship created");
      }
      setFormOpen(false);
      await load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (r: AdminInternshipRow) => {
    const warn =
      `Delete "${r.title}"?\n\n` +
      "This permanently deletes the internship and ALL its vouchers. " +
      "Students who have already redeemed their voucher keep access to their " +
      "chosen course — only the internship-cohort link is removed.";
    if (!(await confirmDialog(warn))) return;
    try {
      await internshipApi.adminDelete(r.id);
      setRows((prev) => prev.filter((x) => x.id !== r.id));
      toast.success("Internship deleted");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Delete failed";
      toast.error(msg);
    }
  };

  const openVouchers = async (r: AdminInternshipRow) => {
    setVouchersFor(r);
    setVouchersData(null);
    setVouchersLoading(true);
    try {
      setVouchersData(await internshipApi.adminVouchers(r.id));
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to load vouchers");
      setVouchersFor(null);
    } finally {
      setVouchersLoading(false);
    }
  };

  const openRoster = async (r: AdminInternshipRow) => {
    setRosterFor(r);
    setRosterData(null);
    setRosterLoading(true);
    try {
      const [roster, approved] = await Promise.all([
        internshipApi.adminRoster(r.id),
        companies.length > 0
          ? Promise.resolve(companies)
          : internshipApi.listApprovedCompanies().catch(() => []),
      ]);
      setRosterData(roster);
      if (approved && approved.length > 0) setCompanies(approved);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to load roster");
      setRosterFor(null);
    } finally {
      setRosterLoading(false);
    }
  };

  const refreshRoster = async () => {
    if (!rosterFor) return;
    try {
      setRosterData(await internshipApi.adminRoster(rosterFor.id));
    } catch {
      // non-fatal — leave existing data in place
    }
  };

  const markPresentToday = async (row: AdminRosterRow) => {
    if (!rosterFor || !row.buyer_id) return;
    const key = `att-${row.voucher_id}`;
    setRowBusy((b) => ({ ...b, [key]: true }));
    try {
      await internshipApi.adminAttendanceMark(rosterFor.id, {
        user_id: row.buyer_id,
        attended_at: new Date().toISOString().slice(0, 10),
        status: "present",
      });
      toast.success("Marked present");
      await refreshRoster();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to mark attendance");
    } finally {
      setRowBusy((b) => ({ ...b, [key]: false }));
    }
  };

  const openAttendanceLog = async (row: AdminRosterRow) => {
    if (!rosterFor || !row.buyer_id) return;
    setAttendanceFor(row);
    setAttendanceRows(null);
    setAttendanceLoading(true);
    setAttForm({
      attended_at: new Date().toISOString().slice(0, 10),
      status: "present",
      notes: "",
    });
    try {
      setAttendanceRows(
        await internshipApi.adminAttendanceList(rosterFor.id, row.buyer_id),
      );
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to load attendance");
      setAttendanceFor(null);
    } finally {
      setAttendanceLoading(false);
    }
  };

  const submitAttendance = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rosterFor || !attendanceFor || !attendanceFor.buyer_id) return;
    try {
      await internshipApi.adminAttendanceMark(rosterFor.id, {
        user_id: attendanceFor.buyer_id,
        attended_at: attForm.attended_at,
        status: attForm.status,
        notes: attForm.notes,
      });
      toast.success("Attendance saved");
      setAttendanceRows(
        await internshipApi.adminAttendanceList(
          rosterFor.id,
          attendanceFor.buyer_id,
        ),
      );
      await refreshRoster();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to save attendance");
    }
  };

  const deleteAttendance = async (rec: AdminAttendanceRow) => {
    if (!rosterFor || !attendanceFor || !attendanceFor.buyer_id) return;
    if (!(await confirmDialog(`Delete attendance on ${rec.attended_at}?`)))
      return;
    try {
      await internshipApi.adminAttendanceDelete(rosterFor.id, rec.id);
      setAttendanceRows(
        await internshipApi.adminAttendanceList(
          rosterFor.id,
          attendanceFor.buyer_id,
        ),
      );
      await refreshRoster();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to delete record");
    }
  };

  const assignCompany = async (row: AdminRosterRow, companyId: number) => {
    if (!rosterFor || !companyId) return;
    const key = `co-${row.voucher_id}`;
    setRowBusy((b) => ({ ...b, [key]: true }));
    try {
      await internshipApi.adminAssignCompany(
        rosterFor.id,
        row.voucher_id,
        companyId,
      );
      toast.success("Company assigned");
      await refreshRoster();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to assign company");
    } finally {
      setRowBusy((b) => ({ ...b, [key]: false }));
    }
  };

  const clearCompanyOverride = async (row: AdminRosterRow) => {
    if (!rosterFor) return;
    if (
      !(await confirmDialog(
        "Clear manual company override (resume auto detection)?",
      ))
    )
      return;
    const key = `co-${row.voucher_id}`;
    setRowBusy((b) => ({ ...b, [key]: true }));
    try {
      await internshipApi.adminClearCompanyOverride(
        rosterFor.id,
        row.voucher_id,
      );
      toast.success("Override cleared");
      await refreshRoster();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to clear override");
    } finally {
      setRowBusy((b) => ({ ...b, [key]: false }));
    }
  };

  const issueCertificate = async (row: AdminRosterRow) => {
    if (!row.enrollment_id) {
      toast.error("Student has not redeemed voucher (no enrollment yet)");
      return;
    }
    if (
      !(await confirmDialog(
        "Force completion and issue certificate for this student?",
      ))
    )
      return;
    const key = `cert-${row.voucher_id}`;
    setRowBusy((b) => ({ ...b, [key]: true }));
    try {
      await internshipApi.adminIssueCertForEnrollment(row.enrollment_id, true);
      toast.success("Certificate issued");
      await refreshRoster();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to issue certificate");
    } finally {
      setRowBusy((b) => ({ ...b, [key]: false }));
    }
  };

  const revokeCertificate = async (row: AdminRosterRow) => {
    if (!row.issued_certificate_id) {
      toast.error("No certificate on file for this student");
      return;
    }
    const reason = await promptDialog("Reason for revoking certificate:");
    if (!reason || !reason.trim()) return;
    const key = `cert-${row.voucher_id}`;
    setRowBusy((b) => ({ ...b, [key]: true }));
    try {
      await internshipApi.adminRevokeCert(
        row.issued_certificate_id,
        reason.trim(),
      );
      toast.success("Certificate revoked");
      await refreshRoster();
    } catch (err: any) {
      toast.error(
        err?.response?.data?.detail || "Failed to revoke certificate",
      );
    } finally {
      setRowBusy((b) => ({ ...b, [key]: false }));
    }
  };

  const copyCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      toast.success("Copied");
    } catch {
      toast.error("Copy failed");
    }
  };

  const openAddStudent = async () => {
    setAddStudentForm({ user_id: 0, amount_paid: 0 });
    setAddStudentOpen(true);
    try {
      const res =
        await api.get<{ id: number; email: string; display_name: string }[]>(
          "/admin/students",
        );
      setStudents(res.data || []);
    } catch {
      setStudents([]);
    }
  };

  const submitAddStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rosterFor || !addStudentForm.user_id) {
      toast.error("Please select a student");
      return;
    }
    setAddStudentSaving(true);
    try {
      await internshipApi.adminCreateManualVoucher(
        rosterFor.id,
        addStudentForm,
      );
      toast.success("Student added to roster");
      setAddStudentOpen(false);
      await refreshRoster();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to add student");
    } finally {
      setAddStudentSaving(false);
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith("image/")) {
      toast.error("Please select an image file");
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error("Image must be smaller than 5MB");
      return;
    }

    try {
      setUploading(true);
      const result = await uploadImage(file);
      setForm({ ...form, cover_image: result.file_url });
      toast.success("Image uploaded successfully");
    } catch (err: any) {
      toast.error(err?.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const removeImage = () => {
    setForm({ ...form, cover_image: "" });
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <Briefcase className="w-7 h-7 text-yellow-500" />
              Paid Internships
            </h1>
            <p className="text-gray-600 mt-1">
              Manage paid internship programs, vouchers, and roster
            </p>
          </div>
          <div className="flex items-center gap-3">
            <ExportImportPanel section="internships" />
            <button
              onClick={startCreate}
              className="inline-flex items-center gap-2 bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-semibold px-4 py-2 rounded-lg"
            >
              <Plus className="w-4 h-4" /> New Internship
            </button>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-internships"
    >
      <InternshipAnalyticsCharts period="30d" />
      <div
        className="bg-white border border-gray-200 rounded-lg overflow-hidden"
        data-glass="work"
      >
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <Th>Title</Th>
              <Th>Price</Th>
              <Th>SPOC</Th>
              <Th>Vouchers</Th>
              <Th>Published</Th>
              <Th>Actions</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-gray-500">
                  Loading...
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-gray-500">
                  No internships yet. Click "New Internship" to create one.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {r.title}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    ₹{Number(r.price).toLocaleString("en-IN")}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {r.spoc_name || "—"}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {r.vouchers_redeemed} / {r.vouchers_issued}
                    <div className="text-xs text-gray-500">
                      redeemed / issued
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        r.is_published
                          ? "bg-green-100 text-green-800"
                          : "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {r.is_published ? "Published" : "Draft"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => openVouchers(r)}
                        className="text-gray-600 hover:text-gray-900"
                        title="View vouchers"
                      >
                        <Ticket className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => openRoster(r)}
                        className="text-gray-600 hover:text-gray-900"
                        title="View roster"
                      >
                        <Users className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => startEdit(r)}
                        className="text-blue-600 hover:text-blue-900"
                        title="Edit"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => remove(r)}
                        className="text-red-600 hover:text-red-900"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {formOpen && (
        <Overlay onClose={() => setFormOpen(false)}>
          <form
            onSubmit={save}
            className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6 space-y-4 max-h-[90vh] my-auto overflow-y-auto"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">
                {editingId ? "Edit internship" : "New internship"}
              </h2>
              <button
                type="button"
                onClick={() => setFormOpen(false)}
                className="text-gray-500 hover:text-gray-900"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <TextField
              label="Title"
              required
              value={form.title}
              onChange={(v) => setForm({ ...form, title: v })}
            />

            <label className="block">
              <span className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </span>
              <textarea
                value={form.description}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value })
                }
                rows={5}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </label>

            <div className="grid md:grid-cols-2 gap-4">
              <label className="block">
                <span className="block text-sm font-medium text-gray-700 mb-1">
                  Price (₹) <span className="text-red-600">*</span>
                </span>
                <input
                  type="number"
                  min={0}
                  step={1}
                  value={form.price}
                  onChange={(e) =>
                    setForm({ ...form, price: Number(e.target.value) })
                  }
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </label>
              <label className="block">
                <span className="block text-sm font-medium text-gray-700 mb-1">
                  SPOC (mentor) <span className="text-red-600">*</span>
                </span>
                <select
                  value={form.spoc_user_id || ""}
                  onChange={(e) =>
                    setForm({ ...form, spoc_user_id: Number(e.target.value) })
                  }
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="">Select SPOC...</option>
                  {spocs.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.display_name} ({s.email})
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {/* Cover image upload */}
            <div>
              <span className="block text-sm font-medium text-gray-700 mb-2">
                Cover image
              </span>
              {form.cover_image ? (
                <div className="relative w-full h-48 bg-gray-100 rounded-lg overflow-hidden border border-gray-300">
                  <img
                    src={form.cover_image}
                    alt="Cover preview"
                    className="w-full h-full object-contain"
                  />
                  <button
                    type="button"
                    onClick={removeImage}
                    className="absolute top-2 right-2 p-1.5 bg-red-500 hover:bg-red-600 text-white rounded-full shadow-md"
                    title="Remove image"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                  <input
                    type="file"
                    id="cover-image-upload"
                    accept="image/*"
                    onChange={handleImageUpload}
                    disabled={uploading}
                    className="hidden"
                  />
                  <label
                    htmlFor="cover-image-upload"
                    className={`cursor-pointer inline-flex flex-col items-center gap-2 ${
                      uploading ? "opacity-50 cursor-not-allowed" : ""
                    }`}
                  >
                    {uploading ? (
                      <>
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-500"></div>
                        <span className="text-sm text-gray-600">
                          Uploading...
                        </span>
                      </>
                    ) : (
                      <>
                        <ImageIcon className="w-10 h-10 text-gray-400" />
                        <span className="text-sm text-gray-600">
                          Click to upload cover image
                        </span>
                        <span className="text-xs text-gray-500">
                          PNG, JPG, GIF up to 5MB
                        </span>
                      </>
                    )}
                  </label>
                </div>
              )}
              <div className="mt-2">
                <input
                  type="text"
                  placeholder="Or paste image URL..."
                  value={form.cover_image || ""}
                  onChange={(e) =>
                    setForm({ ...form, cover_image: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                />
              </div>
            </div>

            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.is_published ?? true}
                onChange={(e) =>
                  setForm({ ...form, is_published: e.target.checked })
                }
              />
              <span className="text-sm text-gray-700">Published</span>
            </label>

            <div className="flex justify-end gap-3 pt-2 border-t border-gray-200">
              <button
                type="button"
                onClick={() => setFormOpen(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-semibold rounded-md disabled:opacity-60"
              >
                {saving ? "Saving..." : editingId ? "Save changes" : "Create"}
              </button>
            </div>
          </form>
        </Overlay>
      )}
      {vouchersFor && (
        <Modal
          onClose={() => setVouchersFor(null)}
          title={`Vouchers — ${vouchersFor.title}`}
        >
          {vouchersLoading ? (
            <div className="p-8 text-center text-gray-500">Loading...</div>
          ) : !vouchersData || vouchersData.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No vouchers issued yet.
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <Th>Code</Th>
                  <Th>Buyer</Th>
                  <Th>Status</Th>
                  <Th>Redeemed on</Th>
                  <Th>Issued</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {vouchersData.map((v) => (
                  <tr key={v.code}>
                    <td className="px-4 py-2">
                      <div className="inline-flex items-center gap-2">
                        <code className="bg-gray-100 px-2 py-0.5 rounded font-mono text-xs">
                          {v.code}
                        </code>
                        <button
                          onClick={() => copyCode(v.code)}
                          className="text-gray-500 hover:text-gray-900"
                          title="Copy"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      <div className="font-medium text-gray-900">
                        {v.buyer_name}
                      </div>
                      <div className="text-xs text-gray-500">
                        {v.buyer_email}
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          v.status === "redeemed"
                            ? "bg-green-100 text-green-800"
                            : "bg-yellow-100 text-yellow-800"
                        }`}
                      >
                        {v.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-700">
                      {v.redeemed_on_course_title || "—"}
                    </td>
                    <td className="px-4 py-2 text-gray-500">
                      {v.created_at
                        ? new Date(v.created_at).toLocaleDateString()
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Modal>
      )}
      {rosterFor && (
        <Modal
          onClose={() => setRosterFor(null)}
          title={`Roster — ${rosterFor.title}`}
          wide
        >
          <div className="px-6 py-3 border-b border-gray-200 flex justify-end">
            <button
              onClick={openAddStudent}
              className="inline-flex items-center gap-2 bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-semibold px-3 py-1.5 rounded text-sm"
            >
              <Plus className="w-3.5 h-3.5" /> Add Student
            </button>
          </div>
          {rosterLoading ? (
            <div className="p-8 text-center text-gray-500">Loading...</div>
          ) : !rosterData || rosterData.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <p>No students enrolled yet.</p>
              <button
                onClick={openAddStudent}
                className="mt-3 inline-flex items-center gap-2 bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-semibold px-4 py-2 rounded"
              >
                <Plus className="w-4 h-4" /> Add Student Manually
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-[1200px] divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <Th>Name</Th>
                    <Th>Voucher</Th>
                    <Th>Course</Th>
                    <Th>Progress</Th>
                    <Th>Completed</Th>
                    <Th>Certs</Th>
                    <Th>Attendance</Th>
                    <Th>Hired by</Th>
                    <Th>Admin actions</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {rosterData.map((r) => {
                    const attKey = `att-${r.voucher_id}`;
                    const coKey = `co-${r.voucher_id}`;
                    const certKey = `cert-${r.voucher_id}`;
                    return (
                      <tr key={r.voucher_code}>
                        <td className="px-4 py-2">
                          <div className="font-medium text-gray-900">
                            {r.buyer_name}
                          </div>
                          <div className="text-xs text-gray-500">
                            {r.buyer_email}
                          </div>
                        </td>
                        <td className="px-4 py-2">
                          <code className="bg-gray-100 px-2 py-0.5 rounded font-mono text-xs">
                            {r.voucher_code}
                          </code>
                        </td>
                        <td className="px-4 py-2 text-gray-700">
                          {r.redeemed_course_title || (
                            <span className="text-gray-400">not redeemed</span>
                          )}
                        </td>
                        <td className="px-4 py-2 w-40">
                          {r.progress_pct != null ? (
                            <div>
                              <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-green-500"
                                  style={{
                                    width: `${Math.min(100, Math.max(0, r.progress_pct))}%`,
                                  }}
                                />
                              </div>
                              <div className="text-xs text-gray-500 mt-0.5">
                                {Math.round(r.progress_pct)}%
                              </div>
                            </div>
                          ) : (
                            <span className="text-gray-400 text-xs">—</span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-gray-600">
                          {r.completion_date
                            ? new Date(r.completion_date).toLocaleDateString()
                            : "—"}
                        </td>
                        <td className="px-4 py-2 text-gray-700">
                          {r.certs_count ?? 0}
                        </td>
                        <td className="px-4 py-2 text-gray-700">
                          <span className="font-medium">
                            {r.attendance_count ?? 0}
                          </span>
                          <span className="text-xs text-gray-500 ml-1">
                            days
                          </span>
                        </td>
                        <td className="px-4 py-2 text-gray-700">
                          {r.hired_by_company ? (
                            <div className="flex items-center gap-1">
                              <span>{r.hired_by_company}</span>
                              {r.hired_by_source === "override" && (
                                <>
                                  <span
                                    className="text-[10px] uppercase tracking-wide bg-purple-100 text-purple-800 px-1.5 py-0.5 rounded font-medium"
                                    title="Manually assigned by admin"
                                  >
                                    manual
                                  </span>
                                  <button
                                    onClick={() => clearCompanyOverride(r)}
                                    disabled={!!rowBusy[coKey]}
                                    className="text-red-600 hover:text-red-800 ml-0.5"
                                    title="Clear override (resume auto detection)"
                                  >
                                    <X className="w-3 h-3" />
                                  </button>
                                </>
                              )}
                              {r.hired_by_source === "auto" && (
                                <span
                                  className="text-[10px] uppercase tracking-wide bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded"
                                  title="Auto-detected from CompanyInterest"
                                >
                                  auto
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                        <td className="px-4 py-2 relative">
                          <div className="flex flex-col gap-1.5">
                            {/* Attendance */}
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => markPresentToday(r)}
                                disabled={!r.buyer_id || !!rowBusy[attKey]}
                                className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-green-50 hover:bg-green-100 text-green-800 rounded border border-green-200 disabled:opacity-50"
                                title="Mark present today"
                              >
                                <Check className="w-3 h-3" /> Present
                              </button>
                              <button
                                onClick={() => openAttendanceLog(r)}
                                disabled={!r.buyer_id}
                                className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-gray-50 hover:bg-gray-100 text-gray-700 rounded border border-gray-200 disabled:opacity-50"
                                title="View attendance log"
                              >
                                <Calendar className="w-3 h-3" /> Log
                              </button>
                            </div>

                            {/* Assign company */}
                            <div className="flex items-center gap-1 relative z-50">
                              <select
                                value=""
                                onChange={(e) => {
                                  const id = Number(e.target.value);
                                  if (id) assignCompany(r, id);
                                  e.currentTarget.selectedIndex = 0;
                                }}
                                disabled={
                                  !!rowBusy[coKey] || companies.length === 0
                                }
                                className="text-xs px-2 py-1.5 border border-gray-300 rounded-md min-w-[160px] max-w-[200px] bg-white"
                                title="Assign hiring company"
                              >
                                <option value="">
                                  {companies.length === 0
                                    ? "No companies"
                                    : "Assign company…"}
                                </option>
                                {companies.map((c) => (
                                  <option key={c.id} value={c.id}>
                                    {c.name}
                                  </option>
                                ))}
                              </select>
                            </div>

                            {/* Certificate */}
                            <div className="flex items-center gap-1">
                              {(r.certs_count ?? 0) === 0 &&
                              !r.completion_date ? (
                                <button
                                  onClick={() => issueCertificate(r)}
                                  disabled={
                                    !r.enrollment_id || !!rowBusy[certKey]
                                  }
                                  className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-yellow-50 hover:bg-yellow-100 text-yellow-900 rounded border border-yellow-200 disabled:opacity-50"
                                  title={
                                    r.enrollment_id
                                      ? "Force completion and issue certificate"
                                      : "Student must redeem voucher first"
                                  }
                                >
                                  <Award className="w-3 h-3" /> Issue cert
                                </button>
                              ) : (r.certs_count ?? 0) > 0 ? (
                                <button
                                  onClick={() => revokeCertificate(r)}
                                  disabled={
                                    !r.issued_certificate_id ||
                                    !!rowBusy[certKey]
                                  }
                                  className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-red-50 hover:bg-red-100 text-red-800 rounded border border-red-200 disabled:opacity-50"
                                  title="Revoke certificate"
                                >
                                  <X className="w-3 h-3" /> Revoke
                                </button>
                              ) : (
                                <span className="text-xs text-gray-400">—</span>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Modal>
      )}
      {attendanceFor && rosterFor && (
        <Modal
          onClose={() => setAttendanceFor(null)}
          title={`Attendance — ${attendanceFor.buyer_name}`}
        >
          <div className="p-6 space-y-6">
            <form
              onSubmit={submitAttendance}
              className="grid md:grid-cols-4 gap-3 items-end bg-gray-50 border border-gray-200 rounded-md p-3"
            >
              <label className="block">
                <span className="block text-xs font-medium text-gray-700 mb-1">
                  Date
                </span>
                <input
                  type="date"
                  value={attForm.attended_at}
                  onChange={(e) =>
                    setAttForm({ ...attForm, attended_at: e.target.value })
                  }
                  required
                  className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded"
                />
              </label>
              <label className="block">
                <span className="block text-xs font-medium text-gray-700 mb-1">
                  Status
                </span>
                <select
                  value={attForm.status}
                  onChange={(e) =>
                    setAttForm({ ...attForm, status: e.target.value })
                  }
                  className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded"
                >
                  <option value="present">Present</option>
                  <option value="late">Late</option>
                  <option value="absent">Absent</option>
                  <option value="excused">Excused</option>
                </select>
              </label>
              <label className="block md:col-span-1">
                <span className="block text-xs font-medium text-gray-700 mb-1">
                  Notes
                </span>
                <input
                  type="text"
                  value={attForm.notes}
                  onChange={(e) =>
                    setAttForm({ ...attForm, notes: e.target.value })
                  }
                  placeholder="optional"
                  className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded"
                />
              </label>
              <button
                type="submit"
                className="px-3 py-1.5 bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-semibold text-sm rounded"
              >
                Save
              </button>
            </form>

            {attendanceLoading ? (
              <div className="text-center text-gray-500 py-6">Loading…</div>
            ) : !attendanceRows || attendanceRows.length === 0 ? (
              <div className="text-center text-gray-500 py-6">
                No attendance records yet.
              </div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <Th>Date</Th>
                    <Th>Status</Th>
                    <Th>Notes</Th>
                    <Th>Marked at</Th>
                    <Th> </Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {attendanceRows.map((rec) => (
                    <tr key={rec.id}>
                      <td className="px-4 py-2 text-gray-700">
                        {rec.attended_at}
                      </td>
                      <td className="px-4 py-2">
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            rec.status === "present"
                              ? "bg-green-100 text-green-800"
                              : rec.status === "late"
                                ? "bg-yellow-100 text-yellow-800"
                                : rec.status === "excused"
                                  ? "bg-blue-100 text-blue-800"
                                  : "bg-red-100 text-red-800"
                          }`}
                        >
                          {rec.status}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-600">
                        {rec.notes || "—"}
                      </td>
                      <td className="px-4 py-2 text-gray-500 text-xs">
                        {rec.updated_at
                          ? new Date(rec.updated_at).toLocaleString()
                          : "—"}
                      </td>
                      <td className="px-4 py-2">
                        <button
                          onClick={() => deleteAttendance(rec)}
                          className="text-red-600 hover:text-red-800"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Modal>
      )}
      {addStudentOpen && (
        <Modal
          onClose={() => setAddStudentOpen(false)}
          title="Add Student to Roster"
        >
          <form onSubmit={submitAddStudent} className="p-6 space-y-4">
            <p className="text-sm text-gray-600">
              Manually add a student to the internship roster. Use this for
              offline payments or special cases.
            </p>
            <label className="block">
              <span className="block text-sm font-medium text-gray-700 mb-1">
                Student <span className="text-red-600">*</span>
              </span>
              <select
                value={addStudentForm.user_id || ""}
                onChange={(e) =>
                  setAddStudentForm({
                    ...addStudentForm,
                    user_id: Number(e.target.value),
                  })
                }
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="">Select a student...</option>
                {students.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.display_name} ({s.email})
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="block text-sm font-medium text-gray-700 mb-1">
                Amount Paid (₹)
              </span>
              <input
                type="number"
                min={0}
                step={1}
                value={addStudentForm.amount_paid}
                onChange={(e) =>
                  setAddStudentForm({
                    ...addStudentForm,
                    amount_paid: Number(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="Leave 0 for unpaid/manual"
              />
            </label>
            <div className="flex justify-end gap-3 pt-2 border-t border-gray-200">
              <button
                type="button"
                onClick={() => setAddStudentOpen(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={addStudentSaving}
                className="px-4 py-2 bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-semibold rounded-md disabled:opacity-60"
              >
                {addStudentSaving ? "Adding..." : "Add Student"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </PageLayout>
  );
};

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
      {children}
    </th>
  );
}

function TextField({
  label,
  value,
  onChange,
  required,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <span className="block text-sm font-medium text-gray-700 mb-1">
        {label} {required && <span className="text-red-600">*</span>}
      </span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-300 rounded-md"
      />
    </label>
  );
}

/**
 * Portal host for every overlay on this page.
 *
 * The admin shell renders page content inside DashboardWorkspace's
 * `<main class="relative z-10">`, which opens a stacking context, and inside a
 * framer-motion transition wrapper, which sets a `transform` while animating.
 * Both trap a `position: fixed` overlay: the transform makes it position
 * against the content box instead of the viewport, and the z-10 context caps it
 * below the `z-40` fixed sidebar — which is exactly why the roster panel
 * appeared behind the workspace with most of it cut off. Rendering into
 * `document.body` escapes both.
 */
function Overlay({
  onClose,
  children,
  className = "",
}: {
  onClose?: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  // Escape closes; body scroll is locked so the page behind doesn't move.
  useEffect(() => {
    if (!onClose) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  return createPortal(
    <div
      className={`fixed inset-0 bg-black/40 flex items-start sm:items-center justify-center z-[100] p-4 overflow-y-auto ${className}`}
      role="dialog"
      aria-modal="true"
    >
      {children}
    </div>,
    document.body,
  );
}

function Modal({
  title,
  onClose,
  children,
  wide,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <Overlay onClose={onClose}>
      <div
        className={`bg-white rounded-lg shadow-xl w-full ${
          wide ? "max-w-6xl" : "max-w-3xl"
        } max-h-[90vh] my-auto flex flex-col`}
        data-glass="content"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0">
          <h2 className="text-lg font-bold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-900"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="overflow-auto flex-1">{children}</div>
      </div>
    </Overlay>
  );
}

export default AdminInternships;
