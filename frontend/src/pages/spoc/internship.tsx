import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, BookOpen, Award, Briefcase } from "lucide-react";
import toast from "react-hot-toast";
import {
  internshipApi,
  AdminInternshipRow,
  AdminRosterRow,
} from "@/api/internship";
import { ViewAsSpocBanner } from "@/components/spoc/ViewAsSpocBanner";

export const SpocInternshipDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const internshipId = Number(id);

  const [details, setDetails] = useState<AdminInternshipRow | null>(null);
  const [roster, setRoster] = useState<AdminRosterRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!internshipId) return;
    (async () => {
      try {
        // /spoc/my-internships returns the full list; find this one.
        const all = await internshipApi.spocMyInternships();
        const match = all.find((x) => x.id === internshipId);
        if (!match) {
          toast.error("Internship not assigned to you");
          return;
        }
        setDetails(match);
        setRoster(await internshipApi.spocRoster(internshipId));
      } catch (e: any) {
        toast.error(e?.response?.data?.detail || "Failed to load internship");
      } finally {
        setLoading(false);
      }
    })();
  }, [internshipId]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-10 text-gray-400">Loading…</div>
    );
  }

  if (!details) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-10">
        <Link
          to="/spoc/dashboard"
          className="text-indigo-600 inline-flex items-center gap-1 mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </Link>
        <div className="text-gray-500">Internship not found.</div>
      </div>
    );
  }

  return (
    <>
      <ViewAsSpocBanner />
      <PageLayout
        header={
          <PageHeader>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <Briefcase className="h-6 w-6" /> {details.title}
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                {details.vouchers_redeemed ?? 0} of{" "}
                {details.vouchers_issued ?? 0} vouchers redeemed
              </p>
            </div>
            <span
              className={`text-xs px-2 py-1 rounded-full ${
                details.is_published
                  ? "bg-green-50 text-green-700"
                  : "bg-gray-100 text-gray-500"
              }`}
            >
              {details.is_published ? "published" : "draft"}
            </span>
          </PageHeader>
        }
        className="rd-screen rd-screen-spoc-internship"
      >
        <Link
          to="/spoc/dashboard"
          className="text-indigo-600 inline-flex items-center gap-1 mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> All internships
        </Link>
        <div
          className="bg-white rounded-lg shadow border border-gray-100 overflow-hidden"
          data-glass="work"
        >
          <div className="px-5 py-3 border-b border-gray-100 bg-gray-50 text-sm font-medium text-gray-700">
            Student roster
          </div>
          {roster.length === 0 ? (
            <div className="p-10 text-center text-gray-400 text-sm">
              No voucher purchases yet.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-2 text-left">Student</th>
                  <th className="px-4 py-2 text-left">Voucher</th>
                  <th className="px-4 py-2 text-left">Course</th>
                  <th className="px-4 py-2 text-left">Progress</th>
                  <th className="px-4 py-2 text-left">Certs</th>
                  <th className="px-4 py-2 text-left">Hired by</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {roster.map((r) => (
                  <tr key={r.voucher_code} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">
                        {r.buyer_name}
                      </div>
                      <div className="text-xs text-gray-500">
                        {r.buyer_email}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <code className="bg-gray-100 px-2 py-0.5 rounded font-mono text-xs">
                        {r.voucher_code}
                      </code>
                      <span
                        className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
                          r.status === "redeemed"
                            ? "bg-green-50 text-green-700"
                            : "bg-amber-50 text-amber-700"
                        }`}
                      >
                        {r.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {r.redeemed_course_title ? (
                        <span className="inline-flex items-center gap-1">
                          <BookOpen className="h-3.5 w-3.5 text-gray-400" />
                          {r.redeemed_course_title}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">
                          Not redeemed
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {r.status === "issued" ? (
                        <span
                          className="text-gray-400 text-xs italic"
                          title="Voucher must be redeemed first"
                        >
                          Not enrolled
                        </span>
                      ) : r.redeemed_course_title ? (
                        <div className="flex items-center gap-2">
                          <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-indigo-500"
                              style={{
                                width: `${Math.min(100, r.progress_pct || 0)}%`,
                              }}
                            />
                          </div>
                          <span className="text-xs text-gray-600">
                            {r.progress_pct || 0}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-gray-400 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {r.certs_count ? (
                        <span
                          className="inline-flex items-center gap-1 text-sm"
                          title="Total certificates on platform"
                        >
                          <Award className="h-4 w-4 text-yellow-500" />{" "}
                          {r.certs_count}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs italic">
                          None
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {r.hired_by_company ? (
                        <span className="text-indigo-600 font-medium">
                          {r.hired_by_company}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs italic">
                          Not hired
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </PageLayout>
    </>
  );
};

export default SpocInternshipDetail;
