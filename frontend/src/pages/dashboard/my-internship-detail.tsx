import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Briefcase,
  CheckCircle2,
  Clock,
  PlayCircle,
  Calendar,
  Ticket,
} from "lucide-react";
import toast from "react-hot-toast";
import { internshipApi, type MyVoucher } from "@/api/internship";
import { DashboardShell } from "@/components/dashboard/primitives";

export const MyInternshipDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [voucher, setVoucher] = useState<MyVoucher | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    (async () => {
      try {
        setLoading(true);
        // Fetch my vouchers and find the one matching this slug
        const vouchers = await internshipApi.myVouchers();
        const found = vouchers.find((v) => v.internship_slug === slug);
        if (found) {
          setVoucher(found);
        } else {
          toast.error("Internship enrollment not found");
        }
      } catch (err: any) {
        console.error("Error fetching internship details:", err);
        toast.error("Failed to load internship details");
      } finally {
        setLoading(false);
      }
    })();
  }, [slug]);

  if (loading) {
    return (
      <DashboardShell>
        <div className="flex items-center justify-center min-h-[50vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
        </div>
      </DashboardShell>
    );
  }

  if (!voucher) {
    return (
      <DashboardShell>
        <div className="text-center py-12">
          <p className="text-gray-500">Internship enrollment not found</p>
          <Link
            to="/dashboard/my-internships"
            className="text-orange-600 hover:underline mt-4 inline-block"
          >
            Back to my internships
          </Link>
        </div>
      </DashboardShell>
    );
  }

  const isRedeemed =
    voucher.status === "redeemed" || voucher.redeemed_course_id;

  return (
    <DashboardShell>
      <div className="max-w-4xl mx-auto">
        <Link
          to="/dashboard/my-internships"
          className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> Back to my internships
        </Link>

        <div
          className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
          data-glass="content"
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-orange-500 to-amber-500 px-6 py-8 text-white">
            <h1 className="text-2xl font-bold">{voucher.internship_title}</h1>
            <div className="flex items-center gap-4 mt-2 text-orange-100">
              <span className="flex items-center gap-1 text-sm">
                <Briefcase className="w-4 h-4" />
                Voucher: {voucher.code}
              </span>
              {isRedeemed && (
                <span className="flex items-center gap-1 text-sm bg-green-500 px-2 py-1 rounded-full">
                  <CheckCircle2 className="w-3 h-3" /> Enrolled
                </span>
              )}
              {!isRedeemed && (
                <span className="flex items-center gap-1 text-sm bg-yellow-500 px-2 py-1 rounded-full">
                  <Clock className="w-3 h-3" /> Not Enrolled
                </span>
              )}
            </div>
          </div>

          {/* Details */}
          <div className="p-6 space-y-6">
            {/* Company Allocation */}
            {voucher.company_name && (
              <div className="flex items-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <Briefcase className="w-5 h-5 text-blue-600" />
                <div>
                  <p className="text-sm text-gray-600">Allocated Company</p>
                  <p className="font-semibold text-gray-900">
                    {voucher.company_name}
                  </p>
                </div>
              </div>
            )}

            {/* Course Enrollment */}
            {voucher.redeemed_course_id ? (
              <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
                <PlayCircle className="w-5 h-5 text-green-600" />
                <div className="flex-1">
                  <p className="text-sm text-gray-600">Enrolled Course</p>
                  <p className="font-semibold text-gray-900">
                    {voucher.redeemed_course_title || "Course"}
                  </p>
                </div>
                <Link
                  to={`/courses/${voucher.redeemed_course_id}/learn`}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium"
                >
                  Continue Learning
                </Link>
              </div>
            ) : (
              <div className="flex items-center gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <Clock className="w-5 h-5 text-amber-600" />
                <div className="flex-1">
                  <p className="text-sm text-gray-600">Course Enrollment</p>
                  <p className="font-medium text-gray-900">
                    Voucher not yet redeemed for any course
                  </p>
                </div>
                <Link
                  to="/courses"
                  className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 text-sm font-medium"
                >
                  Browse Courses
                </Link>
              </div>
            )}

            {/* Attendance */}
            {isRedeemed && (
              <div className="flex items-center gap-3 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                <Ticket className="w-5 h-5 text-purple-600" />
                <div>
                  <p className="text-sm text-gray-600">Attendance</p>
                  <p className="font-semibold text-gray-900">
                    {voucher.attendance_count ?? 0} days attended
                  </p>
                </div>
              </div>
            )}

            {/* Dates */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 flex items-center gap-1">
                  <Calendar className="w-4 h-4" /> Purchased
                </p>
                <p className="font-medium text-gray-900">
                  {new Date(voucher.created_at).toLocaleDateString()}
                </p>
              </div>
              {voucher.redeemed_at && (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600 flex items-center gap-1">
                    <CheckCircle2 className="w-4 h-4" /> Redeemed
                  </p>
                  <p className="font-medium text-gray-900">
                    {new Date(voucher.redeemed_at).toLocaleDateString()}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
};

export default MyInternshipDetailPage;
