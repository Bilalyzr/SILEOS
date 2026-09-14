import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React from "react";
import { api } from "@/api/axios";
import toast from "react-hot-toast";
import { CheckCircle, RotateCcw, Award } from "lucide-react";

interface PendingSub {
  submission_id: number;
  student_name: string;
  course_title: string;
  assignment_title: string;
  submitted_at: string | null;
  blocks_certificate: boolean;
}

export const AdminApprovals: React.FC = () => {
  const [rows, setRows] = React.useState<PendingSub[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setRows(
        (await api.get("/admin/pending-submissions")).data.submissions || [],
      );
    } catch {
      setRows([]);
    } finally {
      setLoading(false);
    }
  };
  React.useEffect(() => {
    load();
  }, []);

  const approve = async (id: number) => {
    setBusy(id);
    try {
      await api.post(`/submissions/${id}/grade`, {
        grade: 100,
        feedback: "Approved",
      });
      toast.success("Approved");
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to approve");
    } finally {
      setBusy(null);
    }
  };

  const reject = async (id: number) => {
    setBusy(id);
    try {
      await api.post(`/submissions/${id}/return`, {
        feedback: "Please revise and resubmit",
      });
      toast.success("Returned to student");
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to return");
    } finally {
      setBusy(null);
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="text-3xl font-bold text-gray-900">Approvals</h1>
          <p className="text-gray-600 mt-1">
            Pending assignment submissions across all courses
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-approvals"
    >
      <div
        className="bg-white rounded-lg border border-gray-200 overflow-hidden"
        data-glass="work"
      >
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {[
                  "Student",
                  "Course",
                  "Assignment",
                  "Submitted",
                  "Actions",
                ].map((h) => (
                  <th
                    key={h}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    Loading…
                  </td>
                </tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-6 py-12 text-center text-gray-500"
                  >
                    No pending submissions
                  </td>
                </tr>
              ) : (
                rows.map((r) => (
                  <tr key={r.submission_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {r.student_name}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {r.course_title}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {r.assignment_title}
                      {r.blocks_certificate && (
                        <span className="ml-2 inline-flex items-center gap-1 text-xs text-amber-700">
                          <Award className="w-3 h-3" /> blocks certificate
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {r.submitted_at
                        ? new Date(r.submitted_at).toLocaleDateString()
                        : "—"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => approve(r.submission_id)}
                          disabled={busy === r.submission_id}
                          title="Approve (issues certificate when it's the last one)"
                          className="p-2 rounded-lg text-green-600 hover:bg-green-50 disabled:opacity-50"
                        >
                          <CheckCircle className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => reject(r.submission_id)}
                          disabled={busy === r.submission_id}
                          title="Return to student"
                          className="p-2 rounded-lg text-amber-600 hover:bg-amber-50 disabled:opacity-50"
                        >
                          <RotateCcw className="w-4 h-4" />
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
    </PageLayout>
  );
};
