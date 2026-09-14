import { PageLayout } from "@/components/design-system/PageLayout";
import { PageBanner } from "@/components/design-system/PageBanner";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import {
  ArrowLeft,
  BookOpen,
  Check,
  Loader2,
  Lock,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/store/auth";
import {
  fetchBundle,
  createBundleOrder,
  verifyBundlePayment,
  BundleDetail,
} from "@/api/bundle";

const ensureRazorpayLoaded = async (): Promise<void> => {
  if ((window as any).Razorpay) return;
  await new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      'script[src="https://checkout.razorpay.com/v1/checkout.js"]',
    );
    if (existing) {
      if ((window as any).Razorpay) return resolve();
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () =>
        reject(new Error("Failed to load Razorpay SDK")),
      );
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Razorpay SDK"));
    document.body.appendChild(script);
  });
  // Race guard: onload can fire before the global is actually attached
  // in some browsers/adblock scenarios.
  if (!(window as any).Razorpay) {
    throw new Error(
      "Razorpay SDK did not initialize. Please disable ad-blockers and retry.",
    );
  }
};

const savingsPercent = (bundle: BundleDetail): number => {
  if (bundle.combined_price <= 0) return 0;
  const savings = bundle.combined_price - bundle.bundle_price;
  if (savings <= 0) return 0;
  return Math.round((savings / bundle.combined_price) * 100);
};

export default function BundleDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const [bundle, setBundle] = useState<BundleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    setNotFound(false);
    setError("");
    fetchBundle(slug)
      .then(setBundle)
      .catch((err: any) => {
        if (err?.response?.status === 404) {
          setNotFound(true);
        } else {
          setError("Could not load this bundle");
        }
      })
      .finally(() => setLoading(false));
  }, [slug]);

  const handleBuy = async () => {
    if (!bundle) return;
    if (!isAuthenticated) {
      navigate(
        `/login?redirect=${encodeURIComponent(`/bundles/${bundle.slug}`)}`,
      );
      return;
    }
    setBusy(true);
    setError("");
    try {
      const order = await createBundleOrder(bundle.id);
      await ensureRazorpayLoaded();

      const rzp = new (window as any).Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency || "INR",
        name: "SashaInfinity",
        description: bundle.name,
        order_id: order.order_id,
        prefill: {
          name: user
            ? `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim()
            : "",
          email: user?.user_email ?? "",
        },
        theme: { color: "#f97316" },
        // Never grant anything client-side — the handler only verifies with
        // the server and then navigates. Access is confirmed server-side.
        handler: async (response: any) => {
          try {
            await verifyBundlePayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              bundle_id: bundle.id,
            });
            toast.success(
              "Payment confirmed — all bundle courses are unlocked.",
            );
            navigate("/dashboard");
          } catch (verifyErr: any) {
            const message =
              verifyErr?.response?.data?.detail ??
              "Payment verification failed. Please contact support before paying again.";
            setError(message);
            toast.error(message);
          } finally {
            setBusy(false);
          }
        },
        modal: {
          ondismiss: () => {
            toast.error("Payment cancelled");
            setBusy(false);
          },
        },
      });
      rzp.on("payment.failed", (resp: any) => {
        toast.error(resp?.error?.description || "Payment failed");
        setBusy(false);
      });
      rzp.open();
    } catch (e: any) {
      const message = e?.response?.data?.detail ?? "Could not start payment";
      setError(message);
      toast.error(message);
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
      </div>
    );
  }

  if (notFound || !bundle) {
    return (
      <div className="min-h-screen bg-gray-50 py-12">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-gray-600 mb-4">This bundle could not be found.</p>
          <Link
            to="/bundles"
            className="text-orange-600 hover:underline inline-flex items-center gap-1"
          >
            <ArrowLeft className="h-4 w-4" /> Back to bundles
          </Link>
        </div>
      </div>
    );
  }

  const pct = savingsPercent(bundle);
  const ownedSet = new Set(bundle.owned_course_ids);

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <PageLayout
        header={
          <PageBanner
            eyebrow="Curated learning bundle"
            title={bundle.name}
            description={bundle.description}
            share
            shareTitle={bundle.name}
            shareDescription={`${bundle.courses.length} courses brought together in one learning bundle.`}
          />
        }
        className="rd-screen rd-screen-bundle-detail"
      >
        <Link
          to="/bundles"
          className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="h-4 w-4" /> Back to bundles
        </Link>
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3 text-center">
            {error}
          </div>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-gray-400" />
              Courses in this bundle
            </h2>
            <div className="space-y-3">
              {bundle.courses.map((course) => {
                const owned = ownedSet.has(course.id);
                return (
                  <Card
                    key={course.id}
                    className="p-4 flex items-center justify-between gap-4"
                  >
                    <div>
                      <p className="font-medium text-gray-900">
                        {course.title}
                      </p>
                      {owned && (
                        <Badge variant="success" className="mt-1">
                          You already own this — it stays yours
                        </Badge>
                      )}
                    </div>
                    <span className="text-gray-700 font-medium whitespace-nowrap">
                      ₹{course.price}
                    </span>
                  </Card>
                );
              })}
            </div>
          </div>

          <div>
            <Card className="p-6 sticky top-8">
              <div className="mb-4 flex items-baseline gap-2 flex-wrap">
                <span className="text-3xl font-bold text-gray-900">
                  ₹{bundle.bundle_price}
                </span>
                {bundle.combined_price > bundle.bundle_price && (
                  <span className="text-sm text-gray-500 line-through">
                    ₹{bundle.combined_price}
                  </span>
                )}
              </div>
              {pct > 0 && (
                <div className="flex items-center gap-2 text-sm text-emerald-700 mb-6">
                  <Check className="h-4 w-4 flex-shrink-0" />
                  Save {pct}% vs buying individually
                </div>
              )}
              <Button className="w-full" disabled={busy} onClick={handleBuy}>
                {busy ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Lock className="h-4 w-4 mr-2" />
                    Buy bundle
                  </>
                )}
              </Button>
              <p className="text-xs text-gray-500 mt-3 text-center">
                Payments are processed securely by Razorpay.
              </p>
            </Card>
          </div>
        </div>
      </PageLayout>
    </div>
  );
}
