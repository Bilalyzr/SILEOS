import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { Check, Crown, Loader2, ShieldCheck, Sparkles, Tag } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import {
  fetchMembershipPlans,
  fetchMyMembership,
  subscribeToPlan,
  MembershipPlan,
} from "@/api/membership";
import {
  SymphoButton,
  SymphoCtaBanner,
  SymphoPageHero,
  SymphoSectionHeader,
} from "@/components/sympho/SymphoSystem";

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
  const [couponCode, setCouponCode] = useState("");
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
        theme: { color: "#bd6a45" },
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

  const renderPrice = (plan: MembershipPlan, isFeatured: boolean) => {
    const cadence =
      plan.interval > 1 ? `${plan.interval} ${plan.period}` : plan.period;
    return (
      <div className="flex items-baseline gap-2">
        <span
          className={`font-display text-4xl font-light ${
            isFeatured ? "text-limestone-50" : "text-ink-900"
          }`}
        >
          ₹{plan.price}
        </span>
        <span
          className={`font-mono text-xs uppercase tracking-[0.14em] ${
            isFeatured ? "text-limestone-300/70" : "text-ink-500"
          }`}
        >
          / {cadence}
        </span>
      </div>
    );
  };

  const renderCoverage = (plan: MembershipPlan) =>
    plan.all_access
      ? "Every paid course"
      : `${plan.covered_courses} courses included`;

  return (
    <div className="sympho-scope rd-screen rd-screen-membership min-h-screen bg-limestone-100 text-ink-900">
      <SymphoPageHero
        index="SI—MEM.01"
        category="ALL-ACCESS SCHOLARSHIP"
        code="RECURRING MEMBERSHIP"
        title="Choose your membership."
        subtitle="Subscribe once and unlock ongoing access to studio courses, interactive 3D labs, and verified certificates — billed automatically with zero friction until you cancel."
        metrics={[
          {
            value: String(plans.length || 3),
            unit: "tiers",
            label: "Subscription Cadences",
            code: "MEM—01",
          },
          {
            value: "100%",
            unit: "flexibility",
            label: "Cancel Anytime",
            code: "MEM—02",
          },
          {
            value: "RAZORPAY",
            unit: "verified",
            label: "Instant Provisioning",
            code: "MEM—03",
          },
        ]}
        actions={
          <>
            <SymphoButton href="#membership-tiers" variant="copper">
              Select Membership Tier
            </SymphoButton>
            <SymphoButton to="/bundles" variant="ghost-dark">
              Compare Course Bundles
            </SymphoButton>
          </>
        }
      />

      <section id="membership-tiers" className="py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <div className="flex flex-col justify-between gap-8 lg:flex-row lg:items-end">
            <div className="flex-1">
              <SymphoSectionHeader
                index="MEM—01"
                category="SUBSCRIPTION SCHEDULE"
                code="PATRONAGE TIERS"
                title="Membership Plans"
                subtitle="Transparent recurring plans backed by Razorpay mandate security and instant library activation."
              />
            </div>

            {/* Coupon Bar */}
            <div
              className="sheet-frame flex w-full max-w-md items-center gap-3 bg-limestone-50 px-4 py-3"
              data-testid="membership-coupon"
            >
              <Tag className="h-4 w-4 flex-shrink-0 text-copper-500" />
              <input
                value={couponCode}
                onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                placeholder="Coupon code (optional)"
                className="flex-1 bg-transparent font-mono text-xs uppercase tracking-[0.14em] text-ink-900 placeholder:text-ink-400 focus:outline-none"
                aria-label="Coupon code"
              />
              <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-500">
                applied at checkout
              </span>
            </div>
          </div>

          {error && (
            <div
              role="alert"
              className="mt-8 sheet-frame border-red-500/40 bg-red-500/10 p-4 text-center font-mono text-xs uppercase tracking-[0.14em] text-red-700"
            >
              {error}
            </div>
          )}

          <div className="mt-12">
            {loadingPlans ? (
              <div className="flex flex-col items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-copper-500" />
                <span className="mt-3 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-500">
                  Loading membership tiers...
                </span>
              </div>
            ) : plans.length === 0 ? (
              <div className="sheet-frame mx-auto max-w-2xl bg-limestone-50 p-12 text-center">
                <Crown className="mx-auto h-8 w-8 text-copper-500" />
                <p className="mt-4 font-display text-2xl font-light text-ink-900">
                  No membership plans are available right now.
                </p>
                <p className="mx-auto mt-2 max-w-md text-sm text-ink-600">
                  Explore our individual courses or curated course bundles while membership tiers are being updated.
                </p>
                <div className="mt-8 flex justify-center gap-3">
                  <SymphoButton to="/courses" variant="primary">
                    Browse Courses
                  </SymphoButton>
                  <SymphoButton to="/bundles" variant="outline">
                    View Bundles
                  </SymphoButton>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {plans.map((plan, idx) => {
                  const isBusy = busyPlan === plan.id;
                  const disabled = hasMembership || busyPlan !== null;
                  const isFeatured = Boolean(plan.all_access);

                  return (
                    <div
                      key={plan.id}
                      className={`sheet-frame relative flex flex-col justify-between p-8 transition-all duration-300 ${
                        isFeatured
                          ? "on-dark bg-ink-950 text-limestone-100 shadow-lift"
                          : "bg-limestone-50 text-ink-900"
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between border-b border-current/10 pb-4">
                          <span className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em] text-copper-500">
                            {isFeatured ? (
                              <Crown className="h-3.5 w-3.5" />
                            ) : (
                              <Sparkles className="h-3.5 w-3.5" />
                            )}
                            TIER—{String(idx + 1).padStart(2, "0")}
                          </span>
                          {isFeatured && (
                            <span className="rounded-pill bg-copper-500 px-3 py-0.5 font-mono text-[10px] font-medium uppercase tracking-[0.14em] text-limestone-50">
                              Most popular
                            </span>
                          )}
                        </div>

                        <h2
                          className={`mt-6 font-display text-3xl font-light ${
                            isFeatured ? "text-limestone-50" : "text-ink-900"
                          }`}
                        >
                          {plan.name}
                        </h2>

                        <p
                          className={`mt-2 text-sm leading-relaxed ${
                            isFeatured ? "text-limestone-200/75" : "text-ink-600"
                          }`}
                        >
                          {plan.description}
                        </p>

                        <div className="mt-6 border-y border-current/10 py-5">
                          {renderPrice(plan, isFeatured)}
                        </div>

                        <ul className="mt-6 space-y-3">
                          <li className="flex items-center gap-3 text-sm">
                            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-copper-500/15 text-copper-500">
                              <Check className="h-3.5 w-3.5" />
                            </span>
                            <span>{renderCoverage(plan)}</span>
                          </li>
                          <li className="flex items-center gap-3 text-sm">
                            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-copper-500/15 text-copper-500">
                              <Check className="h-3.5 w-3.5" />
                            </span>
                            <span>Interactive 3D Labs & Digital Library access</span>
                          </li>
                          <li className="flex items-center gap-3 text-sm">
                            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-copper-500/15 text-copper-500">
                              <ShieldCheck className="h-3.5 w-3.5" />
                            </span>
                            <span>Verified completion certificates included</span>
                          </li>
                        </ul>
                      </div>

                      <div className="mt-8 pt-4">
                        <button
                          type="button"
                          disabled={disabled}
                          onClick={() => handleSubscribe(plan)}
                          className={`w-full rounded-pill px-6 py-3.5 font-mono text-xs uppercase tracking-[0.16em] transition-all disabled:cursor-not-allowed disabled:opacity-50 ${
                            isFeatured
                              ? "bg-copper-500 text-limestone-50 hover:bg-copper-400"
                              : "bg-ink-900 text-limestone-100 hover:bg-copper-500"
                          }`}
                        >
                          {isBusy ? (
                            <span className="inline-flex items-center justify-center gap-2">
                              <Loader2 className="h-4 w-4 animate-spin" />
                              Processing...
                            </span>
                          ) : hasMembership ? (
                            "You're a member"
                          ) : (
                            "Subscribe"
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </section>

      <SymphoCtaBanner
        code="SI—MEM // 02"
        eyebrow="INSTITUTIONAL LICENSING"
        title="Deploying SashaInfinity for an entire campus?"
        description="Explore SashaInfinity Campus OS for schools, colleges, and training institutes with unified admissions, fee ledgers, and cohort analytics."
        primaryLabel="Explore Campus OS"
        primaryTo="/for-institutions"
        secondaryLabel="Contact Admissions Team"
        secondaryTo="/contact"
      />
    </div>
  );
}
