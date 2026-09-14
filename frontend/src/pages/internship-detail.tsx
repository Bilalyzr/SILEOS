import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { PageBanner } from "@/components/design-system/PageBanner";
import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import toast from "react-hot-toast";
import { ArrowLeft, Check, Copy, Loader2 } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useSEO } from "@/hooks/use-seo";
import {
  internshipApi,
  purchaseAndVerify,
  PublicInternship,
} from "@/api/internship";

export const InternshipDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();

  const [internship, setInternship] = useState<PublicInternship | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [voucherCode, setVoucherCode] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    (async () => {
      try {
        setLoading(true);
        const data = await internshipApi.getBySlug(slug);
        setInternship(data);
      } catch (err: any) {
        toast.error(err?.response?.data?.detail || "Internship not found");
      } finally {
        setLoading(false);
      }
    })();
  }, [slug]);

  // SEO / Open Graph meta tags for internship page
  useSEO(
    internship
      ? {
          title: internship.title,
          description:
            internship.description?.replace(/<[^>]*>/g, "").slice(0, 160) ||
            `Apply for ${internship.title} internship program at SashaInfinity`,
          image: internship.cover_image,
          url: `${window.location.origin}/internships/${internship.slug}`,
          type: "website",
        }
      : {},
  );

  const handleEnroll = async () => {
    if (!internship) return;
    if (!isAuthenticated) {
      navigate(`/login?redirect=${encodeURIComponent(`/internships/${slug}`)}`);
      return;
    }
    try {
      setProcessing(true);
      const voucher = await purchaseAndVerify(internship.id, {
        prefill: {
          name: user?.display_name || "",
          email: (user as any)?.user_email || (user as any)?.email || "",
        },
      });
      setVoucherCode(voucher.code);
      toast.success("Payment successful! Voucher issued.");
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        "Payment failed";
      toast.error(msg);
    } finally {
      setProcessing(false);
    }
  };

  const copyCode = async () => {
    if (!voucherCode) return;
    try {
      await navigator.clipboard.writeText(voucherCode);
      toast.success("Voucher code copied");
    } catch {
      toast.error("Copy failed — select and copy manually");
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-10 text-gray-500">
        Loading...
      </div>
    );
  }
  if (!internship) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-10">
        <p className="text-gray-500">Internship not found.</p>
        <Link to="/internships" className="text-yellow-600 hover:underline">
          Back to internships
        </Link>
      </div>
    );
  }

  // ---------- Success view (voucher issued) ----------
  if (voucherCode) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-10">
        <PageLayout
          header={
            <PageHeader>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Enrollment successful!
                </h1>
                <p className="mt-2 text-gray-600">
                  Your voucher has been issued. Use this code at any course
                  checkout to enrol free.
                </p>
              </div>
            </PageHeader>
          }
          className="rd-screen rd-screen-internship-detail"
        >
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Check className="w-8 h-8 text-green-600" />
          </div>
          <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="text-xs uppercase tracking-wider text-gray-500 mb-1">
              Your voucher code
            </div>
            <div className="flex items-center justify-center gap-3">
              <code className="text-2xl font-mono font-bold text-gray-900 tracking-widest">
                {voucherCode}
              </code>
              <button
                onClick={copyCode}
                className="inline-flex items-center gap-1 px-2 py-1 border border-gray-300 rounded hover:bg-white text-sm"
              >
                <Copy className="w-4 h-4" /> Copy
              </button>
            </div>
          </div>
          <div className="mt-4 text-sm text-gray-600">
            Keep this safe — you can also view it any time in{" "}
            <Link
              to="/dashboard/my-vouchers"
              className="text-yellow-700 underline"
            >
              My Vouchers
            </Link>
            .
          </div>
          <div className="mt-6 flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              to="/courses"
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-yellow-400 hover:bg-yellow-500 font-semibold text-gray-900"
            >
              Browse courses
            </Link>
            <Link
              to="/dashboard/my-vouchers"
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg border border-gray-300 hover:bg-gray-50 font-semibold text-gray-900"
            >
              View my vouchers
            </Link>
          </div>
        </PageLayout>
      </div>
    );
  }

  // ---------- Default view ----------
  return (
    <PageLayout
      header={
        <PageBanner
          eyebrow={
            internship.spoc_name
              ? `Mentored by ${internship.spoc_name}`
              : "Mentor-led internship"
          }
          title={internship.title}
          description={internship.description
            ?.replace(/<[^>]*>/g, "")
            .slice(0, 180)}
          image={internship.cover_image || undefined}
          share
          shareUrl={`${window.location.origin}/internships/${internship.slug}`}
        />
      }
      className="rd-screen rd-screen-internship-detail"
    >
      <Link
        to="/internships"
        className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 mb-4"
      >
        <ArrowLeft className="w-4 h-4" /> Back to internships
      </Link>
      {internship.cover_image && (
        <img
          src={internship.cover_image}
          alt={internship.title}
          className="w-full h-64 object-cover rounded-lg mb-6"
        />
      )}
      {internship.description && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            About the program
          </h2>
          <div className="prose max-w-none text-gray-700 whitespace-pre-wrap">
            {internship.description}
          </div>
        </section>
      )}
      <div className="bg-gradient-to-br from-yellow-50 to-amber-50 border border-yellow-200 rounded-lg p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-wider text-gray-600">
            Ready to join?
          </div>
          <p className="mt-2 text-sm text-gray-700 max-w-lg">
            Includes one redeemable course voucher + mentor-led program access.
            You'll see the full fee on the secure Razorpay payment screen.
          </p>
        </div>
        <button
          onClick={handleEnroll}
          disabled={processing}
          className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-yellow-400 hover:bg-yellow-500 font-semibold text-gray-900 disabled:opacity-60 disabled:cursor-not-allowed text-lg"
        >
          {processing ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Processing...
            </>
          ) : (
            <>Enroll Now</>
          )}
        </button>
      </div>
    </PageLayout>
  );
};

export default InternshipDetailPage;
