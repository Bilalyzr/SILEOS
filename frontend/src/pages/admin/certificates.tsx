import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useState, useEffect } from "react";
import { confirmDialog, promptDialog } from "@/components/ui/confirm";
import { Link } from "react-router-dom";
import {
  Search,
  Award,
  Download,
  Eye,
  Calendar,
  Users,
  CheckCircle,
  FileImage,
  Ban,
  PlusCircle,
} from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/api/axios";
import { internshipApi } from "@/api/internship";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";
import { TemplateGallery } from "@/components/certificates/designer/TemplateGallery";
import { CertificateDesignerEditor } from "@/components/certificates/designer/CertificateDesignerEditor";
import { listDesignerTemplates, errorDetail } from "@/api/certificateDesigner";
import type { DesignerTemplate } from "@/lib/certificateDesignerTypes";

interface Certificate {
  id: number;
  student_name: string;
  student_email: string;
  course_title: string;
  course_id: number;
  certificate_id: string;
  secure_certificate_id?: string;
  certificate_hash?: string;
  issue_date: string;
  completion_date: string;
  grade: number;
}

export const AdminCertificates: React.FC = () => {
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeSection, setActiveSection] = useState<"issued" | "templates">(
    "issued",
  );

  const [templates, setTemplates] = useState<DesignerTemplate[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(true);
  const [templatesError, setTemplatesError] = useState<string | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<
    DesignerTemplate | null | "new"
  >(null);
  const [busyCertId, setBusyCertId] = useState<number | null>(null);
  const [issuing, setIssuing] = useState(false);

  const loadTemplates = async () => {
    try {
      setTemplatesLoading(true);
      setTemplatesError(null);
      const data = await listDesignerTemplates();
      setTemplates(data);
    } catch (err) {
      setTemplatesError(
        errorDetail(err, "Failed to load certificate templates"),
      );
    } finally {
      setTemplatesLoading(false);
    }
  };

  useEffect(() => {
    fetchCertificates();
    loadTemplates();
  }, []);

  const fetchCertificates = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/admin/certificates?limit=100`);
      const data = response.data;
      setCertificates(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error fetching certificates:", error);
      setCertificates([]);
    } finally {
      setLoading(false);
    }
  };

  // A-H5: revoke/issue actions. Both backend routes already existed
  // (certificates.py:1790 issue, :1838 revoke) — the only UI callers were
  // on the Internships roster page (internships.tsx:316,336); this page
  // had none. Reuses the exact same internshipApi client functions.
  const handleRevoke = async (certificateId: number) => {
    const reason = await promptDialog("Reason for revoking this certificate:");
    if (!reason || !reason.trim()) return;
    if (
      !(await confirmDialog("Revoke this certificate? This cannot be undone."))
    )
      return;
    setBusyCertId(certificateId);
    try {
      await internshipApi.adminRevokeCert(certificateId, reason.trim());
      toast.success("Certificate revoked");
      fetchCertificates();
    } catch (err: any) {
      toast.error(
        err?.response?.data?.detail || "Failed to revoke certificate",
      );
    } finally {
      setBusyCertId(null);
    }
  };

  const handleIssueForEnrollment = async () => {
    const raw = await promptDialog(
      "Enrollment ID to issue a certificate for:",
      "",
      { placeholder: "e.g. 42", required: true, confirmLabel: "Issue" },
    );
    if (!raw || !raw.trim()) return;
    const enrollmentId = Number(raw.trim());
    if (!Number.isFinite(enrollmentId) || enrollmentId <= 0) {
      toast.error("Enter a valid enrollment ID");
      return;
    }
    const forceCompletion = await confirmDialog(
      "Force-complete this enrollment before issuing (OK), or only issue if already completed (Cancel)?",
    );
    setIssuing(true);
    try {
      await internshipApi.adminIssueCertForEnrollment(
        enrollmentId,
        forceCompletion,
      );
      toast.success("Certificate issued");
      fetchCertificates();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to issue certificate");
    } finally {
      setIssuing(false);
    }
  };

  const filteredCertificates = certificates.filter(
    (cert) =>
      cert.student_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cert.course_title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cert.certificate_id.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const stats = {
    total: certificates.length,
    thisMonth: certificates.filter((c) => {
      const issueDate = new Date(c.issue_date);
      const now = new Date();
      return (
        issueDate.getMonth() === now.getMonth() &&
        issueDate.getFullYear() === now.getFullYear()
      );
    }).length,
    avgGrade:
      certificates.length > 0
        ? Math.round(
            certificates.reduce((sum, c) => sum + c.grade, 0) /
              certificates.length,
          )
        : 0,
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Certificates</h1>
            <p className="text-gray-600 mt-1">
              Manage certificates and templates
            </p>
          </div>
          <ExportImportPanel section="certificates" />
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-certificates"
    >
      <div className="border-b border-gray-200">
        <nav className="flex gap-6">
          <button
            onClick={() => setActiveSection("issued")}
            className={`pb-4 px-1 font-medium transition-colors ${
              activeSection === "issued"
                ? "text-blue-600 border-b-2 border-blue-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <div className="flex items-center gap-2">
              <Award size={18} />
              Issued Certificates ({stats.total})
            </div>
          </button>
          <button
            onClick={() => setActiveSection("templates")}
            className={`pb-4 px-1 font-medium transition-colors ${
              activeSection === "templates"
                ? "text-blue-600 border-b-2 border-blue-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <div className="flex items-center gap-2">
              <FileImage size={18} />
              Certificate Templates
            </div>
          </button>
        </nav>
      </div>
      {activeSection === "issued" && (
        <>
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div
              className="bg-white rounded-lg border border-gray-200 p-4"
              data-glass="content"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Certificates</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {stats.total}
                  </p>
                </div>
                <Award className="w-8 h-8 text-blue-600" />
              </div>
            </div>
            <div
              className="bg-white rounded-lg border border-gray-200 p-4"
              data-glass="content"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">This Month</p>
                  <p className="text-2xl font-bold text-green-600 mt-1">
                    {stats.thisMonth}
                  </p>
                </div>
                <Calendar className="w-8 h-8 text-green-600" />
              </div>
            </div>
            <div
              className="bg-white rounded-lg border border-gray-200 p-4"
              data-glass="content"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Avg Grade</p>
                  <p className="text-2xl font-bold text-purple-600 mt-1">
                    {stats.avgGrade}%
                  </p>
                </div>
                <CheckCircle className="w-8 h-8 text-purple-600" />
              </div>
            </div>
            <div
              className="bg-white rounded-lg border border-gray-200 p-4"
              data-glass="content"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Unique Students</p>
                  <p className="text-2xl font-bold text-orange-600 mt-1">
                    {new Set(certificates.map((c) => c.student_email)).size}
                  </p>
                </div>
                <Users className="w-8 h-8 text-orange-600" />
              </div>
            </div>
          </div>

          {/* Search + manual issue */}
          <div
            className="bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-between gap-4 flex-wrap"
            data-glass="work"
          >
            <div className="relative max-w-md flex-1 min-w-[240px]">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search certificates..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <button
              onClick={handleIssueForEnrollment}
              disabled={issuing}
              className="inline-flex items-center gap-2 px-4 py-2 border border-green-300 text-green-700 rounded-lg hover:bg-green-50 text-sm font-medium disabled:opacity-50"
            >
              <PlusCircle className="w-4 h-4" />
              {issuing ? "Issuing…" : "Issue certificate for enrollment"}
            </button>
          </div>

          {/* Certificates Table */}
          <div
            className="bg-white rounded-lg border border-gray-200 overflow-hidden"
            data-glass="work"
          >
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Certificate ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Student
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Course
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Completion Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Issue Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Grade
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {loading ? (
                    <tr>
                      <td
                        colSpan={7}
                        className="px-6 py-12 text-center text-gray-500"
                      >
                        Loading certificates...
                      </td>
                    </tr>
                  ) : filteredCertificates.length === 0 ? (
                    <tr>
                      <td
                        colSpan={7}
                        className="px-6 py-12 text-center text-gray-500"
                      >
                        <div className="flex flex-col items-center space-y-3">
                          <Award className="w-12 h-12 text-gray-400" />
                          <p>No certificates issued yet</p>
                          <p className="text-sm text-gray-400">
                            Certificates are automatically issued when students
                            complete courses
                          </p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredCertificates.map((certificate) => (
                      <tr key={certificate.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <Award className="w-5 h-5 text-yellow-500 mr-2" />
                            <div className="text-sm font-medium text-gray-900">
                              {certificate.certificate_id}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {certificate.student_name}
                            </div>
                            <div className="text-sm text-gray-500">
                              {certificate.student_email}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <Link
                            to={`/courses/${certificate.course_id}`}
                            className="text-sm text-blue-600 hover:text-blue-800 line-clamp-2"
                          >
                            {certificate.course_title}
                          </Link>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center text-sm text-gray-500">
                            <Calendar className="w-4 h-4 mr-2" />
                            {formatDate(certificate.completion_date)}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center text-sm text-gray-500">
                            <Calendar className="w-4 h-4 mr-2" />
                            {formatDate(certificate.issue_date)}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="w-16">
                              <div className="text-sm font-medium text-gray-900">
                                {certificate.grade}%
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-1.5 mt-1">
                                <div
                                  className={`h-1.5 rounded-full ${
                                    certificate.grade >= 90
                                      ? "bg-green-600"
                                      : certificate.grade >= 75
                                        ? "bg-blue-600"
                                        : "bg-yellow-600"
                                  }`}
                                  style={{ width: `${certificate.grade}%` }}
                                ></div>
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => {
                                const verifyUrl =
                                  certificate.secure_certificate_id &&
                                  certificate.certificate_hash
                                    ? `/api/v1/certificates/verify-certificate?id=${certificate.secure_certificate_id}&hash=${certificate.certificate_hash}`
                                    : `/certificates/view/${certificate.id}`;
                                window.open(verifyUrl, "_blank");
                              }}
                              className="text-blue-600 hover:text-blue-900"
                              title="View Certificate"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => {
                                const downloadUrl =
                                  certificate.secure_certificate_id &&
                                  certificate.certificate_hash
                                    ? `/api/v1/certificates/download-html-pdf/${certificate.secure_certificate_id}/${certificate.certificate_hash}.pdf`
                                    : `/api/v1/certificates/download/${certificate.id}`;
                                window.open(downloadUrl, "_blank");
                              }}
                              className="text-green-600 hover:text-green-900"
                              title="Download PDF"
                            >
                              <Download className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleRevoke(certificate.id)}
                              disabled={busyCertId === certificate.id}
                              className="text-red-600 hover:text-red-900 disabled:opacity-50"
                              title="Revoke certificate"
                            >
                              <Ban className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
      {activeSection === "templates" &&
        (editingTemplate !== null ? (
          <CertificateDesignerEditor
            template={editingTemplate === "new" ? null : editingTemplate}
            isAdmin
            onCancel={() => setEditingTemplate(null)}
            onSaved={(saved) => {
              setEditingTemplate(null);
              loadTemplates();
              setTemplates((prev) => {
                const exists = prev.some((t) => t.id === saved.id);
                return exists
                  ? prev.map((t) => (t.id === saved.id ? saved : t))
                  : [saved, ...prev];
              });
            }}
          />
        ) : templatesError ? (
          <div
            className="bg-white rounded-lg border border-gray-200 p-8 text-center"
            data-glass="content"
          >
            <p className="text-sm text-red-600 mb-3">{templatesError}</p>
            <button
              onClick={loadTemplates}
              className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            >
              Try again
            </button>
          </div>
        ) : (
          <TemplateGallery
            templates={templates}
            loading={templatesLoading}
            onCreateNew={() => setEditingTemplate("new")}
            onEdit={(t) => setEditingTemplate(t)}
            onChanged={loadTemplates}
            isAdmin
          />
        ))}
    </PageLayout>
  );
};
