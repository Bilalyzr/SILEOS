import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { Check, Crown, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth";
import {
  fetchMembershipPlans,
  fetchMyMembership,
  subscribeToPlan,
  MembershipPlan,
} from "@/api/membership";

// Statuses that mean the user already has (or is on the way to having) an
// active membership — the subscribe CTA is disabled for all of these so a
// member can't accidentally stack a second subscription.
const ACTIVE_STATUSES = ["pending", "active", "grace"];

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

export default function MembershipPage() {
  const [plans, setPlans] = useState<MembershipPlan[]>([]);
  const [loadingPlans, setLoadingPlans] = useState(true);
  const [hasMembership, setHasMembership] = useState(false);
  const [busyPlan, setBusyPlan] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [couponCode, setCouponCode] = useState(""); // R7: coupon with a Razorpay Offer
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    setLoadingPlans(true);
    fetchMembershipPlans()
      .then(setPlans)
      .catch(() => setError("Could not load plans"))
      .finally(() => setLoadingPlans(false));
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      setHasMembership(false);
      return;
    }
    fetchMyMembership()
      .then((m) => setHasMembership(!!m && ACTIVE_STATUSES.includes(m.status)))
      .catch(() => {
        // Non-404 failure (500 / network) — do NOT silently treat this as
        // "no membership" (that would re-enable Subscribe for an existing
        // member during an outage). Leave hasMembership as-is and surface
        // the error instead.
        setError("Could not check your membership — try again shortly");
      });
  }, [isAuthenticated]);

  const handleSubscribe = async (plan: MembershipPlan) => {
    if (!isAuthenticated) {
      navigate("/login?redirect=/membership");
      return;
    }
    setBusyPlan(plan.id);
    setError("");
    try {
      const { subscription_id, razorpay_key } = await subscribeToPlan(
        plan.id,
        couponCode.trim() || undefined,
      );
      await ensureRazorpayLoaded();

      const rzp = new (window as any).Razorpay({
        key: razorpay_key,
        subscription_id,
        name: "SashaInfinity",
        description: `${plan.name} membership`,
        prefill: {
          name: user
            ? `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim()
            : "",
          email: user?.user_email ?? "",
        },
        theme: { color: "#f97316" },
        // Never grant anything client-side — the handler only navigates the
        // user to the dashboard. Activation is confirmed server-side (via
        // webhook / reconciliation), never by this callback firing.
        handler: () => {
          toast.success(
            "Payment received — your membership activates within a minute.",
          );
          navigate("/dashboard?membership=activating");
        },
        modal: {
          ondismiss: () => {
            toast.error("Subscription cancelled");
            setBusyPlan(null);
          },
        },
      });
      rzp.on("payment.failed", (resp: any) => {
        toast.error(resp?.error?.description || "Payment failed");
        setBusyPlan(null);
      });
      rzp.open();
    } catch (e: any) {
      const message =
        e?.response?.data?.detail ?? "Could not start subscription";
      setError(message);
      toast.error(message);
      setBusyPlan(null);
    }
  };

  const renderPrice = (plan: MembershipPlan) => {
    const cadence =
      plan.interval > 1 ? `${plan.interval} ${plan.period}` : plan.period;
    return (
      <span>
        <span className="text-3xl font-bold text-gray-900">₹{plan.price}</span>
        <span className="text-gray-500"> / {cadence}</span>
      </span>
    );
  };

  const renderCoverage = (plan: MembershipPlan) =>
    plan.all_access
      ? "Every paid course"
      : `${plan.covered_courses} courses included`;

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <PageLayout
        header={
          <PageHeader>
            <div className="inline-flex items-center gap-2 text-orange-600 font-semibold text-sm mb-2">
              <Crown className="h-4 w-4" />
              MEMBERSHIP
            </div>
            <h1 className="text-3xl font-bold text-gray-900">
              Choose your membership
            </h1>
            <p className="mt-2 text-gray-600 max-w-2xl mx-auto">
              Subscribe once and get ongoing access to courses — billed
              automatically until you cancel.
            </p>
          </PageHeader>
        }
        className="rd-screen rd-screen-membership"
      >
        <div
          className="max-w-md mx-auto mb-6 flex gap-2"
          data-testid="membership-coupon"
        >
          <input
            value={couponCode}
            onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
            placeholder="Coupon code (optional)"
            className="si-input flex-1"
            aria-label="Coupon code"
          />
          <span className="self-center text-xs text-gray-500">
            applied at checkout
          </span>
        </div>
        {error && (
          <div className="mb-6 max-w-xl mx-auto bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3 text-center">
            {error}
          </div>
        )}
        {loadingPlans ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
          </div>
        ) : plans.length === 0 ? (
          <div className="text-center text-gray-500 py-16">
            No membership plans are available right now.
          </div>
        ) : (
          <div className="flex flex-wrap justify-center gap-6">
            {plans.map((plan) => {
              const isBusy = busyPlan === plan.id;
              const disabled = hasMembership || busyPlan !== null;

              return (
                <Card
                  tier="work"
                  key={plan.id}
                  className={`relative p-6 flex flex-col w-full sm:w-80 ${
                    plan.all_access
                      ? "border-orange-400 border-2 shadow-lg"
                      : ""
                  }`}
                >
                  {plan.all_access && (
                    <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-orange-500 text-white text-xs font-semibold px-3 py-0.5 rounded-full whitespace-nowrap">
                      Most popular
                    </span>
                  )}
                  <div className="flex items-center gap-2 mb-2">
                    {plan.all_access && (
                      <Crown className="h-5 w-5 text-orange-500" />
                    )}
                    <h2 className="text-lg font-semibold text-gray-900">
                      {plan.name}
                    </h2>
                  </div>
                  <p className="text-sm text-gray-600 mb-4 flex-1">
                    {plan.description}
                  </p>
                  <div className="mb-4">{renderPrice(plan)}</div>
                  <div className="flex items-center gap-2 text-sm text-gray-700 mb-6">
                    <Check className="h-4 w-4 text-emerald-600 flex-shrink-0" />
                    {renderCoverage(plan)}
                  </div>
                  <Button
                    className="w-full"
                    disabled={disabled}
                    onClick={() => handleSubscribe(plan)}
                  >
                    {isBusy ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : hasMembership ? (
                      "You're a member"
                    ) : (
                      "Subscribe"
                    )}
                  </Button>
                </Card>
              );
            })}
          </div>
        )}
      </PageLayout>
    </div>
  );
}
