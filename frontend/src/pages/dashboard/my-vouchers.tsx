import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { Ticket, Copy, Briefcase } from "lucide-react";
import { internshipApi, MyVoucher } from "@/api/internship";

export const MyVouchersPage: React.FC = () => {
  const [vouchers, setVouchers] = useState<MyVoucher[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const data = await internshipApi.myVouchers();
        setVouchers(data || []);
      } catch (err: any) {
        toast.error(err?.response?.data?.detail || "Failed to load vouchers");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const copy = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      toast.success("Code copied");
    } catch {
      toast.error("Copy failed");
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Ticket className="w-7 h-7 text-yellow-500" />
            My Vouchers
          </h1>
          <p className="mt-1 text-gray-600">
            Vouchers issued from your paid internship enrollments. Use a voucher
            code at any course checkout to enrol free.
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-dashboard-my-vouchers"
    >
      {loading ? (
        <div className="text-center text-gray-500 py-12">Loading...</div>
      ) : vouchers.length === 0 ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-12 text-center">
          <Briefcase className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600 mb-3">No vouchers yet.</p>
          <p className="text-sm text-gray-500">
            Browse paid internships at{" "}
            <Link to="/internships" className="text-yellow-700 underline">
              /internships
            </Link>
            .
          </p>
        </div>
      ) : (
        <div
          className="bg-white border border-gray-200 rounded-lg overflow-hidden"
          data-glass="work"
        >
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Program
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Code
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Course Progress
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Issued
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Redeemed
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {vouchers.map((v) => {
                const isRedeemed =
                  v.status === "redeemed" || !!v.redeemed_course_id;
                return (
                  <tr key={v.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {v.internship_title}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="inline-flex items-center gap-2">
                        <code className="bg-gray-100 px-2 py-1 rounded font-mono text-xs">
                          {v.code}
                        </code>
                        <button
                          onClick={() => copy(v.code)}
                          className="text-gray-500 hover:text-gray-900"
                          title="Copy code"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {isRedeemed ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Redeemed
                          {v.redeemed_course_title && (
                            <span className="text-green-700">
                              {" "}
                              on “{v.redeemed_course_title}”
                            </span>
                          )}
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                          Issued
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {v.course_progress ? (
                        <div className="flex flex-col gap-1">
                          <span
                            className={
                              v.course_progress.is_completed
                                ? "text-green-700 font-medium"
                                : "text-gray-700"
                            }
                          >
                            {v.course_progress.is_completed
                              ? "Completed"
                              : `${v.course_progress.progress_percentage || 0}%`}
                          </span>
                          <div className="w-24 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className={
                                v.course_progress.is_completed
                                  ? "bg-green-500 h-full"
                                  : "bg-blue-500 h-full"
                              }
                              style={{
                                width: `${Math.min(100, v.course_progress.progress_percentage || 0)}%`,
                              }}
                            />
                          </div>
                        </div>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {v.created_at
                        ? new Date(v.created_at).toLocaleDateString()
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {v.redeemed_at
                        ? new Date(v.redeemed_at).toLocaleDateString()
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </PageLayout>
  );
};

export default MyVouchersPage;
