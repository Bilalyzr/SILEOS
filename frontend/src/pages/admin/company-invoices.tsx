import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback } from "react";
import React, { useState, useEffect } from "react";
import { confirmDialog, promptDialog } from "@/components/ui/confirm";
import { Plus, FileText, Receipt } from "lucide-react";
import { api } from "@/api/axios";
import { companyAPI, AdminCompanyRow } from "@/api/company";
import toast from "react-hot-toast";

type InvoiceStatus = "draft" | "issued" | "paid" | "cancelled";

interface InvoiceItem {
  id?: number;
  description: string;
  course_id: number | null;
  bundle_id: number | null;
  quantity: number;
  unit_price: number;
  line_total?: number;
}

interface AdminInvoice {
  id: number;
  invoice_number: string | null;
  company_id: number;
  company_name: string;
  status: InvoiceStatus;
  subtotal: number;
  cgst: number;
  sgst: number;
  igst: number;
  total: number;
  tax_note: string;
  due_date: string | null;
  issued_at: string | null;
  paid_at: string | null;
  paid_via: string;
  payment_reference: string;
  notes: string;
  items: InvoiceItem[];
}

const STATUS_FILTERS: { value: "" | InvoiceStatus; label: string }[] = [
  { value: "", label: "All" },
  { value: "draft", label: "Draft" },
  { value: "issued", label: "Issued" },
  { value: "paid", label: "Paid" },
  { value: "cancelled", label: "Cancelled" },
];

function StatusChip({ status }: { status: InvoiceStatus }) {
  const classes: Record<InvoiceStatus, string> = {
    draft: "bg-gray-100 text-gray-800",
    issued: "bg-blue-100 text-blue-800",
    paid: "bg-green-100 text-green-800",
    cancelled: "bg-red-100 text-red-800",
  };
  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded-full ${classes[status]}`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
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

async function downloadInvoicePdf(
  invoiceId: number,
  filename?: string,
): Promise<void> {
  const { data } = await api.get(`/admin/company-invoices/${invoiceId}/pdf`, {
    responseType: "blob",
  });
  const blob = new Blob([data], { type: "application/pdf" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || `invoice-${invoiceId}.pdf`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

export function CompanyInvoicesPage() {
  const [invoices, setInvoices] = useState<AdminInvoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<"" | InvoiceStatus>("");
  const [showFormModal, setShowFormModal] = useState(false);
  const [editingInvoice, setEditingInvoice] = useState<AdminInvoice | null>(
    null,
  );

  const fetchInvoices = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get("/admin/company-invoices", {
        params: statusFilter ? { status: statusFilter } : undefined,
      });
      setInvoices(response.data || []);
    } catch (error: any) {
      console.error("Error fetching invoices:", error);
      toast.error("Failed to fetch invoices");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);
  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices, statusFilter]);

  const handleIssue = async (invoice: AdminInvoice) => {
    if (
      !(await confirmDialog(
        `Issue invoice for ${invoice.company_name}? This computes GST and locks the line items.`,
      ))
    ) {
      return;
    }
    try {
      await api.post(`/admin/company-invoices/${invoice.id}/issue`);
      toast.success("Invoice issued");
      fetchInvoices();
    } catch (error: any) {
      console.error("Error issuing invoice:", error);
      toast.error(error.response?.data?.detail || "Failed to issue invoice");
    }
  };

  const handleCancel = async (invoice: AdminInvoice) => {
    if (
      !(await confirmDialog(
        `Cancel invoice ${invoice.invoice_number || `#${invoice.id}`}?`,
      ))
    ) {
      return;
    }
    try {
      await api.post(`/admin/company-invoices/${invoice.id}/cancel`);
      toast.success("Invoice cancelled");
      fetchInvoices();
    } catch (error: any) {
      console.error("Error cancelling invoice:", error);
      toast.error(error.response?.data?.detail || "Failed to cancel invoice");
    }
  };

  const handleMarkPaid = async (invoice: AdminInvoice) => {
    const reference = await promptDialog(
      "Payment reference (bank transfer ref, cheque no., etc.):",
    );
    if (!reference || !reference.trim()) return;
    try {
      await api.post(`/admin/company-invoices/${invoice.id}/mark-paid`, {
        reference: reference.trim(),
      });
      toast.success("Invoice marked as paid");
      fetchInvoices();
    } catch (error: any) {
      console.error("Error marking invoice paid:", error);
      toast.error(
        error.response?.data?.detail || "Failed to mark invoice paid",
      );
    }
  };

  const handleDownloadPdf = async (invoice: AdminInvoice) => {
    try {
      await downloadInvoicePdf(
        invoice.id,
        `${invoice.invoice_number || `invoice-${invoice.id}`}.pdf`,
      );
    } catch (error: any) {
      console.error("Error downloading PDF:", error);
      toast.error("Failed to download invoice PDF");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <PageLayout
        header={
          <PageHeader>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Company Invoices
              </h1>
              <p className="text-gray-600">
                Create and manage admin-negotiated GST invoices for companies
              </p>
            </div>
          </PageHeader>
        }
        className="rd-screen rd-screen-admin-company-invoices"
      >
        <div
          className="bg-white rounded-lg shadow p-6 mb-6"
          data-glass="content"
        >
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              {STATUS_FILTERS.map((f) => (
                <button
                  key={f.value || "all"}
                  onClick={() => setStatusFilter(f.value)}
                  className={`px-3 py-1.5 text-sm rounded-lg ${
                    statusFilter === f.value
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <button
              onClick={() => setShowFormModal(true)}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <Plus className="w-5 h-5" />
              New Invoice
            </button>
          </div>
        </div>
        <div
          className="bg-white rounded-lg shadow overflow-hidden mb-8"
          data-glass="work"
        >
          {loading ? (
            <div className="p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading invoices...</p>
            </div>
          ) : invoices.length === 0 ? (
            <div className="p-12 text-center">
              <Receipt className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-xl text-gray-600 mb-2">No invoices found</p>
              <p className="text-gray-500">
                Create your first invoice to get started
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Number
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Company
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Total
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Issued
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {invoices.map((invoice) => (
                    <tr key={invoice.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-bold text-gray-900">
                          {invoice.invoice_number || "—"}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {invoice.company_name}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          ₹{invoice.total.toFixed(2)}
                        </div>
                        <div className="text-xs text-gray-500">
                          {invoice.tax_note}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <StatusChip status={invoice.status} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {fmtDate(invoice.issued_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex items-center justify-end gap-3">
                          {invoice.status === "draft" && (
                            <>
                              <button
                                onClick={() => {
                                  setEditingInvoice(invoice);
                                  setShowFormModal(true);
                                }}
                                className="text-blue-600 hover:text-blue-900"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleIssue(invoice)}
                                className="text-green-600 hover:text-green-900"
                              >
                                Issue
                              </button>
                            </>
                          )}
                          {invoice.status === "issued" && (
                            <>
                              <button
                                onClick={() => handleMarkPaid(invoice)}
                                className="text-green-600 hover:text-green-900"
                              >
                                Mark paid
                              </button>
                              <button
                                onClick={() => handleCancel(invoice)}
                                className="text-red-600 hover:text-red-900"
                              >
                                Cancel
                              </button>
                            </>
                          )}
                          {invoice.status !== "draft" && (
                            <button
                              onClick={() => handleDownloadPdf(invoice)}
                              className="text-gray-600 hover:text-gray-900 flex items-center gap-1"
                            >
                              <FileText className="w-4 h-4" />
                              PDF
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </PageLayout>

      {/* Create/Edit Modal */}
      {showFormModal && (
        <InvoiceFormModal
          invoice={editingInvoice}
          onClose={() => {
            setShowFormModal(false);
            setEditingInvoice(null);
          }}
          onSuccess={() => {
            setShowFormModal(false);
            setEditingInvoice(null);
            fetchInvoices();
          }}
        />
      )}
    </div>
  );
}

// Invoice Form Modal Component
interface InvoiceFormModalProps {
  invoice: AdminInvoice | null;
  onClose: () => void;
  onSuccess: () => void;
}

interface PickerCourse {
  id: number;
  title: string;
  price?: number;
}

interface PickerBundle {
  id: number;
  name: string;
  bundle_price?: number;
}

function emptyItem(): InvoiceItem {
  return {
    description: "",
    course_id: null,
    bundle_id: null,
    quantity: 1,
    unit_price: 0,
  };
}

function InvoiceFormModal({
  invoice,
  onClose,
  onSuccess,
}: InvoiceFormModalProps) {
  const [companyId, setCompanyId] = useState<number | "">(
    invoice?.company_id || "",
  );
  const [dueDate, setDueDate] = useState(
    invoice?.due_date ? invoice.due_date.slice(0, 10) : "",
  );
  const [notes, setNotes] = useState(invoice?.notes || "");
  const [items, setItems] = useState<InvoiceItem[]>(
    invoice?.items?.length
      ? invoice.items.map((i) => ({
          id: i.id,
          description: i.description,
          course_id: i.course_id,
          bundle_id: i.bundle_id,
          quantity: i.quantity,
          unit_price: i.unit_price,
        }))
      : [emptyItem()],
  );

  const [companies, setCompanies] = useState<AdminCompanyRow[]>([]);
  const [courses, setCourses] = useState<PickerCourse[]>([]);
  const [bundles, setBundles] = useState<PickerBundle[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchCompanies();
    fetchCourses();
    fetchBundles();
  }, []);

  const fetchCompanies = async () => {
    try {
      const res = await companyAPI.adminListAll({
        status: "active",
        limit: 200,
      });
      setCompanies(res.items);
    } catch (error) {
      console.error("Error fetching companies:", error);
    }
  };

  const fetchCourses = async () => {
    try {
      const response = await api.get("/courses/", {
        params: { page: 1, page_size: 100 },
      });
      setCourses(response.data.courses || []);
    } catch (error) {
      console.error("Error fetching courses:", error);
    }
  };

  const fetchBundles = async () => {
    try {
      const response = await api.get("/admin/bundles");
      setBundles(response.data || []);
    } catch (error) {
      console.error("Error fetching bundles:", error);
    }
  };

  const updateItem = (index: number, patch: Partial<InvoiceItem>) => {
    setItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    );
  };

  const addItem = () => setItems((prev) => [...prev, emptyItem()]);
  const removeItem = (index: number) =>
    setItems((prev) => prev.filter((_, i) => i !== index));

  const lineTotal = (item: InvoiceItem) =>
    (item.quantity || 0) * (item.unit_price || 0);
  const subtotal = items.reduce((sum, item) => sum + lineTotal(item), 0);

  const itemsValid =
    items.length > 0 &&
    items.every(
      (item) =>
        item.description.trim().length > 0 &&
        item.quantity >= 1 &&
        item.unit_price > 0,
    );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!companyId) {
      toast.error("Select a company");
      return;
    }
    if (!itemsValid) {
      toast.error(
        "Every line item needs a description, quantity ≥ 1, and unit price > 0",
      );
      return;
    }

    const payloadItems = items.map((item) => ({
      description: item.description.trim(),
      course_id: item.course_id ?? undefined,
      bundle_id: item.bundle_id ?? undefined,
      quantity: item.quantity,
      unit_price: item.unit_price,
    }));

    setLoading(true);
    try {
      if (invoice) {
        await api.patch(`/admin/company-invoices/${invoice.id}`, {
          due_date: dueDate || undefined,
          notes,
          items: payloadItems,
        });
        toast.success("Invoice updated");
      } else {
        await api.post("/admin/company-invoices", {
          company_id: companyId,
          due_date: dueDate || undefined,
          notes,
          items: payloadItems,
        });
        toast.success("Invoice created");
      }
      onSuccess();
    } catch (error: any) {
      console.error("Error saving invoice:", error);
      toast.error(error.response?.data?.detail || "Failed to save invoice");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-modal p-4">
      <div
        className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto"
        data-glass="work"
      >
        <div className="p-6">
          <h2 className="text-2xl font-bold mb-6">
            {invoice ? "Edit Invoice (Draft)" : "New Invoice"}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Company */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Company *
              </label>
              <select
                required
                disabled={!!invoice}
                value={companyId}
                onChange={(e) =>
                  setCompanyId(e.target.value ? Number(e.target.value) : "")
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              >
                <option value="">Select a company…</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              {invoice && (
                <p className="text-xs text-gray-500 mt-1">
                  {invoice.company_name}
                </p>
              )}
            </div>

            {/* Due date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Due date
              </label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Notes */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Notes
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                rows={2}
                placeholder="Internal notes shown on the invoice"
              />
            </div>

            {/* Line items */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">
                  Line items *
                </label>
                <button
                  type="button"
                  onClick={addItem}
                  className="text-sm text-blue-600 hover:text-blue-900 flex items-center gap-1"
                >
                  <Plus className="w-4 h-4" />
                  Add item
                </button>
              </div>

              <div className="space-y-3">
                {items.map((item, index) => (
                  <div
                    key={index}
                    className="border border-gray-200 rounded-lg p-3 space-y-2"
                  >
                    <div className="flex items-start gap-2">
                      <input
                        type="text"
                        required
                        placeholder="Description"
                        value={item.description}
                        onChange={(e) =>
                          updateItem(index, { description: e.target.value })
                        }
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                      />
                      {items.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeItem(index)}
                          className="text-red-600 hover:text-red-900 text-sm px-2 py-2"
                        >
                          Remove
                        </button>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-xs text-gray-500 mb-0.5">
                          Course (optional)
                        </label>
                        <select
                          value={item.course_id ?? ""}
                          disabled={!!item.bundle_id}
                          onChange={(e) =>
                            updateItem(index, {
                              course_id: e.target.value
                                ? Number(e.target.value)
                                : null,
                            })
                          }
                          className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm disabled:bg-gray-100"
                        >
                          <option value="">None</option>
                          {courses.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.title}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-0.5">
                          Bundle (optional)
                        </label>
                        <select
                          value={item.bundle_id ?? ""}
                          disabled={!!item.course_id}
                          onChange={(e) =>
                            updateItem(index, {
                              bundle_id: e.target.value
                                ? Number(e.target.value)
                                : null,
                            })
                          }
                          className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm disabled:bg-gray-100"
                        >
                          <option value="">None</option>
                          {bundles.map((b) => (
                            <option key={b.id} value={b.id}>
                              {b.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 items-end">
                      <div>
                        <label className="block text-xs text-gray-500 mb-0.5">
                          Qty
                        </label>
                        <input
                          type="number"
                          required
                          min="1"
                          step="1"
                          value={item.quantity}
                          onChange={(e) =>
                            updateItem(index, {
                              quantity: parseInt(e.target.value, 10) || 0,
                            })
                          }
                          className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-0.5">
                          Unit price (₹)
                        </label>
                        <input
                          type="number"
                          required
                          min="0.01"
                          step="0.01"
                          value={item.unit_price}
                          onChange={(e) =>
                            updateItem(index, {
                              unit_price: parseFloat(e.target.value) || 0,
                            })
                          }
                          className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm"
                        />
                      </div>
                      <div className="text-sm text-gray-700 pb-1.5">
                        Line total:{" "}
                        <span className="font-medium">
                          ₹{lineTotal(item).toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between mt-3 px-1">
                <p className="text-xs text-gray-500">
                  GST is computed when the invoice is issued.
                </p>
                <p className="text-sm font-medium text-gray-900">
                  Subtotal: ₹{subtotal.toFixed(2)}
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {loading
                  ? "Saving..."
                  : invoice
                    ? "Update Invoice"
                    : "Create Invoice"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
